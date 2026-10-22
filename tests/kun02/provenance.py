"""Environmental provenance for KUN-02 evidence: Git, Python, Swiss, ephemeris data, tzdata."""
from __future__ import annotations

from importlib import metadata
from pathlib import Path
import hashlib
import platform
import subprocess
import sys
import zoneinfo

from sabpuja_kundali.ephemeris import load_manifest

from .common import REPO_ROOT


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True,
                              check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNAVAILABLE"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tz_source(key: str = "Asia/Kolkata") -> dict:
    """Which tzdata the zoneinfo module actually reads for `key`, and its version.

    zoneinfo searches TZPATH first and only then the PyPI tzdata package, so the
    host's system tzdata decides civil-time results unless TZPATH is emptied.
    """
    result: dict = {"tzpath": list(zoneinfo.TZPATH), "key": key}
    for root in zoneinfo.TZPATH:
        candidate = Path(root) / key
        if candidate.is_file():
            version = "UNKNOWN"
            zi = Path(root) / "tzdata.zi"
            if zi.is_file():
                first = zi.read_text(encoding="utf-8", errors="replace").splitlines()[0]
                version = first.removeprefix("# version ").strip()
            result.update(source="system", root=root, version=version,
                          tzif_sha256=_sha256(candidate))
            break
    else:
        result.update(source="tzdata-package")
    try:
        import tzdata  # noqa: F401  (optional PyPI package)
        from importlib import resources
        package_file = resources.files("tzdata.zoneinfo").joinpath(*key.split("/"))
        result["tzdata_package"] = {
            "version": metadata.version("tzdata"),
            "iana_version": getattr(tzdata, "IANA_VERSION", "UNKNOWN"),
            "tzif_sha256": hashlib.sha256(package_file.read_bytes()).hexdigest(),
        }
    except ImportError:
        result["tzdata_package"] = None
    return result


def collect(ephe_folder: Path | None) -> dict:
    import swisseph as swe
    manifest = load_manifest()
    files = []
    for entry in manifest["files"]:
        item = {"name": entry["name"], "required": entry["required"],
                "manifest_sha256": entry["sha256"], "manifest_size": entry["size_bytes"]}
        if ephe_folder is not None and (ephe_folder / entry["name"]).is_file():
            path = ephe_folder / entry["name"]
            item.update(actual_sha256=_sha256(path), actual_size=path.stat().st_size)
            item["match"] = (item["actual_sha256"] == entry["sha256"]
                             and item["actual_size"] == entry["size_bytes"])
        files.append(item)
    if ephe_folder is not None:
        swe.set_ephe_path(str(ephe_folder))
        swe.calc_ut(2451545.0, swe.SUN, swe.FLG_SWIEPH)  # opens the file so the tidal value is reported
    status = _git("status", "--porcelain")
    return {
        "git": {"head": _git("rev-parse", "HEAD"), "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
                "clean": status == "", "status_porcelain": status.splitlines()},
        "python": {"version": sys.version.split()[0], "implementation": platform.python_implementation(),
                   "platform": platform.platform()},
        "swiss": {"pyswisseph": metadata.version("pyswisseph"), "swe_version": swe.version,
                  "tidal_acceleration_after_open": swe.get_tid_acc()},
        "ephemeris": {"directory": str(ephe_folder) if ephe_folder else None,
                      "source_commit": manifest["source"]["commit"],
                      "manifest_sha256": _sha256(Path(__file__).resolve().parents[2]
                                                 / "src/sabpuja_kundali/ephemeris-manifest.json"),
                      "files": files},
        "tz": tz_source(),
    }
