"""PAN-QA-08 v2 identity gate: fail-closed controls (KUN-I18N-INT-001).

Each test feeds `identity_v2` one defect and requires a refusal: baseline
substitution, malformed or tampered manifests, missing files, unexpected hashes and
undeclared changes. A pristine copy of the committed tree must pass. No scientific
tolerance, ephemeris or chart value is read or changed here.
"""
from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from .common import REPO
from . import identity_v2 as iv
from .identity_v2 import IdentityError


def _committed():
    v1_bytes = (REPO / iv.V1_PATH).read_bytes()
    v2_bytes = (REPO / iv.V2_PATH).read_bytes()
    v1 = iv.load_v1(v1_bytes)
    return v1_bytes, v1, v2_bytes, iv.load_v2(v2_bytes, v1, v1_bytes)


class ManifestStructureTest(unittest.TestCase):
    def setUp(self):
        self.v1_bytes, self.v1, self.v2_bytes, self.v2 = _committed()

    def bad(self, mutate, needle):
        doc = copy.deepcopy(self.v2)
        mutate(doc)
        with self.assertRaises(IdentityError) as ctx:
            iv.validate_v2(doc, self.v1, self.v1_bytes)
        self.assertIn(needle, str(ctx.exception))

    def first(self, section):
        return next(iter(self.v2[section]))

    def test_committed_manifests_are_the_pinned_ones(self):
        self.assertEqual(iv.sha256(self.v1_bytes), iv.V1_SHA256)
        self.assertEqual(iv.sha256(self.v2_bytes), iv.V2_SHA256)
        self.assertEqual(self.v2["counts"], {"v1": 222, "modified": 12, "unchanged": 210, "added": 55})
        self.assertEqual(len(self.v1["files"]) - len(self.v2["modified"]), 210)

    def test_baseline_substitution_is_refused(self):
        swapped = self.v1_bytes.replace(b'"files"', b'"files" ', 1)
        with self.assertRaisesRegex(IdentityError, "baseline substitution"):
            iv.load_v1(swapped)
        doc = json.loads(self.v1_bytes)
        doc["files"][next(iter(doc["files"]))] = "0" * 64
        forged = json.dumps(doc).encode()
        with self.assertRaisesRegex(IdentityError, "baseline substitution"):
            iv.load_v1(forged)
        # A forged v1 that is self-consistent still fails the v2 binding to the preserved v1.
        forged_v1 = iv.load_v1(forged, expected_sha=iv.sha256(forged))
        with self.assertRaisesRegex(IdentityError, "does not bind the preserved v1"):
            iv.validate_v2(copy.deepcopy(self.v2), forged_v1, forged)

    def test_v2_byte_change_is_refused_by_the_pin(self):
        with self.assertRaisesRegex(IdentityError, "pinned SHA-256"):
            iv.load_v2(self.v2_bytes + b" ", self.v1, self.v1_bytes)

    def test_not_json_and_duplicate_keys_are_refused(self):
        with self.assertRaisesRegex(IdentityError, "not valid JSON"):
            iv.load_v2(b"{", self.v1, self.v1_bytes, expected_sha=iv.sha256(b"{"))
        dup = self.v2_bytes.replace(b'"counts": {', b'"counts": {"v1": 222, ', 1)
        with self.assertRaisesRegex(IdentityError, "duplicate key"):
            iv.load_v2(dup, self.v1, self.v1_bytes, expected_sha=iv.sha256(dup))

    def test_top_level_shape(self):
        self.bad(lambda d: d.pop("added"), "keys differ")
        self.bad(lambda d: d.update(extra=1), "keys differ")
        self.bad(lambda d: d.update(manifest_schema="sabpuja-pan-qa-08-identity/1"), "manifest_schema")
        self.bad(lambda d: d.update(note=""), "note")
        self.bad(lambda d: d["sources"].update(integrated_head="0" * 40), "approved commits")
        self.bad(lambda d: d["counts"].update(unchanged=211), "counts")
        self.bad(lambda d: d["v1_baseline"].update(file_count=221), "does not bind")
        self.bad(lambda d: d["v1_baseline"].update(base_commit="0" * 40), "does not bind")

    def test_path_lists_must_be_complete_and_sorted(self):
        m = self.first("modified")
        self.bad(lambda d: d["modified"].pop(m), "path counts")
        a = self.first("added")
        self.bad(lambda d: d["added"].pop(a), "path counts")

        def unsort(d):
            items = list(d["added"].items())
            d["added"] = dict(reversed(items))
        self.bad(unsort, "sorted")

    def test_modified_entries(self):
        m = self.first("modified")
        self.bad(lambda d: d["modified"][m].update(v1_sha256="0" * 64), "differs from the v1 baseline")
        self.bad(lambda d: d["modified"][m].update(v2_sha256=d["modified"][m]["v1_sha256"]), "declares no change")
        self.bad(lambda d: d["modified"][m].update(v2_sha256="XYZ"), "hash malformed")
        self.bad(lambda d: d["modified"][m].update(v2_git_blob="0" * 39), "hash malformed")
        self.bad(lambda d: d["modified"][m].pop("v2_git_blob"), "entry malformed")

        def not_in_v1(d):
            e = d["modified"].pop(m)
            d["modified"]["zz/not-in-v1.txt"] = e
        self.bad(not_in_v1, "not a v1 file")

    def test_added_entries(self):
        a = self.first("added")
        unchanged = next(p for p in self.v1["files"] if p not in self.v2["modified"])
        for bad_path, needle in ((unchanged, "already exists in v1"), ("../escape", "unsafe"),
                                 ("/abs/path", "unsafe"), ("a//b", "unsafe"), ("a\\b", "unsafe")):
            def swap(d, bad_path=bad_path):
                e = d["added"].pop(a)
                d["added"][bad_path] = e
                d["added"] = dict(sorted(d["added"].items()))
            self.bad(swap, needle)
        self.bad(lambda d: d["added"][a].update(sha256="0" * 63), "entry malformed")
        self.bad(lambda d: d["added"][a].update(extra="x"), "entry malformed")

        def self_declared(d):
            e = d["added"].pop(a)
            d["added"][iv.V2_PATH] = e
            d["added"] = dict(sorted(d["added"].items()))
        self.bad(self_declared, "cannot declare itself")


