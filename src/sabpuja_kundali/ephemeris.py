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
import re

_MANIFEST_NAME = "ephemeris-manifest.json"
_SHA256_HEX = re.compile(r"[0-9a-f]{64}")


class EphemerisDataError(RuntimeError):
    """Required ephemeris data is absent, unreadable or does not match the manifest."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code


def _malformed() -> EphemerisDataError:
    # Fixed text: never echoes a manifest value, which could be a path or arbitrary data.
    return EphemerisDataError("EPHEMERIS_MANIFEST_INVALID", "ephemeris manifest has an unexpected structure")


def _is_int(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _required_entries(manifest: dict) -> list[dict]:
    """Return the required file entries after checking every field the gate reads.

    Each `files` entry must be an object with a boolean `required`. A required entry
    needs a plain file `name` (no directory part), a non-negative integer `size_bytes`
    and a lowercase hex `sha256`. Anything else is EPHEMERIS_MANIFEST_INVALID.
    """
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, list):
        raise _malformed()
    required = []
    for entry in files:
        if not isinstance(entry, dict) or not isinstance(entry.get("required"), bool):
            raise _malformed()
        if not entry["required"]:
            continue
        name, size, sha = entry.get("name"), entry.get("size_bytes"), entry.get("sha256")
        if (not isinstance(name, str) or name in ("", ".", "..") or "/" in name or "\\" in name
                or "\0" in name or not _is_int(size) or size < 0
                or not isinstance(sha, str) or not _SHA256_HEX.fullmatch(sha)):
            raise _malformed()
        required.append(entry)
    return required


def load_manifest() -> dict:
    """Read the packaged manifest; a read, parse or shape failure is a structured refusal.

    Besides the file entries, checks the fields that calculation metadata reads, so a
    malformed manifest is refused before any Swiss call rather than after it.
    """
    try:
        text = resources.files(__package__).joinpath(_MANIFEST_NAME).read_text(encoding="utf-8")
        manifest = json.loads(text)
    except (OSError, ValueError):
        raise EphemerisDataError("EPHEMERIS_MANIFEST_INVALID", "ephemeris manifest cannot be read") from None
    _required_entries(manifest)
    source, coverage = manifest.get("source"), manifest.get("coverage")
    if (not isinstance(manifest.get("manifest_version"), str)
            or not isinstance(source, dict) or not isinstance(source.get("repository"), str)
            or not isinstance(source.get("commit"), str)
            or not isinstance(coverage, dict) or not _is_int(coverage.get("start_year"))
            or not _is_int(coverage.get("end_year"))):
        raise _malformed()
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
    required = _required_entries(manifest)
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
