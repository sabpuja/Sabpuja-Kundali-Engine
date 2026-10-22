"""KUN-03 P5 (D1-D4): deterministic input refusal codes and their fixed order.

Synthetic inputs only. Every input refusal is an InputRefusalError (a ValueError)
with a stable code; the earliest failing check decides the code. Accepted
conforming inputs keep exactly the UTC instant the previous parser gave.
"""
import json
import os
import random
import subprocess
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sabpuja_kundali import engine
from sabpuja_kundali.engine import InputRefusalError, UnsupportedInputError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError

SRC = Path(__file__).resolve().parents[1] / "src"
MISSING = "/nonexistent/sabpuja-ephemeris"
BASE = {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata",
        "latitude": 28.6139, "longitude": 77.2090}
# Fixed order (docs/api-contract.md). Reserved codes are not raised in P5.
ORDER = ("REQUEST_INVALID", "TIME_FORMAT_INVALID", "TIME_OFFSET_REQUIRED", "TIME_LEAP_SECOND_UNSUPPORTED",
         "DATE_INVALID", "TIMEZONE_INVALID", "DATE_OUTSIDE_SUPPORTED_RANGE", "TIME_NONEXISTENT_LOCAL",
         "TIME_OFFSET_MISMATCH", "COORDINATE_INVALID", "LATITUDE_OUTSIDE_SUPPORTED_BAND")
ENVELOPE = {"TIME_LEAP_SECOND_UNSUPPORTED", "DATE_OUTSIDE_SUPPORTED_RANGE", "LATITUDE_OUTSIDE_SUPPORTED_BAND"}


def _code(**fields):
    try:
        calculate({**BASE, **fields}, ephe_path=MISSING)
    except InputRefusalError as exc:
        return exc.code
    except EphemerisDataError:
        return "ACCEPT"
    raise AssertionError("neither refused nor stopped at the ephemeris gate")


def _previous_parse(text, key):
    """P4's parser (fromisoformat), kept here as the reference for unchanged results."""
    local = datetime.fromisoformat(text)
    if local.tzinfo is None:
        return None
    zone = ZoneInfo(key)
    if not engine.SUPPORTED_LOCAL_DATES[0] <= local.date() <= engine.SUPPORTED_LOCAL_DATES[1]:
        return None
    actual = local.astimezone(zone)
    if actual.replace(tzinfo=None) != local.replace(tzinfo=None) or actual.utcoffset() != local.utcoffset():
        return None
    return local.astimezone(timezone.utc)


