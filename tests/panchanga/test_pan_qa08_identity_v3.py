"""PAN-QA-08 v3 identity overlay: fail-closed controls (KUN-I18N-INT-001A).

Positive controls: the committed v3 manifest is the pinned one, and a pristine copy of the
tree passes. Every other test seeds one or more defects and requires a refusal. No
scientific tolerance, ephemeris or chart value is read or changed here.
"""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from .common import REPO
from . import identity_v2 as iv2
from . import identity_v3 as iv3
from .identity_v2 import IdentityError

SERVER = "prototype/kundali_prototype/server.py"
NEW_TEST = "prototype/tests/test_report_slot_release.py"


def _committed():
    v1, v2 = iv2.load_committed(REPO)
    v2_bytes = (REPO / iv2.V2_PATH).read_bytes()
    v3_bytes = (REPO / iv3.V3_PATH).read_bytes()
    return v1, v2, v2_bytes, v3_bytes, iv3.load_v3(v3_bytes, v1, v2, v2_bytes)


class ManifestStructureTest(unittest.TestCase):
    def setUp(self):
        self.v1, self.v2, self.v2_bytes, self.v3_bytes, self.v3 = _committed()

    def bad(self, mutate, needle):
        doc = copy.deepcopy(self.v3)
        mutate(doc)
        with self.assertRaises(IdentityError) as ctx:
            iv3.validate_v3(doc, self.v1, self.v2, self.v2_bytes)
        self.assertIn(needle, str(ctx.exception))

    def test_committed_manifest_is_the_pinned_one(self):
        self.assertEqual(iv2.sha256(self.v3_bytes), iv3.V3_SHA256)
        self.assertEqual(list(self.v3["modified"]), [SERVER])
        self.assertEqual(list(self.v3["added"]), [NEW_TEST])
        self.assertEqual(self.v3["v2_manifest"]["sha256"], iv2.V2_SHA256)
        self.assertEqual(self.v3["v2_manifest"]["v1_sha256"], iv2.V1_SHA256)
        self.assertEqual(self.v3["modified"][SERVER]["v2_sha256"], self.v2["modified"][SERVER]["v2_sha256"])

    def test_pin_json_and_duplicate_keys(self):
        with self.assertRaisesRegex(IdentityError, "pinned SHA-256"):
            iv3.load_v3(self.v3_bytes + b" ", self.v1, self.v2, self.v2_bytes)
        with self.assertRaisesRegex(IdentityError, "not valid JSON"):
            iv3.load_v3(b"{", self.v1, self.v2, self.v2_bytes, expected_sha=iv2.sha256(b"{"))
        dup = self.v3_bytes.replace(b'"counts": {', b'"counts": {"added": 1, ', 1)
        with self.assertRaisesRegex(IdentityError, "duplicate key"):
            iv3.load_v3(dup, self.v1, self.v2, self.v2_bytes, expected_sha=iv2.sha256(dup))

    def test_v2_substitution_is_refused(self):
        self.bad(lambda d: d["v2_manifest"].update(sha256="0" * 64), "does not bind")
        self.bad(lambda d: d["v2_manifest"].update(v1_sha256="0" * 64), "does not bind")
        self.bad(lambda d: d["v2_manifest"].update(base_commit="0" * 40), "does not bind")
        forged = self.v2_bytes + b"\n"
        with self.assertRaisesRegex(IdentityError, "does not bind"):
            iv3.validate_v3(copy.deepcopy(self.v3), self.v1, self.v2, forged)

    def test_shape(self):
        self.bad(lambda d: d.pop("task"), "keys differ")
        self.bad(lambda d: d.update(extra=1), "keys differ")
        self.bad(lambda d: d.update(manifest_schema=iv2.SCHEMA), "manifest_schema")
        self.bad(lambda d: d.update(note=""), "note")
        self.bad(lambda d: d["counts"].update(added=2), "counts")

    def test_only_the_authorized_paths(self):
        def extra_modified(d):
            d["modified"]["prototype/README.md"] = dict(d["modified"][SERVER])
        self.bad(extra_modified, "authorized")

        def extra_added(d):
            d["added"]["prototype/tests/zz_extra.py"] = dict(d["added"][NEW_TEST])
        self.bad(extra_added, "authorized")
        self.bad(lambda d: d["modified"].pop(SERVER), "authorized")
        self.bad(lambda d: d["added"].pop(NEW_TEST), "authorized")

    def test_entries(self):
        self.bad(lambda d: d["modified"][SERVER].update(v2_sha256="0" * 64), "differs from v2")
        self.bad(lambda d: d["modified"][SERVER].update(v3_sha256=d["modified"][SERVER]["v2_sha256"]),
                 "declares no change")
        self.bad(lambda d: d["modified"][SERVER].update(v3_git_blob="x"), "malformed")
        self.bad(lambda d: d["modified"][SERVER].pop("v3_sha256"), "malformed")
        self.bad(lambda d: d["added"][NEW_TEST].update(sha256="0" * 63), "malformed")
        self.bad(lambda d: d["added"][NEW_TEST].update(extra="x"), "malformed")


