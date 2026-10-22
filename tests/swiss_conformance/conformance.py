"""Swiss-conformance runner: Sabpuja's Python integration vs the official swetest CLI.

This is Swiss-on-Swiss conformance. It checks input conversion, flags and
integration against the same library and data; it is never independent
astronomical validation. Verdicts: SWISS-CONFORMANCE PASS / FAIL / BLOCKED.
"""
from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
from importlib import metadata
from pathlib import Path
import csv
import io
import json
import os
import platform
import subprocess

from . import inputs, oracle, swetest_cli

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
PASS, FAIL, BLOCKED, INDETERMINATE = "PASS", "FAIL", "BLOCKED", "BOUNDARY-INDETERMINATE"
VERDICT = {PASS: "SWISS-CONFORMANCE PASS", FAIL: "SWISS-CONFORMANCE FAIL", BLOCKED: "SWISS-CONFORMANCE BLOCKED"}
EXIT = {PASS: 0, FAIL: 1, BLOCKED: 2}
PLACIDUS_FAILED = "House method Placidus failed"


load_json = inputs.load_json


def overall(outcomes: list[str]) -> str:
    """Any FAIL is FAIL; anything not judged (BLOCKED, BOUNDARY-INDETERMINATE) or nothing at all is BLOCKED."""
    if FAIL in outcomes:
        return FAIL
    if not outcomes or BLOCKED in outcomes or INDETERMINATE in outcomes:
        return BLOCKED
    return PASS


# ---------------------------------------------------------------- provenance

def git_state(repo: Path) -> dict:
    try:
        run = lambda *a: subprocess.run(["git", "-C", str(repo), *a], capture_output=True, text=True,
                                        check=True, timeout=30).stdout
        return {"commit": run("rev-parse", "HEAD").strip(), "dirty": bool(run("status", "--porcelain").strip())}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "dirty": None}


def binding_state() -> dict:
    try:
        import swisseph
        library = swisseph.version
    except ImportError:
        library = None
    try:
        dist = metadata.version("pyswisseph")
    except metadata.PackageNotFoundError:
        dist = None
    return {"pyswisseph": dist, "swiss_library": library}


def ephemeris_state(ephe: str | None) -> dict:
    from sabpuja_kundali.ephemeris import EphemerisDataError, load_manifest, verify_ephemeris_dir
    manifest = load_manifest()
    state = {"verified": False, "error_code": None, "manifest_version": manifest["manifest_version"],
             "source_commit": manifest["source"]["commit"], "files": {}}
    try:
        verify_ephemeris_dir(ephe)
    except EphemerisDataError as exc:
        state["error_code"] = exc.code
        return state
    state["verified"] = True
    state["files"] = {e["name"]: e["sha256"] for e in manifest["files"] if e.get("required") is True}
    return state


def swetest_state(swetest: str | None, receipt_path: str | None) -> dict:
    state = {"present": False, "sha256": None, "receipt": None, "source": None, "receipt_errors": [],
             "receipt_nature": "builder testimony plus binary SHA-256; not proof of reproducible compilation"}
    if not swetest or not Path(swetest).is_file() or not os.access(swetest, os.X_OK):
        return state
    state["present"] = True
    state["sha256"] = swetest_cli.sha256_file(Path(swetest))
    if not receipt_path or not Path(receipt_path).is_file():
        state["receipt_errors"].append("SWETEST_BUILD_RECEIPT_MISSING")
        return state
    try:
        receipt = load_json(Path(receipt_path))
    except inputs.InputError:
        state["receipt_errors"].append("SWETEST_BUILD_RECEIPT_INVALID")
        return state
    state["source"], state["receipt_errors"] = inputs.validate_receipt(receipt, state["sha256"])
    if state["receipt_errors"] != ["SWETEST_BUILD_RECEIPT_INVALID"]:
        state["receipt"] = {k: receipt[k] for k in sorted(inputs.RECEIPT_KEYS)}
    return state