class StrictFormatTests(unittest.TestCase):
    def test_profile_forms_accepted_without_coercion(self):
        cases = {
            "2000-01-01T17:30+05:30": "2000-01-01T12:00:00+00:00",
            "2000-01-01T17:30:00+05:30": "2000-01-01T12:00:00+00:00",
            "2000-01-01T17:30:00.5+05:30": "2000-01-01T12:00:00.500000+00:00",
            "2000-01-01T17:30:00.123456+05:30": "2000-01-01T12:00:00.123456+00:00",
            "2000-01-01T17:30:00.000001+05:30": "2000-01-01T12:00:00.000001+00:00",
            "1900-01-01T00:00:00+05:21:10": "1899-12-31T18:38:50+00:00",
        }
        for text, utc in cases.items():
            with self.subTest(text=text):
                self.assertEqual(engine._parse_birth(text, "Asia/Kolkata").isoformat(), utc)
        self.assertEqual(engine._parse_birth("2000-01-01T12:00:00Z", "UTC").isoformat(), "2000-01-01T12:00:00+00:00")
        self.assertEqual(engine._parse_birth("2000-01-01T12:00:00-00:00", "UTC").isoformat(), "2000-01-01T12:00:00+00:00")

    def test_forms_outside_the_profile_refused(self):
        refused = (
            "2000-01-01 17:30:00+05:30", "2000-01-01t17:30:00+05:30", "20000101T173000+0530",
            "2000-W01-6T17:30:00+05:30", "2000-001T17:30:00+05:30", "2000-01-01T17+05:30",
            "2000-01-01T1730+05:30", "2000-01-01T17:30:00,5+05:30", "2000-01-01T17:30:00.1234567+05:30",
            "2000-01-01T17:30:00.+05:30", "2000-01-01T17:30.5+05:30", "2000-01-01T17:30:00+0530",
            "2000-01-01T17:30:00+05", "2000-01-01T17:30:00+5:30", "2000-01-01T17:30:00+05:30:1",
            "2000-01-01T12:00:00z", "2000-01-01T12:00:00 Z", "2000-01-01T12:00:00Z+00:00",
            "2000-01-01T24:00:00+05:30", "2000-01-01T25:00:00+05:30", "2000-01-01T17:60:00+05:30",
            "2000-01-01T17:30:61+05:30", "2000-01-01T17:30:00+24:00", "2000-01-01T17:30:00+05:60",
            "2000-01-01T17:30:00+05:30:60", "٢000-01-01T17:30:00+05:30", "２000-01-01T17:30:00+05:30",
            " 2000-01-01T17:30:00+05:30", "2000-01-01T17:30:00+05:30 ", "2000-01-01T17:30:00+05:30\n",
            "+2000-01-01T17:30:00+05:30", "02000-01-01T17:30:00+05:30", "2000-1-01T17:30:00+05:30", "",
        )
        for text in refused:
            with self.subTest(text=text):
                self.assertEqual(_code(birth_datetime=text), "TIME_FORMAT_INVALID")

    def test_missing_offset_leap_second_and_invalid_dates(self):
        cases = {
            "2000-01-01T17:30:00": "TIME_OFFSET_REQUIRED",
            "2000-01-01T17:30": "TIME_OFFSET_REQUIRED",
            "2000-01-01T17:30:00.25": "TIME_OFFSET_REQUIRED",
            "2016-12-31T23:59:60+00:00": "TIME_LEAP_SECOND_UNSUPPORTED",   # KUN-02 T40 (UTC zone below)
            "2017-01-01T05:29:60+05:30": "TIME_LEAP_SECOND_UNSUPPORTED",   # T41
            "1900-02-29T12:00:00+05:21:10": "DATE_INVALID",                 # T42
            "2100-02-29T12:00:00+05:30": "DATE_INVALID",                    # T45
            "2023-02-29T12:00:00+05:30": "DATE_INVALID",
            "2000-04-31T12:00:00+05:30": "DATE_INVALID",
            "2000-13-01T12:00:00+05:30": "DATE_INVALID",
            "2000-00-10T12:00:00+05:30": "DATE_INVALID",
            "2000-01-00T12:00:00+05:30": "DATE_INVALID",
            "0000-01-01T12:00:00+05:30": "DATE_INVALID",
            "2000-02-29T12:00:00+05:30": "ACCEPT",
            "2024-02-29T12:00:00+05:30": "ACCEPT",
        }
        for text, code in cases.items():
            with self.subTest(text=text):
                self.assertEqual(_code(birth_datetime=text), code)
        self.assertEqual(_code(birth_datetime="2016-12-31T23:59:60+00:00", timezone="UTC"),
                         "TIME_LEAP_SECOND_UNSUPPORTED")


