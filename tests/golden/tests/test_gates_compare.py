"""Fixture gates (approvals, tolerances, sources, coverage, tzdata, time track) and pure comparison."""
from pathlib import Path
import copy
import hashlib
import shutil
import subprocess
import tempfile
import unittest

from ..harness import compare, gates
from ..harness.environment import environment_reasons, git_state, tzdata_in_use
from ..harness.outcomes import Outcome
from .helpers import DUMMY_DIR, GOLDEN_DIR, clean_env, dummy_fixture, load_json, mock_output, world_fixture

UTC = "2001-02-03T04:05:06Z"
TOL = {"planet_longitude": 0.5, "node_longitude": 0.5, "lagna_longitude": 0.5, "utc": 0.0}


class DecisionAndToleranceGates(unittest.TestCase):
    def test_committed_decisions_match_the_register(self):
        # main:docs/DECISIONS.md at 0023fdc: only SCI-01b and SCI-01c approved.
        decisions = load_json(GOLDEN_DIR / "config" / "decision-status.json")["decisions"]
        approved = sorted(d for d, e in decisions.items() if e["status"] == "APPROVED")
        self.assertEqual(approved, ["SCI-01b", "SCI-01c"])
        for d in approved:
            self.assertEqual(decisions[d]["decisions_md_commit"], "0023fdc66f9061daffe60fe54bb92ea935e75b87")
        pending = sorted(set(decisions) - set(approved))
        self.assertEqual({decisions[d]["status"] for d in pending}, {"PENDING"})
        reasons = gates.decision_reasons(sorted(decisions), decisions)
        self.assertEqual(reasons, [f"SCI_DECISION_PENDING: {d}" for d in pending])

    def test_approval_needs_a_complete_record(self):
        record = {"status": "APPROVED", "approver": "x", "approved_on": "2026-01-01", "decisions_md_commit": "abc"}
        self.assertEqual(gates.decision_reasons(["SCI-01a"], {"SCI-01a": record}), [])
        incomplete = {**record, "decisions_md_commit": None}
        self.assertEqual(gates.decision_reasons(["SCI-01a"], {"SCI-01a": incomplete}),
                         ["DECISION_RECORD_INCOMPLETE: SCI-01a"])
        self.assertEqual(gates.decision_reasons(["SCI-99"], {}), ["DECISION_UNKNOWN: SCI-99"])

    def test_committed_tolerances_are_all_not_frozen(self):
        rows = load_json(GOLDEN_DIR / "config" / "tolerances.json")["tolerances"]
        self.assertEqual({r["status"] for r in rows.values()}, {"NOT_FROZEN"})
        self.assertEqual({r["frozen_arcsec"] for r in rows.values()}, {None})
        reasons = gates.tolerance_reasons({"planet_longitude": "T-SID", "utc": "T-UTC"}, rows)
        self.assertEqual(reasons, ["TOLERANCE_NOT_FROZEN: T-SID", "TOLERANCE_NOT_FROZEN: T-UTC"])

    def test_frozen_tolerance_needs_value_and_qa_ref(self):
        ok = {"status": "FROZEN", "frozen_arcsec": 0.5, "qa_ref": "QA"}
        self.assertEqual(gates.tolerance_reasons({"q": "T"}, {"T": ok}), [])
        for bad in ({**ok, "qa_ref": None}, {**ok, "frozen_arcsec": None}, {**ok, "frozen_arcsec": -1},
                    {**ok, "frozen_arcsec": True}):
            self.assertEqual(gates.tolerance_reasons({"q": "T"}, {"T": bad}), ["TOLERANCE_RECORD_INCOMPLETE: T"])
        self.assertEqual(gates.tolerance_reasons({"q": "X"}, {}), ["TOLERANCE_UNKNOWN: X"])

    def test_committed_registry_has_nothing_obtained(self):
        refs = load_json(GOLDEN_DIR / "config" / "reference-registry.json")["references"]
        self.assertFalse([r for r in refs.values() if r["obtained"]])


