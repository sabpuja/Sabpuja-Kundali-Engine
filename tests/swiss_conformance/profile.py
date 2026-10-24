"""Strict loading of the versioned KUN-03 current-engine profile (an overlay on the frozen PR #18 inputs).

spec.json and cases.json stay byte-identical and keep their own SHA-256 pins
in inputs.py. The overlay records, per case, what the current engine is
expected to do and, for every case that differs from the archival profile,
the source milestone and the reason. Anything that does not match the pins
below exactly (file hash, case set, order, codes, counts, house letter,
supplement and observation lists, archival divergence) is an error code, and
the current runner turns any code into SWISS-CONFORMANCE BLOCKED before the
engine or swetest is called.
"""
from __future__ import annotations

from pathlib import Path

from . import inputs, swetest_cli

HERE = Path(__file__).resolve().parent
PROFILE_PATH = HERE / "profiles" / "kun03-current-v1.json"
PROFILE_SCHEMA = "sabpuja-swiss-conformance-profile/1"
PROFILE_ID = "KUN-03-current"
PROFILE_VERSION = 1
# Byte-exact SHA-256 of the overlay; changing it needs a code change, QA review and a new profile_version.
PROFILE_SHA256 = "06d24730205213b680223aaa4077b9efc44335a4eb1638f98deb622bbc17e698"

HOUSE_LETTER = "W"
ARCHIVAL_HOUSE_LETTER = "P"
SWETEST_HOUSES = ["-edir<EPHE>", "-bj<JD>", *swetest_cli.HOUSE_ARGS, f"-house<LON>,<LAT>,{HOUSE_LETTER}"]

# Current expected behaviour: case id -> "chart" or the expected refusal code.
CURRENT_CASES = {
    "SC-01": "chart", "SC-02": "chart", "SC-03": "chart", "SC-04": "chart", "SC-05": "chart",
    "SC-06": "chart", "SC-07": "TIME_NONEXISTENT_LOCAL", "SC-08": "chart", "SC-09": "HISTORICAL_CLOCK_UNVERIFIED",
    "SC-10": "DATE_OUTSIDE_SUPPORTED_RANGE", "SC-11": "chart", "SC-12": "DATE_OUTSIDE_SUPPORTED_RANGE",
    "SC-13": "HISTORICAL_CLOCK_UNVERIFIED", "SC-14": "chart", "SC-15": "chart", "SC-16": "chart",
    "SC-17": "LATITUDE_OUTSIDE_SUPPORTED_BAND", "SC-18": "LATITUDE_OUTSIDE_SUPPORTED_BAND", "SC-19": "chart",
    "SC-20": "chart", "SC-21": "chart", "SC-22": "chart", "SC-23": "HISTORICAL_CLOCK_UNVERIFIED", "SC-24": "chart",
}
CHART_CASES = sum(1 for v in CURRENT_CASES.values() if v == "chart")
CHANGED_CASES = tuple(cid for cid in CURRENT_CASES if CURRENT_CASES[cid] != inputs.CASES[cid])
HOUSE_METHOD_CHECKS_PER_CHART = 4
REFUSAL_CHECKS_PER_CASE = 2
HISTORICAL_SUPPLEMENT = ("SC-09", "SC-23")
PLACIDUS_OBSERVATION_CASES = ("SC-17", "SC-18")
PLACIDUS_OBSERVATIONS_PER_CASE = 2
# Exact outcome of the unchanged PR #18 runner against the current engine.
ARCHIVAL_DIVERGENCE = {
    "SC-09": "engine refused (INPUT_REFUSED) a case expected to chart",
    "SC-17": "expected refusal ASCENDANT_UNCOMPUTABLE, engine gave INPUT_REFUSED",
    "SC-18": "expected refusal ASCENDANT_UNCOMPUTABLE, engine gave INPUT_REFUSED",
    "SC-23": "engine refused (INPUT_REFUSED) a case expected to chart",
}
COUNTS = {
    "cases": len(CURRENT_CASES),
    "chart_cases": CHART_CASES,
    "refusal_cases": len(CURRENT_CASES) - CHART_CASES,
    "checks_per_chart": inputs.CHECKS_PER_CHART,
    "comparison_checks": CHART_CASES * inputs.CHECKS_PER_CHART,
    "self_consistency_per_chart": inputs.SELF_CHECKS_PER_CHART,
    "self_consistency_checks": CHART_CASES * inputs.SELF_CHECKS_PER_CHART,
    "house_method_checks_per_chart": HOUSE_METHOD_CHECKS_PER_CHART,
    "house_method_checks": CHART_CASES * HOUSE_METHOD_CHECKS_PER_CHART,
    "refusal_checks_per_case": REFUSAL_CHECKS_PER_CASE,
    "refusal_checks": (len(CURRENT_CASES) - CHART_CASES) * REFUSAL_CHECKS_PER_CASE,
    "placidus_reference_observations": len(PLACIDUS_OBSERVATION_CASES) * PLACIDUS_OBSERVATIONS_PER_CASE,
    "historical_supplement_cases": len(HISTORICAL_SUPPLEMENT),
    "historical_supplement_comparison_checks": len(HISTORICAL_SUPPLEMENT) * inputs.CHECKS_PER_CHART,
    "historical_supplement_self_consistency_checks": len(HISTORICAL_SUPPLEMENT) * inputs.SELF_CHECKS_PER_CHART,
    "historical_supplement_house_method_checks": len(HISTORICAL_SUPPLEMENT) * HOUSE_METHOD_CHECKS_PER_CHART,
    "archival_cases": len(inputs.CASES),
    "archival_chart_cases": inputs.CHART_CASES,
    "archival_comparison_checks": inputs.CHART_CASES * inputs.CHECKS_PER_CHART,
    "archival_self_consistency_checks": inputs.CHART_CASES * inputs.SELF_CHECKS_PER_CHART,
}
# Pinned literal totals: a derived count that drifts from these blocks too.
EXPECTED_TOTALS = {"chart_cases": 16, "refusal_cases": 8, "comparison_checks": 784, "self_consistency_checks": 32,
                   "archival_comparison_checks": 882, "archival_self_consistency_checks": 36}


