"""Method manifest pinning and the reference-generator independence guard."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from ..generator.isolation import check_reference_classes, scan_directory, scan_source
from ..harness.manifest import (REQUIRED_FILES, check_manifest, emitted_block_contradictions, git_blob_sha1,
                                load_manifest, signature_mismatches)
from .helpers import GOLDEN_DIR, REPO_ROOT, dummy_fixture, load_json, write_json

MANIFEST = GOLDEN_DIR / "method-manifest.json"
TESTS_DIR = GOLDEN_DIR.parent


class MethodManifest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.repo = self.tmp / "repo"
        for rel in REQUIRED_FILES:
            (self.repo / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / rel, self.repo / rel)
        self.manifest_path = self.tmp / "method-manifest.json"
        shutil.copyfile(MANIFEST, self.manifest_path)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_blob_sha_matches_git(self):
        for rel in REQUIRED_FILES:
            expected = subprocess.run(["git", "-C", str(REPO_ROOT), "hash-object", rel], check=True,
                                      capture_output=True, text=True).stdout.strip()
            self.assertEqual(git_blob_sha1((REPO_ROOT / rel).read_bytes()), expected)

    def test_committed_manifest_pins_current_engine_and_is_unreviewed(self):
        manifest, reasons = check_manifest(MANIFEST, REPO_ROOT)
        self.assertEqual(manifest["inspected_commit"], "d8193c692d52aa12595f81c227638a061605a3d9")
        self.assertEqual(reasons, ["METHOD_MANIFEST_UNREVIEWED"])

    def test_changed_code_blob_is_stale(self):
        engine = self.repo / "src/sabpuja_kundali/engine.py"
        engine.write_bytes(engine.read_bytes() + b"\n# changed\n")
        _, reasons = check_manifest(self.manifest_path, self.repo)
        self.assertIn("METHOD_MANIFEST_STALE: src/sabpuja_kundali/engine.py changed since inspection; re-inspect",
                      reasons)

    def test_missing_source_and_missing_manifest(self):
        (self.repo / "src/sabpuja_kundali/rules.py").unlink()
        _, reasons = check_manifest(self.manifest_path, self.repo)
        self.assertIn("METHOD_MANIFEST_SOURCE_MISSING: src/sabpuja_kundali/rules.py", reasons)
        self.assertEqual(check_manifest(self.tmp / "absent.json", self.repo), (None, ["METHOD_MANIFEST_MISSING"]))

    def test_reviewed_and_current_has_no_reasons(self):
        data = load_json(self.manifest_path)
        data.update(status="REVIEWED", qa_review="TEST-ONLY")
        write_json(self.manifest_path, data)
        self.assertEqual(check_manifest(self.manifest_path, self.repo)[1], [])

    def test_malformed_manifest(self):
        data = load_json(self.manifest_path)
        del data["files"]["src/sabpuja_kundali/rules.py"]
        write_json(self.manifest_path, data)
        manifest, errors = load_manifest(self.manifest_path)
        self.assertIsNone(manifest)
        self.assertTrue(errors[0].startswith("METHOD_MANIFEST_INVALID"))
        self.manifest_path.write_text("{", encoding="utf-8")
        self.assertEqual(load_manifest(self.manifest_path), (None, ["METHOD_MANIFEST_INVALID: not JSON"]))

    def test_check_never_updates_the_manifest(self):
        engine = self.repo / "src/sabpuja_kundali/engine.py"
        engine.write_bytes(b"changed")
        before = self.manifest_path.read_bytes()
        check_manifest(self.manifest_path, self.repo)
        self.assertEqual(self.manifest_path.read_bytes(), before)

    def test_signature_and_emitted_block(self):
        manifest = load_json(MANIFEST)
        self.assertEqual(signature_mismatches(dummy_fixture()["method_signature"], manifest), [])
        self.assertEqual(signature_mismatches(dummy_fixture("DUMMY-03.json")["method_signature"], manifest), ["node"])
        good = {"ayanamsa": "Lahiri", "nodes": "mean", "houses": "whole_sign", "binding_version": "x"}
        self.assertEqual(emitted_block_contradictions(good, manifest), [])
        self.assertEqual(emitted_block_contradictions({**good, "nodes": "true"}, manifest), ["nodes"])
        self.assertEqual(emitted_block_contradictions(None, manifest), ["method block missing"])


class GeneratorIsolation(unittest.TestCase):
    def test_forbidden_imports_and_reads_are_found(self):
        bad = {
            "import swisseph": "imports swisseph",
            "import sabpuja_kundali.engine as e": "imports sabpuja_kundali.engine",
            "from sabpuja_kundali import rules": "imports from sabpuja_kundali",
            "from swisseph import calc_ut": "imports from swisseph",
            "__import__('swisseph')": "__import__('swisseph')",
            "import importlib\nimportlib.import_module('sabpuja_kundali.engine')": "import_module(",
            "import importlib\nname = 'x'\nimportlib.import_module(name)": "dynamic import_module",
            "exec('import swisseph')": "exec is not allowed",
            "open('reports/golden-report-x.json')": "open reads an engine output path",
            "from pathlib import Path\nPath('reports/x.md').read_text()": "Path reads an engine output path",
            "def f(:\n": "cannot parse",
        }
        for source, needle in bad.items():
            with self.subTest(source=source):
                found = scan_source(source, "probe.py")
                self.assertTrue(any(needle in v for v in found), found)

    def test_clean_source_and_committed_generator_pass(self):
        self.assertEqual(scan_source("import math\nfrom . import isolation\nprint(math.pi)\n"), [])
        self.assertEqual(scan_directory(GOLDEN_DIR / "generator"), [])

    def test_prohibited_import_in_a_generator_file_is_found(self):
        with tempfile.TemporaryDirectory() as tmp:
            gen = Path(tmp) / "generator"
            shutil.copytree(GOLDEN_DIR / "generator", gen, ignore=shutil.ignore_patterns("__pycache__"))
            (gen / "sub").mkdir()
            (gen / "sub" / "sneaky.py").write_text("import swisseph\n", encoding="utf-8")
            self.assertEqual(scan_directory(gen), ["sub/sneaky.py:1: imports swisseph"])
        self.assertEqual(scan_directory(Path(tmp)), ["generator directory missing: " + Path(tmp).name])

    def run_isolated(self, code: str) -> subprocess.CompletedProcess:
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
        return subprocess.run([sys.executable, "-I", "-c", f"import sys; sys.path.insert(0, {str(TESTS_DIR)!r})\n"
                               + textwrap.dedent(code)], capture_output=True, text=True, env=env, timeout=60)

    def test_runtime_guard_blocks_imports(self):
        result = self.run_isolated("""
            from golden.generator.isolation import import_guard
            for name in ("swisseph", "sabpuja_kundali", "sabpuja_kundali.engine"):
                with import_guard():
                    try:
                        __import__(name)
                    except ImportError as exc:
                        assert "forbidden" in str(exc), exc
                    else:
                        raise SystemExit("imported " + name)
            import json
            print("guard-ok")
        """)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("guard-ok", result.stdout)

    def test_runtime_guard_refuses_when_already_loaded(self):
        result = self.run_isolated("""
            import types, sys
            sys.modules["swisseph"] = types.ModuleType("swisseph")
            from golden.generator.isolation import import_guard
            try:
                with import_guard():
                    pass
            except ImportError as exc:
                print("refused", exc)
        """)
        self.assertIn("refused forbidden modules already loaded: ['swisseph']", result.stdout)

    def test_generator_entry_point_is_blocked(self):
        result = self.run_isolated("""
            from golden.generator.generate import main
            raise SystemExit(main())
        """)
        self.assertEqual(result.returncode, 2)
        self.assertIn("BLOCKED: reference generator not implemented", result.stderr)

    def test_reference_classes(self):
        registry = load_json(GOLDEN_DIR / "config" / "reference-registry.json")["references"]
        refs = [{"source_id": s, "source_class": c} for s, c in
                (("R-10", "D"), ("R-12", "M"), ("R-08", "D"), ("R-02", "I-code"), ("FAKE-SOURCE-DO-NOT-USE-01", "FAKE"))]
        self.assertEqual(check_reference_classes(refs, registry), [
            "REFERENCE_CLASS_NOT_INDEPENDENT: R-10 is class D",
            "REFERENCE_CLASS_NOT_INDEPENDENT: R-12 is class M",
            "REFERENCE_CLASS_NOT_INDEPENDENT: R-08 is class D",
            "REFERENCE_NOT_OBTAINED: R-02",
            "REFERENCE_CLASS_UNKNOWN: FAKE-SOURCE-DO-NOT-USE-01 fixture class not recognised",
            "REFERENCE_UNKNOWN: FAKE-SOURCE-DO-NOT-USE-01",
        ])

    def test_fixture_class_must_match_registry(self):
        independent = {"X": {"class": "I-code", "obtained": True}}
        dependent = {"X": {"class": "D", "obtained": True}}
        self.assertEqual(check_reference_classes([{"source_id": "X", "source_class": "I-code"}], independent), [])
        self.assertEqual(check_reference_classes([{"source_id": "X", "source_class": "D"}], independent),
                         ["REFERENCE_CLASS_MISMATCH: X fixture says D, registry says I-code"])
        self.assertEqual(check_reference_classes([{"source_id": "X", "source_class": "I-code"}], dependent),
                         ["REFERENCE_CLASS_MISMATCH: X fixture says I-code, registry says D"])
        self.assertEqual(check_reference_classes([{"source_id": "X", "source_class": "I-code"}],
                                                 {"X": {"class": "gold", "obtained": True}}),
                         ["REFERENCE_CLASS_UNKNOWN: X registry class not recognised"])
        self.assertEqual(check_reference_classes([{"source_id": "X"}], independent),
                         ["REFERENCE_CLASS_UNKNOWN: X fixture class not recognised"])


if __name__ == "__main__":
    unittest.main()
