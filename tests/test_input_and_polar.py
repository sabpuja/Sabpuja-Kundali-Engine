"""Numeric input hardening and polar ascendant failure, without Swiss data files.

Real pinned-data polar cases live in test_swiss_integration.py. Here Swiss is
either never reached (input rejected first) or mocked.
"""
import contextlib
import io
import json
import unittest
from unittest import mock

import swisseph

from sabpuja_kundali import cli, engine
from sabpuja_kundali.engine import ChartComputationError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError

SYNTHETIC = {
    "birth_datetime": "2000-01-01T17:30:00+05:30",
    "timezone": "Asia/Kolkata",
    "latitude": 28.6139,
    "longitude": 77.2090
}
MISSING = "/does-not-exist/sabpuja"
HUGE = "1" + "0" * 400  # 10**400 as JSON integer text


def run_cli(text):
    out, err = io.StringIO(), io.StringIO()
    # Real stdin has a byte buffer; the CLI's 4 KB limit counts bytes (KUN-03 P5-QA-01).
    with mock.patch("sys.stdin", io.TextIOWrapper(io.BytesIO(text.encode("utf-8")), encoding="utf-8")), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = cli.main()
    return code, out.getvalue(), err.getvalue()


def request_text(latitude="28.6139", longitude="77.2090"):
    # Raw JSON so non-standard tokens (NaN, Infinity, huge ints) reach the parser.
    return ('{"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata", '
            f'"latitude": {latitude}, "longitude": {longitude}}}')


class CoordinateValidationTests(unittest.TestCase):
    def assert_rejected(self, **fields):
        # ValueError (not EphemerisDataError) proves rejection before any data access.
        with self.assertRaises(ValueError):
            calculate({**SYNTHETIC, **fields}, ephe_path=MISSING)

    def assert_accepted(self, **fields):
        # Passing validation reaches the ephemeris gate, which fails on the missing folder.
        with self.assertRaises(EphemerisDataError):
            calculate({**SYNTHETIC, **fields}, ephe_path=MISSING)

    def test_huge_integer_rejected(self):
        self.assert_rejected(latitude=10**400)
        self.assert_rejected(longitude=10**400)
        self.assert_rejected(latitude=-10**400)

    def test_non_finite_rejected(self):
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                self.assert_rejected(latitude=value)
                self.assert_rejected(longitude=value)

    def test_boolean_and_non_number_rejected(self):
        for value in (True, False, "28.6", None, [28.6]):
            with self.subTest(value=value):
                self.assert_rejected(latitude=value)
                self.assert_rejected(longitude=value)

    def test_out_of_range_rejected(self):
        for lat in (89, -89, 89.0, 90, -90.5):
            with self.subTest(latitude=lat):
                self.assert_rejected(latitude=lat)
        for lon in (180.000001, -180.000001, 181, -360):
            with self.subTest(longitude=lon):
                self.assert_rejected(longitude=lon)

    def test_accepted_range(self):
        # KUN-03 P2 (SCI-01g): the supported band is -66.0 to 66.0 inclusive. The
        # polar latitudes once listed here (70, 80, 88.9, 88.999999 and their
        # negatives) are now refused; see test_polar_latitudes_refused_by_band.
        for lat in (28.6139, -33.8688, 0, 66, -66, 66.0, -66.0):
            with self.subTest(latitude=lat):
                self.assert_accepted(latitude=lat)
        for lon in (-180, 180, -180.0, 180.0, 0):
            with self.subTest(longitude=lon):
                self.assert_accepted(longitude=lon)

    def test_polar_latitudes_refused_by_band(self):
        for lat in (70, -70, 80, -80, 88.9, -88.9, 88.999999):
            with self.subTest(latitude=lat):
                with self.assertRaises(engine.UnsupportedInputError) as ctx:
                    calculate({**SYNTHETIC, "latitude": lat}, ephe_path=MISSING)
                self.assertEqual(ctx.exception.code, "LATITUDE_OUTSIDE_SUPPORTED_BAND")

    def test_large_finite_integer_rejected_as_range(self):
        with self.assertRaisesRegex(ValueError, "between"):
            calculate({**SYNTHETIC, "latitude": 10**20}, ephe_path=MISSING)

    def test_messages_do_not_echo_values(self):
        with self.assertRaises(ValueError) as ctx:
            calculate({**SYNTHETIC, "latitude": 123.456}, ephe_path=MISSING)
        self.assertNotIn("123.456", str(ctx.exception))


