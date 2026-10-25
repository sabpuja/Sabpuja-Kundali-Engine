"""Fail-closed verification of local Swiss Ephemeris data against a pinned manifest.

Runs before any Swiss calculation. Local-only: never downloads data. Error
messages name the failing data file only, never request or birth details.
"""
from __future__ import annotations

from importlib import resources
from pathlib import Path
import hashlib
import json
import os

_MANIFEST_NAME = "ephemeris-manifest.json"


class EphemerisDataError(RuntimeError):
    """Required ephemeris data is absent, unreadable or does not match the manifest."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code


def load_manifest() -> dict:
    """Read the packaged manifest; a read or parse failure is a structured refusal."""
    try:
        text = resources.files(__package__).joinpath(_MANIFEST_NAME).read_text(encoding="utf-8")
        manifest = json.loads(text)
    except (OSError, ValueError):
        raise EphemerisDataError("EPHEMERIS_MANIFEST_INVALID", "ephemeris manifest cannot be read") from None
    if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), list):
        raise EphemerisDataError("EPHEMERIS_MANIFEST_INVALID", "ephemeris manifest has an unexpected structure")
    return manifest


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_ephemeris_dir(ephe_path: str | None, manifest: dict | None = None) -> Path:
    """Return the resolved directory only if every required manifest file matches.

    Optional and unrelated files are ignored: they can never satisfy the check.
    """
    # Swiss Ephemeris gives SE_EPHE_PATH precedence over swe.set_ephe_path, so
    # data outside the verified directory could be read. Refuse instead.
    if os.environ.get("SE_EPHE_PATH"):
        raise EphemerisDataError(
            "EPHEMERIS_PATH_OVERRIDE",
            "SE_EPHE_PATH is set; unset it so only the verified directory is used")
    if not ephe_path or not str(ephe_path).strip():
        raise EphemerisDataError(
            "EPHEMERIS_PATH_MISSING",
            "Missing local Swiss Ephemeris directory; see data/ephemeris/README.md")
    folder = Path(ephe_path)
    if not folder.is_dir():
        raise EphemerisDataError(
            "EPHEMERIS_PATH_MISSING",
            "Missing local Swiss Ephemeris directory; see data/ephemeris/README.md")
    manifest = manifest if manifest is not None else load_manifest()
    required = [entry for entry in manifest["files"] if entry.get("required") is True]
    if not required:
        raise EphemerisDataError("EPHEMERIS_MANIFEST_INVALID", "manifest lists no required files")
    for entry in required:
        name = entry["name"]
        path = folder / name
        if not path.is_file():
            raise EphemerisDataError("EPHEMERIS_FILE_MISSING", f"required file {name} not found")
        try:
            size = path.stat().st_size
            actual = _sha256(path)
        except OSError:
            raise EphemerisDataError("EPHEMERIS_FILE_UNREADABLE", f"required file {name} cannot be read") from None
        if size != entry["size_bytes"] or actual != entry["sha256"]:
            raise EphemerisDataError(
                "EPHEMERIS_FILE_MISMATCH", f"required file {name} does not match the pinned SHA-256")
    return folder.resolve()
