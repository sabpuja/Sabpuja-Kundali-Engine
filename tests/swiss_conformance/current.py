"""KUN-03 current-profile Swiss conformance, reported beside the unchanged archival PR #18 run.

Three parts, each with its own verdict, combined fail-closed:

* archival: the PR #18 runner, unchanged, against the current engine; it must
  diverge exactly at the cases the overlay records and nowhere else;
* current: the 24 frozen requests with the overlay's expectations, whole-sign
  (W) swetest and binding references, the same 49 checks per chart, house
  method checks proving the W letter, and refusal checks;
* historical supplement: the archival charts SC-09 and SC-23 with the
  historical clock gate overridden in this process only (test-only, never
  production acceptance), so their 49 numeric checks keep running.

Swiss-on-Swiss conformance only; see profile.json's claim boundary.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from unittest import mock
import csv
import io
import json
import math
import re
import subprocess

from . import conformance as c
from . import inputs, oracle, profile, swetest_cli

PASS, FAIL, BLOCKED, INDETERMINATE = c.PASS, c.FAIL, c.BLOCKED, c.INDETERMINATE
REPORT_SCHEMA = "sabpuja-swiss-conformance-reconciliation-report/1"
HOUSE_METHOD_QUANTITIES = ("engine_houses_ex_call", "swetest_house_system_letter", "swetest_whole_sign_cusps",
                           "binding_vs_swetest_cusps")
REFUSAL_QUANTITIES = ("engine_refusal_code", "refused_before_ephemeris_and_swiss")
OBSERVATION_QUANTITIES = ("placidus_failure_reproduced", "whole_sign_ascendant_computes")
_HOUSE_SYSTEM = re.compile(r"^Houses system (\S) \(")
SWETEST_NAMES = {"Sun": "sun", "Moon": "moon", "Mercury": "mercury", "Venus": "venus", "Mars": "mars",
                 "Jupiter": "jupiter", "Saturn": "saturn", "mean Node": "rahu_mean", "Ascendant": "lagna"}


# ---------------------------------------------------------------- engine, recorded

@contextmanager
def historical_gate_override():
    """Test-only (P8 G1): empty historical clock gate inside this block; restoration is verified."""
    from sabpuja_kundali import engine
    original = engine.HISTORICAL_CLOCK_GATE
    with mock.patch.object(engine, "HISTORICAL_CLOCK_GATE", ()):
        yield
    if engine.HISTORICAL_CLOCK_GATE is not original:
        raise RuntimeError("historical clock gate was not restored")


def call_engine(request: dict, ephe: str) -> tuple[str, object, dict]:
    """Return (status, chart or code, record of the ephemeris check and every Swiss call)."""
    import swisseph as swe
    from sabpuja_kundali import engine
    from sabpuja_kundali.ephemeris import EphemerisDataError
    record = {"ephemeris_checked": False, "swiss_calls": [], "houses_ex": []}

    def spy(name, real):
        def wrapper(*args, **kwargs):
            record["swiss_calls"].append(name)
            if name == "houses_ex":
                record["houses_ex"].append({"hsys": args[3], "flags": args[4], "argc": len(args)})
            return real(*args, **kwargs)
        return wrapper

    def checked(*args, **kwargs):
        record["ephemeris_checked"] = True
        return verify(*args, **kwargs)

    verify = engine.verify_ephemeris_dir
    names = ("julday", "set_ephe_path", "set_sid_mode", "set_delta_t_userdef", "calc_ut", "houses_ex")
    patches = [mock.patch.object(engine, "verify_ephemeris_dir", checked)]
    patches += [mock.patch.object(swe, n, spy(n, getattr(swe, n))) for n in names]
    try:
        for p in patches:
            p.start()
        try:
            return "chart", engine.calculate(dict(request), ephe_path=ephe), record
        except (engine.InputRefusalError, engine.ChartComputationError) as exc:
            return "refused", exc.code, record
        except EphemerisDataError as exc:
            return "blocked", exc.code, record
        except ValueError:
            return "refused", "UNCODED_VALUE_ERROR", record
        except Exception as exc:  # noqa: BLE001 - recorded as a type only
            return "blocked", f"ENGINE_ERROR_{type(exc).__name__}", record
    finally:
        for p in reversed(patches):
            p.stop()


# ---------------------------------------------------------------- references

def binding_values(jd: float, lat: float, lon: float, ephe: str, letter: str) -> dict:
    """Unrounded binding values with the engine's flags and state sequence; houses with `letter`.

    'lagna' and 'cusps' are None when Swiss refuses the house method.
    """
    import swisseph as swe
    from sabpuja_kundali.engine import _SWISS_LOCK
    from sabpuja_kundali.ephemeris import verify_ephemeris_dir
    folder = verify_ephemeris_dir(ephe)
    bodies = {"sun": swe.SUN, "moon": swe.MOON, "mercury": swe.MERCURY, "venus": swe.VENUS, "mars": swe.MARS,
              "jupiter": swe.JUPITER, "saturn": swe.SATURN, "rahu_mean": swe.MEAN_NODE}
    out = {}
    with _SWISS_LOCK:
        swe.set_ephe_path(str(folder))
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        swe.set_delta_t_userdef(swe.DELTAT_AUTOMATIC)
        for name, body in bodies.items():
            pos, flags = swe.calc_ut(jd, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
            if not flags & swe.FLG_SWIEPH:
                raise RuntimeError("binding fell back from Swiss files")
            out[name] = float(pos[0])
        try:
            cusps, ascmc = swe.houses_ex(jd, lat, lon, letter.encode("ascii"), swe.FLG_SIDEREAL)
            out["lagna"], out["cusps"] = float(ascmc[0]), [float(x) for x in cusps[:12]]
        except swe.Error:
            out["lagna"] = out["cusps"] = None
    return out


def house_argv(swetest: str, ephe: str, jd: float, lat: float, lon: float, letter: str) -> list[str]:
    return [swetest, f"-edir{ephe}", swetest_cli.jd_arg(jd), *swetest_cli.HOUSE_ARGS, f"-house{lon!r},{lat!r},{letter}"]


def swetest_pair(swetest: str, ephe: str, jd: float, lat: float, lon: float, letter: str) -> dict:
    """Planets and houses from swetest; same strict parser and problem rules as PR #18."""
    out = {"values": {}, "cusps": {}, "house_system": None, "receipts": [], "problems": [], "uts": [],
           "warnings": []}
    for argv in (swetest_cli.planet_argv(swetest, ephe, jd), house_argv(swetest, ephe, jd, lat, lon, letter)):
        try:
            result = swetest_cli.run(argv, ephe)
        except swetest_cli.SwetestOutputError as exc:
            out["problems"].append(f"SWETEST_OUTPUT_MALFORMED: {exc}")
            out["receipts"].append({"argv": [swetest_cli.redact(a, swetest, ephe) for a in argv], "error": str(exc)})
            continue
        except (OSError, subprocess.SubprocessError) as exc:
            out["problems"].append(f"SWETEST_NOT_RUN: {type(exc).__name__}")
            continue
        out["receipts"].append({"argv": result.argv, "exit_code": result.exit_code, "stdout": result.stdout,
                                "stderr": result.stderr, "version": result.version, "ut_jd": result.ut_jd,
                                "ayanamsa_name": result.ayanamsa_name, "warnings": result.warnings})
        if result.exit_code != 0:
            out["problems"].append(f"SWETEST_EXIT_{result.exit_code}")
            continue
        out["uts"].append(result.ut_jd)
        out["warnings"] += result.warnings
        for line in result.stdout.splitlines():
            match = _HOUSE_SYSTEM.match(line.strip())
            if match:
                out["house_system"] = match.group(1)
        for name, value in result.values.items():
            if name in SWETEST_NAMES:
                out["values"][SWETEST_NAMES[name]] = value
            elif name.startswith("house ") and name[6:].isdigit():
                out["cusps"][int(name[6:])] = value
    out["problems"] += [f"SWETEST_WARNING: {w}" for w in out["warnings"]]
    return out