class GapAndMismatchTests(unittest.TestCase):
    def test_gaps_are_nonexistent_for_every_offset(self):
        gaps = (  # KUN-02 IDs where the fixture has them
            ("1906-01-01T00:00:00+05:30", "Asia/Kolkata"), ("1906-01-01T00:05:00+05:21:10", "Asia/Kolkata"),  # T05, T07
            ("1941-10-01T00:30:00+05:30", "Asia/Kolkata"), ("1941-10-01T00:30:00+06:30", "Asia/Kolkata"),    # T08, T09
            ("2021-03-14T02:30:00-05:00", "America/New_York"), ("2021-03-14T02:30:00-04:00", "America/New_York"),
            ("2021-03-28T01:30:00+00:00", "Europe/London"), ("2021-03-28T01:30:00+01:00", "Europe/London"),
            ("2021-10-03T02:30:00+10:00", "Australia/Sydney"), ("2021-10-03T02:30:00+11:00", "Australia/Sydney"),
            ("2011-12-30T12:00:00+14:00", "Pacific/Apia"), ("2011-12-30T12:00:00-10:00", "Pacific/Apia"),     # T38, T39
            ("2011-12-30T12:00:00+05:30", "Pacific/Apia"),
        )
        for text, key in gaps:
            with self.subTest(text=text, timezone=key):
                self.assertEqual(_code(birth_datetime=text, timezone=key), "TIME_NONEXISTENT_LOCAL")

    def test_existing_wall_time_with_a_wrong_offset_is_a_mismatch(self):
        cases = (
            ("1905-06-15T12:00:00+05:30", "Asia/Kolkata"),    # T03
            ("1943-06-15T12:00:00+05:30", "Asia/Kolkata"),    # T11
            ("2000-01-01T12:00:00Z", "Asia/Kolkata"),         # T53
            ("2000-01-01T17:30:00+04:00", "Asia/Kolkata"),
            ("2021-11-07T01:30:00-06:00", "America/New_York"),  # fold, third offset
        )
        for text, key in cases:
            with self.subTest(text=text, timezone=key):
                self.assertEqual(_code(birth_datetime=text, timezone=key), "TIME_OFFSET_MISMATCH")

    def test_folds_accept_both_offsets_one_hour_apart(self):
        for first, second, key in (
                ("2021-11-07T01:30:00-04:00", "2021-11-07T01:30:00-05:00", "America/New_York"),
                ("2021-10-31T01:30:00+01:00", "2021-10-31T01:30:00+00:00", "Europe/London"),
                ("2021-04-04T02:30:00+11:00", "2021-04-04T02:30:00+10:00", "Australia/Sydney")):
            with self.subTest(timezone=key):
                self.assertEqual(engine._parse_birth(second, key) - engine._parse_birth(first, key), timedelta(hours=1))

    def test_reserved_codes_are_not_raised(self):
        # D3: TIMEZONE_NOT_LOCATION_BASED is reserved only; P8 owns HISTORICAL_CLOCK_UNVERIFIED.
        self.assertEqual(set(engine.RESERVED_CODES), {"TIMEZONE_NOT_LOCATION_BASED", "HISTORICAL_CLOCK_UNVERIFIED"})
        for text, key in (("2000-01-01T17:00:00+05:00", "Etc/GMT-5"), ("2000-01-01T12:00:00+00:00", "UTC"),
                          ("1950-06-15T12:00:00+05:30", "Asia/Kolkata"), ("1900-06-15T12:00:00+05:21:10", "Asia/Kolkata")):
            with self.subTest(text=text, timezone=key):
                self.assertEqual(_code(birth_datetime=text, timezone=key), "ACCEPT")


