"""End-to-end harness runs: the committed dummy demo, temporary approved worlds, reports and privacy."""
from pathlib import Path
import getpass
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest

from ..harness.report import to_json, to_markdown, write_reports
from ..harness.run import DEMO_BANNER, run_golden
from .helpers import (DUMMY_DIR, GOLDEN_DIR, REPO_ROOT, build_world, clean_env, dummy_fixture, fixed_clock,
                      load_json, mock_output, world_fixture, write_json)

UTC = "2001-02-03T04:05:06Z"


def refuse_engine(request, ephe_path):
    raise AssertionError("engine must not be called while any gate blocks")


class DummyDemo(unittest.TestCase):
    def test_committed_dummy_set_is_blocked_with_exit_2(self):
        data = run_golden(DUMMY_DIR, None, engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock)
        self.assertEqual((data["verdict"], data["exit_code"]), ("BLOCKED", 2))
        self.assertEqual(data["banner"], DEMO_BANNER)
        self.assertEqual(data["checks"], [])
        self.assertEqual(data["self_consistency"], [])
        self.assertIn("METHOD_MANIFEST_UNREVIEWED", data["run_reasons"])
        self.assertIn("TIME_TRACK_NOT_VERIFIED", data["run_reasons"])
        by_id = {f["fixture_id"]: f for f in data["fixtures"]}
        self.assertEqual(sorted(by_id), ["DUMMY-01", "DUMMY-02", "DUMMY-03", "DUMMY-04"])
        for fx in by_id.values():
            self.assertEqual((fx["outcome"], fx["engine_called"]), ("BLOCKED", False))
            self.assertIn("DUMMY_FIXTURE: synthetic demonstration data, never a reference", fx["reasons"])
            self.assertIn("SCI_DECISION_PENDING: SCI-01a", fx["reasons"])
            self.assertIn("TOLERANCE_NOT_FROZEN: T-SID", fx["reasons"])
        self.assertIn("SOURCE_HASH_MISMATCH: FAKE-SOURCE-DO-NOT-USE-02", by_id["DUMMY-02"]["reasons"])
        self.assertIn("TZDATA_MISMATCH", by_id["DUMMY-02"]["reasons"])
        self.assertIn("SOURCE_BYTES_MISSING: FAKE-SOURCE-DO-NOT-USE-03", by_id["DUMMY-03"]["reasons"])
        self.assertEqual(by_id["DUMMY-03"]["method_mismatches"], ["node"])
        self.assertIn("OUTSIDE_REFERENCE_COVERAGE: FAKE-SOURCE-DO-NOT-USE-04", by_id["DUMMY-04"]["reasons"])

    def test_demo_with_dirty_tree_missing_ephemeris_and_wrong_tzdata(self):
        env = clean_env(git={"commit": "a" * 40, "dirty": True}, tzdata={"source": "system", "version": "2024a"},
                        ephemeris={"manifest_version": "1.0.0", "source_commit": "c" * 40, "verified": False,
                                   "error_code": "EPHEMERIS_PATH_MISSING", "files": {}})
        data = run_golden(DUMMY_DIR, None, engine_fn=refuse_engine, env=env, clock=fixed_clock)
        self.assertEqual(data["exit_code"], 2)
        self.assertIn("DIRTY_TREE", data["run_reasons"])
        self.assertIn("EPHEMERIS_UNVERIFIED: EPHEMERIS_PATH_MISSING", data["run_reasons"])
        self.assertTrue(all("TZDATA_MISMATCH" in f["reasons"] for f in data["fixtures"]))


