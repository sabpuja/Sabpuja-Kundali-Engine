"""PII-safe run environment capture (qa-architecture.md section 4, run header).

Records versions and hashes only. Never records paths, host or user names,
environment variables or birth data. Failures are recorded as codes.
"""
from __future__ import annotations

from importlib import metadata
from pathlib import Path
import platform
import subprocess
import zoneinfo


def _dist_version(name: str) -> str | None:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return None


def tzdata_in_use() -> dict:
    """The tzdata zoneinfo actually reads: first TZPATH entry with tzdata.zi, else the tzdata package."""
    for root in zoneinfo.TZPATH:
        zi = Path(root) / "tzdata.zi"
        if zi.is_file():
            with zi.open(encoding="utf-8") as handle:
                first = handle.readline().strip()
            if first.startswith("# version "):
                return {"source": "system", "version": first.removeprefix("# version ")}
            return {"source": "system", "version": None}
    version = _dist_version("tzdata")
    return {"source": "tzdata-package" if version else None, "version": version}


def git_state(repo_root: Path) -> dict:
    def git(*args: str) -> str:
        return subprocess.run(["git", "-C", str(repo_root), *args], check=True,
                              capture_output=True, text=True, timeout=30).stdout
    try:
        head = git("rev-parse", "HEAD").strip()
        dirty = bool(git("status", "--porcelain").strip())
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}
    return {"commit": head, "dirty": dirty}


def swiss_state() -> dict:
    try:
        import swisseph
        library = swisseph.version
    except ImportError:
        library = None
    return {"pyswisseph": _dist_version("pyswisseph"), "swiss_library": library}


def ephemeris_state(ephe_path: str | None) -> dict:
    """Verify with the engine's own unchanged gate; record hashes, never the path."""
    from sabpuja_kundali.ephemeris import EphemerisDataError, load_manifest, verify_ephemeris_dir
    manifest = load_manifest()
    state = {"manifest_version": manifest["manifest_version"],
             "source_commit": manifest["source"]["commit"], "verified": False,
             "error_code": None, "files": {}}
    try:
        verify_ephemeris_dir(ephe_path)
    except EphemerisDataError as exc:
        state["error_code"] = exc.code
        return state
    state["verified"] = True
    state["files"] = {e["name"]: e["sha256"] for e in manifest["files"] if e.get("required") is True}
    return state


def capture_environment(repo_root: Path, ephe_path: str | None) -> dict:
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": f"{platform.system()}-{platform.machine()}",
        "swiss": swiss_state(),
        "tzdata": tzdata_in_use(),
        "git": git_state(repo_root),
        "ephemeris": ephemeris_state(ephe_path),
    }


def environment_reasons(env: dict) -> list[str]:
    """Run-level blocking reasons from the captured environment."""
    reasons = []
    if env["git"]["commit"] is None:
        reasons.append("GIT_UNAVAILABLE")
    elif env["git"]["dirty"]:
        reasons.append("DIRTY_TREE")
    if not env["ephemeris"]["verified"]:
        reasons.append(f"EPHEMERIS_UNVERIFIED: {env['ephemeris']['error_code']}")
    if not env["tzdata"]["version"]:
        reasons.append("TZDATA_UNKNOWN")
    if not env["swiss"]["pyswisseph"] or not env["swiss"]["swiss_library"]:
        reasons.append("SWISS_VERSION_UNKNOWN")
    return reasons
