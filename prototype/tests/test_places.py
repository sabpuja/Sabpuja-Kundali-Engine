"""Birthplace fixture: shape, provenance, pinned zones and D3 policy."""
import hashlib
import json
from importlib import resources
from pathlib import Path
import unittest

from sabpuja_kundali import zone_policy
from sabpuja_kundali.timezones import get_zone
from kundali_prototype import places as places_mod



class PlaceFixture(unittest.TestCase):
    def setUp(self):
        self.places = places_mod.load_places()
        self.raw = json.loads(resources.files("kundali_prototype").joinpath("places.json").read_text("utf-8"))

    def test_india_first_small_curated_list(self):
        countries = [p["country"] for p in self.places.values()]
        self.assertEqual(len(countries), 12)
        self.assertEqual(countries.count("India"), 10)
        self.assertEqual(list(self.places)[:10], [p["id"] for p in self.raw["places"] if p["country"] == "India"])

    def test_every_entry_has_place_region_country_coordinates_zone_and_provenance(self):
        for pid, p in self.places.items():
            with self.subTest(pid):
                for key in ("name", "region", "country", "timezone"):
                    self.assertTrue(p[key].strip())
                self.assertIsInstance(p["latitude"], float)
                self.assertIsInstance(p["longitude"], float)
                prov = p["provenance"]
                self.assertEqual(prov["source"], "geonames")
                self.assertIsInstance(prov["geonames_id"], int)
                self.assertEqual(prov["cross_check"]["source"], "natural_earth")
                self.assertLess(prov["cross_check"]["distance_km"], 10)

    def test_zones_are_pinned_and_geographic(self):
        for pid, p in self.places.items():
            with self.subTest(pid):
                get_zone(p["timezone"])
                self.assertTrue(zone_policy.is_location_based(p["timezone"]))
        self.assertEqual({p["timezone"] for p in self.places.values() if p["country"] == "India"}, {"Asia/Kolkata"})

    def test_sources_are_pinned_by_hash(self):
        src = self.raw["sources"]
        self.assertEqual(src["geonames"]["artifact_sha256"],
                         "24fdaaeaf236f88786dec8c0ab55447f5f7f95ef6c094e79fa9ef74114ea1fe2")
        self.assertEqual(src["natural_earth"]["commit"], "f1890d9f152c896d250a77557a5751a93d494776")
        self.assertIn("not the DATA-01 production gazetteer", self.raw["status"])

    def test_non_india_entries_are_labelled_test_coverage(self):
        for p in self.places.values():
            if p["country"] != "India":
                self.assertIn("Non-India test coverage", p["note"])
        self.assertFalse(places_mod.public_place(self.places["no-tromso"])["in_supported_latitude_band"])

    def test_public_view_has_no_raw_provenance(self):
        view = places_mod.public_place(self.places["in-mumbai"])
        self.assertNotIn("provenance", view)
        self.assertEqual(view["source"], "GeoNames 1275339; Natural Earth cross-check 0.86 km")

    def test_bad_fixtures_fail_closed(self):
        good = self.raw["places"][0]
        cases = {
            "duplicate": [good, good],
            "etc-zone": [dict(good, timezone="Etc/GMT-5")],
            "unknown-zone": [dict(good, timezone="Asia/Atlantis")],
            "int-latitude": [dict(good, latitude=28)],
            "no-provenance": [{k: v for k, v in good.items() if k != "provenance"}],
            "bad-id": [dict(good, id="New Delhi")],
            "empty": [],
        }
        original = places_mod.resources
        for name, rows in cases.items():
            with self.subTest(name):
                text = json.dumps(dict(self.raw, places=rows))

                class Fake:
                    @staticmethod
                    def files(_pkg):
                        class F:
                            def joinpath(self, _n):
                                class R:
                                    def read_text(self, encoding):
                                        return text
                                return R()
                        return F()
                places_mod.resources = Fake
                try:
                    with self.assertRaises(places_mod.PlaceFixtureError):
                        places_mod.load_places()
                finally:
                    places_mod.resources = original

    def test_fixture_hash_is_recorded(self):
        data = resources.files("kundali_prototype").joinpath("places.json").read_bytes()
        # Recorded in prototype/README.md; a fixture change must update both.
        readme = (Path(__file__).resolve().parents[1] / "README.md").read_text("utf-8")
        self.assertIn(hashlib.sha256(data).hexdigest(), readme)


if __name__ == "__main__":
    unittest.main()
