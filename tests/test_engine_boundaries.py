"""engine.calculate classifies unrounded Swiss values (CLAUDE-002c, D-05).

A test double stands in for swisseph so chosen near-boundary longitudes reach
the engine; this proves derivation and rendering only, not astronomy.
"""
import json
import math
import sys
import types
import unittest
from pathlib import Path
from unittest import mock

from sabpuja_kundali import engine, provenance

SYNTHETIC = {
    "birth_datetime": "2000-01-01T17:30:00+05:30",
    "timezone": "Asia/Kolkata",
    "latitude": 28.6139,
    "longitude": 77.2090
}
JUST_BELOW_TEN = math.nextafter(10.0, 0.0)
BELOW_360 = math.nextafter(360.0, 0.0)
FIXTURE = {
    "sun": 29.999999996,
    "moon": 20.0,
    "mars": 359.999999996,
    "mercury": 56.666666666666664,
    "jupiter": 226.66666666666666,
    "venus": 0.0,
    "saturn": BELOW_360,
    "rahu_mean": JUST_BELOW_TEN,
}
LAGNA = math.nextafter(330.0, 0.0)


def fake_swisseph(longitudes, lagna):
    swe = types.ModuleType("swisseph")
    bodies = list(longitudes)
    for number, name in enumerate(bodies):
        setattr(swe, {"rahu_mean": "MEAN_NODE"}.get(name, name.upper()), number)
    swe.FLG_SWIEPH, swe.FLG_SIDEREAL, swe.SIDM_LAHIRI, swe.DELTAT_AUTOMATIC = 2, 64 * 1024, 1, -1e-10
    # Gate 3C: the engine refuses any other library version before computing.
    swe.version = engine.REQUIRED_SWISS_LIBRARY_VERSION
    swe.Error = type("Error", (Exception,), {})
    swe.julday = lambda *args: 2451545.0
    swe.set_ephe_path = swe.set_sid_mode = swe.set_delta_t_userdef = lambda *args: None
    swe.calc_ut = lambda jd, body, flags: ((longitudes[bodies[body]], 0.0, 1.0, 0.0, 0.0, 0.0), flags)
    swe.houses_ex = lambda jd, lat, lon, hsys, flags: ((0.0,) * 12, (lagna,) + (0.0,) * 9)
    return swe


def run(longitudes=FIXTURE, lagna=LAGNA):
    with mock.patch.dict(sys.modules, {"swisseph": fake_swisseph(longitudes, lagna)}), \
         mock.patch.object(engine, "verify_ephemeris_dir", return_value=Path("/unused")), \
         mock.patch.object(provenance, "binding_distribution_version",
                           return_value=engine.REQUIRED_BINDING_VERSION):
        return engine.calculate(dict(SYNTHETIC))


class EngineBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.out = run()
        self.planets = self.out["planets"]

    def test_category_follows_raw_value_not_display(self):
        sun = self.planets["sun"]
        self.assertEqual(sun["longitude_deg"], 30.0)  # display rounds up to the boundary
        self.assertEqual(sun["rashi"], "Mesha")
        self.assertEqual(sun["navamsa_rashi"], "Dhanu")
        self.assertEqual(sun["whole_sign_house"], 3)  # Mesha from Kumbha lagna

    def test_display_never_360(self):
        for name in ("mars", "saturn"):
            with self.subTest(name=name):
                self.assertEqual(self.planets[name]["longitude_deg"], 0.0)
                self.assertEqual(self.planets[name]["rashi"], "Meena")
                self.assertEqual(self.planets[name]["navamsa_rashi"], "Meena")
                self.assertEqual(self.planets[name]["whole_sign_house"], 2)
        for value in [p["longitude_deg"] for p in self.planets.values()] + [self.out["lagna"]["longitude_deg"]]:
            self.assertTrue(0.0 <= value < 360.0 and math.isfinite(value), value)

    def test_moon_nakshatra_from_raw_moon(self):
        self.assertEqual(self.out["moon_nakshatra"], {"index": 1, "name": "Bharani", "pada": 3})

    def test_d9_and_nakshatra_boundary_floats(self):
        self.assertEqual(self.planets["mercury"]["navamsa_rashi"], "Simha")
        self.assertEqual(self.planets["jupiter"]["rashi"], "Vrischika")
        self.assertEqual(self.planets["jupiter"]["navamsa_rashi"], "Vrischika")

    def test_ketu_exactly_opposite_unrounded_rahu(self):
        rahu, ketu = self.planets["rahu_mean"], self.planets["ketu_mean"]
        self.assertEqual(rahu["longitude_deg"], 10.0)
        self.assertEqual(rahu["navamsa_rashi"], "Mithuna")
        self.assertEqual(ketu["longitude_deg"], 190.0)
        self.assertEqual(ketu["rashi"], "Tula")
        self.assertEqual(ketu["navamsa_rashi"], "Dhanu")  # 189.99...98 is D9 segment 56
        self.assertEqual(ketu["whole_sign_house"], 9)

    def test_lagna_raw_classification(self):
        self.assertEqual(self.out["lagna"], {"longitude_deg": 330.0, "rashi": "Kumbha", "navamsa_rashi": "Mithuna"})

    def test_schema_keys_unchanged(self):
        # P7 appends one metadata block; the 0.1.0 legacy projection keeps the original keys and order.
        legacy = ["schema_version", "validation_status", "method", "birth", "lagna", "moon_nakshatra", "planets"]
        self.assertEqual(list(self.out), legacy + ["calculation_metadata"])
        self.assertEqual(list(provenance.legacy_projection(self.out)), legacy)
        self.assertEqual(list(self.planets), list(FIXTURE) + ["ketu_mean"])
        for value in self.planets.values():
            self.assertEqual(list(value), ["longitude_deg", "rashi", "navamsa_rashi", "whole_sign_house"])
        json.dumps(self.out, allow_nan=False)

    def test_ketu_wraps_through_360(self):
        out = run({**FIXTURE, "rahu_mean": 180.0}, lagna=0.0)
        self.assertEqual(out["planets"]["ketu_mean"]["longitude_deg"], 0.0)
        self.assertEqual(out["planets"]["ketu_mean"]["rashi"], "Mesha")
        out = run({**FIXTURE, "rahu_mean": math.nextafter(180.0, 0.0)}, lagna=0.0)
        ketu = out["planets"]["ketu_mean"]
        self.assertEqual(ketu["longitude_deg"], 0.0)
        self.assertEqual((ketu["rashi"], ketu["navamsa_rashi"], ketu["whole_sign_house"]), ("Meena", "Meena", 12))


if __name__ == "__main__":
    unittest.main()
