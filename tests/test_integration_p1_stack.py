"""KUN-03 P1 + P2-P8 integration: the pinned timezone loader under the P5 refusal order and the P8 gate.

Synthetic inputs only. P1's own tests cover the loader; these check the joins: where its
failures sit in the P5 order, that the P8 gate and P4 window see pinned-data offsets, and that
nothing reaches the host zoneinfo or Swiss when timezone data is broken.
"""
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from sabpuja_kundali import engine, timezones, zone_policy
from sabpuja_kundali.engine import InputRefusalError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError
from sabpuja_kundali.timezones import TimezoneDataError

SRC = Path(__file__).resolve().parents[1] / "src"
MISSING = "/nonexistent/sabpuja-ephemeris"
BASE = {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata",
        "latitude": 28.6139, "longitude": 77.2090}
BROKEN = TimezoneDataError("TZDATA_FILE_MISMATCH", "a zone file does not match the pinned SHA-256")


def _outcome(**fields):
    try:
        calculate({**BASE, **fields}, ephe_path=MISSING)
    except InputRefusalError as exc:
        return exc.code
    except TimezoneDataError as exc:
        return exc.code
    except EphemerisDataError:
        return "ACCEPT"
    raise AssertionError("neither refused nor stopped at the ephemeris gate")


class LoaderJoinTests(unittest.TestCase):
    def test_engine_uses_only_the_pinned_loader(self):
        self.assertFalse(hasattr(engine, "ZoneInfo"))
        self.assertIs(engine.get_zone, timezones.get_zone)
        with mock.patch.object(engine, "get_zone", wraps=timezones.get_zone) as loader:
            self.assertEqual(_outcome(), "ACCEPT")
        loader.assert_called_once_with("Asia/Kolkata")

    def test_unknown_key_is_timezone_invalid_in_the_p5_slot(self):
        for key in ("Mars/Base", "asia/kolkata", "localtime", "../etc/passwd", "", "Asia/Kolkata "):
            with self.subTest(key=key):
                self.assertEqual(_outcome(timezone=key), "TIMEZONE_INVALID")
        # Earlier codes still win over an unknown key.
        self.assertEqual(_outcome(birth_datetime="2000-01-01 17:30:00+05:30", timezone="Mars/Base"), "TIME_FORMAT_INVALID")
        self.assertEqual(_outcome(birth_datetime="2000-02-30T12:00:00+05:30", timezone="Mars/Base"), "DATE_INVALID")

    def test_broken_timezone_data_fails_closed_before_window_gate_and_coordinates(self):
        # TZDATA_* replaces the zone-load step: format and date checks come first; the window,
        # P8 gate and coordinates are never reached; Swiss is never called.
        with mock.patch.object(engine, "get_zone", side_effect=BROKEN), \
                mock.patch.object(engine, "verify_ephemeris_dir") as ephemeris:
            self.assertEqual(_outcome(birth_datetime="2000-01-01T17:30+0530"), "TIME_FORMAT_INVALID")
            for fields in ({}, {"birth_datetime": "1899-12-31T12:00:00+05:21:10"},
                           {"birth_datetime": "1950-06-15T12:00:00+05:30"}, {"latitude": 80.0}, {"longitude": 500.0}):
                with self.subTest(fields=fields):
                    self.assertEqual(_outcome(**fields), "TZDATA_FILE_MISMATCH")
        ephemeris.assert_not_called()

    def test_pinned_offsets_drive_the_window_and_the_gate(self):
        # Pre-1970 zone history comes from the pinned files: the P5 gap/mismatch codes still
        # come before the P8 gate, and the gate opens at local 1970-01-01 everywhere.
        self.assertEqual(_outcome(birth_datetime="1941-10-01T00:30:00+05:30"), "TIME_NONEXISTENT_LOCAL")
        self.assertEqual(_outcome(birth_datetime="1905-06-15T12:00:00+05:30"), "TIME_OFFSET_MISMATCH")
        self.assertEqual(_outcome(birth_datetime="1905-06-15T12:00:00+05:21:10"), "HISTORICAL_CLOCK_UNVERIFIED")
        self.assertEqual(_outcome(birth_datetime="1899-12-31T23:59:59+05:21:10"), "DATE_OUTSIDE_SUPPORTED_RANGE")
        # Geographic keys at the extremes of 1970 offsets (D3 refuses UTC and Etc/*, which these
        # rows used before; they are kept below with their D3 refusal).
        for key, offset in (("Asia/Kolkata", "+05:30"), ("Pacific/Auckland", "+12:00"), ("Pacific/Pago_Pago", "-11:00"),
                            ("Africa/Abidjan", "Z"), ("Africa/Monrovia", "-00:44:30")):
            with self.subTest(key=key):
                self.assertEqual(_outcome(birth_datetime="1969-12-31T23:59:59" + offset, timezone=key),
                                 "HISTORICAL_CLOCK_UNVERIFIED")
                # Monrovia keeps its -00:44:30 clock until 1972, so its 1970 example is valid too.
                self.assertEqual(_outcome(birth_datetime="1970-01-01T00:00:00" + offset, timezone=key), "ACCEPT")
        for key, offset in (("Etc/GMT-14", "+14:00"), ("Etc/GMT+12", "-12:00"), ("UTC", "Z")):
            for wall in ("1969-12-31T23:59:59", "1970-01-01T00:00:00"):
                with self.subTest(key=key, wall=wall):
                    self.assertEqual(_outcome(birth_datetime=wall + offset, timezone=key), "TIMEZONE_NOT_LOCATION_BASED")

    def test_every_manifest_key_is_gated_on_the_local_date(self):
        loader = timezones.default_loader()
        keys = sorted(loader.keys())
        self.assertGreater(len(keys), 500)
        for key in keys:
            zone = engine.get_zone(key)
            # D3: a key that names no place is refused before the gate, on both sides of 1970.
            located = zone_policy.is_location_based(key)
            for wall, want in (("1969-12-31T12:00:00", "HISTORICAL_CLOCK_UNVERIFIED"), ("1970-01-02T12:00:00", "ACCEPT")):
                want = want if located else "TIMEZONE_NOT_LOCATION_BASED"
                from datetime import datetime
                total = int(datetime.fromisoformat(wall).replace(tzinfo=zone).utcoffset().total_seconds())
                sign, total = ("-" if total < 0 else "+"), abs(total)
                text = wall + f"{sign}{total // 3600:02d}:{total % 3600 // 60:02d}" + (f":{total % 60:02d}" if total % 60 else "")
                with self.subTest(key=key, wall=wall):
                    self.assertEqual(_outcome(birth_datetime=text, timezone=key), want)