def gate_receipts(sw: dict, spec: dict) -> tuple[str, list[str]] | None:
    for receipt in sw["receipts"]:
        if receipt.get("version") != spec["required_versions"]["swiss_library"]:
            return BLOCKED, ["SWETEST_VERSION_MISMATCH: method-incomparable"]
        if receipt.get("ayanamsa_name") != "Lahiri":
            return FAIL, ["swetest ayanamsa is not Lahiri"]
    return None


# ---------------------------------------------------------------- house method checks

def _check(cid: str, quantity: str, outcome: str, detail) -> dict:
    return {"case": cid, "kind": "method", "quantity": quantity, "detail": detail, "outcome": outcome}


def house_method_checks(cid: str, record: dict, sw: dict, bind: dict, tol: float) -> list[dict]:
    import swisseph as swe
    calls = record["houses_ex"]
    wanted = [{"hsys": profile.HOUSE_LETTER.encode("ascii"), "flags": swe.FLG_SIDEREAL, "argc": 5}]
    checks = [_check(cid, "engine_houses_ex_call", PASS if calls == wanted else FAIL,
                     [{"hsys": x["hsys"].decode("ascii", "replace") if isinstance(x["hsys"], bytes) else repr(x["hsys"]),
                       "flags": x["flags"], "argc": x["argc"]} for x in calls])]
    letter = sw["house_system"]
    checks.append(_check(cid, "swetest_house_system_letter", PASS if letter == profile.HOUSE_LETTER else FAIL, letter))
    asc, cusps = sw["values"].get("lagna"), sw["cusps"]
    if not inputs.is_number(asc) or sorted(cusps) != list(range(1, 13)):
        checks.append(_check(cid, "swetest_whole_sign_cusps", BLOCKED, "ascendant or cusps missing"))
    else:
        first = math.floor(Fraction(asc) / 30)
        expected = [float(((first + n) % 12) * 30) for n in range(12)]
        got = [cusps[n] for n in range(1, 13)]
        near = oracle.boundary_distance(asc, oracle.RASHI_SPAN) <= Fraction(tol)
        checks.append(_check(cid, "swetest_whole_sign_cusps",
                             PASS if got == expected else (INDETERMINATE if near else FAIL), got))
    if bind.get("cusps") is None or len(cusps) != 12:
        checks.append(_check(cid, "binding_vs_swetest_cusps", BLOCKED, "cusps missing"))
    else:
        diffs = [float((Fraction(b) - Fraction(cusps[n + 1]) + 180) % 360 - 180) for n, b in enumerate(bind["cusps"])]
        worst = max(abs(d) for d in diffs)
        checks.append(_check(cid, "binding_vs_swetest_cusps", PASS if worst <= tol else FAIL, worst))
    return checks


