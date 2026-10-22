"""KUN-03 P2 (SCI-01g): fixed supported latitude band, -66.0 to 66.0 inclusive.

Synthetic inputs only. The band is checked before any Swiss call and is the same
for every date. Since KUN-03 P3 the ascendant vehicle is b"W" (SCI-01e), which
computes at any latitude, so the band alone decides acceptance. Real-data cases
run only when SABPUJA_TEST_EPHE_PATH is set.
"""
import json
import math
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

import swisseph

from sabpuja_kundali import engine
from sabpuja_kundali.engine import ChartComputationError, UnsupportedInputError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError

SRC = Path(__file__).resolve().parent.parent / "src"
SYNTHETIC = {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata",
             "latitude": 28.6139, "longitude": 77.2090}
MISSING = "/does-not-exist/sabpuja"
CODE = "LATITUDE_OUTSIDE_SUPPORTED_BAND"
ABOVE = math.nextafter(66.0, math.inf)
BELOW = math.nextafter(-66.0, -math.inf)
INSIDE_EDGES = (66, -66, 66.0, -66.0, math.nextafter(66.0, 0.0), math.nextafter(-66.0, 0.0))
POLAR = (ABOVE, BELOW, 66.000001, -66.000001, 66.5, 66.55, 66.58, -66.58, 70, -70, 75.0, -75.0,
         80, -80, 88.9, -88.9, 89, -89, 90, -90, 91.5, 1e20, -1e20, 10**20)
# Representative synthetic inputs: Indian birthplaces, the equator, both hemispheres,
# several dates and longitudes, and the band edges.
IN_BAND = [
    SYNTHETIC,
    {"birth_datetime": "1985-08-15T06:10:00+05:30", "timezone": "Asia/Kolkata", "latitude": 19.076, "longitude": 72.8777},
    {"birth_datetime": "1999-12-31T23:59:00+05:30", "timezone": "Asia/Kolkata", "latitude": 22.5726, "longitude": 88.3639},
    {"birth_datetime": "2024-02-29T04:45:00+05:30", "timezone": "Asia/Kolkata", "latitude": 8.5241, "longitude": 76.9366},
    {"birth_datetime": "2010-06-21T12:00:00+05:30", "timezone": "Asia/Kolkata", "latitude": 34.0837, "longitude": 74.7973},
    {"birth_datetime": "2024-03-10T12:00:00+00:00", "timezone": "UTC", "latitude": 0, "longitude": 0},
    {"birth_datetime": "2000-01-01T23:00:00+11:00", "timezone": "Australia/Sydney", "latitude": -33.8688, "longitude": 151.2093},
    {"birth_datetime": "2026-06-21T12:00:00+00:00", "timezone": "UTC", "latitude": 66.0, "longitude": 25.0},
    {"birth_datetime": "2026-12-21T00:00:00+00:00", "timezone": "UTC", "latitude": -66.0, "longitude": 0.0},
    {"birth_datetime": "2026-03-20T09:00:00+00:00", "timezone": "UTC", "latitude": 66, "longitude": -18.0},
    {"birth_datetime": "1975-01-01T00:00:00+00:00", "timezone": "UTC", "latitude": -66, "longitude": 180},
    {"birth_datetime": "2001-07-01T00:00:00+00:00", "timezone": "UTC", "latitude": 65.9999, "longitude": -180},
]


