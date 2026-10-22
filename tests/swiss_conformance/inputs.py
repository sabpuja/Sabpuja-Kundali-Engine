"""Strict loading and validation of the frozen spec, cases and swetest receipt.

Anything that does not match the predeclared inputs exactly is reported as an
error code; the runner turns any code into SWISS-CONFORMANCE BLOCKED before
the engine or swetest is called. The constants below are the frozen policy;
spec.json and cases.json must agree with them, byte for byte (SHA-256) and
field by field.
"""
from __future__ import annotations

from pathlib import Path
import hashlib
import json
import math
import re

from . import swetest_cli

MAX_INPUT_BYTES = 1 << 20

SPEC_SCHEMA = "sabpuja-swiss-conformance-spec/1"
CASES_SCHEMA = "sabpuja-swiss-conformance-cases/1"
REQUIRED_VERSIONS = {"swiss_library": "2.10.03", "pyswisseph": "2.10.3.2"}
CLAIM_MARKER = "NOT independent astronomical validation"
TOLERANCES = {
    "binding_vs_swetest": 1e-09,
    "engine_vs_swetest": 1e-08,
    "swetest_ut_jd_day": 1e-09,
    "independent_jd_day": 1e-09,
    "ketu_identity_deg": 1e-08,
}
BODIES = ("sun", "moon", "mercury", "venus", "mars", "jupiter", "saturn", "rahu_mean")
SWETEST_NAMES = {"sun": "Sun", "moon": "Moon", "mercury": "Mercury", "venus": "Venus", "mars": "Mars",
                 "jupiter": "Jupiter", "saturn": "Saturn", "rahu_mean": "mean Node", "lagna": "Ascendant"}
VERDICT_CODES = {"SWISS-CONFORMANCE PASS": 0, "SWISS-CONFORMANCE FAIL": 1, "SWISS-CONFORMANCE BLOCKED": 2}

# Predeclared coverage: case id -> "chart" or the expected refusal code.
CASES = {
    "SC-01": "chart", "SC-02": "chart", "SC-03": "chart", "SC-04": "chart", "SC-05": "chart",
    "SC-06": "chart", "SC-07": "INPUT_REFUSED", "SC-08": "chart", "SC-09": "chart", "SC-10": "INPUT_REFUSED",
    "SC-11": "chart", "SC-12": "INPUT_REFUSED", "SC-13": "INPUT_REFUSED", "SC-14": "chart", "SC-15": "chart",
    "SC-16": "chart", "SC-17": "ASCENDANT_UNCOMPUTABLE", "SC-18": "ASCENDANT_UNCOMPUTABLE", "SC-19": "chart",
    "SC-20": "chart", "SC-21": "chart", "SC-22": "chart", "SC-23": "chart", "SC-24": "chart",
}
CHART_CASES = sum(1 for v in CASES.values() if v == "chart")
CHART_BODIES = (*BODIES, "lagna")
# Exact quantities every chart case must report (49 per case, 882 in all).
CHART_QUANTITIES = frozenset(
    ["utc", "jd_vs_independent_formula", "jd_vs_swetest_ut_line_1", "jd_vs_swetest_ut_line_2",
     "moon.nakshatra_pada"]
    + [f"{kind}:{b}" for kind in ("binding_vs_swetest_deg", "engine_vs_swetest_deg") for b in CHART_BODIES]
    + [f"{b}.rashi" for b in CHART_BODIES] + [f"{b}.navamsa_rashi" for b in CHART_BODIES]
    + [f"{b}.whole_sign_house" for b in BODIES])
CHECKS_PER_CHART = len(CHART_QUANTITIES)
SELF_CHECKS_PER_CHART = 2

# Byte-exact SHA-256 of the frozen inputs; changing either file needs a code change and QA review.
INPUT_SHA256 = {
    "spec.json": "642a770d713c11bc42fc92fe441da02e4848522fc4978ae3049dddbea33d12a8",
    "cases.json": "afd8864cd84c246011d9ed8510b3efa5ed5e6c68daa6381114a77adf0ef399c9",
}

# Approved swetest sources. The receipt is the builder's testimony plus the binary's
# SHA-256; it is not cryptographic proof that the binary was compiled from that source.
OFFICIAL_SOURCE = ("https://github.com/aloistr/swisseph", "c69c14adb7a0f94829586ffd92cd422aacb21e86")
APPROVED_SOURCES = {
    OFFICIAL_SOURCE: "official aloistr/swisseph@c69c14a (reference build)",
    ("pyswisseph 2.10.3.2 sdist (PyPI) libswe/",
     "sdist sha256 c54c305e83dbd5d2b71e58d8a69d8ee41de24c4d3328ce09e2af860a3537624d"):
        "pyswisseph 2.10.3.2 sdist libswe (cross-check build, NOT the official source)",
}
RECEIPT_KEYS = ("swetest_sha256", "source_repository", "source_commit", "build_command", "compiler",
                "license", "swiss_version")