# ---------------------------------------------------------------- cases

def chart_result(case: dict, swetest: str, ephe: str, spec: dict, status: str, payload, record: dict) -> dict:
    tol = {k: v["value"] for k, v in spec["tolerances_deg"].items()}
    result = {"case": case["id"], "purpose": case["purpose"], "expect": "chart", "expected_refusal": None,
              "outcome": None, "reasons": [], "receipts": [], "checks": [], "self_consistency": [],
              "method_checks": []}
    if status == "blocked":
        result.update(outcome=BLOCKED, reasons=[f"ENGINE_BLOCKED: {payload}"])
        return result
    if status != "chart":
        result.update(outcome=FAIL, reasons=[f"engine refused ({payload}) a case expected to chart"])
        return result
    if payload["birth"]["utc"] != case["expected_utc"]:
        result["reasons"].append("engine UTC differs from the frozen expected_utc")
    jd = c.engine_jd(payload["birth"]["utc"])
    req = case["request"]
    sw = swetest_pair(swetest, ephe, jd, req["latitude"], req["longitude"], profile.HOUSE_LETTER)
    result["receipts"] = sw["receipts"]
    if sw["problems"]:
        result.update(outcome=BLOCKED, reasons=sw["problems"])
        return result
    gated = gate_receipts(sw, spec)
    if gated:
        result.update(outcome=gated[0], reasons=gated[1])
        return result
    method = payload.get("method", {})
    if (method.get("ayanamsa"), method.get("nodes"), method.get("houses")) != ("Lahiri", "mean", "whole_sign"):
        result.update(outcome=FAIL, reasons=["engine method block contradicts Lahiri / mean node / whole sign"])
        return result
    bind = binding_values(jd, req["latitude"], req["longitude"], ephe, profile.HOUSE_LETTER)
    checks, self_checks = c.compare_chart(case, payload, sw["values"], {k: v for k, v in bind.items() if k != "cusps"},
                                          sw["uts"], jd, tol)
    result["checks"], result["self_consistency"] = checks, self_checks
    result["method_checks"] = house_method_checks(case["id"], record, sw, bind, tol["binding_vs_swetest"])
    outcomes = [x["outcome"] for x in checks + result["method_checks"]]
    outcomes += [FAIL for s in self_checks if s["result"].endswith(FAIL)]
    result["outcome"] = c.overall(outcomes)
    return result