class MockedSwissTests(unittest.TestCase):
    """Drive calculate() past the gate with Swiss calls mocked."""

    def setUp(self):
        patches = [
            mock.patch.object(engine, "verify_ephemeris_dir", return_value="/mock"),
            mock.patch.object(swisseph, "set_ephe_path"),
            mock.patch.object(swisseph, "calc_ut",
                              return_value=((10.0, 0.0, 1.0, 0.0, 0.0, 0.0), swisseph.FLG_SWIEPH)),
        ]
        for patch in patches:
            patch.start()
            self.addCleanup(patch.stop)

    def test_swiss_error_becomes_structured_failure(self):
        # Defensive path: the band keeps real requests inside the polar circles, so
        # Swiss is mocked to fail at an in-band latitude (was 70.0 before KUN-03 P2).
        with mock.patch.object(swisseph, "houses_ex", side_effect=swisseph.Error("houses_ex: error")):
            with self.assertRaises(ChartComputationError) as ctx:
                calculate({**SYNTHETIC, "latitude": 45.5})
        self.assertEqual(ctx.exception.code, "ASCENDANT_UNCOMPUTABLE")
        self.assertIsInstance(ctx.exception, RuntimeError)
        self.assertNotIn("45.5", str(ctx.exception))

    def test_other_houses_exceptions_not_swallowed(self):
        with mock.patch.object(swisseph, "houses_ex", side_effect=TypeError("bug")):
            with self.assertRaises(TypeError):
                calculate(SYNTHETIC)

    def test_house_method_and_flags(self):
        # KUN-03 P3 (SCI-01e): whole-sign vehicle; was b"P" before P3.
        ascmc = (100.0,) + (0.0,) * 7
        with mock.patch.object(swisseph, "houses_ex", return_value=((0.0,) * 12, ascmc)) as houses:
            calculate(SYNTHETIC)
        args = houses.call_args.args
        self.assertEqual(args[3], b"W")
        self.assertEqual(args[4], swisseph.FLG_SIDEREAL)

    def test_cli_polar_failure_exit_2_without_traceback(self):
        with mock.patch.object(swisseph, "houses_ex", side_effect=swisseph.Error("houses_ex: error")):
            code, out, err = run_cli(request_text(latitude="45.5"))  # was 70 before KUN-03 P2
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        payload = json.loads(err)
        self.assertEqual(list(payload), ["error"])
        self.assertTrue(payload["error"].startswith("ASCENDANT_UNCOMPUTABLE: "))
        self.assertNotIn("Traceback", err)


class CliInputTests(unittest.TestCase):
    CASES = {
        "huge latitude": request_text(latitude=HUGE),
        "huge longitude": request_text(longitude=HUGE),
        "negative huge latitude": request_text(latitude="-" + HUGE),
        "NaN latitude": request_text(latitude="NaN"),
        "Infinity longitude": request_text(longitude="Infinity"),
        "-Infinity latitude": request_text(latitude="-Infinity"),
        "float overflow to inf": request_text(latitude="1e400"),
        "boolean latitude": request_text(latitude="true"),
        "latitude 89": request_text(latitude="89"),
        "longitude 180.5": request_text(longitude="180.5"),
    }

    def test_rejections_are_structured_and_private(self):
        for label, text in self.CASES.items():
            with self.subTest(label):
                code, out, err = run_cli(text)
                self.assertEqual(code, 2)
                self.assertEqual(out, "")
                payload = json.loads(err)
                self.assertEqual(list(payload), ["error"])
                self.assertNotIn("Traceback", err)
                for secret in ("2000-01-01", "17:30", "Asia/Kolkata", "28.6139", "77.209", HUGE[:20]):
                    self.assertNotIn(secret, err)


if __name__ == "__main__":
    unittest.main()