class NoBypassTests(unittest.TestCase):
    def test_policy_tables_are_constants_and_nothing_reads_a_switch(self):
        # The only environment reads in the package are the two ephemeris-path checks; the
        # P8 gate and P1 loader have no environment, CLI or request switch.
        self.assertEqual(engine.HISTORICAL_CLOCK_GATE, (("*", __import__("datetime").date.min,
                                                         __import__("datetime").date(1969, 12, 31)),))
        self.assertEqual(engine.HISTORICAL_CLOCK_EXCEPTIONS, ())
        self.assertEqual(engine.RESERVED_CODES, ())  # D3 now raises TIMEZONE_NOT_LOCATION_BASED
        self.assertEqual(zone_policy.ZONE_POLICY, "KUN-03 D3 location-based birthplace timezone, version 2")
        self.assertIsInstance(zone_policy.NON_LOCATION_IDENTIFIERS, tuple)
        self.assertIsInstance(zone_policy.NON_LOCATION_PREFIXES, tuple)
        reads = []
        for path in sorted((SRC / "sabpuja_kundali").glob("*.py")):
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if any(token in line for token in ("os.environ", "getenv", "sys.argv")):
                    reads.append((path.name, line.strip()))
        self.assertEqual(reads, [
            ("engine.py", 'folder = verify_ephemeris_dir(ephe_path or os.environ.get("SABPUJA_EPHE_PATH", ""), ephemeris_manifest)'),
            ("ephemeris.py", 'if os.environ.get("SE_EPHE_PATH"):'),
        ])


class CliJoinTests(unittest.TestCase):
    def _cli(self, request, prelude=""):
        code = "import sys\nfrom sabpuja_kundali import timezones, cli\n" + prelude + "raise SystemExit(cli.main())\n"
        env = {**os.environ, "PYTHONPATH": str(SRC), "SABPUJA_EPHE_PATH": MISSING}
        proc = subprocess.run([sys.executable, "-c", code], input=json.dumps(request),
                              capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        self.assertNotIn("Traceback", proc.stderr)
        return json.loads(proc.stderr)["error"]

    def test_missing_timezone_package_and_historical_gate_are_structured_and_private(self):
        request = {**BASE, "birth_datetime": "1957-08-15T10:20:30+05:30"}
        absent = "timezones._LOADER = timezones.PinnedZoneLoader(timezones.load_manifest(), package='sabpuja_absent_tzdata')\n"
        errors = (self._cli(request, absent), self._cli(request))
        self.assertTrue(errors[0].startswith("TZDATA_PACKAGE_MISSING: "), errors[0])
        self.assertTrue(errors[1].startswith("HISTORICAL_CLOCK_UNVERIFIED: "), errors[1])
        for error in errors:
            for secret in ("1957", "08-15", "10:20", "Asia/Kolkata", "28.6139", "77.209"):
                self.assertNotIn(secret, error)

    def test_host_timezone_environment_is_ignored(self):
        request = {**BASE, "birth_datetime": "1975-01-15T14:00:00+02:00", "timezone": "EET"}
        env = {**os.environ, "PYTHONPATH": str(SRC), "PYTHONTZPATH": "/nonexistent", "TZ": "Pacific/Kiritimati"}
        code = ("from sabpuja_kundali.engine import _parse_birth\n"
                "print(_parse_birth('1975-01-15T14:00:00+02:00', 'EET').isoformat())\n")
        proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "1975-01-15T12:00:00+00:00")


if __name__ == "__main__":
    unittest.main()
