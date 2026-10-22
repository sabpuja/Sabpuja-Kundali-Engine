"""KUN-02 scientific probes as tests. Synthetic data only; no production code is changed.

Civil-time cases need no ephemeris data and always run. Probes that call Swiss
Ephemeris skip only when SABPUJA_TEST_EPHE_PATH is unset; once it is set, wrong
or missing pinned files fail the class instead of skipping.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sabpuja_kundali.engine import calculate
from sabpuja_kundali.ephemeris import EphemerisDataError, verify_ephemeris_dir

from . import envelope_probe, lagna_probe, run, time_probe
from .common import DATA_ENV, load_fixture

DATA = os.environ.get(DATA_ENV)


class CivilTimeCases(unittest.TestCase):
    """Engine time parsing versus hand-derived IANA/Python expectations (no Swiss data)."""

    def test_each_time_case(self):
        for case in load_fixture("time_cases.json")["cases"]:
            with self.subTest(case=case["id"], topic=case["topic"]):
                outcome, utc = time_probe.classify(case)
                self.assertEqual(outcome, case["expect"])
                self.assertEqual(utc, case.get("expect_utc"))

    def test_zoneinfo_matches_iana_transcription(self):
        for zone in time_probe.iana_crosscheck()["zones"]:
            with self.subTest(zone=zone["zone"]):
                self.assertEqual(zone["mismatch_count"], 0, zone["mismatches"])

    def test_kolkata_local_gaps_and_folds(self):
        events = time_probe.kolkata_local_anomalies()["events_1900_2100"]
        self.assertEqual(
            [(e["kind"], e["local_interval"][0]) for e in events],
            [("nonexistent local interval", "1906-01-01T00:00:00"),
             ("nonexistent local interval", "1941-10-01T00:00:00"),
             ("repeated local interval", "1942-05-14T23:00:00"),
             ("nonexistent local interval", "1942-09-01T00:00:00"),
             ("repeated local interval", "1945-10-14T23:00:00")])

    def test_utc_year_rule_disagrees_with_local_date_at_both_edges(self):
        # Current behaviour, recorded so a later local-date fix is visible in review.
        cases = {c["id"]: c for c in load_fixture("time_cases.json")["cases"]}
        self.assertEqual(time_probe.classify(cases["T46"])[0], "RANGE")   # local 1900-01-01, refused
        self.assertEqual(time_probe.classify(cases["T49"])[0], "ACCEPT")  # local 2101-01-01, accepted
        self.assertEqual(time_probe.classify(cases["T50"])[0], "RANGE")   # local 2100-12-31, refused
        self.assertEqual(time_probe.classify(cases["T51"])[0], "ACCEPT")  # local 1899-12-31, accepted


class RunnerGates(unittest.TestCase):
    def test_blocked_without_data(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("SE_EPHE_PATH", None)
            report = run.run_all("")
        self.assertEqual((report["verdict"], report["exit_code"]), ("BLOCKED", 2))
        self.assertIn("EPHEMERIS_PATH_MISSING", report["reason"])

    def test_blocked_with_wrong_files(self):
        with tempfile.TemporaryDirectory() as d, mock.patch.dict(os.environ):
            os.environ.pop("SE_EPHE_PATH", None)
            for name in ("sepl_18.se1", "semo_18.se1"):
                Path(d, name).write_bytes(b"not the pinned file")
            report = run.run_all(d)
        self.assertEqual(report["exit_code"], 2)
        self.assertIn("EPHEMERIS_FILE_MISMATCH", report["reason"])

    def test_blocked_when_se_ephe_path_set(self):
        with mock.patch.dict(os.environ, {"SE_EPHE_PATH": "/tmp"}):
            report = run.run_all(DATA or "/nonexistent")
        self.assertEqual(report["exit_code"], 2)
        self.assertIn("EPHEMERIS_PATH_OVERRIDE", report["reason"])


@unittest.skipIf(DATA is None, f"{DATA_ENV} unset: KUN-02 real-data probes not requested")
class RealDataProbes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env = mock.patch.dict(os.environ)
        cls._env.start()
        os.environ.pop("SE_EPHE_PATH", None)
        try:
            cls.folder = verify_ephemeris_dir(DATA)
        except EphemerisDataError as exc:
            cls._env.stop()
            raise AssertionError(f"{DATA_ENV} is set but does not hold the pinned required files: {exc}") from None
        cls.report = {"lagna": lagna_probe.run(cls.folder), "time": time_probe.run(cls.folder),
                      "envelope": envelope_probe.run(cls.folder)}
        cls.checks = run.invariants(cls.report)

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def test_invariants(self):
        self.assertEqual(len(self.checks), 16)
        for c in self.checks:
            with self.subTest(check=c["id"], claim=c["claim"]):
                self.assertTrue(c["pass"])

    def test_p_and_w_compared_on_enough_points(self):
        a = self.report["lagna"]
        compared = sum(v["samples"] - v["p_refused"] for s in ("structured_grid", "random_within_66", "random_66_to_89")
                       for v in a[s]["by_band"].values())
        self.assertEqual(compared, 167_612)  # deterministic grids: 107,136 + 60,000 + 476

    def test_polar_refusal_depends_on_date_today(self):
        rows = {(r["birth_datetime"][:4], r["latitude"]): r["engine"]
                for r in self.report["envelope"]["latitude_behaviour"]["rows"]}
        self.assertEqual(rows[("1900", 66.55)], "REFUSE ASCENDANT_UNCOMPUTABLE")
        self.assertTrue(rows[("2100", 66.55)].startswith("ACCEPT"))

    def test_swiss_sidereal_time_step_at_2050_is_recorded(self):
        # Swiss 2.10.03 switches sidereal-time model at 2050-01-01 0h UT; the step is a
        # known Swiss convention, pinned here so a Swiss upgrade that changes it is noticed.
        st = self.report["time"]["sidereal_time"]
        self.assertLess(st["max_abs_arcsec_1900_2049"], 0.01)
        self.assertAlmostEqual(st["swiss_step_at_2050_arcsec"], -1.908, delta=0.01)

    def test_engine_resets_leaked_swiss_state(self):
        # Another caller in the same process leaves SIDBIT_PREC_ORIG set; the engine
        # must not inherit it, because set_sid_mode alone does not undo it.
        import swisseph as swe
        req = {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata",
               "latitude": 28.6139, "longitude": 77.2090}
        clean = calculate(req, ephe_path=str(self.folder))["lagna"]["longitude_deg"]
        swe.set_sid_mode(swe.SIDM_LAHIRI | swe.SIDBIT_PREC_ORIG, 0, 0)
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        leaked = swe.houses_ex(2451545.0, 28.6139, 77.2090, b"W", swe.FLG_SIDEREAL)[1][0]
        self.assertNotEqual(round(leaked, 8), clean)
        self.assertEqual(calculate(req, ephe_path=str(self.folder))["lagna"]["longitude_deg"], clean)


if __name__ == "__main__":
    unittest.main()
