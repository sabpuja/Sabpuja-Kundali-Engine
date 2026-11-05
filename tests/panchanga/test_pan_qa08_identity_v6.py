"""PAN-QA-08 v6 identity overlay: fail-closed controls (KUN-PAN-RPT-001).

Positive controls: the committed v6 manifest is the pinned one and declares exactly the authorized report
paths; a pristine copy of the committed tree passes; and recording a decision in the live register still
passes without a new manifest version. Every other test seeds a defect and requires a refusal. No
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
from . import identity_v5 as iv5
from . import identity_v6 as iv6
from .identity_v2 import IdentityError

RECORD = iv6.RECORD
PREMIUM = "report/phase1/premium_report.py"
EXT = "report/phase1/panchanga_report.py"
STD_CAT = "report/phase1/report_i18n.json"
UI = "prototype/kundali_prototype/static/i18n.json"
M1 = "src/sabpuja_kundali/panchanga/contract.py"


def _committed():
    v1, v2, v3, v4, v5 = iv5.load_committed(REPO)
    v5_bytes = (REPO / iv5.V5_PATH).read_bytes()
    v6_bytes = (REPO / iv6.V6_PATH).read_bytes()
    return v1, v2, v3, v4, v5, v5_bytes, v6_bytes, iv6.load_v6(v6_bytes, v1, v2, v3, v4, v5, v5_bytes)


class ManifestStructureTest(unittest.TestCase):
    def setUp(self):
        self.v1, self.v2, self.v3, self.v4, self.v5, self.v5_bytes, self.v6_bytes, self.v6 = _committed()

    def bad(self, mutate, needle):
        doc = copy.deepcopy(self.v6)
        mutate(doc)
        with self.assertRaises(IdentityError) as ctx:
            iv6.validate_v6(doc, self.v1, self.v2, self.v3, self.v4, self.v5, self.v5_bytes)
        self.assertIn(needle, str(ctx.exception))

    def test_committed_manifest_is_the_pinned_one(self):
        self.assertEqual(iv2.sha256(self.v6_bytes), iv6.V6_SHA256)
        self.assertEqual(tuple(self.v6["modified"]), iv6.AUTHORIZED_MODIFIED)
        self.assertEqual(tuple(self.v6["added"]), iv6.AUTHORIZED_ADDED)
        self.assertEqual(self.v6["v5_manifest"]["sha256"], iv5.V5_SHA256)
        declared = list(self.v6["modified"]) + list(self.v6["added"])
        self.assertTrue(all(p.startswith("report/phase1/") for p in declared), "report paths only")
        self.assertNotIn(STD_CAT, declared, "the approved ten-page catalog is not declared")
        self.assertFalse(any(p.startswith(("src/", "data/", "preview/", "prototype/")) for p in declared))

    def test_wrong_pin_or_json_is_refused(self):
        with self.assertRaisesRegex(IdentityError, "pinned SHA-256"):
            iv6.load_v6(self.v6_bytes + b" ", self.v1, self.v2, self.v3, self.v4, self.v5, self.v5_bytes)
        with self.assertRaisesRegex(IdentityError, "not valid JSON"):
            iv6.load_v6(b"{", self.v1, self.v2, self.v3, self.v4, self.v5, self.v5_bytes,
                        expected_sha=iv2.sha256(b"{"))

    def test_structural_defects_are_refused(self):
        self.bad(lambda d: d.update(extra=1), "keys differ")
        self.bad(lambda d: d.update(task="KUN-OTHER"), "task wrong")
        self.bad(lambda d: d.update(note=""), "note missing")
        self.bad(lambda d: d["v5_manifest"].update(sha256="1" * 64), "does not bind")
        self.bad(lambda d: d["v5_manifest"].update(base_commit="0" * 40), "does not bind")
        self.bad(lambda d: d["counts"].update(added=1), "counts wrong")
        self.bad(lambda d: d["modified"][PREMIUM].update(before_sha256="1" * 64), "before_sha256 differs")
        self.bad(lambda d: d["modified"][PREMIUM].update(v6_sha256=d["modified"][PREMIUM]["before_sha256"]),
                 "declares no change")
        self.bad(lambda d: d["modified"][PREMIUM].update(v6_git_blob="xyz"), "entry malformed")
        self.bad(lambda d: d["added"][EXT].update(extra="1" * 64), "entry malformed")

    def test_unauthorized_paths_are_refused(self):
        def add(d, path, where):
            d[where][path] = ({"before_sha256": "1" * 64, "v6_sha256": "2" * 64, "v6_git_blob": "3" * 40}
                              if where == "modified" else {"sha256": "1" * 64, "git_blob": "2" * 40})
            d["counts"][where] += 1
        for path in (STD_CAT, UI, M1, "pyproject.toml"):
            with self.subTest(path):
                self.bad(lambda d: add(d, path, "modified"), "modified paths differ from the authorized")
        self.bad(lambda d: add(d, "report/phase1/tests/test_zz.py", "added"), "added paths differ")

        def drop(d):
            d["added"].pop(EXT)
            d["counts"]["added"] -= 1
        self.bad(drop, "added paths differ")


class TreeVerificationTest(unittest.TestCase):
    """The v1 to v5 + v6 check on a private copy of the committed HEAD tree."""

    @classmethod
    def setUpClass(cls):
        cls.v1, cls.v2, cls.v3, cls.v4, cls.v5, _, _, cls.v6 = _committed()
        out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", "HEAD"],
                             capture_output=True, check=True).stdout
        prior = iv6.v5_expectations(cls.v1, cls.v2, cls.v3, cls.v4, cls.v5)
        cls.paths = [p for p in out.decode().split("\0")
                     if p and (iv2.in_scope(p) or p in prior or p.startswith(iv6.PACKET_PREFIX))]
        cls.blobs = iv2.Git(REPO).blobs("HEAD", cls.paths)
        cls.base = iv2.Git(REPO).blobs(iv6.BASE_COMMIT, list(iv6.AUTHORIZED_MODIFIED))

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pan-qa08-v6-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        for p in self.paths:
            (self.tmp / p).parent.mkdir(parents=True, exist_ok=True)
            (self.tmp / p).write_bytes(self.blobs[p])

    def verify(self):
        return iv6.verify_tree(self.tmp, self.v1, self.v2, self.v3, self.v4, self.v5, self.v6)

    def refused(self, needle):
        with self.assertRaises(IdentityError) as ctx:
            self.verify()
        self.assertIn(needle, str(ctx.exception))

    def test_pristine_copy_passes(self):
        self.assertEqual(self.verify(), {"v1_unchanged": 209, "v5_modified": 13, "v5_packet": 42,
                                         "v5_record": 1, "v6_modified": 2, "v6_added": 18})

    def test_recording_a_decision_needs_no_new_version(self):
        doc = json.loads(self.blobs[RECORD])
        doc["items"][0]["owner_copy"] = {"status": "PENDING"}
        doc["customer_release"]["note"] = "a later owner instruction would be recorded here"
        (self.tmp / RECORD).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(self.verify()["v5_record"], 1)
        doc["items"][0]["title"] = "x"
        (self.tmp / RECORD).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.refused(f"decision record changed outside its decision fields: {RECORD}")

    def test_edits_to_declared_report_files_are_refused(self):
        for p in (PREMIUM, EXT, "report/phase1/tests/fixtures/panchanga/s07-noon.json"):
            with self.subTest(p):
                with open(self.tmp / p, "ab") as f:
                    f.write(b"\n")
                label = "v6 modified" if p in iv6.AUTHORIZED_MODIFIED else "v6 added"
                self.refused(f"unexpected hash (declared {label}): {p}")
                (self.tmp / p).write_bytes(self.blobs[p])

    def test_reverting_or_removing_is_refused(self):
        (self.tmp / PREMIUM).write_bytes(self.base[PREMIUM])
        self.refused(f"unexpected hash (declared v6 modified): {PREMIUM}")
        (self.tmp / PREMIUM).write_bytes(self.blobs[PREMIUM])
        (self.tmp / EXT).unlink()
        self.refused(f"missing: {EXT}")

    def test_catalog_engine_and_extra_files_are_refused(self):
        with open(self.tmp / STD_CAT, "ab") as f:
            f.write(b" ")
        self.refused(STD_CAT)
        (self.tmp / STD_CAT).write_bytes(self.blobs[STD_CAT])
        with open(self.tmp / M1, "ab") as f:
            f.write(b"\n")
        self.refused(M1)
        (self.tmp / M1).write_bytes(self.blobs[M1])
        p = "report/phase1/tests/fixtures/panchanga/s14-extra.json"
        (self.tmp / p).write_text("{}")
        self.refused(f"undeclared file in v1 scope: {p}")
        (self.tmp / p).unlink()
        q = iv6.PACKET_PREFIX + "signed/owner.md"
        (self.tmp / q).parent.mkdir()
        (self.tmp / q).write_text("x")
        self.refused(f"undeclared file in the editorial packet: {q}")

    def test_v5_alone_rejects_the_v6_tree(self):
        with self.assertRaises(IdentityError) as ctx:
            iv5.verify_tree(self.tmp, self.v1, self.v2, self.v3, self.v4, self.v5)
        for p in iv6.AUTHORIZED_MODIFIED + iv6.AUTHORIZED_ADDED:
            self.assertIn(p, str(ctx.exception))


class ExactCommitTest(unittest.TestCase):
    def setUp(self):
        self.v1, self.v2, self.v3, self.v4, self.v5, _, _, self.v6 = _committed()

    def args(self, v6=None):
        return (REPO, self.v1, self.v2, self.v3, self.v4, self.v5, v6 or self.v6)

    def test_tampered_entries_fail_against_git_objects(self):
        doc = copy.deepcopy(self.v6)
        doc["modified"][PREMIUM]["v6_git_blob"] = "1" * 40
        with self.assertRaisesRegex(IdentityError, f"v6 modified hash differs from the committed object: {PREMIUM}"):
            iv6.verify_git_v6(*self.args(doc))
        doc = copy.deepcopy(self.v6)
        doc["added"][EXT]["sha256"] = "1" * 64
        with self.assertRaisesRegex(IdentityError, f"v6 added hash differs from the committed object: {EXT}"):
            iv6.verify_git_v6(*self.args(doc))

    def test_main_itself_is_not_the_v6_tree(self):
        with self.assertRaisesRegex(IdentityError, "differs from the v6 declaration"):
            iv6.verify_git_v6(*self.args(), commit=iv6.BASE_COMMIT)

    def test_a_commit_without_main_in_its_history_is_refused(self):
        with self.assertRaisesRegex(IdentityError, "not an ancestor"):
            iv6.verify_git_v6(*self.args(), commit=iv5.BASE_COMMIT)

    def test_not_a_git_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv6.verify_git_v6(Path(tmp), self.v1, self.v2, self.v3, self.v4, self.v5, self.v6)
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv6.verify_commit(Path(tmp), "HEAD", self.v1, self.v2, self.v3, self.v4, self.v5, self.v6)


if __name__ == "__main__":
    unittest.main()
