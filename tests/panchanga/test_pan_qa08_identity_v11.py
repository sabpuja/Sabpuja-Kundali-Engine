"""PAN-QA-08 identity v11 (KUN-PAN-VARA-G2-001): structure, tree and exact-commit checks, with negative controls."""
from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from .common import REPO
from . import identity_v10 as iv10
from . import identity_v11 as iv11
from .identity_v2 import IdentityError, Git, in_scope, sha256

SUN = "src/sabpuja_kundali/panchanga/sun.py"
CONTRACT = "src/sabpuja_kundali/panchanga/contract.py"
VARA = "src/sabpuja_kundali/panchanga/vara.py"
PREMIUM = "report/phase1/premium_report.py"
VARA_REPORT = "report/phase1/vara_report.py"
CATALOG = "report/phase1/essentials_en.json"
PINS = "report/phase1/tests/fixtures/essentials-en-sha256.json"
FIXTURE = "report/phase1/tests/fixtures/vara/s07-noon.json"


def _committed():
    return iv11.load_committed(REPO)


class ManifestStructure(unittest.TestCase):
    def setUp(self):
        *self.prior, self.v11 = _committed()
        self.v10_bytes = (REPO / iv10.V10_PATH).read_bytes()

    def validate(self, doc):
        return iv11.validate_v11(doc, *self.prior, self.v10_bytes)

    def test_pinned_and_bounded(self):
        self.assertEqual(sha256((REPO / iv11.V11_PATH).read_bytes()), iv11.V11_SHA256)
        self.assertEqual(tuple(self.v11["modified"]), iv11.AUTHORIZED_MODIFIED)
        self.assertEqual(len(self.v11["modified"]), 32)
        for p in (SUN, VARA, VARA_REPORT, CATALOG, FIXTURE):
            self.assertIn(p, self.v11["modified"])
        for p in (PREMIUM, PINS, "report/phase1/report_vara_i18n.json"):
            self.assertNotIn(p, self.v11["modified"])
        self.assertIn(CONTRACT, self.v11["package"])
        self.assertEqual(len(self.v11["package"]), 6)
        self.assertFalse(any(p.startswith("tests/panchanga/") for p in self.v11["modified"]))

    def test_wrong_pin_refused(self):
        data = (REPO / iv11.V11_PATH).read_bytes()
        with self.assertRaisesRegex(IdentityError, "pinned SHA-256"):
            iv11.load_v11(data + b" ", *self.prior, self.v10_bytes)

    def test_structural_and_path_defects_refused(self):
        cases = []
        d = copy.deepcopy(self.v11); d["modified"].pop(SUN); cases.append((d, "modified paths differ"))
        d = copy.deepcopy(self.v11); d["modified"][PREMIUM] = d["modified"][VARA_REPORT]
        cases.append((d, "modified paths differ"))
        d = copy.deepcopy(self.v11); d["package"][CONTRACT]["sha256"] = "0" * 64; cases.append((d, "not the v10 pin"))
        d = copy.deepcopy(self.v11); d["package"] = {}; d["counts"]["package"] = 0; cases.append((d, "must list"))
        d = copy.deepcopy(self.v11); d["modified"][SUN]["before_sha256"] = "0" * 64
        cases.append((d, "before_sha256 differs"))
        d = copy.deepcopy(self.v11); d["modified"][SUN]["v11_sha256"] = d["modified"][SUN]["before_sha256"]
        cases.append((d, "declares no change"))
        d = copy.deepcopy(self.v11); d["v10_manifest"]["sha256"] = "0" * 64; cases.append((d, "does not bind"))
        d = copy.deepcopy(self.v11); d["counts"]["modified"] = 31; cases.append((d, "counts wrong"))
        d = copy.deepcopy(self.v11); d["extra"] = 1; cases.append((d, "keys differ"))
        d = copy.deepcopy(self.v11); d["modified"][SUN]["v11_git_blob"] = "x"; cases.append((d, "malformed"))
        for doc, msg in cases:
            with self.subTest(msg):
                with self.assertRaisesRegex(IdentityError, msg):
                    self.validate(doc)


