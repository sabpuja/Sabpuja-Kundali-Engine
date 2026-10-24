"""KUN-03 P1: deterministic timezone data (pinned tzdata, TZif SHA-256 manifest).

Synthetic instants only. fixtures/kun02_time_cases.json is a byte-identical copy
of tests/kun02/fixtures/time_cases.json at PR #19 head 1986b0a (SHA-256
f482f178f21702799fc8afa7a5092a82d9d4a9d110f54c4c0b33b6a84ba60f82), read as data.
Proves host independence and fail-closed loading, not historical clock accuracy.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import zoneinfo
from datetime import datetime, timedelta, timezone
from importlib import resources
from pathlib import Path
from unittest import mock
from zoneinfo import ZoneInfo

import tzdata

from sabpuja_kundali import engine, timezones
from sabpuja_kundali.engine import _parse_birth, calculate
from sabpuja_kundali.timezones import PinnedZoneLoader, TimezoneDataError, load_manifest, manifest_digest

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "src"
CASES = json.loads((HERE / "fixtures" / "kun02_time_cases.json").read_text(encoding="utf-8"))
WHEEL_SHA256 = "b683bd1b6659ddcd810ff02ad09ba821d4bf1065072805063eb35c49617905ac"
INVALID_TZ = "timezone must be a valid IANA timezone identifier"
SAMPLE_INSTANTS = [datetime(y, m, 15, 12, tzinfo=timezone.utc)
                   for y in (1900, 1920, 1942, 1955, 1970, 2000, 2024, 2050, 2100) for m in (1, 7)]
SYNTHETIC = {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata",
             "latitude": 28.6139, "longitude": 77.2090}


# Integration overlay (KUN-03 P4/P5). The frozen KUN-02 fixture keeps its original
# 'expect' values; refusal codes map back to its labels, and decided changes are
# versioned here with the decision that made them.
CODE_LABELS = {"TIME_FORMAT_INVALID": "PARSE", "TIME_LEAP_SECOND_UNSUPPORTED": "PARSE", "DATE_INVALID": "PARSE",
               "TIME_OFFSET_REQUIRED": "NAIVE", "TIMEZONE_INVALID": "TZ_INVALID",
               "DATE_OUTSIDE_SUPPORTED_RANGE": "RANGE", "TIME_NONEXISTENT_LOCAL": "OFFSET_MISMATCH",
               "TIME_OFFSET_MISMATCH": "OFFSET_MISMATCH", "HISTORICAL_CLOCK_UNVERIFIED": "HIST",
               "TIMEZONE_NOT_LOCATION_BASED": "NOT_LOCATION"}
VERSIONED = {  # case: (expected label, expected UTC, decision)
    "T49": ("RANGE", None, "SCI-03 local-date window (P4)"),
    "T50": ("ACCEPT", "2101-01-01T01:00:00Z", "SCI-03 local-date window (P4)"),
    "T51": ("RANGE", None, "SCI-03 local-date window (P4)"),
    "T59": ("PARSE", None, "P5-D2 strict profile"),
    "T60": ("PARSE", None, "P5-D2 strict profile"),
}
# SCI-03 RG-HIST Option B (P8): every accepted local date before 1970-01-01 is refused
# (T46 was versioned to ACCEPT by P4 and now reaches the gate; T17/T19 stay OFFSET_MISMATCH).
VERSIONED.update({case: ("HIST", None, "SCI-03 RG-HIST Option B (P8)") for case in (
    "T02", "T04", "T06", "T10", "T12", "T13", "T14", "T15", "T16", "T18", "T21", "T23", "T24", "T46", "T47",
    "T61", "T62")})
# KUN-03 D3: the fixture's proposed TIMEZONE_NOT_LOCATION_BASED for Etc/* and UTC. The
# fixture keeps the KUN-02 ACCEPT and its instant; geographic equivalents accept below.
VERSIONED.update({case: ("NOT_LOCATION", None, "KUN-03 D3 location-based timezone") for case in ("T56", "T57")})


def outcome(birth_datetime, tz_name):
    """KUN-02 outcome label and UTC instant for one case through the engine parser."""
    try:
        utc = _parse_birth(birth_datetime, tz_name)
    except ValueError as exc:
        return CODE_LABELS.get(getattr(exc, "code", None), f"UNEXPECTED: {exc}"), None
    return "ACCEPT", utc.isoformat().replace("+00:00", "Z")


def case_outcomes():
    return [[c["id"], *outcome(c["birth_datetime"], c["timezone"])] for c in CASES["cases"]]


def offsets_table(get_zone, keys):
    return [[key] + [int(t.astimezone(get_zone(key)).utcoffset().total_seconds()) for t in SAMPLE_INSTANTS]
            for key in keys]


def digest(value):
    return hashlib.sha256(json.dumps(value).encode()).hexdigest()


def copy_package(tmp, name):
    """Copy the installed tzdata package under another import name, for tampering."""
    pkg = Path(tmp, name)
    shutil.copytree(Path(tzdata.__file__).parent, pkg)
    return pkg


def make_host(tmp, name, kolkata_source):
    """A fake system zoneinfo tree whose Asia/Kolkata holds another zone's bytes."""
    tree = Path(tmp, name)
    (tree / "Asia").mkdir(parents=True)
    source = resources.files("tzdata.zoneinfo")
    for part in kolkata_source.split("/"):
        source = source.joinpath(part)
    (tree / "Asia" / "Kolkata").write_bytes(source.read_bytes())
    return str(tree)


class PinnedDataTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest()
        self.loader = PinnedZoneLoader(self.manifest)

    def test_installed_package_matches_manifest(self):
        self.assertEqual(tzdata.__version__, "2026.5")
        self.assertEqual(tzdata.IANA_VERSION, "2026e")
        self.assertEqual(self.manifest["package_version"], tzdata.__version__)
        self.assertEqual(self.manifest["iana_version"], tzdata.IANA_VERSION)
        self.assertEqual(self.loader.verify_all(), 598)

    def test_manifest_is_self_consistent_and_tied_to_the_wheel(self):
        self.assertEqual(manifest_digest(self.manifest), self.manifest["manifest_sha256"])
        self.assertEqual(self.manifest["wheel_sha256"], WHEEL_SHA256)
        self.assertEqual(self.manifest["wheel"], "tzdata-2026.5-py2.py3-none-any.whl")
        for entry in self.manifest["zones"].values():
            self.assertRegex(entry["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(entry["size_bytes"], 0)

    def test_provenance_metadata(self):
        self.assertEqual(self.loader.provenance(), {
            "source": "PyPI tzdata", "package_version": "2026.5", "iana_version": "2026e",
            "manifest_sha256": self.manifest["manifest_sha256"]})

    def test_known_offsets_including_negative_and_fractional_zones(self):
        cases = [
            ("Asia/Kolkata", datetime(2000, 1, 1, 12), timedelta(hours=5, minutes=30)),
            ("Asia/Kolkata", datetime(1943, 6, 15, 5, 30), timedelta(hours=6, minutes=30)),
            ("Asia/Kolkata", datetime(1905, 6, 15, 6, 38, 50), timedelta(hours=5, minutes=21, seconds=10)),
            ("Asia/Kathmandu", datetime(2000, 1, 1), timedelta(hours=5, minutes=45)),
            ("America/St_Johns", datetime(2000, 1, 15), timedelta(hours=-3, minutes=-30)),
            ("America/St_Johns", datetime(2000, 7, 15), timedelta(hours=-2, minutes=-30)),
            ("Pacific/Pago_Pago", datetime(2000, 1, 1), timedelta(hours=-11)),
            ("Pacific/Chatham", datetime(2000, 1, 15), timedelta(hours=13, minutes=45)),
            ("Australia/Lord_Howe", datetime(2000, 1, 15), timedelta(hours=11)),
            ("Australia/Lord_Howe", datetime(2000, 7, 15), timedelta(hours=10, minutes=30)),
            ("America/New_York", datetime(2021, 11, 7, 5, 30), timedelta(hours=-4)),
            ("America/New_York", datetime(2021, 11, 7, 6, 30), timedelta(hours=-5)),
        ]
        for key, instant, offset in cases:
            with self.subTest(key=key, instant=instant):
                utc = instant.replace(tzinfo=timezone.utc)
                self.assertEqual(utc.astimezone(self.loader.get(key)).utcoffset(), offset)

    def test_alias_is_byte_identical_to_its_canonical_zone(self):
        zones = self.manifest["zones"]
        self.assertEqual(zones["Asia/Calcutta"], zones["Asia/Kolkata"])
        self.assertEqual(outcome("2000-01-01T17:30:00+05:30", "Asia/Calcutta"),
                         ("ACCEPT", "2000-01-01T12:00:00Z"))


class Kun02TimeCaseTests(unittest.TestCase):
    def test_all_63_cases_match_the_kun02_expectation(self):
        self.assertEqual(len(CASES["cases"]), 63)
        for case in CASES["cases"]:
            with self.subTest(case=case["id"]):
                label, utc = outcome(case["birth_datetime"], case["timezone"])
                expect, expect_utc, _ = VERSIONED.get(case["id"], (case["expect"], case.get("expect_utc"), None))
                self.assertEqual(label, expect)
                if label == "ACCEPT":
                    self.assertEqual(utc, expect_utc)

    def test_d3_cases_keep_their_kun02_instant_on_geographic_zones(self):
        # T56 (Etc/GMT-5) and T57 (UTC) are refused by D3; the same wall times on
        # geographic zones with the same offset in 2000 give the KUN-02 instant.
        for case_id, key in (("T56", "Asia/Karachi"), ("T57", "Africa/Abidjan")):
            case = next(c for c in CASES["cases"] if c["id"] == case_id)
            with self.subTest(case=case_id):
                self.assertEqual(outcome(case["birth_datetime"], case["timezone"]), ("NOT_LOCATION", None))
                self.assertEqual(outcome(case["birth_datetime"], key), ("ACCEPT", case["expect_utc"]))

    def test_platform_dependent_case_is_refused_on_every_platform(self):
        # T-PD1: a lower-case key loads on case-insensitive file systems with stdlib
        # ZoneInfo; manifest lookup is exact, so it is refused everywhere.
        for case in CASES["platform_dependent"]:
            with self.subTest(case=case["id"]):
                self.assertEqual(outcome(case["birth_datetime"], case["timezone"]), ("TZ_INVALID", None))

    def test_dst_gaps_and_folds_in_both_hemispheres(self):
        cases = [
            # New York: gap 2021-03-14 02:00-03:00, fold 2021-11-07 01:00-02:00.
            ("2021-03-14T02:30:00-05:00", "America/New_York", "OFFSET_MISMATCH", None),
            ("2021-03-14T02:30:00-04:00", "America/New_York", "OFFSET_MISMATCH", None),
            ("2021-11-07T01:30:00-04:00", "America/New_York", "ACCEPT", "2021-11-07T05:30:00Z"),
            ("2021-11-07T01:30:00-05:00", "America/New_York", "ACCEPT", "2021-11-07T06:30:00Z"),
            # Sydney: fold 2021-04-04 02:00-03:00, gap 2021-10-03 02:00-03:00.
            ("2021-04-04T02:30:00+11:00", "Australia/Sydney", "ACCEPT", "2021-04-03T15:30:00Z"),
            ("2021-04-04T02:30:00+10:00", "Australia/Sydney", "ACCEPT", "2021-04-03T16:30:00Z"),
            ("2021-10-03T02:30:00+10:00", "Australia/Sydney", "OFFSET_MISMATCH", None),
            ("2021-10-03T02:30:00+11:00", "Australia/Sydney", "OFFSET_MISMATCH", None),
        ]
        for birth, key, label, utc in cases:
            with self.subTest(birth=birth, key=key):
                self.assertEqual(outcome(birth, key), (label, utc))


class FailClosedTests(unittest.TestCase):
    def setUp(self):
        self.manifest = load_manifest()

    def test_unsupported_and_malformed_keys_are_invalid_input(self):
        for key in ("Not/AZone", "IST", "../../etc/passwd", "Asia/../UTC", "/etc/localtime",
                    "Asia/Kolkata\x00", "", "asia/kolkata", "Asia\\Kolkata", "Asia/Kolkata/",
                    "tzdata.zi", "zone.tab", "iso3166.tab", 5, None, ["Asia/Kolkata"]):
            with self.subTest(key=key):
                with self.assertRaises(ValueError) as ctx:
                    PinnedZoneLoader(self.manifest).get(key)
                self.assertEqual(str(ctx.exception), INVALID_TZ)

    def test_key_absent_from_manifest_is_refused_even_if_the_package_has_it(self):
        manifest = json.loads(json.dumps(self.manifest))
        del manifest["zones"]["Asia/Kolkata"]
        manifest["manifest_sha256"] = manifest_digest(manifest)
        with self.assertRaises(ValueError):
            PinnedZoneLoader(manifest).get("Asia/Kolkata")

    def test_edited_manifest_is_refused(self):
        manifest = json.loads(json.dumps(self.manifest))
        manifest["zones"]["Asia/Kolkata"] = manifest["zones"]["UTC"]
        with self.assertRaises(TimezoneDataError) as ctx:
            PinnedZoneLoader(manifest)
        self.assertEqual(ctx.exception.code, "TZDATA_MANIFEST_INVALID")

    def test_version_mismatch_is_refused(self):
        for field, value in (("iana_version", "2026d"), ("package_version", "2026.4")):
            with self.subTest(field=field):
                manifest = {**self.manifest, field: value}
                manifest["manifest_sha256"] = manifest_digest(manifest)
                with self.assertRaises(TimezoneDataError) as ctx:
                    PinnedZoneLoader(manifest).get("Asia/Kolkata")
                self.assertEqual(ctx.exception.code, "TZDATA_VERSION_MISMATCH")

    def test_missing_package_is_refused(self):
        with self.assertRaises(TimezoneDataError) as ctx:
            PinnedZoneLoader(self.manifest, package="sabpuja_absent_tzdata").get("Asia/Kolkata")
        self.assertEqual(ctx.exception.code, "TZDATA_PACKAGE_MISSING")

    def test_tampered_or_missing_zone_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = copy_package(tmp, "tzdata_tamper_copy")
            target = pkg / "zoneinfo" / "Asia" / "Kolkata"
            data = bytearray(target.read_bytes())
            data[-2] ^= 0x01
            target.write_bytes(bytes(data))
            (pkg / "zoneinfo" / "Asia" / "Kathmandu").unlink()
            sys.path.insert(0, tmp)
            try:
                loader = PinnedZoneLoader(self.manifest, package="tzdata_tamper_copy")
                for key, code in (("Asia/Kolkata", "TZDATA_FILE_MISMATCH"), ("Asia/Kathmandu", "TZDATA_FILE_MISSING")):
                    with self.subTest(key=key):
                        with self.assertRaises(TimezoneDataError) as ctx:
                            loader.get(key)
                        self.assertEqual(ctx.exception.code, code)
                        self.assertNotIn(key, str(ctx.exception))
                self.assertEqual(loader.get("Asia/Dhaka").key, "Asia/Dhaka")
            finally:
                sys.path.remove(tmp)
                sys.modules.pop("tzdata_tamper_copy", None)

    def test_engine_never_falls_back_to_host_zoneinfo(self):
        self.assertFalse(hasattr(engine, "ZoneInfo"))
        failure = TimezoneDataError("TZDATA_FILE_MISMATCH", "a zone file does not match the pinned SHA-256")
        with mock.patch.object(engine, "get_zone", side_effect=failure), \
                mock.patch.object(engine, "verify_ephemeris_dir") as ephemeris:
            with self.assertRaises(TimezoneDataError):
                calculate(SYNTHETIC)
        ephemeris.assert_not_called()

    def test_cli_reports_timezone_data_failure_without_birth_details(self):
        code = (
            "import sys\n"
            "from sabpuja_kundali import timezones, cli\n"
            "timezones._LOADER = timezones.PinnedZoneLoader(timezones.load_manifest(), package='sabpuja_absent_tzdata')\n"
            "raise SystemExit(cli.main())\n")
        env = {**os.environ, "PYTHONPATH": str(SRC)}
        proc = subprocess.run([sys.executable, "-c", code], input=json.dumps(SYNTHETIC),
                              capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        error = json.loads(proc.stderr)["error"]
        self.assertTrue(error.startswith("TZDATA_PACKAGE_MISSING"), error)
        for detail in ("Asia/Kolkata", "17:30", "28.6139"):
            self.assertNotIn(detail, error)


def _manifest_variants():
    """(name, expected code, writer) for each corrupted manifest resource."""
    def rewrite(change):
        def write(path):
            manifest = json.loads(path.read_text(encoding="utf-8"))
            change(manifest)
            path.write_text(json.dumps(manifest), encoding="utf-8")
        return write

    def redigest(change):
        def both(manifest):
            change(manifest)
            if isinstance(manifest, dict):
                manifest["manifest_sha256"] = manifest_digest(manifest)
        return both

    def unreadable(path):
        path.unlink()
        path.mkdir()

    return [
        ("missing", "TZDATA_MANIFEST_MISSING", lambda path: path.unlink()),
        ("unreadable", "TZDATA_MANIFEST_INVALID", unreadable),
        ("invalid_utf8", "TZDATA_MANIFEST_INVALID", lambda path: path.write_bytes(b"\xff\xfe{")),
        ("malformed_json", "TZDATA_MANIFEST_INVALID", lambda path: path.write_text('{"zones": ', encoding="utf-8")),
        ("top_level_list", "TZDATA_MANIFEST_INVALID", lambda path: path.write_text("[]", encoding="utf-8")),
        ("zones_missing", "TZDATA_MANIFEST_INVALID", rewrite(redigest(lambda m: m.pop("zones")))),
        ("zones_not_object", "TZDATA_MANIFEST_INVALID", rewrite(redigest(lambda m: m.update(zones=["Asia/Kolkata"])))),
        ("zone_entry_not_object", "TZDATA_MANIFEST_INVALID",
         rewrite(redigest(lambda m: m["zones"].update({"Asia/Kolkata": "abc"})))),
        ("zone_size_bool", "TZDATA_MANIFEST_INVALID",
         rewrite(redigest(lambda m: m["zones"]["Asia/Kolkata"].update(size_bytes=True)))),
        ("version_not_string", "TZDATA_MANIFEST_INVALID", rewrite(redigest(lambda m: m.update(iana_version=2026)))),
        ("corrupted_digest", "TZDATA_MANIFEST_INVALID", rewrite(lambda m: m.update(manifest_sha256="0" * 64))),
    ]


class ManifestFailureTests(unittest.TestCase):
    """P1-QA-01: a missing or malformed manifest is a structured TZDATA_* refusal, never a traceback."""

    CLI = (
        "import sys\n"
        "from sabpuja_kundali import cli, engine\n"
        "def swiss_reached(*args, **kwargs):\n"
        "    raise SystemExit(99)\n"
        "engine.verify_ephemeris_dir = swiss_reached\n"
        "raise SystemExit(cli.main())\n")

    def broken_package(self, tmp, writer):
        root = Path(tmp, "src")
        shutil.copytree(SRC / "sabpuja_kundali", root / "sabpuja_kundali",
                        ignore=shutil.ignore_patterns("__pycache__"))
        writer(root / "sabpuja_kundali" / "tzif-manifest.json")
        return root

    def test_loader_refuses_each_broken_manifest_without_reaching_swiss(self):
        for name, code, writer in _manifest_variants():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                path = self.broken_package(tmp, writer) / "sabpuja_kundali" / "tzif-manifest.json"
                with mock.patch.object(timezones, "_manifest_resource", return_value=path), \
                        mock.patch.object(timezones, "_LOADER", None), \
                        mock.patch.object(engine, "verify_ephemeris_dir") as ephemeris:
                    with self.assertRaises(TimezoneDataError) as ctx:
                        calculate(SYNTHETIC)
                    self.assertEqual(ctx.exception.code, code)
                    ephemeris.assert_not_called()
                    # Refusal repeats on the next request; nothing broken is cached.
                    with self.assertRaises(TimezoneDataError):
                        timezones.get_zone("Asia/Kolkata")

    def test_cli_refuses_each_broken_manifest_without_traceback_or_details(self):
        for name, code, writer in _manifest_variants():
            with self.subTest(case=name), tempfile.TemporaryDirectory() as tmp:
                root = self.broken_package(tmp, writer)
                env = {k: v for k, v in os.environ.items() if k not in ("TZ", "SE_EPHE_PATH")}
                env["PYTHONPATH"] = str(root)
                proc = subprocess.run([sys.executable, "-c", self.CLI], input=json.dumps(SYNTHETIC),
                                      capture_output=True, text=True, env=env)
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertEqual(proc.stdout, "")
                self.assertNotIn("Traceback", proc.stderr)
                error = json.loads(proc.stderr)["error"]
                self.assertTrue(error.startswith(code + ":"), error)
                for detail in ("Asia/Kolkata", "17:30", "28.6139", "77.209"):
                    self.assertNotIn(detail, error)

    def test_intact_copy_is_accepted_control(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self.broken_package(tmp, lambda path: None)
            env = {**os.environ, "PYTHONPATH": str(root)}
            code = "from sabpuja_kundali.timezones import get_zone; print(get_zone('Asia/Kolkata').key)"
            proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, check=True)
        self.assertEqual(proc.stdout.strip(), "Asia/Kolkata")


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.loader = PinnedZoneLoader(load_manifest())

    def test_same_verified_instance_and_independent_of_stdlib_cache(self):
        first = self.loader.get("Asia/Kolkata")
        self.assertIs(self.loader.get("Asia/Kolkata"), first)
        ZoneInfo.clear_cache()
        self.assertIs(self.loader.get("Asia/Kolkata"), first)
        self.assertIsNot(first, ZoneInfo("Asia/Kolkata"))

    def test_cached_zone_is_not_replaced_by_later_disk_changes(self):
        manifest = load_manifest()
        with tempfile.TemporaryDirectory() as tmp:
            pkg = copy_package(tmp, "tzdata_stale_copy")
            sys.path.insert(0, tmp)
            try:
                loader = PinnedZoneLoader(manifest, package="tzdata_stale_copy")
                cached = loader.get("Asia/Kolkata")
                shutil.copy(pkg / "zoneinfo" / "UTC", pkg / "zoneinfo" / "Asia" / "Kolkata")
                self.assertIs(loader.get("Asia/Kolkata"), cached)
                self.assertEqual(datetime(2000, 1, 1, tzinfo=timezone.utc).astimezone(cached).utcoffset(),
                                 timedelta(hours=5, minutes=30))
                with self.assertRaises(TimezoneDataError) as ctx:
                    PinnedZoneLoader(manifest, package="tzdata_stale_copy").get("Asia/Kolkata")
                self.assertEqual(ctx.exception.code, "TZDATA_FILE_MISMATCH")
            finally:
                sys.path.remove(tmp)
                sys.modules.pop("tzdata_stale_copy", None)

    def test_concurrent_requests_match_sequential_results(self):
        loader = PinnedZoneLoader(load_manifest())
        expected = case_outcomes()
        results, instances, errors = [], [], []
        barrier = threading.Barrier(24)

        def worker():
            try:
                barrier.wait()
                instances.append(loader.get("Asia/Kathmandu"))
                results.append(case_outcomes())
            except Exception as exc:  # pragma: no cover - surfaced below
                errors.append(exc)

        threads = [threading.Thread(target=worker) for _ in range(24)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(len({id(zone) for zone in instances}), 1)
        self.assertEqual(len(results), 24)
        for result in results:
            self.assertEqual(result, expected)

    def test_loader_never_reconfigures_process_timezone_state(self):
        before = (zoneinfo.TZPATH, os.environ.get("TZ"), os.environ.get("PYTHONTZPATH"), time.tzname)
        for key in ("Asia/Kolkata", "America/New_York", "Australia/Sydney", "Pacific/Chatham"):
            self.loader.get(key)
        _parse_birth(SYNTHETIC["birth_datetime"], SYNTHETIC["timezone"])
        self.assertEqual((zoneinfo.TZPATH, os.environ.get("TZ"), os.environ.get("PYTHONTZPATH"), time.tzname),
                         before)


class CompatibilityTests(unittest.TestCase):
    """Outcomes that P1 changes on some hosts, pinned so they cannot drift unreviewed.

    Against Ubuntu's 2026e system build: 101 keys absent there are accepted (old
    names), and 110 keys give different offsets, all before 1970 except the
    non-location rule zones WET (to 1996-03-30) and EET (to 1980-04-05), which
    tzdata 2024b+ links to Europe/Lisbon and Europe/Athens. KUN-03 D3 refuses UTC,
    GMT, Etc/* and their aliases, and (zone policy version 2) CST6CDT, EST5EDT,
    MST7MDT and PST8PDT; WET, EET and the other five abbreviation-style names stay
    accepted by owner decision (zone_policy.REVIEWED_ACCEPTED).
    """

    def test_non_location_rule_zones_after_1970_follow_the_pinned_links(self):
        cases = [
            ("1995-07-01T14:00:00+02:00", "WET", ("ACCEPT", "1995-07-01T12:00:00Z")),
            ("1995-07-01T13:00:00+01:00", "WET", ("OFFSET_MISMATCH", None)),
            ("1975-07-01T13:00:00+01:00", "WET", ("ACCEPT", "1975-07-01T12:00:00Z")),
            ("1975-07-01T15:00:00+03:00", "EET", ("ACCEPT", "1975-07-01T12:00:00Z")),
            ("1975-07-01T14:00:00+02:00", "EET", ("OFFSET_MISMATCH", None)),
        ]
        for birth, key, expected in cases:
            with self.subTest(birth=birth, key=key):
                self.assertEqual(outcome(birth, key), expected)
        zones = load_manifest()["zones"]
        self.assertEqual(zones["WET"], zones["Europe/Lisbon"])
        self.assertEqual(zones["EET"], zones["Europe/Athens"])

    def test_old_names_match_their_current_zone_after_1970(self):
        pairs = [("Asia/Calcutta", "Asia/Kolkata"), ("Asia/Katmandu", "Asia/Kathmandu"),
                 ("Asia/Saigon", "Asia/Ho_Chi_Minh"), ("Europe/Kiev", "Europe/Kyiv"),
                 ("Australia/ACT", "Australia/Sydney"), ("America/Buenos_Aires", "America/Argentina/Buenos_Aires"),
                 ("US/Eastern", "America/New_York"), ("Japan", "Asia/Tokyo")]
        loader = timezones.default_loader()
        instants = [datetime(y, m, 15, 12, tzinfo=timezone.utc) for y in range(1970, 2101, 5) for m in (1, 7)]
        for old, current in pairs:
            with self.subTest(old=old):
                self.assertEqual([t.astimezone(loader.get(old)).utcoffset() for t in instants],
                                 [t.astimezone(loader.get(current)).utcoffset() for t in instants])

    def test_byte_identical_keys_give_identical_offsets(self):
        groups = {}
        for key, entry in load_manifest()["zones"].items():
            groups.setdefault(entry["sha256"], []).append(key)
        loader = timezones.default_loader()
        shared = [keys for keys in groups.values() if len(keys) > 1]
        self.assertGreater(len(shared), 1)
        for keys in shared:
            tables = {tuple(row[1:]) for row in offsets_table(loader.get, keys)}
            self.assertEqual(len(tables), 1, keys)

    def test_start_up_gate_fails_closed_on_a_tampered_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            pkg = copy_package(tmp, "tzdata_gate_copy")
            target = pkg / "zoneinfo" / "Pacific" / "Chatham"
            target.write_bytes(target.read_bytes()[:-1])
            sys.path.insert(0, tmp)
            try:
                with self.assertRaises(TimezoneDataError) as ctx:
                    PinnedZoneLoader(load_manifest(), package="tzdata_gate_copy").verify_all()
                self.assertEqual(ctx.exception.code, "TZDATA_FILE_MISMATCH")
            finally:
                sys.path.remove(tmp)
                sys.modules.pop("tzdata_gate_copy", None)


class HostIndependenceTests(unittest.TestCase):
    """Two simulated hosts whose system zoneinfo trees disagree must give identical results."""

    PROBE = (
        "import json,hashlib\n"
        "from datetime import datetime,timezone\n"
        "from zoneinfo import ZoneInfo\n"
        "from sabpuja_kundali.timezones import default_loader\n"
        "import test_timezones as t\n"
        "noon=datetime(2000,1,1,12,tzinfo=timezone.utc)\n"
        "keys=sorted(default_loader().keys())\n"
        "print(json.dumps({'stdlib_kolkata':noon.astimezone(ZoneInfo('Asia/Kolkata')).utcoffset().total_seconds(),"
        "'cases':t.digest(t.case_outcomes()),'offsets':t.digest(t.offsets_table(default_loader().get,keys))}))\n")

    def run_host(self, tzpath):
        env = {k: v for k, v in os.environ.items() if k not in ("TZ", "PYTHONTZPATH")}
        env["PYTHONTZPATH"] = tzpath
        env["PYTHONPATH"] = os.pathsep.join([str(SRC), str(HERE)])
        proc = subprocess.run([sys.executable, "-c", self.PROBE], env=env, capture_output=True, text=True, check=True)
        return json.loads(proc.stdout)

    def test_differing_host_trees_and_restarts_give_identical_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            host_a = make_host(tmp, "host_a", "UTC")
            host_b = make_host(tmp, "host_b", "Asia/Dhaka")
            runs = [self.run_host(path) for path in (host_a, host_b, "/nonexistent-zoneinfo", host_a)]
        # Precondition: stdlib ZoneInfo really follows each host tree.
        self.assertEqual([run["stdlib_kolkata"] for run in runs[:2]], [0.0, 21600.0])
        in_process = {"cases": digest(case_outcomes()),
                      "offsets": digest(offsets_table(timezones.default_loader().get,
                                                      sorted(timezones.default_loader().keys())))}
        for run in runs:
            self.assertEqual({k: run[k] for k in ("cases", "offsets")}, in_process)


REAL_DATA = os.environ.get("SABPUJA_TEST_EPHE_PATH")


@unittest.skipIf(REAL_DATA is None, "SABPUJA_TEST_EPHE_PATH unset: real-data integration tests not requested")
class RealDataHostIndependenceTests(unittest.TestCase):
    INPUTS = [
        SYNTHETIC,
        {**SYNTHETIC, "timezone": "Asia/Calcutta"},
        {"birth_datetime": "2021-11-07T01:30:00-05:00", "timezone": "America/New_York",
         "latitude": 40.7128, "longitude": -74.006},
        {"birth_datetime": "2021-04-04T02:30:00+11:00", "timezone": "Australia/Sydney",
         "latitude": -33.8688, "longitude": 151.2093},
    ]

    def run_cli(self, request, tzpath):
        env = {k: v for k, v in os.environ.items() if k not in ("TZ", "SE_EPHE_PATH")}
        env.update({"PYTHONTZPATH": tzpath, "PYTHONPATH": str(SRC), "SABPUJA_EPHE_PATH": REAL_DATA})
        return subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"], input=json.dumps(request),
                              capture_output=True, text=True, env=env, check=True).stdout

    def test_full_chart_output_is_identical_across_hosts(self):
        with tempfile.TemporaryDirectory() as tmp:
            hostile = make_host(tmp, "host", "UTC")
            for request in self.INPUTS:
                with self.subTest(timezone=request["timezone"]):
                    outputs = {self.run_cli(request, path) for path in (hostile, "/nonexistent-zoneinfo")}
                    self.assertEqual(len(outputs), 1)
                    in_process = json.dumps(calculate(request, ephe_path=REAL_DATA), ensure_ascii=False, indent=2)
                    self.assertEqual(outputs.pop().rstrip("\n"), in_process)


if __name__ == "__main__":
    unittest.main()