class TreeVerificationTest(unittest.TestCase):
    """verify_tree on a private copy of the v1 scope and the 55 added paths, taken from the git
    objects of the audited v2 commit be608d8 (since KUN-I18N-INT-001A the working tree carries
    the v3 changes, which identity_v3 and its own tests cover)."""

    @classmethod
    def setUpClass(cls):
        cls.v1_bytes, cls.v1, cls.v2_bytes, cls.v2 = _committed()
        out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", iv.V2_CANDIDATE_COMMIT],
                             capture_output=True, check=True).stdout
        tracked = [p for p in out.decode().split("\0") if p]
        cls.paths = [p for p in tracked if iv.in_scope(p) or p in cls.v2["added"]]
        cls.blobs = iv.Git(REPO).blobs(iv.V2_CANDIDATE_COMMIT, cls.paths)

    def restore(self, p):
        (self.tmp / p).write_bytes(self.blobs[p])

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pan-qa08-v2-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        for p in self.paths:
            (self.tmp / p).parent.mkdir(parents=True, exist_ok=True)
            self.restore(p)

    def refused(self, needle):
        with self.assertRaises(IdentityError) as ctx:
            iv.verify_tree(self.tmp, self.v1, self.v2)
        self.assertIn(needle, str(ctx.exception))

    def unchanged_path(self):
        return next(p for p in sorted(self.v1["files"]) if p not in self.v2["modified"])

    def test_pristine_copy_passes(self):
        self.assertEqual(iv.verify_tree(self.tmp, self.v1, self.v2), {"unchanged": 210, "modified": 12, "added": 55})

    def test_missing_files_are_refused(self):
        for p in (self.unchanged_path(), next(iter(self.v2["modified"])), next(iter(self.v2["added"]))):
            with self.subTest(p=p):
                data = (self.tmp / p).read_bytes()
                (self.tmp / p).unlink()
                self.refused(f"missing: {p}")
                (self.tmp / p).write_bytes(data)

    def test_unexpected_hashes_are_refused(self):
        m, a = next(iter(self.v2["modified"])), next(iter(self.v2["added"]))
        with open(self.tmp / m, "ab") as f:
            f.write(b"\n")
        self.refused(f"unexpected hash (declared v2 modified): {m}")
        self.restore(m)
        with open(self.tmp / a, "ab") as f:
            f.write(b"\n")
        self.refused(f"unexpected hash (declared v2 added): {a}")

    def test_reverting_a_declared_change_to_v1_bytes_is_refused(self):
        m = next(iter(self.v2["modified"]))
        old = subprocess.run(["git", "-C", str(REPO), "cat-file", "blob", f"{iv.V1_BASE_COMMIT}:{m}"],
                             capture_output=True, check=True).stdout
        (self.tmp / m).write_bytes(old)
        self.refused(f"unexpected hash (declared v2 modified): {m}")

    def test_undeclared_change_to_a_v1_file_is_refused(self):
        p = self.unchanged_path()
        with open(self.tmp / p, "ab") as f:
            f.write(b"\n")
        self.refused(f"undeclared change to a v1 file: {p}")

    def test_undeclared_new_files_in_scope_are_refused(self):
        for p in ("src/sabpuja_kundali/extra.py", "report/phase1/extra.json", "prototype/kundali_prototype/static/x.js",
                  "preview/extra.sh", "tests/extra_test.py", "data/ephemeris/extra.se1", "examples/extra.json"):
            with self.subTest(p=p):
                (self.tmp / p).parent.mkdir(parents=True, exist_ok=True)
                (self.tmp / p).write_text("x")
                self.refused(f"undeclared file in v1 scope: {p}")
                (self.tmp / p).unlink()

    def test_symlink_in_place_of_a_file_is_refused(self):
        p = self.unchanged_path()
        target = self.tmp / "elsewhere"
        shutil.copyfile(self.tmp / p, target)
        (self.tmp / p).unlink()
        os.symlink(target, self.tmp / p)
        self.refused(f"missing: {p}")


