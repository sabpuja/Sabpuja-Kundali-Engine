"""KUN-03 P8 (SCI-03 RG-HIST Option B; G1-G5): fail-closed historical-clock gate.

Synthetic inputs only. With the production table, every recognised zone is
refused for local civil dates before 1970-01-01 with HISTORICAL_CLOCK_UNVERIFIED,
after every other time check and before the coordinates. No exception is
enabled. The tests here never patch the production table except where a block
says so (the DATA-01 exception mechanism), and check it is restored.
"""
import json
import os
import subprocess
import sys
import unittest
import zoneinfo
from datetime import date, datetime
from pathlib import Path
from unittest import mock

from sabpuja_kundali import engine, zone_policy
from sabpuja_kundali.engine import InputRefusalError, UnsupportedInputError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError

SRC = Path(__file__).resolve().parents[1] / "src"
MISSING = "/nonexistent/sabpuja-ephemeris"
CODE = "HISTORICAL_CLOCK_UNVERIFIED"
DETAIL = "birth dates before 1970-01-01 need a verified historical clock record"
D3 = "TIMEZONE_NOT_LOCATION_BASED"
# The engine's own zone loader (stdlib zoneinfo here; the pinned get_zone once P1 is merged).
_load = getattr(engine, "get_zone", None) or zoneinfo.ZoneInfo
BASE = {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata",
        "latitude": 28.6139, "longitude": 77.2090}


def _code(**fields):
    try:
        calculate({**BASE, **fields}, ephe_path=MISSING)
    except InputRefusalError as exc:
        return exc.code
    except EphemerisDataError:
        return "ACCEPT"
    raise AssertionError("neither refused nor stopped at the ephemeris gate")


def _birth(wall, key):
    """Wall time with the zone's own offset (fold 0), written in the strict profile."""
    offset = datetime.fromisoformat(wall).replace(tzinfo=_load(key)).utcoffset()
    total = int(offset.total_seconds())
    sign, total = ("-" if total < 0 else "+"), abs(total)
    text = f"{sign}{total // 3600:02d}:{total % 3600 // 60:02d}" + (f":{total % 60:02d}" if total % 60 else "")
    return wall + text


class ProductionTableTests(unittest.TestCase):
    def test_table_is_the_owner_policy_with_no_exceptions(self):
        self.assertEqual(engine.HISTORICAL_CLOCK_GATE, (("*", date.min, date(1969, 12, 31)),))
        self.assertEqual(engine.HISTORICAL_CLOCK_EXCEPTIONS, ())
        self.assertIsInstance(engine.HISTORICAL_CLOCK_GATE, tuple)
        self.assertEqual(engine.HISTORICAL_CLOCK_POLICY, "SCI-03 RG-HIST Option B, version 1")
        self.assertNotIn(CODE, engine.RESERVED_CODES)

    def test_refusal_is_typed_fixed_and_private(self):
        with self.assertRaises(UnsupportedInputError) as ctx:
            calculate({**BASE, "birth_datetime": "1969-12-31T23:59:59+05:30"}, ephe_path=MISSING)
        self.assertEqual(ctx.exception.code, CODE)
        self.assertIsInstance(ctx.exception, ValueError)
        self.assertEqual(str(ctx.exception), f"{CODE}: {DETAIL}")


class GateEdgeTests(unittest.TestCase):
    def test_edges_by_local_civil_date(self):
        cases = (
            ("1969-12-31T23:59:59.999999+05:30", "Asia/Kolkata", CODE),
            ("1970-01-01T00:00:00+05:30", "Asia/Kolkata", "ACCEPT"),
            ("1969-12-31T23:59:59+00:00", "Africa/Abidjan", CODE),
            ("1970-01-01T00:00:00Z", "Africa/Abidjan", "ACCEPT"),
            ("1969-12-31T23:59:59-11:00", "Pacific/Pago_Pago", CODE),   # UTC 1970-01-01T10:59:59
            ("1970-01-01T00:00:00+12:00", "Pacific/Auckland", "ACCEPT"),  # UTC 1969-12-31T12:00
            # Before D3 these four rows used UTC, Etc/GMT+12 and Etc/GMT-14 (gate code, accept,
            # gate code, accept). Those keys are now refused earlier, whatever the date.
            ("1969-12-31T23:59:59+00:00", "UTC", D3),
            ("1970-01-01T00:00:00Z", "UTC", D3),
            ("1969-12-31T23:59:59-12:00", "Etc/GMT+12", D3),
            ("1970-01-01T00:00:00+14:00", "Etc/GMT-14", D3),
            ("1969-12-31T23:59:59-05:00", "America/New_York", CODE),
            ("1970-01-01T00:00:00-05:00", "America/New_York", "ACCEPT"),
            ("1969-12-31T23:59:59+10:00", "Australia/Sydney", CODE),
            ("1970-01-01T00:00:00+10:00", "Australia/Sydney", "ACCEPT"),
            ("1969-12-31T12:00:00-00:44:30", "Africa/Monrovia", CODE),
            ("1971-06-01T12:00:00-00:44:30", "Africa/Monrovia", "ACCEPT"),
        )
        for text, key, code in cases:
            with self.subTest(text=text, timezone=key):
                self.assertEqual(_code(birth_datetime=text, timezone=key), code)

    def test_kolkata_option_b_scope(self):
        # Option B includes Asia/Kolkata 1956-1969 (Option A would have stopped at 1956).
        for year in (1900, 1947, 1955, 1956, 1960, 1969):
            with self.subTest(year=year):
                self.assertEqual(_code(birth_datetime=_birth(f"{year}-06-15T12:00:00", "Asia/Kolkata")), CODE)
        for year in (1970, 1971, 2000, 2100):
            with self.subTest(year=year):
                self.assertEqual(_code(birth_datetime=_birth(f"{year}-06-15T12:00:00", "Asia/Kolkata")), "ACCEPT")

    def test_every_recognised_zone_on_both_sides_of_1970(self):
        # G2: every key the engine's loader recognises, including old link names. Since D3 the
        # keys that name no place (UTC, GMT, Etc/*, their aliases, Factory and, since zone policy
        # version 2, the four US-rules zones) are refused before the gate on both sides of 1970;
        # every other key is gated exactly as before.
        checked = not_location = 0
        for key in sorted(zoneinfo.available_timezones()):
            try:
                _load(key)
            except ValueError:
                continue  # not a key the engine accepts (e.g. "localtime" under the pinned loader)
            with self.subTest(timezone=key):
                located = zone_policy.is_location_based(key)
                for wall, code in (("1969-12-31T12:00:00", CODE), ("1970-01-02T12:00:00", "ACCEPT")):
                    self.assertEqual(_code(birth_datetime=_birth(wall, key), timezone=key), code if located else D3)
                checked += 1
                not_location += not located
        self.assertGreater(checked - not_location, 300)
        self.assertEqual(not_location, 49)


