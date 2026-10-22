"""Frozen-input validation, coverage enforcement and receipt provenance (no Swiss data or swetest needed)."""
from pathlib import Path
from unittest import mock
import json
import tempfile
import unittest

from . import conformance as c
from . import inputs
from .test_parser_and_gates import env_ok

SPEC_TEXT = (c.HERE / "spec.json").read_text(encoding="utf-8")
CASES_TEXT = (c.HERE / "cases.json").read_text(encoding="utf-8")
OFFICIAL = {"swetest_sha256": "a" * 64, "source_repository": "https://github.com/aloistr/swisseph",
            "source_commit": "c69c14adb7a0f94829586ffd92cd422aacb21e86", "build_command": "make swetest",
            "compiler": "gcc 13.3.0", "license": "AGPL-3.0", "swiss_version": "2.10.03"}


def must_not_run(*args, **kwargs):
    raise AssertionError("engine or swetest must not run")


class Inputs(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name, text):
        path = Path(self.tmp.name) / name
        path.write_text(text, encoding="utf-8")
        return path

    def blocked_run(self, spec_text=SPEC_TEXT, cases_text=CASES_TEXT):
        """run_all on edited inputs: must be BLOCKED without touching the engine or swetest."""
        spec, cases = self.write("spec.json", spec_text), self.write("cases.json", cases_text)
        with mock.patch.object(c, "run_case", side_effect=must_not_run), \
             mock.patch.object(c.swetest_cli, "run", side_effect=must_not_run), \
             mock.patch.object(c, "call_engine", side_effect=must_not_run):
            report = c.run_all("x", "y", "z", spec_path=spec, cases_path=cases, env=env_ok())
        self.assertEqual((report["verdict"], report["exit_code"], report["cases"]), ("SWISS-CONFORMANCE BLOCKED", 2, []))
        return report["run_reasons"]

    def test_frozen_inputs_are_valid_and_hashed(self):
        spec, cases, record, errors = inputs.load_inputs(c.HERE / "spec.json", c.HERE / "cases.json")
        self.assertEqual(errors, [])
        self.assertEqual(len(cases), 24)
        self.assertEqual(sum(v == "chart" for v in inputs.CASES.values()), 18)
        self.assertEqual(inputs.CHECKS_PER_CHART * inputs.CHART_CASES, 882)
        for name in ("spec.json", "cases.json"):
            self.assertEqual(record[name]["sha256"], inputs.INPUT_SHA256[name])

    def test_strict_json(self):
        for text, code in (('{"a": NaN}', "NON_FINITE_NUMBER"), ('{"a": Infinity}', "NON_FINITE_NUMBER"),
                           ('{"a": -Infinity}', "NON_FINITE_NUMBER"), ('{"a": 1e400}', "NON_FINITE_NUMBER"),
                           ('{"a": 1, "a": 2}', "DUPLICATE_KEY"), ('{"a": ', "INVALID_JSON"),
                           ("[" * 100000, "INVALID_JSON")):
            with self.subTest(text=text[:20]):
                with self.assertRaises(inputs.InputError) as ctx:
                    inputs.parse_strict(text.encode())
                self.assertEqual(ctx.exception.code, code)
        with self.assertRaises(inputs.InputError) as ctx:
            inputs.read_bytes(self.write("big.json", " " * (inputs.MAX_INPUT_BYTES + 1)))
        self.assertEqual(ctx.exception.code, "OVERLONG")

    def test_bad_tolerances_block_before_any_case(self):
        frozen = '"value": 1e-08,'
        self.assertIn(frozen, SPEC_TEXT)
        for bad, code in (("Infinity", "SPEC_NON_FINITE_NUMBER"), ("-Infinity", "SPEC_NON_FINITE_NUMBER"),
                          ("NaN", "SPEC_NON_FINITE_NUMBER"), ("1e400", "SPEC_NON_FINITE_NUMBER"),
                          ("true", "SPEC_TOLERANCE_INVALID: engine_vs_swetest"),
                          ("0", "SPEC_TOLERANCE_INVALID: engine_vs_swetest"),
                          ("0.0", "SPEC_TOLERANCE_INVALID: engine_vs_swetest"),
                          ("-1e-08", "SPEC_TOLERANCE_INVALID: engine_vs_swetest"),
                          ("1", "SPEC_TOLERANCE_INVALID: engine_vs_swetest"),
                          ("\"1e-08\"", "SPEC_TOLERANCE_INVALID: engine_vs_swetest"),
                          ("1e-07", "SPEC_TOLERANCE_NOT_FROZEN: engine_vs_swetest"),
                          ("1e-09", "SPEC_TOLERANCE_NOT_FROZEN: engine_vs_swetest")):
            with self.subTest(bad=bad):
                reasons = self.blocked_run(spec_text=SPEC_TEXT.replace(frozen, f'"value": {bad},', 1))
                self.assertIn("SPEC_SHA256_MISMATCH", reasons)
                self.assertIn(code, reasons)

    def test_other_spec_edits_block(self):
        edits = {
            "SPEC_CLAIM_BOUNDARY": lambda s: s.update(claim_boundary="Astronomically validated."),
            "SPEC_REQUIRED_VERSIONS": lambda s: s["required_versions"].update(swiss_library="2.10.02"),
            "SPEC_SWETEST_SWITCHES": lambda s: s["swetest_switches"]["planets"].__setitem__(3, "-sid3"),
            "SPEC_BODIES": lambda s: s["bodies"].pop(),
            "SPEC_KEYS": lambda s: s.pop("boundary_rule"),
            "SPEC_NOT_FROZEN": lambda s: s.update(status="DRAFT"),
            "SPEC_TOLERANCE_KEYS": lambda s: s["tolerances_deg"].pop("ketu_identity_deg"),
        }
        for code, edit in edits.items():
            with self.subTest(code=code):
                edited = json.loads(SPEC_TEXT)
                edit(edited)
                self.assertIn(code, self.blocked_run(spec_text=json.dumps(edited, indent=2)))
        self.assertIn("SPEC_NOT_OBJECT", self.blocked_run(spec_text="[]"))

    def test_case_set_edits_block(self):
        doc = json.loads(CASES_TEXT)
        by_id = {case["id"]: case for case in doc["cases"]}

        def with_cases(cases):
            return json.dumps({**doc, "cases": cases}, indent=2)
        refusal_only = self.blocked_run(cases_text=with_cases([by_id["SC-07"]]))
        self.assertIn("CASE_MISSING: SC-01", refusal_only)
        self.assertEqual(sum(r.startswith("CASE_MISSING") for r in refusal_only), 23)
        self.assertIn("CASE_DUPLICATE: SC-03", self.blocked_run(cases_text=with_cases(doc["cases"] + [by_id["SC-03"]])))
        renamed = [dict(case, id="SC-99") if case["id"] == "SC-24" else case for case in doc["cases"]]
        reasons = self.blocked_run(cases_text=with_cases(renamed))
        self.assertIn("CASE_UNEXPECTED: SC-99", reasons)
        self.assertIn("CASE_MISSING: SC-24", reasons)
        bad_id = [dict(case, id="sc-24") if case["id"] == "SC-24" else case for case in doc["cases"]]
        self.assertIn("CASE_ID_INVALID", self.blocked_run(cases_text=with_cases(bad_id)))
        retyped = [dict(case, expect="refuse", expected_utc=None, expected_refusal="INPUT_REFUSED")
                   if case["id"] == "SC-01" else case for case in doc["cases"]]
        self.assertIn("CASE_TYPE_CHANGED: SC-01", self.blocked_run(cases_text=with_cases(retyped)))
        for lat in (True, 91.0, "28.6"):
            with self.subTest(lat=lat):
                edited = [dict(case, request=dict(case["request"], latitude=lat)) if case["id"] == "SC-01" else case
                          for case in doc["cases"]]
                self.assertIn("CASE_REQUEST: SC-01", self.blocked_run(cases_text=with_cases(edited)))
        self.assertIn("CASE_ORDER", self.blocked_run(cases_text=with_cases(doc["cases"][::-1])))
        self.assertIn("CASES_NOT_OBJECT", self.blocked_run(cases_text='{"cases": []}'))

    def test_missing_input_file_blocks(self):
        report = c.run_all("x", "y", "z", spec_path=Path(self.tmp.name) / "none.json", env=env_ok())
        self.assertEqual(report["exit_code"], 2)
        self.assertIn("SPEC_MISSING", report["run_reasons"])


