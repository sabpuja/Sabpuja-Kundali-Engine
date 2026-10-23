"""Real swetest vs the Python integration, including deliberate mismatches.

Skipped only when SABPUJA_TEST_SWETEST is unset. Once it is set, the
binary, its build receipt (SABPUJA_TEST_SWETEST_RECEIPT) and the pinned data
(SABPUJA_TEST_EPHE_PATH) must all be valid or the class errors instead of
skipping. Swiss-on-Swiss conformance only, not astronomical validation.

KUN-03 D3: these tests exercise the archival comparison machinery on frozen
UTC requests, so they reproduce the PR #33 timezone policy with the D3 check
bypassed for each test (d3.d3_override, test-only, restoration verified).
test_d3_profile pins the archival divergence from the D3 engine without it.
"""
from unittest import mock
import os
import tempfile
import unittest

from . import conformance as c
from . import d3, profile
from . import swetest_cli as cli

SWETEST = os.environ.get("SABPUJA_TEST_SWETEST")
RECEIPT = os.environ.get("SABPUJA_TEST_SWETEST_RECEIPT")
EPHE = os.environ.get("SABPUJA_TEST_EPHE_PATH")
SPEC = c.load_json(c.HERE / "spec.json")
CASES = {case["id"]: case for case in c.load_json(c.HERE / "cases.json")["cases"]}