class OrderTests(unittest.TestCase):
    def test_earlier_time_checks_still_win(self):
        cases = (
            ("1950-06-15 12:00:00+05:30", "Asia/Kolkata", "TIME_FORMAT_INVALID"),
            ("1950-06-15T12:00:00", "Asia/Kolkata", "TIME_OFFSET_REQUIRED"),
            ("1950-06-15T23:59:60+05:30", "Asia/Kolkata", "TIME_LEAP_SECOND_UNSUPPORTED"),
            ("1900-02-29T12:00:00+05:21:10", "Asia/Kolkata", "DATE_INVALID"),
            ("1950-06-15T12:00:00+05:30", "Mars/Base", "TIMEZONE_INVALID"),
            ("1899-12-31T23:59:59+05:21:10", "Asia/Kolkata", "DATE_OUTSIDE_SUPPORTED_RANGE"),
            ("1941-10-01T00:30:00+05:30", "Asia/Kolkata", "TIME_NONEXISTENT_LOCAL"),    # KUN-02 T08
            ("1905-06-15T12:00:00+05:30", "Asia/Kolkata", "TIME_OFFSET_MISMATCH"),      # KUN-02 T03
        )
        for text, key, code in cases:
            with self.subTest(text=text):
                self.assertEqual(_code(birth_datetime=text, timezone=key), code)

    def test_gate_comes_before_every_coordinate_check(self):
        for fields in ({"latitude": float("nan")}, {"latitude": 95.0}, {"latitude": 70.0}, {"longitude": 200.0},
                       {"latitude": True}):
            with self.subTest(fields=fields):
                self.assertEqual(_code(birth_datetime="1969-06-15T12:00:00+05:30", **fields), CODE)


class ExceptionMechanismTests(unittest.TestCase):
    """G4: the DATA-01 exception path, exercised with synthetic rows in this block only."""

    def test_a_verified_exception_admits_exactly_its_zone_and_dates(self):
        row = ("Asia/Kolkata", date(1960, 1, 1), date(1960, 12, 31))
        with mock.patch.object(engine, "HISTORICAL_CLOCK_EXCEPTIONS", (row,)):
            self.assertEqual(_code(birth_datetime="1960-01-01T00:00:00+05:30"), "ACCEPT")
            self.assertEqual(_code(birth_datetime="1960-12-31T23:59:59+05:30"), "ACCEPT")
            self.assertEqual(_code(birth_datetime="1959-12-31T23:59:59+05:30"), CODE)
            self.assertEqual(_code(birth_datetime="1961-01-01T00:00:00+05:30"), CODE)
            self.assertEqual(_code(birth_datetime="1960-06-15T12:00:00+05:00", timezone="Asia/Karachi"), CODE)
            self.assertEqual(_code(birth_datetime="1960-06-15T12:00:00+05:30", timezone="Asia/Calcutta"), CODE)
        self.assertEqual(engine.HISTORICAL_CLOCK_EXCEPTIONS, ())
        self.assertEqual(_code(birth_datetime="1960-06-15T12:00:00+05:30"), CODE)

    def test_a_wildcard_exception_opens_nothing(self):
        with mock.patch.object(engine, "HISTORICAL_CLOCK_EXCEPTIONS", (("*", date.min, date(1969, 12, 31)),)):
            self.assertEqual(_code(birth_datetime="1960-06-15T12:00:00+05:30"), CODE)


class CliPrivacyTests(unittest.TestCase):
    def test_cli_refusal_is_structured_and_private(self):
        env = {**os.environ, "PYTHONPATH": str(SRC), "SABPUJA_EPHE_PATH": MISSING}
        request = {**BASE, "birth_datetime": "1957-08-15T10:20:30+05:30"}
        proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"], input=json.dumps(request),
                              capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertNotIn("Traceback", proc.stderr)
        self.assertEqual(json.loads(proc.stderr), {"error": f"{CODE}: {DETAIL}"})
        for secret in ("1957", "08-15", "10:20", "Asia/Kolkata", "28.6139", "77.209"):
            self.assertNotIn(secret, proc.stderr)


if __name__ == "__main__":
    unittest.main()
