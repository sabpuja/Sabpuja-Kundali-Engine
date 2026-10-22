"""KUN-03 P4 (SCI-03 date window): 1900-01-01 to 2100-12-31 inclusive, by local civil date.

Synthetic inputs only. The window is checked on the wall-clock date as written,
before conversion, so the UTC instant may fall in 1899 or 2101. DST gap/fold
behaviour and offset validation are unchanged. Real-data cases run only when
SABPUJA_TEST_EPHE_PATH is set.
"""
from datetime import datetime, timedelta
import json
import os
import subprocess
import sys
import unittest
from unittest import mock
from pathlib import Path

import swisseph

from sabpuja_kundali import engine
from sabpuja_kundali.engine import UnsupportedInputError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError

SRC = Path(__file__).resolve().parent.parent / "src"
CODE = "DATE_OUTSIDE_SUPPORTED_RANGE"
MISSING = "/does-not-exist/sabpuja"


def _zone(key):
    # The engine's own zone source (stdlib ZoneInfo before KUN-03 P1, the pinned loader after).
    get = getattr(engine, "get_zone", None)
    return get(key) if get else engine.ZoneInfo(key)


def _offset_text(delta: timedelta) -> str:
    sign = "-" if delta < timedelta(0) else "+"
    seconds = abs(int(delta.total_seconds()))
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{sign}{hours:02d}:{minutes:02d}" + (f":{secs:02d}" if secs else "")


def _birth(wall: str, key: str) -> str:
    """Wall time with the offset the engine's zone data gives for it (synthetic)."""
    naive = datetime.fromisoformat(wall)
    return wall + _offset_text(naive.replace(tzinfo=_zone(key)).utcoffset())


# (birth_datetime, timezone): accepted because the local date is inside the window,
# although for the first three the UTC year is 1899 or 2101.
EDGE_ACCEPTED = [
    ("1900-01-01T00:00:00+14:00", "Etc/GMT-14"),        # UTC 1899-12-31T10:00
    ("2100-12-31T23:59:59-12:00", "Etc/GMT+12"),        # UTC 2101-01-01T11:59:59
    ("2100-12-31T23:59:59-11:00", "Pacific/Pago_Pago"),  # UTC 2101-01-01T10:59:59
    ("1900-01-01T00:00:00-12:00", "Etc/GMT+12"),
    ("2100-12-31T23:59:59+14:00", "Pacific/Kiritimati"),
    ("1900-01-01T00:00:00+00:00", "UTC"),
    ("2100-12-31T23:59:59+00:00", "UTC"),
    ("2100-12-31T23:59:59+05:30", "Asia/Kolkata"),
    ("2100-12-31T23:59:59-08:00", "America/Los_Angeles"),
    ("2100-12-31T23:59:59.999999+00:00", "UTC"),
]
# Refused because the local date is outside, although for the first three the UTC
# year is 1900 or 2100.
EDGE_REFUSED = [
    ("1899-12-31T23:59:59-12:00", "Etc/GMT+12"),        # UTC 1900-01-01T11:59:59
    ("2101-01-01T00:00:00+14:00", "Etc/GMT-14"),        # UTC 2100-12-31T10:00
    ("2101-01-01T00:00:00+05:30", "Asia/Kolkata"),      # UTC 2100-12-31T18:30
    ("1899-12-31T23:59:59+14:00", "Etc/GMT-14"),
    ("2101-01-01T00:00:00-12:00", "Etc/GMT+12"),
    ("1899-12-31T23:59:59+00:00", "UTC"),
    ("2101-01-01T00:00:00+00:00", "UTC"),
    ("1899-12-31T23:59:59.999999+00:00", "UTC"),
    ("1800-06-15T12:00:00+00:00", "UTC"),
    ("2400-01-01T00:00:00+00:00", "UTC"),
    ("0001-01-01T00:00:00+14:00", "Pacific/Kiritimati"),  # used to raise OverflowError
    ("9999-12-31T23:59:59-12:00", "Etc/GMT+12"),          # used to raise OverflowError
]


def _request(birth, tz, lat=28.6139, lon=77.2090):
    return {"birth_datetime": birth, "timezone": tz, "latitude": lat, "longitude": lon}


