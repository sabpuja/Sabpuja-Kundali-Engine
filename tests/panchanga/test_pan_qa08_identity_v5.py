"""PAN-QA-08 v5 identity overlay: fail-closed controls (KUN-GOV-SIMPLE-001).

Positive controls: the committed v5 manifest is the pinned one and declares exactly the authorized paths; a
pristine copy of the committed tree passes; and recording a decision (changing only the decision fields of the
live register) still passes without a new manifest version. Every other test seeds a defect and requires a
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
from . import identity_v5 as iv5
from .identity_v2 import IdentityError

PKT = iv5.PACKET_PREFIX
RECORD = iv5.RECORD
UI = "prototype/kundali_prototype/static/i18n.json"
PDF_CAT = "report/phase1/report_i18n.json"
GATE = "report/phase1/tests/test_editorial_register.py"
ATTEST = PKT + "OWNER-COPY-ATTESTATION.md"
REG_MD = PKT + "EDITORIAL-ACCEPTANCE-REGISTER.md"
PAGE10 = PKT + "assets/en-hi-page-10.png"


def _committed():
    v1, v2, v3, v4 = iv4.load_committed(REPO)
    v4_bytes = (REPO / iv4.V4_PATH).read_bytes()
    v5_bytes = (REPO / iv5.V5_PATH).read_bytes()
    return v1, v2, v3, v4, v4_bytes, v5_bytes, iv5.load_v5(v5_bytes, v1, v2, v3, v4, v4_bytes)


class ManifestStructureTest(unittest.TestCase):
    def setUp(self):
        self.v1, self.v2, self.v3, self.v4, self.v4_bytes, self.v5_bytes, self.v5 = _committed()

    def bad(self, mutate, needle):
        doc = copy.deepcopy(self.v5)
        mutate(doc)
        with self.assertRaises(IdentityError) as ctx:
            iv5.validate_v5(doc, self.v1, self.v2, self.v3, self.v4, self.v4_bytes)
        self.assertIn(needle, str(ctx.exception))

    def test_committed_manifest_is_the_pinned_one(self):
        self.assertEqual(iv2.sha256(self.v5_bytes), iv5.V5_SHA256)
        self.assertEqual(tuple(self.v5["modified"]), iv5.AUTHORIZED)
        self.assertEqual(self.v5["v4_manifest"]["sha256"], iv4.V4_SHA256)
        self.assertNotIn(RECORD, self.v5["packet"])
        self.assertFalse(any("/signed/" in p for p in self.v5["packet"]), "no signed evidence exists or is needed")
        self.assertFalse(any(p.startswith(("src/", "data/", "preview/")) or p in (UI, PDF_CAT)
                             for p in self.v5["modified"]), "no application, data or catalog path is declared")

    def test_preserved_manifests_are_byte_identical_to_main(self):
        git = iv2.Git(REPO)
        for path, pinned in ((iv2.V1_PATH, iv2.V1_SHA256), (iv2.V2_PATH, iv2.V2_SHA256),
                             (iv3.V3_PATH, iv3.V3_SHA256), (iv4.V4_PATH, iv4.V4_SHA256)):
            with self.subTest(path):
                at_main = git.blobs(iv5.BASE_COMMIT, [path])[path]
                self.assertEqual((REPO / path).read_bytes(), at_main)
                self.assertEqual(iv2.sha256(at_main), pinned)

    def test_pin_json_and_duplicate_keys(self):
        args = (self.v1, self.v2, self.v3, self.v4, self.v4_bytes)
        with self.assertRaisesRegex(IdentityError, "pinned SHA-256"):
            iv5.load_v5(self.v5_bytes + b" ", *args)
        with self.assertRaisesRegex(IdentityError, "not valid JSON"):
            iv5.load_v5(b"{", *args, expected_sha=iv2.sha256(b"{"))
        dup = self.v5_bytes.replace(b'"counts": {', b'"counts": {"packet": 1, ', 1)
        with self.assertRaisesRegex(IdentityError, "duplicate key"):
            iv5.load_v5(dup, *args, expected_sha=iv2.sha256(dup))

    def test_baseline_substitution_is_refused(self):
        for key in ("sha256", "v3_sha256", "v2_sha256", "v1_sha256", "base_commit", "path"):
            with self.subTest(key):
                self.bad(lambda d, k=key: d["v4_manifest"].update({k: "0" * 64}), "does not bind")
        with self.assertRaisesRegex(IdentityError, "does not bind"):
            iv5.validate_v5(copy.deepcopy(self.v5), self.v1, self.v2, self.v3, self.v4, self.v4_bytes + b"\n")

    def test_shape(self):
        self.bad(lambda d: d.pop("record"), "keys differ")
        self.bad(lambda d: d.update(extra=1), "keys differ")
        self.bad(lambda d: d.update(manifest_schema=iv4.SCHEMA), "manifest_schema")
        self.bad(lambda d: d.update(task="KUN-OTHER"), "task")
        self.bad(lambda d: d.update(note=""), "note")
        self.bad(lambda d: d["counts"].update(packet=1), "counts")

    def test_only_the_authorized_paths(self):
        def extra(d, p):
            d["modified"][p] = dict(d["modified"][GATE])
        for p in ("src/sabpuja_kundali/engine.py", UI, PDF_CAT, "tests/panchanga/baseline-hashes.json"):
            with self.subTest(p):
                self.bad(lambda d, p=p: extra(d, p), "authorized")
        self.bad(lambda d: d["modified"].pop(GATE), "authorized")
        self.bad(lambda d: d.update(modified=dict(reversed(list(d["modified"].items())))), "authorized")

    def test_entries(self):
        self.bad(lambda d: d["modified"][GATE].update(before_sha256="0" * 64), "differs from v2 added")
        self.bad(lambda d: d["modified"][REG_MD].update(before_sha256="0" * 64), "differs from v4 modified")
        self.bad(lambda d: d["modified"][ATTEST].update(before_sha256="0" * 64), "differs from v4 packet")
        self.bad(lambda d: d["modified"][GATE].update(v5_sha256=d["modified"][GATE]["before_sha256"]),
                 "declares no change")
        self.bad(lambda d: d["modified"][GATE].update(v5_git_blob="x"), "malformed")

    def test_record_entry(self):
        self.bad(lambda d: d["record"].update(projection_sha256="x"), "record entry malformed")
        self.bad(lambda d: d["record"].update(path=PKT + "other.json"), "record entry malformed")
        self.bad(lambda d: d["record"]["item_decision_fields"].append("developer_correction"), "record entry malformed")
        self.bad(lambda d: d["record"]["top_decision_fields"].append("reviewed_source"), "record entry malformed")
        self.bad(lambda d: d["record"].update(extra=1), "record entry malformed")

    def test_packet_inventory_rules(self):
        self.bad(lambda d: d.update(packet=dict(reversed(list(d["packet"].items())))), "sorted")

        def pin_record(d):
            d["packet"][RECORD] = dict(d["packet"][ATTEST])
            d["packet"] = dict(sorted(d["packet"].items()))
            d["counts"]["packet"] += 1
        self.bad(pin_record, "must not pin the live decision record")

        def signed_sheet(d):
            d["packet"][PKT + "signed/owner-sheet.pdf"] = dict(d["packet"][ATTEST])
            d["packet"] = dict(sorted(d["packet"].items()))
            d["counts"]["packet"] += 1
        self.bad(signed_sheet, "new, unauthorized file")
        for unsafe in (PKT + "../escape.md", "/" + PKT + "x.md", PKT + "a\\b.md", "docs/other/x.md", PKT + "./x.md"):
            with self.subTest(unsafe):
                def traversal(d, u=unsafe):
                    d["packet"][u] = dict(d["packet"][ATTEST])
                    d["packet"] = dict(sorted(d["packet"].items()))
                    d["counts"]["packet"] += 1
                self.bad(traversal, "unsafe or outside the packet")

        def drop(d, p):
            d["packet"].pop(p)
            d["counts"]["packet"] -= 1
        self.bad(lambda d: drop(d, PAGE10), "drops a v4 packet file")
        self.bad(lambda d: drop(d, ATTEST), "missing from the inventory")
        self.bad(lambda d: d["packet"][ATTEST].update(sha256="1" * 64), "disagrees with its modified entry")
        self.bad(lambda d: d["packet"][PAGE10].update(sha256="1" * 64), "without declaring it")


class TreeVerificationTest(unittest.TestCase):
    """The v1 to v4 + v5 check on a private copy of the committed HEAD tree."""

    @classmethod
    def setUpClass(cls):
        cls.v1, cls.v2, cls.v3, cls.v4, _, _, cls.v5 = _committed()
        out = subprocess.run(["git", "-C", str(REPO), "ls-tree", "-r", "-z", "--name-only", "HEAD"],
                             capture_output=True, check=True).stdout
        prior = iv5.v4_expectations(cls.v1, cls.v2, cls.v3, cls.v4)
        cls.paths = [p for p in out.decode().split("\0") if p and (iv2.in_scope(p) or p in prior or p.startswith(PKT))]
        cls.blobs = iv2.Git(REPO).blobs("HEAD", cls.paths)
        cls.main = iv2.Git(REPO).blobs(iv5.BASE_COMMIT, [GATE, REG_MD, ATTEST, RECORD])

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="pan-qa08-v5-"))
        self.addCleanup(shutil.rmtree, self.tmp)
        for p in self.paths:
            (self.tmp / p).parent.mkdir(parents=True, exist_ok=True)
            (self.tmp / p).write_bytes(self.blobs[p])

    def verify(self):
        return iv5.verify_tree(self.tmp, self.v1, self.v2, self.v3, self.v4, self.v5)

    def refused(self, needle):
        with self.assertRaises(IdentityError) as ctx:
            self.verify()
        self.assertIn(needle, str(ctx.exception))

    def record(self):
        return json.loads(self.blobs[RECORD])

    def write_record(self, doc):
        (self.tmp / RECORD).write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_pristine_copy_passes(self):
        self.assertEqual(self.verify()["v1_unchanged"], 209)

    def test_recording_a_decision_needs_no_new_version(self):
        """The point of v5: decision fields change, nothing else, and the same pinned manifest passes."""
        doc = self.record()
        item = next(i for i in doc["items"] if i["id"] == "8")
        item["human_hindi_language"] = {"status": "ACCEPTED", "reviewer": {"name": "Synthetic Reviewer"},
                                        "record": "https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/1"}
        next(i for i in doc["items"] if i["id"] == "2")["human_jyotish_terminology"]["status"] = "REVISED"
        next(i for i in doc["items"] if i["id"] == "13")["owner_copy"] = {"status": "PENDING"}
        doc["customer_release"]["note"] = "a later owner instruction would be recorded here"
        self.write_record(doc)
        self.assertEqual(self.verify()["v5_record"], 1)

    def test_frozen_part_of_the_record_cannot_change(self):
        cases = {
            "reviewed_source": lambda d: d["reviewed_source"].update(commit="0" * 40),
            "rules": lambda d: d["rules"].append("signatures are required again"),
            "developer layer": lambda d: d["items"][0]["developer_correction"].update(note="x"),
            "engineering layer": lambda d: d["items"][0]["engineering_rendering_verification"].update(status="FAIL"),
            "item title": lambda d: d["items"][3].update(title="x"),
            "item removed": lambda d: d["items"].pop(),
            "new top-level key": lambda d: d.update(signed_sheets=[]),
            "new item key": lambda d: d["items"][0].update(owner_signature="x"),
        }
        for name, mutate in cases.items():
            with self.subTest(name):
                doc = self.record()
                mutate(doc)
                self.write_record(doc)
                self.refused(f"decision record changed outside its decision fields: {RECORD}")

    def test_malformed_or_missing_record_is_refused(self):
        (self.tmp / RECORD).write_text("{", encoding="utf-8")
        self.refused("decision record is not valid JSON")
        (self.tmp / RECORD).write_text('{"items": [], "items": [], "customer_release": null}', encoding="utf-8")
        self.refused("duplicate key")
        doc = self.record()
        del doc["items"][0]["owner_copy"]
        self.write_record(doc)
        self.refused("decision record item has an unexpected shape")
        (self.tmp / RECORD).unlink()
        self.refused(f"missing: {RECORD}")
        (self.tmp / RECORD).symlink_to(self.tmp / ATTEST)
        self.refused(f"missing: {RECORD}")

    def test_reverting_to_main_bytes_is_refused(self):
        for p in (GATE, REG_MD, ATTEST):
            with self.subTest(p):
                (self.tmp / p).write_bytes(self.main[p])
                self.refused(p)
                (self.tmp / p).write_bytes(self.blobs[p])
        (self.tmp / RECORD).write_bytes(self.main[RECORD])  # the old rules text requiring signed sheets
        self.refused(f"decision record changed outside its decision fields: {RECORD}")

    def test_catalog_and_application_edits_are_refused(self):
        data = json.loads(self.blobs[UI])
        data["ui"]["d9.footnote"]["hi"] += " "
        (self.tmp / UI).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        self.refused(f"unexpected hash (declared v4 modified): {UI}")
        (self.tmp / UI).write_bytes(self.blobs[UI])
        untouched = next(p for p in sorted(self.v1["files"]) if p.startswith("src/") and p not in self.v2["modified"])
        with open(self.tmp / untouched, "ab") as f:
            f.write(b"\n")
        self.refused(f"undeclared change to a v1 file: {untouched}")

    def test_signed_documents_and_extra_files_are_refused(self):
        (self.tmp / PKT / "signed").mkdir()
        (self.tmp / PKT / "signed/owner.md").write_text("Approve. Signed: someone")
        self.refused(f"undeclared file in the editorial packet: {PKT}signed/owner.md")
        shutil.rmtree(self.tmp / PKT / "signed")
        with open(self.tmp / ATTEST, "a", encoding="utf-8") as f:
            f.write("| Signature | X |\n")
        self.refused(f"unexpected hash (declared v5 modified): {ATTEST}")
        (self.tmp / ATTEST).write_bytes(self.blobs[ATTEST])
        p = "report/phase1/tests/test_zz_extra.py"
        (self.tmp / p).write_text("x")
        self.refused(f"undeclared file in v1 scope: {p}")

    def test_v4_alone_rejects_the_v5_tree(self):
        with self.assertRaises(IdentityError) as ctx:
            iv4.verify_tree(self.tmp, self.v1, self.v2, self.v3, self.v4)
        for p in (GATE, REG_MD, ATTEST, RECORD):
            self.assertIn(p, str(ctx.exception))


class ExactCommitTest(unittest.TestCase):
    def setUp(self):
        self.v1, self.v2, self.v3, self.v4, _, _, self.v5 = _committed()

    def test_tampered_entries_fail_against_git_objects(self):
        doc = copy.deepcopy(self.v5)
        doc["modified"][GATE]["v5_git_blob"] = "1" * 40
        with self.assertRaisesRegex(IdentityError, f"v5 modified hash differs from the committed object: {GATE}"):
            iv5.verify_git_v5(REPO, self.v1, self.v2, self.v3, self.v4, doc)

    def test_main_itself_is_not_the_v5_tree(self):
        with self.assertRaisesRegex(IdentityError, "differs from the v5 declaration"):
            iv5.verify_git_v5(REPO, self.v1, self.v2, self.v3, self.v4, self.v5, commit=iv5.BASE_COMMIT)

    def test_a_commit_without_main_in_its_history_is_refused(self):
        with self.assertRaisesRegex(IdentityError, "not an ancestor"):
            iv5.verify_git_v5(REPO, self.v1, self.v2, self.v3, self.v4, self.v5, commit=iv4.BASE_COMMIT)

    def test_not_a_git_clone_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv5.verify_git_v5(Path(tmp), self.v1, self.v2, self.v3, self.v4, self.v5)
            with self.assertRaisesRegex(IdentityError, "not a git clone"):
                iv5.verify_commit(Path(tmp), "HEAD", self.v1, self.v2, self.v3, self.v4, self.v5)


if __name__ == "__main__":
    unittest.main()
