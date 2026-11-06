"""PAN-QA-08 v7 identity overlay: fail-closed controls (KUN-PAN-M2-NAMES-001).

Positive controls: the committed v7 manifest is the pinned one and declares exactly the authorized report
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
from . import identity_v6 as iv6
from . import identity_v7 as iv7
from .identity_v2 import IdentityError

RECORD = iv7.RECORD
PREMIUM = "report/phase1/premium_report.py"
EXT = "report/phase1/panchanga_report.py"
NAMES = "report/phase1/panchanga_names.json"
M1_CAT = "report/phase1/report_panchanga_i18n.json"
STD_CAT = "report/phase1/report_i18n.json"
UI = "prototype/kundali_prototype/static/i18n.json"
ENGINE = "src/sabpuja_kundali/provenance.py"
M1_PREFIX = "src/sabpuja_kundali/panchanga/"


def _committed():
    v1, v2, v3, v4, v5, v6 = iv6.load_committed(REPO)
    v6_bytes = (REPO / iv6.V6_PATH).read_bytes()
    v7_bytes = (REPO / iv7.V7_PATH).read_bytes()
    return v1, v2, v3, v4, v5, v6, v6_bytes, v7_bytes, iv7.load_v7(v7_bytes, v1, v2, v3, v4, v5, v6, v6_bytes)


class ManifestStructureTest(unittest.TestCase):
    def setUp(self):
        (self.v1, self.v2, self.v3, self.v4, self.v5, self.v6, self.v6_bytes, self.v7_bytes,
         self.v7) = _committed()

    def bad(self, mutate, needle):
        doc = copy.deepcopy(self.v7)
        mutate(doc)
        with self.assertRaises(IdentityError) as ctx:
            iv7.validate_v7(doc, self.v1, self.v2, self.v3, self.v4, self.v5, self.v6, self.v6_bytes)
        self.assertIn(needle, str(ctx.exception))

    def test_committed_manifest_is_the_pinned_one(self):
        self.assertEqual(iv2.sha256(self.v7_bytes), iv7.V7_SHA256)
        self.assertEqual(tuple(self.v7["modified"]), iv7.AUTHORIZED_MODIFIED)
        self.assertEqual(tuple(self.v7["added"]), iv7.AUTHORIZED_ADDED)
        self.assertEqual(self.v7["v6_manifest"]["sha256"], iv6.V6_SHA256)
        declared = list(self.v7["modified"]) + list(self.v7["added"])
        self.assertTrue(all(p.startswith("report/phase1/") for p in declared), "report paths only")
        self.assertFalse({STD_CAT, M1_CAT} & set(declared), "the approved and M1 catalogs are not declared")
        self.assertFalse(any(p.startswith(("src/", "data/", "preview/", "prototype/")) for p in declared))

    def test_wrong_pin_or_json_is_refused(self):
        args = (self.v1, self.v2, self.v3, self.v4, self.v5, self.v6, self.v6_bytes)
        with self.assertRaisesRegex(IdentityError, "pinned SHA-256"):
            iv7.load_v7(self.v7_bytes + b" ", *args)
        with self.assertRaisesRegex(IdentityError, "not valid JSON"):
            iv7.load_v7(b"{", *args, expected_sha=iv2.sha256(b"{"))

    def test_structural_defects_are_refused(self):
        self.bad(lambda d: d.update(extra=1), "keys differ")
        self.bad(lambda d: d.update(task="KUN-OTHER"), "task wrong")
        self.bad(lambda d: d.update(note=""), "note missing")
        self.bad(lambda d: d["v6_manifest"].update(sha256="1" * 64), "does not bind")
        self.bad(lambda d: d["v6_manifest"].update(base_commit="0" * 40), "does not bind")
        self.bad(lambda d: d["counts"].update(added=1), "counts wrong")
        self.bad(lambda d: d["modified"][PREMIUM].update(before_sha256="1" * 64), "before_sha256 differs")
        self.bad(lambda d: d["modified"][EXT].update(v7_sha256=d["modified"][EXT]["before_sha256"]),
                 "declares no change")
        self.bad(lambda d: d["modified"][PREMIUM].update(v7_git_blob="xyz"), "entry malformed")
        self.bad(lambda d: d["added"][NAMES].update(extra="1" * 64), "entry malformed")

    def test_unauthorized_paths_are_refused(self):
        def add(d, path, where):
            d[where][path] = ({"before_sha256": "1" * 64, "v7_sha256": "2" * 64, "v7_git_blob": "3" * 40}
                              if where == "modified" else {"sha256": "1" * 64, "git_blob": "2" * 40})
            d["counts"][where] += 1
        for path in (STD_CAT, M1_CAT, UI, ENGINE, M1_PREFIX + "rules.py", "pyproject.toml"):
            with self.subTest(path):
                self.bad(lambda d: add(d, path, "modified"), "modified paths differ from the authorized")
        self.bad(lambda d: add(d, "report/phase1/tests/test_zz.py", "added"), "added paths differ")

        def drop(d):
            d["added"].pop(NAMES)
            d["counts"]["added"] -= 1
        self.bad(drop, "added paths differ")


class TreeVerificationTest(unittest.TestCase):
    """The v1 to v6 + v7 check on a private copy of the tree of a8c3108, the audited v7 commit.

    Before KUN-PAN-RPT-002 this copied HEAD. HEAD now carries the v9 overlay (two v7 report files modified),
    which v7 alone must reject (test_v9_tree_is_rejected_by_v7_alone); the working tree is checked through v9."""

    @classmethod
    def setUpClass(cls):
        cls.v1, cls.v2, cls.v3, cls.v4, cls.v5, cls.v6, _, _, cls.v7 = _committed()
        from . import identity_v8 as iv8
        cls.commit = iv8.BASE_COMMIT
        out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", cls.commit],
                             capture_output=True, check=True).stdout
        prior = iv7.v6_expectations(cls.v1, cls.v2, cls.v3, cls.v4, cls.v5, cls.v6)
        cls.paths = [p for p in out.decode().split("\0")
                     if p and (iv2.in_scope(p) or p in prior or p.startswith(iv7.PACKET_PREFIX))]
        cls.blobs = iv2.Git(REPO).blobs(cls.commit, cls.paths)
        cls.base = iv2.Git(REPO).blobs(iv7.BASE_COMMIT, list(iv7.AUTHORIZED_MODIFIED))

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pan-qa08-v7-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        for p in self.paths:
            (self.tmp / p).parent.mkdir(parents=True, exist_ok=True)
            (self.tmp / p).write_bytes(self.blobs[p])

    def verify(self):
        return iv7.verify_tree(self.tmp, self.v1, self.v2, self.v3, self.v4, self.v5, self.v6, self.v7)

    def refused(self, needle):
        with self.assertRaises(IdentityError) as ctx:
            self.verify()
        self.assertIn(needle, str(ctx.exception))

    def test_pristine_copy_passes(self):
        self.assertEqual(self.verify(), {"v1_unchanged": 209, "v5_packet": 42, "v5_record": 1, "v6_modified": 2,
                                         "v6_added": 18, "v7_modified": 2, "v7_added": 5})

    def test_v9_tree_is_rejected_by_v7_alone(self):
        from . import identity_v9 as iv9
        head = iv2.Git(REPO).blobs("HEAD", list(iv9.AUTHORIZED_MODIFIED))
        (self.tmp / EXT).write_bytes(head[EXT])
        self.refused(f"unexpected hash (declared v7 modified): {EXT}")

    def test_recording_a_decision_needs_no_new_version(self):
        doc = json.loads(self.blobs[RECORD])
        doc["items"][0]["owner_copy"] = {"status": "PENDING"}
        (self.tmp / RECORD).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(self.verify()["v5_record"], 1)
        doc["items"][0]["title"] = "x"
        (self.tmp / RECORD).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.refused(f"decision record changed outside its decision fields: {RECORD}")

    def test_edits_to_declared_report_files_are_refused(self):
        for p in (PREMIUM, EXT, NAMES, "report/phase1/tests/fixtures/panchanga/s07-noon.json"):
            with self.subTest(p):
                with open(self.tmp / p, "ab") as f:
                    f.write(b"\n")
                label = ("v7 modified" if p in iv7.AUTHORIZED_MODIFIED else
                         "v7 added" if p in iv7.AUTHORIZED_ADDED else "v6 added")
                self.refused(f"unexpected hash (declared {label}): {p}")
                (self.tmp / p).write_bytes(self.blobs[p])

    def test_reverting_or_removing_is_refused(self):
        (self.tmp / EXT).write_bytes(self.base[EXT])
        self.refused(f"unexpected hash (declared v7 modified): {EXT}")
        (self.tmp / EXT).write_bytes(self.blobs[EXT])
        (self.tmp / NAMES).unlink()
        self.refused(f"missing: {NAMES}")

    def test_catalogs_engine_and_extra_files_are_refused(self):
        for cat in (STD_CAT, M1_CAT):
            with open(self.tmp / cat, "ab") as f:
                f.write(b" ")
            self.refused(cat)
            (self.tmp / cat).write_bytes(self.blobs[cat])
        with open(self.tmp / ENGINE, "ab") as f:
            f.write(b"\n")
        self.refused(f"undeclared change to a v1 file: {ENGINE}")
        (self.tmp / ENGINE).write_bytes(self.blobs[ENGINE])
        p = "report/phase1/panchanga_names_extra.json"
        (self.tmp / p).write_text("{}")
        self.refused(f"undeclared file in v1 scope: {p}")


A8C = "a8c31081dfc631f5a0a960c699aaabc24b05d7fe"   # the audited v7 commit (draft PR #81 head)


class ExactCommitTest(unittest.TestCase):
    def setUp(self):
        self.v1, self.v2, self.v3, self.v4, self.v5, self.v6, _, _, self.v7 = _committed()

    def args(self, v7=None):
        return (REPO, self.v1, self.v2, self.v3, self.v4, self.v5, self.v6, v7 or self.v7)

    def test_tampered_entries_fail_against_git_objects(self):
        doc = copy.deepcopy(self.v7)
        doc["modified"][EXT]["v7_git_blob"] = "1" * 40
        with self.assertRaisesRegex(IdentityError, f"v7 modified hash differs from the committed object: {EXT}"):
            iv7.verify_git_v7(*self.args(doc), commit=A8C)
        doc = copy.deepcopy(self.v7)
        doc["added"][NAMES]["sha256"] = "1" * 64
        with self.assertRaisesRegex(IdentityError, f"v7 added hash differs from the committed object: {NAMES}"):
            iv7.verify_git_v7(*self.args(doc), commit=A8C)

    def test_base_itself_is_not_the_v7_tree(self):
        with self.assertRaisesRegex(IdentityError, "differs from the v7 declaration"):
            iv7.verify_git_v7(*self.args(), commit=iv7.BASE_COMMIT)

    def test_a_commit_without_the_base_in_its_history_is_refused(self):
        with self.assertRaisesRegex(IdentityError, "not an ancestor"):
            iv7.verify_git_v7(*self.args(), commit=iv6.BASE_COMMIT)

    def test_engine_data_preview_panchanga_m1_and_catalogs_are_byte_identical_to_the_base(self):
        """No change under src/, data/, preview/ or prototype/, nor to either report catalog, f26dd10..a8c3108.

        Before KUN-PAN-M2-SUN-001 this compared f26dd10 with HEAD. The v7 tree is now its audited commit a8c3108;
        the later change (one added Panchanga module) is declared and checked by v8 (test_pan_qa08_identity_v8)."""
        from . import identity_v8 as iv8
        out = subprocess.run(["git", "-C", str(REPO), "diff", "--name-only", iv7.BASE_COMMIT, iv8.BASE_COMMIT, "--",
                              "src", "data", "preview", "prototype", "pyproject.toml", STD_CAT, M1_CAT],
                             capture_output=True, check=True, text=True).stdout
        self.assertEqual(out, "")

    def test_not_a_git_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv7.verify_git_v7(Path(tmp), *self.args()[1:])


if __name__ == "__main__":
    unittest.main()
