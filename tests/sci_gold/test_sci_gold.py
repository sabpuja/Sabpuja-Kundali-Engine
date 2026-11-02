"""KUN-SCI-GOLD-001 tests: isolated reference rules, TZif reader, matrix/receipt integrity, runner.

Real-data tests follow the existing suite convention: they skip without
SABPUJA_TEST_EPHE_PATH, and with it set they must pass. The live swetest
reproduction test runs when SABPUJA_TEST_SWETEST is also set.
"""
from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
import ast
import copy
import hashlib
import io
import json
import os
import subprocess
import sys
import unittest

from . import asc_formula, reference_rules as rr, swiss_reference as sr, tzif_reference as tzr
from . import run as gold

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
MATRIX = json.loads((HERE / "matrix.json").read_text(encoding="utf-8"))
EPHE = os.environ.get("SABPUJA_TEST_EPHE_PATH")
SWETEST = os.environ.get("SABPUJA_TEST_SWETEST")
RECEIPT = os.environ.get("SABPUJA_TEST_SWETEST_RECEIPT")
ISOLATED = ("reference_rules.py", "tzif_reference.py", "asc_formula.py")
ALLOWED_IMPORTS = {"__future__", "fractions", "math", "re", "struct", "calendar"}


def charts():
    return [f for f in MATRIX["fixtures"] if f["expect"]["kind"] == "chart"]


