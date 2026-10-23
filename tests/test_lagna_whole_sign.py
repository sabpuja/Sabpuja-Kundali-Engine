"""KUN-03 P3 (SCI-01e): Lagna = ascmc[0] of houses_ex(..., b"W", FLG_SIDEREAL).

Synthetic inputs only. Inside the SCI-01g band (P2) the b"W" ascendant is
bit-identical to b"P", so no accepted chart may change. b"W" computes at any
latitude, so the band must stay the only thing deciding acceptance. Real-data
cases run only when SABPUJA_TEST_EPHE_PATH is set.
"""
import math
import os
import unittest
from unittest import mock

import swisseph

from sabpuja_kundali import engine, provenance
from sabpuja_kundali.engine import ChartComputationError, UnsupportedInputError, calculate

SYNTHETIC = {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata",
             "latitude": 28.6139, "longitude": 77.2090}
EDGES = (66.0, -66.0, math.nextafter(66.0, 0.0), math.nextafter(-66.0, 0.0), 65.9999, -65.9999)
# Every 3 deg across the band, plus the edges and Indian birthplaces.
LATITUDES = tuple(float(x) for x in range(-63, 64, 3)) + EDGES + (8.5241, 19.076, 22.5726, 28.6139, 34.0837)
LONGITUDES = (-180.0, 0.0, 77.209, 151.2093)
BIRTHS = ("1900-01-01T00:00:00+00:00", "1900-06-21T12:00:00+00:00", "1947-08-15T00:00:00+00:00",
          "1975-03-20T06:00:00+00:00", "2000-01-01T12:00:00+00:00", "2026-09-23T18:30:00+00:00",
          "2049-12-31T23:59:59+00:00", "2050-01-01T00:00:00+00:00", "2075-12-21T03:15:00+00:00",
          "2100-12-31T12:00:00+00:00")


def _force_vehicle(hsys):
    """houses_ex wrapper that replaces only the house-system byte."""
    real = swisseph.houses_ex

    def call(jd, lat, lon, _hsys, flags):
        return real(jd, lat, lon, hsys, flags)
    return call


class VehicleTests(unittest.TestCase):
    def setUp(self):
        for patch in (mock.patch.object(engine, "verify_ephemeris_dir", return_value="/mock"),
                      mock.patch.object(swisseph, "set_ephe_path"),
                      mock.patch.object(swisseph, "calc_ut",
                                        return_value=((10.0, 0.0, 1.0, 0.0, 0.0, 0.0), swisseph.FLG_SWIEPH))):
            patch.start()
            self.addCleanup(patch.stop)

    def test_lagna_is_ascmc_zero_of_one_whole_sign_call(self):
        ascmc = (123.25, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0)
        cusps = tuple(float(30 * i) for i in range(12))
        with mock.patch.object(swisseph, "houses_ex", return_value=(cusps, ascmc)) as houses:
            result = calculate(SYNTHETIC)
        houses.assert_called_once()
        self.assertEqual(houses.call_args.args[3:], (b"W", swisseph.FLG_SIDEREAL))
        self.assertEqual(result["lagna"]["longitude_deg"], 123.25)
        self.assertEqual(result["lagna"]["rashi"], engine.sign(123.25))

    def test_no_fallback_to_another_house_method(self):
        with mock.patch.object(swisseph, "houses_ex", side_effect=swisseph.Error("houses_ex: error")) as houses, \
                mock.patch.object(swisseph, "houses") as plain:
            with self.assertRaises(ChartComputationError) as ctx:
                calculate(SYNTHETIC)
        self.assertEqual(ctx.exception.code, "ASCENDANT_UNCOMPUTABLE")
        houses.assert_called_once()
        plain.assert_not_called()

    def test_output_schema_and_method_fields_unchanged(self):
        # From P7 (schema 0.2.0) the ascendant vehicle is recorded in calculation metadata; the
        # 0.1.0 legacy projection and the method block are unchanged.
        with mock.patch.object(swisseph, "houses_ex", return_value=((0.0,) * 12, (100.0,) + (0.0,) * 7)):
            result = calculate(SYNTHETIC)
        self.assertEqual(result["schema_version"], "0.2.0")
        self.assertEqual(provenance.legacy_projection(result)["schema_version"], "0.1.0")
        ascendant = result["calculation_metadata"]["conventions"]["ascendant"]
        self.assertEqual((ascendant["swiss_function"], ascendant["swiss_house_system"], ascendant["value"]),
                         ("houses_ex", "W", "ascmc[0]"))
        self.assertEqual(set(result["method"]), {"ayanamsa", "nodes", "houses", "ephemeris", "binding_version"})
        self.assertEqual(result["method"]["houses"], "whole_sign")