class SourceIntegrity(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        (self.tmp / "raw").mkdir()
        self.raw = self.tmp / "raw" / "r.txt"
        self.raw.write_bytes(b"bytes\n")
        self.sha = hashlib.sha256(b"bytes\n").hexdigest()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def ref(self, path="raw/r.txt", sha=None):
        return {"source_id": "S", "raw_output_path": path, "raw_output_sha256": sha or self.sha}

    def test_matching_bytes(self):
        self.assertEqual(gates.source_reasons([self.ref()], self.tmp), [])

    def test_missing_mismatched_and_escaping_paths(self):
        self.assertEqual(gates.source_reasons([self.ref("raw/none.txt")], self.tmp), ["SOURCE_BYTES_MISSING: S"])
        self.assertEqual(gates.source_reasons([self.ref(sha="0" * 64)], self.tmp), ["SOURCE_HASH_MISMATCH: S"])
        for path in ("../r.txt", "/etc/hostname", "raw/../../x"):
            self.assertEqual(gates.source_reasons([self.ref(path)], self.tmp), ["SOURCE_PATH_INVALID: S"])

    def test_dummy_fixtures_block_even_with_matching_bytes(self):
        configs = {"references": load_json(GOLDEN_DIR / "config" / "reference-registry.json")["references"],
                   "decisions": {}, "tolerances": {}}
        reasons = gates.fixture_reasons(dummy_fixture(), DUMMY_DIR, configs, "2026e")
        self.assertIn("DUMMY_FIXTURE: synthetic demonstration data, never a reference", reasons)
        self.assertIn("REFERENCE_UNVERIFIED", reasons)
        self.assertIn("REFERENCE_UNKNOWN: FAKE-SOURCE-DO-NOT-USE-01", reasons)
        self.assertFalse([r for r in reasons if r.startswith("SOURCE_")])
        self.assertNotIn("TZDATA_MISMATCH", reasons)

    def test_tzdata_mismatch(self):
        configs = {"references": {}, "decisions": {}, "tolerances": {}}
        self.assertIn("TZDATA_MISMATCH", gates.fixture_reasons(dummy_fixture(), DUMMY_DIR, configs, "2025a"))
        self.assertIn("TZDATA_MISMATCH", gates.fixture_reasons(dummy_fixture(), DUMMY_DIR, configs, None))


class CoverageAndTime(unittest.TestCase):
    def test_coverage(self):
        fixture = dummy_fixture()
        self.assertEqual(gates.coverage_reasons(fixture), [])
        self.assertEqual(gates.coverage_reasons(dummy_fixture("DUMMY-04.json")),
                         ["OUTSIDE_REFERENCE_COVERAGE: FAKE-SOURCE-DO-NOT-USE-04"])
        bad = copy.deepcopy(fixture)
        bad["references"][0]["coverage_utc"] = ["1900-01-01T00:00:00+05:30", "2000-01-01T00:00:00Z"]
        self.assertEqual(gates.coverage_reasons(bad), ["COVERAGE_INVALID: FAKE-SOURCE-DO-NOT-USE-01"])
        bad["derived_time"]["utc"] = "yesterday"
        self.assertEqual(gates.coverage_reasons(bad), ["DERIVED_UTC_INVALID"])

    def test_time_track(self):
        committed = load_json(GOLDEN_DIR / "config" / "time-track.json")
        self.assertEqual(gates.time_track_reasons(committed), ["TIME_TRACK_NOT_VERIFIED"])
        verified = {"status": "VERIFIED", "qa_ref": "QA", "observed_delta_t_through_utc": None}
        self.assertEqual(gates.time_track_reasons(verified), ["TIME_TRACK_INCOMPLETE: observed_delta_t_through_utc"])
        verified["observed_delta_t_through_utc"] = "2026-01-01T00:00:00Z"
        self.assertEqual(gates.time_track_reasons(verified), [])

    def test_future_epoch_is_qualified(self):
        self.assertIsNone(gates.time_qualification("2020-01-01T00:00:00Z", "2026-01-01T00:00:00Z"))
        self.assertTrue(gates.time_qualification("2099-06-15T12:00:00Z", "2026-01-01T00:00:00Z")
                        .startswith("FUTURE_DELTA_T"))


class Environment(unittest.TestCase):
    def test_reasons(self):
        self.assertEqual(environment_reasons(clean_env()), [])
        self.assertEqual(environment_reasons(clean_env(git={"commit": "a" * 40, "dirty": True})), ["DIRTY_TREE"])
        self.assertEqual(environment_reasons(clean_env(git={"commit": None, "dirty": None})), ["GIT_UNAVAILABLE"])
        missing = clean_env(ephemeris={"verified": False, "error_code": "EPHEMERIS_FILE_MISSING", "files": {}})
        self.assertEqual(environment_reasons(missing), ["EPHEMERIS_UNVERIFIED: EPHEMERIS_FILE_MISSING"])
        self.assertEqual(environment_reasons(clean_env(tzdata={"source": None, "version": None})), ["TZDATA_UNKNOWN"])
        self.assertEqual(environment_reasons(clean_env(swiss={"pyswisseph": None, "swiss_library": None})),
                         ["SWISS_VERSION_UNKNOWN"])

    def test_tzdata_in_use_reports_a_version(self):
        self.assertTrue(tzdata_in_use()["version"])

    def test_dirty_tree_detection_in_a_temporary_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            run = lambda *a: subprocess.run(["git", "-C", tmp, *a], check=True, capture_output=True)
            run("init", "-q")
            (repo / "a.txt").write_text("a", encoding="utf-8")
            run("add", "a.txt")
            run("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-qm", "t")
            self.assertEqual(git_state(repo)["dirty"], False)
            (repo / "a.txt").write_text("b", encoding="utf-8")
            self.assertEqual(git_state(repo)["dirty"], True)
            (repo / "a.txt").write_text("a", encoding="utf-8")
            (repo / "new.txt").write_text("n", encoding="utf-8")
            self.assertEqual(git_state(repo)["dirty"], True)
        self.assertEqual(git_state(Path(tmp)), {"commit": None, "dirty": None})


class Compare(unittest.TestCase):
    def setUp(self):
        self.fixture = world_fixture()
        self.expected = self.fixture["expected"]["sidereal_longitude_deg"]

    def outcomes(self, checks):
        return {(c["quantity"], c["body"]): c["outcome"] for c in checks}

    def test_all_within_tolerance_pass(self):
        out = mock_output(self.expected, UTC, {"sun": 0.4, "moon": -0.4})
        checks = compare.compare_fixture(self.fixture, out, TOL)
        self.assertEqual(set(self.outcomes(checks).values()), {"PASS"})
        self.assertEqual(len(checks), 5)  # utc + sun, moon, rahu_mean, lagna

    def test_outside_tolerance_fails(self):
        out = mock_output(self.expected, UTC, {"moon": 0.6})
        checks = compare.compare_fixture(self.fixture, out, TOL)
        moon = next(c for c in checks if c["body"] == "moon")
        self.assertEqual(moon["outcome"], "FAIL")
        self.assertAlmostEqual(moon["diff_arcsec"], 0.6, places=6)

    def test_category_difference_fails(self):
        out = mock_output(self.expected, UTC)
        out["planets"]["sun"]["rashi"] = "Meena"
        out["moon_nakshatra"]["pada"] = 4 if out["moon_nakshatra"]["pada"] != 4 else 1
        checks = compare.compare_fixture(self.fixture, out, TOL)
        sun = next(c for c in checks if c["body"] == "sun")
        moon = next(c for c in checks if c["body"] == "moon")
        self.assertEqual((sun["outcome"], sun["category_mismatches"]), ("FAIL", ["rashi"]))
        self.assertEqual((moon["outcome"], moon["category_mismatches"]), ("FAIL", ["moon_nakshatra"]))

    def test_wrap_and_boundary_indeterminate(self):
        expected = {"sun": 0.0001, "lagna": 5.5}
        fixture = world_fixture(**expected)
        out = mock_output(expected, UTC, {"sun": -0.72})  # engine 359.9999
        sun = next(c for c in compare.compare_fixture(fixture, out, TOL) if c["body"] == "sun")
        self.assertAlmostEqual(sun["engine_deg"], 359.9999, places=9)
        self.assertAlmostEqual(sun["diff_arcsec"], -0.72, places=6)
        self.assertAlmostEqual(sun["boundary_distance_arcsec"], 0.36, places=6)
        self.assertEqual(sun["outcome"], "BOUNDARY-INDETERMINATE")
        # The same wrap far from a boundary judgement: a wide-enough tolerance still cannot pass near an edge.
        sun = next(c for c in compare.compare_fixture(fixture, out, {**TOL, "planet_longitude": 1.0})
                   if c["body"] == "sun")
        self.assertEqual(sun["outcome"], "BOUNDARY-INDETERMINATE")

    def test_house_boundary_follows_lagna(self):
        expected = {"sun": 100.5, "lagna": 29.99999}
        fixture = world_fixture(**expected)
        sun = next(c for c in compare.compare_fixture(fixture, mock_output(expected, UTC), TOL) if c["body"] == "sun")
        self.assertEqual(sun["outcome"], "BOUNDARY-INDETERMINATE")

    def test_qualified(self):
        checks = compare.compare_fixture(self.fixture, mock_output(self.expected, UTC), TOL, "FUTURE_DELTA_T: x")
        longitudes = [c for c in checks if c["quantity"] != "utc"]
        self.assertEqual({c["outcome"] for c in longitudes}, {"QUALIFIED"})

    def test_missing_tolerance_blocks(self):
        checks = compare.compare_fixture(self.fixture, mock_output(self.expected, UTC), {"utc": 0.0})
        self.assertEqual({c["outcome"] for c in checks if c["quantity"] != "utc"}, {"BLOCKED"})

    def test_time_conversion(self):
        out = mock_output(self.expected, "2001-02-03T04:05:07Z")
        self.assertEqual(compare.compare_fixture(self.fixture, out, TOL)[0]["outcome"], "FAIL")
        fixture = copy.deepcopy(self.fixture)
        fixture["expected"]["time_conversion"] = {"utc": None, "error_code": "NONEXISTENT_LOCAL_TIME"}
        self.assertEqual(compare.compare_fixture(fixture, out, TOL)[0]["outcome"], "BLOCKED")
        fixture["expected"]["time_conversion"] = {"utc": None, "error_code": None}
        self.assertNotEqual(compare.compare_fixture(fixture, out, TOL)[0]["quantity"], "utc")

    def test_ketu_identity_is_self_consistency(self):
        out = mock_output(self.expected, UTC)
        self.assertEqual(compare.ketu_identity("GC-99", out)["result"], "SELF-CONSISTENCY PASS")
        out["planets"]["ketu_mean"]["longitude_deg"] += 0.001
        self.assertEqual(compare.ketu_identity("GC-99", out)["result"], "SELF-CONSISTENCY FAIL")
        self.assertNotIn(compare.ketu_identity("GC-99", out)["result"], {o.value for o in Outcome})


if __name__ == "__main__":
    unittest.main()