def placidus_observations(case: dict, swetest: str, ephe: str, tol: float) -> list[dict]:
    """Archival reference only: Placidus fails here in swetest and the binding; whole sign computes."""
    req = case["request"]
    utc = datetime.fromisoformat(req["birth_datetime"]).astimezone(timezone.utc)
    jd = c.engine_jd(utc.isoformat().replace("+00:00", "Z"))
    lat, lon, cid = req["latitude"], req["longitude"], case["id"]
    out = []
    sw_p = swetest_pair(swetest, ephe, jd, lat, lon, profile.ARCHIVAL_HOUSE_LETTER)
    bind_p = binding_values(jd, lat, lon, ephe, profile.ARCHIVAL_HOUSE_LETTER)
    placidus = [p for p in sw_p["problems"] if c.PLACIDUS_FAILED in p]
    others = [p for p in sw_p["problems"] if c.PLACIDUS_FAILED not in p]
    if others:
        out.append(_check(cid, "placidus_failure_reproduced", BLOCKED, others))
    else:
        out.append(_check(cid, "placidus_failure_reproduced",
                          PASS if placidus and bind_p["lagna"] is None else FAIL,
                          {"swetest_placidus_failed": bool(placidus), "binding_raised": bind_p["lagna"] is None}))
    sw_w = swetest_pair(swetest, ephe, jd, lat, lon, profile.HOUSE_LETTER)
    bind_w = binding_values(jd, lat, lon, ephe, profile.HOUSE_LETTER)
    asc = sw_w["values"].get("lagna")
    if sw_w["problems"]:
        out.append(_check(cid, "whole_sign_ascendant_computes", BLOCKED, sw_w["problems"]))
    elif not inputs.is_number(asc) or bind_w["lagna"] is None or sw_w["house_system"] != profile.HOUSE_LETTER:
        out.append(_check(cid, "whole_sign_ascendant_computes", FAIL, "no whole-sign ascendant"))
    else:
        diff = float((Fraction(bind_w["lagna"]) - Fraction(asc) + 180) % 360 - 180)
        out.append(_check(cid, "whole_sign_ascendant_computes", PASS if abs(diff) <= tol else FAIL, diff))
    return out


def refusal_result(case: dict, expected: str, swetest: str, ephe: str, spec: dict, status: str, payload,
                   record: dict) -> dict:
    cid = case["id"]
    result = {"case": cid, "purpose": case["purpose"], "expect": "refuse", "expected_refusal": expected,
              "outcome": None, "reasons": [], "receipts": [], "checks": [], "self_consistency": [],
              "method_checks": [], "reference_observations": []}
    if status == "blocked":
        result.update(outcome=BLOCKED, reasons=[f"ENGINE_BLOCKED: {payload}"])
        return result
    got = payload if status == "refused" else "a chart"
    result["checks"] = [
        _check(cid, "engine_refusal_code", PASS if status == "refused" and payload == expected else FAIL, got),
        _check(cid, "refused_before_ephemeris_and_swiss",
               PASS if not record["ephemeris_checked"] and not record["swiss_calls"] else FAIL,
               {"ephemeris_checked": record["ephemeris_checked"], "swiss_calls": len(record["swiss_calls"])}),
    ]
    if cid in profile.PLACIDUS_OBSERVATION_CASES:
        result["reference_observations"] = placidus_observations(
            case, swetest, ephe, spec["tolerances_deg"]["binding_vs_swetest"]["value"])
    outcomes = [x["outcome"] for x in result["checks"] + result["reference_observations"]]
    result["outcome"] = c.overall(outcomes)
    if result["outcome"] != PASS:
        result["reasons"] = [f"{x['quantity']}: {x['detail']}" for x in result["checks"] + result["reference_observations"]
                             if x["outcome"] != PASS]
    return result


def run_current_case(case: dict, swetest: str, ephe: str, spec: dict) -> dict:
    expected = profile.CURRENT_CASES[case["id"]]
    status, payload, record = call_engine(case["request"], ephe)
    if expected == "chart":
        return chart_result(case, swetest, ephe, spec, status, payload, record)
    return refusal_result(case, expected, swetest, ephe, spec, status, payload, record)


