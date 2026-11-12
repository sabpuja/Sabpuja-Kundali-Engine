"""PAN-QA-08 identity v10 (KUN-RC-ESS-001): structure, tree and exact-commit checks, with negative controls."""
from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path

from .common import REPO
from . import identity_v9 as iv9
from . import identity_v10 as iv10
from .identity_v2 import IdentityError, Git, in_scope, sha256

SUN = "src/sabpuja_kundali/panchanga/sun.py"
CONTRACT = "src/sabpuja_kundali/panchanga/contract.py"
VARA = "src/sabpuja_kundali/panchanga/vara.py"
PREMIUM = "report/phase1/premium_report.py"
VARA_REPORT = "report/phase1/vara_report.py"
ESSENTIALS = "report/phase1/essentials.py"
CATALOG = "report/phase1/essentials_en.json"


def _committed():
    return iv10.load_committed(REPO)


class ManifestStructure(unittest.TestCase):
    def setUp(self):
        *self.prior, self.v10 = _committed()
        self.v9_bytes = (REPO / iv9.V9_PATH).read_bytes()

    def validate(self, doc):
        return iv10.validate_v10(doc, *self.prior, self.v9_bytes)

    def test_pinned_and_bounded(self):
        self.assertEqual(sha256((REPO / iv10.V10_PATH).read_bytes()), iv10.V10_SHA256)
        self.assertEqual(tuple(self.v10["modified"]), iv10.AUTHORIZED_MODIFIED)
        self.assertEqual(tuple(self.v10["added"]), iv10.AUTHORIZED_ADDED)
        self.assertEqual(len(self.v10["added"]), 6)
        for p in (SUN, CONTRACT, VARA):
            self.assertIn(p, self.v10["package"])
        self.assertIn(VARA_REPORT, self.v10["modified"])
        self.assertFalse(any(p.startswith("tests/panchanga/") for p in self.v10["added"]))
        self.assertFalse(any(p.startswith(("src/", "prototype/", "preview/", "data/")) for p in
                             list(self.v10["added"]) + list(self.v10["modified"])))

    def test_wrong_pin_refused(self):
        data = (REPO / iv10.V10_PATH).read_bytes()
        with self.assertRaisesRegex(IdentityError, "pinned SHA-256"):
            iv10.load_v10(data + b" ", *self.prior, self.v9_bytes)

    def test_structural_and_path_defects_refused(self):
        cases = []
        d = copy.deepcopy(self.v10); d["modified"].pop(PREMIUM); cases.append((d, "modified paths differ"))
        d = copy.deepcopy(self.v10); d["modified"]["report/phase1/report_locale.py"] = d["modified"][PREMIUM]
        cases.append((d, "modified paths differ"))
        d = copy.deepcopy(self.v10); d["added"]["report/phase1/x.py"] = d["added"][ESSENTIALS]
        cases.append((d, "added paths differ"))
        d = copy.deepcopy(self.v10); d["added"].pop(CATALOG); cases.append((d, "added paths differ"))
        d = copy.deepcopy(self.v10); d["package"][VARA]["sha256"] = "0" * 64; cases.append((d, "not the v9 pin"))
        d = copy.deepcopy(self.v10); d["package"] = {}; d["counts"]["package"] = 0; cases.append((d, "must list"))
        d = copy.deepcopy(self.v10); d["modified"][PREMIUM]["before_sha256"] = "0" * 64
        cases.append((d, "before_sha256 differs"))
        d = copy.deepcopy(self.v10)
        d["modified"][PREMIUM]["v10_sha256"] = d["modified"][PREMIUM]["before_sha256"]
        cases.append((d, "declares no change"))
        d = copy.deepcopy(self.v10); d["v9_manifest"]["sha256"] = "0" * 64; cases.append((d, "does not bind"))
        d = copy.deepcopy(self.v10); d["counts"]["added"] = 5; cases.append((d, "counts wrong"))
        d = copy.deepcopy(self.v10); d["extra"] = 1; cases.append((d, "keys differ"))
        d = copy.deepcopy(self.v10); d["added"][ESSENTIALS]["git_blob"] = "x"; cases.append((d, "malformed"))
        for doc, msg in cases:
            with self.subTest(msg):
                with self.assertRaisesRegex(IdentityError, msg):
                    self.validate(doc)


D30B = "30bdacea14eac444f0dc3353b5922134a255c697"   # the audited v10 commit (draft PR #93 head)


