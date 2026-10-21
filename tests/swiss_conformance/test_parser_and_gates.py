"""swetest output parsing, provenance gates and comparison logic (no Swiss data or swetest needed)."""
from fractions import Fraction
from pathlib import Path
from unittest import mock
import json
import os
import stat
import sys
import tempfile
import textwrap
import unittest

from . import conformance as c
from . import swetest_cli as cli

ECHO = "<SWETEST> -edir<EPHE> -bj2451545.0 -ut -sid1 -i65538 -p0123456m -fPl -ep -g, "
GOOD = ECHO + """
date (dmy) 1.1.2000 greg.   12:00:00 UT\t\tversion 2.10.03
UT:  2451545.000000000     delta t: 63.828915 sec
TT:  2451545.000738760   ayanamsa =   23°51'11.60094970 (Lahiri)
Epsilon (m)       23°26'21.40599805
Sun            , 256.51569618387
Moon           , 199.47052896032
mean Node      , 101.18742357059
"""


def env_ok(**over):
    env = {"python": "3", "platform": "x", "git": {"commit": "a" * 40, "dirty": False},
           "binding": {"pyswisseph": "2.10.3.2", "swiss_library": "2.10.03"},
           "ephemeris": {"verified": True, "error_code": None, "manifest_version": "1", "source_commit": "c", "files": {}},
           "swetest": {"present": True, "sha256": "f" * 64, "receipt": {}, "receipt_errors": []}}
    env.update(over)
    return env


SPEC = c.load_json(c.HERE / "spec.json")


class Parser(unittest.TestCase):
    def test_good_output(self):
        version, ut, aya, values, warnings = cli.parse(GOOD, ECHO)
        self.assertEqual((version, ut, aya, warnings), ("2.10.03", 2451545.0, "Lahiri", []))
        self.assertEqual(values, {"Sun": 256.51569618387, "Moon": 199.47052896032, "mean Node": 101.18742357059})

    def test_house_names_with_punctuation(self):
        text = GOOD + "house  1       , 76.32320044476\nco-Asc. W.Koch , 51.86374944972\nAscendant      , 76.32320044476\n"
        values = cli.parse(text, ECHO)[3]
        self.assertEqual(values["house 1"], 76.32320044476)
        self.assertIn("co-Asc. W.Koch", values)

    def test_moshier_fallback_and_errors_are_surfaced(self):
        text = GOOD + "\nwarning: SwissEph file 'sepl_18.se1' not found in PATH '<EPHE>/' \nusing Moshier eph.; \n"
        warnings = cli.parse(text, ECHO)[4]
        self.assertEqual(len(warnings), 2)
        self.assertIn("Moshier", warnings[1])
        text = GOOD + "error: House method Placidus failed, Porphyry calculated instead\n"
        self.assertEqual(cli.parse(text, ECHO)[4], ["error: House method Placidus failed, Porphyry calculated instead"])

    def test_malformed_outputs_raise(self):
        bad = {
            "wrong echo": GOOD.replace("-sid1", "-sid3", 1),
            "unknown line": GOOD + "something unexpected\n",
            "seven decimals": GOOD.replace("256.51569618387", "256.5156962"),
            "duplicate": GOOD + "Sun            , 256.51569618387\n",
            "no version": GOOD.replace("version 2.10.03", "release"),
            "no UT line": GOOD.replace("UT:  2451545.000000000", "UT?"),
            "non-number": GOOD.replace("256.51569618387", "nan"),
            "empty": "",
        }
        for label, text in bad.items():
            with self.subTest(label=label):
                with self.assertRaises(cli.SwetestOutputError) as ctx:
                    cli.parse(text, ECHO)
                self.assertNotIn("256.5", str(ctx.exception))  # raw output never echoed in the reason

    def test_argv_matches_spec_and_jd_round_trips(self):
        jd = 2461339.0780010265
        self.assertEqual(cli.jd_arg(jd), "-bj2461339.0780010265")
        self.assertEqual(float(cli.jd_arg(jd)[3:]), jd)
        planets = cli.planet_argv("S", "E", jd)
        houses = cli.house_argv("S", "E", jd, 28.6139, 77.209)
        spec = SPEC["swetest_switches"]
        self.assertEqual(planets[3:], spec["planets"][2:])
        self.assertEqual(houses[3:-1], spec["houses"][2:-1])
        self.assertEqual(houses[-1], "-house77.209,28.6139,P")

    def test_redaction(self):
        text = "/opt/x/swetest -edir/data/ephe/ ... PATH '/data/ephe/'"
        self.assertEqual(cli.redact(text, "/opt/x/swetest", "/data/ephe"), "<SWETEST> -edir<EPHE>/ ... PATH '<EPHE>/'")