def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _archival(cid: str) -> tuple[str, str | None]:
    expected = inputs.CASES[cid]
    return ("chart", None) if expected == "chart" else ("refuse", expected)


def validate_profile(doc) -> list[str]:
    if not isinstance(doc, dict):
        return ["PROFILE_NOT_OBJECT"]
    errors = []
    keys = {"schema", "profile_id", "profile_version", "status", "claim_boundary", "base", "house_reference",
            "counts", "cases", "historical_numerics_supplement", "placidus_reference_observations",
            "archival_run_expected_divergence"}
    if set(doc) != keys:
        errors.append("PROFILE_KEYS")
    if doc.get("schema") != PROFILE_SCHEMA:
        errors.append("PROFILE_SCHEMA")
    if doc.get("profile_id") != PROFILE_ID or type(doc.get("profile_version")) is not int \
            or doc.get("profile_version") != PROFILE_VERSION:
        errors.append("PROFILE_VERSION")
    if not _text(doc.get("status")) or not doc["status"].startswith("FROZEN"):
        errors.append("PROFILE_NOT_FROZEN")
    claim = doc.get("claim_boundary")
    if not _text(claim) or any(m not in claim for m in (inputs.CLAIM_MARKER, "NOT mathematical verification",
                                                         "NOT historical clock verification",
                                                         "never production acceptance")):
        errors.append("PROFILE_CLAIM_BOUNDARY")
    base = doc.get("base")
    if not isinstance(base, dict) or set(base) != {"framework", "spec.json", "cases.json"} \
            or not _text(base.get("framework")) \
            or any(base.get(n) != inputs.INPUT_SHA256[n] for n in ("spec.json", "cases.json")):
        errors.append("PROFILE_BASE_HASH")
    house = doc.get("house_reference")
    if not isinstance(house, dict) or set(house) != {"letter", "engine_call", "swetest_houses", "archival_letter",
                                                     "source_milestone", "reason"} \
            or house.get("letter") != HOUSE_LETTER or house.get("archival_letter") != ARCHIVAL_HOUSE_LETTER \
            or house.get("swetest_houses") != SWETEST_HOUSES \
            or not all(_text(house.get(k)) for k in ("engine_call", "source_milestone", "reason")) \
            or 'b"W"' not in house["engine_call"]:
        errors.append("PROFILE_HOUSE_REFERENCE")
    if doc.get("counts") != COUNTS or {k: COUNTS[k] for k in EXPECTED_TOTALS} != EXPECTED_TOTALS:
        errors.append("PROFILE_COUNTS")
    errors += _validate_cases(doc.get("cases"))
    supplement = doc.get("historical_numerics_supplement")
    if not isinstance(supplement, dict) or set(supplement) != {"cases", "override", "label"} \
            or supplement.get("cases") != list(HISTORICAL_SUPPLEMENT) \
            or not _text(supplement.get("override")) or not _text(supplement.get("label")) \
            or "TEST-ONLY" not in supplement["label"] or "NOT production acceptance" not in supplement["label"]:
        errors.append("PROFILE_HISTORICAL_SUPPLEMENT")
    placidus = doc.get("placidus_reference_observations")
    if not isinstance(placidus, dict) or set(placidus) != {"cases", "observations", "reason"} \
            or placidus.get("cases") != list(PLACIDUS_OBSERVATION_CASES) \
            or not isinstance(placidus.get("observations"), list) \
            or len(placidus["observations"]) != PLACIDUS_OBSERVATIONS_PER_CASE \
            or not all(_text(o) for o in placidus["observations"]) or not _text(placidus.get("reason")):
        errors.append("PROFILE_PLACIDUS_OBSERVATIONS")
    if doc.get("archival_run_expected_divergence") != ARCHIVAL_DIVERGENCE:
        errors.append("PROFILE_ARCHIVAL_DIVERGENCE")
    return errors