class TreeAndCommit(unittest.TestCase):
    """Since KUN-PAN-VARA-G2-001 these run on 30bdace, the audited v10 tree; HEAD carries the v11 overlay, which
    v10 alone must reject (test_v11_head_is_rejected_by_v10_alone), and is checked through v11."""

    def setUp(self):
        self.all = _committed()

    def test_audited_tree_and_exact_commit(self):
        t = iv10.verify_commit(REPO, D30B, *self.all)
        self.assertEqual((t["v1_unchanged"], t["v10_modified"], t["v10_added"], t["v10_package"]), (209, 4, 6, 8))
        g = iv10.verify_git_v10(REPO, *self.all, commit=D30B)
        self.assertEqual((g["v10_modified"], g["v10_added"]), (4, 6))

    def test_v11_head_is_rejected_by_v10_alone(self):
        with self.assertRaises(IdentityError):
            iv10.verify_commit(REPO, "HEAD", *self.all)

    def _tree_with(self, mutate):
        names = [n for n in subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", D30B],
                                           capture_output=True, check=True).stdout.decode().split("\0") if n]
        blobs = Git(REPO).blobs(D30B, names)
        mutate(blobs)
        return iv10.verify_tree(REPO, *self.all, read=blobs.get,
                                listing=lambda: {n for n in blobs if in_scope(n) and blobs[n] is not None},
                                packet_listing=lambda: {n for n in blobs if n.startswith(iv10.PACKET_PREFIX)})

    def test_pristine_head_copy_passes(self):
        self.assertEqual(self._tree_with(lambda b: None)["v10_added"], 6)

    def test_negative_controls(self):
        engine = "src/sabpuja_kundali/engine.py"
        server = "prototype/kundali_prototype/server.py"
        catalog = "report/phase1/report_vara_i18n.json"
        for label, mutate, msg in (
            ("M1 contract edited", lambda b: b.__setitem__(CONTRACT, b[CONTRACT] + b"\n"), "v10 package"),
            ("sun.py edited", lambda b: b.__setitem__(SUN, b[SUN] + b"\n"), "v10 package"),
            ("vara.py edited", lambda b: b.__setitem__(VARA, b[VARA] + b"\n"), "v10 package"),
            ("engine edited", lambda b: b.__setitem__(engine, b[engine] + b"\n"), "undeclared change to a v1 file"),
            ("server edited", lambda b: b.__setitem__(server, b[server] + b"\n"), "declared v3 modified"),
            ("Vara catalog edited", lambda b: b.__setitem__(catalog, b[catalog] + b"\n"), "declared v9 added"),
            ("Essentials catalog edited", lambda b: b.__setitem__(CATALOG, b[CATALOG] + b"\n"), "declared v10 added"),
            ("report edited", lambda b: b.__setitem__(PREMIUM, b[PREMIUM] + b"\n"), "declared v10 modified"),
            ("Essentials removed", lambda b: b.__setitem__(ESSENTIALS, None), "missing"),
            ("extra package file", lambda b: b.__setitem__("src/sabpuja_kundali/panchanga/daily.py", b"x = 1\n"),
             "undeclared file"),
            ("extra report file", lambda b: b.__setitem__("report/phase1/extra.py", b"x = 1\n"), "undeclared file"),
        ):
            with self.subTest(label):
                with self.assertRaisesRegex(IdentityError, msg):
                    self._tree_with(mutate)

    def test_base_is_not_the_v10_tree_and_history_is_required(self):
        with self.assertRaisesRegex(IdentityError, "v10"):
            iv10.verify_git_v10(REPO, *self.all, commit=iv10.BASE_COMMIT)
        with self.assertRaisesRegex(IdentityError, "not an ancestor"):
            iv10.verify_git_v10(REPO, *self.all, commit=iv9.BASE_COMMIT)

    def test_engine_data_preview_prototype_unchanged_7d9d10a_to_30bdace(self):
        out = subprocess.run(["git", "-C", str(REPO), "diff", "--name-status", iv10.BASE_COMMIT, D30B, "--",
                              "src", "data", "preview", "prototype", "pyproject.toml", "examples"],
                             capture_output=True, check=True, text=True).stdout
        self.assertEqual(out, "")

    def test_not_a_git_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv10.verify_git_v10(Path(tmp), *self.all)


if __name__ == "__main__":
    unittest.main()