class TreeAndCommit(unittest.TestCase):
    def setUp(self):
        self.all = _committed()

    def test_current_tree_and_exact_commit(self):
        t = iv11.verify_tree(REPO, *self.all)
        self.assertEqual((t["v1_unchanged"], t["v11_modified"], t["v11_package"]), (209, 32, 6))
        g = iv11.verify_git_v11(REPO, *self.all)
        self.assertEqual(g["v11_modified"], 32)

    def _tree_with(self, mutate):
        names = [n for n in subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", "HEAD"],
                                           capture_output=True, check=True).stdout.decode().split("\0") if n]
        blobs = Git(REPO).blobs("HEAD", names)
        mutate(blobs)
        return iv11.verify_tree(REPO, *self.all, read=blobs.get,
                                listing=lambda: {n for n in blobs if in_scope(n) and blobs[n] is not None},
                                packet_listing=lambda: {n for n in blobs if n.startswith(iv11.PACKET_PREFIX)})

    def test_pristine_head_copy_passes(self):
        self.assertEqual(self._tree_with(lambda b: None)["v11_modified"], 32)

    def test_negative_controls(self):
        engine = "src/sabpuja_kundali/engine.py"
        catalog = "report/phase1/report_vara_i18n.json"
        for label, mutate, msg in (
            ("M1 contract edited", lambda b: b.__setitem__(CONTRACT, b[CONTRACT] + b"\n"), "v11 package"),
            ("sun.py edited", lambda b: b.__setitem__(SUN, b[SUN] + b"\n"), "declared v11 modified"),
            ("vara.py edited", lambda b: b.__setitem__(VARA, b[VARA] + b"\n"), "declared v11 modified"),
            ("engine edited", lambda b: b.__setitem__(engine, b[engine] + b"\n"), "undeclared change to a v1 file"),
            ("Vara catalog edited", lambda b: b.__setitem__(catalog, b[catalog] + b"\n"), "declared v9 added"),
            ("Essentials PDF pins edited", lambda b: b.__setitem__(PINS, b[PINS] + b"\n"), "declared v10 added"),
            ("report edited", lambda b: b.__setitem__(PREMIUM, b[PREMIUM] + b"\n"), "declared v10 modified"),
            ("fixture removed", lambda b: b.__setitem__(FIXTURE, None), "missing"),
            ("extra package file", lambda b: b.__setitem__("src/sabpuja_kundali/panchanga/daily.py", b"x = 1\n"),
             "undeclared file"),
        ):
            with self.subTest(label):
                with self.assertRaisesRegex(IdentityError, msg):
                    self._tree_with(mutate)

    def test_base_is_not_the_v11_tree_and_history_is_required(self):
        with self.assertRaisesRegex(IdentityError, "v11"):
            iv11.verify_git_v11(REPO, *self.all, commit=iv11.BASE_COMMIT)
        with self.assertRaisesRegex(IdentityError, "not an ancestor"):
            iv11.verify_git_v11(REPO, *self.all, commit=iv10.BASE_COMMIT)

    def test_engine_data_preview_prototype_unchanged_since_30bdace(self):
        """Outside the Panchanga package nothing of the engine, data, preview or prototype changes."""
        out = subprocess.run(["git", "-C", str(REPO), "diff", "--name-status", iv11.BASE_COMMIT, "HEAD", "--",
                              "src", "data", "preview", "prototype", "pyproject.toml", "examples"],
                             capture_output=True, check=True, text=True).stdout
        self.assertEqual(out, f"M\t{SUN}\nM\t{VARA}\n")

    def test_only_status_and_provenance_lines_change_in_the_engine_modules(self):
        """No formula, threshold or refusal line changes: every changed line of sun.py and vara.py is in the
        docstring or in a status, claim-boundary or convention-decision constant."""
        allowed = ("STATUS", "CLAIM_BOUNDARY", "CONVENTION_STATUS", "convention_status", "convention_decision",
                   "claim_boundary")
        for path in (SUN, VARA):
            diff = subprocess.run(["git", "-C", str(REPO), "diff", "-U0", iv11.BASE_COMMIT, "HEAD", "--", path],
                                  capture_output=True, check=True, text=True).stdout
            base = subprocess.run(["git", "-C", str(REPO), "show", f"{iv11.BASE_COMMIT}:{path}"],
                                  capture_output=True, check=True, text=True).stdout
            head = (REPO / path).read_text(encoding="utf-8")
            doc_end_base, doc_end_head = base.index('"""', 3) + 3, head.index('"""', 3) + 3
            self.assertEqual(base[doc_end_base:].count("\n") > 0, True)
            code_base = [l for l in base[doc_end_base:].splitlines()]
            code_head = [l for l in head[doc_end_head:].splitlines()]
            removed = [l for l in code_base if l not in code_head]
            added = [l for l in code_head if l not in code_base]
            for line in removed + added:
                with self.subTest(path=path, line=line):
                    stripped = line.strip()
                    self.assertTrue(stripped == "" or stripped.startswith(('"', "#"))
                                    or any(stripped.startswith(a) or f'"{a}"' in stripped for a in allowed),
                                    line)
            self.assertTrue(diff)

    def test_vara_fixtures_change_only_status_fields(self):
        """Every one of the 25 Vara documents differs from 30bdace only in status, claim_boundary and
        method.convention_decision: all instants, weekdays, boundaries and provenance are unchanged."""
        fixtures = [p for p in iv11.AUTHORIZED_MODIFIED if "/fixtures/vara" in p]
        self.assertEqual(len(fixtures), 25)
        old_blobs = Git(REPO).blobs(iv11.BASE_COMMIT, fixtures)

        def strip(doc):
            doc = copy.deepcopy(doc)
            v = doc["vara"] if "vara" in doc and "schema" not in doc else doc
            for k in ("status", "claim_boundary"):
                v.pop(k)
            v["method"].pop("convention_decision")
            return doc
        for p in fixtures:
            with self.subTest(p):
                old, new = json.loads(old_blobs[p]), json.loads((REPO / p).read_text(encoding="utf-8"))
                self.assertNotEqual(old, new)
                self.assertEqual(strip(old), strip(new))

    def test_not_a_git_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv11.verify_git_v11(Path(tmp), *self.all)


if __name__ == "__main__":
    unittest.main()
