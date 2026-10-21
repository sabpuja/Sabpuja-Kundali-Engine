"""Strict fixture schema, dummy labelling and fixture-set index integrity."""
from pathlib import Path
import copy
import json
import shutil
import tempfile
import unittest

from ..harness.schema import load_fixture_set, validate_fixture
from .helpers import DUMMY_DIR, dummy_fixture, load_json, write_json


class FixtureSchema(unittest.TestCase):
    def setUp(self):
        self.fixture = dummy_fixture()

    def errors(self, mutate):
        fixture = copy.deepcopy(self.fixture)
        mutate(fixture)
        return validate_fixture(fixture)

    def test_committed_dummies_are_valid_and_labelled(self):
        for name in sorted(load_json(DUMMY_DIR / "INDEX.json")["fixtures"]):
            fixture = load_json(DUMMY_DIR / name)
            with self.subTest(name=name):
                self.assertEqual(validate_fixture(fixture), [])
                self.assertTrue(fixture["fixture_id"].startswith("DUMMY-"))
                self.assertIs(fixture["synthetic"], True)
                self.assertIs(fixture["dummy"], True)
                self.assertIs(fixture["reference_verified"], False)
                self.assertIs(fixture["accuracy_claim"], False)
                for ref in fixture["references"]:
                    self.assertIn("FAKE-SOURCE-DO-NOT-USE", ref["source_id"])

    def test_no_real_golden_ids_in_dummy_set(self):
        names = [p.name for p in DUMMY_DIR.glob("*.json")]
        self.assertFalse([n for n in names if n.startswith(("GC-", "TR-", "TZ-"))])

    def test_unknown_and_missing_keys(self):
        self.assertTrue(self.errors(lambda f: f.update(extra=1)))
        self.assertTrue(self.errors(lambda f: f.pop("limitations")))
        self.assertTrue(self.errors(lambda f: f["input"].update(place_name="x")))
        self.assertTrue(self.errors(lambda f: f["references"][0].pop("raw_output_sha256")))

    def test_dummy_flags_cannot_be_inconsistent(self):
        self.assertTrue(self.errors(lambda f: f.update(accuracy_claim=True)))
        self.assertTrue(self.errors(lambda f: f.update(reference_verified=True)))
        self.assertTrue(self.errors(lambda f: f.update(dummy=False)))  # DUMMY id reserved
        self.assertTrue(self.errors(lambda f: f.update(fixture_id="GC-01")))  # dummy needs DUMMY id
        self.assertTrue(self.errors(lambda f: f.update(synthetic=False)))
        self.assertTrue(self.errors(lambda f: f.update(dummy="false")))

    def test_accuracy_claim_needs_verified_non_dummy(self):
        errors = self.errors(lambda f: f.update(fixture_id="GC-99", dummy=False, accuracy_claim=True))
        self.assertIn("accuracy_claim requires dummy false and reference_verified true", errors)

    def test_types_and_ranges(self):
        self.assertTrue(self.errors(lambda f: f["input"].update(latitude=True)))
        self.assertTrue(self.errors(lambda f: f["input"].update(longitude=float("nan"))))
        self.assertTrue(self.errors(lambda f: f["expected"]["sidereal_longitude_deg"].update(sun=360.0)))
        self.assertTrue(self.errors(lambda f: f["expected"]["sidereal_longitude_deg"].update(pluto=1.0)))
        self.assertTrue(self.errors(lambda f: f["references"][0].update(raw_output_sha256="ABC")))
        self.assertTrue(self.errors(lambda f: f.update(fixture_revision=0)))
        self.assertTrue(self.errors(lambda f: f.update(fixture_id="XX-01")))
        self.assertTrue(self.errors(lambda f: f["tolerance_ids"].update(speed="T-SID")))
        self.assertTrue(self.errors(lambda f: f["method_signature"].update(sidereal_bits="0")))
        self.assertEqual(validate_fixture([]), ["fixture: must be an object"])


class FixtureIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.dir = self.tmp / "fx"
        shutil.copytree(DUMMY_DIR, self.dir)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_committed_index_matches_bytes_and_revisions(self):
        records, per_file, set_errors = load_fixture_set(DUMMY_DIR)
        self.assertEqual(set_errors, [])
        self.assertEqual(len(records), 4)
        self.assertTrue(all(errors == [] for errors in per_file.values()), per_file)

    def test_changed_fixture_bytes_are_a_hash_mismatch(self):
        path = self.dir / "DUMMY-01.json"
        path.write_text(path.read_text(encoding="utf-8").replace("111.111111", "111.111112"), encoding="utf-8")
        _, per_file, _ = load_fixture_set(self.dir)
        self.assertIn("FIXTURE_HASH_MISMATCH", per_file["DUMMY-01.json"])

    def test_revision_mismatch(self):
        index = load_json(self.dir / "INDEX.json")
        index["fixtures"]["DUMMY-02.json"]["revision"] = 2
        write_json(self.dir / "INDEX.json", index)
        _, per_file, _ = load_fixture_set(self.dir)
        self.assertEqual(per_file["DUMMY-02.json"], ["FIXTURE_REVISION_MISMATCH"])

    def test_unindexed_missing_and_invalid_files(self):
        (self.dir / "DUMMY-09.json").write_text("{}", encoding="utf-8")
        (self.dir / "DUMMY-03.json").unlink()
        (self.dir / "DUMMY-04.json").write_text("not json", encoding="utf-8")
        records, per_file, set_errors = load_fixture_set(self.dir)
        self.assertEqual(set_errors, ["DUMMY-09.json: present on disk but not in INDEX.json"])
        self.assertEqual(per_file["DUMMY-03.json"], ["FIXTURE_FILE_MISSING"])
        self.assertIn("FIXTURE_NOT_JSON", per_file["DUMMY-04.json"])

    def test_schema_errors_are_reported_per_file(self):
        fixture = load_json(self.dir / "DUMMY-01.json")
        fixture["accuracy_claim"] = True
        index = load_json(self.dir / "INDEX.json")
        index["fixtures"]["DUMMY-01.json"]["sha256"] = write_json(self.dir / "DUMMY-01.json", fixture)
        write_json(self.dir / "INDEX.json", index)
        _, per_file, _ = load_fixture_set(self.dir)
        self.assertTrue(any(e.startswith("SCHEMA_INVALID") for e in per_file["DUMMY-01.json"]))

    def test_missing_or_bad_index(self):
        (self.dir / "INDEX.json").write_text(json.dumps({"fixtures": []}), encoding="utf-8")
        self.assertEqual(load_fixture_set(self.dir)[2], ["INDEX.json is not a valid fixture index"])
        (self.dir / "INDEX.json").unlink()
        self.assertEqual(load_fixture_set(self.dir), ([], {}, ["INDEX.json missing in fixture directory"]))


if __name__ == "__main__":
    unittest.main()