DATA = os.environ.get("SABPUJA_TEST_EPHE_PATH")


@unittest.skipIf(DATA is None, "SABPUJA_TEST_EPHE_PATH unset: real-data integration tests not requested")
class RealDataLagnaTests(unittest.TestCase):
    @mock.patch.object(engine, "HISTORICAL_CLOCK_GATE", ())  # P8 (G1): calculation check on 1900-1969 dates; restored after the test
    def test_whole_sign_charts_identical_to_placidus_charts_in_band(self):
        # Same full output whether the vehicle is b"W" (P3) or forced back to b"P" (P2).
        checked = 0
        for birth in BIRTHS:
            for lat in LATITUDES:
                for lon in LONGITUDES:
                    request = {"birth_datetime": birth, "timezone": "UTC", "latitude": lat, "longitude": lon}
                    with self.subTest(request=request):
                        whole_sign = calculate(request, ephe_path=DATA)
                        with mock.patch.object(swisseph, "houses_ex", _force_vehicle(b"P")):
                            placidus = calculate(request, ephe_path=DATA)
                        self.assertEqual(whole_sign, placidus)
                        checked += 1
        self.assertEqual(checked, len(BIRTHS) * len(LATITUDES) * len(LONGITUDES))

    @mock.patch.object(engine, "HISTORICAL_CLOCK_GATE", ())  # P8 (G1): calculation check on 1900-1969 dates; restored after the test
    def test_raw_ascendant_bit_identical_at_band_edges(self):
        swe = swisseph
        for birth in BIRTHS:
            utc = engine._parse_birth(birth, "UTC")
            jd = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60 + utc.second / 3600)
            for lat in EDGES:
                with self.subTest(birth=birth, latitude=lat), engine._SWISS_LOCK:
                    swe.set_ephe_path(DATA)
                    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
                    _, w = swe.houses_ex(jd, lat, 25.0, b"W", swe.FLG_SIDEREAL)
                    _, p = swe.houses_ex(jd, lat, 25.0, b"P", swe.FLG_SIDEREAL)
                    self.assertEqual(w[0].hex(), p[0].hex())

    def test_band_still_refuses_where_whole_sign_would_compute(self):
        # b"W" returns an ascendant at 70 deg (precondition), yet the request is refused
        # by the band before Swiss, so P3 accepts no new location.
        jd = swisseph.julday(2026, 6, 21, 12.0)
        with engine._SWISS_LOCK:
            swisseph.set_ephe_path(DATA)
            swisseph.set_sid_mode(swisseph.SIDM_LAHIRI, 0, 0)
            _, ascmc = swisseph.houses_ex(jd, 70.0, 25.0, b"W", swisseph.FLG_SIDEREAL)
        self.assertTrue(math.isfinite(ascmc[0]))
        for lat in (math.nextafter(66.0, math.inf), 66.55, 70.0, -75.0, 89.0):
            with self.subTest(latitude=lat), mock.patch.object(swisseph, "houses_ex") as houses:
                with self.assertRaises(UnsupportedInputError) as ctx:
                    calculate({"birth_datetime": "2026-06-21T12:00:00+00:00", "timezone": "UTC",
                               "latitude": lat, "longitude": 25.0}, ephe_path=DATA)
                self.assertEqual(ctx.exception.code, "LATITUDE_OUTSIDE_SUPPORTED_BAND")
                houses.assert_not_called()


if __name__ == "__main__":
    unittest.main()