@unittest.skipIf(SWETEST is None, "SABPUJA_TEST_SWETEST unset: swetest conformance not requested")
class SwetestConformance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not EPHE:
            raise RuntimeError("SABPUJA_TEST_SWETEST is set but SABPUJA_TEST_EPHE_PATH is not")
        env = c.capture_environment(SWETEST, RECEIPT, EPHE)
        # The git gate is enforced by the CLI run; unit tests run on a working tree.
        problems = [r for r in c.run_reasons(env, SPEC) if r not in ("DIRTY_TREE", "GIT_UNAVAILABLE")]
        if problems:
            raise RuntimeError(f"swetest environment not valid: {problems}")

    def setUp(self):
        self.enterContext(d3.d3_override())

    def run_case(self, case_id):
        return c.run_case(CASES[case_id], SWETEST, EPHE, SPEC)

    def test_every_predeclared_case_conforms(self):
        # Archival profile against the KUN-03 engine: every case conforms except
        # the divergence recorded in the versioned current profile, which must
        # fail exactly as recorded (see profile.py and RECONCILIATION.md).
        for case_id in CASES:
            with self.subTest(case=case_id):
                result = self.run_case(case_id)
                if case_id in profile.ARCHIVAL_DIVERGENCE:
                    self.assertEqual((result["outcome"], result["reasons"]),
                                     (c.FAIL, [profile.ARCHIVAL_DIVERGENCE[case_id]]))
                    continue
                self.assertEqual(result["outcome"], c.PASS, (result["reasons"],
                                 [x for x in result["checks"] if x["outcome"] != c.PASS]))

    def test_boundary_cases_classify_on_each_side(self):
        below, above = self.run_case("SC-14"), self.run_case("SC-15")
        moon = lambda r: next(x for x in r["checks"] if x["quantity"] == "moon.nakshatra_pada")
        self.assertEqual(moon(below)["reference"], ("Revati", 4))
        self.assertEqual(moon(above)["reference"], ("Ashwini", 1))

    def test_swetest_version_and_flags_echoed(self):
        result = self.run_case("SC-01")
        receipt = result["receipts"][0]
        self.assertEqual(receipt["version"], "2.10.03")
        self.assertEqual(receipt["argv"][3:], list(cli.PLANET_ARGS))
        self.assertNotIn(EPHE, receipt["stdout"])

    def mismatch(self, planet_args=None, house_args=None):
        with mock.patch.object(cli, "PLANET_ARGS", planet_args or cli.PLANET_ARGS), \
             mock.patch.object(cli, "HOUSE_ARGS", house_args or cli.HOUSE_ARGS):
            return self.run_case("SC-01")

    def failing(self, result):
        return sorted({x["quantity"] for x in result["checks"] if x["outcome"] == c.FAIL})

    def test_wrong_ayanamsa_fails(self):
        args = tuple("-sid3" if a == "-sid1" else a for a in cli.PLANET_ARGS)
        result = self.mismatch(planet_args=args)
        self.assertEqual(result["outcome"], c.FAIL)  # swetest reports Raman, not Lahiri

    def test_true_node_fails(self):
        args = tuple("-p0123456t" if a == "-p0123456m" else a for a in cli.PLANET_ARGS)
        result = self.mismatch(planet_args=args)
        self.assertEqual(result["outcome"], c.BLOCKED)  # mean node line missing: not comparable
        self.assertTrue(any(x["quantity"] == "rahu_mean" and x["outcome"] == c.BLOCKED for x in result["checks"]))

    def test_true_node_relabelled_as_mean_fails(self):
        real_run = cli.run

        def relabel(argv, ephe):
            res = real_run([("-p0123456t" if a == "-p0123456m" else a) for a in argv], ephe)
            res.values = {("mean Node" if k == "true Node" else k): v for k, v in res.values.items()}
            return res
        with mock.patch.object(cli, "run", side_effect=relabel):
            result = self.run_case("SC-01")
        self.assertEqual(result["outcome"], c.FAIL)
        self.assertIn("rahu_mean", self.failing(result))

    def test_no_aberration_flag_fails(self):
        args = tuple("-i66562" if a == "-i65538" else a for a in cli.PLANET_ARGS)  # + SEFLG_NOABERR
        result = self.mismatch(planet_args=args)
        self.assertEqual(result["outcome"], c.FAIL)
        self.assertIn("sun", self.failing(result))

    def test_no_nutation_flag_is_inert_in_sidereal_mode(self):
        # Recorded finding: Swiss sidereal positions already exclude nutation,
        # so SEFLG_NONUT cannot be detected by this suite.
        args = tuple("-i65602" if a == "-i65538" else a for a in cli.PLANET_ARGS)
        self.assertEqual(self.mismatch(planet_args=args)["outcome"], c.PASS)

    def test_tropical_fails(self):
        args = tuple(a for a in cli.PLANET_ARGS if a != "-sid1")
        args = tuple("-i2" if a == "-i65538" else a for a in args)
        result = self.mismatch(planet_args=args)
        self.assertEqual(result["outcome"], c.FAIL)

    def test_moshier_ephemeris_fails(self):
        result = self.mismatch(planet_args=(*cli.PLANET_ARGS, "-emos"))
        self.assertNotEqual(result["outcome"], c.PASS)

    def patched_house(self, edit):
        real = cli.house_argv
        with mock.patch.object(cli, "house_argv", side_effect=lambda *a: edit(real(*a))):
            return self.run_case("SC-01")

    def test_tropical_houses_fail_for_lagna(self):
        result = self.patched_house(lambda argv: ["-i0" if x == "-i65536" else x for x in argv if x != "-sid1"])
        self.assertEqual(result["outcome"], c.FAIL)
        self.assertEqual(result["reasons"], ["swetest ayanamsa is not Lahiri"])

    def test_wrong_longitude_fails_for_lagna(self):
        result = self.patched_house(lambda argv: argv[:-1] + ["-house78.209,28.6139,P"])
        self.assertEqual(result["outcome"], c.FAIL)
        self.assertIn("lagna", self.failing(result))

    def test_house_system_letter_does_not_move_ascendant(self):
        # Recorded finding: swetest prints the same Ascendant for P and W, so
        # the house-system letter is not observable through the lagna.
        result = self.patched_house(lambda argv: argv[:-1] + [argv[-1][:-1] + "W"])
        self.assertEqual(result["outcome"], c.PASS)

    def test_missing_ephemeris_files_block(self):
        with tempfile.TemporaryDirectory() as empty:
            values, receipts, problems, uts = c.swetest_pair(SWETEST, empty, 2451545.0, 0.0, 0.0)
            self.assertTrue(any("Moshier" in p for p in problems), problems)
            result = c.run_case(CASES["SC-01"], SWETEST, empty, SPEC)
            self.assertEqual(result["outcome"], c.BLOCKED)
            self.assertEqual(result["reasons"], ["ENGINE_BLOCKED: EPHEMERIS_FILE_MISSING"])

    def test_cli_run_is_blocked_with_wrong_data_path(self):
        with tempfile.TemporaryDirectory() as empty:
            env = c.capture_environment(SWETEST, RECEIPT, empty)
            self.assertIn("EPHEMERIS_UNVERIFIED: EPHEMERIS_FILE_MISSING", c.run_reasons(env, SPEC))


if __name__ == "__main__":
    unittest.main()
