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


class InvariantGuards(unittest.TestCase):
    """Failure injection on a synthetic report: empty, partial or altered evidence must FAIL (no Swiss data)."""

    @staticmethod
    def good_report() -> dict:
        exp = run.expected_counts()

        def band(n, refused=0):
            return {"samples": n, "p_refused": refused, "w_refused": 0, "p_w_bitwise_equal": n - refused,
                    "p_w_max_abs_arcsec": 0.0, "mc_armc_equal": n - refused, "lahiri_max_abs_arcsec": 0.0,
                    "independent_max_abs_arcsec": 0.0, "independent_opposite": 0, "max_abs_altitude_arcsec": 0.0,
                    "not_rising": 0, "w_cusp_failures": 0}

        def sample(n, polar=False):
            return {"points": n, "by_band": {run.POLAR_BAND: band(n, n)} if polar else {"[0,10)": band(n)}}

        engine = []
        for cid in exp["engine_case_ids"]:
            if cid == "EC-TOS-2000":
                engine.append({"id": cid, "p_asc": None, "w_asc": 150.5, "engine": {"refused": "ASCENDANT_UNCOMPUTABLE"}})
            else:
                engine.append({"id": cid, "p_asc": 76.3, "w_asc": 76.3, "engine": {
                    "lagna_display": 76.3, "display_equals_w": True, "rashi_equals_w": True,
                    "navamsa_equals_w": True, "all_houses_equal_w": True}})
        coverage = [{"instant": p, "all_bodies_swiss_files": True} for p in run.COVERAGE_PREFIXES]
        coverage += [{"instant": f"{y}-06-01 (outside data)", "all_bodies_swiss_files": False} for y in (1799, 2400)]
        return {
            "lagna": {
                "structured_grid": sample(exp["structured_points"]),
                "random_within_66": sample(exp["random_within_66"]),
                "random_66_to_89": sample(exp["random_66_to_89"], polar=True),
                "placidus_threshold": {"per_date": [{"date_utc": d, "north_minus_polar_arcsec": 0.0,
                                                     "south_minus_polar_arcsec": 0.0} for d in exp["threshold_dates"]]},
                "boundary_sweep": {"per_location": [{"location": l, "failures": [], "navamsa_crossings": 108}
                                                    for l in exp["sweep_locations"]]},
                "chart_consistency": {"checks": exp["chart_consistency_checks"], "mismatches": 0},
                "wrong_configurations": {"minus_reference_arcsec": {
                    "sid_mode_never_set": 3000.0, "lahiri_flag_missing": 90000.0, "lahiri_nonut": 5.0,
                    "krishnamurti": 300.0, "lahiri_empty_ephe_dir": 0.0,
                    "lahiri_after_prec_orig_mode_reset_only": 0.0175, "lahiri_after_path_and_mode_reset": 0.0}},
                "engine_cases": {"cases": engine},
            },
            "time": {
                "engine_time_cases": {"all_match": True, "cases": [
                    {"id": i, "actual": "ACCEPT", "matches_expectation": True, "engine_utc_matches_parser": True}
                    for i in exp["time_case_ids"]]},
                "iana_crosscheck": {"zones": [{"zone": z, "probes": exp["iana_probes"][z], "mismatch_count": 0}
                                              for z in exp["iana_zones"]]},
                "timescale": {
                    "iers_consistency_1972_2026": {"samples": run.IERS_SAMPLES_1972_2026, "all_within_0_9_s": True},
                    "swiss_leap_seconds": {"iers_leap_dates": exp["iers_leap_dates"],
                                           "swiss_accepts_23_59_60": exp["iers_leap_dates"],
                                           "swiss_refuses_iers_leap": [],
                                           "non_leap_dates": [{"swiss": "refused"}] * 4}},
            },
            "envelope": {"ephemeris_coverage": {"rows": coverage}},
        }

    def assertOnlyFails(self, report, *ids):
        result = {c["id"]: c["pass"] for c in run.invariants(report)}
        self.assertEqual(len(result), 16)
        self.assertEqual(sorted(k for k, ok in result.items() if not ok), sorted(ids))

    def mutated(self, change):
        report = self.good_report()
        change(report)
        return report

    def test_complete_report_passes(self):
        self.assertOnlyFails(self.good_report())

    def test_predeclared_counts_are_frozen(self):
        # Derived from the fixtures and probe schedules; pinned to the values measured at 2cff706/0c181a7.
        exp = run.expected_counts()
        self.assertEqual((exp["structured_points"], exp["random_within_66"], exp["random_66_to_89"]),
                         (124_416, 60_000, 20_000))
        self.assertEqual(exp["chart_consistency_checks"], 90_720)
        self.assertEqual(exp["iana_probes"], {
            "Asia/Kolkata": 12_245, "Asia/Karachi": 5_916, "Asia/Dhaka": 7_759, "Asia/Kathmandu": 12_230,
            "Asia/Colombo": 12_248, "Asia/Yangon": 12_236, "Asia/Thimphu": 12_230})
        self.assertEqual(sum(exp["iana_probes"].values()), 74_864)
        self.assertEqual((len(exp["engine_case_ids"]), len(exp["time_case_ids"]), len(exp["threshold_dates"]),
                          len(exp["sweep_locations"]), exp["iers_leap_dates"]), (6, 63, 8, 3, 27))

    def test_a12_rejects_wrong_engine_rows(self):
        def accepted(r):
            return r["lagna"]["engine_cases"]["cases"][0]

        def polar(r):
            return r["lagna"]["engine_cases"]["cases"][-1]

        cases = {
            "unexpected refusal": lambda r: accepted(r).update(engine={"refused": "INPUT_REFUSED"}),
            "empty engine dict": lambda r: accepted(r).update(engine={}),
            "category false": lambda r: accepted(r)["engine"].update(navamsa_equals_w=False),
            "truthy non-bool": lambda r: accepted(r)["engine"].update(rashi_equals_w="yes"),
            "missing field": lambda r: accepted(r)["engine"].pop("all_houses_equal_w"),
            "unexpected field": lambda r: accepted(r)["engine"].update(refused="INPUT_REFUSED"),
            "polar refused with another code": lambda r: polar(r).update(engine={"refused": "INPUT_REFUSED"}),
            "polar accepted": lambda r: polar(r).update(engine=dict(accepted(r)["engine"])),
            "no cases": lambda r: r["lagna"]["engine_cases"].update(cases=[]),
            "case missing": lambda r: r["lagna"]["engine_cases"]["cases"].pop(0),
        }
        for name, change in cases.items():
            with self.subTest(name):
                self.assertOnlyFails(self.mutated(change), "A12")

    def test_empty_or_partial_sections_fail(self):
        lagna, time, env = (lambda r: r["lagna"]), (lambda r: r["time"]), (lambda r: r["envelope"])
        cases = {
            "A4": [lambda r: lagna(r)["placidus_threshold"].update(per_date=[]),
                   lambda r: lagna(r)["placidus_threshold"]["per_date"].pop()],
            "A9": [lambda r: lagna(r)["boundary_sweep"].update(per_location=[]),
                   lambda r: lagna(r)["boundary_sweep"]["per_location"].pop()],
            "A10": [lambda r: lagna(r)["chart_consistency"].update(checks=0),
                    lambda r: lagna(r)["chart_consistency"].update(checks=1),
                    lambda r: lagna(r)["chart_consistency"].update(checks=lagna(r)["chart_consistency"]["checks"] - 1)],
            "A11": [lambda r: lagna(r).pop("wrong_configurations")],
            "B1": [lambda r: time(r)["engine_time_cases"].update(cases=[]),
                   lambda r: time(r)["engine_time_cases"]["cases"][0].pop("engine_utc_matches_parser")],
            "B2": [lambda r: time(r)["iana_crosscheck"].update(zones=[]),
                   lambda r: time(r)["iana_crosscheck"]["zones"].pop(),
                   lambda r: time(r)["iana_crosscheck"]["zones"][0].update(probes=0),
                   lambda r: [z.update(probes=1) for z in time(r)["iana_crosscheck"]["zones"]],
                   lambda r: time(r)["iana_crosscheck"]["zones"][-1].update(
                       probes=time(r)["iana_crosscheck"]["zones"][-1]["probes"] - 1)],
            "B3": [lambda r: time(r)["timescale"]["iers_consistency_1972_2026"].update(samples=0),
                   lambda r: time(r)["timescale"]["swiss_leap_seconds"].update(
                       iers_leap_dates=0, swiss_accepts_23_59_60=0)],
            "C1": [lambda r: env(r)["ephemeris_coverage"].update(rows=[]),
                   lambda r: env(r)["ephemeris_coverage"].update(rows=env(r)["ephemeris_coverage"]["rows"][:2]),
                   lambda r: env(r)["ephemeris_coverage"]["rows"][-1].update(all_bodies_swiss_files=True)],
        }
        for cid, changes in cases.items():
            for n, change in enumerate(changes):
                with self.subTest(check=cid, variant=n):
                    self.assertOnlyFails(self.mutated(change), cid)

    def test_missing_or_short_point_samples_fail_all_band_checks(self):
        band_checks = ("A1", "A2", "A3", "A5", "A6", "A7", "A8")
        cases = [
            lambda r: r["lagna"]["structured_grid"].update(points=0, by_band={}),
            lambda r: r["lagna"]["random_within_66"]["by_band"]["[0,10)"].update(samples=1),
            lambda r: r["lagna"]["random_66_to_89"].update(by_band={}),
        ]
        for n, change in enumerate(cases):
            with self.subTest(variant=n):
                self.assertOnlyFails(self.mutated(change), *band_checks)


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