def run_supplement_case(case: dict, swetest: str, ephe: str, spec: dict) -> dict:
    with historical_gate_override():
        status, payload, record = call_engine(case["request"], ephe)
    result = chart_result(case, swetest, ephe, spec, status, payload, record)
    # The gate must refuse the same request again once restored.
    after = call_engine(case["request"], ephe)[:2]
    result["gate_restored"] = after == ("refused", profile.CURRENT_CASES[case["id"]])
    if not result["gate_restored"]:
        result.update(outcome=FAIL, reasons=result["reasons"] + ["historical clock gate not restored"])
    return result


# ---------------------------------------------------------------- coverage

def coverage(results: list[dict], supplement: list[dict]) -> tuple[dict, list[str]]:
    errors = []
    if [r["case"] for r in results] != list(profile.CURRENT_CASES):
        errors.append("COVERAGE_CASE_SET")
    if [r["case"] for r in supplement] != list(profile.HISTORICAL_SUPPLEMENT):
        errors.append("COVERAGE_SUPPLEMENT_SET")
    for r in results + supplement:
        if r["outcome"] != PASS:
            continue
        if r["expect"] == "chart":
            keys = [x["quantity"] if x["kind"] not in ("binding_vs_swetest_deg", "engine_vs_swetest_deg")
                    else f"{x['kind']}:{x['quantity']}" for x in r["checks"]]
            if len(keys) != len(set(keys)) or set(keys) != inputs.CHART_QUANTITIES:
                errors.append(f"COVERAGE_CHART_QUANTITIES: {r['case']}")
            if len(r["self_consistency"]) != inputs.SELF_CHECKS_PER_CHART:
                errors.append(f"COVERAGE_SELF_CONSISTENCY: {r['case']}")
            if [x["quantity"] for x in r["method_checks"]] != list(HOUSE_METHOD_QUANTITIES):
                errors.append(f"COVERAGE_HOUSE_METHOD: {r['case']}")
        else:
            if [x["quantity"] for x in r["checks"]] != list(REFUSAL_QUANTITIES):
                errors.append(f"COVERAGE_REFUSAL_CHECKS: {r['case']}")
            observed = [x["quantity"] for x in r["reference_observations"]]
            if observed != (list(OBSERVATION_QUANTITIES) if r["case"] in profile.PLACIDUS_OBSERVATION_CASES else []):
                errors.append(f"COVERAGE_PLACIDUS_OBSERVATIONS: {r['case']}")
    charts = [r for r in results if r["expect"] == "chart"]
    refusals = [r for r in results if r["expect"] == "refuse"]
    passed = lambda rows: sum(x["outcome"] == PASS for x in rows)
    counts = {
        "cases": len(results), "chart_cases": len(charts), "refusal_cases": len(refusals),
        "case_outcomes": {o: sum(r["outcome"] == o for r in results) for o in (PASS, FAIL, BLOCKED, INDETERMINATE)},
        "comparison_checks": sum(len(r["checks"]) for r in charts),
        "comparison_checks_passed": sum(passed(r["checks"]) for r in charts),
        "self_consistency_checks": sum(len(r["self_consistency"]) for r in charts),
        "self_consistency_passed": sum(s["result"].endswith(PASS) for r in charts for s in r["self_consistency"]),
        "house_method_checks": sum(len(r["method_checks"]) for r in charts),
        "house_method_checks_passed": sum(passed(r["method_checks"]) for r in charts),
        "refusal_checks": sum(len(r["checks"]) for r in refusals),
        "refusal_checks_passed": sum(passed(r["checks"]) for r in refusals),
        "placidus_reference_observations": sum(len(r["reference_observations"]) for r in refusals),
        "placidus_reference_observations_passed": sum(passed(r["reference_observations"]) for r in refusals),
        "historical_supplement_cases": len(supplement),
        "historical_supplement_comparison_checks": sum(len(r["checks"]) for r in supplement),
        "historical_supplement_comparison_checks_passed": sum(passed(r["checks"]) for r in supplement),
        "historical_supplement_self_consistency_checks": sum(len(r["self_consistency"]) for r in supplement),
        "historical_supplement_house_method_checks": sum(len(r["method_checks"]) for r in supplement),
    }
    for key in ("cases", "chart_cases", "refusal_cases", "comparison_checks", "self_consistency_checks",
                "house_method_checks", "refusal_checks", "placidus_reference_observations",
                "historical_supplement_cases", "historical_supplement_comparison_checks",
                "historical_supplement_self_consistency_checks", "historical_supplement_house_method_checks"):
        if counts[key] != profile.COUNTS[key]:
            errors.append(f"COVERAGE_COUNT: {key}")
    return counts, errors


