"""Gate 3E: D9 whole-sign houses (SCI-01f) against an independent oracle.

The expected answers come from tests/d9_house_oracle.py (classical element
rule and sign counting), never from sabpuja_kundali.rules. A test double
stands in for swisseph in the engine-level classes, so chosen exact
longitudes reach the engine; that proves derivation only, not astronomy.
The real-data class records the unrounded Swiss values the engine received
and checks every chart against the oracle.
"""
import json
import math
import os
import random
import unittest
from fractions import Fraction
from unittest import mock

import d9_house_oracle as oracle
import boundary_oracle
from sabpuja_kundali import engine, provenance, rules

import test_engine_boundaries

run = test_engine_boundaries.run  # module import only: its TestCases are not re-collected here

BODIES = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu_mean", "ketu_mean")
SWISS_BODIES = BODIES[:-1]
ARC = Fraction(10, 3)
TINY = Fraction(1, 10 ** 15)
DATA = os.environ.get("SABPUJA_TEST_EPHE_PATH")


def boundary(n):
    """Exact start of Navamsa segment n (n may be any integer)."""
    return ARC * n


def floats_around(edge):
    """The float just below the exact edge, and the first float at or above it."""
    at_or_above = boundary_oracle.first_float_at_or_above(edge)
    below = math.nextafter(at_or_above, -math.inf)
    assert Fraction(below) < edge <= Fraction(at_or_above)
    return below, at_or_above


