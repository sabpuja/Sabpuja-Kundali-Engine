"""KUN-03 current profile: fail-closed overlay, refusal codes and precedence, whole-sign reference.

The overlay and engine-refusal tests need no Swiss data or swetest. Tests that
compute charts need SABPUJA_TEST_EPHE_PATH (unset skips); the swetest class is
skipped only when SABPUJA_TEST_SWETEST is unset and errors if it is set but the
binary, receipt or data are not valid. Swiss-on-Swiss conformance only.
"""
from pathlib import Path
from unittest import mock
import json
import os
import tempfile
import unittest

from sabpuja_kundali import engine

from . import conformance as c
from . import current as cur
from . import inputs, profile
from .test_parser_and_gates import env_ok

SWETEST = os.environ.get("SABPUJA_TEST_SWETEST")
RECEIPT = os.environ.get("SABPUJA_TEST_SWETEST_RECEIPT")
EPHE = os.environ.get("SABPUJA_TEST_EPHE_PATH")
PROFILE_TEXT = profile.PROFILE_PATH.read_text(encoding="utf-8")
CASES = {case["id"]: case for case in c.load_json(c.HERE / "cases.json")["cases"]}
SPEC = c.load_json(c.HERE / "spec.json")


def must_not_run(*args, **kwargs):
    raise AssertionError("engine or swetest must not run")


def code(request, ephe="/nonexistent-ephemeris"):
    try:
        engine.calculate(dict(request), ephe_path=ephe)
    except (engine.InputRefusalError, engine.ChartComputationError) as exc:
        return exc.code
    return "chart"