def run_reasons(env: dict, spec: dict) -> list[str]:
    reasons = []
    if env["git"]["commit"] is None:
        reasons.append("GIT_UNAVAILABLE")
    elif env["git"]["dirty"]:
        reasons.append("DIRTY_TREE")
    required = spec["required_versions"]
    if env["binding"]["pyswisseph"] != required["pyswisseph"] or env["binding"]["swiss_library"] != required["swiss_library"]:
        reasons.append("BINDING_VERSION_MISMATCH")
    if not env["ephemeris"]["verified"]:
        reasons.append(f"EPHEMERIS_UNVERIFIED: {env['ephemeris']['error_code']}")
    if os.environ.get("SE_EPHE_PATH"):
        reasons.append("SE_EPHE_PATH_SET")
    if not env["swetest"]["present"]:
        reasons.append("SWETEST_MISSING")
    reasons += env["swetest"]["receipt_errors"]
    return reasons


# ---------------------------------------------------------------- python side

def engine_jd(utc_text: str) -> float:
    """The engine's own Julian Day for its reported UTC instant (same swe.julday call shape)."""
    import swisseph as swe
    utc = datetime.fromisoformat(utc_text.replace("Z", "+00:00"))
    return swe.julday(utc.year, utc.month, utc.day,
                      utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1_000_000) / 3600)


