"""KUN-03 P7: calculation method, time-scale and provenance metadata (schema 0.2.0).

The metadata is additive: the 0.1.0 legacy projection (metadata removed, old
schema version restored) must equal the PR #33 engine output byte for byte.
Every claim is checked against what the engine actually does (recorded Swiss
calls, verified manifests, installed versions). Synthetic inputs only.

Era, disclosure and projection tests need no data. Chart tests need the pinned
data in SABPUJA_TEST_EPHE_PATH (unset skips, as in test_swiss_integration).
"""
from datetime import datetime, timedelta, timezone
from importlib import metadata as importlib_metadata
from pathlib import Path
from unittest import mock
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import tomllib
import unittest

import swisseph as swe
import tzdata

from sabpuja_kundali import engine, ephemeris, provenance, timezones, zone_policy
from sabpuja_kundali.engine import InputRefusalError, calculate
from sabpuja_kundali.ephemeris import EphemerisDataError
from sabpuja_kundali.timezones import TimezoneDataError

DATA = os.environ.get("SABPUJA_TEST_EPHE_PATH")
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
UTC = timezone.utc
# KUN-03 D3 refuses the UTC key; +00:00 charts here use a geographic zone whose clock
# has been +00:00 since 1912 (zone and coordinates are not cross-validated).
ZERO = "Africa/Abidjan"

# Synthetic boundary requests and the SHA-256 of their 0.1.0 outputs computed with the
# PR #33 engine at bec4641 (canonical JSON: sorted keys, compact separators, UTF-8).
LEGACY_REQUESTS = [
    ("2000-01-01T12:00:00+00:00", "UTC", 28.6139, 77.209),
    ("1970-01-01T00:00:00+05:30", "Asia/Kolkata", 19.076, 72.8777),
    ("1971-12-31T23:59:59+00:00", "UTC", -33.8688, 151.2093),
    ("1972-01-01T00:00:00+00:00", "UTC", 51.4779, -0.0015),
    ("2027-06-27T23:59:59+00:00", "UTC", 60.0, 10.0),
    ("2027-06-28T00:00:00+00:00", "UTC", -60.5, -70.0),
    ("2049-12-31T23:59:59+00:00", "UTC", 66.0, -18.0),
    ("2050-01-01T00:00:00+00:00", "UTC", -66.0, 180.0),
    ("2026-11-01T01:30:00-05:00", "America/New_York", 40.7128, -74.006),
    ("2100-12-31T23:59:59.999999+14:00", "Pacific/Kiritimati", 1.87, -157.4),
]
LEGACY_SHA256 = "be619e62d14aed164619609481ce2ab67e32f0e19937c091f52a0d2a7aac25c3"
# KUN-03 D3: seven LEGACY_REQUESTS use the UTC key and are now refused. The golden above
# is still reproduced with the D3 check bypassed inside the test only; the same instants
# and coordinates on geographic +00:00 zones have their own PR #33 golden (bec4641).
LEGACY_GEO_ZONES = {28.6139: ZERO, -33.8688: ZERO, 51.4779: "Europe/London", 60.0: ZERO, -60.5: ZERO,
                    66.0: "Atlantic/Reykjavik", -66.0: ZERO}
LEGACY_GEO_REQUESTS = [(b, LEGACY_GEO_ZONES[lat] if tz == "UTC" else tz, lat, lon)
                       for b, tz, lat, lon in LEGACY_REQUESTS]
LEGACY_GEO_SHA256 = "8c7907773c7175d15c227461e3a85cd9d22ce7c14301da6919f7d94c8fe7e924"
LEGACY_KEYS = ["schema_version", "validation_status", "method", "birth", "lagna", "moon_nakshatra", "planets"]

# Every metadata key and its JSON type; lists of objects give the item shape.
SHAPE = {
    "metadata_schema": str,
    "conventions": {
        "zodiac": str,
        "ayanamsa": {"name": str, "swiss_mode": str, "swiss_mode_number": int, "swiss_call": str, "kind": str,
                     "definition": str},
        "planetary_positions": {"center": str, "position": str, "frame": str, "swiss_function": str,
                                "swiss_flags": [str], "swiss_flags_value": int, "swiss_bodies": [str],
                                "moshier_fallback": str},
        "nodes": {"rahu": str, "rahu_swiss_body": str, "ketu": str},
        "houses": {"d1_model": str, "rule": str},
        "ascendant": {"definition": str, "swiss_function": str, "swiss_house_system": str, "swiss_flags": [str],
                      "swiss_flags_value": int, "value": str, "note": str},
        "swiss_state": {"reset_per_request_under_lock": [str]},
        "longitude_display": {"range": str, "decimals": int, "note": str},
        "classification": str,
    },
    "swiss_ephemeris": {"library_version": str, "python_binding": str, "python_binding_version": str},
    "ephemeris_data": {"source_repository": str, "source_commit": str, "manifest_version": str,
                       "manifest_sha256": str, "manifest_sha256_method": str,
                       "required_files": [{"name": str, "size_bytes": int, "sha256": str}],
                       "verified_before_calculation": bool, "verification": str, "coverage_years": [int]},
    "timezone_data": {"source": str, "package_version": str, "iana_version": str, "manifest_sha256": str,
                      "host_timezone_database_used": bool, "verification": str},
    "time_scale": {"pipeline": str, "ut1_assumption": str, "measured_ut1_minus_utc_used": bool,
                   "earth_orientation_data_used": bool,
                   "delta_t": {"source": str, "user_override_used": bool, "measured_series_used": bool, "note": str},
                   "era": str, "era_basis": str, "era_description": str, "leap_second_list_expiry_utc": str,
                   "leap_second_list_source": str,
                   "sidereal_time_model": {"switch_ut": str, "recorded_step_arcsec": float, "chart_side": str,
                                           "note": str}},
    "input_policy": {
        "local_date_window": {"first": str, "last": str, "basis": str},
        "historical_clock": {"policy": str, "mode": str,
                             "refused_local_dates": [{"zone": str, "first_local_date": (str, type(None)),
                                                      "last_local_date": (str, type(None))}],
                             "exceptions": list},
        "latitude_band_deg": {"min": float, "max": float, "inclusive": bool},
        "timezone_identifier": {"policy": str, "mode": str, "rule": str, "refused_identifiers": [str],
                                "refused_prefixes": [str], "zone_matches_coordinates_verified": bool},
        "time_offset": str,
        "refusal_order": str,
    },
    "disclosures": [{"code": str, "description": str}],
    "validation": {"status": str, "claim_boundary": str},
}