def chart_checks(case_id, drop=None):
    checks = []
    for key in sorted(inputs.CHART_QUANTITIES):
        if key == drop:
            continue
        kind, _, body = key.partition(":")
        checks.append({"case": case_id, "kind": kind if body else "x", "quantity": body or key, "outcome": c.PASS})
    return checks


def results(drop=None, only=None):
    out = []
    for cid, kind in inputs.CASES.items():
        if only and cid not in only:
            continue
        chart = kind == "chart"
        out.append({"case": cid, "outcome": c.PASS, "checks": chart_checks(cid, drop) if chart else [],
                    "self_consistency": [{"result": "SELF-CONSISTENCY PASS"}] * 2 if chart else []})
    return out


class Coverage(unittest.TestCase):
    def run_with(self, fake_results):
        queue = iter(fake_results)
        with mock.patch.object(c, "run_case", side_effect=lambda *a: next(queue)):
            return c.run_all("x", "y", "z", env=env_ok())

    def test_full_coverage_passes(self):
        counts, errors = c.coverage(results())
        self.assertEqual(errors, [])
        self.assertEqual((counts["comparison_checks_run"], counts["comparison_checks_passed"]), (882, 882))
        self.assertEqual(counts["self_consistency_passed"], 36)

    def test_missing_quantity_blocks_even_if_everything_else_passes(self):
        report = self.run_with(results(drop="engine_vs_swetest_deg:lagna"))
        self.assertEqual(report["exit_code"], 2)
        self.assertIn("COVERAGE_CHART_QUANTITIES: SC-01", report["coverage_errors"])

    def test_case_with_no_checks_blocks(self):
        hollow = results()
        hollow[0]["checks"] = []
        self.assertEqual(self.run_with(hollow)["exit_code"], 2)

    def test_partial_case_set_blocks(self):
        counts, errors = c.coverage(results(only={"SC-07"}))
        self.assertEqual(errors, ["COVERAGE_CASE_SET"])
        self.assertEqual(counts["comparison_checks_run"], 0)

    def test_fail_stays_fail(self):
        failed = results()
        failed[0]["outcome"] = c.FAIL
        self.assertEqual(self.run_with(failed)["exit_code"], 1)