class LocalDateWindowTests(unittest.TestCase):
    def assert_accepted(self, birth, tz):
        # Passing validation reaches the ephemeris gate, which fails on the missing folder.
        with self.assertRaises(EphemerisDataError):
            calculate(_request(birth, tz), ephe_path=MISSING)

    def assert_refused(self, birth, tz):
        with self.assertRaises(UnsupportedInputError) as ctx:
            calculate(_request(birth, tz), ephe_path=MISSING)
        self.assertEqual(ctx.exception.code, CODE)
        self.assertIsInstance(ctx.exception, ValueError)
        self.assertEqual(str(ctx.exception),
                         f"{CODE}: local birth date must be between 1900-01-01 and 2100-12-31 (inclusive)")

    def assert_gated(self, birth, tz):
        # KUN-03 P8 (G3): inside the window and otherwise valid, so the only refusal
        # left is the later historical-clock gate (local dates before 1970-01-01).
        with self.assertRaises(UnsupportedInputError) as ctx:
            calculate(_request(birth, tz), ephe_path=MISSING)
        self.assertEqual(ctx.exception.code, "HISTORICAL_CLOCK_UNVERIFIED")

    def assert_inside_window(self, birth, tz):
        (self.assert_gated if birth < "1970" else self.assert_accepted)(birth, tz)

    def test_window_edges_accepted_by_local_date(self):
        # P8 (G3, versioned): the local 1900-01-01 edges were accepted before P8;
        # they still pass the window and now reach HISTORICAL_CLOCK_UNVERIFIED.
        for birth, tz in EDGE_ACCEPTED:
            with self.subTest(birth=birth, timezone=tz):
                self.assert_inside_window(birth, tz)

    def test_outside_window_refused_by_local_date(self):
        for birth, tz in EDGE_REFUSED:
            with self.subTest(birth=birth, timezone=tz):
                self.assert_refused(birth, tz)

    def test_local_and_utc_years_differ(self):
        # The cases that flip relative to the old UTC-year rule.
        for birth, tz in EDGE_ACCEPTED[:3]:
            with self.subTest(birth=birth):
                self.assert_inside_window(birth, tz)
                # P8 (G1): the conversion itself, with the gate table empty in this block only.
                with mock.patch.object(engine, "HISTORICAL_CLOCK_GATE", ()):
                    self.assertIn(engine._parse_birth(birth, tz).year, (1899, 2101))
        for birth, tz in EDGE_REFUSED[:3]:
            with self.subTest(birth=birth):
                self.assertIn(datetime.fromisoformat(birth).astimezone(_zone("UTC")).year, (1900, 2100))
                self.assert_refused(birth, tz)

    def test_exact_utc_extremes(self):
        # Documented in docs/api-contract.md: the earliest and latest accepted instants.
        # P8 (G1/G3): the lower extreme now reaches the historical-clock gate; its
        # instant is still checked with the gate table empty in this block only.
        self.assert_gated("1900-01-01T00:00:00+14:00", "Etc/GMT-14")
        with mock.patch.object(engine, "HISTORICAL_CLOCK_GATE", ()):
            self.assertEqual(engine._parse_birth("1900-01-01T00:00:00+14:00", "Etc/GMT-14").isoformat(),
                             "1899-12-31T10:00:00+00:00")
        self.assertEqual(engine._parse_birth("2100-12-31T23:59:59.999999-12:00", "Etc/GMT+12").isoformat(),
                         "2101-01-01T11:59:59.999999+00:00")
        self.assert_refused("2101-01-01T00:00:00.000000-12:00", "Etc/GMT+12")
        self.assert_refused("1899-12-31T23:59:59.999999+14:00", "Etc/GMT-14")

    def test_historical_zone_edges_use_the_zone_offset(self):
        # Local mean / historical offsets at the start of the window, taken from the engine's zone data.
        for key in ("Asia/Kolkata", "Asia/Karachi", "Asia/Dhaka", "Europe/London", "America/New_York",
                    "Australia/Sydney"):
            with self.subTest(timezone=key):
                self.assert_gated(_birth("1900-01-01T00:00:00", key), key)  # P8 (G3)
                self.assert_refused(_birth("1899-12-31T23:59:59", key), key)
                self.assert_accepted(_birth("2100-12-31T23:59:59", key), key)
                self.assert_refused(_birth("2101-01-01T00:00:00", key), key)

    def test_leap_days(self):
        for birth in ("2000-02-29T12:00:00+05:30", "2024-02-29T12:00:00+05:30", "2096-02-29T12:00:00+05:30"):
            with self.subTest(birth=birth):
                self.assert_accepted(birth, "Asia/Kolkata")
        # 1900 and 2100 are not leap years: an invalid date is a format error, not a range refusal.
        for birth in ("1900-02-29T12:00:00+00:00", "2100-02-29T12:00:00+00:00"):
            with self.subTest(birth=birth), self.assertRaises(ValueError) as ctx:
                calculate(_request(birth, "UTC"), ephe_path=MISSING)
            self.assertNotIsInstance(ctx.exception, UnsupportedInputError)

    def test_check_order_around_the_window(self):
        # Missing offset and invalid timezone are reported before the window.
        for birth, tz, message in (("1800-01-01T00:00:00", "UTC", "explicit UTC offset"),
                                   ("1800-01-01T00:00:00+00:00", "Not/AZone", "valid IANA timezone")):
            with self.subTest(birth=birth, timezone=tz):
                with self.assertRaises(ValueError) as ctx:
                    calculate(_request(birth, tz), ephe_path=MISSING)
                self.assertNotIsInstance(ctx.exception, UnsupportedInputError)
                self.assertIn(message, str(ctx.exception))
        # Outside the window, the window is reported before an offset mismatch.
        self.assert_refused("2101-01-01T00:00:00+09:00", "Asia/Kolkata")
        # Inside the window, offset mismatches keep their existing error.
        with self.assertRaises(ValueError) as ctx:
            calculate(_request("2100-12-31T23:59:59+09:00", "Asia/Kolkata"), ephe_path=MISSING)
        self.assertNotIsInstance(ctx.exception, UnsupportedInputError)
        self.assertIn("does not match IANA timezone", str(ctx.exception))

    def test_dst_gap_and_fold_unchanged(self):
        # Gaps: neither offset names an existing wall time. Still refused; since
        # P5 (D1) with TIME_NONEXISTENT_LOCAL instead of the shared mismatch text.
        for birth, tz in (("2024-03-10T02:30:00-05:00", "America/New_York"),
                          ("2024-03-10T02:30:00-04:00", "America/New_York"),
                          ("2024-10-06T02:30:00+10:00", "Australia/Sydney"),
                          ("2024-10-06T02:30:00+11:00", "Australia/Sydney")):
            with self.subTest(gap=birth), self.assertRaises(ValueError) as ctx:
                calculate(_request(birth, tz), ephe_path=MISSING)
            self.assertEqual(ctx.exception.code, "TIME_NONEXISTENT_LOCAL")
        # Folds: both offsets accepted, and they give different instants.
        for first, second, tz in (("2024-11-03T01:30:00-04:00", "2024-11-03T01:30:00-05:00", "America/New_York"),
                                  ("2024-04-07T02:30:00+11:00", "2024-04-07T02:30:00+10:00", "Australia/Sydney")):
            with self.subTest(fold=tz):
                self.assert_accepted(first, tz)
                self.assert_accepted(second, tz)
                self.assertEqual(engine._parse_birth(second, tz) - engine._parse_birth(first, tz), timedelta(hours=1))

    def test_cli_refusal_is_structured_and_private(self):
        request = json.dumps(_request("2101-01-01T00:00:00+05:30", "Asia/Kolkata"))
        proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"], input=request, text=True,
                              capture_output=True, env={**os.environ, "PYTHONPATH": str(SRC)}, timeout=60)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertNotIn("Traceback", proc.stderr)
        self.assertTrue(json.loads(proc.stderr)["error"].startswith(f"{CODE}: "))
        for secret in ("2101-01-01T", "00:00:00", "Asia/Kolkata", "28.6139", "77.209"):
            self.assertNotIn(secret, proc.stderr)


