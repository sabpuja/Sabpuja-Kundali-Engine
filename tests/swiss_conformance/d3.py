"""KUN-03 D3 conformance profile: the 24 frozen requests under the location-based timezone policy.

D3 refuses UTC, GMT, Etc/* and their aliases (TIMEZONE_NOT_LOCATION_BASED), so
nine requests the KUN-03 current profile v1 charted are now refused and six
refusals now stop at D3 first. This module keeps spec.json, cases.json and
profiles/kun03-current-v1.json byte-identical and runs, each with its own verdict
and combined fail-closed:

* d3: the 24 requests with the D3 profile's expectations (7 charts, 17 refusals),
  whole-sign swetest and binding references, 49 checks per chart;
* numeric continuation: every chart the v1 profile compared keeps its 49 checks.
  SC-01, SC-04 and SC-24 run as geographic equivalents (same UTC instant, same
  coordinates, a verified offset) in production, and each is proven equal to its
  original request; SC-11, SC-14, SC-15, SC-16, SC-19 and SC-20 run their original
  requests with the D3 check bypassed in this process only (TEST-ONLY, never
  production acceptance);
* historical supplement: SC-09 (historical gate and D3 bypassed) and SC-23
  (historical gate bypassed), test-only as in v1;
* divergence: the v1 current-profile runner and the archival PR #18 runner,
  unchanged, against the D3 engine; each must fail exactly where recorded.

Swiss-on-Swiss conformance only; see the profile's claim boundary.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
import csv
import io
import json

from . import conformance as c
from . import current as cur
from . import inputs, profile

PASS, FAIL, BLOCKED = c.PASS, c.FAIL, c.BLOCKED
HERE = Path(__file__).resolve().parent
PROFILE_PATH = HERE / "profiles" / "kun03-d3-v1.json"
PROFILE_SCHEMA = "sabpuja-swiss-conformance-d3-profile/1"
PROFILE_ID = "KUN-03-D3"
PROFILE_VERSION = 1
# Byte-exact SHA-256 of the D3 profile; changing it needs a code change, QA review and a new profile_version.
PROFILE_SHA256 = "942a0eac0a18b45f26de91b238d0b5b3868713076a4a50e457598b1fa999b980"
REPORT_SCHEMA = "sabpuja-swiss-conformance-d3-report/1"
D3 = "TIMEZONE_NOT_LOCATION_BASED"
ZONE_POLICY = "KUN-03 D3 location-based birthplace timezone, version 1"
SOURCE_MILESTONE = "KUN-03 D3 (location-based birthplace timezone)"

D3_CASES = {
    "SC-01": D3, "SC-02": "chart", "SC-03": "chart", "SC-04": D3, "SC-05": "chart", "SC-06": "chart",
    "SC-07": "TIME_NONEXISTENT_LOCAL", "SC-08": "chart", "SC-09": D3, "SC-10": D3, "SC-11": D3, "SC-12": D3,
    "SC-13": D3, "SC-14": D3, "SC-15": D3, "SC-16": D3, "SC-17": D3, "SC-18": D3, "SC-19": D3, "SC-20": D3,
    "SC-21": "chart", "SC-22": "chart", "SC-23": "HISTORICAL_CLOCK_UNVERIFIED", "SC-24": D3,
}
CHART_CASES = sum(1 for v in D3_CASES.values() if v == "chart")
NEWLY_REFUSED = tuple(cid for cid, v in profile.CURRENT_CASES.items() if v == "chart" and D3_CASES[cid] != "chart")
REFUSED_EARLIER = tuple(cid for cid, v in profile.CURRENT_CASES.items() if v != "chart" and D3_CASES[cid] != v)
CHANGED_CASES = tuple(cid for cid in D3_CASES if cid in NEWLY_REFUSED + REFUSED_EARLIER)

# Production numerics for three newly refused charts: the frozen instant and coordinates on a
# geographic zone whose pinned offset at that instant is the one written.
GEOGRAPHIC_EQUIVALENTS = {
    "SC-01": {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata"},
    "SC-04": {"birth_datetime": "2000-02-29T11:00:00+11:00", "timezone": "Australia/Sydney"},
    "SC-24": {"birth_datetime": "2026-03-20T09:00:00+00:00", "timezone": "Atlantic/Reykjavik"},
}
# No geographic equivalent: SC-11's local date is 2101 in Tokyo (outside the window) and the
# others are open ocean at 0 deg or the antimeridian. Original requests, D3 bypassed, test-only.
D3_OVERRIDE_SUPPLEMENT = ("SC-11", "SC-14", "SC-15", "SC-16", "SC-19", "SC-20")
HISTORICAL_SUPPLEMENT = {"SC-09": ["historical_clock", "d3"], "SC-23": ["historical_clock"]}
PLACIDUS_OBSERVATION_CASES = profile.PLACIDUS_OBSERVATION_CASES
CONTINUATION = {**{cid: "geographic_equivalent" for cid in GEOGRAPHIC_EQUIVALENTS},
                **{cid: "d3_override_supplement" for cid in D3_OVERRIDE_SUPPLEMENT},
                "SC-09": "historical_supplement"}
EQUIVALENCE_QUANTITY = "same_chart_as_original_request_with_d3_bypassed"
_REQUESTS = {case["id"]: case["request"] for case in c.load_json(HERE / "cases.json")["cases"]}

# Exact outcome of the unchanged v1 current-profile runner against the D3 engine.
_V1_REFUSED = "engine refused (TIMEZONE_NOT_LOCATION_BASED) a case expected to chart"
V1_DIVERGENCE = {
    "cases": {**{cid: _V1_REFUSED for cid in NEWLY_REFUSED},
              **{cid: f"engine_refusal_code: {D3}" for cid in REFUSED_EARLIER}},
    "historical_supplement": {"SC-09": _V1_REFUSED},
}
# Exact outcome of the unchanged PR #18 runner against the D3 engine.
_ARCHIVAL_REFUSED = "engine refused (INPUT_REFUSED) a case expected to chart"
ARCHIVAL_DIVERGENCE = {
    **{cid: _ARCHIVAL_REFUSED for cid in ("SC-01", "SC-04", "SC-09", "SC-11", "SC-14", "SC-15", "SC-16", "SC-19",
                                          "SC-20", "SC-23", "SC-24")},
    "SC-17": "expected refusal ASCENDANT_UNCOMPUTABLE, engine gave INPUT_REFUSED",
    "SC-18": "expected refusal ASCENDANT_UNCOMPUTABLE, engine gave INPUT_REFUSED",
}
ARCHIVAL_DIVERGENCE = {cid: ARCHIVAL_DIVERGENCE[cid] for cid in D3_CASES if cid in ARCHIVAL_DIVERGENCE}

N = inputs.CHECKS_PER_CHART
COUNTS = {
    "cases": len(D3_CASES),
    "chart_cases": CHART_CASES,
    "refusal_cases": len(D3_CASES) - CHART_CASES,
    "checks_per_chart": N,
    "comparison_checks": CHART_CASES * N,
    "self_consistency_checks": CHART_CASES * inputs.SELF_CHECKS_PER_CHART,
    "house_method_checks": CHART_CASES * len(cur.HOUSE_METHOD_QUANTITIES),
    "refusal_checks": (len(D3_CASES) - CHART_CASES) * profile.REFUSAL_CHECKS_PER_CASE,
    "placidus_reference_observations": len(PLACIDUS_OBSERVATION_CASES) * profile.PLACIDUS_OBSERVATIONS_PER_CASE,
    "geographic_equivalent_cases": len(GEOGRAPHIC_EQUIVALENTS),
    "geographic_equivalent_comparison_checks": len(GEOGRAPHIC_EQUIVALENTS) * N,
    "geographic_equivalent_self_consistency_checks": len(GEOGRAPHIC_EQUIVALENTS) * inputs.SELF_CHECKS_PER_CHART,
    "geographic_equivalent_house_method_checks": len(GEOGRAPHIC_EQUIVALENTS) * len(cur.HOUSE_METHOD_QUANTITIES),
    "geographic_equivalence_checks": len(GEOGRAPHIC_EQUIVALENTS),
    "d3_override_supplement_cases": len(D3_OVERRIDE_SUPPLEMENT),
    "d3_override_supplement_comparison_checks": len(D3_OVERRIDE_SUPPLEMENT) * N,
    "d3_override_supplement_self_consistency_checks": len(D3_OVERRIDE_SUPPLEMENT) * inputs.SELF_CHECKS_PER_CHART,
    "d3_override_supplement_house_method_checks": len(D3_OVERRIDE_SUPPLEMENT) * len(cur.HOUSE_METHOD_QUANTITIES),
    "historical_supplement_cases": len(HISTORICAL_SUPPLEMENT),
    "historical_supplement_comparison_checks": len(HISTORICAL_SUPPLEMENT) * N,
    "historical_supplement_self_consistency_checks": len(HISTORICAL_SUPPLEMENT) * inputs.SELF_CHECKS_PER_CHART,
    "historical_supplement_house_method_checks": len(HISTORICAL_SUPPLEMENT) * len(cur.HOUSE_METHOD_QUANTITIES),
    "v1_comparison_checks": profile.COUNTS["comparison_checks"],
    "v1_comparison_checks_accounted": (CHART_CASES + len(GEOGRAPHIC_EQUIVALENTS) + len(D3_OVERRIDE_SUPPLEMENT)) * N,
    "v1_historical_supplement_comparison_checks_accounted": len(HISTORICAL_SUPPLEMENT) * N,
}
# Pinned literal totals: a derived count that drifts from these blocks too.
EXPECTED_TOTALS = {"chart_cases": 7, "refusal_cases": 17, "comparison_checks": 343, "self_consistency_checks": 14,
                   "house_method_checks": 28, "refusal_checks": 34, "geographic_equivalent_comparison_checks": 147,
                   "d3_override_supplement_comparison_checks": 294, "v1_comparison_checks": 784,
                   "v1_comparison_checks_accounted": 784, "v1_historical_supplement_comparison_checks_accounted": 98}

_KEYS = {"schema", "profile_id", "profile_version", "status", "claim_boundary", "zone_policy", "base", "counts",
         "cases", "numeric_continuation", "historical_numerics_supplement", "placidus_reference_observations",
         "expected_divergence"}


# ---------------------------------------------------------------- overrides (test-only)

@contextmanager
def d3_override():
    """Test-only: the D3 check accepts every recognised key inside this block; restoration is verified."""
    from sabpuja_kundali import zone_policy
    original = zone_policy.is_location_based
    with mock.patch.object(zone_policy, "is_location_based", lambda name: True):
        yield
    if zone_policy.is_location_based is not original:
        raise RuntimeError("D3 check was not restored")


@contextmanager
def overrides(names):
    with (cur.historical_gate_override() if "historical_clock" in names else _nothing()), \
         (d3_override() if "d3" in names else _nothing()):
        yield


@contextmanager
def _nothing():
    yield


# ---------------------------------------------------------------- profile

def _text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _outcome(code: str) -> tuple[str, str | None]:
    return ("chart", None) if code == "chart" else ("refuse", code)


def validate_profile(doc) -> list[str]:
    if not isinstance(doc, dict):
        return ["D3_PROFILE_NOT_OBJECT"]
    errors = []
    if set(doc) != _KEYS:
        errors.append("D3_PROFILE_KEYS")
    if doc.get("schema") != PROFILE_SCHEMA:
        errors.append("D3_PROFILE_SCHEMA")
    if doc.get("profile_id") != PROFILE_ID or type(doc.get("profile_version")) is not int \
            or doc.get("profile_version") != PROFILE_VERSION:
        errors.append("D3_PROFILE_VERSION")
    if not _text(doc.get("status")) or not doc["status"].startswith("FROZEN"):
        errors.append("D3_PROFILE_NOT_FROZEN")
    claim = doc.get("claim_boundary")
    if not _text(claim) or any(m not in claim for m in (inputs.CLAIM_MARKER, "NOT mathematical verification",
                                                         "NOT historical clock verification", "NOT geolocation",
                                                         "never production acceptance")):
        errors.append("D3_PROFILE_CLAIM_BOUNDARY")
    if doc.get("zone_policy") != ZONE_POLICY:
        errors.append("D3_PROFILE_ZONE_POLICY")
    base = doc.get("base")
    if not isinstance(base, dict) or set(base) != {"framework", "spec.json", "cases.json", "previous_profile"} \
            or not _text(base.get("framework")) \
            or any(base.get(n) != inputs.INPUT_SHA256[n] for n in ("spec.json", "cases.json")) \
            or base.get("previous_profile") != {"id": profile.PROFILE_ID, "version": profile.PROFILE_VERSION,
                                                "sha256": profile.PROFILE_SHA256}:
        errors.append("D3_PROFILE_BASE_HASH")
    if doc.get("counts") != COUNTS or {k: COUNTS[k] for k in EXPECTED_TOTALS} != EXPECTED_TOTALS \
            or COUNTS["v1_comparison_checks_accounted"] != COUNTS["v1_comparison_checks"]:
        errors.append("D3_PROFILE_COUNTS")
    errors += _validate_cases(doc.get("cases"))
    errors += _validate_continuation(doc.get("numeric_continuation"))
    supplement = doc.get("historical_numerics_supplement")
    if not isinstance(supplement, dict) or set(supplement) != {"cases", "label"} \
            or supplement.get("cases") != HISTORICAL_SUPPLEMENT or not _text(supplement.get("label")) \
            or "TEST-ONLY" not in supplement["label"] or "NOT production acceptance" not in supplement["label"]:
        errors.append("D3_PROFILE_HISTORICAL_SUPPLEMENT")
    placidus = doc.get("placidus_reference_observations")
    if not isinstance(placidus, dict) or set(placidus) != {"cases", "reason"} \
            or placidus.get("cases") != list(PLACIDUS_OBSERVATION_CASES) or not _text(placidus.get("reason")):
        errors.append("D3_PROFILE_PLACIDUS_OBSERVATIONS")
    if doc.get("expected_divergence") != {"v1_current_profile": V1_DIVERGENCE, "archival_pr18": ARCHIVAL_DIVERGENCE}:
        errors.append("D3_PROFILE_DIVERGENCE")
    return errors


def _validate_cases(cases) -> list[str]:
    if not isinstance(cases, list):
        return ["D3_PROFILE_CASES_NOT_LIST"]
    errors, ids = [], []
    for entry in cases:
        if not isinstance(entry, dict) or set(entry) != {"id", "expect", "expected_refusal", "previous", "change"}:
            errors.append("D3_PROFILE_CASE_KEYS")
            continue
        cid = entry["id"]
        if cid not in D3_CASES:
            errors.append("D3_PROFILE_CASE_UNEXPECTED")
            continue
        ids.append(cid)
        if (entry["expect"], entry["expected_refusal"]) != _outcome(D3_CASES[cid]):
            errors.append(f"D3_PROFILE_CASE_CODE: {cid}")
        expect, refusal = _outcome(profile.CURRENT_CASES[cid])
        if entry["previous"] != {"profile": f"{profile.PROFILE_ID} v{profile.PROFILE_VERSION}",
                                 "expect": expect, "expected_refusal": refusal}:
            errors.append(f"D3_PROFILE_CASE_PREVIOUS: {cid}")
        change = entry["change"]
        if cid in CHANGED_CASES:
            if not isinstance(change, dict) or set(change) != {"source_milestone", "reason", "numeric_continuation"} \
                    or change["source_milestone"] != SOURCE_MILESTONE or not _text(change["reason"]) \
                    or change["numeric_continuation"] != CONTINUATION.get(cid):
                errors.append(f"D3_PROFILE_CASE_CHANGE: {cid}")
        elif change is not None:
            errors.append(f"D3_PROFILE_CASE_CHANGE: {cid}")
    if len(ids) != len(set(ids)):
        errors.append("D3_PROFILE_CASE_DUPLICATE")
    errors += [f"D3_PROFILE_CASE_MISSING: {cid}" for cid in D3_CASES if cid not in ids]
    if not errors and ids != list(inputs.CASES):
        errors.append("D3_PROFILE_CASE_ORDER")
    return errors


def _validate_continuation(doc) -> list[str]:
    if not isinstance(doc, dict) or set(doc) != {"geographic_equivalents", "d3_override_supplement"}:
        return ["D3_PROFILE_CONTINUATION"]
    errors = []
    geo = doc["geographic_equivalents"]
    if not isinstance(geo, dict) or set(geo) != {"cases", "basis"} or not _text(geo.get("basis")) \
            or "production" not in geo["basis"] or geo.get("cases") != GEOGRAPHIC_EQUIVALENTS:
        errors.append("D3_PROFILE_GEOGRAPHIC_EQUIVALENTS")
    sup = doc["d3_override_supplement"]
    if not isinstance(sup, dict) or set(sup) != {"cases", "label"} or sup.get("cases") != list(D3_OVERRIDE_SUPPLEMENT) \
            or not _text(sup.get("label")) or "TEST-ONLY" not in sup["label"] \
            or "NOT production acceptance" not in sup["label"]:
        errors.append("D3_PROFILE_OVERRIDE_SUPPLEMENT")
    return errors


def load_profile(path: Path = PROFILE_PATH) -> tuple[dict | None, dict, list[str]]:
    """Return (profile, input record, errors). The profile is None unless it is fully valid."""
    try:
        data = inputs.read_bytes(path)
    except inputs.InputError as exc:
        return None, {"sha256": None, "bytes": None, "frozen_sha256": PROFILE_SHA256}, [f"D3_PROFILE_{exc.code}"]
    digest = inputs.sha256_bytes(data)
    record = {"sha256": digest, "bytes": len(data), "frozen_sha256": PROFILE_SHA256}
    errors = [] if digest == PROFILE_SHA256 else ["D3_PROFILE_SHA256_MISMATCH"]
    try:
        doc = inputs.parse_strict(data)
    except inputs.InputError as exc:
        return None, record, errors + [f"D3_PROFILE_{exc.code}"]
    errors += validate_profile(doc)
    return (None if errors else doc), record, errors


# ---------------------------------------------------------------- cases

def run_d3_case(case: dict, swetest: str, ephe: str, spec: dict) -> dict:
    expected = D3_CASES[case["id"]]
    status, payload, record = cur.call_engine(case["request"], ephe)
    if expected == "chart":
        return cur.chart_result(case, swetest, ephe, spec, status, payload, record)
    return cur.refusal_result(case, expected, swetest, ephe, spec, status, payload, record)


def _restored(case: dict, ephe: str) -> bool:
    """Production refuses the original request again, with its D3 code, after an override block."""
    return cur.call_engine(case["request"], ephe)[:2] == ("refused", D3_CASES[case["id"]])


def run_geographic_case(case: dict, swetest: str, ephe: str, spec: dict) -> dict:
    """Production run of the equivalent request, then proof that it equals the original with D3 bypassed."""
    cid = case["id"]
    equivalent = dict(case, request={**case["request"], **GEOGRAPHIC_EQUIVALENTS[cid]})
    status, payload, record = cur.call_engine(equivalent["request"], ephe)
    result = cur.chart_result(equivalent, swetest, ephe, spec, status, payload, record)
    result["request"] = equivalent["request"]
    with d3_override():
        o_status, original, _ = cur.call_engine(case["request"], ephe)
    same = (status == o_status == "chart"
            and payload == {**original, "birth": {**original["birth"], "timezone": equivalent["request"]["timezone"]}})
    result["equivalence"] = [{"case": cid, "kind": "equivalence", "quantity": EQUIVALENCE_QUANTITY,
                              "detail": {"utc": payload["birth"]["utc"] if status == "chart" else None,
                                         "original_status": o_status},
                              "outcome": PASS if same else FAIL}]
    result["override_restored"] = _restored(case, ephe)
    if not same or not result["override_restored"]:
        result.update(outcome=FAIL, reasons=result["reasons"] + (
            [] if same else ["equivalent request differs from the original with D3 bypassed"]) + (
            [] if result["override_restored"] else ["D3 check not restored"]))
    return result


def run_override_case(case: dict, names: list[str], swetest: str, ephe: str, spec: dict) -> dict:
    with overrides(names):
        status, payload, record = cur.call_engine(case["request"], ephe)
    result = cur.chart_result(case, swetest, ephe, spec, status, payload, record)
    result["overrides"] = list(names)
    result["override_restored"] = _restored(case, ephe)
    if not result["override_restored"]:
        result.update(outcome=FAIL, reasons=result["reasons"] + ["override not restored"])
    return result


def v1_divergence(cases: list[dict], swetest: str, ephe: str, spec: dict) -> dict:
    """The unchanged v1 current-profile cases and supplement against the D3 engine, no override."""
    by_id = {case["id"]: case for case in cases}
    rows = [cur.run_current_case(case, swetest, ephe, spec) for case in cases]
    supplement = [cur.run_supplement_case(by_id[cid], swetest, ephe, spec) for cid in profile.HISTORICAL_SUPPLEMENT]
    failed = {r["case"]: "; ".join(r["reasons"]) for r in rows if r["outcome"] != PASS}
    failed_supplement = {r["case"]: r["reasons"][0] for r in supplement if r["outcome"] != PASS}
    observed = {"cases": failed, "historical_supplement": failed_supplement}
    findings = [] if observed == V1_DIVERGENCE else ["v1 profile divergence differs from the recorded divergence"]
    return {"outcome": PASS if not findings else FAIL, "observed": observed, "findings": findings,
            "passed_cases": [r["case"] for r in rows if r["outcome"] == PASS],
            "passed_supplement": [r["case"] for r in supplement if r["outcome"] == PASS]}


def archival_divergence(archival: dict, current: list[dict]) -> dict:
    if archival["run_reasons"]:
        return {"outcome": BLOCKED, "findings": [f"archival run blocked: {r}" for r in archival["run_reasons"]],
                "per_chart": []}
    findings = []
    by_case = {r["case"]: r for r in archival["cases"]}
    failed = {cid: r["reasons"] for cid, r in by_case.items() if r["outcome"] == FAIL}
    if failed != {cid: [reason] for cid, reason in ARCHIVAL_DIVERGENCE.items()}:
        findings.append("archival FAIL set differs from the recorded D3 divergence")
    findings += [f"archival case {cid} is {r['outcome']}" for cid, r in by_case.items()
                 if cid not in ARCHIVAL_DIVERGENCE and r["outcome"] != PASS]
    if archival["verdict"] != c.VERDICT[FAIL]:
        findings.append(f"archival verdict is {archival['verdict']}, expected the recorded FAIL")
    per_chart = []
    key = lambda x: (x["kind"], x["quantity"])
    for r in current:
        if r["expect"] != "chart":
            continue
        old = by_case.get(r["case"], {"checks": [], "outcome": None})
        same = sorted(map(key, old["checks"])) == sorted(map(key, r["checks"]))
        values = {key(x): x["value"] for x in old["checks"]} == {key(x): x["value"] for x in r["checks"]}
        per_chart.append({"case": r["case"], "archival_checks": len(old["checks"]), "current_checks": len(r["checks"]),
                          "archival_outcome": old["outcome"], "current_outcome": r["outcome"],
                          "same_quantities": same, "same_engine_and_binding_values": values})
        if not (same and values and len(r["checks"]) == N and old["outcome"] == r["outcome"] == PASS):
            findings.append(f"chart {r['case']} lost or changed checks between profiles")
    if len(per_chart) != CHART_CASES:
        findings.append("D3 chart set incomplete")
    return {"outcome": FAIL if findings else PASS, "findings": findings, "per_chart": per_chart}


# ---------------------------------------------------------------- coverage

def _chart_errors(r: dict, label: str) -> list[str]:
    errors = []
    keys = [x["quantity"] if x["kind"] not in ("binding_vs_swetest_deg", "engine_vs_swetest_deg")
            else f"{x['kind']}:{x['quantity']}" for x in r["checks"]]
    if len(keys) != len(set(keys)) or set(keys) != inputs.CHART_QUANTITIES:
        errors.append(f"COVERAGE_CHART_QUANTITIES: {label} {r['case']}")
    if len(r["self_consistency"]) != inputs.SELF_CHECKS_PER_CHART:
        errors.append(f"COVERAGE_SELF_CONSISTENCY: {label} {r['case']}")
    if [x["quantity"] for x in r["method_checks"]] != list(cur.HOUSE_METHOD_QUANTITIES):
        errors.append(f"COVERAGE_HOUSE_METHOD: {label} {r['case']}")
    return errors


def coverage(results: list[dict], geographic: list[dict], supplement: list[dict],
             historical: list[dict]) -> tuple[dict, list[str]]:
    errors = []
    sets = ((results, list(D3_CASES), "COVERAGE_CASE_SET"),
            (geographic, list(GEOGRAPHIC_EQUIVALENTS), "COVERAGE_GEOGRAPHIC_SET"),
            (supplement, list(D3_OVERRIDE_SUPPLEMENT), "COVERAGE_OVERRIDE_SUPPLEMENT_SET"),
            (historical, list(HISTORICAL_SUPPLEMENT), "COVERAGE_HISTORICAL_SUPPLEMENT_SET"))
    errors += [code for rows, wanted, code in sets if [r["case"] for r in rows] != wanted]
    for label, rows in (("d3", results), ("geographic", geographic), ("override", supplement),
                        ("historical", historical)):
        for r in rows:
            if r["outcome"] != PASS:
                continue
            if r["expect"] == "chart":
                errors += _chart_errors(r, label)
            else:
                if [x["quantity"] for x in r["checks"]] != list(cur.REFUSAL_QUANTITIES):
                    errors.append(f"COVERAGE_REFUSAL_CHECKS: {r['case']}")
                observed = [x["quantity"] for x in r["reference_observations"]]
                if observed != (list(cur.OBSERVATION_QUANTITIES) if r["case"] in PLACIDUS_OBSERVATION_CASES else []):
                    errors.append(f"COVERAGE_PLACIDUS_OBSERVATIONS: {r['case']}")
    for r in geographic:
        if r["outcome"] == PASS and [x["quantity"] for x in r.get("equivalence", [])] != [EQUIVALENCE_QUANTITY]:
            errors.append(f"COVERAGE_EQUIVALENCE: {r['case']}")
    charts = [r for r in results if r["expect"] == "chart"]
    refusals = [r for r in results if r["expect"] == "refuse"]
    passed = lambda rows: sum(x["outcome"] == PASS for x in rows)
    total = lambda rows, k: sum(len(r[k]) for r in rows)
    counts = {
        "cases": len(results), "chart_cases": len(charts), "refusal_cases": len(refusals),
        "case_outcomes": {o: sum(r["outcome"] == o for r in results) for o in (PASS, FAIL, BLOCKED, c.INDETERMINATE)},
        "comparison_checks": total(charts, "checks"),
        "comparison_checks_passed": sum(passed(r["checks"]) for r in charts),
        "self_consistency_checks": total(charts, "self_consistency"),
        "house_method_checks": total(charts, "method_checks"),
        "refusal_checks": total(refusals, "checks"),
        "refusal_checks_passed": sum(passed(r["checks"]) for r in refusals),
        "placidus_reference_observations": total(refusals, "reference_observations"),
        "geographic_equivalent_cases": len(geographic),
        "geographic_equivalent_comparison_checks": total(geographic, "checks"),
        "geographic_equivalent_comparison_checks_passed": sum(passed(r["checks"]) for r in geographic),
        "geographic_equivalent_self_consistency_checks": total(geographic, "self_consistency"),
        "geographic_equivalent_house_method_checks": total(geographic, "method_checks"),
        "geographic_equivalence_checks": sum(len(r.get("equivalence", [])) for r in geographic),
        "geographic_equivalence_checks_passed": sum(passed(r.get("equivalence", [])) for r in geographic),
        "d3_override_supplement_cases": len(supplement),
        "d3_override_supplement_comparison_checks": total(supplement, "checks"),
        "d3_override_supplement_comparison_checks_passed": sum(passed(r["checks"]) for r in supplement),
        "d3_override_supplement_self_consistency_checks": total(supplement, "self_consistency"),
        "d3_override_supplement_house_method_checks": total(supplement, "method_checks"),
        "historical_supplement_cases": len(historical),
        "historical_supplement_comparison_checks": total(historical, "checks"),
        "historical_supplement_self_consistency_checks": total(historical, "self_consistency"),
        "historical_supplement_house_method_checks": total(historical, "method_checks"),
    }
    counts["v1_comparison_checks_accounted"] = (counts["comparison_checks"] + counts[
        "geographic_equivalent_comparison_checks"] + counts["d3_override_supplement_comparison_checks"])
    counts["v1_historical_supplement_comparison_checks_accounted"] = counts["historical_supplement_comparison_checks"]
    for key in [k for k in COUNTS if k in counts]:
        if counts[key] != COUNTS[key]:
            errors.append(f"COVERAGE_COUNT: {key}")
    if counts["v1_comparison_checks_accounted"] != profile.COUNTS["comparison_checks"]:
        errors.append("COVERAGE_V1_CHECKS_NOT_ACCOUNTED")
    return counts, errors


# ---------------------------------------------------------------- run and report

def run_all(swetest: str | None, ephe: str | None, receipt: str | None, *, env: dict | None = None,
            profile_path: Path = PROFILE_PATH, clock=lambda: datetime.now(timezone.utc)) -> dict:
    started = clock().strftime("%Y-%m-%dT%H:%M:%SZ")
    spec, cases, input_record, reasons = inputs.load_inputs(c.HERE / "spec.json", c.HERE / "cases.json")
    _, v1_record, v1_errors = profile.load_profile()
    prof, profile_record, profile_errors = load_profile(profile_path)
    input_record["profile_v1"], input_record["profile_d3"] = v1_record, profile_record
    env = env if env is not None else c.capture_environment(swetest, receipt, ephe)
    reasons = reasons + v1_errors + profile_errors + c.run_reasons(env, {"required_versions": inputs.REQUIRED_VERSIONS})
    results, geographic, supplement, historical = [], [], [], []
    v1 = archival = archival_check = None
    if not reasons:
        by_id = {case["id"]: case for case in cases}
        results = [run_d3_case(case, swetest, ephe, spec) for case in cases]
        geographic = [run_geographic_case(by_id[cid], swetest, ephe, spec) for cid in GEOGRAPHIC_EQUIVALENTS]
        supplement = [run_override_case(by_id[cid], ["d3"], swetest, ephe, spec) for cid in D3_OVERRIDE_SUPPLEMENT]
        historical = [run_override_case(by_id[cid], names, swetest, ephe, spec)
                      for cid, names in HISTORICAL_SUPPLEMENT.items()]
        v1 = v1_divergence(cases, swetest, ephe, spec)
        archival = c.run_all(swetest, ephe, receipt, env=env, clock=clock)
        archival_check = archival_divergence(archival, results)
    counts, coverage_errors = coverage(results, geographic, supplement, historical)
    parts = ("d3", "numeric_continuation", "historical_supplement", "v1_divergence", "archival_divergence")
    if reasons:
        coverage_errors = []
        verdicts = dict.fromkeys(parts, BLOCKED)
    else:
        verdicts = {"d3": c.overall([r["outcome"] for r in results]),
                    "numeric_continuation": c.overall([r["outcome"] for r in geographic + supplement]),
                    "historical_supplement": c.overall([r["outcome"] for r in historical]),
                    "v1_divergence": v1["outcome"], "archival_divergence": archival_check["outcome"]}
        if coverage_errors:
            verdicts = {k: (BLOCKED if v == PASS else v) for k, v in verdicts.items()}
    verdict = c.overall(list(verdicts.values()))
    return {"report_schema": REPORT_SCHEMA,
            "claim_boundary": prof["claim_boundary"] if prof else inputs.CLAIM_MARKER,
            "profile": {"id": PROFILE_ID, "version": PROFILE_VERSION, "zone_policy": ZONE_POLICY,
                        "house_letter": profile.HOUSE_LETTER, "sha256": profile_record["sha256"]},
            "started_utc": started, "finished_utc": clock().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "environment": env, "inputs": input_record, "run_reasons": reasons,
            "coverage": counts, "coverage_errors": coverage_errors,
            "spec_tolerances_deg": spec["tolerances_deg"] if spec else None,
            "changes": prof["cases"] if prof else None,
            "cases": results, "geographic_equivalents": geographic, "d3_override_supplement": supplement,
            "d3_override_supplement_label": prof["numeric_continuation"]["d3_override_supplement"]["label"] if prof else None,
            "historical_supplement": historical,
            "historical_supplement_label": prof["historical_numerics_supplement"]["label"] if prof else None,
            "v1_divergence": v1, "archival": archival, "archival_divergence": archival_check,
            "verdicts": {k: c.VERDICT[v] for k, v in verdicts.items()},
            "verdict": c.VERDICT[verdict], "exit_code": c.EXIT[verdict]}


def to_json(report: dict) -> str:
    return cur.to_json(report)


def to_csv(report: dict) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["section", "case", "kind", "quantity", "value", "reference", "diff", "tolerance", "outcome"])
    sections = [("d3", report["cases"]), ("geographic_equivalent", report["geographic_equivalents"]),
                ("d3_override_supplement_TEST_ONLY", report["d3_override_supplement"]),
                ("historical_supplement_TEST_ONLY", report["historical_supplement"]),
                ("archival", (report["archival"] or {}).get("cases", []))]
    for name, rows in sections:
        for case in rows:
            for x in (case["checks"] + case.get("method_checks", []) + case.get("reference_observations", [])
                      + case.get("equivalence", [])):
                writer.writerow([name, x["case"], x["kind"], x["quantity"],
                                 cur._cell(x.get("value", json.dumps(x.get("detail"), default=repr))),
                                 cur._cell(x.get("reference", "")), "" if x.get("diff") is None else repr(x["diff"]),
                                 "" if x.get("tolerance") is None else repr(x["tolerance"]), x["outcome"]])
            for s in case["self_consistency"]:
                writer.writerow([name, s["case"], "self_consistency", s["check"], "", "",
                                 "" if s["diff_deg"] is None else repr(s["diff_deg"]),
                                 "" if s["limit_deg"] is None else repr(s["limit_deg"]), s["result"]])
    return out.getvalue()


def delta_rows(report: dict) -> list[str]:
    """Case-by-case: v1 expectation, D3 expectation, observed outcome and where the numerics went."""
    rows = ["| Case | Timezone | v1 profile | D3 profile | D3 outcome | Numeric continuation |", "|---|---|---|---|---|---|"]
    by_case = {r["case"]: r for r in report["cases"]}
    cont = {r["case"]: f"geographic equivalent {r['request']['timezone']}: {r['outcome']}"
            for r in report["geographic_equivalents"]}
    cont.update({r["case"]: f"TEST-ONLY {'+'.join(r['overrides'])} bypass: {r['outcome']}"
                 for r in report["d3_override_supplement"] + report["historical_supplement"]})
    for entry in report["changes"] or []:
        cid, r = entry["id"], by_case.get(entry["id"], {})
        prev = entry["previous"]
        rows.append(f"| {cid} | {_REQUESTS[cid]['timezone']} | {prev['expect']} {prev['expected_refusal'] or ''} | "
                    f"{entry['expect']} {entry['expected_refusal'] or ''} | {r.get('outcome', '')} | {cont.get(cid, '')} |")
    return rows


def to_markdown(report: dict) -> str:
    env = report["environment"]
    lines = [f"# {report['verdict']} (exit {report['exit_code']}): KUN-03 D3 conformance, profile "
             f"{report['profile']['id']} v{report['profile']['version']}", "",
             f"_{report['claim_boundary']}_", "", f"Zone policy: {report['profile']['zone_policy']}", "",
             "| Part | Verdict |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in report["verdicts"].items()]
    lines += ["", f"- Commit `{env['git']['commit']}` dirty={env['git']['dirty']}",
              f"- Python {env['python']} ({env['platform']}); pyswisseph {env['binding']['pyswisseph']}; "
              f"Swiss library {env['binding']['swiss_library']}",
              f"- swetest sha256 `{env['swetest']['sha256']}`; source {env['swetest']['source'] or 'not approved'}",
              f"- Ephemeris verified={env['ephemeris']['verified']} {env['ephemeris']['error_code'] or ''}".rstrip()]
    lines += [f"- Input `{n}` sha256 `{r['sha256']}` (pinned `{r.get('frozen_sha256')}`)"
              for n, r in sorted(report["inputs"].items())]
    lines += ["", "## Run-level blocking reasons", ""] + ([f"- {r}" for r in report["run_reasons"]] or ["- none"])
    lines += ["", "## Coverage", ""] + [f"- {k}: {v}" for k, v in report["coverage"].items()]
    lines += [f"- COVERAGE ERROR: {e}" for e in report["coverage_errors"]]
    lines += ["", "## Case-by-case delta (v1 to D3)", ""] + delta_rows(report)
    lines += ["", "## D3-supported charts and D3 refusals (production, no override)", ""] + cur._case_rows(report["cases"])
    lines += ["", "## Numeric continuation: geographic equivalents (production, no override)", ""]
    lines += cur._case_rows(report["geographic_equivalents"])
    lines += [f"- {r['case']}: {json.dumps(r['request'], sort_keys=True)}; equal to the original with D3 bypassed = "
              f"{[x['outcome'] for x in r.get('equivalence', [])]}; D3 restored = {r.get('override_restored')}"
              for r in report["geographic_equivalents"]]
    lines += ["", "## Numeric continuation: D3 override supplement", "", f"**{report['d3_override_supplement_label']}**", ""]
    lines += cur._case_rows(report["d3_override_supplement"])
    lines += [f"- {r['case']}: D3 restored and refusing again = {r.get('override_restored')}"
              for r in report["d3_override_supplement"]]
    lines += ["", "## Historical-numerics supplement", "", f"**{report['historical_supplement_label']}**", ""]
    lines += cur._case_rows(report["historical_supplement"])
    lines += [f"- {r['case']}: overrides {r.get('overrides')}; restored and refusing again = {r.get('override_restored')}"
              for r in report["historical_supplement"]]
    v1 = report["v1_divergence"]
    if v1:
        lines += ["", f"## v1 current profile, unchanged expectations, against the D3 engine: divergence {v1['outcome']}", ""]
        lines += [f"- {cid}: {reason}" for cid, reason in v1["observed"]["cases"].items()]
        lines += [f"- supplement {cid}: {reason}" for cid, reason in v1["observed"]["historical_supplement"].items()]
        lines += [f"- still passing: {', '.join(v1['passed_cases'])}; supplement: {', '.join(v1['passed_supplement'])}"]
        lines += [f"- FINDING: {f}" for f in v1["findings"]]
    archival, check = report["archival"], report["archival_divergence"]
    if archival:
        lines += ["", f"## Archival PR #18 profile, unchanged runner: {archival['verdict']}; divergence {check['outcome']}",
                  "", "| Case | Expect | Outcome | Checks (pass/total) | Notes |", "|---|---|---|---|---|"]
        for r in archival["cases"]:
            lines.append(f"| {r['case']} | {r['expect']} | {r['outcome']} | "
                         f"{sum(x['outcome'] == PASS for x in r['checks'])}/{len(r['checks'])} | {'; '.join(r['reasons'])} |")
        lines += [""] + ([f"- FINDING: {f}" for f in check["findings"]] or ["- no findings"])
        lines += ["", "| Chart | Archival checks | D3 checks | Same quantities | Same values | Archival | D3 |",
                  "|---|---|---|---|---|---|---|"]
        lines += [f"| {p['case']} | {p['archival_checks']} | {p['current_checks']} | {p['same_quantities']} | "
                  f"{p['same_engine_and_binding_values']} | {p['archival_outcome']} | {p['current_outcome']} |"
                  for p in check["per_chart"]]
    return "\n".join(lines) + "\n"


def write_reports(report: dict, directory: Path) -> list[Path]:
    commit = (report["environment"]["git"]["commit"] or "nogit")[:12]
    stamp = report["started_utc"].replace("-", "").replace(":", "")
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / f"swiss-d3-{commit}-{stamp}"
    paths = [base.with_suffix(".json"), base.with_suffix(".csv"), base.with_suffix(".md")]
    for path, text in zip(paths, (to_json(report), to_csv(report), to_markdown(report))):
        path.write_text(text, encoding="utf-8")
    return paths