_ID = re.compile(r"^SC-\d{2}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


class InputError(ValueError):
    """Carries a code only; never the offending text."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise InputError("NON_FINITE_NUMBER")
    return value


def _no_constant(name: str):
    raise InputError("NON_FINITE_NUMBER")


def _no_duplicate_keys(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise InputError("DUPLICATE_KEY")
        out[key] = value
    return out


def read_bytes(path: Path) -> bytes:
    try:
        size = Path(path).stat().st_size
    except OSError:
        raise InputError("MISSING") from None
    if size > MAX_INPUT_BYTES:
        raise InputError("OVERLONG")
    return Path(path).read_bytes()


def parse_strict(data: bytes):
    """JSON with no NaN/Infinity, no overflowing floats and no duplicate keys."""
    try:
        return json.loads(data.decode("utf-8"), parse_float=_finite_float, parse_constant=_no_constant,
                          object_pairs_hook=_no_duplicate_keys)
    except InputError:
        raise
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise InputError("INVALID_JSON") from None


def load_json(path: Path):
    return parse_strict(read_bytes(path))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def is_number(value) -> bool:
    """Finite int or float; never raises (an int too large for a float is not a usable number)."""
    if type(value) not in (int, float):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def valid_tolerance(value) -> bool:
    return isinstance(value, float) and math.isfinite(value) and 0 < value <= 1e-6


def validate_spec(spec) -> list[str]:
    if not isinstance(spec, dict):
        return ["SPEC_NOT_OBJECT"]
    errors = []
    required = {"schema", "status", "claim_boundary", "required_versions", "swetest_switches", "tolerances_deg",
                "boundary_rule", "verdict_rule", "verdicts", "bodies", "swetest_names"}
    if set(spec) != required:
        errors.append("SPEC_KEYS")
    if spec.get("schema") != SPEC_SCHEMA:
        errors.append("SPEC_SCHEMA")
    if not isinstance(spec.get("status"), str) or not spec["status"].startswith("FROZEN"):
        errors.append("SPEC_NOT_FROZEN")
    if not isinstance(spec.get("claim_boundary"), str) or CLAIM_MARKER not in spec["claim_boundary"]:
        errors.append("SPEC_CLAIM_BOUNDARY")
    if spec.get("required_versions") != REQUIRED_VERSIONS:
        errors.append("SPEC_REQUIRED_VERSIONS")
    switches = spec.get("swetest_switches")
    planets = ["-edir<EPHE>", "-bj<JD>", *swetest_cli.PLANET_ARGS]
    houses = ["-edir<EPHE>", "-bj<JD>", *swetest_cli.HOUSE_ARGS, "-house<LON>,<LAT>,P"]
    if not isinstance(switches, dict) or switches.get("planets") != planets or switches.get("houses") != houses:
        errors.append("SPEC_SWETEST_SWITCHES")
    tolerances = spec.get("tolerances_deg")
    if not isinstance(tolerances, dict) or set(tolerances) != set(TOLERANCES):
        errors.append("SPEC_TOLERANCE_KEYS")
    else:
        for name, entry in sorted(tolerances.items()):
            value = entry.get("value") if isinstance(entry, dict) else None
            if not valid_tolerance(value):
                errors.append(f"SPEC_TOLERANCE_INVALID: {name}")
            elif value != TOLERANCES[name]:
                errors.append(f"SPEC_TOLERANCE_NOT_FROZEN: {name}")
            if not isinstance(entry, dict) or not isinstance(entry.get("basis"), str) or not entry["basis"].strip():
                errors.append(f"SPEC_TOLERANCE_BASIS: {name}")
    for key in ("boundary_rule", "verdict_rule"):
        if not isinstance(spec.get(key), str) or not spec[key].strip():
            errors.append(f"SPEC_{key.upper()}")
    if spec.get("verdicts") != VERDICT_CODES:
        errors.append("SPEC_VERDICTS")
    if spec.get("bodies") != list(BODIES):
        errors.append("SPEC_BODIES")
    if spec.get("swetest_names") != SWETEST_NAMES:
        errors.append("SPEC_SWETEST_NAMES")
    return errors


def _validate_case(case) -> list[str]:
    if not isinstance(case, dict):
        return ["CASE_NOT_OBJECT"]
    cid = case.get("id")
    label = cid if isinstance(cid, str) and _ID.match(cid) else "?"
    errors = []
    if set(case) != {"id", "purpose", "request", "expect", "expected_utc", "expected_refusal"}:
        errors.append(f"CASE_KEYS: {label}")
    if label == "?":
        return errors + ["CASE_ID_INVALID"]
    if not isinstance(case.get("purpose"), str) or not case["purpose"].strip():
        errors.append(f"CASE_PURPOSE: {label}")
    req = case.get("request")
    if not isinstance(req, dict) or set(req) != {"birth_datetime", "timezone", "latitude", "longitude"}:
        errors.append(f"CASE_REQUEST: {label}")
    elif not (isinstance(req["birth_datetime"], str) and isinstance(req["timezone"], str)
              and is_number(req["latitude"]) and -90 <= req["latitude"] <= 90
              and is_number(req["longitude"]) and -180 <= req["longitude"] <= 180):
        errors.append(f"CASE_REQUEST: {label}")
    expected = CASES.get(cid)
    if expected == "chart":
        if case.get("expect") != "chart" or not isinstance(case.get("expected_utc"), str) \
                or case.get("expected_refusal") is not None:
            errors.append(f"CASE_TYPE_CHANGED: {label}")
    elif expected is not None:
        if case.get("expect") != "refuse" or case.get("expected_utc") is not None \
                or case.get("expected_refusal") != expected:
            errors.append(f"CASE_TYPE_CHANGED: {label}")
    return errors


def validate_cases(document) -> list[str]:
    if not isinstance(document, dict) or set(document) != {"schema", "note", "cases"}:
        return ["CASES_NOT_OBJECT"]
    errors = []
    if document["schema"] != CASES_SCHEMA:
        errors.append("CASES_SCHEMA")
    cases = document["cases"]
    if not isinstance(cases, list):
        return errors + ["CASES_NOT_LIST"]
    ids = []
    for case in cases:
        errors += _validate_case(case)
        if isinstance(case, dict) and isinstance(case.get("id"), str):
            ids.append(case["id"])
    seen = set()
    for cid in ids:
        if cid in seen:
            errors.append(f"CASE_DUPLICATE: {cid if _ID.match(cid) else '?'}")
        seen.add(cid)
    errors += [f"CASE_MISSING: {cid}" for cid in CASES if cid not in seen]
    errors += [f"CASE_UNEXPECTED: {cid if _ID.match(cid) else '?'}" for cid in sorted(seen - set(CASES))]
    if ids != list(CASES) and not errors:
        errors.append("CASE_ORDER")
    return errors


def load_inputs(spec_path: Path, cases_path: Path) -> tuple[dict | None, list | None, dict, list[str]]:
    """Return (spec, cases, input record, errors). Spec/cases are None unless both are fully valid."""
    record, errors, parsed = {}, [], {}
    for label, path, validate in (("spec.json", spec_path, validate_spec), ("cases.json", cases_path, validate_cases)):
        prefix = "SPEC" if label == "spec.json" else "CASES"
        try:
            data = read_bytes(path)
        except InputError as exc:
            record[label] = {"sha256": None, "bytes": None}
            errors.append(f"{prefix}_{exc.code}")
            continue
        digest = sha256_bytes(data)
        record[label] = {"sha256": digest, "bytes": len(data), "frozen_sha256": INPUT_SHA256[label]}
        if digest != INPUT_SHA256[label]:
            errors.append(f"{prefix}_SHA256_MISMATCH")
        try:
            parsed[label] = parse_strict(data)
        except InputError as exc:
            errors.append(f"{prefix}_{exc.code}")
            continue
        errors += validate(parsed[label])
    if errors:
        return None, None, record, errors
    return parsed["spec.json"], parsed["cases.json"]["cases"], record, []


def validate_receipt(receipt, binary_sha256: str) -> tuple[str | None, list[str]]:
    """Return (approved source label, errors) for a swetest build receipt."""
    if not isinstance(receipt, dict) or set(RECEIPT_KEYS) - set(receipt):
        return None, ["SWETEST_BUILD_RECEIPT_INVALID"]
    if not all(isinstance(receipt[k], str) and receipt[k].strip() for k in RECEIPT_KEYS):
        return None, ["SWETEST_BUILD_RECEIPT_INVALID"]
    errors = []
    if not _SHA.match(receipt["swetest_sha256"]) or receipt["swetest_sha256"] != binary_sha256:
        errors.append("SWETEST_BUILD_RECEIPT_MISMATCH")
    source = APPROVED_SOURCES.get((receipt["source_repository"], receipt["source_commit"]))
    if source is None:
        errors.append("SWETEST_SOURCE_NOT_APPROVED")
    if receipt["swiss_version"] != REQUIRED_VERSIONS["swiss_library"]:
        errors.append("SWETEST_RECEIPT_VERSION_MISMATCH")
    return source, errors
