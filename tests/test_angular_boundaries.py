"""Exact half-open sector boundaries (CLAUDE-002c, audit defect D-05).

Expectations come from boundary_oracle (Fraction arithmetic) or directly from
the segment number, never from the production helper under test.
"""
import math
import random
import unittest
from fractions import Fraction

from boundary_oracle import (NAKSHATRAS, SIGNS, exact_angle, expected, expected_house,
                             first_float_at_or_above)
from sabpuja_kundali.rules import nakshatra, navamsa_sign, normalize, sign, sign_index, whole_sign_house

BELOW_360 = math.nextafter(360.0, 0.0)
SWEEP_SEED = 20261021
SWEEP_SHIFTS = (0, 360, -360, 720, -720, -3600, 36000)
SWEEP_ULP_STEPS = 2
SWEEP_RANDOM = 400
SWEEP_EXTREMES = (0.0, -0.0, 5e-324, -5e-324, 1e-300, -1e-300, 360.0, -360.0, BELOW_360,
                  -BELOW_360, 1e15, -1e15, 1e300, -1e300, 1.7976931348623157e308,
                  -1.7976931348623157e308)


def step(value, ulps):
    toward = math.inf if ulps > 0 else -math.inf
    for _ in range(abs(ulps)):
        value = math.nextafter(value, toward)
    return value


def sweep_candidates():
    """Fixed-seed boundary-adjacent candidates: every 10/3 degree boundary (which
    includes all Rashi and Nakshatra starts), shifted by whole turns, at
    -2..+2 ulps from the nearest float; plus signed extremes and random values."""
    candidates = set()
    for k in range(109):
        for shift in SWEEP_SHIFTS:
            nearest = float(Fraction(10 * k, 3) + shift)
            for ulps in range(-SWEEP_ULP_STEPS, SWEEP_ULP_STEPS + 1):
                candidates.add(step(nearest, ulps))
    candidates.update(SWEEP_EXTREMES)
    rng = random.Random(SWEEP_SEED)
    candidates.update(rng.uniform(-1e4, 1e4) for _ in range(SWEEP_RANDOM))
    # -0.0 == 0.0 in a set; keep -0.0 explicitly as its own candidate.
    return sorted(candidates) + [-0.0]


def observed(value):
    return {
        "sign_index": sign_index(value),
        "rashi": sign(value),
        "nakshatra": nakshatra(value),
        "navamsa_rashi": navamsa_sign(value),
    }


class NamedRegressions(unittest.TestCase):
    """Reproduced baseline mismatches from issue #9."""

    def test_twenty_degrees_is_bharani_pada_3(self):
        self.assertEqual(nakshatra(20.0), {"index": 1, "name": "Bharani", "pada": 3})
        self.assertEqual(nakshatra(20.0), expected(20.0)["nakshatra"])

    def test_float_just_below_170_over_3_is_simha_d9(self):
        self.assertLess(Fraction(56.666666666666664), Fraction(170, 3))
        self.assertEqual(navamsa_sign(56.666666666666664), "Simha")
        self.assertEqual(nakshatra(56.666666666666664), {"index": 4, "name": "Mrigashira", "pada": 1})

    def test_float_just_below_680_over_3_is_anuradha_pada_4(self):
        self.assertLess(Fraction(226.66666666666666), Fraction(680, 3))
        self.assertEqual(nakshatra(226.66666666666666), {"index": 16, "name": "Anuradha", "pada": 4})
        self.assertEqual(navamsa_sign(226.66666666666666), "Vrischika")

    def test_raw_values_that_round_up_to_a_boundary(self):
        self.assertEqual(sign(29.999999996), "Mesha")
        self.assertEqual(sign(359.999999996), "Meena")
        self.assertEqual(nakshatra(359.999999996), {"index": 26, "name": "Revati", "pada": 4})
        self.assertEqual(navamsa_sign(359.999999996), "Meena")

    def test_negative_sub_ulp_wraps_below_360(self):
        value = normalize(-5e-324)
        self.assertLess(value, 360.0)
        self.assertEqual(value, BELOW_360)
        self.assertEqual(sign(-5e-324), "Meena")
        self.assertEqual(nakshatra(-5e-324), {"index": 26, "name": "Revati", "pada": 4})
        self.assertEqual(navamsa_sign(-5e-324), "Meena")