def _validate_cases(cases) -> list[str]:
    if not isinstance(cases, list):
        return ["PROFILE_CASES_NOT_LIST"]
    errors, ids = [], []
    for entry in cases:
        if not isinstance(entry, dict) or set(entry) != {"id", "expect", "expected_refusal", "change"}:
            errors.append("PROFILE_CASE_KEYS")
            continue
        cid = entry["id"]
        if cid not in CURRENT_CASES:
            errors.append("PROFILE_CASE_UNEXPECTED")
            continue
        ids.append(cid)
        expected = CURRENT_CASES[cid]
        current = ("chart", None) if expected == "chart" else ("refuse", expected)
        if (entry["expect"], entry["expected_refusal"]) != current:
            errors.append(f"PROFILE_CASE_CODE: {cid}")
        change = entry["change"]
        if cid in CHANGED_CASES:
            if not isinstance(change, dict) or set(change) != {"archival_expect", "archival_expected_refusal",
                                                               "source_milestone", "reason"}:
                errors.append(f"PROFILE_CASE_CHANGE: {cid}")
            elif (change["archival_expect"], change["archival_expected_refusal"]) != _archival(cid) \
                    or not _text(change["source_milestone"]) or not _text(change["reason"]):
                errors.append(f"PROFILE_CASE_CHANGE: {cid}")
        elif change is not None:
            errors.append(f"PROFILE_CASE_CHANGE: {cid}")
    if len(ids) != len(set(ids)):
        errors.append("PROFILE_CASE_DUPLICATE")
    errors += [f"PROFILE_CASE_MISSING: {cid}" for cid in CURRENT_CASES if cid not in ids]
    if not errors and ids != list(inputs.CASES):
        errors.append("PROFILE_CASE_ORDER")
    return errors


def load_profile(path: Path = PROFILE_PATH) -> tuple[dict | None, dict, list[str]]:
    """Return (profile, input record, errors). The profile is None unless it is fully valid."""
    try:
        data = inputs.read_bytes(path)
    except inputs.InputError as exc:
        return None, {"sha256": None, "bytes": None, "frozen_sha256": PROFILE_SHA256}, [f"PROFILE_{exc.code}"]
    digest = inputs.sha256_bytes(data)
    record = {"sha256": digest, "bytes": len(data), "frozen_sha256": PROFILE_SHA256}
    errors = [] if digest == PROFILE_SHA256 else ["PROFILE_SHA256_MISMATCH"]
    try:
        doc = inputs.parse_strict(data)
    except inputs.InputError as exc:
        return None, record, errors + [f"PROFILE_{exc.code}"]
    errors += validate_profile(doc)
    return (None if errors else doc), record, errors
