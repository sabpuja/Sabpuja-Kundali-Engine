"""PAN-QA-08 identity v9 (KUN-PAN-RPT-002): structure, tree and exact-commit checks, with negative controls."""
from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

from .common import REPO
from . import identity_v8 as iv8
from . import identity_v9 as iv9
from .identity_v2 import IdentityError, Git, in_scope, sha256

SUN = "src/sabpuja_kundali/panchanga/sun.py"
CONTRACT = "src/sabpuja_kundali/panchanga/contract.py"
VARA = "src/sabpuja_kundali/panchanga/vara.py"
PREMIUM = "report/phase1/premium_report.py"
VARA_REPORT = "report/phase1/vara_report.py"


def _committed():
    return iv9.load_committed(REPO)


class ManifestStructure(unittest.TestCase):
    def setUp(self):
        *self.prior, self.v9 = _committed()
        self.v8_bytes = (REPO / iv8.V8_PATH).read_bytes()

    def validate(self, doc):
        return iv9.validate_v9(doc, *self.prior, self.v8_bytes)

    def test_pinned_and_bounded(self):
        self.assertEqual(sha256((REPO / iv9.V9_PATH).read_bytes()), iv9.V9_SHA256)
        self.assertEqual(tuple(self.v9["modified"]), iv9.AUTHORIZED_MODIFIED)
        self.assertEqual(tuple(self.v9["added"]), iv9.AUTHORIZED_ADDED)
        self.assertEqual(len(self.v9["added"]), 32)
        self.assertIn(VARA, self.v9["added"])
        for p in (SUN, CONTRACT):
            self.assertIn(p, self.v9["package"])
        self.assertNotIn(VARA, self.v9["package"])
        self.assertFalse(any(p.startswith("tests/panchanga/") for p in self.v9["added"]))

    def test_wrong_pin_refused(self):
        data = (REPO / iv9.V9_PATH).read_bytes()
        with self.assertRaisesRegex(IdentityError, "pinned SHA-256"):
            iv9.load_v9(data + b" ", *self.prior, self.v8_bytes)

    def test_structural_and_path_defects_refused(self):
        cases = []
        d = copy.deepcopy(self.v9); d["modified"].pop(PREMIUM); cases.append((d, "modified paths differ"))
        d = copy.deepcopy(self.v9); d["modified"]["report/phase1/report_locale.py"] = d["modified"][PREMIUM]
        cases.append((d, "modified paths differ"))
        d = copy.deepcopy(self.v9); d["added"]["report/phase1/x.py"] = d["added"][VARA_REPORT]
        cases.append((d, "added paths differ"))
        d = copy.deepcopy(self.v9); d["added"].pop(VARA); cases.append((d, "added paths differ"))
        d = copy.deepcopy(self.v9); d["package"][SUN]["sha256"] = "0" * 64; cases.append((d, "not the v8 pin"))
        d = copy.deepcopy(self.v9); d["package"] = {}; d["counts"]["package"] = 0; cases.append((d, "must list"))
        d = copy.deepcopy(self.v9); d["modified"][PREMIUM]["before_sha256"] = "0" * 64
        cases.append((d, "before_sha256 differs"))
        d = copy.deepcopy(self.v9)
        d["modified"][PREMIUM]["v9_sha256"] = d["modified"][PREMIUM]["before_sha256"]
        cases.append((d, "declares no change"))
        d = copy.deepcopy(self.v9); d["v8_manifest"]["sha256"] = "0" * 64; cases.append((d, "does not bind"))
        d = copy.deepcopy(self.v9); d["counts"]["added"] = 31; cases.append((d, "counts wrong"))
        d = copy.deepcopy(self.v9); d["extra"] = 1; cases.append((d, "keys differ"))
        d = copy.deepcopy(self.v9); d["added"][VARA]["git_blob"] = "x"; cases.append((d, "malformed"))
        for doc, msg in cases:
            with self.subTest(msg):
                with self.assertRaisesRegex(IdentityError, msg):
                    self.validate(doc)


class TreeAndCommit(unittest.TestCase):
    def setUp(self):
        self.all = _committed()

    def test_current_tree_and_exact_commit(self):
        t = iv9.verify_tree(REPO, *self.all)
        self.assertEqual((t["v1_unchanged"], t["v9_modified"], t["v9_added"]), (209, 3, 32))
        g = iv9.verify_git_v9(REPO, *self.all)
        self.assertEqual((g["v9_modified"], g["v9_added"]), (3, 32))

    def _tree_with(self, mutate):
        names = [n for n in subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", "HEAD"],
                                           capture_output=True, check=True).stdout.decode().split("\0") if n]
        blobs = Git(REPO).blobs("HEAD", names)
        mutate(blobs)
        return iv9.verify_tree(REPO, *self.all, read=blobs.get,
                               listing=lambda: {n for n in blobs if in_scope(n) and blobs[n] is not None},
                               packet_listing=lambda: {n for n in blobs if n.startswith(iv9.PACKET_PREFIX)})

    def test_pristine_head_copy_passes(self):
        self.assertEqual(self._tree_with(lambda b: None)["v9_added"], 32)

    def test_negative_controls(self):
        engine = "src/sabpuja_kundali/engine.py"
        for label, mutate, msg in (
            ("M1 contract edited", lambda b: b.__setitem__(CONTRACT, b[CONTRACT] + b"\n"), "v9 package"),
            ("sun.py edited", lambda b: b.__setitem__(SUN, b[SUN] + b"\n"), "v9 package"),
            ("engine edited", lambda b: b.__setitem__(engine, b[engine] + b"\n"), "undeclared change to a v1 file"),
            ("vara module edited", lambda b: b.__setitem__(VARA, b[VARA] + b"\n"), "declared v9 added"),
            ("report edited", lambda b: b.__setitem__(PREMIUM, b[PREMIUM] + b"\n"), "declared v9 modified"),
            ("vara module removed", lambda b: b.__setitem__(VARA, None), "missing"),
            ("extra package file", lambda b: b.__setitem__("src/sabpuja_kundali/panchanga/daily.py", b"x = 1\n"),
             "undeclared file"),
            ("extra report file", lambda b: b.__setitem__("report/phase1/extra.py", b"x = 1\n"), "undeclared file"),
        ):
            with self.subTest(label):
                with self.assertRaisesRegex(IdentityError, msg):
                    self._tree_with(mutate)

    def test_base_is_not_the_v9_tree_and_history_is_required(self):
        with self.assertRaisesRegex(IdentityError, "v9"):
            iv9.verify_git_v9(REPO, *self.all, commit=iv9.BASE_COMMIT)
        with self.assertRaisesRegex(IdentityError, "not an ancestor"):
            iv9.verify_git_v9(REPO, *self.all, commit=iv8.BASE_COMMIT)

    def test_engine_data_preview_prototype_unchanged_since_c759c41(self):
        out = subprocess.run(["git", "-C", str(REPO), "diff", "--name-status", iv9.BASE_COMMIT, "HEAD", "--",
                              "src", "data", "preview", "prototype", "pyproject.toml", "examples"],
                             capture_output=True, check=True, text=True).stdout
        self.assertEqual(out, f"A\t{VARA}\n")

    def test_not_a_git_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv9.verify_git_v9(Path(tmp), *self.all)


if __name__ == "__main__":
    unittest.main()