def reconcile(archival: dict, current: list[dict]) -> dict:
    """The archival run must diverge exactly where the overlay says, and every current chart keeps its 49 checks."""
    findings = []
    if archival["run_reasons"]:
        return {"outcome": BLOCKED, "findings": [f"archival run blocked: {r}" for r in archival["run_reasons"]],
                "per_chart": []}
    by_case = {r["case"]: r for r in archival["cases"]}
    failed = {cid: r["reasons"] for cid, r in by_case.items() if r["outcome"] == FAIL}
    if failed != {cid: [reason] for cid, reason in profile.ARCHIVAL_DIVERGENCE.items()}:
        findings.append("archival FAIL set differs from the recorded divergence")
    others = [cid for cid, r in by_case.items() if cid not in profile.ARCHIVAL_DIVERGENCE and r["outcome"] != PASS]
    findings += [f"archival case {cid} is {by_case[cid]['outcome']}" for cid in others]
    if archival["verdict"] != c.VERDICT[FAIL]:
        findings.append(f"archival verdict is {archival['verdict']}, expected the recorded FAIL")
    per_chart = []
    for r in current:
        if r["expect"] != "chart":
            continue
        old = by_case.get(r["case"], {"checks": [], "outcome": None})
        key = lambda x: (x["kind"], x["quantity"])
        same = sorted(map(key, old["checks"])) == sorted(map(key, r["checks"]))
        values = {key(x): x["value"] for x in old["checks"]} == {key(x): x["value"] for x in r["checks"]}
        row = {"case": r["case"], "archival_checks": len(old["checks"]), "current_checks": len(r["checks"]),
               "archival_outcome": old["outcome"], "current_outcome": r["outcome"],
               "same_quantities": same, "same_engine_and_binding_values": values}
        per_chart.append(row)
        if not (same and len(r["checks"]) == inputs.CHECKS_PER_CHART and old["outcome"] == r["outcome"] == PASS):
            findings.append(f"chart {r['case']} lost or changed checks between profiles")
    if len(per_chart) != profile.CHART_CASES:
        findings.append("current chart set incomplete")
    if any(r["case"] in profile.ARCHIVAL_DIVERGENCE for r in per_chart):
        findings.append("a divergent case is still a chart")
    blocked = archival["verdict"] == c.VERDICT[BLOCKED]
    return {"outcome": BLOCKED if blocked else (FAIL if findings else PASS), "findings": findings,
            "per_chart": per_chart}


# ---------------------------------------------------------------- run and report

def run_all(swetest: str | None, ephe: str | None, receipt: str | None, *, env: dict | None = None,
            profile_path: Path = profile.PROFILE_PATH, clock=lambda: datetime.now(timezone.utc)) -> dict:
    started = clock().strftime("%Y-%m-%dT%H:%M:%SZ")
    spec, cases, input_record, reasons = inputs.load_inputs(c.HERE / "spec.json", c.HERE / "cases.json")
    prof, profile_record, profile_errors = profile.load_profile(profile_path)
    input_record["profile"] = profile_record
    env = env if env is not None else c.capture_environment(swetest, receipt, ephe)
    reasons = reasons + profile_errors + c.run_reasons(env, {"required_versions": inputs.REQUIRED_VERSIONS})
    results, supplement, archival, reconciliation = [], [], None, None
    if not reasons:
        results = [run_current_case(case, swetest, ephe, spec) for case in cases]
        by_id = {case["id"]: case for case in cases}
        supplement = [run_supplement_case(by_id[cid], swetest, ephe, spec) for cid in profile.HISTORICAL_SUPPLEMENT]
        archival = c.run_all(swetest, ephe, receipt, env=env, clock=clock)
        reconciliation = reconcile(archival, results)
    counts, coverage_errors = coverage(results, supplement)
    if reasons:
        coverage_errors = []
        verdicts = {"current": BLOCKED, "historical_supplement": BLOCKED, "reconciliation": BLOCKED}
    else:
        verdicts = {"current": c.overall([r["outcome"] for r in results]),
                    "historical_supplement": c.overall([r["outcome"] for r in supplement]),
                    "reconciliation": reconciliation["outcome"]}
        if coverage_errors and verdicts["current"] == PASS:
            verdicts["current"] = BLOCKED
    verdict = c.overall(list(verdicts.values()))
    return {"report_schema": REPORT_SCHEMA,
            "claim_boundary": prof["claim_boundary"] if prof else inputs.CLAIM_MARKER,
            "profile": {"id": profile.PROFILE_ID, "version": profile.PROFILE_VERSION,
                        "house_letter": profile.HOUSE_LETTER, "sha256": profile_record["sha256"]},
            "started_utc": started, "finished_utc": clock().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "environment": env, "inputs": input_record, "run_reasons": reasons,
            "coverage": counts, "coverage_errors": coverage_errors,
            "spec_tolerances_deg": spec["tolerances_deg"] if spec else None,
            "changes": prof["cases"] if prof else None,
            "cases": results, "historical_supplement": supplement,
            "historical_supplement_label": prof["historical_numerics_supplement"]["label"] if prof else None,
            "archival": archival, "reconciliation": reconciliation,
            "verdicts": {k: c.VERDICT[v] for k, v in verdicts.items()},
            "verdict": c.VERDICT[verdict], "exit_code": c.EXIT[verdict]}