class BandValidationTests(unittest.TestCase):
    def assert_accepted(self, lat):
        # Passing validation reaches the ephemeris gate, which fails on the missing folder.
        with self.assertRaises(EphemerisDataError):
            calculate({**SYNTHETIC, "latitude": lat}, ephe_path=MISSING)

    def test_band_edges_and_interior_accepted(self):
        for lat in (*INSIDE_EDGES, 0, 0.0, -0.0, 28.6139, -33.8688, 60, -60, 65.9999):
            with self.subTest(latitude=lat):
                self.assert_accepted(lat)

    def test_outside_band_refused_with_code_before_swiss(self):
        with mock.patch.object(engine, "verify_ephemeris_dir") as ephemeris:
            for lat in POLAR:
                with self.subTest(latitude=lat):
                    with self.assertRaises(UnsupportedInputError) as ctx:
                        calculate({**SYNTHETIC, "latitude": lat}, ephe_path=MISSING)
                    self.assertEqual(ctx.exception.code, CODE)
                    self.assertIsInstance(ctx.exception, ValueError)
                    # Fixed text: the refused value is never echoed.
                    self.assertEqual(str(ctx.exception), f"{CODE}: latitude must be between -66 and 66 (inclusive)")
        ephemeris.assert_not_called()

    def test_refusal_is_independent_of_date_and_longitude(self):
        dates = ("1900-01-01T12:00:00+00:00", "1956-03-21T00:00:00+00:00", "2000-01-01T00:00:00+00:00",
                 "2050-01-01T00:00:00+00:00", "2100-12-31T12:00:00+00:00")
        for lat in (ABOVE, BELOW, 66.55, -66.55):
            for birth in dates:
                for lon in (-180, -74.006, 0, 77.209, 180):
                    with self.subTest(latitude=lat, birth=birth, longitude=lon):
                        request = {"birth_datetime": birth, "timezone": "UTC", "latitude": lat, "longitude": lon}
                        with self.assertRaises(UnsupportedInputError):
                            calculate(request, ephe_path=MISSING)

    def test_invalid_values_keep_their_existing_errors_first(self):
        cases = {True: "must be a number", False: "must be a number", "28.6": "must be a number",
                 None: "must be a number", float("nan"): "finite", float("inf"): "finite",
                 float("-inf"): "finite", 10**400: "finite", -10**400: "finite"}
        for value, text in cases.items():
            with self.subTest(latitude=value):
                with self.assertRaises(ValueError) as ctx:
                    calculate({**SYNTHETIC, "latitude": value}, ephe_path=MISSING)
                self.assertNotIsInstance(ctx.exception, UnsupportedInputError)
                self.assertIn(text, str(ctx.exception))

    def test_longitude_validation_unchanged(self):
        for lon in (-180, 180, -180.0, 180.0, 0, 77.209):
            with self.subTest(longitude=lon):
                with self.assertRaises(EphemerisDataError):
                    calculate({**SYNTHETIC, "longitude": lon}, ephe_path=MISSING)
        for lon in (180.000001, -180.000001, 181, -360, 10**20):
            with self.subTest(longitude=lon):
                with self.assertRaises(ValueError) as ctx:
                    calculate({**SYNTHETIC, "longitude": lon}, ephe_path=MISSING)
                self.assertNotIsInstance(ctx.exception, UnsupportedInputError)
                # P5 (D4) adds the code prefix; the detail text is unchanged.
                self.assertEqual(str(ctx.exception), "COORDINATE_INVALID: longitude must be between -180 and 180 (inclusive)")

    def test_cli_refusal_is_structured_and_private(self):
        env = {k: v for k, v in os.environ.items() if k != "SE_EPHE_PATH"}
        env.update({"PYTHONPATH": str(SRC), "SABPUJA_EPHE_PATH": MISSING})
        for lat in (66.5, -75.25):
            with self.subTest(latitude=lat):
                proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"],
                                      input=json.dumps({**SYNTHETIC, "latitude": lat}),
                                      capture_output=True, text=True, env=env)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")
                self.assertNotIn("Traceback", proc.stderr)
                payload = json.loads(proc.stderr)
                self.assertEqual(payload, {"error": f"{CODE}: latitude must be between -66 and 66 (inclusive)"})
                for secret in ("2000-01-01", "17:30", "Asia/Kolkata", str(lat), "77.209"):
                    self.assertNotIn(secret, proc.stderr)