def mid_of_d9_sign(d9_index, rashi=None):
    """A longitude (float, exact in binary) in the middle of a Navamsa with this D9 sign."""
    for n in range(108):
        if n % 12 == d9_index and (rashi is None or n // 9 == rashi):
            return float(boundary(n) + ARC / 2)
    raise AssertionError("no such segment")


def check_d9_block(test, chart):
    """Every D9 field agrees with every other and with the oracle's house order."""
    d9 = chart["d9"]
    test.assertEqual(list(d9), ["house_system", "lagna_rashi", "houses"])
    test.assertEqual(d9["house_system"], "whole_sign")
    test.assertEqual(d9["lagna_rashi"], chart["lagna"]["navamsa_rashi"])
    test.assertEqual([h["house"] for h in d9["houses"]], list(range(1, 13)))
    expected = []
    start = oracle.SIGNS.index(d9["lagna_rashi"])
    for i in range(12):
        expected.append(oracle.SIGNS[(start + i) % 12])
    test.assertEqual([h["rashi"] for h in d9["houses"]], expected)
    seen = []
    for h in d9["houses"]:
        test.assertEqual(list(h), ["house", "rashi", "grahas"])
        for body in h["grahas"]:
            p = chart["planets"][body]
            test.assertEqual(p["navamsa_whole_sign_house"], h["house"], body)
            test.assertEqual(p["navamsa_rashi"], h["rashi"], body)
            seen.append(body)
    test.assertEqual(sorted(seen), sorted(BODIES))  # each body exactly once
    for h in d9["houses"]:  # graha order inside a house is the planets order
        test.assertEqual(h["grahas"], [b for b in BODIES if b in h["grahas"]])


class OracleSelfCheck(unittest.TestCase):
    """The classical oracle agrees with the separate continuous oracle (two derivations)."""

    def test_classical_and_continuous_oracles_agree_on_all_108_segments(self):
        for n in range(108):
            for value in (boundary(n), boundary(n) + TINY, boundary(n + 1) - TINY, boundary(n) + ARC / 2):
                with self.subTest(n=n, value=value):
                    self.assertEqual(oracle.d9_sign(value), boundary_oracle.expected(value)["navamsa_rashi"])

    def test_classical_element_rule_examples(self):
        # First Navamsa of a movable / fixed / dual Rashi: itself, 9th, 5th.
        self.assertEqual(oracle.d9_sign(Fraction(0)), "Mesha")
        self.assertEqual(oracle.d9_sign(Fraction(30)), "Makara")
        self.assertEqual(oracle.d9_sign(Fraction(60)), "Tula")
        self.assertEqual(oracle.d9_sign(Fraction(90)), "Karka")
        # Last Navamsa of Meena is Meena; of Mesha is Dhanu.
        self.assertEqual(oracle.d9_sign(Fraction(360) - TINY), "Meena")
        self.assertEqual(oracle.d9_sign(Fraction(30) - TINY), "Dhanu")


class NavamsaSegments(unittest.TestCase):
    """Production D9 sign index on all 108 half-open segments and their exact edges."""

    def test_every_segment_start_inside_and_end(self):
        for n in range(108):
            start, end = boundary(n), boundary(n + 1)
            cases = [start, start + TINY, start + ARC / 2, end - TINY]
            for value in cases:
                with self.subTest(n=n, value=value):
                    self.assertEqual(rules.navamsa_sign_index(value), oracle.d9_sign_index(value))
                    self.assertEqual(rules.SIGNS[rules.navamsa_sign_index(value)], rules.navamsa_sign(value))
            self.assertEqual(oracle.d9_sign_index(start), n % 12)
            self.assertEqual(oracle.d9_sign_index(end - TINY), n % 12)

    def test_exact_float_neighbours_of_every_boundary(self):
        # No epsilon: the float just below an exact 3 deg 20 min edge stays in the earlier
        # segment and the first float at or above it moves on.
        for n in range(1, 109):
            below, above = floats_around(boundary(n))
            with self.subTest(n=n):
                self.assertEqual(rules.navamsa_sign_index(below), oracle.d9_sign_index(below))
                self.assertEqual(rules.navamsa_sign_index(above), oracle.d9_sign_index(above))
                self.assertEqual(oracle.d9_sign_index(below), (n - 1) % 12)
                self.assertEqual(oracle.d9_sign_index(above), n % 12)

    def test_zero_and_360_wrap(self):
        below_360 = math.nextafter(360.0, 0.0)
        cases = [(0.0, 0), (-0.0, 0), (360.0, 0), (720.0, 0), (below_360, 11), (math.nextafter(0.0, 1.0), 0),
                 (math.nextafter(0.0, -1.0), 11), (-360.0, 0), (Fraction(360) - TINY, 11),
                 (Fraction(-360) - TINY, 11), (math.nextafter(-360.0, 0.0), 0)]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(rules.navamsa_sign_index(value), expected)
                self.assertEqual(oracle.d9_sign_index(value), expected)

    def test_negative_and_cyclic_representations(self):
        rng = random.Random(20261025)
        for _ in range(500):
            base = Fraction(rng.randrange(0, 360 * 10 ** 6), 10 ** 6)
            for turns in (-3, -1, 1, 2, 5):
                value = base + 360 * turns
                with self.subTest(base=base, turns=turns):
                    self.assertEqual(rules.navamsa_sign_index(value), oracle.d9_sign_index(base))
                    self.assertEqual(oracle.d9_sign_index(value), oracle.d9_sign_index(base))
        for n in range(108):  # cyclic copies of every edge, as Fractions and as floats
            for turns in (-2, -1, 1, 3):
                edge = boundary(n) + 360 * turns
                self.assertEqual(rules.navamsa_sign_index(edge), n % 12)
                below, above = floats_around(edge)
                self.assertEqual(rules.navamsa_sign_index(below), oracle.d9_sign_index(below))
                self.assertEqual(rules.navamsa_sign_index(above), oracle.d9_sign_index(above))

    def test_random_exact_and_float_longitudes(self):
        rng = random.Random(9)
        for _ in range(20000):
            value = rng.uniform(-720.0, 1080.0)
            self.assertEqual(rules.navamsa_sign_index(value), oracle.d9_sign_index(value), value)


class D9HouseRule(unittest.TestCase):
    """navamsa_whole_sign_house for every D9 Lagna sign and every planetary D9 sign."""

    def test_all_144_lagna_and_planet_d9_sign_pairs(self):
        for lagna_d9 in range(12):
            lagna = mid_of_d9_sign(lagna_d9)
            for planet_d9 in range(12):
                planet = mid_of_d9_sign(planet_d9)
                with self.subTest(lagna=lagna_d9, planet=planet_d9):
                    house = rules.navamsa_whole_sign_house(planet, lagna)
                    self.assertEqual(house, oracle.d9_house(planet, lagna))
                    self.assertEqual(oracle.d9_house_rashis(lagna)[house - 1], oracle.d9_sign(planet))

    def test_every_segment_against_every_lagna_segment(self):
        # 108 x 108 exact segment starts and last-instant values: all pairs.
        for ln in range(108):
            for lagna in (boundary(ln), boundary(ln + 1) - TINY):
                for pn in range(108):
                    for planet in (boundary(pn), boundary(pn + 1) - TINY):
                        self.assertEqual(rules.navamsa_whole_sign_house(planet, lagna),
                                         oracle.d9_house(planet, lagna), (ln, pn))

    def test_house_1_and_house_12_transitions_at_exact_edges(self):
        for ln in range(108):
            lagna = boundary(ln) + ARC / 2
            # The D9 Lagna's own segment start is house 1; the float just below it is house 12.
            # The next segment start is house 2.
            below, at = floats_around(boundary(ln))
            self.assertEqual(rules.navamsa_whole_sign_house(at, lagna), 1)
            self.assertEqual(rules.navamsa_whole_sign_house(below, lagna), 12)
            self.assertEqual(oracle.d9_house(below, lagna), 12)
            self.assertEqual(rules.navamsa_whole_sign_house(boundary(ln + 1), lagna), 2)
            # The Lagna itself is always in house 1, including on its exact edges.
            for value in (boundary(ln), boundary(ln + 1) - TINY, at):
                self.assertEqual(rules.navamsa_whole_sign_house(value, value), 1)

    def test_property_house_matches_rashi_random(self):
        rng = random.Random(31)
        for _ in range(5000):
            lagna = Fraction(rng.randrange(-360 * 10 ** 9, 720 * 10 ** 9), 10 ** 9)
            planet = Fraction(rng.randrange(-360 * 10 ** 9, 720 * 10 ** 9), 10 ** 9)
            house = rules.navamsa_whole_sign_house(planet, lagna)
            self.assertEqual(house, oracle.d9_house(planet, lagna))
            self.assertEqual(oracle.d9_house_rashis(lagna)[house - 1], oracle.d9_sign(planet))


class EngineD9Block(unittest.TestCase):
    """engine.calculate output with chosen exact longitudes (test double for swisseph)."""

    def chart(self, longitudes, lagna):
        chart = run(longitudes, lagna)
        check_d9_block(self, chart)
        sources = dict(longitudes, ketu_mean=Fraction(longitudes["rahu_mean"]) + 180)
        for body in BODIES:
            p = chart["planets"][body]
            self.assertEqual(p["navamsa_rashi"], oracle.d9_sign(sources[body]), body)
            self.assertEqual(p["navamsa_whole_sign_house"], oracle.d9_house(sources[body], lagna), body)
        self.assertEqual(chart["lagna"]["navamsa_rashi"], oracle.d9_sign(lagna))
        return chart

    def test_all_twelve_d9_lagna_signs(self):
        for d9 in range(12):
            lagna = mid_of_d9_sign(d9)
            longitudes = {b: mid_of_d9_sign((d9 + i) % 12) for i, b in enumerate(SWISS_BODIES)}
            with self.subTest(d9_lagna=oracle.SIGNS[d9]):
                chart = self.chart(longitudes, lagna)
                self.assertEqual(chart["d9"]["lagna_rashi"], oracle.SIGNS[d9])
                self.assertEqual(chart["d9"]["houses"][0]["rashi"], oracle.SIGNS[d9])

    def test_all_twelve_planet_d9_signs_for_each_lagna(self):
        for ld in range(12):
            lagna = mid_of_d9_sign(ld)
            for pd in range(12):
                longitudes = {b: mid_of_d9_sign(pd) for b in SWISS_BODIES}
                chart = self.chart(longitudes, lagna)
                expected_house = (pd - ld) % 12 + 1
                self.assertEqual(chart["planets"]["sun"]["navamsa_whole_sign_house"], expected_house)

    def test_crowded_house_and_empty_houses(self):
        # Eight bodies in one Navamsa (same D9 sign as the D9 Lagna); Ketu is 180 deg from Rahu.
        lagna = mid_of_d9_sign(4)
        longitudes = {b: mid_of_d9_sign(4) for b in SWISS_BODIES}
        chart = self.chart(longitudes, lagna)
        houses = chart["d9"]["houses"]
        self.assertEqual(houses[0]["grahas"], list(SWISS_BODIES))
        ketu_house = chart["planets"]["ketu_mean"]["navamsa_whole_sign_house"]
        self.assertEqual(houses[ketu_house - 1]["grahas"], ["ketu_mean"])
        self.assertEqual(sum(1 for h in houses if not h["grahas"]), 10)

    def test_house_12_and_house_1_at_the_lagna_segment_edge(self):
        # Lagna inside segment 40; Sun on the float just below segment 40 (house 12), Moon on
        # the first float at or above it (house 1), Mars on the next segment start (house 2).
        lagna = float(boundary(40) + ARC / 2)
        below, at = floats_around(boundary(40))
        _, next_start = floats_around(boundary(41))
        longitudes = {"sun": below, "moon": at, "mars": next_start, "mercury": 1.0, "jupiter": 100.0,
                      "venus": 200.0, "saturn": 300.0, "rahu_mean": 45.0}
        chart = self.chart(longitudes, lagna)
        houses = {b: chart["planets"][b]["navamsa_whole_sign_house"] for b in BODIES}
        self.assertEqual((houses["sun"], houses["moon"], houses["mars"]), (12, 1, 2))

    def test_ketu_exact_opposite_classification(self):
        # Rahu just below an edge such that the float sum Rahu + 180.0 rounds onto the next
        # segment; the engine must classify the exact sum (earlier segment).
        found = crossing = 0
        for n in range(108):
            below, _ = floats_around(boundary(n))
            if below < 0 or below >= 180:
                continue
            if Fraction(below + 180.0) != Fraction(below) + 180:
                longitudes = dict.fromkeys(SWISS_BODIES, 1.0)
                longitudes["rahu_mean"] = below
                chart = self.chart(longitudes, 5.0)
                exact_sum = Fraction(below) + 180
                self.assertEqual(chart["planets"]["ketu_mean"]["navamsa_rashi"], oracle.d9_sign(exact_sum))
                rahu_d9 = oracle.d9_sign_index(below)
                ketu_d9 = oracle.d9_sign_index(exact_sum)
                self.assertEqual(ketu_d9, (rahu_d9 + 6) % 12)  # 54 segments = 6 signs mod 12
                rahu_h = chart["planets"]["rahu_mean"]["navamsa_whole_sign_house"]
                ketu_h = chart["planets"]["ketu_mean"]["navamsa_whole_sign_house"]
                self.assertEqual((ketu_h - rahu_h) % 12, 6)
                found += 1
                if oracle.d9_sign_index(below + 180.0) != ketu_d9:
                    crossing += 1  # the float sum would have moved Ketu to the next Navamsa
                    self.assertNotEqual(chart["planets"]["ketu_mean"]["navamsa_rashi"],
                                        oracle.d9_sign(below + 180.0))
        self.assertGreater(found, 0)
        self.assertGreater(crossing, 0)

    def test_rahu_ketu_always_seven_houses_apart_random(self):
        rng = random.Random(5)
        for _ in range(300):
            longitudes = {b: rng.uniform(0, 360) for b in SWISS_BODIES}
            chart = self.chart(longitudes, rng.uniform(0, 360))
            r = chart["planets"]["rahu_mean"]["navamsa_whole_sign_house"]
            k = chart["planets"]["ketu_mean"]["navamsa_whole_sign_house"]
            self.assertEqual((k - r) % 12, 6)

    def test_not_classified_from_displayed_longitude(self):
        # 29.999999996 is displayed as 30.0 (D9 of 30.0 is Makara) but its exact value is in
        # the last Navamsa of Mesha (Dhanu); the house follows the exact value.
        longitudes = dict.fromkeys(SWISS_BODIES, 100.0)
        longitudes["sun"] = 29.999999996
        lagna = mid_of_d9_sign(0)
        chart = self.chart(longitudes, lagna)
        sun = chart["planets"]["sun"]
        self.assertEqual(sun["longitude_deg"], 30.0)
        self.assertEqual(sun["navamsa_rashi"], "Dhanu")
        self.assertEqual(sun["navamsa_whole_sign_house"], 9)
        self.assertNotEqual(oracle.d9_house(sun["longitude_deg"], lagna), 9)

    def test_property_random_charts(self):
        rng = random.Random(20261026)
        for _ in range(400):
            longitudes = {b: rng.uniform(0, 360) for b in SWISS_BODIES}
            self.chart(longitudes, rng.uniform(0, 360))

    def test_d1_and_existing_fields_unchanged_by_projection(self):
        chart = run()
        baseline = provenance.baseline_projection(chart)
        self.assertEqual(baseline["schema_version"], "0.2.0")
        self.assertNotIn("d9", baseline)
        for body in BODIES:
            self.assertNotIn("navamsa_whole_sign_house", baseline["planets"][body])
            for key in ("longitude_deg", "rashi", "navamsa_rashi", "whole_sign_house"):
                self.assertEqual(baseline["planets"][body][key], chart["planets"][body][key])
        self.assertEqual(provenance.legacy_projection(chart), {
            k: v for k, v in baseline.items() if k != "calculation_metadata"} | {"schema_version": "0.1.0"})
        json.dumps(chart, allow_nan=False)


@unittest.skipIf(DATA is None, "SABPUJA_TEST_EPHE_PATH unset: real-data D9 checks need the pinned data")
class RealSwissD9(unittest.TestCase):
    """Real Swiss charts: record the unrounded values the engine received, then check the oracle."""

    REQUESTS = [(f"{y:04d}-{m:02d}-{d:02d}T{h:02d}:{mi:02d}:00+05:30", "Asia/Kolkata", lat, lon)
                for (y, m, d, h, mi, lat, lon) in [
                    (1970, 1, 1, 0, 0, 28.6139, 77.2090), (1984, 11, 2, 23, 59, 19.076, 72.8777),
                    (1990, 5, 15, 10, 30, 28.63576, 77.22445), (2000, 2, 29, 5, 45, 13.0827, 80.2707),
                    (2012, 12, 21, 12, 0, 12.9716, 77.5946), (2024, 8, 15, 6, 5, 26.9124, 75.7873),
                    (2050, 1, 1, 0, 0, 25.3176, 82.9739), (2070, 10, 4, 6, 0, 26.1445, 91.7362),
                    (2100, 12, 31, 23, 59, 22.5726, 88.3639)]]
    REQUESTS += [(f"2031-03-{d:02d}T{h:02d}:17:00+05:30", "Asia/Kolkata", 21.1458, 79.0882)
                 for d in (3, 11, 19, 27) for h in range(0, 24, 3)]

    def test_real_charts_match_oracle(self):
        import swisseph as swe
        real_calc, real_houses = swe.calc_ut, swe.houses_ex
        for birth, tz, lat, lon in self.REQUESTS:
            seen = {}

            def calc(jd, body, flags):
                out = real_calc(jd, body, flags)
                seen[body] = out[0][0]
                return out

            def houses(*args):
                out = real_houses(*args)
                seen["lagna"] = out[1][0]
                return out

            with mock.patch.object(swe, "calc_ut", calc), mock.patch.object(swe, "houses_ex", houses):
                chart = engine.calculate({"birth_datetime": birth, "timezone": tz, "latitude": lat,
                                          "longitude": lon}, ephe_path=DATA)
            numbers = dict(zip(SWISS_BODIES, (swe.SUN, swe.MOON, swe.MARS, swe.MERCURY, swe.JUPITER,
                                              swe.VENUS, swe.SATURN, swe.MEAN_NODE)))
            sources = {b: seen[numbers[b]] for b in SWISS_BODIES}
            sources["ketu_mean"] = Fraction(sources["rahu_mean"]) + 180
            lagna = seen["lagna"]
            with self.subTest(birth=birth):
                check_d9_block(self, chart)
                self.assertEqual(chart["lagna"]["navamsa_rashi"], oracle.d9_sign(lagna))
                for body in BODIES:
                    p = chart["planets"][body]
                    self.assertEqual(p["navamsa_rashi"], oracle.d9_sign(sources[body]))
                    self.assertEqual(p["navamsa_whole_sign_house"], oracle.d9_house(sources[body], lagna))
                # The block is the same with no recording wrapper in place.
                plain = engine.calculate({"birth_datetime": birth, "timezone": tz, "latitude": lat,
                                          "longitude": lon}, ephe_path=DATA)
                self.assertEqual(plain, chart)


if __name__ == "__main__":
    unittest.main()
