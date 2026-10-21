"""Method-manifest check (docs/accuracy/qa-architecture.md section 3a).

Read-only: this module never writes or regenerates the manifest. A stale,
missing, unreviewed or malformed manifest is BLOCKED; re-inspection is a
human step reviewed by QA.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import re

from .schema import METHOD_KEYS

MANIFEST_NAME = "method-manifest.json"
REQUIRED_FILES = (
    "src/sabpuja_kundali/engine.py",
    "src/sabpuja_kundali/rules.py",
    "src/sabpuja_kundali/ephemeris.py",
    "src/sabpuja_kundali/ephemeris-manifest.json",
)
_TOP = {"schema", "status", "note", "inspected_commit", "inspector", "qa_review", "files",
        "signature", "emitted_method_block", "facts"}
_SHA1 = re.compile(r"^[0-9a-f]{40}$")


def git_blob_sha1(data: bytes) -> str:
    """The id git gives these bytes as a blob: sha1(b"blob <len>\\0" + data)."""
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def load_manifest(path: Path) -> tuple[dict | None, list[str]]:
    if not path.is_file():
        return None, ["METHOD_MANIFEST_MISSING"]
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None, ["METHOD_MANIFEST_INVALID: not JSON"]
    errors = []
    if not isinstance(manifest, dict) or set(manifest) != _TOP:
        return None, ["METHOD_MANIFEST_INVALID: wrong top-level keys"]
    if not isinstance(manifest["inspected_commit"], str) or not _SHA1.match(manifest["inspected_commit"]):
        errors.append("METHOD_MANIFEST_INVALID: inspected_commit must be a full commit SHA")
    files = manifest["files"]
    if not isinstance(files, dict) or set(files) != set(REQUIRED_FILES) or not all(
            isinstance(v, str) and _SHA1.match(v) for v in files.values()):
        errors.append(f"METHOD_MANIFEST_INVALID: files must pin exactly {list(REQUIRED_FILES)} to blob SHAs")
    sig = manifest["signature"]
    if not isinstance(sig, dict) or set(sig) != set(METHOD_KEYS):
        errors.append("METHOD_MANIFEST_INVALID: signature keys")
    if not isinstance(manifest["emitted_method_block"], dict):
        errors.append("METHOD_MANIFEST_INVALID: emitted_method_block")
    return (None if errors else manifest), errors


def check_manifest(path: Path, repo_root: Path) -> tuple[dict | None, list[str]]:
    """Return (manifest, blocking reasons). Reasons empty only if reviewed and current."""
    manifest, errors = load_manifest(path)
    if manifest is None:
        return None, errors
    reasons = []
    if manifest["status"] != "REVIEWED" or not manifest["qa_review"]:
        reasons.append("METHOD_MANIFEST_UNREVIEWED")
    for rel, pinned in sorted(manifest["files"].items()):
        source = repo_root / rel
        if not source.is_file():
            reasons.append(f"METHOD_MANIFEST_SOURCE_MISSING: {rel}")
        elif git_blob_sha1(source.read_bytes()) != pinned:
            reasons.append(f"METHOD_MANIFEST_STALE: {rel} changed since inspection; re-inspect")
    return manifest, reasons


def signature_mismatches(fixture_signature: dict, manifest: dict) -> list[str]:
    """Keys where the fixture's method signature differs from the inspected engine method."""
    return sorted(k for k in METHOD_KEYS if fixture_signature.get(k) != manifest["signature"].get(k))


def emitted_block_contradictions(emitted: object, manifest: dict) -> list[str]:
    """Keys of the engine's emitted method block that contradict the manifest.

    The emitted block is only checked for contradiction; it can never prove agreement.
    """
    if not isinstance(emitted, dict):
        return ["method block missing"]
    expected = manifest["emitted_method_block"]
    return sorted(k for k in expected if emitted.get(k) != expected[k])