DATA = os.environ.get("SABPUJA_TEST_EPHE_PATH")


@unittest.skipIf(DATA is None, "SABPUJA_TEST_EPHE_PATH unset: real-data integration tests not requested")
@mock.patch.object(engine, "HISTORICAL_CLOCK_GATE", ())  # P8 (G1): calculation check only; restored after each test
class RealDataWindowTests(unittest.TestCase):
    def test_charts_at_the_utc_extremes_of_the_window(self):
        # The earliest and latest accepted instants (UTC 1899-12-31T10:00 and 2101-01-01T11:59:59)
        # are inside the pinned ephemeris data and equal direct Swiss values.
        for birth, tz in EDGE_ACCEPTED[:2]:
            with self.subTest(birth=birth):
                result = calculate(_request(birth, tz, lat=0.0, lon=0.0), ephe_path=DATA)
                utc = engine._parse_birth(birth, tz)
                jd = swisseph.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60 + utc.second / 3600)
                with engine._SWISS_LOCK:
                    swisseph.set_ephe_path(DATA)
                    swisseph.set_sid_mode(swisseph.SIDM_LAHIRI, 0, 0)
                    moon = swisseph.calc_ut(jd, swisseph.MOON, swisseph.FLG_SWIEPH | swisseph.FLG_SIDEREAL)[0][0]
                self.assertEqual(result["planets"]["moon"]["longitude_deg"], engine._display_deg(float(moon)))
                self.assertEqual(result["birth"]["utc"][:4], "1899" if birth.startswith("1900") else "2101")


if __name__ == "__main__":
    unittest.main()