class OrderTests(unittest.TestCase):
    def test_each_check_precedes_the_next(self):
        # Each request fails the named check and every later one; the earliest wins.
        bad = {"latitude": 70.0, "longitude": 200.0}
        cases = (
            ({"birth_datetime": 5, **bad}, "REQUEST_INVALID"),
            ({"birth_datetime": "2000-01-01 17:30:00", "timezone": "Mars/Base", **bad}, "TIME_FORMAT_INVALID"),
            ({"birth_datetime": "2016-12-31T23:59:60", "timezone": "Mars/Base"}, "TIME_OFFSET_REQUIRED"),
            ({"birth_datetime": "1899-02-29T23:59:60+05:30", "timezone": "Mars/Base"}, "TIME_LEAP_SECOND_UNSUPPORTED"),
            ({"birth_datetime": "1899-02-29T12:00:00+05:30", "timezone": "Mars/Base"}, "DATE_INVALID"),
            ({"birth_datetime": "1899-12-31T12:00:00+05:30", "timezone": "Mars/Base", **bad}, "TIMEZONE_INVALID"),
            ({"birth_datetime": "2101-03-13T02:30:00+09:00", "timezone": "America/New_York", **bad},
             "DATE_OUTSIDE_SUPPORTED_RANGE"),
            ({"birth_datetime": "2021-03-14T02:30:00+09:00", "timezone": "America/New_York", **bad},
             "TIME_NONEXISTENT_LOCAL"),
            ({"birth_datetime": "2021-03-14T12:00:00+09:00", "timezone": "America/New_York", **bad},
             "TIME_OFFSET_MISMATCH"),
            ({"latitude": float("nan"), "longitude": 200.0}, "COORDINATE_INVALID"),
            ({"latitude": 70.0, "longitude": 200.0}, "COORDINATE_INVALID"),
            ({"latitude": "70"}, "COORDINATE_INVALID"),
            ({"latitude": 70.0}, "LATITUDE_OUTSIDE_SUPPORTED_BAND"),
            ({"latitude": 10**20}, "LATITUDE_OUTSIDE_SUPPORTED_BAND"),
        )
        for fields, code in cases:
            with self.subTest(fields=fields):
                self.assertEqual(_code(**fields), code)

    def test_time_refusals_come_before_coordinate_refusals(self):
        for lat in (float("nan"), 95.0, 70.0, True):
            with self.subTest(latitude=lat):
                self.assertEqual(_code(birth_datetime="2000-01-01T17:30:00", latitude=lat), "TIME_OFFSET_REQUIRED")

    def test_request_shape(self):
        for request in (None, [], "x", {**BASE, "name": "x"}, {k: v for k, v in BASE.items() if k != "timezone"},
                        {**BASE, "timezone": None}, {**BASE, "birth_datetime": b"2000"}):
            with self.subTest(request=request), self.assertRaises(InputRefusalError) as ctx:
                calculate(request, ephe_path=MISSING)
            self.assertEqual(ctx.exception.code, "REQUEST_INVALID")

    def test_every_refusal_is_typed_and_coded(self):
        self.assertTrue(issubclass(UnsupportedInputError, InputRefusalError))
        samples = {"TIME_FORMAT_INVALID": {"birth_datetime": "x"},
                   "TIME_LEAP_SECOND_UNSUPPORTED": {"birth_datetime": "2017-01-01T05:29:60+05:30"},
                   "DATE_OUTSIDE_SUPPORTED_RANGE": {"birth_datetime": "1899-12-31T12:00:00+05:21:10"},
                   "TIME_OFFSET_MISMATCH": {"birth_datetime": "2000-01-01T17:30:00+04:00"},
                   "COORDINATE_INVALID": {"longitude": 181},
                   "LATITUDE_OUTSIDE_SUPPORTED_BAND": {"latitude": 66.5}}
        for code, fields in samples.items():
            with self.subTest(code=code), self.assertRaises(ValueError) as ctx:
                calculate({**BASE, **fields}, ephe_path=MISSING)
            self.assertIsInstance(ctx.exception, InputRefusalError)
            self.assertEqual(ctx.exception.code, code)
            self.assertTrue(str(ctx.exception).startswith(code + ": "))
            self.assertEqual(isinstance(ctx.exception, UnsupportedInputError), code in ENVELOPE)


class UnchangedResultTests(unittest.TestCase):
    def test_conforming_inputs_keep_the_previous_outcome_and_instant(self):
        # 6,000 seeded conforming strings across gaps, folds and window edges.
        rng = random.Random(20261022)
        zones = ("Asia/Kolkata", "America/New_York", "Europe/London", "Australia/Sydney", "Pacific/Apia",
                 "Pacific/Kiritimati", "Etc/GMT+12", "Asia/Kathmandu", "America/St_Johns", "UTC")
        days = ("1900-01-01", "1906-01-01", "1941-10-01", "1945-10-15", "2011-12-30", "2021-03-14",
                "2021-03-28", "2021-10-03", "2021-11-07", "2021-04-04", "2021-10-31", "2100-12-31")
        offsets = ("+05:30", "+05:21:10", "+06:30", "-05:00", "-04:00", "+00:00", "+01:00", "+10:00",
                   "+11:00", "+13:00", "+14:00", "-10:00", "-11:00", "-12:00", "+05:45", "-03:30", "-02:30", "Z")
        compared = accepted = 0
        for _ in range(6000):
            text = (f"{rng.choice(days)}T{rng.randrange(24):02d}:{rng.choice((0, 5, 30, 59)):02d}:"
                    f"{rng.randrange(60):02d}{rng.choice(('', '.5', '.123456'))}{rng.choice(offsets)}")
            key = rng.choice(zones)
            before = _previous_parse(text, key)
            try:
                after = engine._parse_birth(text, key)
            except InputRefusalError as exc:
                self.assertIsNone(before, (text, key))
                self.assertIn(exc.code, {"DATE_OUTSIDE_SUPPORTED_RANGE", "TIME_NONEXISTENT_LOCAL", "TIME_OFFSET_MISMATCH"})
            else:
                self.assertEqual(after, before, (text, key))
                self.assertEqual(after.utcoffset(), timedelta(0))
                accepted += 1
            compared += 1
        self.assertEqual(compared, 6000)
        self.assertGreater(accepted, 300)


