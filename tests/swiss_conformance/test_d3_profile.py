"""KUN-03 D3 conformance profile: fail-closed D3 overlay, D3 refusals, numeric continuation, divergence.

The active profile is D3 profile v2 (zone policy version 2); the archived D3
profile v1 stays byte-identical and is reproduced only in a test-only,
versioned compatibility context.

The profile, refusal and override tests need no Swiss data or swetest. Tests
that compute charts need SABPUJA_TEST_EPHE_PATH (unset skips); the swetest class
is skipped only when SABPUJA_TEST_SWETEST is unset and errors if it is set but
the binary, receipt or data are not valid. Swiss-on-Swiss conformance only.
"""
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock
import json
import os
import tempfile
import unittest

from sabpuja_kundali import engine, zone_policy

from . import conformance as c
from . import current as cur
from . import d3, inputs, profile
from .test_parser_and_gates import env_ok

SWETEST = os.environ.get("SABPUJA_TEST_SWETEST")
RECEIPT = os.environ.get("SABPUJA_TEST_SWETEST_RECEIPT")
EPHE = os.environ.get("SABPUJA_TEST_EPHE_PATH")
PROFILE_TEXT = d3.PROFILE_PATH.read_text(encoding="utf-8")
CASES = {case["id"]: case for case in c.load_json(c.HERE / "cases.json")["cases"]}
SPEC = c.load_json(c.HERE / "spec.json")
D3 = "TIMEZONE_NOT_LOCATION_BASED"


def must_not_run(*args, **kwargs):
    raise AssertionError("engine or swetest must not run")