class Receipts(unittest.TestCase):
    def test_official_receipt_is_approved(self):
        source, errors = inputs.validate_receipt(OFFICIAL, "a" * 64)
        self.assertEqual(errors, [])
        self.assertIn("reference build", source)

    def test_bundled_receipt_is_labelled_as_cross_check(self):
        bundled = dict(OFFICIAL, source_repository="pyswisseph 2.10.3.2 sdist (PyPI) libswe/",
                       source_commit="sdist sha256 c54c305e83dbd5d2b71e58d8a69d8ee41de24c4d3328ce09e2af860a3537624d")
        source, errors = inputs.validate_receipt(bundled, "a" * 64)
        self.assertEqual(errors, [])
        self.assertIn("NOT the official source", source)

    def test_bad_receipts_block(self):
        cases = {
            "wrong commit": (dict(OFFICIAL, source_commit="0" * 40), "SWETEST_SOURCE_NOT_APPROVED"),
            "wrong repository": (dict(OFFICIAL, source_repository="https://example.invalid/swisseph"),
                                 "SWETEST_SOURCE_NOT_APPROVED"),
            "wrong version": (dict(OFFICIAL, swiss_version="2.10.02"), "SWETEST_RECEIPT_VERSION_MISMATCH"),
            "empty build": (dict(OFFICIAL, build_command="  "), "SWETEST_BUILD_RECEIPT_INVALID"),
            "missing license": ({k: v for k, v in OFFICIAL.items() if k != "license"}, "SWETEST_BUILD_RECEIPT_INVALID"),
            "non-string compiler": (dict(OFFICIAL, compiler=13), "SWETEST_BUILD_RECEIPT_INVALID"),
            "sha mismatch": (dict(OFFICIAL, swetest_sha256="b" * 64), "SWETEST_BUILD_RECEIPT_MISMATCH"),
            "not an object": ([], "SWETEST_BUILD_RECEIPT_INVALID"),
        }
        for label, (receipt, code) in cases.items():
            with self.subTest(label=label):
                self.assertIn(code, inputs.validate_receipt(receipt, "a" * 64)[1])
                self.assertIn(code, c.run_reasons(env_ok(swetest={"present": True, "sha256": "a" * 64, "receipt": None,
                                                                  "source": None, "receipt_errors":
                                                                  inputs.validate_receipt(receipt, "a" * 64)[1]}),
                                                  json.loads(SPEC_TEXT)))


if __name__ == "__main__":
    unittest.main()