class ExactCommitTest(unittest.TestCase):
    def setUp(self):
        self.v1_bytes, self.v1, self.v2_bytes, self.v2 = _committed()

    def test_tampered_entries_fail_against_git_objects(self):
        a = next(iter(self.v2["added"]))
        doc = copy.deepcopy(self.v2)
        doc["added"][a]["sha256"] = "1" * 64
        with self.assertRaisesRegex(IdentityError, f"v2 added hash differs from PR #61 git object: {a}"):
            iv.verify_git(REPO, self.v1, doc)
        m = next(iter(self.v2["modified"]))
        doc = copy.deepcopy(self.v2)
        doc["modified"][m]["v2_git_blob"] = "2" * 40
        with self.assertRaisesRegex(IdentityError, f"v2 modified hash differs from PR #61 git object: {m}"):
            iv.verify_git(REPO, self.v1, doc)

    def test_dropping_a_declared_path_fails_the_side_diff(self):
        doc = copy.deepcopy(self.v2)
        doc["added"].pop(next(iter(doc["added"])))
        with self.assertRaisesRegex(IdentityError, "side diff differs"):
            iv.verify_git(REPO, self.v1, doc)

    def test_not_a_git_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv.verify_git(Path(tmp), self.v1, self.v2)


if __name__ == "__main__":
    unittest.main()