class Overlay(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_profile_is_valid_hashed_and_counts_match(self):
        doc, record, errors = profile.load_profile()
        self.assertEqual(errors, [])
        self.assertEqual(record["sha256"], profile.PROFILE_SHA256)
        self.assertEqual((profile.COUNTS["chart_cases"], profile.COUNTS["refusal_cases"],
                          profile.COUNTS["comparison_checks"], profile.COUNTS["self_consistency_checks"]),
                         (16, 8, 784, 32))
        self.assertEqual((profile.COUNTS["archival_comparison_checks"], profile.COUNTS["archival_self_consistency_checks"]),
                         (882, 36))
        self.assertEqual(profile.CHANGED_CASES, ("SC-07", "SC-09", "SC-10", "SC-12", "SC-13", "SC-17", "SC-18", "SC-23"))

    def test_frozen_inputs_untouched(self):
        # Literal pins, independent of inputs.py: re-pinning the code alone cannot hide a fixture or tolerance change.
        frozen = {"spec.json": "642a770d713c11bc42fc92fe441da02e4848522fc4978ae3049dddbea33d12a8",
                  "cases.json": "afd8864cd84c246011d9ed8510b3efa5ed5e6c68daa6381114a77adf0ef399c9"}
        for name, digest in frozen.items():
            self.assertEqual(inputs.sha256_bytes((c.HERE / name).read_bytes()), digest)
            self.assertEqual(inputs.INPUT_SHA256[name], digest)
        self.assertEqual(inputs.TOLERANCES, {"binding_vs_swetest": 1e-09, "engine_vs_swetest": 1e-08,
                                             "swetest_ut_jd_day": 1e-09, "independent_jd_day": 1e-09,
                                             "ketu_identity_deg": 1e-08})
        self.assertEqual({k: v["value"] for k, v in SPEC["tolerances_deg"].items()}, inputs.TOLERANCES)
        self.assertEqual(inputs.CHECKS_PER_CHART, 49)

    def edited(self, edit):
        doc = json.loads(PROFILE_TEXT)
        edit(doc)
        path = Path(self.tmp.name) / "profile.json"
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return path

    def blocked(self, path, *codes):
        with mock.patch.object(cur, "run_current_case", side_effect=must_not_run), \
             mock.patch.object(cur, "run_supplement_case", side_effect=must_not_run), \
             mock.patch.object(cur, "call_engine", side_effect=must_not_run), \
             mock.patch.object(c, "run_all", side_effect=must_not_run), \
             mock.patch.object(cur.swetest_cli, "run", side_effect=must_not_run):
            report = cur.run_all("x", "y", "z", env=env_ok(), profile_path=path)
        self.assertEqual((report["verdict"], report["exit_code"], report["cases"]), ("SWISS-CONFORMANCE BLOCKED", 2, []))
        for wanted in codes:
            self.assertIn(wanted, report["run_reasons"])
        return report

    def test_any_byte_change_blocks(self):
        path = Path(self.tmp.name) / "p.json"
        path.write_text(PROFILE_TEXT.replace("\"profile_version\": 1", "\"profile_version\": 1 "), encoding="utf-8")
        self.blocked(path, "PROFILE_SHA256_MISMATCH")
        self.blocked(Path(self.tmp.name) / "absent.json", "PROFILE_MISSING")

    def test_field_edits_block_even_with_a_forged_hash(self):
        def case(cid):
            return lambda d: next(e for e in d["cases"] if e["id"] == cid)
        edits = {
            "case removed": (lambda d: d["cases"].pop(), "PROFILE_CASE_MISSING: SC-24"),
            "case duplicated": (lambda d: d["cases"].append(dict(d["cases"][0])), "PROFILE_CASE_DUPLICATE"),
            "case order": (lambda d: d["cases"].reverse(), "PROFILE_CASE_ORDER"),
            "code changed": (lambda d: case("SC-07")(d).update(expected_refusal="TIME_OFFSET_MISMATCH"),
                             "PROFILE_CASE_CODE: SC-07"),
            "code missing": (lambda d: case("SC-17")(d).update(expected_refusal=None), "PROFILE_CASE_CODE: SC-17"),
            "historical case accepted": (lambda d: case("SC-09")(d).update(expect="chart", expected_refusal=None),
                                         "PROFILE_CASE_CODE: SC-09"),
            "latitude reverted": (lambda d: case("SC-18")(d).update(expected_refusal="ASCENDANT_UNCOMPUTABLE"),
                                  "PROFILE_CASE_CODE: SC-18"),
            "reason removed": (lambda d: case("SC-23")(d)["change"].update(reason=" "), "PROFILE_CASE_CHANGE: SC-23"),
            "milestone removed": (lambda d: case("SC-13")(d)["change"].pop("source_milestone"), "PROFILE_CASE_CHANGE: SC-13"),
            "archival misstated": (lambda d: case("SC-17")(d)["change"].update(archival_expected_refusal="INPUT_REFUSED"),
                                   "PROFILE_CASE_CHANGE: SC-17"),
            "unrecorded change": (lambda d: case("SC-01")(d).update(change=case("SC-09")(d)["change"]),
                                  "PROFILE_CASE_CHANGE: SC-01"),
            "comparison count reduced": (lambda d: d["counts"].update(comparison_checks=735), "PROFILE_COUNTS"),
            "self-consistency count": (lambda d: d["counts"].update(self_consistency_checks=36), "PROFILE_COUNTS"),
            "house letter P": (lambda d: d["house_reference"].update(letter="P"), "PROFILE_HOUSE_REFERENCE"),
            "swetest switch P": (lambda d: d["house_reference"]["swetest_houses"].__setitem__(-1, "-house<LON>,<LAT>,P"),
                                 "PROFILE_HOUSE_REFERENCE"),
            "base hash forged": (lambda d: d["base"].update({"cases.json": "0" * 64}), "PROFILE_BASE_HASH"),
            "supplement widened": (lambda d: d["historical_numerics_supplement"]["cases"].append("SC-13"),
                                   "PROFILE_HISTORICAL_SUPPLEMENT"),
            "supplement relabelled": (lambda d: d["historical_numerics_supplement"].update(label="production numerics"),
                                      "PROFILE_HISTORICAL_SUPPLEMENT"),
            "observation dropped": (lambda d: d["placidus_reference_observations"]["observations"].pop(),
                                    "PROFILE_PLACIDUS_OBSERVATIONS"),
            "divergence edited": (lambda d: d["archival_run_expected_divergence"].pop("SC-23"),
                                  "PROFILE_ARCHIVAL_DIVERGENCE"),
            "claim weakened": (lambda d: d.update(claim_boundary="Swiss conformance"), "PROFILE_CLAIM_BOUNDARY"),
            "version bumped": (lambda d: d.update(profile_version=2), "PROFILE_VERSION"),
            "extra key": (lambda d: d.update(extra=1), "PROFILE_KEYS"),
        }
        for label, (edit, wanted) in edits.items():
            with self.subTest(edit=label):
                path = self.edited(edit)
                # Forge the pin to the edited bytes: field validation must still block.
                with mock.patch.object(profile, "PROFILE_SHA256", inputs.sha256_bytes(path.read_bytes())):
                    report = self.blocked(path, wanted)
                self.assertNotIn("PROFILE_SHA256_MISMATCH", report["run_reasons"])

    def test_strict_json(self):
        for text, wanted in (("{", "PROFILE_INVALID_JSON"), ('{"a": 1, "a": 2}', "PROFILE_DUPLICATE_KEY"),
                             ('{"a": NaN}', "PROFILE_NON_FINITE_NUMBER")):
            with self.subTest(text=text):
                path = Path(self.tmp.name) / "p.json"
                path.write_text(text, encoding="utf-8")
                self.blocked(path, wanted)

    def test_code_table_drift_blocks(self):
        drifted = dict(profile.CURRENT_CASES, **{"SC-13": "DATE_OUTSIDE_SUPPORTED_RANGE"})
        with mock.patch.object(profile, "CURRENT_CASES", drifted):
            self.assertIn("PROFILE_CASE_CODE: SC-13", profile.load_profile()[2])
        with mock.patch.dict(profile.COUNTS, comparison_checks=735):
            self.assertIn("PROFILE_COUNTS", profile.load_profile()[2])

    def test_frozen_input_edit_still_blocks_through_current_runner(self):
        with mock.patch.dict(inputs.INPUT_SHA256, {"cases.json": "0" * 64}):
            report = self.blocked(profile.PROFILE_PATH, "CASES_SHA256_MISMATCH", "PROFILE_BASE_HASH")
        self.assertEqual(report["verdicts"]["current"], "SWISS-CONFORMANCE BLOCKED")


class EngineRefusals(unittest.TestCase):
    """Refusal codes, P5 precedence and pre-ephemeris refusal; no Swiss data needed."""

    def test_every_refusal_case_has_its_code_before_ephemeris(self):
        for cid, expected in profile.CURRENT_CASES.items():
            if expected == "chart":
                continue
            with self.subTest(case=cid), \
                 mock.patch.object(engine, "verify_ephemeris_dir", side_effect=must_not_run):
                self.assertEqual(code(CASES[cid]["request"]), expected)

    def test_sc13_offset_and_precedence(self):
        request = CASES["SC-13"]["request"]
        from datetime import datetime, timedelta
        from sabpuja_kundali.timezones import get_zone
        self.assertEqual(get_zone("Etc/GMT-3").utcoffset(datetime(1900, 1, 1, 2)), timedelta(hours=3))
        self.assertEqual(code(request), "HISTORICAL_CLOCK_UNVERIFIED")
        # Earlier P5 steps win: offset mismatch before the historical gate.
        for offset in ("+04:00", "+02:00"):
            self.assertEqual(code(dict(request, birth_datetime="1900-01-01T02:00:00" + offset)), "TIME_OFFSET_MISMATCH")
        # The same instant written as a UTC 1899 local date is outside the local-date window.
        self.assertEqual(code(dict(request, birth_datetime="1899-12-31T23:00:00+00:00", timezone="UTC")),
                         "DATE_OUTSIDE_SUPPORTED_RANGE")
        # Only the historical gate refuses it: gate overridden, it proceeds to the ephemeris check.
        with cur.historical_gate_override(), \
             mock.patch.object(engine, "verify_ephemeris_dir", side_effect=RuntimeError("reached ephemeris")):
            with self.assertRaisesRegex(RuntimeError, "reached ephemeris"):
                engine.calculate(dict(request), ephe_path="/nonexistent-ephemeris")

    def test_time_refusals_precede_latitude(self):
        polar = CASES["SC-17"]["request"]
        self.assertEqual(code(dict(polar, birth_datetime="1950-06-21T12:00:00+00:00")), "HISTORICAL_CLOCK_UNVERIFIED")
        self.assertEqual(code(dict(polar, birth_datetime="2026-06-21T12:00:00")), "TIME_OFFSET_REQUIRED")
        with cur.historical_gate_override():
            self.assertEqual(code(dict(polar, birth_datetime="1950-06-21T12:00:00+00:00")),
                             "LATITUDE_OUTSIDE_SUPPORTED_BAND")

    def test_gate_override_is_scoped_and_restored(self):
        original = engine.HISTORICAL_CLOCK_GATE
        with cur.historical_gate_override():
            self.assertEqual(engine.HISTORICAL_CLOCK_GATE, ())
        self.assertIs(engine.HISTORICAL_CLOCK_GATE, original)
        self.assertEqual(code(CASES["SC-09"]["request"]), "HISTORICAL_CLOCK_UNVERIFIED")

    def test_recorded_refusal_makes_no_swiss_call(self):
        status, payload, record = cur.call_engine(CASES["SC-17"]["request"], "/nonexistent-ephemeris")
        self.assertEqual((status, payload), ("refused", "LATITUDE_OUTSIDE_SUPPORTED_BAND"))
        self.assertEqual(record, {"ephemeris_checked": False, "swiss_calls": [], "houses_ex": []})


class MethodChecks(unittest.TestCase):
    def sw(self, letter="W", asc=76.33809052205, cusps=None):
        base = int(asc // 30)
        cusps = cusps or {n: float(((base + n - 1) % 12) * 30) for n in range(1, 13)}
        return {"house_system": letter, "values": {"lagna": asc}, "cusps": cusps}

    def record(self, hsys=b"W", flags=None):
        import swisseph as swe
        return {"houses_ex": [{"hsys": hsys, "flags": swe.FLG_SIDEREAL if flags is None else flags, "argc": 5}]}

    def outcomes(self, record, sw, bind_cusps=None):
        bind = {"cusps": bind_cusps if bind_cusps is not None else [sw["cusps"][n] for n in range(1, 13)]}
        return {x["quantity"]: x["outcome"] for x in cur.house_method_checks("X", record, sw, bind, 1e-9)}

    def test_whole_sign_passes(self):
        self.assertEqual(set(self.outcomes(self.record(), self.sw()).values()), {c.PASS})

    def test_placidus_anywhere_fails(self):
        self.assertEqual(self.outcomes(self.record(b"P"), self.sw())["engine_houses_ex_call"], c.FAIL)
        self.assertEqual(self.outcomes(self.record(flags=0), self.sw())["engine_houses_ex_call"], c.FAIL)
        self.assertEqual(self.outcomes({"houses_ex": []}, self.sw())["engine_houses_ex_call"], c.FAIL)
        self.assertEqual(self.outcomes(self.record(), self.sw(letter="P"))["swetest_house_system_letter"], c.FAIL)
        placidus = {n: 76.33809052205 + n for n in range(1, 13)}
        self.assertEqual(self.outcomes(self.record(), self.sw(cusps=placidus))["swetest_whole_sign_cusps"], c.FAIL)
        shifted = [x + 1e-6 for x in (self.sw()["cusps"][n] for n in range(1, 13))]
        self.assertEqual(self.outcomes(self.record(), self.sw(), shifted)["binding_vs_swetest_cusps"], c.FAIL)

    def test_missing_cusps_block(self):
        sw = self.sw()
        sw["cusps"] = {}
        self.assertEqual(self.outcomes(self.record(), sw, [])["swetest_whole_sign_cusps"], c.BLOCKED)


class CoverageAndReconciliation(unittest.TestCase):
    def fake(self):
        charts = [{"case": cid, "expect": "chart", "outcome": c.PASS,
                   "checks": [{"kind": "x", "quantity": q, "outcome": c.PASS, "value": 1} for q in inputs.CHART_QUANTITIES],
                   "self_consistency": [{"result": "SELF-CONSISTENCY PASS"}] * 2,
                   "method_checks": [{"quantity": q, "outcome": c.PASS} for q in cur.HOUSE_METHOD_QUANTITIES]}
                  for cid in profile.CURRENT_CASES]
        for r in charts:
            if profile.CURRENT_CASES[r["case"]] != "chart":
                obs = cur.OBSERVATION_QUANTITIES if r["case"] in profile.PLACIDUS_OBSERVATION_CASES else ()
                r.update(expect="refuse", checks=[{"quantity": q, "outcome": c.PASS} for q in cur.REFUSAL_QUANTITIES],
                         self_consistency=[], method_checks=[],
                         reference_observations=[{"quantity": q, "outcome": c.PASS} for q in obs])
        supplement = [dict(next(r for r in charts if r["case"] == "SC-01"), case=cid, expect="chart",
                           checks=charts[0]["checks"], self_consistency=charts[0]["self_consistency"],
                           method_checks=charts[0]["method_checks"]) for cid in profile.HISTORICAL_SUPPLEMENT]
        return charts, supplement

    def test_full_coverage(self):
        counts, errors = cur.coverage(*self.fake())
        self.assertEqual(errors, [])
        self.assertEqual((counts["comparison_checks"], counts["self_consistency_checks"], counts["house_method_checks"],
                          counts["refusal_checks"], counts["placidus_reference_observations"]), (784, 32, 64, 16, 4))

    def test_dropped_check_or_case_blocks(self):
        charts, supplement = self.fake()
        charts[0]["checks"].pop()
        self.assertIn("COVERAGE_CHART_QUANTITIES: SC-01", cur.coverage(charts, supplement)[1])
        charts, supplement = self.fake()
        self.assertIn("COVERAGE_CASE_SET", cur.coverage(charts[:-1], supplement)[1])
        charts, supplement = self.fake()
        charts[16]["reference_observations"] = []
        self.assertIn("COVERAGE_PLACIDUS_OBSERVATIONS: SC-17", cur.coverage(charts, supplement)[1])
        charts, supplement = self.fake()
        self.assertIn("COVERAGE_SUPPLEMENT_SET", cur.coverage(charts, supplement[:1])[1])
        with mock.patch.dict(profile.COUNTS, comparison_checks=735):
            self.assertIn("COVERAGE_COUNT: comparison_checks", cur.coverage(*self.fake())[1])

    def archival(self, failed=None):
        failed = dict(profile.ARCHIVAL_DIVERGENCE) if failed is None else failed
        charts = self.fake()[0]
        cases = [{"case": r["case"], "outcome": c.FAIL if r["case"] in failed else c.PASS,
                  "reasons": [failed[r["case"]]] if r["case"] in failed else [],
                  "checks": r["checks"] if r["expect"] == "chart" else []} for r in charts]
        return {"run_reasons": [], "cases": cases, "verdict": c.VERDICT[c.FAIL] if failed else c.VERDICT[c.PASS]}, charts

    def test_reconciliation(self):
        archival, charts = self.archival()
        self.assertEqual(cur.reconcile(archival, charts)["outcome"], c.PASS)
        archival, charts = self.archival({k: v for k, v in profile.ARCHIVAL_DIVERGENCE.items() if k != "SC-23"})
        self.assertEqual(cur.reconcile(archival, charts)["outcome"], c.FAIL)
        archival, charts = self.archival(dict(profile.ARCHIVAL_DIVERGENCE, **{"SC-01": "x"}))
        self.assertEqual(cur.reconcile(archival, charts)["outcome"], c.FAIL)
        archival, charts = self.archival()
        charts[0]["checks"] = charts[0]["checks"][:-1]
        self.assertEqual(cur.reconcile(archival, charts)["outcome"], c.FAIL)
        archival["run_reasons"] = ["SWETEST_MISSING"]
        self.assertEqual(cur.reconcile(archival, charts)["outcome"], c.BLOCKED)


class MissingReferences(unittest.TestCase):
    def test_missing_swetest_is_never_pass(self):
        env = env_ok(swetest={"present": False, "sha256": None, "receipt": None, "receipt_errors": []})
        with mock.patch.object(cur, "run_current_case", side_effect=must_not_run):
            report = cur.run_all(None, EPHE, None, env=env)
        self.assertEqual((report["exit_code"], report["cases"]), (2, []))
        self.assertIn("SWETEST_MISSING", report["run_reasons"])
        self.assertEqual(set(report["verdicts"].values()), {"SWISS-CONFORMANCE BLOCKED"})

    def test_unrunnable_swetest_blocks_each_case(self):
        with tempfile.TemporaryDirectory() as tmp:
            sw = cur.swetest_pair(str(Path(tmp) / "absent"), tmp, 2451545.0, 0.0, 0.0, "W")
        self.assertEqual(sw["problems"], ["SWETEST_NOT_RUN: FileNotFoundError"] * 2)

    def test_receipt_problems_block(self):
        for errors in (["SWETEST_BUILD_RECEIPT_MISSING"], ["SWETEST_BUILD_RECEIPT_INVALID"],
                       ["SWETEST_BUILD_RECEIPT_MISMATCH"], ["SWETEST_SOURCE_NOT_APPROVED"]):
            with self.subTest(errors=errors):
                env = env_ok(swetest={"present": True, "sha256": "f" * 64, "receipt": None, "receipt_errors": errors})
                report = cur.run_all("x", "y", "z", env=env)
                self.assertEqual(report["exit_code"], 2)
                self.assertIn(errors[0], report["run_reasons"])


@unittest.skipIf(not EPHE, "SABPUJA_TEST_EPHE_PATH unset: chart-computing method tests skipped")
class EngineWholeSignCall(unittest.TestCase):
    def test_engine_calls_whole_sign_with_sidereal_flag_only(self):
        import swisseph as swe
        for cid in [k for k, v in profile.CURRENT_CASES.items() if v == "chart"]:
            with self.subTest(case=cid):
                status, payload, record = cur.call_engine(CASES[cid]["request"], EPHE)
                self.assertEqual(status, "chart")
                self.assertEqual(record["houses_ex"], [{"hsys": b"W", "flags": swe.FLG_SIDEREAL, "argc": 5}])
                self.assertTrue(record["ephemeris_checked"])

    def test_supplement_charts_only_with_override(self):
        for cid in profile.HISTORICAL_SUPPLEMENT:
            with self.subTest(case=cid):
                with cur.historical_gate_override():
                    status, payload, _ = cur.call_engine(CASES[cid]["request"], EPHE)
                self.assertEqual((status, payload["birth"]["utc"]), ("chart", CASES[cid]["expected_utc"]))
                self.assertEqual(cur.call_engine(CASES[cid]["request"], EPHE)[:2],
                                 ("refused", "HISTORICAL_CLOCK_UNVERIFIED"))


@unittest.skipIf(SWETEST is None, "SABPUJA_TEST_SWETEST unset: swetest conformance not requested")
class CurrentProfileWithSwetest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not EPHE:
            raise RuntimeError("SABPUJA_TEST_SWETEST is set but SABPUJA_TEST_EPHE_PATH is not")
        env = c.capture_environment(SWETEST, RECEIPT, EPHE)
        problems = [r for r in c.run_reasons(env, SPEC) if r not in ("DIRTY_TREE", "GIT_UNAVAILABLE")]
        if problems:
            raise RuntimeError(f"swetest environment not valid: {problems}")

    def run_case(self, cid):
        return cur.run_current_case(CASES[cid], SWETEST, EPHE, SPEC)

    def failing(self, result):
        return sorted({x["quantity"] for x in result["checks"] + result.get("method_checks", [])
                       if x["outcome"] == c.FAIL})

    def test_every_case_conforms_to_current_profile(self):
        for cid in profile.CURRENT_CASES:
            with self.subTest(case=cid):
                result = self.run_case(cid)
                self.assertEqual(result["outcome"], c.PASS, result["reasons"])

    def test_historical_supplement_conforms(self):
        for cid in profile.HISTORICAL_SUPPLEMENT:
            with self.subTest(case=cid):
                result = cur.run_supplement_case(CASES[cid], SWETEST, EPHE, SPEC)
                self.assertEqual((result["outcome"], len(result["checks"]), result["gate_restored"]), (c.PASS, 49, True))

    def test_placidus_reference_reproduces(self):
        for cid in profile.PLACIDUS_OBSERVATION_CASES:
            with self.subTest(case=cid):
                obs = self.run_case(cid)["reference_observations"]
                self.assertEqual([(x["quantity"], x["outcome"]) for x in obs],
                                 [(q, c.PASS) for q in cur.OBSERVATION_QUANTITIES])

    def test_placidus_reference_letter_fails_method_checks_only(self):
        # The Ascendant agrees for P and W, so only the house-method checks can see the letter.
        real = cur.house_argv
        with mock.patch.object(cur, "house_argv", side_effect=lambda *a: real(*a[:-1], "P")):
            result = self.run_case("SC-01")
        self.assertEqual(result["outcome"], c.FAIL)
        self.assertEqual(self.failing(result), ["binding_vs_swetest_cusps", "swetest_house_system_letter",
                                                "swetest_whole_sign_cusps"])
        self.assertEqual(sum(x["outcome"] == c.PASS for x in result["checks"]), 49)

    def test_engine_placidus_call_fails(self):
        # An engine whose source asks Swiss for b"P" (same Ascendant) is caught by the recorded call only.
        source = Path(engine.__file__).read_text(encoding="utf-8")
        self.assertEqual(source.count('b"W", swe.FLG_SIDEREAL'), 1)
        namespace = {"__name__": "sabpuja_kundali._mutant_engine", "__package__": "sabpuja_kundali"}
        exec(compile(source.replace('b"W", swe.FLG_SIDEREAL', 'b"P", swe.FLG_SIDEREAL'), engine.__file__, "exec"), namespace)
        with mock.patch.object(engine, "calculate", namespace["calculate"]):
            result = self.run_case("SC-01")
        self.assertEqual(result["outcome"], c.FAIL)
        self.assertEqual(self.failing(result), ["engine_houses_ex_call"])

    def test_wrong_location_fails_for_lagna(self):
        real = cur.house_argv
        with mock.patch.object(cur, "house_argv", side_effect=lambda s, e, jd, lat, lon, letter: real(s, e, jd, lat, lon + 1.0, letter)):
            result = self.run_case("SC-01")
        self.assertEqual(result["outcome"], c.FAIL)
        self.assertIn("lagna", self.failing(result))

    def test_accepting_a_historical_case_fails(self):
        with cur.historical_gate_override():
            result = self.run_case("SC-23")
        self.assertEqual(result["outcome"], c.FAIL)

    def test_reverting_latitude_refusal_fails(self):
        with mock.patch.object(engine, "SUPPORTED_LATITUDE_DEG", 90.0):
            result = self.run_case("SC-17")
        self.assertEqual(result["outcome"], c.FAIL)
        self.assertIn("engine_refusal_code: a chart", result["reasons"])

    def test_full_run_with_git_gate_masked(self):
        env = c.capture_environment(SWETEST, RECEIPT, EPHE)
        env["git"] = {"commit": env["git"]["commit"], "dirty": False}
        report = cur.run_all(SWETEST, EPHE, RECEIPT, env=env)
        self.assertEqual(report["verdicts"], {k: "SWISS-CONFORMANCE PASS" for k in ("current", "historical_supplement",
                                                                                      "reconciliation")})
        self.assertEqual(report["coverage_errors"], [])
        self.assertEqual(report["archival"]["verdict"], "SWISS-CONFORMANCE FAIL")


if __name__ == "__main__":
    unittest.main()
