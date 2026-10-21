"""Strict fixture schema and fixture-set index (revision + SHA-256) validation.

Unknown keys, wrong types and inconsistent dummy/accuracy flags are errors.
A fixture that fails here is BLOCKED; it is never compared.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import re

BODIES = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn",
          "rahu_mean", "ketu_mean", "lagna")
QUANTITIES = ("planet_longitude", "node_longitude", "lagna_longitude", "utc")
METHOD_KEYS = ("ayanamsa_mode", "ayanamsa_kind", "sidereal_bits", "positions", "node",
               "ketu", "ascendant_vehicle", "houses", "time_scale")
_ID = re.compile(r"^(DUMMY-\d{2}|GC-\d{2}|TR-\d{2}|TZ-\d{2}[a-z]?)$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_TOP = {"fixture_id", "fixture_revision", "purpose", "synthetic", "dummy", "reference_verified",
        "accuracy_claim", "input", "derived_time", "method_signature", "references", "expected",
        "tolerance_ids", "approved_decisions_required", "limitations"}
_INPUT = {"birth_datetime", "timezone", "latitude", "longitude"}
_DERIVED = {"utc", "tzdata_version"}
_REF = {"source_id", "source_class", "raw_output_path", "raw_output_sha256", "coverage_utc"}
_EXPECTED = {"sidereal_longitude_deg", "time_conversion"}
_TIME = {"utc", "error_code"}
INDEX_NAME = "INDEX.json"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _keys(obj, allowed: set, where: str, errors: list[str]) -> bool:
    if not isinstance(obj, dict):
        errors.append(f"{where}: must be an object")
        return False
    if set(obj) != allowed:
        missing, extra = sorted(allowed - set(obj)), sorted(set(obj) - allowed)
        errors.append(f"{where}: keys must be exactly {sorted(allowed)} (missing {missing}, unknown {extra})")
        return False
    return True


def _is(value, kind) -> bool:
    """Exact numeric type check; bool is never a number here."""
    if kind is float:
        return type(value) in (int, float) and math.isfinite(value)
    return type(value) is kind


def _str_list(value, where: str, errors: list[str]) -> None:
    if not isinstance(value, list) or not all(isinstance(v, str) and v for v in value):
        errors.append(f"{where}: must be a list of non-empty strings")


def validate_fixture(fixture) -> list[str]:
    """Return schema errors; an empty list means structurally valid (not trusted)."""
    errors: list[str] = []
    if not _keys(fixture, _TOP, "fixture", errors):
        return errors
    fid = fixture["fixture_id"]
    if not isinstance(fid, str) or not _ID.match(fid):
        errors.append("fixture_id: must match DUMMY-NN, GC-NN, TR-NN or TZ-NN[a-z]")
    if not _is(fixture["fixture_revision"], int) or fixture["fixture_revision"] < 1:
        errors.append("fixture_revision: must be an integer >= 1")
    if not isinstance(fixture["purpose"], str) or not fixture["purpose"]:
        errors.append("purpose: must be a non-empty string")
    if fixture["synthetic"] is not True:
        errors.append("synthetic: must be true (no real birth data, ever)")
    for flag in ("dummy", "reference_verified", "accuracy_claim"):
        if type(fixture[flag]) is not bool:
            errors.append(f"{flag}: must be a boolean")
    is_dummy_id = isinstance(fid, str) and fid.startswith("DUMMY-")
    if fixture["dummy"] is True:
        if not is_dummy_id:
            errors.append("dummy fixtures must use a DUMMY-NN id")
        if fixture["reference_verified"] is not False or fixture["accuracy_claim"] is not False:
            errors.append("dummy fixtures must set reference_verified and accuracy_claim to false")
    elif is_dummy_id:
        errors.append("DUMMY-NN ids are reserved for dummy fixtures")
    if fixture["accuracy_claim"] is True and (fixture["dummy"] is not False or fixture["reference_verified"] is not True):
        errors.append("accuracy_claim requires dummy false and reference_verified true")

    if _keys(fixture["input"], _INPUT, "input", errors):
        inp = fixture["input"]
        if not isinstance(inp["birth_datetime"], str) or not isinstance(inp["timezone"], str):
            errors.append("input: birth_datetime and timezone must be strings")
        if not _is(inp["latitude"], float) or not _is(inp["longitude"], float):
            errors.append("input: latitude and longitude must be finite numbers")
    if _keys(fixture["derived_time"], _DERIVED, "derived_time", errors):
        for key in _DERIVED:
            if not isinstance(fixture["derived_time"][key], str) or not fixture["derived_time"][key]:
                errors.append(f"derived_time.{key}: must be a non-empty string")
    if _keys(fixture["method_signature"], set(METHOD_KEYS), "method_signature", errors):
        for key, value in fixture["method_signature"].items():
            ok = _is(value, int) if key == "sidereal_bits" else isinstance(value, str) and bool(value)
            if not ok:
                errors.append(f"method_signature.{key}: wrong type")

    refs = fixture["references"]
    if not isinstance(refs, list) or not refs:
        errors.append("references: must be a non-empty list")
    else:
        for i, ref in enumerate(refs):
            where = f"references[{i}]"
            if not _keys(ref, _REF, where, errors):
                continue
            for key in ("source_id", "source_class", "raw_output_path"):
                if not isinstance(ref[key], str) or not ref[key]:
                    errors.append(f"{where}.{key}: must be a non-empty string")
            if not isinstance(ref["raw_output_sha256"], str) or not _SHA256.match(ref["raw_output_sha256"]):
                errors.append(f"{where}.raw_output_sha256: must be 64 lowercase hex characters")
            cov = ref["coverage_utc"]
            if not (isinstance(cov, list) and len(cov) == 2 and all(isinstance(c, str) for c in cov)):
                errors.append(f"{where}.coverage_utc: must be [start, end] strings")

    if _keys(fixture["expected"], _EXPECTED, "expected", errors):
        lon = fixture["expected"]["sidereal_longitude_deg"]
        if not isinstance(lon, dict) or not set(lon) <= set(BODIES):
            errors.append(f"expected.sidereal_longitude_deg: keys must be among {list(BODIES)}")
        else:
            for body, value in lon.items():
                if value is not None and not (_is(value, float) and 0 <= value < 360):
                    errors.append(f"expected.sidereal_longitude_deg.{body}: must be null or in [0, 360)")
        if _keys(fixture["expected"]["time_conversion"], _TIME, "expected.time_conversion", errors):
            for key, value in fixture["expected"]["time_conversion"].items():
                if value is not None and not isinstance(value, str):
                    errors.append(f"expected.time_conversion.{key}: must be null or a string")

    tol = fixture["tolerance_ids"]
    if not isinstance(tol, dict) or not set(tol) <= set(QUANTITIES) or not all(isinstance(v, str) for v in tol.values()):
        errors.append(f"tolerance_ids: must map quantities among {list(QUANTITIES)} to tolerance ids")
    _str_list(fixture["approved_decisions_required"], "approved_decisions_required", errors)
    _str_list(fixture["limitations"], "limitations", errors)
    return errors


def load_fixture_set(directory: Path) -> tuple[list[dict], dict[str, list[str]], list[str]]:
    """Load fixtures listed in INDEX.json and check revision and SHA-256 of each file.

    Returns (fixture records, per-fixture errors keyed by file name, set-level errors).
    Each record is {"file", "sha256", "fixture" (or None)}.
    """
    set_errors: list[str] = []
    per_file: dict[str, list[str]] = {}
    records: list[dict] = []
    index_path = directory / INDEX_NAME
    if not index_path.is_file():
        return records, per_file, [f"{INDEX_NAME} missing in fixture directory"]
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
        entries = index["fixtures"]
        if not isinstance(entries, dict):
            raise TypeError
    except (ValueError, KeyError, TypeError):
        return records, per_file, [f"{INDEX_NAME} is not a valid fixture index"]
    on_disk = sorted(p.name for p in directory.glob("*.json") if p.name != INDEX_NAME)
    for name in sorted(set(on_disk) - set(entries)):
        set_errors.append(f"{name}: present on disk but not in {INDEX_NAME}")
    for name in sorted(entries):
        errors = per_file.setdefault(name, [])
        path = directory / name
        entry = entries[name]
        record = {"file": name, "sha256": None, "fixture": None}
        records.append(record)
        if not path.is_file():
            errors.append("FIXTURE_FILE_MISSING")
            continue
        record["sha256"] = sha256_file(path)
        if not isinstance(entry, dict) or record["sha256"] != entry.get("sha256"):
            errors.append("FIXTURE_HASH_MISMATCH")
        try:
            fixture = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            errors.append("FIXTURE_NOT_JSON")
            continue
        record["fixture"] = fixture
        schema_errors = validate_fixture(fixture)
        errors.extend(f"SCHEMA_INVALID: {e}" for e in schema_errors)
        if not schema_errors and isinstance(entry, dict) and entry.get("revision") != fixture["fixture_revision"]:
            errors.append("FIXTURE_REVISION_MISMATCH")
    return records, per_file, set_errors
