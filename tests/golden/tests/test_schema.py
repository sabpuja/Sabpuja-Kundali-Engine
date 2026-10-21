"""Strict fixture schema, dummy labelling and fixture-set index integrity."""
from pathlib import Path
import copy
import hashlib
import json
import shutil
import tempfile
import unittest

from ..harness.schema import is_finite_number, load_fixture_set, strict_loads, validate_fixture
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
        self.assertTrue(per_file["DUMMY-04.json"][-1].startswith("FIXTURE_NOT_JSON"))

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


class IndexPathSafety(unittest.TestCase):
    """WP1-02: INDEX.json keys can never reach a file outside the fixture directory."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.dir = self.tmp / "fx"
        shutil.copytree(DUMMY_DIR, self.dir)
        self.outside = self.tmp / "outside.json"
        self.outside.write_text(json.dumps(dummy_fixture()), encoding="utf-8")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def add_entry(self, key):
        index = load_json(self.dir / "INDEX.json")
        index["fixtures"][key] = {"revision": 1, "sha256": "0" * 64}
        write_json(self.dir / "INDEX.json", index)

    def load_recording_reads(self):
        from unittest import mock
        reads = []
        real_text, real_bytes = Path.read_text, Path.read_bytes

        def text(path, *a, **k):
            reads.append(path.resolve())
            return real_text(path, *a, **k)

        def data(path, *a, **k):
            reads.append(path.resolve())
            return real_bytes(path, *a, **k)
        with mock.patch.object(Path, "read_text", text), mock.patch.object(Path, "read_bytes", data):
            result = load_fixture_set(self.dir)
        return result, reads

    def test_traversal_and_absolute_keys_are_rejected_unread(self):
        for key in ("../outside.json", str(self.outside), "sub/DUMMY-05.json", "DUMMY-05.JSON", "x.json", ""):
            with self.subTest(key=key):
                shutil.copyfile(DUMMY_DIR / "INDEX.json", self.dir / "INDEX.json")
                self.add_entry(key)
                (records, per_file, _), reads = self.load_recording_reads()
                self.assertNotIn(self.outside.resolve(), reads)
                invalid = [f for f, errors in per_file.items()
                           if errors == ["FIXTURE_PATH_INVALID: not a fixture file name"]]
                self.assertEqual(len(invalid), 1)
                self.assertTrue(invalid[0].startswith("INDEX entry "))
                self.assertNotIn(key or "\0", json.dumps(per_file))
                self.assertEqual(len(records), 5)

    def test_symlink_escape_is_rejected_unread(self):
        (self.dir / "DUMMY-05.json").symlink_to(self.outside)
        self.add_entry("DUMMY-05.json")
        (_, per_file, _), reads = self.load_recording_reads()
        self.assertEqual(per_file["DUMMY-05.json"], ["FIXTURE_PATH_INVALID: symlink or outside the fixture directory"])
        self.assertNotIn(self.outside.resolve(), reads)

    def test_valid_indexed_file_still_loads(self):
        (_, per_file, set_errors), _ = self.load_recording_reads()
        self.assertEqual(set_errors, [])
        self.assertEqual(per_file["DUMMY-01.json"], [])

    def test_unindexed_odd_name_is_not_echoed(self):
        (self.dir / "secret-name.json").write_text("{}", encoding="utf-8")
        _, _, set_errors = load_fixture_set(self.dir)
        self.assertEqual(set_errors, ["a file with a non-fixture name: present on disk but not in INDEX.json"])

    def test_file_name_must_match_fixture_id(self):
        shutil.copyfile(self.dir / "DUMMY-01.json", self.dir / "DUMMY-05.json")
        index = load_json(self.dir / "INDEX.json")
        index["fixtures"]["DUMMY-05.json"] = dict(index["fixtures"]["DUMMY-01.json"])
        write_json(self.dir / "INDEX.json", index)
        _, per_file, _ = load_fixture_set(self.dir)
        self.assertEqual(per_file["DUMMY-05.json"], ["FIXTURE_ID_MISMATCH: file name differs from fixture_id"])


class StrictNumbers(unittest.TestCase):
    """Hardening: special or out-of-range JSON numbers are BLOCKED, never a traceback."""

    def test_strict_loads_rejects_special_constants_and_overflow(self):
        for text in ('{"a": NaN}', '{"a": Infinity}', '{"a": -Infinity}', '{"a": 1e400}', '{"a": -1e400}'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    strict_loads(text)
        self.assertEqual(strict_loads('{"a": 0, "b": 1.5e3}'), {"a": 0, "b": 1500.0})

    def test_is_finite_number(self):
        for value in (0, 0.0, 1, 2.5, -3):
            self.assertTrue(is_finite_number(value), value)
        for value in (True, False, None, "1", float("nan"), float("inf"), -float("inf"), 10 ** 400):
            self.assertFalse(is_finite_number(value), value)

    def test_special_numbers_in_a_fixture_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx = Path(tmp) / "fx"
            shutil.copytree(DUMMY_DIR, fx)
            index = load_json(fx / "INDEX.json")
            original = (fx / "DUMMY-01.json").read_text(encoding="utf-8")
            for literal in ("NaN", "Infinity", "-Infinity", "1e400", "1" + "0" * 400):
                with self.subTest(literal=literal):
                    text = original.replace('"latitude": 11.111', f'"latitude": {literal}')
                    (fx / "DUMMY-01.json").write_text(text, encoding="utf-8")
                    index["fixtures"]["DUMMY-01.json"]["sha256"] = hashlib.sha256(text.encode()).hexdigest()
                    write_json(fx / "INDEX.json", index)
                    _, per_file, _ = load_fixture_set(fx)
                    expected = ("SCHEMA_INVALID: input: latitude and longitude must be finite numbers"
                                if literal.startswith("1000") else
                                "FIXTURE_NOT_JSON: invalid JSON, NaN/Infinity or out-of-range number")
                    self.assertEqual(per_file["DUMMY-01.json"], [expected])  # fixed text; the value is never echoed

    def test_huge_integer_values_are_schema_errors(self):
        fixture = dummy_fixture()
        fixture["input"]["latitude"] = 10 ** 400
        fixture["expected"]["sidereal_longitude_deg"]["sun"] = 10 ** 400
        errors = validate_fixture(fixture)
        self.assertIn("input: latitude and longitude must be finite numbers", errors)
        self.assertIn("expected.sidereal_longitude_deg.sun: must be null or in [0, 360)", errors)

    def test_non_dummy_reference_class_must_be_known(self):
        fixture = dummy_fixture()
        fixture.update(fixture_id="GC-99", dummy=False)
        self.assertIn("references[0].source_class: must be one of ['I-code', 'I-data', 'I-pub', 'D', 'M']",
                      validate_fixture(fixture))
