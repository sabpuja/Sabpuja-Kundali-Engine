"""PAN-QA-08 v4 identity overlay: fail-closed controls (KUN-I18N-COPY-005).

Positive controls: the committed v4 manifest is the pinned one and declares exactly the authorized paths, and
a pristine copy of the committed tree passes. Every other test seeds one or more defects and requires a
refusal. No scientific tolerance, ephemeris or chart value is read or changed here.
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
from . import identity_v4 as iv4
from .identity_v2 import IdentityError

PKT = iv4.PACKET_PREFIX
UI = "prototype/kundali_prototype/static/i18n.json"
PDF_CAT = "report/phase1/report_i18n.json"
HTML = "prototype/kundali_prototype/static/index.html"
PINS = "report/phase1/tests/test_premium_name.py"
REGISTER = PKT + "editorial-acceptance-register.json"
SAMPLE_EN = PKT + "assets/sample-en-anonymous.pdf"
PAGE10 = PKT + "assets/en-hi-page-10.png"
ATTEST = PKT + "OWNER-COPY-ATTESTATION.md"
TEST_A = "report/phase1/tests/test_owner_copy_change_a.py"


def _committed():
    v1, v2, v3 = iv3.load_committed(REPO)
    v3_bytes = (REPO / iv3.V3_PATH).read_bytes()
    v4_bytes = (REPO / iv4.V4_PATH).read_bytes()
    return v1, v2, v3, v3_bytes, v4_bytes, iv4.load_v4(v4_bytes, v1, v2, v3, v3_bytes)


class ManifestStructureTest(unittest.TestCase):
    def setUp(self):
        self.v1, self.v2, self.v3, self.v3_bytes, self.v4_bytes, self.v4 = _committed()

    def bad(self, mutate, needle):
        doc = copy.deepcopy(self.v4)
        mutate(doc)
        with self.assertRaises(IdentityError) as ctx:
            iv4.validate_v4(doc, self.v1, self.v2, self.v3, self.v3_bytes)
        self.assertIn(needle, str(ctx.exception))

    def test_committed_manifest_is_the_pinned_one(self):
        self.assertEqual(iv2.sha256(self.v4_bytes), iv4.V4_SHA256)
        self.assertEqual(tuple(self.v4["modified"]), iv4.AUTHORIZED["modified"])
        self.assertEqual(tuple(self.v4["added"]), iv4.AUTHORIZED["added"])
        self.assertEqual(self.v4["v3_manifest"]["sha256"], iv3.V3_SHA256)
        self.assertIn(ATTEST, self.v4["packet"])
        self.assertFalse(any("/signed/" in p for p in self.v4["packet"]), "no signed evidence is pre-approved")

    def test_preserved_manifests_are_byte_identical_to_main(self):
        git = iv2.Git(REPO)
        for path, pinned in ((iv2.V1_PATH, iv2.V1_SHA256), (iv2.V2_PATH, iv2.V2_SHA256), (iv3.V3_PATH, iv3.V3_SHA256)):
            with self.subTest(path):
                at_main = git.blobs(iv4.BASE_COMMIT, [path])[path]
                self.assertEqual((REPO / path).read_bytes(), at_main)
                self.assertEqual(iv2.sha256(at_main), pinned)

    def test_pin_json_and_duplicate_keys(self):
        with self.assertRaisesRegex(IdentityError, "pinned SHA-256"):
            iv4.load_v4(self.v4_bytes + b" ", self.v1, self.v2, self.v3, self.v3_bytes)
        with self.assertRaisesRegex(IdentityError, "not valid JSON"):
            iv4.load_v4(b"{", self.v1, self.v2, self.v3, self.v3_bytes, expected_sha=iv2.sha256(b"{"))
        dup = self.v4_bytes.replace(b'"counts": {', b'"counts": {"added": 2, ', 1)
        with self.assertRaisesRegex(IdentityError, "duplicate key"):
            iv4.load_v4(dup, self.v1, self.v2, self.v3, self.v3_bytes, expected_sha=iv2.sha256(dup))
        dup = self.v4_bytes.replace(b'"packet": {', b'"packet": {"' + ATTEST.encode() + b'": {}, ', 1)
        with self.assertRaisesRegex(IdentityError, "duplicate key"):
            iv4.load_v4(dup, self.v1, self.v2, self.v3, self.v3_bytes, expected_sha=iv2.sha256(dup))

    def test_baseline_substitution_is_refused(self):
        for key in ("sha256", "v2_sha256", "v1_sha256", "base_commit", "path"):
            with self.subTest(key):
                self.bad(lambda d, k=key: d["v3_manifest"].update({k: "0" * 64}), "does not bind")
        with self.assertRaisesRegex(IdentityError, "does not bind"):
            iv4.validate_v4(copy.deepcopy(self.v4), self.v1, self.v2, self.v3, self.v3_bytes + b"\n")
        with self.assertRaisesRegex(IdentityError, "v3 manifest does not match its pinned SHA-256"):
            iv3.load_v3(self.v3_bytes + b"\n", self.v1, self.v2, (REPO / iv2.V2_PATH).read_bytes())

    def test_shape(self):
        self.bad(lambda d: d.pop("packet"), "keys differ")
        self.bad(lambda d: d.update(extra=1), "keys differ")
        self.bad(lambda d: d.update(manifest_schema=iv3.SCHEMA), "manifest_schema")
        self.bad(lambda d: d.update(task="KUN-OTHER"), "task")
        self.bad(lambda d: d.update(note=""), "note")
        self.bad(lambda d: d["counts"].update(packet=1), "counts")

    def test_only_the_authorized_paths(self):
        def extra_modified(d):
            d["modified"]["src/sabpuja_kundali/engine.py"] = dict(d["modified"][UI])
        self.bad(extra_modified, "authorized")

        def extra_added(d):
            d["added"]["prototype/tests/zz_extra.py"] = dict(d["added"][TEST_A])
        self.bad(extra_added, "authorized")
        self.bad(lambda d: d["modified"].pop(REGISTER), "authorized")
        self.bad(lambda d: d["added"].pop(TEST_A), "authorized")

        def reordered(d):
            d["modified"] = dict(reversed(list(d["modified"].items())))
        self.bad(reordered, "authorized")

    def test_entries_and_catalog_hashes(self):
        self.bad(lambda d: d["modified"][UI].update(before_sha256="0" * 64), "differs from v2 added")
        self.bad(lambda d: d["modified"][PDF_CAT].update(before_sha256="0" * 64), "differs from v2 added")
        self.bad(lambda d: d["modified"][HTML].update(before_sha256="0" * 64), "differs from v2 modified")
        self.bad(lambda d: d["modified"][PINS].update(before_sha256="0" * 64), "differs from v1")
        self.bad(lambda d: d["modified"][UI].update(v4_sha256=d["modified"][UI]["before_sha256"]),
                 "declares no change")
        self.bad(lambda d: d["modified"][PDF_CAT].update(v4_git_blob="x"), "malformed")
        self.bad(lambda d: d["modified"][PDF_CAT].pop("v4_sha256"), "malformed")
        self.bad(lambda d: d["added"][TEST_A].update(sha256="0" * 63), "malformed")

    def test_packet_inventory_rules(self):
        self.bad(lambda d: d.update(packet=dict(reversed(list(d["packet"].items())))), "sorted")

        def unauthorized_new(d):
            d["packet"][PKT + "signed/owner-sheet.pdf"] = dict(d["packet"][ATTEST])
            d["packet"] = dict(sorted(d["packet"].items()))
            d["counts"]["packet"] += 1
        self.bad(unauthorized_new, "new, unauthorized file")
        for unsafe in (PKT + "../escape.md", "/" + PKT + "x.md", PKT + "a\\b.md", "docs/other/x.md", PKT + "./x.md"):
            with self.subTest(unsafe):
                def traversal(d, u=unsafe):
                    d["packet"][u] = dict(d["packet"][ATTEST])
                    d["packet"] = dict(sorted(d["packet"].items()))
                    d["counts"]["packet"] += 1
                self.bad(traversal, "unsafe or outside the packet")

        def drop_attestation(d):
            d["packet"].pop(ATTEST)
            d["counts"]["packet"] -= 1
        self.bad(drop_attestation, "missing or not new")

        def drop_v2_file(d):
            d["packet"].pop(PKT + "assets/en-hi-page-01.png")
            d["counts"]["packet"] -= 1
        self.bad(drop_v2_file, "drops a v2-declared file")
        self.bad(lambda d: d["packet"][REGISTER].update(sha256="1" * 64), "disagrees with its modified entry")
        self.bad(lambda d: d["packet"][PKT + "assets/en-hi-page-01.png"].update(sha256="1" * 64),
                 "without declaring it")


class TreeVerificationTest(unittest.TestCase):
    """The v1/v2/v3 + v4 check on a private copy of the committed HEAD tree."""

    @classmethod
    def setUpClass(cls):
        cls.v1, cls.v2, cls.v3, _, _, cls.v4 = _committed()
        out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", "HEAD"],
                             capture_output=True, check=True).stdout
        prior = iv4.prior_expectations(cls.v1, cls.v2, cls.v3)
        cls.paths = [p for p in out.decode().split("\0") if p and (iv2.in_scope(p) or p in prior or p.startswith(PKT))]
        cls.blobs = iv2.Git(REPO).blobs("HEAD", cls.paths)
        cls.main = iv2.Git(REPO).blobs(iv4.BASE_COMMIT, [SAMPLE_EN, PAGE10, UI, PDF_CAT, PINS, REGISTER, HTML])

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pan-qa08-v4-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        for p in self.paths:
            (self.tmp / p).parent.mkdir(parents=True, exist_ok=True)
            (self.tmp / p).write_bytes(self.blobs[p])

    def refused(self, needle):
        with self.assertRaises(IdentityError) as ctx:
            iv4.verify_tree(self.tmp, self.v1, self.v2, self.v3, self.v4)
        self.assertIn(needle, str(ctx.exception))

    def test_pristine_copy_passes(self):
        self.assertEqual(iv4.verify_tree(self.tmp, self.v1, self.v2, self.v3, self.v4)["v1_unchanged"], 209)

    def test_reverting_to_main_bytes_is_refused(self):
        """Stale catalogs, pins, register, HTML fallback or packet assets from 7fc1702."""
        for p in (UI, PDF_CAT, HTML, PINS, REGISTER, SAMPLE_EN, PAGE10):
            with self.subTest(p):
                (self.tmp / p).write_bytes(self.main[p])
                self.refused(f"{p}")
                (self.tmp / p).write_bytes(self.blobs[p])

    def test_catalog_edit_is_refused(self):
        data = json.loads(self.blobs[UI])
        data["ui"]["d9.footnote"]["hi"] = data["ui"]["d9.footnote"]["hi"].replace("चार्ट", "स्वीकृत चार्ट")
        (self.tmp / UI).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.refused(f"unexpected hash (declared v4 modified): {UI}")

    def test_signed_documents_cannot_appear_or_change(self):
        (self.tmp / PKT / "signed").mkdir()
        (self.tmp / PKT / "signed/owner.md").write_text("Approve. Signed: someone")
        self.refused(f"undeclared file in the editorial packet: {PKT}signed/owner.md")
        shutil.rmtree(self.tmp / PKT / "signed")
        with open(self.tmp / ATTEST, "a", encoding="utf-8") as f:
            f.write("| Signature | X |\n")
        self.refused(f"unexpected hash (declared v4 packet): {ATTEST}")
        (self.tmp / ATTEST).unlink()
        self.refused(f"missing: {ATTEST}")

    def test_other_expectations_still_hold(self):
        untouched = next(p for p in sorted(self.v1["files"]) if p not in self.v2["modified"] and p != PINS)
        with open(self.tmp / untouched, "ab") as f:
            f.write(b"\n")
        self.refused(f"undeclared change to a v1 file: {untouched}")
        (self.tmp / untouched).write_bytes(self.blobs[untouched])
        server = "prototype/kundali_prototype/server.py"
        with open(self.tmp / server, "ab") as f:
            f.write(b"\n")
        self.refused(f"unexpected hash (declared v3 modified): {server}")

    def test_undeclared_files_are_refused(self):
        p = "report/phase1/tests/test_zz_extra.py"
        (self.tmp / p).write_text("x")
        self.refused(f"undeclared file in v1 scope: {p}")
        (self.tmp / p).unlink()
        (self.tmp / PKT / "notes.md").write_text("x")
        self.refused(f"undeclared file in the editorial packet: {PKT}notes.md")

    def test_symlink_in_place_of_a_declared_file_is_refused(self):
        (self.tmp / SAMPLE_EN).unlink()
        (self.tmp / SAMPLE_EN).symlink_to(self.tmp / PKT / "assets/sample-hi-anonymous.pdf")
        self.refused(f"missing: {SAMPLE_EN}")

    def test_v3_alone_rejects_the_v4_tree(self):
        with self.assertRaises(IdentityError) as ctx:
            iv3.verify_tree(self.tmp, self.v1, self.v2, self.v3)
        for p in (UI, PDF_CAT, HTML, REGISTER):
            self.assertIn(p, str(ctx.exception))
        self.assertIn(f"undeclared change to a v1 file: {PINS}", str(ctx.exception))


class ExactCommitTest(unittest.TestCase):
    def setUp(self):
        self.v1, self.v2, self.v3, _, _, self.v4 = _committed()

    def test_tampered_entries_fail_against_git_objects(self):
        doc = copy.deepcopy(self.v4)
        doc["added"][TEST_A]["git_blob"] = "1" * 40
        with self.assertRaisesRegex(IdentityError, f"v4 added hash differs from the committed object: {TEST_A}"):
            iv4.verify_git_v4(REPO, self.v1, self.v2, self.v3, doc)
        doc = copy.deepcopy(self.v4)
        doc["modified"][PDF_CAT]["v4_sha256"] = "2" * 64
        with self.assertRaisesRegex(IdentityError, f"v4 modified hash differs from the committed object: {PDF_CAT}"):
            iv4.verify_git_v4(REPO, self.v1, self.v2, self.v3, doc)

    def test_main_itself_is_not_the_v4_tree(self):
        with self.assertRaisesRegex(IdentityError, "differs from the v4 declaration"):
            iv4.verify_git_v4(REPO, self.v1, self.v2, self.v3, self.v4, commit=iv4.BASE_COMMIT)

    def test_a_commit_without_main_in_its_history_is_refused(self):
        with self.assertRaisesRegex(IdentityError, "not an ancestor"):
            iv4.verify_git_v4(REPO, self.v1, self.v2, self.v3, self.v4, commit=iv3.V3_CANDIDATE_COMMIT)

    def test_not_a_git_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv4.verify_git_v4(Path(tmp), self.v1, self.v2, self.v3, self.v4)
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv4.verify_commit(Path(tmp), "HEAD", self.v1, self.v2, self.v3, self.v4)


if __name__ == "__main__":
    unittest.main()
