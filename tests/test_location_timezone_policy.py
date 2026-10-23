"""KUN-03 D3: a birthplace timezone must be a geographic IANA identifier.

Synthetic inputs only. UTC, GMT, every Etc/* key, their root-level aliases and
Factory are refused with TIMEZONE_NOT_LOCATION_BASED, judged by exact name
against the tz 2026e source classification (zone_policy.py). Nothing is refused
for its offset or its TZif bytes. The check runs after the zone is recognised and
verified (TIMEZONE_INVALID and TZDATA_* first) and before every later check, and
a refusal reaches neither the ephemeris check nor Swiss.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zoneinfo

import swisseph
import tzdata

from sabpuja_kundali import engine, timezones, zone_policy
from sabpuja_kundali.engine import InputRefusalError, UnsupportedInputError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError
from sabpuja_kundali.timezones import TimezoneDataError

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
MISSING = "/nonexistent/sabpuja-ephemeris"
CODE = "TIMEZONE_NOT_LOCATION_BASED"
DETAIL = "birthplace timezone must be a geographic IANA timezone identifier"
MESSAGE = f"{CODE}: {DETAIL}"
CLI_ERROR = json.dumps({"error": MESSAGE})
KEYS = sorted(timezones.load_manifest()["zones"])
ROOT_ALIASES = ["Factory", "GMT", "GMT+0", "GMT-0", "GMT0", "Greenwich", "UCT", "UTC", "Universal", "Zulu"]
ETC = [k for k in KEYS if k.startswith("Etc/")]
REFUSED = sorted(ETC + ROOT_ALIASES)
# Must stay accepted: the assignment's list, zero-offset zones, legacy spellings and the
# abbreviation-style names left for a separate owner decision.
GEOGRAPHIC = ["Asia/Kolkata", "Asia/Kathmandu", "Asia/Tokyo", "America/New_York", "America/Los_Angeles",
              "America/Argentina/Buenos_Aires", "Europe/London", "Australia/Sydney", "Pacific/Auckland",
              "Africa/Abidjan", "Atlantic/Reykjavik"]
LEGACY = ["Asia/Calcutta", "Asia/Katmandu", "Iceland", "GB", "GB-Eire", "Eire", "US/Eastern", "US/Pacific", "Japan",
          "NZ", "Navajo", "W-SU", "Portugal", "Africa/Timbuktu", "America/Buenos_Aires", "Canada/Newfoundland"]
BASE = {"birth_datetime": "2000-01-01T12:00:00+00:00", "timezone": "UTC", "latitude": 28.6139, "longitude": 77.209}


def offset_text(key, wall):
    delta = datetime.fromisoformat(wall).replace(tzinfo=timezones.get_zone(key)).utcoffset()
    sign, seconds = ("-" if delta < timedelta(0) else "+"), abs(int(delta.total_seconds()))
    return f"{sign}{seconds // 3600:02d}:{seconds % 3600 // 60:02d}" + (f":{seconds % 60:02d}" if seconds % 60 else "")


def birth(key, wall="2000-01-01T12:00:00"):
    """The wall time with the offset the pinned zone gives for it (synthetic)."""
    return wall + offset_text(key, wall)


def outcome(**fields):
    try:
        calculate({**BASE, **fields}, ephe_path=MISSING)
    except InputRefusalError as exc:
        return exc.code
    except EphemerisDataError:
        return "ACCEPT"
    raise AssertionError("neither refused nor stopped at the ephemeris gate")


def run_cli(text, env=None, code=None):
    env = {**os.environ, "PYTHONPATH": str(SRC), "SABPUJA_EPHE_PATH": MISSING, **(env or {})}
    argv = [sys.executable, "-c", code] if code else [sys.executable, "-m", "sabpuja_kundali.cli"]
    data = text.encode() if isinstance(text, str) else text
    return subprocess.run(argv, input=data, capture_output=True, env=env, timeout=60)


class Classification(unittest.TestCase):
    def test_refused_set_is_exactly_etc_utc_gmt_aliases_and_factory(self):
        self.assertEqual(len(KEYS), 598)
        self.assertEqual(len(ETC), 35)
        self.assertEqual(sorted(zone_policy.NON_LOCATION_IDENTIFIERS), ROOT_ALIASES)
        self.assertEqual(zone_policy.NON_LOCATION_PREFIXES, ("Etc/",))
        self.assertTrue(set(ROOT_ALIASES) <= set(KEYS))
        self.assertEqual(sorted(k for k in KEYS if not zone_policy.is_location_based(k)), REFUSED)
        self.assertEqual(len(REFUSED), 45)

    def test_geographic_zones_stay_accepted(self):
        for key in GEOGRAPHIC + LEGACY + list(zone_policy.OWNER_REVIEW_PENDING):
            with self.subTest(key=key):
                self.assertIn(key, KEYS)
                self.assertTrue(zone_policy.is_location_based(key))
                self.assertEqual(outcome(birth_datetime=birth(key, "2001-06-15T12:00:00"), timezone=key), "ACCEPT")

    def test_never_refused_for_offset_or_shared_bytes(self):
        zones = timezones.load_manifest()["zones"]
        etc_utc = zones["Etc/UTC"]["sha256"]
        loader = timezones.default_loader()
        zero = [k for k in KEYS if zone_policy.is_location_based(k)
                and datetime(2001, 1, 15, 12, tzinfo=timezone.utc).astimezone(loader.get(k)).utcoffset() == timedelta(0)
                and datetime(2001, 7, 15, 12, tzinfo=timezone.utc).astimezone(loader.get(k)).utcoffset() == timedelta(0)]
        self.assertIn("Africa/Abidjan", zero)
        self.assertIn("Atlantic/Reykjavik", zero)
        self.assertGreater(len(zero), 15)
        for key in zero:  # a constant +00:00 clock, like UTC's, is still a place
            with self.subTest(key=key):
                self.assertEqual(outcome(birth_datetime="2001-07-15T12:00:00+00:00", timezone=key), "ACCEPT")
        # Same TZif bytes as another key: judged by name, never by data.
        by_hash = {}
        for key in KEYS:
            by_hash.setdefault(zones[key]["sha256"], []).append(key)
        shared = [keys for keys in by_hash.values() if len(keys) > 1]
        self.assertTrue(any("Iceland" in keys and "Africa/Abidjan" in keys for keys in shared))
        for keys in shared:
            for key in keys:
                self.assertEqual(zone_policy.is_location_based(key), key not in REFUSED, key)
        self.assertNotIn(etc_utc, {zones[k]["sha256"] for k in KEYS if zone_policy.is_location_based(k)})

    def test_lmt_history_and_no_current_dst_do_not_refuse(self):
        # Kolkata (LMT, no DST today), Kathmandu (+05:45), Monrovia (LMT -00:44:30 until 1972).
        for key, wall in (("Asia/Kolkata", "2001-06-15T12:00:00"), ("Asia/Kathmandu", "2001-06-15T12:00:00"),
                          ("Africa/Monrovia", "1971-06-01T12:00:00")):
            with self.subTest(key=key):
                self.assertEqual(outcome(birth_datetime=birth(key, wall), timezone=key), "ACCEPT")

    def test_exact_match_without_normalisation(self):
        for key in ("utc", "Utc", "gmt", "etc/UTC", "ETC/GMT", "Etc/utc", "factory", " UTC", "UTC ", "Etc/GMT+15",
                    "Etc/GMT-15", "Etc", "Etc/", "UTC/", "Etc/../UTC", "GMT+1"):
            with self.subTest(key=key):
                self.assertEqual(outcome(timezone=key), "TIMEZONE_INVALID")

    def test_policy_reads_names_only_never_host_or_data(self):
        with mock.patch.object(zoneinfo, "ZoneInfo", side_effect=AssertionError("host zoneinfo")), \
                mock.patch.object(zoneinfo, "available_timezones", side_effect=AssertionError("host zoneinfo")), \
                mock.patch.object(timezones, "default_loader", side_effect=AssertionError("tz data")):
            self.assertEqual(sorted(k for k in KEYS if not zone_policy.is_location_based(k)), REFUSED)
        source = (SRC / "sabpuja_kundali" / "zone_policy.py").read_text(encoding="utf-8")
        for word in ("import os", "environ", "getenv", "zoneinfo", "open(", "lower(", "casefold", "upper("):
            self.assertNotIn(word, source)

    def test_no_switch_or_bypass(self):
        for name in dir(zone_policy):
            self.assertNotRegex(name.lower(), "bypass|override|enable|disable|switch|allow")
        engine_source = (SRC / "sabpuja_kundali" / "engine.py").read_text(encoding="utf-8")
        cli_source = (SRC / "sabpuja_kundali" / "cli.py").read_text(encoding="utf-8")
        self.assertEqual(engine_source.count("zone_policy.is_location_based("), 1)
        self.assertNotIn("argv", cli_source)
        self.assertNotIn("environ", cli_source)
        # Environment variables that might look like switches change nothing.
        env = {"SABPUJA_D3": "0", "SABPUJA_ALLOW_UTC": "1", "SABPUJA_TIMEZONE_POLICY": "off", "TZ": "UTC"}
        proc = run_cli(json.dumps(BASE), env=env)
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr.decode().strip()), (2, b"", CLI_ERROR))


class ErrorContract(unittest.TestCase):
    def test_typed_coded_and_private(self):
        for key in REFUSED:
            with self.subTest(key=key), self.assertRaises(InputRefusalError) as ctx:
                calculate({**BASE, "timezone": key, "birth_datetime": birth(key)}, ephe_path=MISSING)
            self.assertEqual(ctx.exception.code, CODE)
            self.assertEqual(str(ctx.exception), MESSAGE)
            self.assertNotIsInstance(ctx.exception, UnsupportedInputError)
            self.assertIsInstance(ctx.exception, ValueError)
            self.assertNotIn(key, str(ctx.exception))

    def test_unknown_key_stays_timezone_invalid(self):
        self.assertEqual(outcome(timezone="Mars/Olympus"), "TIMEZONE_INVALID")
        self.assertEqual(outcome(timezone="Etc/Mars"), "TIMEZONE_INVALID")

    def test_parse_birth_raises_d3_for_every_offset_written(self):
        for text in ("2000-01-01T12:00:00Z", "2000-01-01T12:00:00+00:00", "2000-01-01T17:30:00+05:30"):
            with self.subTest(text=text), self.assertRaises(InputRefusalError) as ctx:
                engine._parse_birth(text, "UTC")
            self.assertEqual(ctx.exception.code, CODE)


class Order(unittest.TestCase):
    def test_earlier_checks_win(self):
        cases = (({"birth_datetime": 5}, "REQUEST_INVALID"),
                 ({"birth_datetime": "2000-01-01 12:00:00+00:00"}, "TIME_FORMAT_INVALID"),
                 ({"birth_datetime": "2000-01-01T12:00:00"}, "TIME_OFFSET_REQUIRED"),
                 ({"birth_datetime": "2016-12-31T23:59:60+00:00"}, "TIME_LEAP_SECOND_UNSUPPORTED"),
                 ({"birth_datetime": "2001-02-29T12:00:00+00:00"}, "DATE_INVALID"))
        for fields, code in cases:
            with self.subTest(fields=fields):
                self.assertEqual(outcome(**fields), code)

    def test_tz_data_faults_win(self):
        failure = TimezoneDataError("TZDATA_FILE_MISMATCH", "a zone file does not match the pinned SHA-256")
        with mock.patch.object(engine, "get_zone", side_effect=failure):
            with self.assertRaises(TimezoneDataError) as ctx:
                calculate(BASE, ephe_path=MISSING)
        self.assertEqual(ctx.exception.code, "TZDATA_FILE_MISMATCH")

    def test_d3_wins_over_every_later_check(self):
        cases = (("2101-01-01T00:00:00+00:00", "UTC", 28.6, 77.2, "DATE_OUTSIDE_SUPPORTED_RANGE"),
                 ("1899-12-31T23:59:59+14:00", "Etc/GMT-14", 28.6, 77.2, "DATE_OUTSIDE_SUPPORTED_RANGE"),
                 ("2000-01-01T12:00:00+05:30", "UTC", 28.6, 77.2, "TIME_OFFSET_MISMATCH"),
                 ("2000-01-01T12:00:00+05:00", "Etc/GMT+5", 28.6, 77.2, "TIME_OFFSET_MISMATCH"),
                 ("1950-06-15T12:00:00+00:00", "UTC", 28.6, 77.2, "HISTORICAL_CLOCK_UNVERIFIED"),
                 ("1969-12-31T23:59:59-12:00", "Etc/GMT+12", 28.6, 77.2, "HISTORICAL_CLOCK_UNVERIFIED"),
                 ("2000-01-01T12:00:00+00:00", "GMT", 28.6, 200.0, "COORDINATE_INVALID"),
                 ("2000-01-01T12:00:00+00:00", "Zulu", float("nan"), 200.0, "COORDINATE_INVALID"),
                 ("2000-01-01T12:00:00+00:00", "Factory", 70.0, 0.0, "LATITUDE_OUTSIDE_SUPPORTED_BAND"))
        for text, key, lat, lon, hidden in cases:
            with self.subTest(key=key, hidden=hidden):
                self.assertEqual(outcome(birth_datetime=text, timezone=key, latitude=lat, longitude=lon), CODE)
        # Each hidden code is still what a geographic zone gets for the same fields.
        for text, key, lat, lon, hidden in (("2101-01-01T00:00:00+00:00", "Africa/Abidjan", 28.6, 77.2,
                                             "DATE_OUTSIDE_SUPPORTED_RANGE"),
                                            ("2000-01-01T12:00:00+05:30", "Africa/Abidjan", 28.6, 77.2,
                                             "TIME_OFFSET_MISMATCH"),
                                            ("1950-06-15T12:00:00+00:00", "Africa/Abidjan", 28.6, 77.2,
                                             "HISTORICAL_CLOCK_UNVERIFIED"),
                                            ("2000-01-01T12:00:00+00:00", "Africa/Abidjan", 28.6, 200.0,
                                             "COORDINATE_INVALID"),
                                            ("2000-01-01T12:00:00+00:00", "Africa/Abidjan", 70.0, 0.0,
                                             "LATITUDE_OUTSIDE_SUPPORTED_BAND")):
            with self.subTest(geographic=hidden):
                self.assertEqual(outcome(birth_datetime=text, timezone=key, latitude=lat, longitude=lon), hidden)

    def test_refusal_reaches_neither_ephemeris_nor_swiss(self):
        names = ("julday", "set_ephe_path", "set_sid_mode", "set_delta_t_userdef", "calc_ut", "houses_ex")
        with mock.patch.object(engine, "verify_ephemeris_dir", side_effect=AssertionError("ephemeris")), \
                mock.patch.multiple(swisseph, **{n: mock.DEFAULT for n in names}) as swiss:
            for key in REFUSED:
                with self.subTest(key=key), self.assertRaises(InputRefusalError) as ctx:
                    calculate({**BASE, "timezone": key, "birth_datetime": birth(key)}, ephe_path=MISSING)
                self.assertEqual(ctx.exception.code, CODE)
        for name, called in swiss.items():
            self.assertFalse(called.called, name)


class Cli(unittest.TestCase):
    """The assignment's scenario matrix, through the real CLI."""

    def assert_d3(self, request):
        text = request if isinstance(request, str) else json.dumps(request)
        proc = run_cli(text)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, b"")
        self.assertEqual(proc.stderr.decode(), CLI_ERROR + "\n")
        self.assertNotIn(b"Traceback", proc.stderr)
        return proc

    def code(self, request):
        proc = run_cli(json.dumps(request))
        self.assertEqual(proc.stdout, b"")
        self.assertNotIn(b"Traceback", proc.stderr)
        return proc.returncode, json.loads(proc.stderr)["error"].split(":")[0]

    def test_01_utc_with_valid_post_1970_birth(self):
        self.assert_d3(BASE)

    def test_02_gmt(self):
        self.assert_d3({**BASE, "timezone": "GMT"})

    def test_03_etc_gmt_variants(self):
        for key in ("Etc/GMT", "Etc/GMT+0", "Etc/GMT-0", "Etc/GMT0", "Etc/UTC", "Etc/UCT", "Etc/Universal", "Etc/Zulu",
                    "Etc/Greenwich"):
            with self.subTest(key=key):
                self.assert_d3({**BASE, "timezone": key})

    def test_04_fixed_offsets_both_signs(self):
        for key, offset in (("Etc/GMT-5", "+05:00"), ("Etc/GMT+5", "-05:00"), ("Etc/GMT-14", "+14:00"),
                            ("Etc/GMT+12", "-12:00")):
            with self.subTest(key=key):
                self.assert_d3({**BASE, "timezone": key, "birth_datetime": "2000-01-01T12:00:00" + offset})

    def test_05_aliases(self):
        for key in ("UCT", "Universal", "Zulu", "GMT+0", "GMT-0", "GMT0", "Greenwich", "Factory"):
            with self.subTest(key=key):
                self.assert_d3({**BASE, "timezone": key})

    def test_06_unknown_key(self):
        self.assertEqual(self.code({**BASE, "timezone": "Mars/Olympus"}), (2, "TIMEZONE_INVALID"))
        self.assertEqual(self.code({**BASE, "timezone": "utc"}), (2, "TIMEZONE_INVALID"))

    def test_07_corrupt_tz_data_before_d3(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = Path(tmp, "tzdata_d3_tamper")
            shutil.copytree(Path(tzdata.__file__).parent, pkg)
            target = pkg / "zoneinfo" / "UTC"
            data = bytearray(target.read_bytes())
            data[-2] ^= 0x01
            target.write_bytes(bytes(data))
            code = ("import sys\nsys.path.insert(0, sys.argv[1])\n"
                    "from sabpuja_kundali import timezones, cli\n"
                    "timezones._LOADER = timezones.PinnedZoneLoader(timezones.load_manifest(), package='tzdata_d3_tamper')\n"
                    "raise SystemExit(cli.main())\n")
            env = {**os.environ, "PYTHONPATH": str(SRC), "SABPUJA_EPHE_PATH": MISSING}
            proc = subprocess.run([sys.executable, "-c", code, tmp], input=json.dumps(BASE).encode(),
                                  capture_output=True, env=env, timeout=60)
        self.assertEqual((proc.returncode, proc.stdout), (2, b""))
        self.assertNotIn(b"Traceback", proc.stderr)
        self.assertTrue(json.loads(proc.stderr)["error"].startswith("TZDATA_FILE_MISMATCH: "), proc.stderr)
        self.assertNotIn(b"UTC", proc.stderr)

    def test_08_d3_with_invalid_coordinates(self):
        for lat, lon in ((95.0, 0.0), (0.0, 200.0), (70.0, 0.0)):
            with self.subTest(lat=lat, lon=lon):
                self.assert_d3({**BASE, "latitude": lat, "longitude": lon})
        self.assert_d3(json.dumps(BASE).replace("28.6139", "NaN"))

    def test_09_d3_with_historical_date(self):
        self.assert_d3({**BASE, "birth_datetime": "1950-06-15T12:00:00+00:00"})

    def test_10_d3_with_offset_mismatch(self):
        self.assert_d3({**BASE, "birth_datetime": "2000-01-01T17:30:00+05:30"})

    def test_11_geographic_zone_with_valid_offset(self):
        for key in ("Africa/Abidjan", "Asia/Kolkata", "Atlantic/Reykjavik"):
            with self.subTest(key=key):
                # Reaches the ephemeris check, which fails closed on the missing folder.
                self.assertEqual(self.code({**BASE, "timezone": key, "birth_datetime": birth(key)}),
                                 (2, "EPHEMERIS_PATH_MISSING"))

    def test_12_gap(self):
        self.assertEqual(self.code({**BASE, "timezone": "America/New_York",
                                    "birth_datetime": "2021-03-14T02:30:00-05:00"}), (2, "TIME_NONEXISTENT_LOCAL"))

    def test_13_fold(self):
        for text in ("2021-11-07T01:30:00-04:00", "2021-11-07T01:30:00-05:00"):
            with self.subTest(text=text):
                self.assertEqual(self.code({**BASE, "timezone": "America/New_York", "birth_datetime": text}),
                                 (2, "EPHEMERIS_PATH_MISSING"))

    def test_14_malicious_input_and_size_limit(self):
        for key in ("UTC\u0000", "../../etc/passwd", "UTC; rm -rf /", "Etc/../UTC", "Etc/UTC\n", "UTC​",
                    "Ｕ" + "TC", "x" * 3000):
            with self.subTest(key=key[:20]):
                self.assertEqual(self.code({**BASE, "timezone": key}), (2, "TIMEZONE_INVALID"))
        exact = json.dumps(BASE).encode()
        exact += b" " * (4096 - len(exact))
        proc = run_cli(exact)
        self.assertEqual((proc.returncode, proc.stdout, proc.stderr.decode()), (2, b"", CLI_ERROR + "\n"))
        proc = run_cli(exact + b" ")
        self.assertEqual(json.loads(proc.stderr)["error"].split(":")[0], "REQUEST_INVALID")
        for secret in (b"2000-01-01", b"12:00", b"28.6139", b"77.209", b"UTC\""):
            self.assertNotIn(secret, self.assert_d3(BASE).stderr)

    def test_host_timezone_settings_do_not_matter(self):
        for env in ({"TZ": "Asia/Kolkata"}, {"TZ": "UTC"}, {"PYTHONTZPATH": "/nonexistent"},
                    {"PYTHONTZPATH": "/usr/share/zoneinfo", "TZ": "Etc/GMT+12"}):
            with self.subTest(env=env):
                proc = run_cli(json.dumps(BASE), env=env)
                self.assertEqual((proc.returncode, proc.stdout, proc.stderr.decode()), (2, b"", CLI_ERROR + "\n"))


if __name__ == "__main__":
    unittest.main()