def request(birth, tz=ZERO, lat=28.6139, lon=77.209):
    return {"birth_datetime": birth, "timezone": tz, "latitude": lat, "longitude": lon}


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def check_shape(test, value, shape, path="calculation_metadata"):
    if isinstance(shape, dict):
        test.assertIsInstance(value, dict, path)
        test.assertEqual(list(value), list(shape), path)
        for key, sub in shape.items():
            check_shape(test, value[key], sub, f"{path}.{key}")
    elif isinstance(shape, list):
        test.assertIsInstance(value, list, path)
        for n, item in enumerate(value):
            check_shape(test, item, shape[0], f"{path}[{n}]")
    elif shape is float:
        test.assertIs(type(value), float, path)
    elif shape is int:
        test.assertIs(type(value), int, path)
    else:
        test.assertIsInstance(value, shape, path)


class Eras(unittest.TestCase):
    """By the converted UTC instant; no data needed."""

    def at(self, text):
        return datetime.fromisoformat(text).astimezone(UTC)

    def test_era_boundaries(self):
        cases = [("1960-12-31T23:59:59.999999+00:00", "CIVIL_TIME_BEFORE_UTC"),
                 ("1961-01-01T00:00:00+00:00", "UTC_BEFORE_LEAP_SECONDS"),
                 ("1971-12-31T23:59:59.999999+00:00", "UTC_BEFORE_LEAP_SECONDS"),
                 ("1972-01-01T00:00:00+00:00", "LEAP_SECOND_UTC"),
                 ("2027-05-19T00:00:00+00:00", "LEAP_SECOND_UTC"),
                 ("2027-05-19T23:59:59.999999+00:00", "LEAP_SECOND_UTC"),
                 ("2027-05-20T00:00:00+00:00", "CONTINUOUS_UTC_TRANSITION_DATE"),
                 ("2027-05-20T12:00:00+00:00", "CONTINUOUS_UTC_TRANSITION_DATE"),
                 ("2027-05-20T23:59:59.999999+00:00", "CONTINUOUS_UTC_TRANSITION_DATE"),
                 ("2027-05-21T00:00:00+00:00", "CONTINUOUS_UTC_AFTER_TRANSITION_DATE"),
                 ("2027-06-27T23:59:59.999999+00:00", "CONTINUOUS_UTC_AFTER_TRANSITION_DATE"),
                 ("2027-06-28T00:00:00+00:00", "AFTER_LEAP_SECOND_LIST_EXPIRY"),
                 ("2100-12-31T23:59:59+00:00", "AFTER_LEAP_SECOND_LIST_EXPIRY")]
        for text, code in cases:
            with self.subTest(text=text):
                self.assertEqual(provenance.era(self.at(text)), code)

    def test_era_follows_utc_not_local_date(self):
        # Local 1972-01-01 in IST is still 1971 in UTC; local 2027-06-28 03:00 IST is 06-27 in UTC.
        self.assertEqual(provenance.era(self.at("1972-01-01T05:00:00+05:30")), "UTC_BEFORE_LEAP_SECONDS")
        self.assertEqual(provenance.era(self.at("2027-06-28T03:00:00+05:30")), "CONTINUOUS_UTC_AFTER_TRANSITION_DATE")
        self.assertEqual(provenance.era(self.at("2027-06-27T20:00:00-04:00")), "AFTER_LEAP_SECOND_LIST_EXPIRY")
        # The transition reporting day is the UTC date: IST 05:30 on 20 and 21 May is UTC midnight.
        self.assertEqual(provenance.era(self.at("2027-05-20T05:29:59.999999+05:30")), "LEAP_SECOND_UTC")
        self.assertEqual(provenance.era(self.at("2027-05-20T05:30:00+05:30")), "CONTINUOUS_UTC_TRANSITION_DATE")
        self.assertEqual(provenance.era(self.at("2027-05-21T05:29:59.999999+05:30")),
                         "CONTINUOUS_UTC_TRANSITION_DATE")
        self.assertEqual(provenance.era(self.at("2027-05-21T05:30:00+05:30")), "CONTINUOUS_UTC_AFTER_TRANSITION_DATE")
        self.assertEqual(provenance.era(self.at("2027-05-19T20:00:00-04:00")), "CONTINUOUS_UTC_TRANSITION_DATE")

    def test_same_instant_in_utc_and_ist_has_one_era(self):
        for utc_text, ist_text in [("2027-05-19T23:59:59.999999+00:00", "2027-05-20T05:29:59.999999+05:30"),
                                   ("2027-05-20T00:00:00+00:00", "2027-05-20T05:30:00+05:30"),
                                   ("2027-05-20T23:59:59.999999+00:00", "2027-05-21T05:29:59.999999+05:30"),
                                   ("2027-05-21T00:00:00+00:00", "2027-05-21T05:30:00+05:30"),
                                   ("2027-06-27T23:59:59.999999+00:00", "2027-06-28T05:29:59.999999+05:30"),
                                   ("2027-06-28T00:00:00+00:00", "2027-06-28T05:30:00+05:30")]:
            with self.subTest(utc=utc_text):
                self.assertEqual(self.at(utc_text), self.at(ist_text))
                self.assertEqual(provenance.era(self.at(utc_text)), provenance.era(self.at(ist_text)))

    def test_pinned_constants(self):
        self.assertEqual(provenance.LEAP_SECOND_LIST_EXPIRY, datetime(2027, 6, 28, tzinfo=UTC))
        self.assertEqual(provenance.LEAP_SECOND_UTC_START, datetime(1972, 1, 1, tzinfo=UTC))
        self.assertEqual(provenance.CONTINUOUS_UTC_TRANSITION_DATE, datetime(2027, 5, 20, tzinfo=UTC))
        self.assertEqual(provenance.CONTINUOUS_UTC_AFTER_TRANSITION_DATE, datetime(2027, 5, 21, tzinfo=UTC))
        self.assertEqual(provenance.SIDEREAL_MODEL_SWITCH, datetime(2050, 1, 1, tzinfo=UTC))
        self.assertEqual(provenance.SIDEREAL_MODEL_STEP_ARCSEC, -1.908)
        self.assertEqual([code for code, *_ in provenance.ERAS],
                         ["CIVIL_TIME_BEFORE_UTC", "UTC_BEFORE_LEAP_SECONDS", "LEAP_SECOND_UTC",
                          "CONTINUOUS_UTC_TRANSITION_DATE", "CONTINUOUS_UTC_AFTER_TRANSITION_DATE",
                          "AFTER_LEAP_SECOND_LIST_EXPIRY"])
        for code, start, end, text in provenance.ERAS:
            self.assertNotIn("verified", text.replace("not a verified", ""), code)
        # Contiguous, half-open, covering every instant.
        bounds = [(start, end) for _, start, end, _ in provenance.ERAS]
        self.assertEqual((bounds[0][0], bounds[-1][1]), (None, None))
        for (_, end), (start, _) in zip(bounds, bounds[1:]):
            self.assertEqual(end, start)

    def test_continuous_utc_disclosure_text(self):
        # SCI-01h after BIPM CGPM 2026 Resolution 5 (owner Option 2, date-granular).
        text = {code: t for code, _, _, t in provenance.ERAS}
        for code, body in text.items():
            for stale in ("2035", "2022", "Resolution 4"):
                self.assertNotIn(stale, body, code)
        for code in ("LEAP_SECOND_UTC", "CONTINUOUS_UTC_TRANSITION_DATE", "CONTINUOUS_UTC_AFTER_TRANSITION_DATE",
                     "AFTER_LEAP_SECOND_LIST_EXPIRY"):
            self.assertIn("CGPM 2026 Resolution 5", text[code], code)
            self.assertIn("treated as UT1", text[code], code)
        # The 0.9 s rule belongs to the leap-second regime; the transition date makes no claim either way.
        self.assertIn("In this regime the IERS rule keeps |UT1-UTC| below 0.9 s", text["LEAP_SECOND_UTC"])
        self.assertIn("2027-05-19", text["LEAP_SECOND_UTC"])
        for code in ("CONTINUOUS_UTC_AFTER_TRANSITION_DATE", "AFTER_LEAP_SECOND_LIST_EXPIRY"):
            self.assertNotIn("0.9", text[code], code)
        day = text["CONTINUOUS_UTC_TRANSITION_DATE"]
        self.assertIn("official effective hour and its time scale are not stated", day)
        self.assertIn("no claim is made that the 0.9 s leap-second rule has ended or still applies", day)
        self.assertIn("reporting convention, not the official effective instant", day)
        for invented in ("00:00", "0h", "midnight", "3 600"):
            self.assertNotIn(invented, day)
        # 3 600 s is a permitted ceiling, never a measured offset or an engine error.
        for code in ("CONTINUOUS_UTC_AFTER_TRANSITION_DATE", "AFTER_LEAP_SECOND_LIST_EXPIRY"):
            self.assertIn("3 600 s", text[code], code)
            self.assertIn("policy ceiling, not a measured", text[code], code)
        self.assertIn("not a measured UT1-UTC or an engine error", text["CONTINUOUS_UTC_AFTER_TRANSITION_DATE"])
        self.assertIn("2027-06-28", text["CONTINUOUS_UTC_AFTER_TRANSITION_DATE"])
        self.assertIn("pinned IERS leap-second list expiry (2027-06-28)", text["AFTER_LEAP_SECOND_LIST_EXPIRY"])
        self.assertIn("Swiss Delta T is extrapolated", text["AFTER_LEAP_SECOND_LIST_EXPIRY"])

    def test_api_contract_documents_the_implemented_eras(self):
        # docs/api-contract.md "Time scale and eras" must list exactly these codes and UTC ranges,
        # and its sample era_description must be the implemented text.
        doc = (ROOT / "docs" / "api-contract.md").read_text(encoding="utf-8")
        section = doc.split("### Time scale and eras", 1)[1].split("\n### ", 1)[0]
        rows = [line.split(" | ")[:2] for line in section.splitlines() if line.startswith("| `")]
        day = lambda moment: moment.date().isoformat()
        expected = []
        for code, start, end, _ in provenance.ERAS:
            span = (f"before {day(end)}" if start is None else
                    f"from {day(start)}" if end is None else f"{day(start)} to {day(end)}")
            expected.append([f"| `{code}`", span])
        self.assertEqual(rows, expected)
        texts = {code: text for code, _, _, text in provenance.ERAS}
        sample = doc.split('"era": "', 1)[1]
        code = sample.split('"', 1)[0]
        described = json.loads(sample.split('"era_description": ', 1)[1].split(",\n", 1)[0])
        self.assertEqual(described, texts[code])
        self.assertIn("reporting convention, **not** the official effective instant", section)
        self.assertNotIn("2035", doc)

    def test_future_disclosure_keeps_list_expiry_not_transition_date(self):
        codes = lambda text: [d["code"] for d in provenance._disclosures(self.at(text), 0.0)]
        for text in ("2027-05-19T23:59:59.999999+00:00", "2027-05-20T00:00:00+00:00", "2027-05-21T00:00:00+00:00",
                     "2027-06-27T23:59:59.999999+00:00", "2027-06-28T05:29:59.999999+05:30"):
            self.assertEqual(codes(text), [], text)
        self.assertEqual(codes("2027-06-28T00:00:00+00:00"), ["FUTURE_CIVIL_TIME_PROJECTED"])

    def test_disclosures(self):
        before, after = self.at("2027-06-27T23:59:59+00:00"), self.at("2027-06-28T00:00:00+00:00")
        codes = lambda utc, lat: [d["code"] for d in provenance._disclosures(utc, lat)]
        self.assertEqual(codes(before, 60.0), [])
        self.assertEqual(codes(before, -60.0), [])
        self.assertEqual(codes(before, math.nextafter(60.0, 90.0)), ["HIGH_LATITUDE_TIME_SENSITIVITY"])
        self.assertEqual(codes(before, -66.0), ["HIGH_LATITUDE_TIME_SENSITIVITY"])
        self.assertEqual(codes(after, 0.0), ["FUTURE_CIVIL_TIME_PROJECTED"])
        self.assertEqual(codes(after, 61.0), ["FUTURE_CIVIL_TIME_PROJECTED", "HIGH_LATITUDE_TIME_SENSITIVITY"])

    def test_high_latitude_text_makes_no_uniform_claim(self):
        # Lagna speed at high latitude depends on date and sidereal time (see the Swiss regression
        # below), so the disclosure must not say it is always faster or always worse.
        text = provenance._disclosures(self.at("2026-03-20T09:00:00+00:00"), 61.0)[0]["description"]
        self.assertEqual(text, "Absolute latitude above 60 deg: ascendant sensitivity to birth-time uncertainty can be "
                               "greater for some dates and sidereal times, but is not uniformly greater. An accurate "
                               "recorded birth time is important. Descriptive only; calculation and acceptance are "
                               "unchanged.")
        lowered = text.lower()
        for claim in ("moves faster", "larger effect", "always", "every chart", "much greater", "uniformly greater."):
            self.assertNotIn(claim, lowered.replace("not uniformly greater", ""), claim)
        self.assertIn("can be", lowered)
        self.assertIn("not uniformly greater", lowered)

    def test_legacy_projection_rejects_non_p7_output(self):
        for chart in ({"schema_version": "0.1.0"}, {"schema_version": "0.2.0"}):
            with self.assertRaises(ValueError):
                provenance.legacy_projection(chart)


