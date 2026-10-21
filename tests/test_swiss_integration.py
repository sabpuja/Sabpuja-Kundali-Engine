"""Real Swiss Ephemeris integration for the manifest gate.

Skipped only when SABPUJA_TEST_EPHE_PATH is unset (optional developer run).
Once it is set, the directory must hold the pinned required files (see
data/ephemeris/README.md) or the whole class errors instead of skipping.
Proves fail-closed behaviour only, not astronomical accuracy against an
independent reference.
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

from sabpuja_kundali.engine import calculate
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


if __name__ == "__main__":
    unittest.main()