class ExactBoundaries(unittest.TestCase):
    def assert_boundary(self, boundary, count, check):
        """At each segment start k: the first float at/above it is segment k and the
        float immediately below it is segment k-1 (mod count)."""
        for k in range(count + 1):
            with self.subTest(k=k):
                at = first_float_at_or_above(boundary * k)
                check(at, k % count)
                check(math.nextafter(at, -math.inf), (k - 1) % count)

    def test_all_12_rashi_starts(self):
        def check(value, k):
            self.assertEqual(sign(value), SIGNS[k])
        self.assert_boundary(Fraction(30), 12, check)

    def test_all_27_nakshatra_starts(self):
        def check(value, k):
            self.assertEqual(nakshatra(value)["index"], k)
            self.assertEqual(nakshatra(value)["name"], NAKSHATRAS[k])
        self.assert_boundary(Fraction(40, 3), 27, check)

    def test_all_108_pada_and_d9_boundaries(self):
        def check(value, k):
            self.assertEqual(nakshatra(value), {"index": k // 4, "name": NAKSHATRAS[k // 4], "pada": k % 4 + 1})
            self.assertEqual(navamsa_sign(value), SIGNS[k % 12])
        self.assert_boundary(Fraction(10, 3), 108, check)

    def test_representable_boundaries_are_left_inclusive(self):
        for k in range(12):
            self.assertEqual(sign(30.0 * k), SIGNS[k])
        for k in range(0, 27, 3):  # 40 degree multiples are exact floats
            self.assertEqual(nakshatra(40.0 * k / 3), {"index": k, "name": NAKSHATRAS[k], "pada": 1})
        for k in range(0, 108, 3):  # 10 degree multiples
            self.assertEqual(navamsa_sign(10.0 * k / 3), SIGNS[k % 12])

    def test_zero_and_360_wrap(self):
        for value in (0.0, -0.0, 360.0, -360.0, 720.0, -720.0):
            with self.subTest(value=value):
                self.assertEqual(normalize(value), 0.0)
                self.assertEqual(sign(value), "Mesha")
                self.assertEqual(nakshatra(value), {"index": 0, "name": "Ashwini", "pada": 1})
                self.assertEqual(navamsa_sign(value), "Mesha")
        for value in (BELOW_360, math.nextafter(0.0, -1.0), math.nextafter(-360.0, -math.inf)):
            with self.subTest(value=value):
                self.assertLess(normalize(value), 360.0)
                self.assertEqual(sign(value), "Meena")
                self.assertEqual(nakshatra(value), {"index": 26, "name": "Revati", "pada": 4})
                self.assertEqual(navamsa_sign(value), "Meena")

    def test_signed_and_large_inputs(self):
        self.assertEqual(sign(-1.0), "Meena")
        self.assertEqual(sign(-30.0), "Meena")
        self.assertEqual(sign(math.nextafter(-30.0, 0.0)), "Meena")
        self.assertEqual(sign(math.nextafter(-30.0, -math.inf)), "Kumbha")
        self.assertEqual(sign(390.0), "Vrishabha")
        for value in (1e300, -1e300, 1.7976931348623157e308, -1.7976931348623157e308):
            with self.subTest(value=value):
                self.assertEqual(observed(value)["nakshatra"], expected(value)["nakshatra"])

    def test_fraction_input_is_exact(self):
        just_below_ten = math.nextafter(10.0, 0.0)
        self.assertEqual(just_below_ten + 180.0, 190.0)  # float sum rounds onto a boundary
        exact = Fraction(just_below_ten) + 180
        self.assertEqual(nakshatra(exact), {"index": 14, "name": "Swati", "pada": 1})
        self.assertEqual(navamsa_sign(exact), "Dhanu")
        self.assertEqual(navamsa_sign(190.0), "Makara")

    def test_non_finite_rejected(self):
        for value in (math.nan, math.inf, -math.inf):
            for func in (normalize, sign, nakshatra, navamsa_sign):
                with self.subTest(value=value, func=func.__name__), self.assertRaises(ValueError):
                    func(value)

    def test_houses_in_range_and_wrap_12_to_1(self):
        for planet in range(12):
            for asc in range(12):
                house = whole_sign_house(30.0 * planet, 30.0 * asc)
                self.assertTrue(1 <= house <= 12)
                self.assertEqual(house, (planet - asc) % 12 + 1)
        self.assertEqual(whole_sign_house(BELOW_360, 0.0), 12)
        self.assertEqual(whole_sign_house(0.0, BELOW_360), 2)
        self.assertEqual(whole_sign_house(-5e-324, 0.0), 12)
        self.assertEqual(whole_sign_house(BELOW_360, BELOW_360), 1)


class OracleSweep(unittest.TestCase):
    def test_sweep_matches_independent_oracle(self):
        candidates = sweep_candidates()
        self.assertGreaterEqual(len(candidates), 1644)
        mismatches = []
        for value in candidates:
            want = expected(value)
            got = observed(value)
            ketu_want = expected(Fraction(value) + 180)
            ketu_got = observed(Fraction(value) + 180)
            if got != want or ketu_got != ketu_want:
                mismatches.append(value)
                continue
            norm = normalize(value)
            self.assertTrue(0.0 <= norm < 360.0, value)
            self.assertTrue(0 <= got["sign_index"] <= 11)
            self.assertTrue(0 <= got["nakshatra"]["index"] <= 26)
            self.assertIn(got["nakshatra"]["pada"], (1, 2, 3, 4))
            self.assertTrue(1 <= whole_sign_house(value, 0.0) <= 12)
            self.assertEqual(whole_sign_house(value, value), 1)
            self.assertEqual(whole_sign_house(value, 45.0), expected_house(value, 45.0))
            if 0.0 <= value < 360.0:
                self.assertEqual(norm, value)
                self.assertEqual(exact_angle(norm), exact_angle(value))
        smallest = min(mismatches, key=abs, default=None)
        self.assertEqual(mismatches, [], f"{len(mismatches)} of {len(candidates)} mismatched; "
                                         f"smallest |x| example {smallest!r}")


if __name__ == "__main__":
    unittest.main()
