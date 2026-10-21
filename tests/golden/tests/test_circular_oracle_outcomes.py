"""Circular differences, boundary distances, the category oracle and outcome precedence."""
from fractions import Fraction
import math
import unittest

from ..harness import oracle
from ..harness.circular import (NAKSHATRA_DEG, PADA_DEG, RASHI_DEG, boundary_distance_arcsec,
                                circular_diff_arcsec, circular_diff_deg)
from ..harness.outcomes import EXIT_CODES, Outcome, Verdict, exit_code, fixture_outcome, overall_verdict


class CircularDifference(unittest.TestCase):
    def test_wrap_359_9999_vs_0_0001_is_0_72_arcsec(self):
        self.assertAlmostEqual(circular_diff_arcsec(359.9999, 0.0001), -0.72, places=6)
        self.assertAlmostEqual(circular_diff_arcsec(0.0001, 359.9999), 0.72, places=6)

    def test_zero_and_360_are_the_same_angle(self):
        self.assertEqual(circular_diff_deg(0.0, 360.0), 0.0)
        self.assertEqual(circular_diff_deg(360.0, 0.0), 0.0)
        self.assertEqual(circular_diff_arcsec(720.0, 0.0), 0.0)

    def test_range_is_half_open_minus_180_to_180(self):
        self.assertEqual(circular_diff_deg(180.0, 0.0), -180.0)
        self.assertEqual(circular_diff_deg(0.0, 180.0), -180.0)
        self.assertAlmostEqual(circular_diff_deg(10.0, 350.0), 20.0, places=12)
        self.assertAlmostEqual(circular_diff_deg(350.0, 10.0), -20.0, places=12)

    def test_negative_inputs(self):
        self.assertAlmostEqual(circular_diff_deg(-0.5, 0.5), -1.0, places=12)

    def test_rejects_non_numbers_and_non_finite(self):
        for bad in (True, "1.0", None):
            with self.assertRaises(TypeError):
                circular_diff_deg(bad, 0.0)
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                circular_diff_arcsec(0.0, bad)


class BoundaryDistance(unittest.TestCase):
    def test_near_rashi_edges_both_sides_and_wrap(self):
        self.assertAlmostEqual(boundary_distance_arcsec(29.9999, RASHI_DEG), 0.36, places=6)
        self.assertAlmostEqual(boundary_distance_arcsec(30.0001, RASHI_DEG), 0.36, places=6)
        self.assertAlmostEqual(boundary_distance_arcsec(359.9999, RASHI_DEG), 0.36, places=6)
        self.assertAlmostEqual(boundary_distance_arcsec(0.0001, RASHI_DEG), 0.36, places=6)
        self.assertEqual(boundary_distance_arcsec(15.0, RASHI_DEG), 15 * 3600)

    def test_nakshatra_and_pada_edges_are_exact(self):
        edge = float(NAKSHATRA_DEG)  # 13.333... as the nearest float
        self.assertLess(boundary_distance_arcsec(edge, NAKSHATRA_DEG), 1e-9)
        self.assertLess(boundary_distance_arcsec(float(PADA_DEG * 7), PADA_DEG), 1e-9)
        self.assertAlmostEqual(boundary_distance_arcsec(float(PADA_DEG) / 2, PADA_DEG), 6000.0, places=6)

    def test_segment_must_be_exact_divisor_of_360(self):
        for bad in (30.0, Fraction(7), Fraction(0), Fraction(-30)):
            with self.assertRaises(ValueError):
                boundary_distance_arcsec(1.0, bad)


class Oracle(unittest.TestCase):
    def test_rashi_edges_half_open(self):
        self.assertEqual(oracle.rashi(0.0), "Mesha")
        self.assertEqual(oracle.rashi(29.999999), "Mesha")
        self.assertEqual(oracle.rashi(30.0), "Vrishabha")
        self.assertEqual(oracle.rashi(359.9999), "Meena")
        self.assertEqual(oracle.rashi(360.0), "Mesha")
        self.assertEqual(oracle.rashi(-0.0001), "Meena")

    def test_nakshatra_pada_navamsa(self):
        self.assertEqual(oracle.nakshatra(0.0), ("Ashwini", 1))
        self.assertEqual(oracle.nakshatra(359.9999), ("Revati", 4))
        self.assertEqual(oracle.nakshatra(Fraction(40, 3)), ("Bharani", 1))
        self.assertEqual(oracle.navamsa(0.0), "Mesha")
        self.assertEqual(oracle.navamsa(Fraction(10, 3)), "Vrishabha")
        self.assertEqual(oracle.navamsa(30.0), "Makara")  # Vrishabha's D9 starts at Makara

    def test_houses(self):
        self.assertEqual(oracle.whole_sign_house(5.0, 5.0), 1)
        self.assertEqual(oracle.whole_sign_house(355.0, 5.0), 12)
        self.assertEqual(oracle.d9_house(0.0, 0.0), 1)
        self.assertEqual(oracle.d9_house(Fraction(10, 3), 0.0), 2)

    def test_rejects_non_finite(self):
        with self.assertRaises(ValueError):
            oracle.rashi(math.nan)


class Outcomes(unittest.TestCase):
    def test_exit_codes(self):
        self.assertEqual(EXIT_CODES, {Verdict.PASS: 0, Verdict.FAIL: 1, Verdict.BLOCKED: 2, Verdict.QUALIFIED: 2})
        self.assertEqual(exit_code(Verdict.PASS), 0)

    def test_empty_is_blocked(self):
        self.assertEqual(overall_verdict([]), Verdict.BLOCKED)
        self.assertEqual(fixture_outcome([]), Outcome.BLOCKED)

    def test_mixed_outcome_priority(self):
        cases = [
            ([Outcome.PASS], Verdict.PASS),
            ([Outcome.PASS, Outcome.QUALIFIED], Verdict.QUALIFIED),
            ([Outcome.QUALIFIED, Outcome.BOUNDARY_INDETERMINATE], Verdict.BLOCKED),
            ([Outcome.PASS, Outcome.METHOD_MISMATCH], Verdict.BLOCKED),
            ([Outcome.PASS, Outcome.BLOCKED], Verdict.BLOCKED),
            ([Outcome.BLOCKED, Outcome.FAIL, Outcome.QUALIFIED], Verdict.FAIL),
            ([Outcome.METHOD_MISMATCH, Outcome.BOUNDARY_INDETERMINATE, Outcome.FAIL], Verdict.FAIL),
        ]
        for outcomes, verdict in cases:
            with self.subTest(outcomes=outcomes):
                self.assertEqual(overall_verdict(outcomes), verdict)

    def test_fixture_outcome_is_most_severe(self):
        self.assertEqual(fixture_outcome([Outcome.PASS, Outcome.FAIL, Outcome.BLOCKED]), Outcome.FAIL)
        self.assertEqual(fixture_outcome([Outcome.PASS, Outcome.BOUNDARY_INDETERMINATE]), Outcome.BOUNDARY_INDETERMINATE)
        self.assertEqual(fixture_outcome([Outcome.PASS, Outcome.QUALIFIED]), Outcome.QUALIFIED)
        self.assertEqual(fixture_outcome([Outcome.PASS, Outcome.PASS]), Outcome.PASS)


if __name__ == "__main__":
    unittest.main()
