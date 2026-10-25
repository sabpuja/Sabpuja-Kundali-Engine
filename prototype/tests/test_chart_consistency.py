"""D1 house layout and D9 table rules, checked against the engine JSON."""
import json
import unittest

from sabpuja_kundali.rules import SIGNS
from kundali_prototype import server
from kundali_prototype.places import load_places

from support import SYNTHETIC, EPHE, requires_data

PLACES = load_places()
BODIES = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu_mean", "ketu_mean")


@requires_data
class EngineChartInvariants(unittest.TestCase):
    """What the North Indian view relies on: house h holds sign (lagna + h - 1) mod 12."""

    def charts(self):
        cases = list(SYNTHETIC) + [("in-new-delhi", "2070-10-04", f"{h:02d}:00") for h in range(0, 24, 2)]
        for pid, d, t in cases:
            status, body = server.handle_chart(
                json.dumps({"place_id": pid, "birth_date": d, "birth_time": t}).encode(), PLACES, EPHE)
            self.assertEqual(status, 200, body.get("error"))
            yield (pid, d, t), body["chart"]

    def test_house_sign_matches_planet_rashi(self):
        for case, chart in self.charts():
            lagna = SIGNS.index(chart["lagna"]["rashi"])
            for name in BODIES:
                p = chart["planets"][name]
                with self.subTest(case=case, body=name):
                    self.assertEqual(SIGNS[(lagna + p["whole_sign_house"] - 1) % 12], p["rashi"])

    def test_d9_fields_present_and_no_d9_houses(self):
        for case, chart in self.charts():
            with self.subTest(case=case):
                self.assertIn(chart["lagna"]["navamsa_rashi"], SIGNS)
                for name in BODIES:
                    self.assertIn(chart["planets"][name]["navamsa_rashi"], SIGNS)
                    self.assertNotIn("navamsa_house", chart["planets"][name])

    def test_crowded_house_cases_exist(self):
        crowded = []
        for case, chart in self.charts():
            houses = [chart["planets"][b]["whole_sign_house"] for b in BODIES]
            crowded.append(max(houses.count(h) for h in range(1, 13)))
        self.assertGreaterEqual(max(crowded), 7)


if __name__ == "__main__":
    unittest.main()