@unittest.skipIf(DATA is None, "SABPUJA_TEST_EPHE_PATH unset: chart metadata tests need the pinned data")
class ChartMetadata(unittest.TestCase):
    def chart(self, *args, **kwargs):
        return calculate(request(*args, **kwargs), ephe_path=DATA)

    def meta(self, *args, **kwargs):
        return self.chart(*args, **kwargs)["calculation_metadata"]

    def test_schema_version_and_shape(self):
        chart = self.chart("2000-01-01T12:00:00+00:00")
        self.assertEqual(chart["schema_version"], "0.2.0")
        self.assertEqual(list(chart), LEGACY_KEYS + ["calculation_metadata"])
        self.assertEqual(chart["calculation_metadata"]["metadata_schema"], "sabpuja-calculation-metadata/3")  # /3 since P7 Option 2 eras; /2 since D3
        check_shape(self, chart["calculation_metadata"], SHAPE)
        json.dumps(chart, allow_nan=False)

    def test_legacy_projection_matches_pr33_byte_for_byte(self):
        # PR #33 policy reproduction: the D3 check is bypassed inside this block only.
        with mock.patch.object(zone_policy, "is_location_based", lambda name: True):
            legacy = [provenance.legacy_projection(calculate(request(*r), ephe_path=DATA)) for r in LEGACY_REQUESTS]
        self.assertFalse(zone_policy.is_location_based("UTC"))  # bypass restored
        geo = [provenance.legacy_projection(calculate(request(*r), ephe_path=DATA)) for r in LEGACY_GEO_REQUESTS]
        for chart in legacy + geo:
            self.assertEqual(list(chart), LEGACY_KEYS)
            self.assertEqual(chart["method"], {"ayanamsa": "Lahiri", "nodes": "mean", "houses": "whole_sign",
                                               "ephemeris": "Swiss Ephemeris, local .se1",
                                               "binding_version": swe.version})
        self.assertEqual(hashlib.sha256(canonical(legacy).encode()).hexdigest(), LEGACY_SHA256)
        self.assertEqual(hashlib.sha256(canonical(geo).encode()).hexdigest(), LEGACY_GEO_SHA256)
        # Same instants and coordinates: the charts differ only in the echoed timezone key.
        for before, after, req in zip(legacy, geo, LEGACY_GEO_REQUESTS):
            self.assertEqual({**before, "birth": {**before["birth"], "timezone": req[1]}}, after)
        # In production the seven UTC requests are refused before any calculation.
        for r in LEGACY_REQUESTS:
            if r[1] == "UTC":
                with self.subTest(request=r), self.assertRaises(InputRefusalError) as ctx:
                    calculate(request(*r), ephe_path=DATA)
                self.assertEqual(ctx.exception.code, "TIMEZONE_NOT_LOCATION_BASED")

    def recorded(self, req):
        """Run the engine with every Swiss call recorded."""
        calls = []

        def spy(name):
            real = getattr(swe, name)

            def wrapper(*args):
                calls.append((name, args))
                return real(*args)
            return wrapper
        with mock.patch.multiple(swe, **{n: spy(n) for n in ("set_sid_mode", "set_delta_t_userdef", "calc_ut",
                                                             "houses_ex")}):
            chart = calculate(req, ephe_path=DATA)
        return chart, calls

    def test_claims_match_the_recorded_swiss_calls(self):
        chart, calls = self.recorded(request("2026-10-22T06:00:00+05:30", "Asia/Kolkata", 12.97, 77.59))
        conv = chart["calculation_metadata"]["conventions"]
        sid = [args for name, args in calls if name == "set_sid_mode"]
        self.assertEqual(sid, [(swe.SIDM_LAHIRI, 0, 0)])
        self.assertEqual(conv["ayanamsa"]["swiss_mode_number"], swe.SIDM_LAHIRI)
        self.assertEqual(conv["ayanamsa"]["swiss_mode_number"], 1)
        planets = [args for name, args in calls if name == "calc_ut"]
        self.assertEqual({flags for _, _, flags in planets}, {conv["planetary_positions"]["swiss_flags_value"]})
        self.assertEqual(conv["planetary_positions"]["swiss_flags_value"], swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
        self.assertEqual(conv["planetary_positions"]["swiss_flags"], ["FLG_SWIEPH", "FLG_SIDEREAL"])
        self.assertEqual(sorted(body for _, body, _ in planets),
                         sorted(getattr(swe, b) for b in conv["planetary_positions"]["swiss_bodies"]))
        self.assertIn(swe.MEAN_NODE, [body for _, body, _ in planets])
        self.assertNotIn(swe.TRUE_NODE, [body for _, body, _ in planets])
        self.assertEqual((conv["nodes"]["rahu"], conv["nodes"]["rahu_swiss_body"]), ("mean", "MEAN_NODE"))
        houses = [args for name, args in calls if name == "houses_ex"]
        self.assertEqual(len(houses), 1)
        self.assertEqual(houses[0][3], conv["ascendant"]["swiss_house_system"].encode("ascii"))
        self.assertEqual(houses[0][3], b"W")
        self.assertEqual(houses[0][4], conv["ascendant"]["swiss_flags_value"])
        self.assertEqual(conv["ascendant"]["swiss_flags_value"], swe.FLG_SIDEREAL)
        self.assertEqual((conv["houses"]["d1_model"], chart["method"]["houses"]), ("whole_sign", "whole_sign"))
        self.assertEqual((conv["zodiac"], conv["ayanamsa"]["name"], chart["method"]["ayanamsa"]),
                         ("sidereal", "Lahiri", "Lahiri"))
        delta = [args for name, args in calls if name == "set_delta_t_userdef"]
        self.assertEqual(delta, [(swe.DELTAT_AUTOMATIC,)])
        self.assertIn("DELTAT_AUTOMATIC", chart["calculation_metadata"]["time_scale"]["delta_t"]["source"])

    def test_swiss_versions(self):
        meta = self.meta("2000-01-01T12:00:00+00:00")["swiss_ephemeris"]
        self.assertEqual(meta["library_version"], swe.version)
        self.assertEqual(meta["library_version"], self.chart("2000-01-01T12:00:00+00:00")["method"]["binding_version"])
        self.assertEqual(meta["python_binding_version"], importlib_metadata.version("pyswisseph"))
        pinned = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
        self.assertIn(f"pyswisseph=={meta['python_binding_version']}", pinned)
        self.assertIn(f"tzdata=={tzdata.__version__}", pinned)

    def test_ephemeris_provenance_is_the_verified_manifest(self):
        meta = self.meta("2000-01-01T12:00:00+00:00")["ephemeris_data"]
        manifest = ephemeris.load_manifest()
        self.assertEqual(meta["manifest_sha256"], provenance.canonical_sha256(manifest))
        # Recomputed here, independently of provenance.py, and pinned for the packaged manifest.
        packaged = json.loads((SRC / "sabpuja_kundali" / "ephemeris-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(packaged, manifest)
        self.assertEqual(meta["manifest_sha256"], hashlib.sha256(
            json.dumps(packaged, sort_keys=True, separators=(",", ":")).encode()).hexdigest())
        self.assertEqual(meta["manifest_sha256"], "1aaca24868bb9cde8558f891038ae239d8dce64beb77b90f963bb185e99b2e34")
        self.assertEqual(meta["required_files"], [{"name": e["name"], "size_bytes": e["size_bytes"],
                                                   "sha256": e["sha256"]} for e in manifest["files"] if e["required"]])
        self.assertEqual((meta["source_commit"], meta["coverage_years"]),
                         ("c69c14adb7a0f94829586ffd92cd422aacb21e86", [1800, 2399]))
        # The manifest is read once and the same object is verified and described.
        edited = json.loads(json.dumps(manifest))
        edited["purpose"] = "synthetic edit"
        seen = []
        real_verify = engine.verify_ephemeris_dir
        with mock.patch.object(engine, "load_ephemeris_manifest", return_value=edited) as load, \
             mock.patch.object(engine, "verify_ephemeris_dir",
                               side_effect=lambda p, m: (seen.append(m), real_verify(p, m))[1]):
            chart = calculate(request("2000-01-01T12:00:00+00:00"), ephe_path=DATA)
        self.assertEqual(load.call_count, 1)
        self.assertIs(seen[0], edited)
        self.assertEqual(chart["calculation_metadata"]["ephemeris_data"]["manifest_sha256"],
                         provenance.canonical_sha256(edited))
        self.assertNotEqual(provenance.canonical_sha256(edited), meta["manifest_sha256"])

    def test_damaged_ephemeris_or_manifest_refuses(self):
        manifest = ephemeris.load_manifest()
        wrong = json.loads(json.dumps(manifest))
        wrong["files"][0]["sha256"] = "0" * 64
        with mock.patch.object(engine, "load_ephemeris_manifest", return_value=wrong):
            with self.assertRaises(EphemerisDataError) as ctx:
                calculate(request("2000-01-01T12:00:00+00:00"), ephe_path=DATA)
        self.assertEqual(ctx.exception.code, "EPHEMERIS_FILE_MISMATCH")
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(Path(DATA) / "semo_18.se1", tmp)
            with self.assertRaises(EphemerisDataError) as ctx:
                calculate(request("2000-01-01T12:00:00+00:00"), ephe_path=tmp)
            self.assertEqual(ctx.exception.code, "EPHEMERIS_FILE_MISSING")
            shutil.copy(Path(DATA) / "sepl_18.se1", tmp)
            with open(Path(tmp) / "sepl_18.se1", "r+b") as handle:
                handle.seek(1000)
                handle.write(b"\x00")
            with self.assertRaises(EphemerisDataError) as ctx:
                calculate(request("2000-01-01T12:00:00+00:00"), ephe_path=tmp)
            self.assertEqual(ctx.exception.code, "EPHEMERIS_FILE_MISMATCH")

    def test_timezone_provenance_is_the_pinned_loader(self):
        meta = self.meta("2026-10-22T06:00:00+05:30", "Asia/Kolkata")["timezone_data"]
        manifest = timezones.load_manifest()
        self.assertEqual(meta["manifest_sha256"], timezones.manifest_digest(manifest))
        self.assertEqual(meta["manifest_sha256"], manifest["manifest_sha256"])
        self.assertEqual((meta["source"], meta["package_version"], meta["iana_version"]),
                         ("PyPI tzdata", tzdata.__version__, tzdata.IANA_VERSION))
        self.assertEqual((meta["package_version"], meta["iana_version"]), ("2026.5", "2026e"))
        self.assertIs(meta["host_timezone_database_used"], False)
        self.assertEqual({k: meta[k] for k in ("source", "package_version", "iana_version", "manifest_sha256")},
                         timezones.default_loader().provenance())

    def test_damaged_timezone_data_refuses_without_metadata(self):
        manifest = timezones.load_manifest()
        tampered = json.loads(json.dumps(manifest))
        tampered["iana_version"] = "2099z"
        with self.assertRaises(TimezoneDataError) as ctx:
            timezones.PinnedZoneLoader(tampered)
        self.assertEqual(ctx.exception.code, "TZDATA_MANIFEST_INVALID")
        tampered["manifest_sha256"] = timezones.manifest_digest(tampered)
        loader = timezones.PinnedZoneLoader(tampered)
        with mock.patch.object(timezones, "_LOADER", loader):
            with self.assertRaises(TimezoneDataError) as ctx:
                calculate(request("2026-10-22T06:00:00+05:30", "Asia/Kolkata"), ephe_path=DATA)
        self.assertEqual(ctx.exception.code, "TZDATA_VERSION_MISMATCH")
        entry = dict(manifest["zones"]["Asia/Kolkata"], sha256="0" * 64)
        bad = json.loads(json.dumps(manifest))
        bad["zones"]["Asia/Kolkata"] = entry
        bad["manifest_sha256"] = timezones.manifest_digest(bad)
        with mock.patch.object(timezones, "_LOADER", timezones.PinnedZoneLoader(bad)):
            with self.assertRaises(TimezoneDataError) as ctx:
                calculate(request("2026-10-22T06:00:00+05:30", "Asia/Kolkata"), ephe_path=DATA)
        self.assertEqual(ctx.exception.code, "TZDATA_FILE_MISMATCH")

    def test_time_scale_labels_at_era_boundaries(self):
        cases = [("1970-01-01T00:00:00+05:30", "Asia/Kolkata", "UTC_BEFORE_LEAP_SECONDS"),  # UTC 1969-12-31
                 ("1971-12-31T23:59:59+00:00", ZERO, "UTC_BEFORE_LEAP_SECONDS"),
                 ("1972-01-01T05:00:00+05:30", "Asia/Kolkata", "UTC_BEFORE_LEAP_SECONDS"),  # UTC 1971-12-31
                 ("1972-01-01T00:00:00+00:00", ZERO, "LEAP_SECOND_UTC"),
                 ("2027-05-19T23:59:59.999999+00:00", ZERO, "LEAP_SECOND_UTC"),
                 ("2027-05-20T05:29:59+05:30", "Asia/Kolkata", "LEAP_SECOND_UTC"),  # UTC 2027-05-19
                 ("2027-05-20T00:00:00+00:00", ZERO, "CONTINUOUS_UTC_TRANSITION_DATE"),
                 ("2027-05-20T05:30:00+05:30", "Asia/Kolkata", "CONTINUOUS_UTC_TRANSITION_DATE"),  # UTC 05-20 0h
                 ("2027-05-20T23:59:59.999999+00:00", ZERO, "CONTINUOUS_UTC_TRANSITION_DATE"),
                 ("2027-05-21T05:29:59+05:30", "Asia/Kolkata", "CONTINUOUS_UTC_TRANSITION_DATE"),  # UTC 05-20
                 ("2027-05-21T00:00:00+00:00", ZERO, "CONTINUOUS_UTC_AFTER_TRANSITION_DATE"),
                 ("2027-05-21T05:30:00+05:30", "Asia/Kolkata", "CONTINUOUS_UTC_AFTER_TRANSITION_DATE"),
                 ("2027-06-27T23:59:59.999999+00:00", ZERO, "CONTINUOUS_UTC_AFTER_TRANSITION_DATE"),
                 ("2027-06-28T03:00:00+05:30", "Asia/Kolkata", "CONTINUOUS_UTC_AFTER_TRANSITION_DATE"),  # UTC 06-27
                 ("2027-06-28T00:00:00+00:00", ZERO, "AFTER_LEAP_SECOND_LIST_EXPIRY"),
                 ("2100-12-31T23:59:59+00:00", ZERO, "AFTER_LEAP_SECOND_LIST_EXPIRY")]
        for birth, tz, era in cases:
            with self.subTest(birth=birth):
                ts = self.meta(birth, tz)["time_scale"]
                self.assertEqual((ts["era"], ts["era_basis"]), (era, "converted UTC instant"))
                self.assertEqual(ts["era_description"], {c: t for c, _, _, t in provenance.ERAS}[era])
                self.assertIs(ts["measured_ut1_minus_utc_used"], False)
                self.assertIs(ts["earth_orientation_data_used"], False)
                self.assertIn("treated as UT1", ts["ut1_assumption"])
                self.assertIn("assumption", ts["ut1_assumption"])
                self.assertEqual(ts["leap_second_list_expiry_utc"], "2027-06-28T00:00:00Z")

    def test_future_disclosure_around_2027_06_28(self):
        codes = lambda birth, tz=ZERO: [d["code"] for d in self.meta(birth, tz)["disclosures"]]
        self.assertEqual(codes("2027-06-27T23:59:59+00:00"), [])
        self.assertEqual(codes("2027-06-28T03:00:00+05:30", "Asia/Kolkata"), [])
        self.assertEqual(codes("2027-06-28T00:00:00+00:00"), ["FUTURE_CIVIL_TIME_PROJECTED"])
        self.assertEqual(codes("2027-06-27T20:00:00-04:00", "America/New_York"), ["FUTURE_CIVIL_TIME_PROJECTED"])
        self.assertNotIn("bound", self.meta("2030-01-01T00:00:00+00:00")["disclosures"][0]["description"])

    def test_sidereal_model_note_around_2050(self):
        side = lambda birth, tz=ZERO: self.meta(birth, tz)["time_scale"]["sidereal_time_model"]
        self.assertEqual(side("2049-12-31T23:59:59.999999+00:00")["chart_side"], "before_switch")
        self.assertEqual(side("2050-01-01T05:00:00+05:30", "Asia/Kolkata")["chart_side"], "before_switch")
        after = side("2050-01-01T00:00:00+00:00")
        self.assertEqual((after["chart_side"], after["switch_ut"], after["recorded_step_arcsec"]),
                         ("on_or_after_switch", "2050-01-01T00:00:00Z", -1.908))
        self.assertIn("not a precision guarantee", after["note"])

    def test_high_latitude_disclosure_is_descriptive_only(self):
        high = ["HIGH_LATITUDE_TIME_SENSITIVITY"]
        for lat, expected in ((0.0, []), (60.0, []), (-60.0, []), (math.nextafter(60.0, 90.0), high),
                              (math.nextafter(-60.0, -90.0), high), (66.0, high), (-66.0, high)):
            with self.subTest(lat=lat):
                chart = self.chart("2026-03-20T09:00:00+00:00", lat=lat, lon=-18.0)
                self.assertEqual([d["code"] for d in chart["calculation_metadata"]["disclosures"]], expected)
        # Disclosure never changes acceptance: the band edge is still the refusal edge.
        for lat in (math.nextafter(66.0, 90.0), math.nextafter(-66.0, -90.0), 70.0, -89.0):
            with self.subTest(lat=lat), self.assertRaises(InputRefusalError) as ctx:
                self.chart("2026-03-20T09:00:00+00:00", lat=lat)
            self.assertEqual(ctx.exception.code, "LATITUDE_OUTSIDE_SUPPORTED_BAND")

    def test_high_latitude_lagna_rate_is_not_uniformly_greater(self):
        # Deterministic Swiss regression behind the disclosure wording: Lagna motion over one UT second
        # at 0 deg E on 2024-06-15, 62 N against the equator. Faster at 00:00 UT, slower at 06:00 UT.
        def rate(start, lat):
            first = self.chart(f"2024-06-15T{start}:00+00:00", lat=lat, lon=0.0)["lagna"]["longitude_deg"]
            second = self.chart(f"2024-06-15T{start}:01+00:00", lat=lat, lon=0.0)["lagna"]["longitude_deg"]
            return (second - first) % 360.0
        rates = {(t, lat): rate(t, lat) for t in ("00:00", "06:00") for lat in (0.0, 62.0)}
        self.assertAlmostEqual(rates["00:00", 0.0], 0.00454375, delta=2e-8)
        self.assertAlmostEqual(rates["00:00", 62.0], 0.01878318, delta=2e-8)
        self.assertAlmostEqual(rates["06:00", 0.0], 0.00383991, delta=2e-8)
        self.assertAlmostEqual(rates["06:00", 62.0], 0.00247911, delta=2e-8)
        self.assertGreater(rates["00:00", 62.0], rates["00:00", 0.0])
        self.assertLess(rates["06:00", 62.0], rates["06:00", 0.0])
        self.assertEqual([d["code"] for d in self.meta("2024-06-15T06:00:00+00:00", lat=62.0, lon=0.0)["disclosures"]],
                         ["HIGH_LATITUDE_TIME_SENSITIVITY"])

    def test_input_policy_reads_engine_constants(self):
        policy = self.meta("2000-01-01T12:00:00+00:00")["input_policy"]
        self.assertEqual(policy["local_date_window"]["first"], engine.SUPPORTED_LOCAL_DATES[0].isoformat())
        self.assertEqual(policy["local_date_window"]["last"], "2100-12-31")
        self.assertEqual(policy["historical_clock"]["policy"], engine.HISTORICAL_CLOCK_POLICY)
        self.assertEqual(policy["historical_clock"]["refused_local_dates"],
                         [{"zone": "*", "first_local_date": None, "last_local_date": "1969-12-31"}])
        self.assertEqual(policy["historical_clock"]["exceptions"], [])
        self.assertEqual(policy["latitude_band_deg"], {"min": -66.0, "max": 66.0, "inclusive": True})
        # KUN-03 D3 (metadata_schema /2): the timezone identifier policy the chart passed. Zone policy
        # version 2 changes the values (four more refused names), not the shape.
        self.assertEqual(policy["timezone_identifier"], {
            "policy": zone_policy.ZONE_POLICY, "mode": "fail_closed",
            "rule": "geographic IANA timezone identifier required (exact match)",
            "refused_identifiers": ["UTC", "UCT", "Universal", "Zulu", "GMT", "GMT+0", "GMT-0", "GMT0",
                                    "Greenwich", "Factory", "CST6CDT", "EST5EDT", "MST7MDT", "PST8PDT"],
            "refused_prefixes": ["Etc/"], "zone_matches_coordinates_verified": False})
        self.assertEqual(policy["timezone_identifier"]["policy"],
                         "KUN-03 D3 location-based birthplace timezone, version 2")
        with mock.patch.object(zone_policy, "NON_LOCATION_IDENTIFIERS", ("UTC",)):  # read live, not copied
            self.assertEqual(self.meta("2000-01-01T12:00:00+00:00")["input_policy"]["timezone_identifier"]
                             ["refused_identifiers"], ["UTC"])

    def test_no_historical_clock_bypass(self):
        for birth in ("1969-12-31T23:59:59+00:00", "1950-06-15T10:00:00-03:00"):
            with self.subTest(birth=birth), self.assertRaises(InputRefusalError) as ctx:
                self.chart(birth, ZERO if birth.endswith("+00:00") else "America/Argentina/Buenos_Aires")
            self.assertEqual(ctx.exception.code, "HISTORICAL_CLOCK_UNVERIFIED")
        # Test-only override: the metadata reports the empty gate truthfully and the pre-UTC era.
        with mock.patch.object(engine, "HISTORICAL_CLOCK_GATE", ()):
            meta = self.meta("1950-06-15T13:00:00+00:00")
        self.assertEqual(meta["input_policy"]["historical_clock"]["refused_local_dates"], [])
        self.assertEqual(meta["time_scale"]["era"], "CIVIL_TIME_BEFORE_UTC")

    def test_refusal_codes_unchanged(self):
        cases = [(request("2026-03-08T02:30:00-05:00", "America/New_York"), "TIME_NONEXISTENT_LOCAL"),
                 (request("2026-03-08T03:30:00-04:00", "America/Chicago"), "TIME_OFFSET_MISMATCH"),
                 (request("2026-03-08T03:30:00"), "TIME_OFFSET_REQUIRED"),
                 (request("1899-12-31T23:59:59+00:00"), "DATE_OUTSIDE_SUPPORTED_RANGE"),
                 (request("2026-01-01T00:00:00+00:00", "Mars/Olympus"), "TIMEZONE_INVALID"),
                 (request("2026-01-01T00:00:00+00:00", lat=70.0), "LATITUDE_OUTSIDE_SUPPORTED_BAND"),
                 (request("2026-01-01T00:00:00+00:00", lon=180.5), "COORDINATE_INVALID"),
                 ({**request("2026-01-01T00:00:00+00:00"), "extra": 1}, "REQUEST_INVALID")]
        for req, code in cases:
            with self.subTest(code=code), self.assertRaises(InputRefusalError) as ctx:
                calculate(req, ephe_path=DATA)
            self.assertEqual(ctx.exception.code, code)

    def test_deterministic_and_no_request_or_path_text(self):
        with tempfile.TemporaryDirectory(prefix="PRIVATE-PATH-7f3a-") as tmp:
            for name in ("sepl_18.se1", "semo_18.se1"):
                shutil.copy(Path(DATA) / name, tmp)
            req = request("2026-10-22T06:00:00+05:30", "Asia/Kolkata", 12.9716, 77.5946)
            first = calculate(dict(req), ephe_path=tmp)
            second = calculate(dict(req), ephe_path=DATA)
            text = canonical(first["calculation_metadata"])
            for secret in ("PRIVATE-PATH-7f3a", tmp, DATA, "/home", "/tmp", "06:00:00", "12.9716", "77.5946",
                           "Asia/Kolkata", sys.prefix):
                self.assertNotIn(secret, text)
            self.assertEqual(canonical(first), canonical(second))

    def test_metadata_has_no_numbers_beyond_the_declared_ones(self):
        # No raw Delta T, Julian Day, sidereal time or other per-request number leaks in.
        numbers = []

        def walk(value, path):
            if isinstance(value, dict):
                for k, v in value.items():
                    walk(v, f"{path}.{k}")
            elif isinstance(value, list):
                for v in value:
                    walk(v, path + "[]")
            elif type(value) in (int, float):
                numbers.append(path)
        walk(self.meta("2030-01-01T00:00:00+00:00", lat=65.0), "m")
        self.assertEqual(sorted(set(numbers)), [
            "m.conventions.ascendant.swiss_flags_value", "m.conventions.ayanamsa.swiss_mode_number",
            "m.conventions.longitude_display.decimals", "m.conventions.planetary_positions.swiss_flags_value",
            "m.ephemeris_data.coverage_years[]", "m.ephemeris_data.required_files[].size_bytes",
            "m.input_policy.latitude_band_deg.max", "m.input_policy.latitude_band_deg.min",
            "m.time_scale.sidereal_time_model.recorded_step_arcsec"])

    def test_metadata_is_the_same_across_requests_of_one_era(self):
        a = self.meta("2000-01-01T12:00:00+00:00", lat=10.0, lon=20.0)
        b = self.meta("2010-07-01T03:00:00+05:30", "Asia/Kolkata", -30.0, -100.0)
        self.assertEqual(canonical(a), canonical(b))

    def test_host_timezone_and_tzpath_do_not_change_output(self):
        code = ("import json,sys\nfrom sabpuja_kundali.engine import calculate\n"
                f"r=calculate({request('2026-11-01T01:30:00-05:00', 'America/New_York', 40.7, -74.0)!r},"
                f"ephe_path={DATA!r})\nprint(json.dumps(r,sort_keys=True))\n")
        outs = set()
        for extra in ({}, {"TZ": "Pacific/Kiritimati"}, {"TZ": "Asia/Kolkata", "PYTHONTZPATH": "/nonexistent"}):
            env = {k: v for k, v in os.environ.items() if k not in ("TZ", "PYTHONTZPATH")}
            env.update(PYTHONPATH=str(SRC), **extra)
            proc = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env=env, timeout=120)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            outs.add(proc.stdout)
        self.assertEqual(len(outs), 1)

    def test_cli_success_carries_metadata_without_private_text(self):
        env = {**os.environ, "PYTHONPATH": str(SRC), "SABPUJA_EPHE_PATH": DATA}
        req = request("2026-10-22T06:00:00+05:30", "Asia/Kolkata", 12.9716, 77.5946)
        proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"], input=json.dumps(req),
                              capture_output=True, text=True, env=env, timeout=120)
        self.assertEqual((proc.returncode, proc.stderr), (0, ""))
        out = json.loads(proc.stdout)
        self.assertEqual(out["schema_version"], "0.2.0")
        self.assertEqual(out["calculation_metadata"], calculate(req, ephe_path=DATA)["calculation_metadata"])
        self.assertNotIn(DATA, proc.stdout)

    def test_delta_t_contamination_still_cleared(self):
        clean = canonical(self.chart("2026-10-22T06:00:00+05:30", "Asia/Kolkata"))
        swe.set_delta_t_userdef(0.5)
        try:
            dirty = self.chart("2026-10-22T06:00:00+05:30", "Asia/Kolkata")
        finally:
            swe.set_delta_t_userdef(swe.DELTAT_AUTOMATIC)
        self.assertEqual(canonical(dirty), clean)
        self.assertIs(dirty["calculation_metadata"]["time_scale"]["delta_t"]["user_override_used"], False)

    def test_concurrent_requests_keep_their_own_metadata(self):
        reqs = [request("2000-01-01T12:00:00+00:00"), request("2030-01-01T00:00:00+00:00", lat=63.0),
                request("2050-06-01T00:00:00+00:00", lat=-10.0)]
        expected = [canonical(calculate(r, ephe_path=DATA)) for r in reqs]
        results, errors = {}, []

        def worker(n):
            try:
                for i in range(15):
                    k = (n + i) % 3
                    results.setdefault(k, set()).add(canonical(calculate(reqs[k], ephe_path=DATA)))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)
        threads = [threading.Thread(target=worker, args=(n,), daemon=True) for n in range(6)]
        for t in threads:
            t.start()
        deadline = __import__("time").monotonic() + 120
        for t in threads:
            t.join(max(0.0, deadline - __import__("time").monotonic()))
        self.assertFalse(any(t.is_alive() for t in threads))
        self.assertEqual(errors, [])
        self.assertEqual({k: v for k, v in results.items()}, {k: {expected[k]} for k in range(3)})


if __name__ == "__main__":
    unittest.main()
