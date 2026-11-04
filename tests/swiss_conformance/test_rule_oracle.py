"""Kundali category rules: engine rules vs the independent exact oracle (no Swiss data needed).

Rule conformance is reported separately from Swiss numerical conformance.
"""
from fractions import Fraction
import math
import random
import unittest

from sabpuja_kundali import rules

from . import oracle

BELOW_360 = math.nextafter(360.0, 0.0)


def edges():
    """All 108 Pada edges (every Rashi, Nakshatra and D9 edge is one), exact."""
    return [oracle.PADA_SPAN * k for k in range(108)]


def neighbours(edge: Fraction):
    nearest = float(edge)
    yield edge
    yield nearest
    yield math.nextafter(nearest, -math.inf)
    yield math.nextafter(nearest, math.inf)


class OracleByHand(unittest.TestCase):
    def test_rashi(self):
        self.assertEqual(oracle.rashi(0.0), "Mesha")
        self.assertEqual(oracle.rashi(29.999999999), "Mesha")
        self.assertEqual(oracle.rashi(30.0), "Vrishabha")
        self.assertEqual(oracle.rashi(BELOW_360), "Meena")
        self.assertEqual(oracle.rashi(360.0), "Mesha")
        self.assertEqual(oracle.rashi(-1e-12), "Meena")

    def test_nakshatra_pada(self):
        self.assertEqual(oracle.nakshatra(0.0), ("Ashwini", 1))
        self.assertEqual(oracle.nakshatra(20.0), ("Bharani", 3))
        self.assertEqual(oracle.nakshatra(Fraction(40, 3)), ("Bharani", 1))
        self.assertEqual(oracle.nakshatra(BELOW_360), ("Revati", 4))
        self.assertEqual(oracle.nakshatra(Fraction(680, 3) - Fraction(1, 10 ** 12)), ("Anuradha", 4))

    def test_navamsa(self):
        self.assertEqual(oracle.navamsa(0.0), "Mesha")
        self.assertEqual(oracle.navamsa(30.0), "Makara")       # fixed sign Vrishabha starts at Makara
        self.assertEqual(oracle.navamsa(60.0), "Tula")         # dual sign Mithuna starts at Tula
        self.assertEqual(oracle.navamsa(90.0), "Karka")        # movable sign Karka starts at itself
        self.assertEqual(oracle.navamsa(BELOW_360), "Meena")

    def test_houses(self):
        self.assertEqual(oracle.whole_sign_house(5.0, 5.0), 1)
        self.assertEqual(oracle.whole_sign_house(355.0, 5.0), 12)
        self.assertEqual(oracle.whole_sign_house(0.0, BELOW_360), 2)
        self.assertEqual(oracle.d9_house(0.0, 0.0), 1)
        self.assertEqual(oracle.d9_house(Fraction(10, 3), 0.0), 2)
        self.assertEqual(oracle.d9_house(0.0, Fraction(10, 3)), 12)

    def test_boundary_distance(self):
        self.assertEqual(oracle.boundary_distance(Fraction(10, 3)), 0)
        self.assertEqual(oracle.boundary_distance(1.0), 1)
        self.assertEqual(oracle.boundary_distance(359.5, oracle.RASHI_SPAN), Fraction(1, 2))

    def test_rejects_bad_input(self):
        for bad in (math.nan, math.inf, True, "1"):
            with self.assertRaises((TypeError, ValueError)):
                oracle.rashi(bad)

    def test_gregorian_jd(self):
        self.assertEqual(oracle.gregorian_jd(2000, 1, 1, 12), 2451545)
        self.assertEqual(oracle.gregorian_jd(1900, 1, 1), Fraction(4830041, 2))
        self.assertEqual(oracle.gregorian_jd(2000, 3, 1) - oracle.gregorian_jd(2000, 2, 28), 2)  # leap
        self.assertEqual(oracle.gregorian_jd(1900, 3, 1) - oracle.gregorian_jd(1900, 2, 28), 1)  # not leap
        self.assertEqual(oracle.gregorian_jd(2100, 3, 1) - oracle.gregorian_jd(2100, 2, 28), 1)

    def test_gregorian_jd_matches_swiss_julday(self):
        import swisseph as swe
        rng = random.Random(16)
        for _ in range(500):
            y, m, d = rng.randint(1900, 2100), rng.randint(1, 12), rng.randint(1, 28)
            h, mi, s = rng.randint(0, 23), rng.randint(0, 59), rng.randint(0, 59)
            swiss = swe.julday(y, m, d, h + mi / 60 + s / 3600)
            self.assertLessEqual(abs(float(oracle.gregorian_jd(y, m, d, h, mi, s)) - swiss), 1e-9)


class EngineRulesMatchOracle(unittest.TestCase):
    def check(self, value):
        self.assertEqual(rules.sign(value), oracle.rashi(value), value)
        nak = rules.nakshatra(value)
        self.assertEqual((nak["name"], nak["pada"]), oracle.nakshatra(value), value)
        self.assertEqual(rules.navamsa_sign(value), oracle.navamsa(value), value)

    def test_every_edge_and_its_float_neighbours(self):
        for edge in edges():
            for value in neighbours(edge):
                self.check(value)
        for value in (0.0, -0.0, BELOW_360, 360.0, -1e-300, 720.0 + 1e-9, -30.0):
            self.check(value)

    def test_deterministic_random_sweep(self):
        rng = random.Random(20261022)
        for _ in range(20000):
            self.check(rng.uniform(-720.0, 720.0))

    def test_whole_sign_houses_including_wrap(self):
        rng = random.Random(7)
        values = [float(e) for e in edges()] + [rng.uniform(0, 360) for _ in range(3000)] + [BELOW_360, 0.0]
        lagnas = [0.0, BELOW_360, 29.999999999999996, 30.0, 185.25, 359.0]
        for lagna in lagnas:
            for value in values:
                self.assertEqual(rules.whole_sign_house(value, lagna), oracle.whole_sign_house(value, lagna))

    def test_ketu_opposite_unrounded_rahu_classifies_exactly(self):
        # Ketu = Rahu + 180 exactly; a float sum can round onto the next edge, the Fraction cannot.
        rahu = math.nextafter(10.0, 0.0)
        exact = Fraction(rahu) + 180
        self.assertEqual(rules.navamsa_sign(exact), oracle.navamsa(exact))
        self.assertEqual(oracle.nakshatra(exact), ("Swati", 1))
        self.assertEqual(oracle.nakshatra(rahu + 180.0), ("Swati", 2))  # the float sum rounds onto the 190 deg edge


if __name__ == "__main__":
    unittest.main()