def to_json(report: dict) -> str:
    return json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False, default=repr) + "\n"


def _cell(value):
    return repr(value) if isinstance(value, float) else value


def to_csv(report: dict) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["profile", "case", "kind", "quantity", "value", "reference", "diff", "tolerance", "outcome"])
    sections = [("current", report["cases"]), ("historical_supplement_TEST_ONLY", report["historical_supplement"]),
                ("archival", (report["archival"] or {}).get("cases", []))]
    for name, cases in sections:
        for case in cases:
            for x in case["checks"] + case.get("method_checks", []) + case.get("reference_observations", []):
                writer.writerow([name, x["case"], x["kind"], x["quantity"],
                                 _cell(x.get("value", json.dumps(x.get("detail"), default=repr))),
                                 _cell(x.get("reference", "")), "" if x.get("diff") is None else repr(x["diff"]),
                                 "" if x.get("tolerance") is None else repr(x["tolerance"]), x["outcome"]])
            for s in case["self_consistency"]:
                writer.writerow([name, s["case"], "self_consistency", s["check"], "", "",
                                 "" if s["diff_deg"] is None else repr(s["diff_deg"]),
                                 "" if s["limit_deg"] is None else repr(s["limit_deg"]), s["result"]])
    return out.getvalue()


def _case_rows(cases: list[dict]) -> list[str]:
    rows = ["| Case | Expect | Outcome | Comparison (pass/total) | Self-consistency | House method | Refusal / observations | Max engine-vs-swetest (deg) | Notes |",
            "|---|---|---|---|---|---|---|---|---|"]
    for r in cases:
        diffs = [abs(x["diff"]) for x in r["checks"] if x["kind"] == "engine_vs_swetest_deg" and x.get("diff") is not None]
        charts = r["expect"] == "chart"
        cmp_ = f"{sum(x['outcome'] == PASS for x in r['checks'])}/{len(r['checks'])}" if charts else ""
        self_ = f"{sum(s['result'].endswith(PASS) for s in r['self_consistency'])}/{len(r['self_consistency'])}" if charts else ""
        meth = f"{sum(x['outcome'] == PASS for x in r.get('method_checks', []))}/{len(r.get('method_checks', []))}" if charts else ""
        obs = r.get("reference_observations", [])
        ref = "" if charts else (f"{r['expected_refusal']}: {sum(x['outcome'] == PASS for x in r['checks'])}/{len(r['checks'])}"
                                 + (f"; Placidus ref {sum(x['outcome'] == PASS for x in obs)}/{len(obs)}" if obs else ""))
        rows.append(f"| {r['case']} | {r['expect']} | {r['outcome']} | {cmp_} | {self_} | {meth} | {ref} | "
                    f"{max(diffs) if diffs else ''} | {'; '.join(r['reasons'])} |")
    return rows