class FakeSwetest(unittest.TestCase):
    """A stand-in executable proves run() and the case logic fail closed on bad process results."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp)

    def fake(self, body: str, code: int = 0) -> str:
        path = self.tmp / "swetest"
        path.write_text(f"#!{sys.executable}\nimport sys\n" + textwrap.dedent(body) + f"\nsys.exit({code})\n",
                        encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
        return str(path)

    def test_nonzero_exit_is_not_parsed(self):
        exe = self.fake("print('boom')", code=3)
        result = cli.run([exe, "-x"], str(self.tmp))
        self.assertEqual(result.exit_code, 3)
        self.assertEqual(result.values, {})

    def test_echo_mismatch_and_moshier_through_swetest_pair(self):
        exe = self.fake("print('not the echo')")
        values, receipts, problems, uts = c.swetest_pair(exe, str(self.tmp), 2451545.0, 0.0, 0.0)
        self.assertEqual(values, {})
        self.assertTrue(all(p.startswith("SWETEST_OUTPUT_MALFORMED") for p in problems), problems)
        exe = self.fake("""
            print(' '.join(sys.argv).replace(sys.argv[0], '<SWETEST>').replace(%r, '<EPHE>') + ' ')
            print('date (dmy) 1.1.2000 greg.   12:00:00 UT\\t\\tversion 2.10.03')
            print('UT:  2451545.000000000     delta t: 63.828915 sec')
            print('Sun            , 256.51569718931')
            print("warning: SwissEph file 'sepl_18.se1' not found in PATH '%s/'")
            print('using Moshier eph.; ')
        """ % (str(self.tmp), str(self.tmp)))
        values, receipts, problems, uts = c.swetest_pair(exe, str(self.tmp), 2451545.0, 0.0, 0.0)
        self.assertTrue(any("Moshier" in p for p in problems), problems)
        self.assertNotIn(str(self.tmp), json.dumps(receipts))

    def test_missing_executable(self):
        values, receipts, problems, uts = c.swetest_pair(str(self.tmp / "absent"), str(self.tmp), 2451545.0, 0.0, 0.0)
        self.assertEqual(problems, ["SWETEST_NOT_RUN: FileNotFoundError"] * 2)


class Gates(unittest.TestCase):
    def test_clean_env_has_no_reasons(self):
        self.assertEqual(c.run_reasons(env_ok(), SPEC), [])

    def test_each_problem_blocks(self):
        cases = {
            "DIRTY_TREE": env_ok(git={"commit": "a" * 40, "dirty": True}),
            "GIT_UNAVAILABLE": env_ok(git={"commit": None, "dirty": None}),
            "BINDING_VERSION_MISMATCH": env_ok(binding={"pyswisseph": "2.10.3.1", "swiss_library": "2.10.03"}),
            "EPHEMERIS_UNVERIFIED: EPHEMERIS_FILE_MISSING": env_ok(ephemeris={"verified": False, "error_code": "EPHEMERIS_FILE_MISSING", "files": {}}),
            "SWETEST_MISSING": env_ok(swetest={"present": False, "sha256": None, "receipt": None, "receipt_errors": []}),
            "SWETEST_BUILD_RECEIPT_MISMATCH": env_ok(swetest={"present": True, "sha256": "f" * 64, "receipt": {},
                                                              "receipt_errors": ["SWETEST_BUILD_RECEIPT_MISMATCH"]}),
        }
        for reason, env in cases.items():
            with self.subTest(reason=reason):
                self.assertEqual(c.run_reasons(env, SPEC), [reason])
        with mock.patch.dict(os.environ, {"SE_EPHE_PATH": "/x"}):
            self.assertEqual(c.run_reasons(env_ok(), SPEC), ["SE_EPHE_PATH_SET"])

    def test_receipt_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / "swetest"
            exe.write_bytes(b"binary")
            exe.chmod(0o755)
            sha = cli.sha256_file(exe)
            self.assertEqual(c.swetest_state(str(exe), None)["receipt_errors"], ["SWETEST_BUILD_RECEIPT_MISSING"])
            receipt = Path(tmp) / "r.json"
            receipt.write_text("{", encoding="utf-8")
            self.assertEqual(c.swetest_state(str(exe), str(receipt))["receipt_errors"], ["SWETEST_BUILD_RECEIPT_INVALID"])
            good = {"swetest_sha256": sha, "source_repository": "r", "source_commit": "c", "build_command": "b", "compiler": "g"}
            receipt.write_text(json.dumps(good), encoding="utf-8")
            self.assertEqual(c.swetest_state(str(exe), str(receipt))["receipt_errors"], [])
            receipt.write_text(json.dumps({**good, "swetest_sha256": "0" * 64}), encoding="utf-8")
            self.assertEqual(c.swetest_state(str(exe), str(receipt))["receipt_errors"], ["SWETEST_BUILD_RECEIPT_MISMATCH"])
            exe.chmod(0o644)
            self.assertFalse(c.swetest_state(str(exe), str(receipt))["present"])

    def test_blocked_run_executes_no_case(self):
        with mock.patch.object(c, "run_case", side_effect=AssertionError("must not run")):
            report = c.run_all(None, None, None, env=env_ok(git={"commit": None, "dirty": None}))
        self.assertEqual((report["verdict"], report["exit_code"], report["cases"]), ("SWISS-CONFORMANCE BLOCKED", 2, []))


class ComparisonLogic(unittest.TestCase):
    def test_overall(self):
        self.assertEqual(c.overall([]), c.BLOCKED)
        self.assertEqual(c.overall([c.PASS, c.PASS]), c.PASS)
        self.assertEqual(c.overall([c.PASS, c.INDETERMINATE]), c.BLOCKED)
        self.assertEqual(c.overall([c.BLOCKED, c.FAIL]), c.FAIL)

    def test_numeric_wraps_through_zero(self):
        record = c.numeric("X", "engine_vs_swetest_deg", "moon", 359.999999995, 0.0, 1e-8)
        self.assertAlmostEqual(record["diff"], -5e-9, places=14)
        self.assertEqual(record["outcome"], c.PASS)
        self.assertEqual(c.numeric("X", "engine_vs_swetest_deg", "moon", 0.0, 359.9999999, 1e-8)["outcome"], c.FAIL)
        self.assertEqual(c.numeric("X", "engine_vs_swetest_deg", "moon", None, 1.0, 1e-8)["outcome"], c.BLOCKED)

    def test_category_rule(self):
        from . import oracle
        edge = 30.0
        resolved = c.category("X", "q", "Mesha", oracle.rashi, (29.9999999999,), (29.99999999999,), True)
        self.assertEqual(resolved["outcome"], c.PASS)
        wrong = c.category("X", "q", "Vrishabha", oracle.rashi, (29.9999999999,), (29.99999999999,), True)
        self.assertEqual(wrong["outcome"], c.FAIL)
        split = c.category("X", "q", "Mesha", oracle.rashi, (edge,), (29.99999999999,), True)
        self.assertEqual(split["outcome"], c.INDETERMINATE)
        far_split = c.category("X", "q", "Mesha", oracle.rashi, (45.0,), (15.0,), False)
        self.assertEqual(far_split["outcome"], c.FAIL)


if __name__ == "__main__":
    unittest.main()