class CliPrivacyTests(unittest.TestCase):
    SECRETS = ("1899", "2000-01-01", "2017", "17:30", "05:29", "Asia/Kolkata", "Mars", "28.6139", "77.209", "181")

    def run_cli(self, text):
        env = {**os.environ, "PYTHONPATH": str(SRC), "SABPUJA_EPHE_PATH": MISSING}
        return subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"], input=text, text=True,
                              capture_output=True, env=env, timeout=60)

    def test_every_code_is_structured_and_private(self):
        cases = {
            "REQUEST_INVALID": json.dumps({**BASE, "name": "x"}),
            "TIME_FORMAT_INVALID": json.dumps({**BASE, "birth_datetime": "2000-01-01 17:30:00+05:30"}),
            "TIME_OFFSET_REQUIRED": json.dumps({**BASE, "birth_datetime": "2000-01-01T17:30:00"}),
            "TIME_LEAP_SECOND_UNSUPPORTED": json.dumps({**BASE, "birth_datetime": "2017-01-01T05:29:60+05:30"}),
            "DATE_INVALID": json.dumps({**BASE, "birth_datetime": "2017-02-29T17:30:00+05:30"}),
            "TIMEZONE_INVALID": json.dumps({**BASE, "timezone": "Mars/Base"}),
            "DATE_OUTSIDE_SUPPORTED_RANGE": json.dumps({**BASE, "birth_datetime": "1899-12-31T17:30:00+05:21:10"}),
            "TIME_NONEXISTENT_LOCAL": json.dumps({**BASE, "birth_datetime": "1941-10-01T00:30:00+05:30"}),
            "TIME_OFFSET_MISMATCH": json.dumps({**BASE, "birth_datetime": "2000-01-01T17:30:00+04:00"}),
            "COORDINATE_INVALID": json.dumps({**BASE, "longitude": 181}),
            "LATITUDE_OUTSIDE_SUPPORTED_BAND": json.dumps({**BASE, "latitude": 70.5}),
        }
        self.assertEqual(set(cases), set(ORDER))
        for code, text in cases.items():
            with self.subTest(code=code):
                proc = self.run_cli(text)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")
                self.assertNotIn("Traceback", proc.stderr)
                payload = json.loads(proc.stderr)
                self.assertEqual(list(payload), ["error"])
                self.assertTrue(payload["error"].startswith(code + ": "), payload)
                for secret in self.SECRETS:
                    self.assertNotIn(secret, proc.stderr)

    def test_unreadable_input_is_request_invalid(self):
        for text in ("", "not json", "[1, 2]", '{"birth_datetime": "2000-01-01T17:30:00+05:30"', "x" * 4097):
            with self.subTest(size=len(text)):
                proc = self.run_cli(text)
                self.assertEqual(proc.returncode, 2)
                self.assertEqual(proc.stdout, "")
                self.assertTrue(json.loads(proc.stderr)["error"].startswith("REQUEST_INVALID: "))
                self.assertNotIn("2000", proc.stderr)


if __name__ == "__main__":
    unittest.main()