class TreeVerificationTest(unittest.TestCase):
    """The v2-with-v3 check on a private copy of the tree, taken from the git objects of the audited v3
    commit 85f6a89 (since KUN-I18N-COPY-005 the working tree carries the v4 changes, which identity_v4 and
    its own tests cover)."""

    @classmethod
    def setUpClass(cls):
        cls.v1, cls.v2, _, _, cls.v3 = _committed()
        out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", iv3.V3_CANDIDATE_COMMIT],
                             capture_output=True, check=True).stdout
        tracked = [p for p in out.decode().split("\0") if p]
        cls.paths = [p for p in tracked if iv2.in_scope(p) or p in cls.v2["added"]]
        cls.blobs = iv2.Git(REPO).blobs(iv3.V3_CANDIDATE_COMMIT, cls.paths)

    def restore(self, p):
        (self.tmp / p).write_bytes(self.blobs[p])

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pan-qa08-v3-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        for p in self.paths:
            (self.tmp / p).parent.mkdir(parents=True, exist_ok=True)
            self.restore(p)

    def refused(self, needle):
        with self.assertRaises(IdentityError) as ctx:
            iv3.verify_tree(self.tmp, self.v1, self.v2, self.v3)
        self.assertIn(needle, str(ctx.exception))

    def test_pristine_copy_passes(self):
        self.assertEqual(iv3.verify_tree(self.tmp, self.v1, self.v2, self.v3),
                         {"unchanged": 210, "modified": 12, "added": 55, "v3_modified": 1, "v3_added": 1})

    def test_reverting_the_fix_to_v2_bytes_is_refused(self):
        old = iv2.Git(REPO).blobs(iv2.V2_CANDIDATE_COMMIT, [SERVER])[SERVER]
        (self.tmp / SERVER).write_bytes(old)
        self.refused(f"unexpected hash (declared v3 modified): {SERVER}")

    def test_v2_expectations_still_hold_elsewhere(self):
        other = next(p for p in self.v2["modified"] if p != SERVER)
        with open(self.tmp / other, "ab") as f:
            f.write(b"\n")
        self.refused(f"unexpected hash (declared v2 modified): {other}")
        self.restore(other)
        added = next(iter(self.v2["added"]))
        with open(self.tmp / added, "ab") as f:
            f.write(b"\n")
        self.refused(f"unexpected hash (declared v2 added): {added}")
        self.restore(added)
        unchanged = next(p for p in sorted(self.v1["files"]) if p not in self.v2["modified"])
        with open(self.tmp / unchanged, "ab") as f:
            f.write(b"\n")
        self.refused(f"undeclared change to a v1 file: {unchanged}")

    def test_v3_added_test_must_be_present_and_exact(self):
        with open(self.tmp / NEW_TEST, "ab") as f:
            f.write(b"\n")
        self.refused(f"unexpected hash (declared v3 added): {NEW_TEST}")
        (self.tmp / NEW_TEST).unlink()
        self.refused(f"missing: {NEW_TEST}")

    def test_undeclared_new_file_is_refused(self):
        p = "prototype/kundali_prototype/extra.py"
        (self.tmp / p).write_text("x")
        self.refused(f"undeclared file in v1 scope: {p}")

    def test_v2_alone_rejects_the_v3_tree(self):
        with self.assertRaises(IdentityError) as ctx:
            iv2.verify_tree(self.tmp, self.v1, self.v2)
        self.assertIn(f"unexpected hash (declared v2 modified): {SERVER}", str(ctx.exception))
        self.assertIn(f"undeclared file in v1 scope: {NEW_TEST}", str(ctx.exception))


class ExactCommitTest(unittest.TestCase):
    def setUp(self):
        self.v1, self.v2, _, _, self.v3 = _committed()

    def test_tampered_entries_fail_against_git_objects(self):
        doc = copy.deepcopy(self.v3)
        doc["added"][NEW_TEST]["git_blob"] = "1" * 40
        with self.assertRaisesRegex(IdentityError, f"v3 added hash differs from the committed object: {NEW_TEST}"):
            iv3.verify_git_v3(REPO, self.v1, self.v2, doc, commit=iv3.V3_CANDIDATE_COMMIT)
        doc = copy.deepcopy(self.v3)
        doc["modified"][SERVER]["v3_sha256"] = "2" * 64
        with self.assertRaisesRegex(IdentityError, f"v3 modified hash differs from the committed object: {SERVER}"):
            iv3.verify_git_v3(REPO, self.v1, self.v2, doc, commit=iv3.V3_CANDIDATE_COMMIT)

    def test_v3_holds_at_its_commit_and_at_main(self):
        for commit in (iv3.V3_CANDIDATE_COMMIT, iv3.V3_MAIN_COMMIT):
            self.assertEqual(iv3.verify_git_v3(REPO, self.v1, self.v2, self.v3, commit=commit)["v3_modified"], 1)

    def test_v3_alone_rejects_the_v4_tree(self):
        """KUN-I18N-COPY-005: v3 is preserved, so it must still refuse the copy changes."""
        with self.assertRaisesRegex(IdentityError, "differs from the v3 declaration"):
            iv3.verify_git_v3(REPO, self.v1, self.v2, self.v3, commit="HEAD")

    def test_the_v2_commit_itself_is_not_the_v3_tree(self):
        with self.assertRaisesRegex(IdentityError, "differs from the v3 declaration"):
            iv3.verify_git_v3(REPO, self.v1, self.v2, self.v3, commit=iv2.V2_CANDIDATE_COMMIT)

    def test_not_a_git_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv3.verify_git_v3(Path(tmp), self.v1, self.v2, self.v3)


if __name__ == "__main__":
    unittest.main()