def to_markdown(report: dict) -> str:
    env = report["environment"]
    lines = [f"# {report['verdict']} (exit {report['exit_code']}): KUN-03 reconciliation, profile "
             f"{report['profile']['id']} v{report['profile']['version']}", "",
             f"_{report['claim_boundary']}_", "",
             "| Part | Verdict |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in report["verdicts"].items()]
    lines += ["", f"- Commit `{env['git']['commit']}` dirty={env['git']['dirty']}",
              f"- Python {env['python']} ({env['platform']}); pyswisseph {env['binding']['pyswisseph']}; "
              f"Swiss library {env['binding']['swiss_library']}",
              f"- swetest sha256 `{env['swetest']['sha256']}`; source {env['swetest']['source'] or 'not approved'}; receipt "
              f"{json.dumps(env['swetest']['receipt'], sort_keys=True) if env['swetest']['receipt'] else 'none'}",
              f"- Ephemeris verified={env['ephemeris']['verified']} {env['ephemeris']['error_code'] or ''}".rstrip()]
    lines += [f"  - `{n}` `{h}`" for n, h in sorted(env["ephemeris"]["files"].items())]
    lines += [f"- Input `{n}` sha256 `{r['sha256']}` (pinned `{r.get('frozen_sha256')}`)" for n, r in sorted(report["inputs"].items())]
    lines += ["", "## Run-level blocking reasons", ""] + ([f"- {r}" for r in report["run_reasons"]] or ["- none"])
    lines += ["", "## Current profile coverage", ""] + [f"- {k}: {v}" for k, v in report["coverage"].items()]
    lines += [f"- COVERAGE ERROR: {e}" for e in report["coverage_errors"]]
    lines += ["", "## Current profile cases (whole-sign reference)", ""] + _case_rows(report["cases"])
    lines += ["", "## Historical-numerics supplement", "", f"**{report['historical_supplement_label']}**", ""]
    lines += _case_rows(report["historical_supplement"])
    lines += [f"- {r['case']}: gate restored and refusing again = {r.get('gate_restored')}" for r in report["historical_supplement"]]
    archival = report["archival"]
    if archival:
        lines += ["", f"## Archival PR #18 profile, unchanged runner: {archival['verdict']}", "",
                  "| Case | Expect | Outcome | Checks (pass/total) | Notes |", "|---|---|---|---|---|"]
        for r in archival["cases"]:
            lines.append(f"| {r['case']} | {r['expect']} | {r['outcome']} | "
                         f"{sum(x['outcome'] == PASS for x in r['checks'])}/{len(r['checks'])} | {'; '.join(r['reasons'])} |")
        lines += ["", "Archival coverage: " + ", ".join(f"{k}={v}" for k, v in archival["coverage"].items())]
    rec = report["reconciliation"]
    if rec:
        lines += ["", f"## Reconciliation: {rec['outcome']}", ""] + ([f"- {f}" for f in rec["findings"]] or ["- no findings"])
        lines += ["", "| Chart | Archival checks | Current checks | Same quantities | Same values | Archival | Current |",
                  "|---|---|---|---|---|---|---|"]
        lines += [f"| {p['case']} | {p['archival_checks']} | {p['current_checks']} | {p['same_quantities']} | "
                  f"{p['same_engine_and_binding_values']} | {p['archival_outcome']} | {p['current_outcome']} |"
                  for p in rec["per_chart"]]
    if report["changes"]:
        lines += ["", "## Differences from the archival profile", "",
                  "| Case | Archival | Current | Source milestone | Reason |", "|---|---|---|---|---|"]
        for entry in report["changes"]:
            ch = entry["change"]
            if ch:
                lines.append(f"| {entry['id']} | {ch['archival_expect']} {ch['archival_expected_refusal'] or ''} | "
                             f"{entry['expect']} {entry['expected_refusal'] or ''} | {ch['source_milestone']} | {ch['reason']} |")
    return "\n".join(lines) + "\n"


def write_reports(report: dict, directory: Path) -> list[Path]:
    commit = (report["environment"]["git"]["commit"] or "nogit")[:12]
    stamp = report["started_utc"].replace("-", "").replace(":", "")
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / f"swiss-reconciliation-{commit}-{stamp}"
    paths = [base.with_suffix(".json"), base.with_suffix(".csv"), base.with_suffix(".md")]
    for path, text in zip(paths, (to_json(report), to_csv(report), to_markdown(report))):
        path.write_text(text, encoding="utf-8")
    return paths