def binding_values(jd: float, lat: float, lon: float, ephe: str) -> dict:
    """Unrounded values from the Python binding with exactly the engine's flags.

    'lagna' is None when Placidus is undefined (the binding raises).
    """
    import swisseph as swe
    from sabpuja_kundali.ephemeris import verify_ephemeris_dir
    folder = verify_ephemeris_dir(ephe)
    bodies = {"sun": swe.SUN, "moon": swe.MOON, "mercury": swe.MERCURY, "venus": swe.VENUS, "mars": swe.MARS,
              "jupiter": swe.JUPITER, "saturn": swe.SATURN, "rahu_mean": swe.MEAN_NODE}
    swe.set_ephe_path(str(folder))
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    out = {}
    for name, body in bodies.items():
        pos, flags = swe.calc_ut(jd, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        if not flags & swe.FLG_SWIEPH:
            raise RuntimeError("binding fell back from Swiss files")
        out[name] = float(pos[0])
    try:
        out["lagna"] = float(swe.houses_ex(jd, lat, lon, b"P", swe.FLG_SIDEREAL)[1][0])
    except swe.Error:
        out["lagna"] = None
    return out


def call_engine(request: dict, ephe: str):
    """Return ('chart', output) or ('refused', code). Messages are never recorded."""
    from sabpuja_kundali.engine import ChartComputationError, calculate
    from sabpuja_kundali.ephemeris import EphemerisDataError
    try:
        return "chart", calculate(dict(request), ephe_path=ephe)
    except ChartComputationError as exc:
        return "refused", exc.code
    except EphemerisDataError as exc:
        return "blocked", exc.code
    except ValueError:
        return "refused", "INPUT_REFUSED"
    except Exception as exc:  # noqa: BLE001 - recorded as a type only
        return "blocked", f"ENGINE_ERROR_{type(exc).__name__}"


# ---------------------------------------------------------------- comparison

def numeric(case_id: str, kind: str, quantity: str, value, reference, tol: float) -> dict:
    record = {"case": case_id, "kind": kind, "quantity": quantity, "value": value, "reference": reference,
              "diff": None, "tolerance": tol, "outcome": FAIL}
    if not inputs.valid_tolerance(tol):
        record.update(value=repr(value), reference=repr(reference), tolerance=repr(tol), outcome=BLOCKED)
        return record
    if not (inputs.is_number(value) and inputs.is_number(reference)):
        # Keep the report valid strict JSON: unusable values are recorded by repr only.
        record.update(value=None if value is None else repr(value),
                      reference=None if reference is None else repr(reference), outcome=BLOCKED)
        return record
    if kind.endswith("_deg"):
        diff = float((Fraction(value) - Fraction(reference) + 180) % 360 - 180)
    else:
        diff = float(Fraction(value) - Fraction(reference))
    record["diff"] = diff
    record["outcome"] = PASS if abs(diff) <= tol else FAIL
    return record


def category(case_id: str, quantity: str, engine_value, classify, sw_args: tuple, bind_args: tuple,
             near: bool) -> dict:
    """Engine category vs the oracle on swetest values; resolved only if both raw sources agree."""
    sw, bind = classify(*sw_args), classify(*bind_args)
    record = {"case": case_id, "kind": "category", "quantity": quantity, "value": engine_value,
              "reference": sw, "outcome": None}
    if sw != bind:
        record["outcome"] = INDETERMINATE if near else FAIL
    else:
        record["outcome"] = PASS if engine_value == sw else FAIL
    return record


def compare_chart(case: dict, output: dict, sw: dict, bind: dict, sw_ut: list[float], jd: float, tol: dict) -> tuple[list, list]:
    cid = case["id"]
    checks, self_checks = [], []
    expected_utc = case["expected_utc"]
    checks.append({"case": cid, "kind": "time", "quantity": "utc", "value": output["birth"]["utc"],
                   "reference": expected_utc, "outcome": PASS if output["birth"]["utc"] == expected_utc else FAIL})
    utc = datetime.fromisoformat(expected_utc.replace("Z", "+00:00"))
    independent = oracle.gregorian_jd(utc.year, utc.month, utc.day, utc.hour, utc.minute, utc.second, utc.microsecond)
    checks.append(numeric(cid, "jd_day", "jd_vs_independent_formula", jd, float(independent), tol["independent_jd_day"]))
    for n, ut in enumerate(sw_ut):
        checks.append(numeric(cid, "jd_day", f"jd_vs_swetest_ut_line_{n + 1}", jd, ut, tol["swetest_ut_jd_day"]))
    names = [*(b for b in bind if b != "lagna"), "lagna"]
    for body in names:
        engine_value = (output["lagna"] if body == "lagna" else output["planets"][body])["longitude_deg"]
        checks.append(numeric(cid, "binding_vs_swetest_deg", body, bind[body], sw.get(body), tol["binding_vs_swetest"]))
        checks.append(numeric(cid, "engine_vs_swetest_deg", body, engine_value, sw.get(body), tol["engine_vs_swetest"]))
    if any(sw.get(b) is None for b in names):
        return checks, self_checks
    near_tol = Fraction(tol["binding_vs_swetest"])
    lagna_near = oracle.boundary_distance(sw["lagna"], oracle.RASHI_SPAN) <= near_tol
    for body in names:
        engine_body = output["lagna"] if body == "lagna" else output["planets"][body]
        near = oracle.boundary_distance(sw[body]) <= near_tol
        checks.append(category(cid, f"{body}.rashi", engine_body["rashi"], oracle.rashi, (sw[body],), (bind[body],), near))
        checks.append(category(cid, f"{body}.navamsa_rashi", engine_body["navamsa_rashi"], oracle.navamsa,
                               (sw[body],), (bind[body],), near))
        if body != "lagna":
            checks.append(category(cid, f"{body}.whole_sign_house", engine_body["whole_sign_house"],
                                   oracle.whole_sign_house, (sw[body], sw["lagna"]), (bind[body], bind["lagna"]),
                                   near or lagna_near))
    moon = output["moon_nakshatra"]
    checks.append(category(cid, "moon.nakshatra_pada", (moon["name"], moon["pada"]), oracle.nakshatra,
                           (sw["moon"],), (bind["moon"],), oracle.boundary_distance(sw["moon"]) <= near_tol))
    # Ketu: self-consistency against the exact unrounded Rahu (same library value as the engine).
    ketu_exact = Fraction(bind["rahu_mean"]) + 180
    ketu = output["planets"]["ketu_mean"]
    rahu_display = output["planets"]["rahu_mean"]["longitude_deg"]
    diff = float((Fraction(ketu["longitude_deg"]) - (Fraction(rahu_display) + 180) + 180) % 360 - 180)
    self_checks.append({"case": cid, "check": "ketu display = rahu display + 180", "diff_deg": diff,
                        "limit_deg": tol["ketu_identity_deg"],
                        "result": "SELF-CONSISTENCY " + (PASS if abs(diff) <= tol["ketu_identity_deg"] else FAIL)})
    expected = (oracle.rashi(ketu_exact), oracle.navamsa(ketu_exact), oracle.whole_sign_house(ketu_exact, bind["lagna"]))
    got = (ketu["rashi"], ketu["navamsa_rashi"], ketu["whole_sign_house"])
    self_checks.append({"case": cid, "check": "ketu categories from exact Fraction(rahu) + 180", "diff_deg": None,
                        "limit_deg": None, "result": "SELF-CONSISTENCY " + (PASS if got == expected else FAIL)})
    return checks, self_checks


def swetest_pair(swetest: str, ephe: str, jd: float, lat: float, lon: float) -> tuple[dict, list[dict], list[str], list[float]]:
    """Run planets and houses; return (values by Sabpuja body name, receipts, problems)."""
    spec_names = {"Sun": "sun", "Moon": "moon", "Mercury": "mercury", "Venus": "venus", "Mars": "mars",
                  "Jupiter": "jupiter", "Saturn": "saturn", "mean Node": "rahu_mean", "Ascendant": "lagna"}
    values, receipts, problems, uts = {}, [], [], []
    for argv in (swetest_cli.planet_argv(swetest, ephe, jd), swetest_cli.house_argv(swetest, ephe, jd, lat, lon)):
        try:
            result = swetest_cli.run(argv, ephe)
        except swetest_cli.SwetestOutputError as exc:
            problems.append(f"SWETEST_OUTPUT_MALFORMED: {exc}")
            receipts.append({"argv": [swetest_cli.redact(a, swetest, ephe) for a in argv], "error": str(exc)})
            continue
        except (OSError, subprocess.SubprocessError) as exc:
            problems.append(f"SWETEST_NOT_RUN: {type(exc).__name__}")
            continue
        receipts.append({"argv": result.argv, "exit_code": result.exit_code, "stdout": result.stdout,
                         "stderr": result.stderr, "version": result.version, "ut_jd": result.ut_jd,
                         "ayanamsa_name": result.ayanamsa_name, "warnings": result.warnings})
        if result.exit_code != 0:
            problems.append(f"SWETEST_EXIT_{result.exit_code}")
            continue
        uts.append(result.ut_jd)
        problems += [f"SWETEST_WARNING: {w}" for w in result.warnings]
        for name, value in result.values.items():
            if name in spec_names:
                values[spec_names[name]] = value
    return values, receipts, problems, uts


def run_case(case: dict, swetest: str, ephe: str, spec: dict) -> dict:
    tol = {k: v["value"] for k, v in spec["tolerances_deg"].items()}
    cid = case["id"]
    result = {"case": cid, "purpose": case["purpose"], "expect": case["expect"], "outcome": None,
              "reasons": [], "receipts": [], "checks": [], "self_consistency": []}
    status, payload = call_engine(case["request"], ephe)
    if status == "blocked":
        result.update(outcome=BLOCKED, reasons=[f"ENGINE_BLOCKED: {payload}"])
        return result
    if case["expect"] == "refuse":
        if status != "refused" or payload != case["expected_refusal"]:
            result.update(outcome=FAIL, reasons=[f"expected refusal {case['expected_refusal']}, engine gave "
                                                 f"{payload if status == 'refused' else 'a chart'}"])
            return result
        if payload == "INPUT_REFUSED":
            result.update(outcome=PASS, reasons=["engine refused invalid or out-of-window input (no swetest run needed)"])
            return result
        # Polar: swetest must also report that Placidus failed; the binding must raise too.
        utc = datetime.fromisoformat(case["request"]["birth_datetime"]).astimezone(timezone.utc)
        jd = engine_jd(utc.isoformat().replace("+00:00", "Z"))
        req = case["request"]
        _, receipts, problems, _ = swetest_pair(swetest, ephe, jd, req["latitude"], req["longitude"])
        result["receipts"] = receipts
        placidus = [p for p in problems if PLACIDUS_FAILED in p]
        others = [p for p in problems if PLACIDUS_FAILED not in p]
        bind = binding_values(jd, req["latitude"], req["longitude"], ephe)
        if others:
            result.update(outcome=BLOCKED, reasons=others)
        elif placidus and bind["lagna"] is None:
            result.update(outcome=PASS, reasons=["engine, binding and swetest all report Placidus undefined"])
        else:
            result.update(outcome=FAIL, reasons=["swetest or binding produced a Placidus ascendant the engine refused"])
        return result
    if status != "chart":
        result.update(outcome=FAIL, reasons=[f"engine refused ({payload}) a case expected to chart"])
        return result
    jd = engine_jd(payload["birth"]["utc"])
    req = case["request"]
    sw, receipts, problems, uts = swetest_pair(swetest, ephe, jd, req["latitude"], req["longitude"])
    result["receipts"] = receipts
    if problems:
        result.update(outcome=BLOCKED, reasons=problems)
        return result
    for receipt in receipts:
        if receipt["version"] != spec["required_versions"]["swiss_library"]:
            result.update(outcome=BLOCKED, reasons=["SWETEST_VERSION_MISMATCH: method-incomparable"])
            return result
        if receipt["ayanamsa_name"] != "Lahiri":
            result.update(outcome=FAIL, reasons=["swetest ayanamsa is not Lahiri"])
            return result
    method = payload.get("method", {})
    if (method.get("ayanamsa"), method.get("nodes"), method.get("houses")) != ("Lahiri", "mean", "whole_sign"):
        result.update(outcome=FAIL, reasons=["engine method block contradicts Lahiri / mean node / whole sign"])
        return result
    bind = binding_values(jd, req["latitude"], req["longitude"], ephe)
    checks, self_checks = compare_chart(case, payload, sw, bind, uts, jd, tol)
    result["checks"], result["self_consistency"] = checks, self_checks
    outcomes = [c["outcome"] for c in checks]
    outcomes += [FAIL for s in self_checks if s["result"].endswith(FAIL)]
    result["outcome"] = overall(outcomes)
    return result


# ---------------------------------------------------------------- run and report

def capture_environment(swetest: str | None, receipt: str | None, ephe: str | None) -> dict:
    return {"python": platform.python_version(), "platform": f"{platform.system()}-{platform.machine()}",
            "git": git_state(REPO_ROOT), "binding": binding_state(), "ephemeris": ephemeris_state(ephe),
            "swetest": swetest_state(swetest, receipt)}


def coverage(results: list[dict]) -> tuple[dict, list[str]]:
    """Counts for the report, and BLOCKED reasons if the frozen coverage was not delivered."""
    errors = []
    ids = [r["case"] for r in results]
    if ids != list(inputs.CASES):
        errors.append("COVERAGE_CASE_SET")
    for r in results:
        if inputs.CASES.get(r["case"]) != "chart" or r["outcome"] != PASS:
            continue
        keys = [c["quantity"] if c["kind"] not in ("binding_vs_swetest_deg", "engine_vs_swetest_deg")
                else f"{c['kind']}:{c['quantity']}" for c in r["checks"]]
        if len(keys) != len(set(keys)) or set(keys) != inputs.CHART_QUANTITIES:
            errors.append(f"COVERAGE_CHART_QUANTITIES: {r['case']}")
        if len(r["self_consistency"]) != inputs.SELF_CHECKS_PER_CHART:
            errors.append(f"COVERAGE_SELF_CONSISTENCY: {r['case']}")
    counts = {
        "cases_expected": len(inputs.CASES), "cases_run": len(results),
        "chart_cases_expected": inputs.CHART_CASES,
        "refusal_cases_expected": len(inputs.CASES) - inputs.CHART_CASES,
        "case_outcomes": {o: sum(r["outcome"] == o for r in results) for o in (PASS, FAIL, BLOCKED, INDETERMINATE)},
        "comparison_checks_expected": inputs.CHART_CASES * inputs.CHECKS_PER_CHART,
        "comparison_checks_run": sum(len(r["checks"]) for r in results),
        "comparison_checks_passed": sum(c["outcome"] == PASS for r in results for c in r["checks"]),
        "self_consistency_expected": inputs.CHART_CASES * inputs.SELF_CHECKS_PER_CHART,
        "self_consistency_run": sum(len(r["self_consistency"]) for r in results),
        "self_consistency_passed": sum(s["result"].endswith(PASS) for r in results for s in r["self_consistency"]),
    }
    if not errors and counts["comparison_checks_run"] != counts["comparison_checks_expected"]:
        errors.append("COVERAGE_CHECK_COUNT")
    return counts, errors


def run_all(swetest: str | None, ephe: str | None, receipt: str | None, *, cases_path: Path = HERE / "cases.json",
            spec_path: Path = HERE / "spec.json", env: dict | None = None, clock=lambda: datetime.now(timezone.utc)) -> dict:
    started = clock().strftime("%Y-%m-%dT%H:%M:%SZ")
    spec, cases, input_record, reasons = inputs.load_inputs(spec_path, cases_path)
    env = env if env is not None else capture_environment(swetest, receipt, ephe)
    reasons = reasons + run_reasons(env, {"required_versions": inputs.REQUIRED_VERSIONS})
    results = []
    if not reasons:
        results = [run_case(case, swetest, ephe, spec) for case in cases]
    counts, coverage_errors = coverage(results)
    if reasons:
        coverage_errors = []  # nothing ran; the run-level reasons already block
    verdict = BLOCKED if reasons else overall([r["outcome"] for r in results])
    if verdict == PASS and coverage_errors:
        verdict = BLOCKED
    return {"report_schema": "sabpuja-swiss-conformance-report/2",
            "claim_boundary": spec["claim_boundary"] if spec else inputs.CLAIM_MARKER,
            "started_utc": started, "finished_utc": clock().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "environment": env, "inputs": input_record, "run_reasons": reasons,
            "coverage": counts, "coverage_errors": coverage_errors,
            "spec_tolerances_deg": spec["tolerances_deg"] if spec else None,
            "cases": results, "verdict": VERDICT[verdict], "exit_code": EXIT[verdict]}


def to_json(report: dict) -> str:
    return json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def to_csv(report: dict) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["case", "kind", "quantity", "value", "reference", "diff", "tolerance", "outcome"])
    for case in report["cases"]:
        for c in case["checks"]:
            writer.writerow([c["case"], c["kind"], c["quantity"],
                             repr(c["value"]) if isinstance(c["value"], float) else c["value"],
                             repr(c["reference"]) if isinstance(c["reference"], float) else c["reference"],
                             "" if c.get("diff") is None else repr(c["diff"]),
                             "" if c.get("tolerance") is None else repr(c["tolerance"]), c["outcome"]])
    return out.getvalue()