class Profile(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def test_profile_is_valid_hashed_and_counts_match(self):
        doc, record, errors = d3.load_profile()
        self.assertEqual(errors, [])
        self.assertEqual(record["sha256"], d3.PROFILE_SHA256)
        counts = d3.COUNTS
        self.assertEqual((counts["chart_cases"], counts["refusal_cases"], counts["comparison_checks"],
                          counts["self_consistency_checks"], counts["house_method_checks"], counts["refusal_checks"]),
                         (7, 17, 343, 14, 28, 34))
        # Every comparison check of profile v1 is accounted for: 343 + 147 + 294 = 784.
        self.assertEqual((counts["geographic_equivalent_comparison_checks"],
                          counts["d3_override_supplement_comparison_checks"], counts["v1_comparison_checks_accounted"]),
                         (147, 294, 784))
        self.assertEqual(counts["v1_comparison_checks_accounted"], profile.COUNTS["comparison_checks"])
        self.assertEqual(counts["v1_historical_supplement_comparison_checks_accounted"],
                         profile.COUNTS["historical_supplement_comparison_checks"])
        self.assertEqual(d3.NEWLY_REFUSED, ("SC-01", "SC-04", "SC-11", "SC-14", "SC-15", "SC-16", "SC-19", "SC-20",
                                            "SC-24"))
        self.assertEqual(d3.REFUSED_EARLIER, ("SC-09", "SC-10", "SC-12", "SC-13", "SC-17", "SC-18"))
        self.assertEqual(sorted([*d3.GEOGRAPHIC_EQUIVALENTS, *d3.D3_OVERRIDE_SUPPLEMENT]),
                         [cid for cid in d3.NEWLY_REFUSED])
        self.assertEqual(doc["zone_policy"], zone_policy.ZONE_POLICY)
        self.assertEqual((doc["profile_version"], doc["zone_policy"]),
                         (2, "KUN-03 D3 location-based birthplace timezone, version 2"))

    def test_v2_lineage_is_the_owner_delta_and_keeps_every_v1_expectation(self):
        v1, record, errors = d3.load_v1_profile()
        self.assertEqual((errors, record["sha256"]), ([], d3.V1_PROFILE_SHA256))
        self.assertEqual((v1["profile_version"], v1["zone_policy"]),
                         (1, "KUN-03 D3 location-based birthplace timezone, version 1"))
        doc = json.loads(PROFILE_TEXT)
        for key in d3.UNCHANGED_FROM_V1:
            self.assertEqual(doc[key], v1[key], key)
        self.assertEqual(set(doc) - set(v1), {"lineage"})
        change = doc["lineage"]["policy_change"]
        self.assertEqual(change["added_refused_identifiers"],
                         sorted(set(zone_policy.NON_LOCATION_IDENTIFIERS) - set(d3.V1_NON_LOCATION_IDENTIFIERS)))
        self.assertEqual(change["added_refused_identifiers"], ["CST6CDT", "EST5EDT", "MST7MDT", "PST8PDT"])
        self.assertEqual(change["kept_accepted_identifiers"], list(zone_policy.REVIEWED_ACCEPTED))
        self.assertEqual(change["affected_cases"], [])  # no frozen request uses the four names
        self.assertFalse({r["timezone"] for r in d3._REQUESTS.values()} & set(change["added_refused_identifiers"]))
        self.assertEqual(doc["lineage"]["previous_d3_profile"]["sha256"], d3.V1_PROFILE_SHA256)

    def test_frozen_inputs_and_v1_profile_untouched(self):
        frozen = {"spec.json": "642a770d713c11bc42fc92fe441da02e4848522fc4978ae3049dddbea33d12a8",
                  "cases.json": "afd8864cd84c246011d9ed8510b3efa5ed5e6c68daa6381114a77adf0ef399c9",
                  "profiles/kun03-current-v1.json": "06d24730205213b680223aaa4077b9efc44335a4eb1638f98deb622bbc17e698",
                  "profiles/kun03-d3-v1.json": "942a0eac0a18b45f26de91b238d0b5b3868713076a4a50e457598b1fa999b980"}
        for name, digest in frozen.items():
            self.assertEqual(inputs.sha256_bytes((c.HERE / name).read_bytes()), digest)
        self.assertEqual(profile.PROFILE_SHA256, frozen["profiles/kun03-current-v1.json"])
        self.assertEqual(d3.V1_PROFILE_SHA256, frozen["profiles/kun03-d3-v1.json"])
        self.assertEqual(profile.load_profile()[2], [])
        self.assertEqual(inputs.TOLERANCES, {"binding_vs_swetest": 1e-09, "engine_vs_swetest": 1e-08,
                                             "swetest_ut_jd_day": 1e-09, "independent_jd_day": 1e-09,
                                             "ketu_identity_deg": 1e-08})

    def test_every_case_records_its_v1_outcome(self):
        doc = json.loads(PROFILE_TEXT)
        for entry in doc["cases"]:
            with self.subTest(case=entry["id"]):
                v1 = profile.CURRENT_CASES[entry["id"]]
                self.assertEqual(entry["previous"]["expected_refusal"], None if v1 == "chart" else v1)
                self.assertEqual(entry["change"] is None, entry["id"] not in d3.CHANGED_CASES)

    def edited(self, edit):
        doc = json.loads(PROFILE_TEXT)
        edit(doc)
        path = Path(self.tmp.name) / "profile.json"
        path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
        return path

    def blocked(self, path, *codes):
        with mock.patch.object(d3, "run_d3_case", side_effect=must_not_run), \
             mock.patch.object(d3, "run_geographic_case", side_effect=must_not_run), \
             mock.patch.object(d3, "run_override_case", side_effect=must_not_run), \
             mock.patch.object(d3, "v1_divergence", side_effect=must_not_run), \
             mock.patch.object(cur, "call_engine", side_effect=must_not_run), \
             mock.patch.object(c, "run_all", side_effect=must_not_run), \
             mock.patch.object(cur.swetest_cli, "run", side_effect=must_not_run):
            report = d3.run_all("x", "y", "z", env=env_ok(), profile_path=path)
        self.assertEqual((report["verdict"], report["exit_code"], report["cases"]), ("SWISS-CONFORMANCE BLOCKED", 2, []))
        self.assertEqual(set(report["verdicts"].values()), {"SWISS-CONFORMANCE BLOCKED"})
        for wanted in codes:
            self.assertIn(wanted, report["run_reasons"])
        return report

    def test_any_byte_change_blocks(self):
        path = Path(self.tmp.name) / "p.json"
        path.write_text(PROFILE_TEXT.replace("\"profile_version\": 2", "\"profile_version\": 2 "), encoding="utf-8")
        self.blocked(path, "D3_PROFILE_SHA256_MISMATCH")
        self.blocked(Path(self.tmp.name) / "absent.json", "D3_PROFILE_MISSING")

    def test_field_edits_block_even_with_a_forged_hash(self):
        def case(cid):
            return lambda d: next(e for e in d["cases"] if e["id"] == cid)
        geo = lambda d: d["numeric_continuation"]["geographic_equivalents"]
        sup = lambda d: d["numeric_continuation"]["d3_override_supplement"]
        edits = {
            "case removed": (lambda d: d["cases"].pop(), "D3_PROFILE_CASE_MISSING: SC-24"),
            "case duplicated": (lambda d: d["cases"].append(dict(d["cases"][0])), "D3_PROFILE_CASE_DUPLICATE"),
            "case order": (lambda d: d["cases"].reverse(), "D3_PROFILE_CASE_ORDER"),
            "UTC chart accepted": (lambda d: case("SC-01")(d).update(expect="chart", expected_refusal=None),
                                   "D3_PROFILE_CASE_CODE: SC-01"),
            "Etc code reverted": (lambda d: case("SC-13")(d).update(expected_refusal="HISTORICAL_CLOCK_UNVERIFIED"),
                                  "D3_PROFILE_CASE_CODE: SC-13"),
            "reported as invalid": (lambda d: case("SC-14")(d).update(expected_refusal="TIMEZONE_INVALID"),
                                    "D3_PROFILE_CASE_CODE: SC-14"),
            "previous misstated": (lambda d: case("SC-10")(d)["previous"].update(expected_refusal=None),
                                   "D3_PROFILE_CASE_PREVIOUS: SC-10"),
            "reason removed": (lambda d: case("SC-24")(d)["change"].update(reason=" "), "D3_PROFILE_CASE_CHANGE: SC-24"),
            "continuation dropped": (lambda d: case("SC-11")(d)["change"].update(numeric_continuation=None),
                                     "D3_PROFILE_CASE_CHANGE: SC-11"),
            "unrecorded change": (lambda d: case("SC-02")(d).update(change=case("SC-01")(d)["change"]),
                                  "D3_PROFILE_CASE_CHANGE: SC-02"),
            "equivalent zone edited": (lambda d: geo(d)["cases"]["SC-24"].update(timezone="Europe/London"),
                                       "D3_PROFILE_GEOGRAPHIC_EQUIVALENTS"),
            "equivalent removed": (lambda d: geo(d)["cases"].pop("SC-04"), "D3_PROFILE_GEOGRAPHIC_EQUIVALENTS"),
            "supplement widened": (lambda d: sup(d)["cases"].append("SC-02"), "D3_PROFILE_OVERRIDE_SUPPLEMENT"),
            "supplement shrunk": (lambda d: sup(d)["cases"].pop(), "D3_PROFILE_OVERRIDE_SUPPLEMENT"),
            "supplement relabelled": (lambda d: sup(d).update(label="production numerics"),
                                      "D3_PROFILE_OVERRIDE_SUPPLEMENT"),
            "historical overrides edited": (lambda d: d["historical_numerics_supplement"]["cases"].update(
                {"SC-09": ["historical_clock"]}), "D3_PROFILE_HISTORICAL_SUPPLEMENT"),
            "comparison count reduced": (lambda d: d["counts"].update(comparison_checks=294), "D3_PROFILE_COUNTS"),
            "accounting forged": (lambda d: d["counts"].update(v1_comparison_checks_accounted=735), "D3_PROFILE_COUNTS"),
            "v1 divergence edited": (lambda d: d["expected_divergence"]["v1_current_profile"]["cases"].pop("SC-24"),
                                     "D3_PROFILE_DIVERGENCE"),
            "archival divergence edited": (lambda d: d["expected_divergence"]["archival_pr18"].pop("SC-23"),
                                           "D3_PROFILE_DIVERGENCE"),
            "base hash forged": (lambda d: d["base"].update({"cases.json": "0" * 64}), "D3_PROFILE_BASE_HASH"),
            "v1 profile hash forged": (lambda d: d["base"]["previous_profile"].update(sha256="0" * 64),
                                       "D3_PROFILE_BASE_HASH"),
            "zone policy renamed": (lambda d: d.update(zone_policy="KUN-03 D3, version 2"), "D3_PROFILE_ZONE_POLICY"),
            "zone policy left at version 1": (lambda d: d.update(
                zone_policy="KUN-03 D3 location-based birthplace timezone, version 1"), "D3_PROFILE_ZONE_POLICY"),
            "lineage widened": (lambda d: d["lineage"]["policy_change"]["added_refused_identifiers"].append("CET"),
                                "D3_PROFILE_LINEAGE"),
            "lineage narrowed": (lambda d: d["lineage"]["policy_change"]["added_refused_identifiers"].pop(),
                                 "D3_PROFILE_LINEAGE"),
            "kept alias dropped": (lambda d: d["lineage"]["policy_change"]["kept_accepted_identifiers"].remove("HST"),
                                   "D3_PROFILE_LINEAGE"),
            "affected case claimed": (lambda d: d["lineage"]["policy_change"]["affected_cases"].append("SC-05"),
                                      "D3_PROFILE_LINEAGE"),
            "previous D3 profile hash forged": (lambda d: d["lineage"]["previous_d3_profile"].update(sha256="0" * 64),
                                                "D3_PROFILE_LINEAGE"),
            "lineage removed": (lambda d: d.pop("lineage"), "D3_PROFILE_KEYS"),
            "geolocation claimed": (lambda d: d.update(claim_boundary=d["claim_boundary"].replace(
                "NOT geolocation", "geolocation")), "D3_PROFILE_CLAIM_BOUNDARY"),
            "version bumped": (lambda d: d.update(profile_version=3), "D3_PROFILE_VERSION"),
            "version reverted": (lambda d: d.update(profile_version=1), "D3_PROFILE_VERSION"),
            "schema reverted": (lambda d: d.update(schema="sabpuja-swiss-conformance-d3-profile/1"), "D3_PROFILE_SCHEMA"),
            "expectation drifts from archived v1": (lambda d: d["placidus_reference_observations"].update(reason="x"),
                                                    "D3_PROFILE_LINEAGE_DRIFT: placidus_reference_observations"),
            "extra key": (lambda d: d.update(bypass=True), "D3_PROFILE_KEYS"),
        }
        for label, (edit, wanted) in edits.items():
            with self.subTest(edit=label):
                path = self.edited(edit)
                with mock.patch.object(d3, "PROFILE_SHA256", inputs.sha256_bytes(path.read_bytes())):
                    report = self.blocked(path, wanted)
                self.assertNotIn("D3_PROFILE_SHA256_MISMATCH", report["run_reasons"])

    def test_strict_json(self):
        for text, wanted in (("{", "D3_PROFILE_INVALID_JSON"), ('{"a": 1, "a": 2}', "D3_PROFILE_DUPLICATE_KEY"),
                             ('{"a": NaN}', "D3_PROFILE_NON_FINITE_NUMBER")):
            with self.subTest(text=text):
                path = Path(self.tmp.name) / "p.json"
                path.write_text(text, encoding="utf-8")
                self.blocked(path, wanted)

    def test_code_table_drift_blocks(self):
        with mock.patch.object(d3, "D3_CASES", dict(d3.D3_CASES, **{"SC-01": "chart"})):
            self.assertIn("D3_PROFILE_CASE_CODE: SC-01", d3.load_profile()[2])
        with mock.patch.dict(d3.COUNTS, comparison_checks=294):
            self.assertIn("D3_PROFILE_COUNTS", d3.load_profile()[2])

    def test_frozen_input_or_v1_profile_edit_blocks_the_d3_runner(self):
        with mock.patch.dict(inputs.INPUT_SHA256, {"cases.json": "0" * 64}):
            self.blocked(d3.PROFILE_PATH, "CASES_SHA256_MISMATCH", "D3_PROFILE_BASE_HASH")
        with mock.patch.object(profile, "PROFILE_SHA256", "0" * 64):
            self.blocked(d3.PROFILE_PATH, "PROFILE_SHA256_MISMATCH", "D3_PROFILE_BASE_HASH")

    def test_archived_d3_v1_profile_edit_blocks_the_d3_runner(self):
        v1_text = d3.V1_PROFILE_PATH.read_text(encoding="utf-8")
        path = Path(self.tmp.name) / "d3-v1.json"
        path.write_text(v1_text.replace("\"profile_version\": 1", "\"profile_version\": 1 "), encoding="utf-8")
        with mock.patch.object(d3, "V1_PROFILE_PATH", path):
            self.blocked(d3.PROFILE_PATH, "D3_V1_PROFILE_SHA256_MISMATCH")
        with mock.patch.object(d3, "V1_PROFILE_PATH", Path(self.tmp.name) / "absent.json"):
            self.blocked(d3.PROFILE_PATH, "D3_V1_PROFILE_MISSING")
        # Re-pinned after an edit: still blocked, by version or by lineage drift.
        for edit, wanted in ((lambda d: d.update(zone_policy="x"), "D3_V1_PROFILE_VERSION"),
                             (lambda d: d["counts"].update(comparison_checks=294), "D3_PROFILE_LINEAGE_DRIFT: counts")):
            doc = json.loads(v1_text)
            edit(doc)
            path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            with self.subTest(wanted=wanted), mock.patch.object(d3, "V1_PROFILE_PATH", path), \
                    mock.patch.object(d3, "V1_PROFILE_SHA256", inputs.sha256_bytes(path.read_bytes())):
                self.blocked(d3.PROFILE_PATH, wanted)

    def test_production_policy_must_match_the_recorded_lineage(self):
        real = zone_policy.is_location_based
        for name in ("CST6CDT", "PST8PDT"):
            with self.subTest(reaccepted=name), \
                    mock.patch.object(zone_policy, "NON_LOCATION_IDENTIFIERS",
                                      tuple(n for n in zone_policy.NON_LOCATION_IDENTIFIERS if n != name)):
                self.assertIn("D3_PROFILE_LINEAGE", d3.load_profile()[2])
        with mock.patch.object(zone_policy, "is_location_based", lambda name: real(name) and name != "WET"):
            self.assertIn("D3_PROFILE_LINEAGE", d3.load_profile()[2])
        with mock.patch.object(zone_policy, "ZONE_POLICY", d3.V1_ZONE_POLICY):
            self.assertIn("D3_PROFILE_ZONE_POLICY", d3.load_profile()[2])
        self.assertEqual(d3.load_profile()[2], [])


class Refusals(unittest.TestCase):
    """D3 codes, precedence and pre-ephemeris refusal on the frozen requests; no Swiss data needed."""

    def test_every_refusal_case_has_its_code_before_ephemeris_and_swiss(self):
        for cid, expected in d3.D3_CASES.items():
            if expected == "chart":
                continue
            with self.subTest(case=cid):
                status, payload, record = cur.call_engine(CASES[cid]["request"], "/nonexistent-ephemeris")
                self.assertEqual((status, payload), ("refused", expected))
                self.assertEqual(record, {"ephemeris_checked": False, "swiss_calls": [], "houses_ex": []})

    def test_d3_precedes_the_later_codes_it_now_hides(self):
        # Each formerly reported code is still what a geographic zone gets for the same wall time.
        cases = {"SC-09": ("Europe/London", "HISTORICAL_CLOCK_UNVERIFIED"),
                 "SC-10": ("Europe/London", "DATE_OUTSIDE_SUPPORTED_RANGE"),
                 "SC-12": ("Africa/Abidjan", "DATE_OUTSIDE_SUPPORTED_RANGE"),
                 "SC-17": ("Africa/Abidjan", "LATITUDE_OUTSIDE_SUPPORTED_BAND"),
                 "SC-18": ("Africa/Abidjan", "LATITUDE_OUTSIDE_SUPPORTED_BAND")}
        for cid, (key, code) in cases.items():
            with self.subTest(case=cid):
                request = dict(CASES[cid]["request"], timezone=key)
                self.assertEqual(cur.call_engine(request, "/nonexistent-ephemeris")[:2], ("refused", code))
        # SC-13 (Etc/GMT-3, local 1900): the same 1900 wall time is gated on a geographic zone.
        request = dict(CASES["SC-13"]["request"], timezone="Asia/Baghdad", birth_datetime="1900-01-01T02:00:00+02:57:36")
        self.assertEqual(cur.call_engine(request, "/nonexistent-ephemeris")[:2], ("refused", "HISTORICAL_CLOCK_UNVERIFIED"))
        # Syntax and unknown-key codes still precede D3.
        for fields, code in (({"birth_datetime": "2000-01-01T12:00:00"}, "TIME_OFFSET_REQUIRED"),
                             ({"timezone": "Etc/Mars"}, "TIMEZONE_INVALID"), ({"timezone": "utc"}, "TIMEZONE_INVALID")):
            with self.subTest(fields=fields):
                request = dict(CASES["SC-01"]["request"], **fields)
                self.assertEqual(cur.call_engine(request, "/nonexistent-ephemeris")[:2], ("refused", code))

    def test_v1_policy_context_is_scoped_versioned_and_restored(self):
        current = (zone_policy.ZONE_POLICY, zone_policy.NON_LOCATION_IDENTIFIERS)
        with d3.v1_policy_context():
            self.assertEqual(zone_policy.ZONE_POLICY, d3.V1_ZONE_POLICY)
            self.assertTrue(all(zone_policy.is_location_based(n) for n in ("CST6CDT", "EST5EDT", "MST7MDT", "PST8PDT")))
            self.assertFalse(zone_policy.is_location_based("UTC"))
            request = {**CASES["SC-05"]["request"], "timezone": "EST5EDT"}
            self.assertEqual(cur.call_engine(request, "/nonexistent-ephemeris")[:2], ("blocked", "EPHEMERIS_PATH_MISSING"))
        self.assertEqual((zone_policy.ZONE_POLICY, zone_policy.NON_LOCATION_IDENTIFIERS), current)
        self.assertEqual(cur.call_engine(request, "/nonexistent-ephemeris")[:2], ("refused", D3))

    def test_d3_override_is_scoped_and_restored(self):
        original = zone_policy.is_location_based
        with d3.d3_override():
            self.assertTrue(zone_policy.is_location_based("UTC"))
        self.assertIs(zone_policy.is_location_based, original)
        self.assertEqual(cur.call_engine(CASES["SC-01"]["request"], "/nonexistent-ephemeris")[:2], ("refused", D3))
        self.assertTrue(d3._restored(CASES["SC-01"], "/nonexistent-ephemeris"))
        # A policy left accepting UTC after an override block is reported as not restored.
        with mock.patch.object(zone_policy, "NON_LOCATION_IDENTIFIERS", ()):
            self.assertFalse(d3._restored(CASES["SC-01"], "/nonexistent-ephemeris"))
        self.assertFalse(zone_policy.is_location_based("UTC"))

    def test_geographic_equivalents_keep_the_frozen_instant_with_a_pinned_offset(self):
        from sabpuja_kundali.timezones import get_zone
        for cid, fields in d3.GEOGRAPHIC_EQUIVALENTS.items():
            with self.subTest(case=cid):
                written = datetime.fromisoformat(fields["birth_datetime"])
                utc = datetime.fromisoformat(CASES[cid]["expected_utc"].replace("Z", "+00:00"))
                self.assertEqual(written.astimezone(timezone.utc), utc)
                self.assertEqual(utc.astimezone(get_zone(fields["timezone"])).utcoffset(), written.utcoffset())
                self.assertTrue(zone_policy.is_location_based(fields["timezone"]))
                self.assertEqual(engine._parse_birth(fields["birth_datetime"], fields["timezone"]), utc)

    def test_override_supplement_has_no_geographic_equivalent_in_the_window(self):
        # SC-11: the same instant in Tokyo is local 2101-01-01, outside the local-date window.
        request = dict(CASES["SC-11"]["request"], birth_datetime="2101-01-01T08:59:59+09:00", timezone="Asia/Tokyo")
        self.assertEqual(cur.call_engine(request, "/nonexistent-ephemeris")[:2], ("refused", "DATE_OUTSIDE_SUPPORTED_RANGE"))


class CoverageAndDivergence(unittest.TestCase):
    def chart(self, cid):
        return {"case": cid, "expect": "chart", "outcome": c.PASS,
                "checks": [{"kind": "x", "quantity": q, "outcome": c.PASS, "value": 1} for q in inputs.CHART_QUANTITIES],
                "self_consistency": [{"result": "SELF-CONSISTENCY PASS"}] * 2,
                "method_checks": [{"quantity": q, "outcome": c.PASS} for q in cur.HOUSE_METHOD_QUANTITIES]}

    def fake(self):
        results = []
        for cid, expected in d3.D3_CASES.items():
            if expected == "chart":
                results.append(self.chart(cid))
                continue
            obs = cur.OBSERVATION_QUANTITIES if cid in d3.PLACIDUS_OBSERVATION_CASES else ()
            results.append({"case": cid, "expect": "refuse", "outcome": c.PASS, "self_consistency": [],
                            "method_checks": [], "checks": [{"quantity": q, "outcome": c.PASS} for q in cur.REFUSAL_QUANTITIES],
                            "reference_observations": [{"quantity": q, "outcome": c.PASS} for q in obs]})
        geographic = [dict(self.chart(cid), equivalence=[{"quantity": d3.EQUIVALENCE_QUANTITY, "outcome": c.PASS}])
                      for cid in d3.GEOGRAPHIC_EQUIVALENTS]
        supplement = [self.chart(cid) for cid in d3.D3_OVERRIDE_SUPPLEMENT]
        historical = [self.chart(cid) for cid in d3.HISTORICAL_SUPPLEMENT]
        return results, geographic, supplement, historical

    def test_full_coverage_accounts_for_every_v1_check(self):
        counts, errors = d3.coverage(*self.fake())
        self.assertEqual(errors, [])
        self.assertEqual((counts["comparison_checks"], counts["geographic_equivalent_comparison_checks"],
                          counts["d3_override_supplement_comparison_checks"], counts["v1_comparison_checks_accounted"],
                          counts["historical_supplement_comparison_checks"], counts["refusal_checks"]),
                         (343, 147, 294, 784, 98, 34))

    def test_silently_reduced_coverage_blocks(self):
        rows = self.fake()
        rows[0][1]["checks"].pop()
        self.assertIn("COVERAGE_CHART_QUANTITIES: d3 SC-02", d3.coverage(*rows)[1])
        rows = self.fake()
        rows[1][0]["equivalence"] = []
        self.assertIn("COVERAGE_EQUIVALENCE: SC-01", d3.coverage(*rows)[1])
        rows = self.fake()
        self.assertIn("COVERAGE_OVERRIDE_SUPPLEMENT_SET", d3.coverage(rows[0], rows[1], rows[2][:-1], rows[3])[1])
        rows = self.fake()
        self.assertIn("COVERAGE_V1_CHECKS_NOT_ACCOUNTED", d3.coverage(rows[0], rows[1][:-1], rows[2], rows[3])[1])
        rows = self.fake()
        self.assertIn("COVERAGE_CASE_SET", d3.coverage(rows[0][:-1], *rows[1:])[1])
        rows = self.fake()
        next(r for r in rows[0] if r["case"] == "SC-17")["reference_observations"] = []
        self.assertIn("COVERAGE_PLACIDUS_OBSERVATIONS: SC-17", d3.coverage(*rows)[1])

    def archival(self, failed=None):
        failed = dict(d3.ARCHIVAL_DIVERGENCE) if failed is None else failed
        results = self.fake()[0]
        cases = [{"case": cid, "outcome": c.FAIL if cid in failed else c.PASS,
                  "reasons": [failed[cid]] if cid in failed else [],
                  "checks": next((r["checks"] for r in results if r["case"] == cid and r["expect"] == "chart"), [])}
                 for cid in d3.D3_CASES]
        return {"run_reasons": [], "cases": cases, "verdict": c.VERDICT[c.FAIL]}, results

    def test_archival_divergence_is_exact(self):
        self.assertEqual(d3.archival_divergence(*self.archival())["outcome"], c.PASS)
        self.assertEqual(len(d3.ARCHIVAL_DIVERGENCE), 13)
        less = {k: v for k, v in d3.ARCHIVAL_DIVERGENCE.items() if k != "SC-24"}
        self.assertEqual(d3.archival_divergence(*self.archival(less))["outcome"], c.FAIL)
        more = dict(d3.ARCHIVAL_DIVERGENCE, **{"SC-02": "x"})
        self.assertEqual(d3.archival_divergence(*self.archival(more))["outcome"], c.FAIL)
        archival, results = self.archival()
        archival["run_reasons"] = ["SWETEST_MISSING"]
        self.assertEqual(d3.archival_divergence(archival, results)["outcome"], c.BLOCKED)


class MissingReferences(unittest.TestCase):
    def test_missing_swetest_is_never_pass(self):
        env = env_ok(swetest={"present": False, "sha256": None, "receipt": None, "receipt_errors": []})
        with mock.patch.object(d3, "run_d3_case", side_effect=must_not_run):
            report = d3.run_all(None, EPHE, None, env=env)
        self.assertEqual((report["exit_code"], report["cases"]), (2, []))
        self.assertIn("SWETEST_MISSING", report["run_reasons"])
        self.assertEqual(set(report["verdicts"].values()), {"SWISS-CONFORMANCE BLOCKED"})


@unittest.skipIf(not EPHE, "SABPUJA_TEST_EPHE_PATH unset: chart-computing tests skipped")
class Continuation(unittest.TestCase):
    def test_geographic_equivalents_equal_the_original_with_d3_bypassed(self):
        for cid, fields in d3.GEOGRAPHIC_EQUIVALENTS.items():
            with self.subTest(case=cid):
                status, chart, _ = cur.call_engine({**CASES[cid]["request"], **fields}, EPHE)
                with d3.d3_override():
                    _, original, _ = cur.call_engine(CASES[cid]["request"], EPHE)
                self.assertEqual(status, "chart")
                self.assertEqual(chart["birth"]["utc"], CASES[cid]["expected_utc"])
                self.assertEqual(chart, {**original, "birth": {**original["birth"], "timezone": fields["timezone"]}})

    def test_override_supplement_charts_only_with_the_override(self):
        for cid in d3.D3_OVERRIDE_SUPPLEMENT:
            with self.subTest(case=cid):
                with d3.d3_override():
                    status, chart, _ = cur.call_engine(CASES[cid]["request"], EPHE)
                self.assertEqual((status, chart["birth"]["utc"]), ("chart", CASES[cid]["expected_utc"]))
                self.assertEqual(cur.call_engine(CASES[cid]["request"], EPHE)[:2], ("refused", D3))


@unittest.skipIf(SWETEST is None, "SABPUJA_TEST_SWETEST unset: swetest conformance not requested")
class D3ProfileWithSwetest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not EPHE:
            raise RuntimeError("SABPUJA_TEST_SWETEST is set but SABPUJA_TEST_EPHE_PATH is not")
        env = c.capture_environment(SWETEST, RECEIPT, EPHE)
        problems = [r for r in c.run_reasons(env, SPEC) if r not in ("DIRTY_TREE", "GIT_UNAVAILABLE")]
        if problems:
            raise RuntimeError(f"swetest environment not valid: {problems}")
        cls.env = dict(env, git={"commit": env["git"]["commit"], "dirty": False})

    def test_full_run(self):
        report = d3.run_all(SWETEST, EPHE, RECEIPT, env=self.env)
        self.assertEqual(report["verdicts"], dict.fromkeys(("d3", "numeric_continuation", "historical_supplement",
                                                            "v1_divergence", "archival_divergence",
                                                            "archived_d3_v1_policy"),
                                                           "SWISS-CONFORMANCE PASS"))
        archived = report["archived_d3_v1_policy"]
        self.assertEqual((archived["cases_checked"], archived["charts"], archived["accepted_inside"], archived["restored"]),
                         (24, 7, ["CST6CDT", "EST5EDT", "MST7MDT", "PST8PDT"], True))
        self.assertEqual(report["profile"]["previous_d3_profile_sha256"], d3.V1_PROFILE_SHA256)
        self.assertEqual(report["inputs"]["profile_d3_v1"]["sha256"], d3.V1_PROFILE_SHA256)
        self.assertEqual(report["coverage_errors"], [])
        self.assertEqual(report["v1_divergence"]["observed"], d3.V1_DIVERGENCE)
        self.assertEqual(report["archival"]["verdict"], "SWISS-CONFORMANCE FAIL")
        self.assertEqual([r["override_restored"] for r in report["geographic_equivalents"] + report[
            "d3_override_supplement"] + report["historical_supplement"]], [True] * 11)

    def test_accepting_utc_in_production_fails(self):
        with mock.patch.object(zone_policy, "NON_LOCATION_IDENTIFIERS",
                               tuple(n for n in zone_policy.NON_LOCATION_IDENTIFIERS if n != "UTC")):
            report = d3.run_all(SWETEST, EPHE, RECEIPT, env=self.env)
        self.assertEqual(report["verdicts"]["d3"], "SWISS-CONFORMANCE FAIL")
        self.assertEqual(report["verdicts"]["v1_divergence"], "SWISS-CONFORMANCE FAIL")
        self.assertEqual(report["exit_code"], 1)

    def test_rejecting_a_geographic_zone_fails(self):
        real = zone_policy.is_location_based
        with mock.patch.object(zone_policy, "is_location_based", lambda name: real(name) and name != "Asia/Kolkata"):
            result = d3.run_d3_case(CASES["SC-02"], SWETEST, EPHE, SPEC)
        self.assertEqual(result["outcome"], c.FAIL)


if __name__ == "__main__":
    unittest.main()
