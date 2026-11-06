"""PAN-QA-08 identity v8 (KUN-PAN-M2-SUN-001): structure, tree and exact-commit checks, with negative controls."""
from __future__ import annotations

import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from .common import REPO
from . import identity_v7 as iv7
from . import identity_v8 as iv8
from .identity_v2 import IdentityError, sha256

SUN = "src/sabpuja_kundali/panchanga/sun.py"
CONTRACT = "src/sabpuja_kundali/panchanga/contract.py"


def _committed():
    return iv8.load_committed(REPO)


class ManifestStructure(unittest.TestCase):
    def setUp(self):
        *self.prior, self.v8 = _committed()
        self.v7_bytes = (REPO / iv7.V7_PATH).read_bytes()

    def validate(self, doc):
        return iv8.validate_v8(doc, *self.prior, self.v7_bytes)

    def test_pinned_and_minimal(self):
        self.assertEqual(sha256((REPO / iv8.V8_PATH).read_bytes()), iv8.V8_SHA256)
        self.assertEqual(self.v8["modified"], {})
        self.assertEqual(tuple(self.v8["added"]), (SUN,))
        self.assertIn(CONTRACT, self.v8["m1_package"])
        self.assertNotIn(SUN, self.v8["m1_package"])

    def test_wrong_pin_refused(self):
        data = (REPO / iv8.V8_PATH).read_bytes()
        with self.assertRaisesRegex(IdentityError, "pinned SHA-256"):
            iv8.load_v8(data + b" ", *self.prior, self.v7_bytes)

    def test_structural_and_path_defects_refused(self):
        cases = []
        d = copy.deepcopy(self.v8); d["modified"] = {CONTRACT: {}}; cases.append((d, "modified paths differ"))
        d = copy.deepcopy(self.v8); d["added"]["report/phase1/x.py"] = d["added"][SUN]; cases.append((d, "added paths differ"))
        d = copy.deepcopy(self.v8); d["added"] = {}; cases.append((d, "added paths differ"))
        d = copy.deepcopy(self.v8); d["m1_package"][SUN] = d["added"][SUN]; cases.append((d, "also listed"))
        d = copy.deepcopy(self.v8); d["m1_package"] = {}; cases.append((d, "must list"))
        d = copy.deepcopy(self.v8); d["v7_manifest"]["sha256"] = "0" * 64; cases.append((d, "does not bind"))
        d = copy.deepcopy(self.v8); d["counts"]["added"] = 2; cases.append((d, "counts wrong"))
        d = copy.deepcopy(self.v8); d["extra"] = 1; cases.append((d, "keys differ"))
        d = copy.deepcopy(self.v8); d["added"][SUN]["git_blob"] = "x"; cases.append((d, "malformed"))
        for doc, msg in cases:
            with self.subTest(msg):
                with self.assertRaisesRegex(IdentityError, msg):
                    self.validate(doc)


class TreeAndCommit(unittest.TestCase):
    def setUp(self):
        self.all = _committed()

    def test_current_tree_and_exact_commit(self):
        t = iv8.verify_tree(REPO, *self.all)
        self.assertEqual((t["v1_unchanged"], t["v8_modified"], t["v8_added"]), (209, 0, 1))
        g = iv8.verify_git_v8(REPO, *self.all)
        self.assertEqual(g["v8_added"], 1)

    def _tree_with(self, mutate):
        names = [n for n in subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", "HEAD"],
                                           capture_output=True, check=True).stdout.decode().split("\0") if n]
        from .identity_v2 import Git
        blobs = Git(REPO).blobs("HEAD", names)
        mutate(blobs)
        from .identity_v2 import in_scope
        return iv8.verify_tree(REPO, *self.all, read=blobs.get,
                               listing=lambda: {n for n in blobs if in_scope(n) and blobs[n] is not None},
                               packet_listing=lambda: {n for n in blobs if n.startswith(iv8.PACKET_PREFIX)})

    def test_pristine_head_copy_passes(self):
        self.assertEqual(self._tree_with(lambda b: None)["v8_added"], 1)

    def test_m1_edit_new_package_file_or_module_edit_refused(self):
        for label, mutate, msg in (
            ("M1 contract edited", lambda b: b.__setitem__(CONTRACT, b[CONTRACT] + b"\n"), "M1 package"),
            ("extra package file", lambda b: b.__setitem__("src/sabpuja_kundali/panchanga/daily.py", b"x = 1\n"),
             "undeclared file"),
            ("sun module edited", lambda b: b.__setitem__(SUN, b[SUN] + b"\n"), "declared v8 added"),
            ("sun module removed", lambda b: b.__setitem__(SUN, None), "missing"),
        ):
            with self.subTest(label):
                with self.assertRaisesRegex(IdentityError, msg):
                    self._tree_with(mutate)

    def test_base_is_not_the_v8_tree_and_history_is_required(self):
        with self.assertRaisesRegex(IdentityError, "differs from the v8 declaration"):
            iv8.verify_git_v8(REPO, *self.all, commit=iv8.BASE_COMMIT)
        with self.assertRaisesRegex(IdentityError, "not an ancestor"):
            iv8.verify_git_v8(REPO, *self.all, commit=iv7.BASE_COMMIT)

    def test_no_engine_data_preview_prototype_or_report_change_since_a8c3108(self):
        out = subprocess.run(["git", "-C", str(REPO), "diff", "--name-status", iv8.BASE_COMMIT, "HEAD", "--",
                              "src", "data", "preview", "prototype", "report", "pyproject.toml", "examples"],
                             capture_output=True, check=True, text=True).stdout
        self.assertEqual(out, f"A\t{SUN}\n")

    def test_not_a_git_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv8.verify_git_v8(Path(tmp), *self.all)


if __name__ == "__main__":
    unittest.main()