class AscendantMethodTests(unittest.TestCase):
    """The band never changes or replaces the ascendant method (b"W" since P3, b"P" in P2)."""

    def setUp(self):
        for patch in (mock.patch.object(engine, "verify_ephemeris_dir", return_value="/mock"),
                      mock.patch.object(swisseph, "set_ephe_path"),
                      mock.patch.object(swisseph, "calc_ut",
                                        return_value=((10.0, 0.0, 1.0, 0.0, 0.0, 0.0), swisseph.FLG_SWIEPH))):
            patch.start()
            self.addCleanup(patch.stop)

    def test_every_in_band_request_uses_whole_sign_once(self):
        ascmc = (100.0,) + (0.0,) * 7
        for lat in (*INSIDE_EDGES, 0, 28.6139):
            with self.subTest(latitude=lat):
                with mock.patch.object(swisseph, "houses_ex", return_value=((0.0,) * 12, ascmc)) as houses:
                    calculate({**SYNTHETIC, "latitude": lat})
                houses.assert_called_once()
                self.assertEqual(houses.call_args.args[1:], (float(lat), 77.2090, b"W", swisseph.FLG_SIDEREAL))

    def test_out_of_band_never_reaches_any_house_method(self):
        with mock.patch.object(swisseph, "houses_ex") as houses, mock.patch.object(swisseph, "houses") as plain:
            for lat in (ABOVE, BELOW, 70.0):
                with self.subTest(latitude=lat), self.assertRaises(UnsupportedInputError):
                    calculate({**SYNTHETIC, "latitude": lat})
        houses.assert_not_called()
        plain.assert_not_called()

    def test_ascendant_failure_is_still_refused_not_replaced(self):
        with mock.patch.object(swisseph, "houses_ex", side_effect=swisseph.Error("houses_ex: error")) as houses:
            with self.assertRaises(ChartComputationError) as ctx:
                calculate({**SYNTHETIC, "latitude": 66.0})
        self.assertEqual(ctx.exception.code, "ASCENDANT_UNCOMPUTABLE")
        houses.assert_called_once()


DATA = os.environ.get("SABPUJA_TEST_EPHE_PATH")


@unittest.skipIf(DATA is None, "SABPUJA_TEST_EPHE_PATH unset: real-data integration tests not requested")
class RealDataBandTests(unittest.TestCase):
    def test_in_band_charts_equal_direct_swiss_placidus_values(self):
        # Unchanged by P3: inside the band the b"W" Lagna equals direct b"P" bit for bit.
        swe = swisseph
        for request in IN_BAND:
            with self.subTest(request=request):
                result = calculate(request, ephe_path=DATA)
                utc = engine._parse_birth(request["birth_datetime"], request["timezone"])
                jd = swe.julday(utc.year, utc.month, utc.day,
                                utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1_000_000) / 3600)
                with engine._SWISS_LOCK:
                    swe.set_ephe_path(DATA)
                    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
                    _, ascmc = swe.houses_ex(jd, float(request["latitude"]), float(request["longitude"]),
                                             b"P", swe.FLG_SIDEREAL)
                    moon = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]
                self.assertEqual(result["lagna"]["longitude_deg"], engine._display_deg(float(ascmc[0])))
                self.assertEqual(result["planets"]["moon"]["longitude_deg"], engine._display_deg(float(moon)))
                self.assertEqual(result["birth"]["latitude"], float(request["latitude"]))

    def test_band_edges_compute_on_every_date(self):
        # Placidus is defined at +-66.0 throughout 1900-2100 (polar circle >= 66.5467 deg).
        for year in (1900, 1950, 2000, 2050, 2100):
            for month in (3, 6, 12):
                for lat in (66.0, -66.0):
                    with self.subTest(year=year, month=month, latitude=lat):
                        request = {"birth_datetime": f"{year}-{month:02d}-21T06:00:00+00:00", "timezone": "UTC",
                                   "latitude": lat, "longitude": 25.0}
                        self.assertIn("lagna", calculate(request, ephe_path=DATA))

    def test_former_accepted_strip_is_now_refused(self):
        # 66.55 was accepted on 2100-12-31 and refused on 1900-01-01 before P2 (KUN-02 E-ENV-LAT).
        for birth in ("1900-01-01T12:00:00+00:00", "2100-12-31T12:00:00+00:00"):
            with self.subTest(birth=birth), self.assertRaises(UnsupportedInputError):
                calculate({"birth_datetime": birth, "timezone": "UTC", "latitude": 66.55, "longitude": 25.0},
                          ephe_path=DATA)


if __name__ == "__main__":
    unittest.main()