class IsolationTest(unittest.TestCase):
    def test_reference_modules_import_only_the_standard_library(self):
        for name in ISOLATED:
            tree = ast.parse((HERE / name).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    mods = [a.name.split(".")[0] for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    self.assertEqual(node.level, 0, (name, "relative import"))
                    mods = [node.module.split(".")[0]]
                else:
                    continue
                for mod in mods:
                    self.assertIn(mod, ALLOWED_IMPORTS, (name, mod))
                if isinstance(node, (ast.Call,)):
                    pass
            text = (HERE / name).read_text(encoding="utf-8")
            for banned in ("__import__", "importlib", "sabpuja_kundali", "swisseph", "zoneinfo", "boundary_oracle"):
                self.assertNotIn(banned + "(", text.replace(" ", ""), (name, banned))
                if banned in ("sabpuja_kundali", "swisseph", "zoneinfo"):
                    self.assertFalse(any(line.lstrip().startswith(("import " + banned, "from " + banned))
                                         for line in text.splitlines()), (name, banned))


class ReferenceRulesTest(unittest.TestCase):
    # Hand-derived (classical rule written out): movable signs count from themselves,
    # fixed from the 9th, dual from the 5th; each part is 3 deg 20 min.
    HAND = [
        ("0", "Mesha", "Mesha", ("Ashwini", 1)),            # Mesha part 1 -> Mesha
        ("3.3333333333", "Mesha", "Mesha", ("Ashwini", 1)),  # just below 3 deg 20 min
        ("3.3333333334", "Mesha", "Vrishabha", ("Ashwini", 2)),
        ("13.3333333334", "Mesha", "Simha", ("Bharani", 1)),   # movable: Mesha part 5 -> Simha
        ("33.5", "Vrishabha", "Kumbha", ("Krittika", 3)),     # fixed: from Makara; part 2 -> Kumbha
        ("63.4", "Mithuna", "Vrischika", ("Mrigashira", 4)),  # dual: from Tula; part 2 -> Vrischika
        ("119.99", "Karka", "Meena", ("Ashlesha", 4)),        # movable: Karka part 9 -> Meena
        ("120", "Simha", "Mesha", ("Magha", 1)),              # fixed: from Mesha (9th from Simha)
        ("185", "Tula", "Vrischika", ("Chitra", 4)),          # movable: Tula part 2 -> Vrischika
        ("359.9999999999", "Meena", "Meena", ("Revati", 4)),  # dual: from Karka; part 9 -> Meena
        ("360", "Mesha", "Mesha", ("Ashwini", 1)),            # wrap
        ("-0.0000000001", "Meena", "Meena", ("Revati", 4)),
    ]

    def test_hand_derived_table(self):
        for lon, rashi, d9, nak in self.HAND:
            self.assertEqual((rr.rashi(lon), rr.navamsa(lon), rr.nakshatra(lon)), (rashi, d9, nak), lon)

    def test_two_classical_formulations_and_the_108_part_rule_agree_everywhere(self):
        # Midpoints and both sides of every Pada edge, exactly.
        eps = Fraction(1, 10 ** 12)
        for k in range(108):
            for x in (k * rr.PADA_SPAN, k * rr.PADA_SPAN + rr.PADA_SPAN / 2, (k + 1) * rr.PADA_SPAN - eps):
                self.assertEqual(rr.navamsa_index_parashari(x), rr.navamsa_index_elemental(x))
                self.assertEqual(rr.navamsa_index_parashari(x), k % 12)
                self.assertEqual(rr.nakshatra(x), (rr.NAKSHATRAS[k // 4], k % 4 + 1))

    def test_decimal_text_is_exact(self):
        self.assertEqual(rr.exact("3.33333333333"), Fraction(333333333333, 10 ** 11))
        self.assertEqual(rr.edge_distance("13.33333333333"), Fraction(40, 3) - Fraction(1333333333333, 10 ** 11))
        with self.assertRaises(TypeError):
            rr.exact(True)
        with self.assertRaises(ValueError):
            rr.exact(float("nan"))

    def test_houses(self):
        self.assertEqual(rr.d1_house("10", "355"), 2)     # Mesha body, Meena Lagna
        self.assertEqual(rr.d1_house("355", "10"), 12)
        self.assertEqual(rr.d9_house("0", "3.4"), 12)     # D9 Mesha body, D9 Vrishabha Lagna
        self.assertEqual(rr.ketu("190"), Fraction(10))

    def test_north_indian_geometry(self):
        centres = {1: (0.5, 0.25), 2: (0.25, 0.1), 3: (0.1, 0.25), 4: (0.25, 0.5), 5: (0.1, 0.75), 6: (0.25, 0.9),
                   7: (0.5, 0.75), 8: (0.75, 0.9), 9: (0.9, 0.75), 10: (0.75, 0.5), 11: (0.9, 0.25), 12: (0.75, 0.1)}
        for house, (u, v) in centres.items():
            self.assertEqual(rr.north_indian_house_at(u, v), house)
        self.assertIsNone(rr.north_indian_house_at(0.5, 0.5))   # on both diagonals
        self.assertIsNone(rr.north_indian_house_at(1.2, 0.5))
        self.assertEqual(rr.north_indian_sign_numbers(3)[1], 4)  # Karka Lagna: house 1 shows 4
        self.assertEqual(rr.north_indian_sign_numbers(11)[2], 1)


class TzifReferenceTest(unittest.TestCase):
    def setUp(self):
        import tzdata
        self.dir = Path(tzdata.__file__).resolve().parent / "zoneinfo"

    def offsets(self, zone, wall_text):
        tz = tzr.parse((self.dir / zone).read_bytes())
        wall = datetime.fromisoformat(wall_text).replace(tzinfo=timezone.utc)
        return tzr.local_offsets(tz, int(wall.timestamp()))

    def test_hand_derived_iana_cases(self):
        h = 3600
        cases = [
            ("Asia/Kolkata", "1970-01-01T00:00:00", [19800]),
            ("Asia/Kathmandu", "1985-12-31T23:59:00", [19800]),
            ("Asia/Kathmandu", "1986-01-01T00:10:00", []),            # gap 00:00-00:15
            ("Asia/Kathmandu", "1986-01-01T00:15:00", [20700]),
            ("Asia/Dhaka", "2009-06-19T23:30:00", []),                # gap 23:00-24:00
            ("Asia/Dhaka", "2009-08-01T12:00:00", [7 * h]),
            ("America/New_York", "2026-03-08T02:30:00", []),
            ("America/New_York", "2026-11-01T01:30:00", [-5 * h, -4 * h]),
            ("Europe/London", "2026-03-29T01:30:00", []),
            ("Europe/London", "2026-10-25T01:30:00", [0, h]),
            ("Australia/Sydney", "2026-04-05T02:30:00", [10 * h, 11 * h]),
            ("Australia/Sydney", "2026-10-04T02:30:00", []),
            ("Europe/Helsinki", "2035-12-21T12:00:00", [2 * h]),       # after the table: POSIX footer
            ("America/New_York", "2090-07-04T12:00:00", [-4 * h]),
        ]
        for zone, wall, want in cases:
            self.assertEqual(self.offsets(zone, wall), want, (zone, wall))

    def test_every_chart_fixture_utc_follows_from_its_offset(self):
        for fx in charts():
            text = fx["input"]["birth_datetime"]
            sign, off = text[-6], text[-5:]
            given = (1 if sign == "+" else -1) * (int(off[:2]) * 3600 + int(off[3:]) * 60)
            self.assertIn(given, self.offsets(fx["input"]["timezone"], text[:-6]), fx["id"])
            self.assertTrue(fx["time_reference"]["rule_text"], fx["id"])


class MatrixAndReceiptTest(unittest.TestCase):
    def test_matrix_shape(self):
        ids = [f["id"] for f in MATRIX["fixtures"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 68)
        for f in MATRIX["fixtures"]:
            self.assertIs(f["synthetic"], True)
            self.assertEqual(set(f["input"]), {"birth_datetime", "timezone", "latitude", "longitude"})
            if f["expect"]["kind"] == "refusal":
                self.assertTrue(f["expect"]["code"] and f["expect"]["basis"])
            else:
                self.assertTrue(f["time_reference"]["expected_utc"].endswith("Z"))

    def test_pins_and_receipt_hashes(self):
        pins = json.loads((HERE / "PINS.json").read_text())
        sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
        self.assertEqual(sha(HERE / "matrix.json"), pins["matrix_sha256"])
        self.assertEqual(sha(sr.RECEIPTS / "SHA256SUMS"), pins["receipts_sha256sums_sha256"])
        self.assertEqual(sha(REPO / "tests" / "swiss_conformance" / "spec.json"), pins["swiss_spec_sha256"])
        sums = dict(l.split("  ")[::-1] for l in (sr.RECEIPTS / "SHA256SUMS").read_text().splitlines())
        self.assertEqual(set(sums), {f["id"] + ".txt" for f in charts()})
        for name, digest in sums.items():
            text = (sr.RECEIPTS / name).read_text(encoding="utf-8")
            self.assertEqual(sr.sha256_text(text), digest, name)
            ref = sr.parse(text)
            self.assertEqual(ref["version"], "2.10.03")
            self.assertNotIn("/", "".join(l for l in text.splitlines() if l.startswith("<SWETEST>")).replace("-g,", ""))

    def test_receipt_parser_refuses_tampering(self):
        text = (sr.RECEIPTS / "GOLD-T01.txt").read_text(encoding="utf-8")
        for bad in (text.replace("## RUN D exit=0", "## RUN D exit=1"), text.replace("(Lahiri)", "(Fagan/Bradley)"),
                    text.replace("version 2.10.03", "version 2.10.02"), text + "warning: using Moshier eph.\n",
                    text.replace("Moon           ,", "Mon            ,")):
            with self.assertRaises(sr.ReceiptError):
                sr.parse(bad)

    def test_exact_julian_day(self):
        self.assertEqual(sr.exact_jd("2000-01-01T12:00:00Z"), Fraction(2451545))
        self.assertEqual(sr.exact_jd("1970-01-01T00:00:00Z"), Fraction(4881175, 2))
        self.assertEqual(sr.jd_double("2024-02-28T18:30:00.000001Z"), float(Fraction(4920737, 2) + Fraction(66600000001, 86400000000)))  # 2024-02-28 0h UT = JD 2460368.5

    def test_lagna_formula_reproduces_swetest_on_every_receipt(self):
        # A self-test of the reference formula (catches a quadrant or sign error), not a scientific tolerance.
        for fx in charts():
            ref = sr.parse((sr.RECEIPTS / f"{fx['id']}.txt").read_text(encoding="utf-8"))
            calc = asc_formula.sidereal_ascendant(float(ref["armc"]), float(ref["eps_true"]), fx["input"]["latitude"],
                                                  float(ref["ayanamsa"]))
            self.assertLess(abs(float(rr.circular_diff(Fraction(calc), rr.exact(ref["ascendant"])))), 1e-6, fx["id"])


class BoundaryDesignTest(unittest.TestCase):
    """Each a/b boundary pair straddles its edge in the swetest reference (design intent, receipts only)."""

    def test_pairs_straddle_their_edge(self):
        fixtures = {f["id"]: f for f in MATRIX["fixtures"]}
        pairs = sorted({i[:-1] for i in fixtures if i.startswith("GOLD-B")})
        self.assertEqual(len(pairs), 10)
        for stem in pairs:
            body = fixtures[stem + "a"]["focus"][0]
            cats = []
            for side in "ab":
                exp = gold.reference_chart(sr.parse((sr.RECEIPTS / f"{stem}{side}.txt").read_text(encoding="utf-8")))
                x = exp["lagna"]["longitude"] if body == "lagna" else exp["planets"][body]["longitude"]
                cats.append((rr.rashi(x), rr.nakshatra(x), rr.navamsa(x)))
                self.assertGreater(rr.edge_distance(x), Fraction(1, 10 ** 5), (stem, side))  # decidable, far above 1e-9
            self.assertNotEqual(cats[0], cats[1], stem)
            # Rashi edges change the Rashi; the 3 deg 20 min and 196 deg 40 min edges change only Pada/D9.
            if stem in ("GOLD-B03", "GOLD-B07"):
                self.assertEqual(cats[0][0], cats[1][0], stem)
            else:
                self.assertNotEqual(cats[0][0] if stem != "GOLD-B02" else cats[0][1][0], cats[1][0] if stem != "GOLD-B02" else cats[1][1][0], stem)

    def test_exact_edge_fixture_is_within_the_frozen_band(self):
        exp = gold.reference_chart(sr.parse((sr.RECEIPTS / "GOLD-E01.txt").read_text(encoding="utf-8")))
        self.assertLessEqual(rr.edge_distance(exp["planets"]["moon"]["longitude"]), Fraction(1, 10 ** 9))


class LayerMutationTest(unittest.TestCase):
    """The comparison layers must detect a wrong engine value (no vacuous PASS)."""

    @classmethod
    def setUpClass(cls):
        cls.fx = next(f for f in MATRIX["fixtures"] if f["id"] == "GOLD-T03")
        cls.ref = sr.parse((sr.RECEIPTS / "GOLD-T03.txt").read_text(encoding="utf-8"))
        cls.exp = gold.reference_chart(cls.ref)
        cls.tol, _ = gold.frozen_tolerances()
        # A synthetic "engine" output assembled from the reference itself (PASS by construction).
        e = cls.exp
        planets = {b: {"longitude_deg": round(float(e["planets"][b]["longitude"]) % 360, 8),
                       **{k: e["planets"][b][k] for k in ("rashi", "navamsa_rashi", "whole_sign_house", "navamsa_whole_sign_house")}}
                   for b in gold.BODIES}
        cls.good = {"lagna": {"longitude_deg": round(float(e["lagna"]["longitude"]), 8), "rashi": e["lagna"]["rashi"],
                              "navamsa_rashi": e["lagna"]["navamsa_rashi"]}, "planets": planets,
                    "moon_nakshatra": {"name": e["moon_nakshatra"][0], "pada": e["moon_nakshatra"][1]},
                    "d9": {"lagna_rashi": e["lagna"]["navamsa_rashi"], "houses": copy.deepcopy(e["d9_houses"])},
                    "birth": {"utc": cls.fx["time_reference"]["expected_utc"]}}

    def classes(self, rows):
        return {r["classification"] for r in rows}

    def test_constructed_output_passes(self):
        self.assertEqual(self.classes(gold.rules_layer(self.fx, self.good, self.exp, self.tol)), {"PASS"})
        self.assertEqual(self.classes(gold.swiss_layer(self.fx, self.good, self.ref, self.exp, self.tol)), {"SWISS-CONFORMANCE PASS"})

    def test_wrong_d9_sign_fails(self):
        bad = copy.deepcopy(self.good)
        p = bad["planets"]["venus"]
        p["navamsa_rashi"] = rr.RASHIS[(rr.RASHIS.index(p["navamsa_rashi"]) + 1) % 12]
        self.assertIn("FAIL", self.classes(gold.rules_layer(self.fx, bad, self.exp, self.tol)))

    def test_wrong_d9_house_list_fails(self):
        bad = copy.deepcopy(self.good)
        bad["d9"]["houses"][0], bad["d9"]["houses"][1] = bad["d9"]["houses"][1], bad["d9"]["houses"][0]
        self.assertIn("FAIL", self.classes(gold.rules_layer(self.fx, bad, self.exp, self.tol)))

    def test_longitude_beyond_frozen_tolerance_fails(self):
        bad = copy.deepcopy(self.good)
        bad["planets"]["moon"]["longitude_deg"] += 2e-8
        self.assertIn("SWISS-CONFORMANCE FAIL", self.classes(gold.swiss_layer(self.fx, bad, self.ref, self.exp, self.tol)))

    def test_ketu_not_opposite_fails(self):
        bad = copy.deepcopy(self.good)
        bad["planets"]["ketu_mean"]["longitude_deg"] = round((bad["planets"]["ketu_mean"]["longitude_deg"] + 1e-7) % 360, 8)
        self.assertIn("SWISS-CONFORMANCE FAIL", self.classes(gold.swiss_layer(self.fx, bad, self.ref, self.exp, self.tol)))


@unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH not set")
class RealDataRunTest(unittest.TestCase):
    def test_committed_receipts_run(self):
        report = gold.run_all(EPHE, SWETEST, RECEIPT)
        bad = [(r["id"], r["classification"]) for r in report["results"] if r["classification"] not in ("PASS", "QUALIFIED")]
        self.assertEqual(bad, [("GOLD-E01", "BOUNDARY-INDETERMINATE")])
        self.assertEqual(report["fixture_counts"], {"PASS": 49, "QUALIFIED": 18, "BOUNDARY-INDETERMINATE": 1})
        self.assertTrue(all(r["layers"][-1]["classification"] == "BLOCKED" or r["expect"]["kind"] == "refusal"
                            for r in report["results"] if r["layers"][-1]["layer"] == "ASTRO"))
        if SWETEST:
            self.assertEqual(report["environment"]["live_swetest"]["reproduced"], 50)
            self.assertEqual(report["environment"]["live_swetest"]["receipt_errors"], [])

    def test_builder_is_deterministic(self):
        env = dict(os.environ, SABPUJA_EPHE_PATH=EPHE)
        env.pop("SE_EPHE_PATH", None)
        out = subprocess.run([sys.executable, str(HERE / "design" / "build_matrix.py")], capture_output=True, env=env,
                             check=True, timeout=600)
        self.assertEqual(out.stdout, (HERE / "matrix.json").read_bytes())


def _quiet_main(argv):
    """Run the CLI with stdout captured; return (exit code, report dict)."""
    import contextlib
    import glob
    import tempfile
    out_dir = tempfile.mkdtemp()
    with contextlib.redirect_stdout(io.StringIO()):
        code = gold.main(list(argv) + ["--report-dir", out_dir])
    (path,) = glob.glob(os.path.join(out_dir, "sci-gold-*.json"))
    return code, json.loads(Path(path).read_text(encoding="utf-8"))


class InputReadinessTest(unittest.TestCase):
    """QA review 5737049196: missing/unverified inputs are BLOCKED, never FAIL; real mismatches still FAIL."""

    def setUp(self):
        self._env = {k: os.environ.pop(k) for k in ("SE_EPHE_PATH", "SABPUJA_TEST_EPHE_PATH") if k in os.environ}

    def tearDown(self):
        os.environ.update(self._env)

    def assert_blocked_not_fail(self, report, reason_prefix):
        counts = report["fixture_counts"]
        self.assertNotIn("FAIL", counts)
        self.assertNotIn("METHOD-MISMATCH", counts)
        self.assertEqual(counts, {"BLOCKED": 50, "PASS": 18})
        self.assertEqual(report["verdict_verified_layers"], "BLOCKED")
        self.assertTrue(any(r.startswith(reason_prefix) for r in report["run_blocking_reasons"]), report["run_blocking_reasons"])
        for r in report["results"]:
            if r["expect"]["kind"] == "chart":
                self.assertTrue(r["notes"] and r["notes"][-1].startswith("BLOCKED: comparison not decidable"))

    def test_missing_ephe_argument_is_structured_blocked(self):
        code, report = _quiet_main([])
        self.assertEqual(code, 2)
        self.assert_blocked_not_fail(report, "EPHEMERIS_UNVERIFIED:EPHEMERIS_PATH_MISSING")

    def test_empty_ephemeris_directory_is_blocked(self):
        import tempfile
        code, report = _quiet_main(["--ephe", tempfile.mkdtemp()])
        self.assertEqual(code, 2)
        self.assert_blocked_not_fail(report, "EPHEMERIS_UNVERIFIED:EPHEMERIS_FILE_MISSING")

    def test_invalid_pinned_files_are_blocked(self):
        import tempfile
        sys.path.insert(0, str(REPO / "src"))
        from sabpuja_kundali.ephemeris import load_manifest
        bad = Path(tempfile.mkdtemp())
        for entry in load_manifest()["files"]:
            (bad / entry["name"]).write_bytes(b"not the pinned file")
        code, report = _quiet_main(["--ephe", str(bad)])
        self.assertEqual(code, 2)
        self.assert_blocked_not_fail(report, "EPHEMERIS_UNVERIFIED:EPHEMERIS_FILE_MISMATCH")

    def test_corrupt_manifest_is_blocked(self):
        import tempfile
        from unittest import mock
        sys.path.insert(0, str(REPO / "src"))
        from sabpuja_kundali import engine, ephemeris  # import engine first so its own binding is patched below
        corrupt = ephemeris.EphemerisDataError("EPHEMERIS_MANIFEST_INVALID", "corrupt (test)")
        with mock.patch.object(ephemeris, "load_manifest", side_effect=corrupt), \
                mock.patch.object(engine, "load_ephemeris_manifest", side_effect=corrupt):
            code, report = _quiet_main(["--ephe", EPHE or tempfile.mkdtemp()])
        self.assertEqual(code, 2)
        self.assert_blocked_not_fail(report, "EPHEMERIS_UNVERIFIED:EPHEMERIS_MANIFEST_INVALID")

    def test_missing_swetest_binary_is_structured(self):
        import tempfile
        code, report = _quiet_main(["--ephe", EPHE or tempfile.mkdtemp(), "--swetest", "/nonexistent/swetest"])
        self.assertEqual(code, 2)
        self.assertIn("SWETEST_BINARY_MISSING", report["run_blocking_reasons"])
        self.assertNotIn("FAIL", report["fixture_counts"])

    @unittest.skipUnless(EPHE and SWETEST, "SABPUJA_TEST_EPHE_PATH and SABPUJA_TEST_SWETEST not set")
    def test_missing_or_corrupt_swetest_build_receipt_is_blocked(self):
        import tempfile
        corrupt = Path(tempfile.mkdtemp()) / "receipt.json"
        corrupt.write_text("{not json", encoding="utf-8")
        for receipt, reason in ((None, "SWETEST_BUILD_RECEIPT_MISSING"), (str(corrupt), "SWETEST_BUILD_RECEIPT_INVALID")):
            report = gold.run_all(EPHE, SWETEST, receipt)
            self.assertIn(reason, report["run_blocking_reasons"])
            self.assertEqual(report["verdict_verified_layers"], "BLOCKED")
            self.assertNotIn("FAIL", report["fixture_counts"])

    @unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH not set")
    def test_missing_committed_receipt_blocks_only_that_fixture(self):
        import shutil
        import tempfile
        from unittest import mock
        copy_dir = Path(tempfile.mkdtemp()) / "receipts"
        shutil.copytree(sr.RECEIPTS, copy_dir)
        (copy_dir / "GOLD-T01.txt").unlink()
        with mock.patch.object(sr, "RECEIPTS", copy_dir):
            report = gold.run_all(EPHE, None, None)
        by_id = {r["id"]: r for r in report["results"]}
        self.assertEqual(by_id["GOLD-T01"]["classification"], "BLOCKED")
        self.assertIn("RECEIPT_FILE_MISSING", by_id["GOLD-T01"]["layers"][-1]["reason"])
        self.assertEqual(report["fixture_counts"], {"BLOCKED": 1, "PASS": 48, "QUALIFIED": 18, "BOUNDARY-INDETERMINATE": 1})

    @unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH not set")
    def test_missing_individual_se1_file_is_blocked(self):
        import shutil
        import tempfile
        sys.path.insert(0, str(REPO / "src"))
        from sabpuja_kundali.ephemeris import load_manifest
        names = [e["name"] for e in load_manifest()["files"] if e.get("required")]
        self.assertGreaterEqual(len(names), 2)
        partial = Path(tempfile.mkdtemp())
        shutil.copy(Path(EPHE) / names[0], partial / names[0])   # every other required file is absent
        code, report = _quiet_main(["--ephe", str(partial)])
        self.assertEqual(code, 2)
        self.assert_blocked_not_fail(report, "EPHEMERIS_UNVERIFIED:EPHEMERIS_FILE_MISSING")

    @unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH not set")
    def test_same_size_wrong_checksum_is_blocked(self):
        import shutil
        import tempfile
        sys.path.insert(0, str(REPO / "src"))
        from sabpuja_kundali.ephemeris import load_manifest
        names = [e["name"] for e in load_manifest()["files"] if e.get("required")]
        flipped = Path(tempfile.mkdtemp())
        for n in names:
            shutil.copy(Path(EPHE) / n, flipped / n)
        data = bytearray((flipped / names[-1]).read_bytes())
        data[len(data) // 2] ^= 0x01                                 # same size, one bit different
        (flipped / names[-1]).write_bytes(bytes(data))
        code, report = _quiet_main(["--ephe", str(flipped)])
        self.assertEqual(code, 2)
        self.assert_blocked_not_fail(report, "EPHEMERIS_UNVERIFIED:EPHEMERIS_FILE_MISMATCH")

    @unittest.skipUnless(EPHE and SWETEST and RECEIPT, "pinned ephemeris, swetest and its build receipt not set")
    def test_mismatched_build_receipt_blocks_live_reproduction(self):
        import tempfile
        rec = json.loads(Path(RECEIPT).read_text(encoding="utf-8"))
        rec["swetest_sha256"] = "0" * 64
        wrong = Path(tempfile.mkdtemp()) / "receipt.json"
        wrong.write_text(json.dumps(rec), encoding="utf-8")
        code, report = _quiet_main(["--ephe", EPHE, "--swetest", SWETEST, "--receipt", str(wrong)])
        self.assertEqual(code, 2)
        live = report["environment"]["live_swetest"]
        self.assertIn("SWETEST_BUILD_RECEIPT_MISMATCH", live["receipt_errors"])
        self.assertEqual((live["reproduction"], live["reproduced"]), ("BLOCKED", 0))
        self.assertEqual(report["verdict_verified_layers"], "BLOCKED")
        self.assertNotIn("FAIL", report["fixture_counts"])

    def _receipt_copy(self):
        import shutil
        import tempfile
        copy_dir = Path(tempfile.mkdtemp()) / "receipts"
        shutil.copytree(sr.RECEIPTS, copy_dir)
        return copy_dir

    @unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH not set")
    def test_tampered_reference_receipt_blocks_that_fixture(self):
        from unittest import mock
        copy_dir = self._receipt_copy()
        path = copy_dir / "GOLD-T01.txt"
        text = path.read_text(encoding="utf-8")
        i = next(i for i, ch in enumerate(text) if ch.isdigit() and i > text.index("## RUN A"))
        path.write_text(text[:i] + str((int(text[i]) + 1) % 10) + text[i + 1:], encoding="utf-8")
        with mock.patch.object(sr, "RECEIPTS", copy_dir):
            report = gold.run_all(EPHE, None, None)
        t01 = next(r for r in report["results"] if r["id"] == "GOLD-T01")
        self.assertEqual(t01["classification"], "BLOCKED")
        self.assertIn("RECEIPT_HASH_MISMATCH", t01["layers"][-1]["reason"])
        self.assertEqual(report["fixture_counts"], {"BLOCKED": 1, "PASS": 48, "QUALIFIED": 18, "BOUNDARY-INDETERMINATE": 1})

    @unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH not set")
    def test_incorrect_or_missing_receipt_hash_blocks_every_chart(self):
        from unittest import mock
        for mode in ("wrong", "missing"):
            copy_dir = self._receipt_copy()
            lines = (copy_dir / "SHA256SUMS").read_text(encoding="utf-8").splitlines()
            j = next(k for k, line in enumerate(lines) if line.endswith("GOLD-T02.txt"))
            if mode == "wrong":
                lines[j] = ("f" if lines[j][0] != "f" else "e") + lines[j][1:]
            else:
                del lines[j]
            (copy_dir / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")
            with mock.patch.object(sr, "RECEIPTS", copy_dir):
                report = gold.run_all(EPHE, None, None)
            self.assert_blocked_not_fail(report, "RECEIPT_SUMS_SHA256_MISMATCH")
            t02 = next(r for r in report["results"] if r["id"] == "GOLD-T02")
            self.assertIn("RECEIPT_HASH_MISMATCH", t02["layers"][-1]["reason"])

    def test_receipt_sums_loader_fails_closed(self):
        import tempfile
        good = (sr.RECEIPTS / "SHA256SUMS").read_bytes()
        raw, sums, errors = gold.load_receipt_sums(sr.RECEIPTS / "SHA256SUMS")
        self.assertEqual((raw, errors, len(sums)), (good, [], 50))
        d = Path(tempfile.mkdtemp())
        lines = good.decode().splitlines()
        cases = {
            "missing": None,
            "not-utf8": b"\xff\xfe\x00",
            "empty": b"",
            "malformed-row": ("\n".join(lines[:5] + ["not a sha256 line"] + lines[5:]) + "\n").encode(),
            "short-hash": ("\n".join([lines[0][1:]] + lines[1:]) + "\n").encode(),
            "one-space": ("\n".join([lines[0].replace("  ", " ")] + lines[1:]) + "\n").encode(),
            "duplicate-name": ("\n".join(lines + [lines[0]]) + "\n").encode(),
        }
        expected = {"missing": "RECEIPT_SUMS_MISSING", "not-utf8": "RECEIPT_SUMS_NOT_UTF8"}
        for name, data in cases.items():
            path = d / name
            if data is not None:
                path.write_bytes(data)
            _, sums, errors = gold.load_receipt_sums(path)
            self.assertEqual((errors, sums), ([expected.get(name, "RECEIPT_SUMS_MALFORMED")], {}), name)

    @unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH not set")
    def test_missing_unreadable_or_malformed_receipt_sums_file_is_blocked(self):
        from unittest import mock
        for mode, reason in (("missing", "RECEIPT_SUMS_MISSING"), ("not-utf8", "RECEIPT_SUMS_NOT_UTF8"),
                             ("malformed-row", "RECEIPT_SUMS_MALFORMED")):
            copy_dir = self._receipt_copy()
            sums = copy_dir / "SHA256SUMS"
            if mode == "missing":
                sums.unlink()
            elif mode == "not-utf8":
                sums.write_bytes(b"\xff\xfe\x00")
            else:
                lines = sums.read_text(encoding="utf-8").splitlines()
                sums.write_text("\n".join(lines[:3] + ["GOLD-T04.txt " + "0" * 64] + lines[4:]) + "\n", encoding="utf-8")
            with mock.patch.object(sr, "RECEIPTS", copy_dir):
                code, report = _quiet_main(["--ephe", EPHE])
            self.assertEqual(code, 2, mode)
            self.assert_blocked_not_fail(report, reason)

    @unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH not set")
    def test_real_mismatches_with_verified_inputs_still_fail(self):
        from unittest import mock
        sys.path.insert(0, str(REPO / "src"))
        from sabpuja_kundali import engine
        real = engine.calculate
        inputs = {f["id"]: f["input"] for f in MATRIX["fixtures"]}

        def injected(payload, ephe):
            out = real(payload, ephe)
            if payload == inputs["GOLD-T01"]:                  # longitude beyond the frozen 1e-8 deg tolerance
                out["planets"]["moon"]["longitude_deg"] = round((out["planets"]["moon"]["longitude_deg"] + 1e-6) % 360, 8)
            if payload == inputs["GOLD-T02"]:                  # wrong D9 whole-sign house
                p = out["planets"]["saturn"]
                p["navamsa_whole_sign_house"] = p["navamsa_whole_sign_house"] % 12 + 1
            if payload == inputs["GOLD-T03"]:                  # wrong D9 sign
                p = out["planets"]["venus"]
                p["navamsa_rashi"] = rr.RASHIS[(rr.RASHIS.index(p["navamsa_rashi"]) + 1) % 12]
            if payload == inputs["GOLD-T05"]:                  # method incompatibility (ayanamsha mode)
                out["calculation_metadata"]["conventions"]["ayanamsa"]["swiss_mode_number"] = 3
            if payload == inputs["GOLD-T04"]:                  # engine refusal with verified inputs
                raise engine.ChartComputationError("SWISS_CALC_FAILED", "injected (test)")
            return out

        with mock.patch.object(engine, "calculate", side_effect=injected):
            code, report = _quiet_main(["--ephe", EPHE])
        by_id = {r["id"]: r for r in report["results"]}
        layers = lambda fid: {(l["layer"], l["classification"]) for l in by_id[fid]["layers"]}
        self.assertIn(("SWISS", "SWISS-CONFORMANCE FAIL"), layers("GOLD-T01"))
        self.assertTrue(any(l["layer"] == "RULES" and l["classification"] == "FAIL" and "navamsa_whole_sign_house" in l["field"]
                            for l in by_id["GOLD-T02"]["layers"]))
        self.assertEqual(by_id["GOLD-T01"]["classification"], "SWISS-CONFORMANCE FAIL")
        for fid in ("GOLD-T02", "GOLD-T03", "GOLD-T04"):
            self.assertEqual(by_id[fid]["classification"], "FAIL", fid)
        self.assertEqual(by_id["GOLD-T05"]["classification"], "METHOD-MISMATCH")
        self.assertEqual(report["verdict_verified_layers"], "FAIL")
        self.assertEqual(code, 1)

    @unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH not set")
    def test_a_lone_swiss_longitude_mismatch_fails_the_run(self):
        from unittest import mock
        sys.path.insert(0, str(REPO / "src"))
        from sabpuja_kundali import engine
        real = engine.calculate
        target = next(f["input"] for f in MATRIX["fixtures"] if f["id"] == "GOLD-T01")

        def injected(payload, ephe):
            out = real(payload, ephe)
            if payload == target:
                out["planets"]["mars"]["longitude_deg"] = round((out["planets"]["mars"]["longitude_deg"] + 2e-8) % 360, 8)
            return out

        with mock.patch.object(engine, "calculate", side_effect=injected):
            code, report = _quiet_main(["--ephe", EPHE])
        self.assertEqual(report["fixture_counts"].get("SWISS-CONFORMANCE FAIL"), 1)
        self.assertEqual(report["verdict_verified_layers"], "FAIL")
        self.assertEqual(code, 1)

    @unittest.skipUnless(EPHE, "SABPUJA_TEST_EPHE_PATH not set")
    def test_verified_run_keeps_boundary_qualified_and_blocked_layers(self):
        code, report = _quiet_main(["--ephe", EPHE])
        self.assertEqual(code, 2)
        self.assertEqual(report["verdict_verified_layers"], "BOUNDARY-INDETERMINATE")
        self.assertEqual(report["fixture_counts"], {"PASS": 49, "QUALIFIED": 18, "BOUNDARY-INDETERMINATE": 1})
        e01 = next(r for r in report["results"] if r["id"] == "GOLD-E01")
        self.assertEqual(e01["classification"], "BOUNDARY-INDETERMINATE")
        self.assertEqual(sum(1 for l in e01["layers"] if l["classification"] == "BOUNDARY-INDETERMINATE"), 6)
        self.assertNotIn("FAIL", {l["classification"] for l in e01["layers"]})
        for r in report["results"]:
            if r["expect"]["kind"] == "chart":
                by_layer = {l["layer"]: l["classification"] for l in r["layers"]}
                self.assertEqual((by_layer["ASTRO"], by_layer["LAGNA-F"]), ("BLOCKED", "BLOCKED"))


if __name__ == "__main__":
    unittest.main()