def to_markdown(report: dict) -> str:
    env = report["environment"]
    lines = [f"# {report['verdict']} (exit {report['exit_code']})", "",
             f"_{report['claim_boundary']}_", "",
             f"- Commit `{env['git']['commit']}` dirty={env['git']['dirty']}",
             f"- Python {env['python']} ({env['platform']}); pyswisseph {env['binding']['pyswisseph']}; "
             f"Swiss library {env['binding']['swiss_library']}",
             f"- swetest sha256 `{env['swetest']['sha256']}`; receipt "
             f"{json.dumps(env['swetest']['receipt'], sort_keys=True) if env['swetest']['receipt'] else 'none'}",
             f"- swetest source: {env['swetest']['source'] or 'not approved'} "
             f"(receipt = {env['swetest']['receipt_nature']})",
             f"- Ephemeris verified={env['ephemeris']['verified']} {env['ephemeris']['error_code'] or ''}".rstrip()]
    lines += [f"  - `{n}` `{h}`" for n, h in sorted(env["ephemeris"]["files"].items())]
    lines += [f"- Input `{n}` sha256 `{r['sha256']}` ({r['bytes']} bytes)" for n, r in sorted(report["inputs"].items())]
    lines += ["", "## Run-level blocking reasons", ""] + ([f"- {r}" for r in report["run_reasons"]] or ["- none"])
    lines += ["", "## Coverage", ""] + [f"- {k}: {v}" for k, v in report["coverage"].items()]
    lines += [f"- COVERAGE ERROR: {e}" for e in report["coverage_errors"]]
    lines += ["", "## Cases", "", "| Case | Expect | Outcome | Checks (pass/total) | Max engine-vs-swetest diff (deg) | Notes |",
              "|---|---|---|---|---|---|"]
    for case in report["cases"]:
        engine_diffs = [abs(c["diff"]) for c in case["checks"] if c["kind"] == "engine_vs_swetest_deg" and c["diff"] is not None]
        passed = sum(1 for c in case["checks"] if c["outcome"] == PASS)
        lines.append(f"| {case['case']} | {case['expect']} | {case['outcome']} | {passed}/{len(case['checks'])} | "
                     f"{max(engine_diffs) if engine_diffs else ''} | {'; '.join(case['reasons'])} |")
    selfs = [s for case in report["cases"] for s in case["self_consistency"]]
    lines += ["", f"Self-consistency (not counted as conformance): {sum(s['result'].endswith(PASS) for s in selfs)}"
              f"/{len(selfs)} PASS", ""]
    return "\n".join(lines)


def write_reports(report: dict, directory: Path) -> list[Path]:
    commit = (report["environment"]["git"]["commit"] or "nogit")[:12]
    stamp = report["started_utc"].replace("-", "").replace(":", "")
    directory.mkdir(parents=True, exist_ok=True)
    base = directory / f"swiss-conformance-{commit}-{stamp}"
    paths = [base.with_suffix(".json"), base.with_suffix(".csv"), base.with_suffix(".md")]
    for path, text in zip(paths, (to_json(report), to_csv(report), to_markdown(report))):
        path.write_text(text, encoding="utf-8")
    return paths