class ApprovedWorld(unittest.TestCase):
    """Temporary worlds where every gate passes with TEST-ONLY records (nothing committed)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_world(self, fixtures, engine_fn, env=None, **world):
        golden, fixtures_dir = build_world(self.tmp, fixtures, **world)
        return run_golden(fixtures_dir, None, golden_dir=golden, repo_root=REPO_ROOT,
                          engine_fn=engine_fn, env=env or clean_env(), clock=fixed_clock)

    def mocked(self, fixtures, offsets=None, method=None):
        """Engine mock keyed by fixture latitude, which the world fixtures set uniquely."""
        table = {f["input"]["latitude"]: f for f in fixtures}

        def fn(request, ephe_path):
            fixture = table[request["latitude"]]
            return mock_output(fixture["expected"]["sidereal_longitude_deg"], UTC,
                               (offsets or {}).get(fixture["fixture_id"]), method)
        return fn

    def fixtures_(self, *ids):
        fixtures = []
        for i, fid in enumerate(ids):
            fixture = world_fixture(fid)
            fixture["input"]["latitude"] = 10.0 + i
            fixtures.append(fixture)
        return fixtures

    def test_all_gates_satisfied_and_within_tolerance_is_pass_exit_0(self):
        fixtures = self.fixtures_("GC-98", "GC-99")
        data = self.run_world(fixtures, self.mocked(fixtures))
        self.assertEqual((data["verdict"], data["exit_code"]), ("PASS", 0), data["run_reasons"])
        self.assertIsNone(data["banner"])
        self.assertEqual(len(data["self_consistency"]), 2)

    def test_one_fail_makes_fail_exit_1_even_with_other_outcomes(self):
        fixtures = self.fixtures_("GC-97", "GC-98", "GC-99")
        fixtures[2]["method_signature"]["houses"] = "Placidus"  # METHOD-MISMATCH
        data = self.run_world(fixtures, self.mocked(fixtures, {"GC-97": {"moon": 5.0}}))
        outcomes = {f["fixture_id"]: f["outcome"] for f in data["fixtures"]}
        self.assertEqual(outcomes, {"GC-97": "FAIL", "GC-98": "PASS", "GC-99": "METHOD-MISMATCH"})
        self.assertEqual((data["verdict"], data["exit_code"]), ("FAIL", 1))

    def test_method_mismatch_alone_is_blocked_and_engine_not_called(self):
        fixtures = self.fixtures_("GC-99")
        fixtures[0]["method_signature"]["node"] = "true node"
        data = self.run_world(fixtures, refuse_engine)
        self.assertEqual((data["fixtures"][0]["outcome"], data["exit_code"]), ("METHOD-MISMATCH", 2))

    def test_emitted_method_block_contradiction(self):
        fixtures = self.fixtures_("GC-99")
        data = self.run_world(fixtures, self.mocked(fixtures, method={"ayanamsa": "Raman", "nodes": "mean",
                                                                      "houses": "whole_sign"}))
        self.assertEqual(data["fixtures"][0]["outcome"], "METHOD-MISMATCH")
        self.assertEqual(data["fixtures"][0]["method_mismatches"], ["emitted method block: ayanamsa"])
        self.assertEqual(data["verdict"], "BLOCKED")

    def test_future_epoch_is_qualified_exit_2(self):
        fixtures = self.fixtures_("GC-99")
        data = self.run_world(fixtures, self.mocked(fixtures), time_observed_through="2000-01-01T00:00:00Z")
        self.assertEqual(data["fixtures"][0]["outcome"], "QUALIFIED")
        self.assertEqual((data["verdict"], data["exit_code"]), ("QUALIFIED", 2))

    def test_boundary_indeterminate_blocks(self):
        fixture = world_fixture("GC-99", sun=59.99999, lagna=5.5)
        data = self.run_world([fixture], self.mocked([fixture]))
        self.assertEqual(data["fixtures"][0]["outcome"], "BOUNDARY-INDETERMINATE")
        self.assertEqual(data["verdict"], "BLOCKED")

    def test_engine_error_is_blocked_with_code_only(self):
        class Boom(RuntimeError):
            code = "ASCENDANT_UNCOMPUTABLE"

        def fn(request, ephe_path):
            raise Boom("detail that must not be logged")
        data = self.run_world(self.fixtures_("GC-99"), fn)
        self.assertEqual(data["fixtures"][0]["reasons"], ["ENGINE_ERROR: ASCENDANT_UNCOMPUTABLE"])
        self.assertNotIn("must not be logged", to_json(data))

    def test_malformed_engine_output_is_blocked(self):
        method = {"ayanamsa": "Lahiri", "nodes": "mean", "houses": "whole_sign"}
        data = self.run_world(self.fixtures_("GC-99"), lambda request, ephe_path: {"method": method})
        self.assertEqual(data["fixtures"][0]["reasons"], ["ENGINE_OUTPUT_MALFORMED"])
        self.assertEqual(data["verdict"], "BLOCKED")

    def test_each_gate_alone_blocks_before_the_engine(self):
        def stale(golden):
            manifest = load_json(golden / "method-manifest.json")
            manifest["files"]["src/sabpuja_kundali/engine.py"] = "f" * 40
            write_json(golden / "method-manifest.json", manifest)

        def unreviewed(golden):
            manifest = load_json(golden / "method-manifest.json")
            manifest.update(status="UNREVIEWED", qa_review=None)
            write_json(golden / "method-manifest.json", manifest)

        def pending(golden):
            data = load_json(golden / "config" / "decision-status.json")
            data["decisions"]["SCI-01b"]["status"] = "PENDING"
            write_json(golden / "config" / "decision-status.json", data)

        def unfrozen(golden):
            data = load_json(golden / "config" / "tolerances.json")
            data["tolerances"]["T-SID"]["status"] = "NOT_FROZEN"
            write_json(golden / "config" / "tolerances.json", data)

        def not_obtained(golden):
            data = load_json(golden / "config" / "reference-registry.json")
            data["references"]["TEST-REF"]["obtained"] = False
            write_json(golden / "config" / "reference-registry.json", data)

        def class_d(golden):
            data = load_json(golden / "config" / "reference-registry.json")
            data["references"]["TEST-REF"]["class"] = "D"
            write_json(golden / "config" / "reference-registry.json", data)

        def leaky_generator(golden):
            (golden / "generator" / "leak.py").write_text("from sabpuja_kundali import engine\n", encoding="utf-8")

        def time_track(golden):
            write_json(golden / "config" / "time-track.json", {"status": "BLOCKED"})

        def broken_config(golden):
            (golden / "config" / "tolerances.json").write_text("{", encoding="utf-8")

        def no_manifest(golden):
            (golden / "method-manifest.json").unlink()

        cases = {
            stale: "METHOD_MANIFEST_STALE: src/sabpuja_kundali/engine.py changed since inspection; re-inspect",
            unreviewed: "METHOD_MANIFEST_UNREVIEWED",
            pending: "SCI_DECISION_PENDING: SCI-01b",
            unfrozen: "TOLERANCE_NOT_FROZEN: T-SID",
            not_obtained: "REFERENCE_NOT_OBTAINED: TEST-REF",
            class_d: "REFERENCE_CLASS_MISMATCH: TEST-REF fixture says I-code, registry says D",
            leaky_generator: "GENERATOR_NOT_ISOLATED: leak.py:1: imports from sabpuja_kundali",
            time_track: "TIME_TRACK_NOT_VERIFIED",
            broken_config: "CONFIG_INVALID: tolerances.json",
            no_manifest: "METHOD_MANIFEST_MISSING",
        }
        for mutate, reason in cases.items():
            with self.subTest(gate=mutate.__name__):
                tmp = self.tmp / mutate.__name__
                golden, fixtures_dir = build_world(tmp, self.fixtures_("GC-99"))
                mutate(golden)
                data = run_golden(fixtures_dir, None, golden_dir=golden, repo_root=REPO_ROOT,
                                  engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock)
                reasons = data["run_reasons"] + data["fixtures"][0]["reasons"]
                self.assertIn(reason, reasons)
                self.assertEqual((data["verdict"], data["exit_code"]), ("BLOCKED", 2))
                self.assertFalse(data["fixtures"][0]["engine_called"])

    def run_blocked(self, fixtures, name, **world):
        """Run a world with the engine refused; return the report data."""
        golden, fixtures_dir = build_world(self.tmp / name, fixtures, **world)
        return golden, fixtures_dir, run_golden(fixtures_dir, None, golden_dir=golden, repo_root=REPO_ROOT,
                                                engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock)

    def assert_blocked_before_engine(self, data, reason):
        reasons = data["run_reasons"] + [r for f in data["fixtures"] for r in f["reasons"]]
        self.assertIn(reason, reasons)
        self.assertEqual((data["verdict"], data["exit_code"]), ("BLOCKED", 2))
        self.assertFalse(any(f["engine_called"] for f in data["fixtures"]))

    def test_invalid_frozen_tolerances_block_before_the_engine(self):
        # WP1-01. NaN/Infinity reach the config file as JSON constants and are rejected at parse.
        for value, reason in ((float("nan"), "CONFIG_INVALID: tolerances.json"),
                              (float("inf"), "CONFIG_INVALID: tolerances.json"),
                              (-float("inf"), "CONFIG_INVALID: tolerances.json"),
                              (-1.0, "TOLERANCE_RECORD_INCOMPLETE: T-SID"),
                              (True, "TOLERANCE_RECORD_INCOMPLETE: T-SID"),
                              (10 ** 400, "TOLERANCE_RECORD_INCOMPLETE: T-SID")):
            with self.subTest(value=value):
                _, _, data = self.run_blocked(self.fixtures_("GC-99"), f"tol-{value!r}"[:20], frozen_arcsec=value)
                self.assert_blocked_before_engine(data, reason)
        golden, fixtures_dir = build_world(self.tmp / "tol-1e400", self.fixtures_("GC-99"))
        path = golden / "config" / "tolerances.json"
        path.write_text(path.read_text(encoding="utf-8").replace("0.5", "1e400"), encoding="utf-8")
        data = run_golden(fixtures_dir, None, golden_dir=golden, repo_root=REPO_ROOT,
                          engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock)
        self.assert_blocked_before_engine(data, "CONFIG_INVALID: tolerances.json")

    def test_zero_tolerance_is_accepted(self):
        fixtures = self.fixtures_("GC-99")
        data = self.run_world(fixtures, self.mocked(fixtures), frozen_arcsec=0)
        self.assertEqual(data["verdict"], "PASS")

    def test_accuracy_claim_false_blocks_before_the_engine(self):
        # WP1-03: a non-dummy, verified-looking fixture that does not claim accuracy can never PASS.
        fixtures = self.fixtures_("GC-99")
        fixtures[0]["accuracy_claim"] = False
        _, _, data = self.run_blocked(fixtures, "claim")
        self.assert_blocked_before_engine(
            data, "ACCURACY_CLAIM_ABSENT: fixture does not claim to be an accuracy reference")

    def test_fixture_and_registry_class_must_agree(self):
        # WP1-04, both directions, then both D.
        fixtures = self.fixtures_("GC-99")
        fixtures[0]["references"][0]["source_class"] = "D"
        _, _, data = self.run_blocked(fixtures, "class-fixture-d")
        self.assert_blocked_before_engine(data, "REFERENCE_CLASS_MISMATCH: TEST-REF fixture says D, registry says I-code")
        golden, fixtures_dir, _ = self.run_blocked(self.fixtures_("GC-99"), "class-registry-d")
        registry = load_json(golden / "config" / "reference-registry.json")
        registry["references"]["TEST-REF"]["class"] = "M"
        write_json(golden / "config" / "reference-registry.json", registry)
        data = run_golden(fixtures_dir, None, golden_dir=golden, repo_root=REPO_ROOT,
                          engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock)
        self.assert_blocked_before_engine(data, "REFERENCE_CLASS_MISMATCH: TEST-REF fixture says I-code, registry says M")
        fixtures = self.fixtures_("GC-99")
        fixtures[0]["references"][0]["source_class"] = "D"
        golden, fixtures_dir = build_world(self.tmp / "class-both-d", fixtures)
        registry = load_json(golden / "config" / "reference-registry.json")
        registry["references"]["TEST-REF"]["class"] = "D"
        write_json(golden / "config" / "reference-registry.json", registry)
        data = run_golden(fixtures_dir, None, golden_dir=golden, repo_root=REPO_ROOT,
                          engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock)
        self.assert_blocked_before_engine(data, "REFERENCE_CLASS_NOT_INDEPENDENT: TEST-REF is class D")

    def test_index_traversal_blocks_before_the_engine(self):
        # WP1-02 end to end: one escaping entry blocks its record and never reads the target.
        golden, fixtures_dir = build_world(self.tmp / "traversal", self.fixtures_("GC-99"))
        (self.tmp / "traversal" / "GC-98.json").write_text("{}", encoding="utf-8")
        index = load_json(fixtures_dir / "INDEX.json")
        index["fixtures"]["../GC-98.json"] = {"revision": 1, "sha256": "0" * 64}
        write_json(fixtures_dir / "INDEX.json", index)
        data = run_golden(fixtures_dir, None, golden_dir=golden, repo_root=REPO_ROOT,
                          engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock)
        bad = [f for f in data["fixtures"] if f["file"].startswith("INDEX entry")]
        self.assertEqual(bad[0]["reasons"], ["FIXTURE_PATH_INVALID: not a fixture file name"])
        self.assertEqual(bad[0]["outcome"], "BLOCKED")
        self.assertNotIn("../GC-98.json", to_json(data))
        self.assertEqual((data["verdict"], data["exit_code"]), ("BLOCKED", 2))

    def test_malformed_fixture_numbers_block_before_the_engine(self):
        fixtures = self.fixtures_("GC-99")
        fixtures[0]["input"]["latitude"] = 10 ** 400
        _, _, data = self.run_blocked(fixtures, "huge")
        self.assert_blocked_before_engine(data, "SCHEMA_INVALID: input: latitude and longitude must be finite numbers")

    def test_fake_or_unknown_reference_blocks(self):
        fixture = world_fixture("GC-99")
        fixture["references"][0]["source_id"] = "FAKE-SOURCE-DO-NOT-USE-09"
        fixture["references"][0]["raw_output_sha256"] = "0" * 64
        data = self.run_world([fixture], refuse_engine)
        reasons = data["fixtures"][0]["reasons"]
        self.assertIn("REFERENCE_UNKNOWN: FAKE-SOURCE-DO-NOT-USE-09", reasons)
        self.assertIn("SOURCE_HASH_MISMATCH: FAKE-SOURCE-DO-NOT-USE-09", reasons)

    def test_no_fixtures_is_blocked(self):
        golden, fixtures_dir = build_world(self.tmp, [])
        data = run_golden(fixtures_dir, None, golden_dir=golden, repo_root=REPO_ROOT,
                          engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock)
        self.assertEqual(data["run_reasons"], ["NO_FIXTURES"])
        self.assertEqual((data["verdict"], data["exit_code"]), ("BLOCKED", 2))


class Reports(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_reports_are_deterministic(self):
        first = run_golden(DUMMY_DIR, None, engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock)
        second = run_golden(DUMMY_DIR, None, engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock)
        self.assertEqual(to_json(first), to_json(second))
        self.assertEqual(to_markdown(first), to_markdown(second))
        a = write_reports(first, self.tmp / "a")
        b = write_reports(second, self.tmp / "b")
        self.assertEqual([p.name for p in a], ["golden-report-000000000000-20260102T030405Z.json",
                                               "golden-report-000000000000-20260102T030405Z.md"])
        self.assertEqual([p.read_bytes() for p in a], [p.read_bytes() for p in b])
        self.assertEqual(json.loads(a[0].read_text(encoding="utf-8")), first)

    def test_markdown_carries_banner_verdict_and_not_validation_statement(self):
        md = to_markdown(run_golden(DUMMY_DIR, None, engine_fn=refuse_engine, env=clean_env(), clock=fixed_clock))
        self.assertTrue(md.startswith(f"# {DEMO_BANNER}\n"))
        self.assertIn("Verdict: **BLOCKED** (exit code 2)", md)
        self.assertIn("This run is not astronomical validation.", md)

    def test_no_privacy_leaks_in_reports_with_real_environment_capture(self):
        ephe = os.environ.get("SABPUJA_TEST_EPHE_PATH") or str(self.tmp / "no-ephe-here")
        data = run_golden(DUMMY_DIR, ephe, engine_fn=refuse_engine, clock=fixed_clock)
        json_path, md_path = write_reports(data, self.tmp / "reports")
        fixture = dummy_fixture()
        forbidden = {fixture["input"]["birth_datetime"], str(fixture["input"]["latitude"]),
                     str(fixture["input"]["longitude"]), ephe, str(self.tmp), str(REPO_ROOT),
                     str(Path.home()), socket.gethostname(), getpass.getuser()}
        forbidden = {f for f in forbidden if f and len(f) > 3}
        for path in (json_path, md_path):
            text = path.read_text(encoding="utf-8")
            for needle in forbidden:
                with self.subTest(report=path.suffix, needle=needle):
                    self.assertNotIn(needle, text)

    def test_cli_demo_ends_blocked_exit_2(self):
        env = {k: v for k, v in os.environ.items() if k not in ("PYTHONPATH", "SE_EPHE_PATH")}
        ephe = os.environ.get("SABPUJA_TEST_EPHE_PATH", "")
        result = subprocess.run([sys.executable, "-m", "tests.golden.harness.run", "--ephe", ephe,
                                 "--report-dir", str(self.tmp / "r")], cwd=REPO_ROOT, env=env,
                                capture_output=True, text=True, timeout=120)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertTrue(result.stdout.startswith(f"# {DEMO_BANNER}"))
        self.assertIn("Verdict: **BLOCKED** (exit code 2)", result.stdout)
        self.assertEqual(len(list((self.tmp / "r").glob("golden-report-*"))), 2)


if __name__ == "__main__":
    unittest.main()
