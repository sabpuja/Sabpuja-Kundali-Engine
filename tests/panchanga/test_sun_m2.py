"""KUN-PAN-M2-SUN-001: sunrise, sunset and Vara validation module (not integrated anywhere).

Pure tests run everywhere. Real-data tests follow the suite convention (skip without
SABPUJA_TEST_EPHE_PATH, fail if it is set but wrong). The swetest layer additionally needs
SABPUJA_TEST_SWETEST. Every place and instant is synthetic; no birth data.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
import inspect
import json
import math
import os
import unittest

from sabpuja_kundali.panchanga import sun
from sabpuja_kundali.engine import InputRefusalError, ChartComputationError
from . import sun_compare as C
from . import sun_oracle as O
from .common import EPHE, SWETEST, real_data

IMD47, USNO50 = C.IMD47, C.USNO50
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


def tol() -> dict:
    return C.pinned(C.TOL_PATH, C.TOL_SHA256)["layers"]


def req(local: str, tz: str = "Asia/Kolkata", lat: float = 28.6139, lon: float = 77.2090) -> dict:
    return {"birth_datetime": local, "timezone": tz, "latitude": lat, "longitude": lon}


def local_string(t_us: int, offset: timedelta) -> str:
    """A birth_datetime string for the exact microsecond instant, written with a fixed offset."""
    wall = (EPOCH + timedelta(microseconds=t_us) + offset).replace(tzinfo=None)
    sign = "+" if offset >= timedelta(0) else "-"
    total = abs(int(offset.total_seconds()))
    return wall.isoformat(timespec="microseconds") + f"{sign}{total // 3600:02d}:{total % 3600 // 60:02d}"


class NoDefaultConvention(unittest.TestCase):
    """PAN-D03 is PENDING: nothing may pick or blend a convention silently."""

    def test_convention_is_keyword_only_without_default(self):
        for fn in (sun.sun_day, sun.vara):
            p = inspect.signature(fn).parameters["convention"]
            self.assertIs(p.kind, inspect.Parameter.KEYWORD_ONLY)
            self.assertIs(p.default, inspect.Parameter.empty)
        with self.assertRaises(TypeError):
            sun.sun_day("2026-11-06", 23.18, 82.5, "Asia/Kolkata")

    def test_exactly_two_conventions_with_documented_constants(self):
        self.assertEqual(set(sun.CONVENTIONS), {IMD47, USNO50})
        for name, (dep, ref, sd) in {IMD47: (47, 31, 16), USNO50: (50, 34, 16)}.items():
            c = sun.CONVENTIONS[name]
            self.assertEqual((c["depression_arcmin"], c["refraction_arcmin"], c["semidiameter_arcmin"]), (dep, ref, sd))
            self.assertEqual(c["refraction_arcmin"] + c["semidiameter_arcmin"], c["depression_arcmin"])

    def test_bad_conventions_refused_before_any_other_check(self):
        for bad in (None, "", "sun-d-imd-47", "IMD", "SUN-B", 47, 47.0, True, ["SUN-D-IMD-47"], "SUN-D-IMD-47 "):
            with self.subTest(bad=bad):
                with self.assertRaises(InputRefusalError) as cm:
                    sun.sun_day("not a date", "x", "y", "Nowhere/Zone", convention=bad)
                self.assertEqual(cm.exception.code, "SUNRISE_CONVENTION_REQUIRED")
                with self.assertRaises(InputRefusalError) as cm:
                    sun.vara("not a request", convention=bad)
                self.assertEqual(cm.exception.code, "SUNRISE_CONVENTION_REQUIRED")

    def test_m1_contract_and_reports_do_not_use_this_module(self):
        import re
        pattern = re.compile(r"(from\s+\.?sun\b|import\s+sun\b|panchanga\.sun\b|from\s+\.\s+import\s+.*\bsun\b)")
        root = Path(sun.__file__).resolve().parent
        for name in ("__init__.py", "contract.py", "rules.py", "search.py", "astro.py", "__main__.py"):
            self.assertIsNone(pattern.search((root / name).read_text(encoding="utf-8")), name)
        report = Path(C.REPO, "report")
        for path in report.rglob("*.py"):
            self.assertNotIn("panchanga.sun", path.read_text(encoding="utf-8"), str(path))


class InputRefusals(unittest.TestCase):
    """Typed refusals, in a fixed order, before any Swiss call (no ephemeris needed)."""

    def code(self, *args, **kw):
        with self.assertRaises(InputRefusalError) as cm:
            sun.sun_day(*args, convention=IMD47, ephe_path="/nonexistent", **kw)
        return cm.exception.code

    def test_date(self):
        for bad in ("2026-11-6", "2026/11/06", "2026-02-30", "20261106", 20261106, None, " 2026-11-06"):
            self.assertEqual(self.code(bad, 23.0, 82.5, "Asia/Kolkata"), "DATE_INVALID", bad)

    def test_envelope_d13a(self):
        self.assertEqual(self.code("1969-12-31", 23.0, 82.5, "Asia/Kolkata"), "DATE_OUTSIDE_SUPPORTED_RANGE")
        self.assertEqual(self.code("2101-01-01", 23.0, 82.5, "Asia/Kolkata"), "DATE_OUTSIDE_SUPPORTED_RANGE")

    def test_zone(self):
        self.assertEqual(self.code("2026-11-06", 23.0, 82.5, "Asia/Calcutta_x"), "TIMEZONE_INVALID")
        self.assertEqual(self.code("2026-11-06", 23.0, 82.5, None), "TIMEZONE_INVALID")
        for key in ("UTC", "Etc/GMT-5"):
            self.assertEqual(self.code("2026-11-06", 23.0, 82.5, key), "TIMEZONE_NOT_LOCATION_BASED")

    def test_coordinates_and_polar_band(self):
        self.assertEqual(self.code("2026-11-06", True, 82.5, "Asia/Kolkata"), "COORDINATE_INVALID")
        self.assertEqual(self.code("2026-11-06", float("nan"), 82.5, "Asia/Kolkata"), "COORDINATE_INVALID")
        self.assertEqual(self.code("2026-11-06", 23.0, 180.5, "Asia/Kolkata"), "COORDINATE_INVALID")
        for lat in (66.0001, -66.5, 69.6492, 90):
            self.assertEqual(self.code("2026-11-06", lat, 18.9, "Europe/Oslo"), "LATITUDE_OUTSIDE_SUPPORTED_BAND")

    def test_ephemeris_gate_after_input(self):
        from sabpuja_kundali.ephemeris import EphemerisDataError
        with self.assertRaises(EphemerisDataError) as cm:
            sun.sun_day("2026-11-06", 23.0, 82.5, "Asia/Kolkata", convention=IMD47, ephe_path="/nonexistent")
        self.assertEqual(cm.exception.code, "EPHEMERIS_PATH_MISSING")
        with mock.patch.dict(os.environ, {"SE_EPHE_PATH": "/tmp"}):
            with self.assertRaises(EphemerisDataError) as cm:
                sun.sun_day("2026-11-06", 23.0, 82.5, "Asia/Kolkata", convention=IMD47, ephe_path="/nonexistent")
        self.assertEqual(cm.exception.code, "EPHEMERIS_PATH_OVERRIDE")

    def test_vara_request_shape_and_chart_order(self):
        def code(r):
            with self.assertRaises(InputRefusalError) as cm:
                sun.vara(r, convention=USNO50, ephe_path="/nonexistent")
            return cm.exception.code
        self.assertEqual(code([]), "REQUEST_INVALID")
        self.assertEqual(code({**req("2026-11-06T05:00:00+05:30"), "extra": 1}), "REQUEST_INVALID")
        self.assertEqual(code(req("2026-11-06T05:00:00")), "TIME_OFFSET_REQUIRED")
        self.assertEqual(code(req("1965-01-01T05:00:00+05:30")), "HISTORICAL_CLOCK_UNVERIFIED")
        self.assertEqual(code(req("2026-11-06T05:00:00+05:30", lat=70.0)), "LATITUDE_OUTSIDE_SUPPORTED_BAND")


class CrossingSearch(unittest.TestCase):
    """The bracketing search on synthetic altitude curves (no Swiss)."""

    def test_grazing_pair_between_samples_is_found(self):
        # A peak only 0.0001 deg above the threshold for ~2 minutes: both crossings fall
        # between two 5-minute samples. The refined extremum must expose them.
        peak = 1_000 * sun.MICROS + 7 * 60 * sun.MICROS
        f = lambda t: 1e-4 - ((t - peak) / (60 * sun.MICROS)) ** 2 * 1e-4
        found = sun._crossings(f, 0, 3600 * sun.MICROS)
        self.assertEqual([k for _, k in found], ["rise", "set"])
        self.assertAlmostEqual(found[0][0], peak - 60 * sun.MICROS, delta=2)
        self.assertAlmostEqual(found[1][0], peak + 60 * sun.MICROS, delta=2)
        # Mutation: without the extremum refinement the samples alone miss the pair.
        times = range(0, 3600 * sun.MICROS + 1, sun.SAMPLE_STEP_US)
        self.assertTrue(all(f(t) < 0 for t in times))

    def test_microsecond_convergence_and_half_open_event(self):
        root = 12_345_678_901
        found = sun._crossings(lambda t: (t - root) / 1e9, 0, 86400 * sun.MICROS)
        self.assertEqual(found, [(root, "rise")])
        found = sun._crossings(lambda t: (t - root - 0.5) / 1e9, 0, 86400 * sun.MICROS)
        self.assertEqual(found, [(root + 1, "rise")])

    def test_residual_bound(self):
        with self.assertRaises(sun.SunComputationError) as cm:
            sun._check_residual(lambda t: 2.0 / 3600, 0)
        self.assertEqual(cm.exception.code, sun.NOT_CONVERGED)
        self.assertEqual(sun._check_residual(lambda t: 0.5 / 3600, 0), 0.5 / 3600)


class OracleSelfChecks(unittest.TestCase):
    """The independent oracle against textbook values (Meeus example 25.a, 1992-10-13 0h TD)."""

    def test_meeus_example_25a(self):
        jd_td = 2448908.5
        jd_ut = jd_td - O.delta_t_seconds(1992.78) / 86400
        ra, dec, _ = O._sun_ra_dec(jd_ut)
        # Meeus: apparent RA 198.38083 deg, Dec -7.78507 deg (low-accuracy method).
        self.assertAlmostEqual(ra, 198.38083, delta=0.002)
        self.assertAlmostEqual(dec, -7.78507, delta=0.002)

    def test_gmst_meeus_example_12a(self):
        # 1987-04-10 0h UT: GMST 13h10m46.3668s = 197.693195 deg.
        self.assertAlmostEqual(O._gast_deg(2446895.5, 0.0), 197.693195, delta=1e-5)


@real_data
class SunDayRealData(unittest.TestCase):

    def day(self, *a, convention):
        return sun.sun_day(*a, convention=convention, ephe_path=EPHE)

    def test_central_station_kartika_matches_imd_minutes_example(self):
        r = self.day("2026-11-06", 23 + 11 / 60, 82.5, "Asia/Kolkata", convention=IMD47)
        self.assertEqual(r["sunrise"]["local"][:16], "2026-11-06T06:08")   # IMD prints 6:08 AM
        self.assertEqual(r["sunset"]["local"][:16], "2026-11-06T17:18")    # 17:18:52 prints 5:19 PM if rounded
        self.assertLessEqual(abs(r["residual_altitude_arcsec"]["sunrise"]), 1.0)
        self.assertEqual(r["civil_weekday"], "friday")
        self.assertEqual(r["method"]["convention"], IMD47)

    def test_conventions_differ_by_12_to_17_seconds_in_india_and_never_blend(self):
        for name, lat, lon in C.INDIA:
            for ds in ("2026-03-20", "2026-06-21", "2026-12-21"):
                a = self.day(ds, lat, lon, "Asia/Kolkata", convention=IMD47)
                b = self.day(ds, lat, lon, "Asia/Kolkata", convention=USNO50)
                rise = (a["sunrise"]["utc_us"] - b["sunrise"]["utc_us"]) / 1e6
                sset = (a["sunset"]["utc_us"] - b["sunset"]["utc_us"]) / 1e6
                self.assertTrue(12.0 <= rise <= 17.0 and -17.0 <= sset <= -12.0, (name, ds, rise, sset))

    def test_polar_day_typed_unavailable_and_convention_dependent_edge(self):
        for c in (IMD47, USNO50):
            r = self.day("2026-06-21", 65.9, 25.0, "Europe/Helsinki", convention=c)     # USNO N01
            self.assertEqual(r["sunrise"], {"status": "unavailable", "reason": sun.UNDEFINED,
                                            "condition": "SUN_ABOVE_DEPRESSION_ALL_DAY"})
            self.assertEqual(r["sunset"]["status"], "unavailable")
            r = self.day("2026-12-21", -66.0, 140.0, "Antarctica/DumontDUrville", convention=c)
            self.assertEqual(r["sunrise"]["condition"], "SUN_ABOVE_DEPRESSION_ALL_DAY")
        # Between the two polar limits (about 65.73 and 65.78 deg) only 47' has a sunrise:
        # the convention decides whether the Vara exists at all.
        a = self.day("2026-06-21", 65.75, 25.0, "Europe/Helsinki", convention=IMD47)
        b = self.day("2026-06-21", 65.75, 25.0, "Europe/Helsinki", convention=USNO50)
        self.assertEqual(a["sunrise"]["status"], "available")
        self.assertEqual(b["sunrise"]["status"], "unavailable")
        # Both conventions defined, eight minutes apart, just inside the limit.
        a = self.day("2026-06-21", 65.70, 25.0, "Europe/Helsinki", convention=IMD47)
        b = self.day("2026-06-21", 65.70, 25.0, "Europe/Helsinki", convention=USNO50)
        self.assertGreater((a["sunrise"]["utc_us"] - b["sunrise"]["utc_us"]) / 1e6, 400)

    def test_dst_days_and_date_line(self):
        for ds, expected in (("2026-03-08", "-04:00"), ("2026-11-01", "-05:00")):
            r = self.day(ds, 40.7128, -74.0060, "America/New_York", convention=USNO50)
            self.assertTrue(r["sunrise"]["local"].startswith(ds) and r["sunrise"]["local"].endswith(expected))
            self.assertTrue(r["sunset"]["local"].startswith(ds))
        r = self.day("2026-01-01", 1.87, -157.4, "Pacific/Kiritimati", convention=IMD47)
        self.assertTrue(r["sunrise"]["local"].startswith("2026-01-01") and r["sunrise"]["utc"].startswith("2025-12-31"))
        r = self.day("2026-01-01", -14.28, -170.7, "Pacific/Pago_Pago", convention=IMD47)
        self.assertTrue(r["sunrise"]["local"].startswith("2026-01-01") and r["sunrise"]["local"].endswith("-11:00"))

    def test_envelope_edges_compute(self):
        for ds in ("1970-01-01", "2100-12-31"):
            r = self.day(ds, 28.6139, 77.2090, "Asia/Kolkata", convention=IMD47)
            self.assertEqual((r["sunrise"]["status"], r["sunset"]["status"]), ("available", "available"))

    def test_moshier_fallback_refused(self):
        import swisseph as swe
        real = swe.calc_ut
        with mock.patch.object(swe, "calc_ut", lambda jd, b, f: (real(jd, b, f)[0], swe.FLG_MOSEPH | swe.FLG_EQUATORIAL)):
            with self.assertRaises(ChartComputationError) as cm:
                self.day("2026-11-06", 23.0, 82.5, "Asia/Kolkata", convention=IMD47)
        self.assertEqual(cm.exception.code, "SWISS_EPHEMERIS_FALLBACK_REFUSED")

    def test_deterministic(self):
        a = self.day("2026-06-21", 34.0837, 74.7973, "Asia/Kolkata", convention=USNO50)
        b = self.day("2026-06-21", 34.0837, 74.7973, "Asia/Kolkata", convention=USNO50)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))


@real_data
class VaraRealData(unittest.TestCase):

    def v(self, r, c=IMD47):
        return sun.vara(r, convention=c, ephe_path=EPHE)

    def test_before_and_after_sunrise_half_open(self):
        day = sun.sun_day("2026-11-06", 28.6139, 77.2090, "Asia/Kolkata", convention=IMD47, ephe_path=EPHE)
        t = day["sunrise"]["utc_us"]
        ist = timedelta(hours=5, minutes=30)
        at = self.v(req(local_string(t, ist)))
        before = self.v(req(local_string(t - 1, ist)))
        self.assertEqual((at["vara"]["vara_id"], at["civil_weekday"], at["vara_differs_from_civil_weekday"]),
                         ("shukravara", "friday", False))
        self.assertEqual(at["seconds_after_governing_sunrise"], 0)
        self.assertEqual((before["vara"]["vara_id"], before["civil_weekday"], before["vara_differs_from_civil_weekday"]),
                         ("guruvara", "friday", True))
        self.assertEqual(before["vara"]["sunrise_local_date"], "2026-11-05")

    def test_convention_changes_vara_only_inside_the_gap(self):
        # A birth 8 s after the 50' sunrise and before the 47' sunrise (Delhi, about 15 s apart).
        a = sun.sun_day("2026-11-06", 28.6139, 77.2090, "Asia/Kolkata", convention=USNO50, ephe_path=EPHE)
        t = a["sunrise"]["utc_us"] + 8 * sun.MICROS
        r = req(local_string(t, timedelta(hours=5, minutes=30)))
        self.assertEqual(self.v(r, USNO50)["vara"]["vara_id"], "shukravara")
        self.assertEqual(self.v(r, IMD47)["vara"]["vara_id"], "guruvara")

    def test_midnight_and_late_evening(self):
        self.assertEqual(self.v(req("2026-11-06T00:00:00+05:30"))["vara"]["vara_id"], "guruvara")
        self.assertEqual(self.v(req("2026-11-06T23:59:59+05:30"))["vara"]["vara_id"], "shukravara")

    def test_dst_zone_birth(self):
        r = self.v(req("2026-03-08T06:00:00-04:00", tz="America/New_York", lat=40.7128, lon=-74.006), USNO50)
        self.assertEqual((r["vara"]["vara_id"], r["civil_weekday"]), ("shanivara", "sunday"))

    def test_polar_vara_unavailable_but_civil_weekday_kept(self):
        r = self.v(req("2026-06-21T12:00:00+03:00", tz="Europe/Helsinki", lat=65.9, lon=25.0))
        self.assertEqual(r["vara"]["status"], "unavailable")
        self.assertEqual(r["vara"]["reason"], sun.UNDEFINED)
        self.assertEqual(r["civil_weekday"], "sunday")
        self.assertIsNone(r["vara_differs_from_civil_weekday"])
        self.assertNotIn("vara_id", r["vara"])

    def test_governing_sunrise_before_envelope(self):
        r = self.v(req("1970-01-01T03:00:00+05:30"))
        self.assertEqual(r["vara"], {"status": "unavailable", "reason": sun.OUTSIDE_ENVELOPE,
                                     "condition": "GOVERNING_SUNRISE_BEFORE_1970_01_01"})
        self.assertEqual(r["civil_weekday"], "thursday")
        r = self.v(req("1970-01-01T09:00:00+05:30"))
        self.assertEqual(r["vara"]["vara_id"], "guruvara")


@real_data
class IndependentReferences(unittest.TestCase):
    """USNO and IMD published minutes, the pure-Python oracle, Swiss rise_trans and swetest."""

    @classmethod
    def setUpClass(cls):
        cls.tol = tol()

    def test_usno_published_within_predeclared_120_s(self):
        limit = self.tol["usno_published"]["seconds"]
        rows = C.usno_layer(EPHE)
        located = [r for r in rows if r["case"].startswith("PAN-REF-SUN-S")]
        self.assertEqual(len(located), 12)
        for r in located:
            for k in ("sunrise", "sunset"):
                self.assertLessEqual(abs(r[f"{k}_usno50_minus_published_s"]), limit, (r["case"], k))
        n01 = next(r for r in rows if r["case"] == "PAN-REF-SUN-N01")
        self.assertIn("Object continuously above the Horizon", n01["usno_sundata"])
        self.assertEqual(n01["sunrise_usno50"], "SUN_ABOVE_DEPRESSION_ALL_DAY")
        n02 = next(r for r in rows if r["case"] == "PAN-REF-SUN-N02")
        self.assertEqual(n02["engine_refusal"], "LATITUDE_OUTSIDE_SUPPORTED_BAND")

    def test_imd_published_within_120_s_and_depression_fit(self):
        limit = self.tol["imd_published"]["seconds"]
        rows = C.imd_layer(EPHE)
        self.assertEqual(len(rows), 60 + 164)
        for r in rows:
            for k in ("sunrise", "sunset"):
                self.assertLessEqual(abs(r[f"{k}_imd47_minus_published_s"]), limit, (r["place"], r["date"], k))
        s = C.imd_summary(rows)
        # Central Station (IMD's own reference point): the day-length fit lands on 47', not 50'.
        self.assertLess(abs(s["central"]["best_fit_depression_arcmin"] - 47.0), 1.5)
        self.assertGreater(abs(s["central"]["best_fit_depression_arcmin"] - 50.0), 2.0)

    def test_oracle_swiss_rise_and_swetest_layers(self):
        t = self.tol
        grid = C.oracle_and_swiss_layer(EPHE, SWETEST)
        self.assertGreater(len(grid), 1000)
        for r in grid:
            if "unavailable" in r:
                self.fail(f"unexpected unavailable event in the validation grid: {r['place']} {r['date']}")
            band = abs(r["lat"]) <= 40
            for tag in ("imd47", "usno50"):
                o = r[f"{tag}_minus_oracle_s"]
                self.assertIsNotNone(o)
                limit = t["independent_oracle"]["seconds_abs_lat_le_40" if band else "seconds_abs_lat_le_66"]
                self.assertLessEqual(abs(o), limit, (r["place"], r["date"], r["event"], tag, o))
                g = r[f"{tag}_minus_swiss_rise_geocentric_s"]
                limit = t["swiss_rise_trans_geocentric"]["seconds_abs_lat_le_40" if band else "seconds_abs_lat_le_66"]
                self.assertLessEqual(abs(g), limit, (r["place"], r["date"], r["event"], tag, g))
                if SWETEST:
                    self.assertLessEqual(abs(r[f"{tag}_swetest_check_arcsec"]), t["swetest_altitude"]["arcsec"])
            if r["zone"] == "Asia/Kolkata":
                self.assertGreaterEqual(abs(r["imd47_minus_usno50_s"]), t["oracle_discrimination"]["min_seconds_india"])
        if not SWETEST:
            self.skipTest("SABPUJA_TEST_SWETEST unset: oracle and Swiss layers passed; swetest layer not run")

    def test_oracle_tells_the_conventions_apart(self):
        # Mutation: an engine run under the wrong convention fails the oracle layer everywhere in India.
        limit = tol()["independent_oracle"]["seconds_abs_lat_le_40"]
        for name, lat, lon in C.INDIA[:6]:
            r = sun.sun_day("2026-06-21", lat, lon, "Asia/Kolkata", convention=IMD47, ephe_path=EPHE)
            t = C.utc_of(r["sunrise"])
            wrong = O.event_utc(t + timedelta(minutes=20), lat, lon, 50, "rise")
            self.assertGreater(abs((t - wrong).total_seconds()), limit, name)


if __name__ == "__main__":
    unittest.main()
