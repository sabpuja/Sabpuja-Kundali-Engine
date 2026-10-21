"""Real Swiss Ephemeris integration for the manifest gate.

Skipped only when SABPUJA_TEST_EPHE_PATH is unset (optional developer run).
Once it is set, the directory must hold the pinned required files (see
data/ephemeris/README.md) or the whole class errors instead of skipping.
Proves fail-closed behaviour, polar ascendant refusal and run-to-run
determinism only, not astronomical accuracy against an independent reference.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sabpuja_kundali.engine import ChartComputationError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError, verify_ephemeris_dir

DATA_ENV = "SABPUJA_TEST_EPHE_PATH"
DATA = os.environ.get(DATA_ENV)
SYNTHETIC = {
    "birth_datetime": "2000-01-01T17:30:00+05:30",
    "timezone": "Asia/Kolkata",
    "latitude": 28.6139,
    "longitude": 77.2090
}


# Stand-in for the optional asteroid file when it is not supplied: the gate must
# ignore it either way, so these cases never need to skip.
ASTEROID_STAND_IN = b"optional asteroid file stand-in"


@unittest.skipIf(DATA is None, f"{DATA_ENV} unset: real-data integration tests not requested")
class SwissIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Explicitly requested real-data run: incomplete or wrong data is a failure, not a skip.
        try:
            with mock.patch.dict(os.environ):
                os.environ.pop("SE_EPHE_PATH", None)
                verify_ephemeris_dir(DATA)
        except EphemerisDataError as exc:
            raise AssertionError(f"{DATA_ENV} is set but does not hold the pinned required files: {exc}") from None

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("SE_EPHE_PATH", None)

    def tearDown(self):
        self._tmp.cleanup()

    def copy(self, *names):
        for name in names:
            source = Path(DATA, name)
            if name == "seas_18.se1" and not source.is_file():
                (self.dir / name).write_bytes(ASTEROID_STAND_IN)
            else:
                shutil.copy(source, self.dir / name)

    def calc_ut_spy(self):
        import swisseph
        return mock.patch.object(swisseph, "calc_ut", wraps=swisseph.calc_ut)

    def test_full_required_set_uses_moon_file(self):
        import swisseph as swe
        self.copy("sepl_18.se1", "semo_18.se1")
        result = calculate(SYNTHETIC, ephe_path=str(self.dir))
        self.assertEqual(set(result["planets"]), {"sun", "moon", "mars", "mercury", "jupiter",
                                                  "venus", "saturn", "rahu_mean", "ketu_mean"})
        # The engine's Moon must differ from a Moshier Moon for the same instant.
        jd = swe.julday(2000, 1, 1, 12.0)
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        moshier = swe.calc_ut(jd, swe.MOON, swe.FLG_MOSEPH | swe.FLG_SIDEREAL)[0][0]
        self.assertNotEqual(round(moshier, 8), result["planets"]["moon"]["longitude_deg"])

    def test_planets_file_only_fails_before_calc_ut(self):
        self.copy("sepl_18.se1")
        with self.calc_ut_spy() as spy:
            with self.assertRaises(EphemerisDataError) as ctx:
                calculate(SYNTHETIC, ephe_path=str(self.dir))
        self.assertEqual(ctx.exception.code, "EPHEMERIS_FILE_MISSING")
        self.assertIn("semo_18.se1", str(ctx.exception))
        spy.assert_not_called()

    def test_planets_and_asteroid_files_fail(self):
        self.copy("sepl_18.se1", "seas_18.se1")
        with self.assertRaises(EphemerisDataError):
            calculate(SYNTHETIC, ephe_path=str(self.dir))

    def test_asteroid_only_fails(self):
        self.copy("seas_18.se1")
        with self.assertRaises(EphemerisDataError):
            calculate(SYNTHETIC, ephe_path=str(self.dir))

    def test_moon_file_only_fails(self):
        self.copy("semo_18.se1")
        with self.assertRaises(EphemerisDataError):
            calculate(SYNTHETIC, ephe_path=str(self.dir))

    def test_corrupted_moon_file_fails_before_calc_ut(self):
        self.copy("sepl_18.se1", "semo_18.se1")
        data = bytearray((self.dir / "semo_18.se1").read_bytes())
        data[len(data) // 2] ^= 0xFF
        (self.dir / "semo_18.se1").write_bytes(bytes(data))
        with self.calc_ut_spy() as spy:
            with self.assertRaises(EphemerisDataError) as ctx:
                calculate(SYNTHETIC, ephe_path=str(self.dir))
        self.assertEqual(ctx.exception.code, "EPHEMERIS_FILE_MISMATCH")
        spy.assert_not_called()

    def test_se_ephe_path_override_fails(self):
        self.copy("sepl_18.se1", "semo_18.se1")
        os.environ["SE_EPHE_PATH"] = DATA
        with self.assertRaises(EphemerisDataError) as ctx:
            calculate(SYNTHETIC, ephe_path=str(self.dir))
        self.assertEqual(ctx.exception.code, "EPHEMERIS_PATH_OVERRIDE")

    def test_cli_planets_file_only_exits_2(self):
        self.copy("sepl_18.se1")
        env = {k: v for k, v in os.environ.items() if k != "SE_EPHE_PATH"}
        env["SABPUJA_EPHE_PATH"] = str(self.dir)
        proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"],
                              input=json.dumps(SYNTHETIC), capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertEqual(json.loads(proc.stderr),
                         {"error": "EPHEMERIS_FILE_MISSING: required file semo_18.se1 not found"})

    def test_polar_latitudes_refused_with_structured_error(self):
        for lat in (70, -70, 80, -80, 88.9, -88.9):
            with self.subTest(latitude=lat):
                with self.assertRaises(ChartComputationError) as ctx:
                    calculate({**SYNTHETIC, "latitude": lat}, ephe_path=DATA)
                self.assertEqual(ctx.exception.code, "ASCENDANT_UNCOMPUTABLE")

    def test_supported_latitudes_and_longitude_bounds_compute(self):
        cases = [
            SYNTHETIC,  # Delhi
            {"birth_datetime": "2000-01-01T23:00:00+11:00", "timezone": "Australia/Sydney",
             "latitude": -33.8688, "longitude": 151.2093},
            {**SYNTHETIC, "longitude": 180},
            {**SYNTHETIC, "longitude": -180},
        ]
        for request in cases:
            with self.subTest(request=request["timezone"], longitude=request["longitude"]):
                result = calculate(request, ephe_path=DATA)
                self.assertEqual(result["method"]["houses"], "whole_sign")
                self.assertEqual(result["birth"]["latitude"], float(request["latitude"]))

    def test_valid_output_deterministic(self):
        first = json.dumps(calculate(SYNTHETIC, ephe_path=DATA), sort_keys=True)
        second = json.dumps(calculate(dict(SYNTHETIC), ephe_path=DATA), sort_keys=True)
        self.assertEqual(first, second)

    def test_cli_polar_exits_2_without_traceback_or_birth_data(self):
        env = {k: v for k, v in os.environ.items() if k != "SE_EPHE_PATH"}
        env["SABPUJA_EPHE_PATH"] = DATA
        for lat in (70, -88.9):
            with self.subTest(latitude=lat):
                proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"],
                                      input=json.dumps({**SYNTHETIC, "latitude": lat}),
                                      capture_output=True, text=True, env=env)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")
                payload = json.loads(proc.stderr)
                self.assertEqual(list(payload), ["error"])
                self.assertTrue(payload["error"].startswith("ASCENDANT_UNCOMPUTABLE: "))
                self.assertNotIn("Traceback", proc.stderr)
                for secret in ("2000-01-01", "Asia/Kolkata", str(lat), "77.209"):
                    self.assertNotIn(secret, proc.stderr)

    def test_categories_match_exact_oracle_on_raw_swiss_values(self):
        # Every category must come from the unrounded Swiss longitude, and the
        # displayed value must be its 8-decimal rounding inside [0, 360).
        import swisseph
        from fractions import Fraction
        from boundary_oracle import expected, expected_house
        requests = [
            SYNTHETIC,
            {"birth_datetime": "1985-07-14T04:12:00+05:30", "timezone": "Asia/Kolkata",
             "latitude": 19.076, "longitude": 72.8777},
            {"birth_datetime": "2024-03-10T12:00:00+00:00", "timezone": "UTC", "latitude": 0, "longitude": 0},
            {"birth_datetime": "1950-12-31T23:59:59+00:00", "timezone": "UTC", "latitude": 51, "longitude": -0.1},
            {"birth_datetime": "2099-12-31T00:00:00-05:00", "timezone": "America/New_York",
             "latitude": 40.7128, "longitude": -74.006},
        ]
        names = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu_mean"]
        for request in requests:
            raw, asc = [], []
            real_calc, real_houses = swisseph.calc_ut, swisseph.houses_ex

            def calc(*args):
                result = real_calc(*args)
                raw.append(result[0][0])
                return result

            def houses(*args):
                result = real_houses(*args)
                asc.append(result[1][0])
                return result

            with self.subTest(request=request["birth_datetime"]), \
                    mock.patch.object(swisseph, "calc_ut", calc), mock.patch.object(swisseph, "houses_ex", houses):
                out = calculate(request, ephe_path=DATA)
                sources = dict(zip(names, raw), ketu_mean=Fraction(raw[-1]) + 180)
                self.assertEqual(list(out["planets"]), names + ["ketu_mean"])
                for name, source in sources.items():
                    want = expected(source)
                    got = out["planets"][name]
                    self.assertEqual((got["rashi"], got["navamsa_rashi"]), (want["rashi"], want["navamsa_rashi"]))
                    self.assertEqual(got["whole_sign_house"], expected_house(source, asc[0]))
                    self.assertTrue(0.0 <= got["longitude_deg"] < 360.0)
                    shown = round(float(source % 360) if isinstance(source, Fraction) else source % 360.0, 8)
                    self.assertEqual(got["longitude_deg"], 0.0 if shown == 360.0 else shown)
                self.assertEqual(out["moon_nakshatra"], expected(sources["moon"])["nakshatra"])
                lagna = expected(asc[0])
                self.assertEqual(out["lagna"]["rashi"], lagna["rashi"])
                self.assertEqual(out["lagna"]["navamsa_rashi"], lagna["navamsa_rashi"])


if __name__ == "__main__":
    unittest.main()
