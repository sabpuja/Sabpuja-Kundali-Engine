"""PAN-QA-01: sector rules against the independent rational oracle; half-open edges; 0/360 wrap.

PAN-SPEC-01 to 05, D08-A, D18-A, D07-A, D16-M1-INDEX, D02-M1 contract. The pinned
tolerance and fixture files are checked byte-exactly before anything reads them.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
import ast
import json
import math
import random
import re
import unittest

from sabpuja_kundali import rules as chart_rules
from sabpuja_kundali.panchanga import rules
from sabpuja_kundali.panchanga.search import DEFAULT_LIMITS, MICROS

from . import oracle
from .common import (EPHE, FIXTURE_SHA256, REPO, TOLERANCES_SHA256, fixture, real_data, request_at_utc,
                     sha256_bytes, tolerances, FIXTURE_PATH, TOLERANCES_PATH, parse_utc)

PKG = REPO / "src/sabpuja_kundali/panchanga"

# Names that must not appear anywhere in M1 code or output (D07-A, D16-M1-INDEX).
# "shukla" is excluded on purpose: it is the approved paksha machine id (D18-A).
FORBIDDEN_NAMES = (
    # Karana
    "bava", "balava", "kaulava", "taitila", "taitula", "garaja", "vanija", "vishti", "bhadra",
    "shakuni", "chatushpada", "kimstughna", "kinstughna",
    # Yoga
    "vishkambha", "priti", "ayushman", "saubhagya", "shobhana", "atiganda", "sukarma", "dhriti",
    "shula", "vriddhi", "dhruva", "vyaghata", "harshana", "vajra", "siddhi", "vyatipata", "variyan",
    "parigha", "sadhya", "shubha", "vaidhriti",
    # Tithi
    "pratipada", "dwitiya", "tritiya", "chaturthi", "panchami", "shashthi", "saptami", "ashtami",
    "navami", "dashami", "ekadashi", "dwadashi", "trayodashi", "chaturdashi", "purnima", "amavasya",
)
FORBIDDEN_KEYS = ("sunrise", "sunset", "vara", "weekday", "masa", "samvat", "kshaya", "adhika", "hindi")


def neighbours(edge: Fraction):
    """The exact edge (as a rational) and the binary floats just below and above it."""
    f = float(edge)
    below = f if Fraction(f) < edge else math.nextafter(f, -math.inf)
    above = f if Fraction(f) > edge else math.nextafter(f, math.inf)
    while Fraction(below) >= edge:
        below = math.nextafter(below, -math.inf)
    while Fraction(above) <= edge:
        above = math.nextafter(above, math.inf)
    return edge, below, above


class PinnedInputsTest(unittest.TestCase):
    def test_tolerance_and_fixture_files_are_byte_identical_to_the_frozen_hashes(self):
        self.assertEqual(sha256_bytes(TOLERANCES_PATH.read_bytes()), TOLERANCES_SHA256)
        self.assertEqual(sha256_bytes(FIXTURE_PATH.read_bytes()), FIXTURE_SHA256)
        tol = tolerances()
        self.assertEqual(tol["source_reference"]["fixture_sha256"], FIXTURE_SHA256)

    def test_search_limits_equal_the_frozen_d09_values(self):
        d09 = tolerances()["D09_A_M1"]
        self.assertEqual(DEFAULT_LIMITS.step_us, d09["bracket_step_hours"] * 3600 * MICROS)
        self.assertEqual(DEFAULT_LIMITS.max_extent_us, int(d09["bracket_extent_max_days_each_direction"] * 86400 * MICROS))
        self.assertEqual(DEFAULT_LIMITS.max_iterations, d09["bisection_max_iterations"])
        self.assertEqual(DEFAULT_LIMITS.bracket_max_us, int(d09["transition_bracket_max_seconds"] * MICROS))
        self.assertEqual(d09["utc_machine_output"], "first_whole_second_in_new_half_open_sector")

    def test_rechecked_ids_are_exactly_the_fixture_cases(self):
        ids = tolerances()["source_reference"]["independently_rechecked_case_ids"]
        self.assertEqual(len(ids), 50)
        self.assertEqual(len(set(ids)), 50)
        self.assertEqual(ids, [c["case_id"] for c in fixture()["cases"]])

    def test_decision_codes_match_the_adoption_record(self):
        from sabpuja_kundali.panchanga.contract import DECISIONS
        self.assertEqual(list(DECISIONS), tolerances()["scientific_decision_adoption"]["options"])


class TithiTest(unittest.TestCase):
    """PAN-SPEC-01 and D18-A."""

    def test_every_tithi_edge_and_float_neighbours(self):
        for k in range(30):
            edge, below, above = neighbours(Fraction(12 * k))
            self.assertEqual(rules.tithi_number(edge), k + 1)
            self.assertEqual(rules.tithi_number(above), k + 1)
            self.assertEqual(rules.tithi_number(below), 30 if k == 0 else k)
            for x in (edge, below, above):
                self.assertEqual(rules.tithi_number(x), oracle.sector(x, 30) + 1)

    def test_paksha_and_paksha_day_for_all_30(self):
        for n in range(1, 31):
            want = oracle.tithi(0, Fraction(12 * (n - 1)) + Fraction(1, 7))
            self.assertEqual(want["number"], n)
            self.assertEqual(rules.paksha(n), want["paksha"])
            self.assertEqual(rules.paksha_day(n), want["paksha_day"])
        self.assertEqual([rules.paksha_day(n) for n in (1, 15, 16, 30)], [1, 15, 1, 15])
        self.assertEqual([rules.paksha(n) for n in (15, 16)], ["shukla", "krishna"])
        for bad in (0, 31, -1):
            with self.assertRaises(ValueError):
                rules.paksha(bad)
            with self.assertRaises(ValueError):
                rules.paksha_day(bad)


class NakshatraTest(unittest.TestCase):
    """PAN-SPEC-02: identical to the chart rule and identifiers."""

    def test_every_pada_edge_and_float_neighbours(self):
        for k in range(108):
            for x in neighbours(Fraction(10 * k, 3)):
                got = rules.moon_nakshatra(x)
                self.assertEqual(got, chart_rules.nakshatra(x))
                nak, pada = oracle.nakshatra_pada(x)
                self.assertEqual((got["index"], got["pada"]), (nak, pada))
                self.assertEqual(got["name"], chart_rules.NAKSHATRAS[nak])
                sectors = rules.element_sectors(0.0, x)
                self.assertEqual((sectors["nakshatra"], sectors["pada"]), (nak, oracle.sector(x, 108)))


class YogaTest(unittest.TestCase):
    """PAN-SPEC-03: the exact sum is reduced, never rounded addends."""

    def test_every_yoga_edge_and_float_neighbours(self):
        for k in range(27):
            for x in neighbours(Fraction(40 * k, 3)):
                self.assertEqual(rules.yoga_index(x), oracle.sector(x, 27) + 1)
        self.assertEqual(rules.yoga_index(Fraction(40, 3)), 2)
        self.assertEqual(rules.yoga_index(neighbours(Fraction(40, 3))[1]), 1)

    def test_sums_above_360_and_float_rounding_traps(self):
        rng = random.Random(20261103)
        hits = 0
        for _ in range(20000):
            sun = rng.uniform(180, 360)
            k = rng.randrange(27)
            target = Fraction(40 * k, 3) + 360
            moon = float(target - Fraction(sun))
            for m in (moon, math.nextafter(moon, 0), math.nextafter(moon, 720)):
                exact = oracle.yoga_index(sun, m)
                self.assertEqual(rules.yoga_index(rules.yoga_sum(sun, m)), exact)
                naive = math.floor((sun + m) % 360 * 27 / 360) + 1
                hits += naive != exact
        # The trap is real: naive float addition misclassifies some of these pairs.
        self.assertGreater(hits, 0)


class KaranaTest(unittest.TestCase):
    """PAN-SPEC-04 and D07-A."""

    def test_every_karana_edge_and_float_neighbours(self):
        for k in range(60):
            edge, below, above = neighbours(Fraction(6 * k))
            self.assertEqual(rules.karana_index(edge), k + 1)
            self.assertEqual(rules.karana_index(above), k + 1)
            self.assertEqual(rules.karana_index(below), 60 if k == 0 else k)

    def test_sixty_and_one_are_adjacent_across_zero(self):
        self.assertEqual(rules.karana_index(rules.elongation(10.0, math.nextafter(10.0, 0))), 60)
        self.assertEqual(rules.karana_index(rules.elongation(10.0, 10.0)), 1)


class WrapTest(unittest.TestCase):
    """PAN-SPEC-05: E and S in [0, 360); negative differences gain 360 exactly; 360 maps to 0."""

    def test_wrap_cases(self):
        below360 = math.nextafter(360.0, 0)
        tiny = math.ulp(0.0)
        cases = [(below360, 0.0), (below360, tiny), (0.0, below360), (tiny, below360), (359.5, 0.25),
                 (0.25, 359.5), (180.0, 180.0), (359.0, 359.0), (360.0, 0.0), (0.0, 360.0), (720.0, -0.0)]
        for sun, moon in cases:
            e, s = rules.elongation(sun, moon), rules.yoga_sum(sun, moon)
            self.assertTrue(0 <= e < 360 and 0 <= s < 360, (sun, moon))
            self.assertEqual(e, oracle.elongation(sun, moon))
            self.assertEqual(s, oracle.yoga_sum(sun, moon))
            self.assertEqual(rules.element_sectors(sun, moon), oracle.all_sectors(sun, moon))
        self.assertEqual(rules.elongation(below360, 0.0), Fraction(0) - Fraction(below360) + 360)
        self.assertEqual(rules.tithi_number(rules.elongation(below360, 0.0)), 1)
        self.assertEqual(rules.tithi_number(rules.elongation(0.0, below360)), 30)
        self.assertEqual(rules.yoga_sum(180.0, 180.0), 0)
        self.assertEqual(rules.yoga_index(rules.yoga_sum(below360, below360)), 27)

    def test_non_finite_and_non_numeric_inputs_are_refused(self):
        for bad in (math.inf, -math.inf, math.nan):
            with self.assertRaises(ValueError):
                rules.elongation(bad, 1.0)
            with self.assertRaises(ValueError):
                rules.yoga_sum(1.0, bad)
        for bad in (True, "1", None):
            with self.assertRaises(TypeError):
                rules.elongation(bad, 1.0)


class SweepTest(unittest.TestCase):
    def test_random_and_near_edge_sweep_against_the_oracle(self):
        rng = random.Random(67)
        for i in range(20000):
            if i % 2:
                sun, moon = rng.uniform(0, 360), rng.uniform(0, 360)
            else:
                sun = rng.uniform(0, 360)
                edge = Fraction(sun) + Fraction(6 * rng.randrange(60))
                moon = float(edge % 360)
                moon = rng.choice((moon, math.nextafter(moon, 0), math.nextafter(moon, 360)))
            self.assertEqual(rules.element_sectors(sun, moon), oracle.all_sectors(sun, moon), (sun, moon))
            e = rules.elongation(sun, moon)
            t = oracle.tithi(sun, moon)
            n = rules.tithi_number(e)
            self.assertEqual((n, rules.paksha(n), rules.paksha_day(n)), (t["number"], t["paksha"], t["paksha_day"]))
            self.assertEqual(rules.karana_index(e), oracle.karana_index(sun, moon))
            self.assertEqual(rules.yoga_index(rules.yoga_sum(sun, moon)), oracle.yoga_index(sun, moon))


class NoNamesInCodeTest(unittest.TestCase):
    """D07-A, D16-M1-INDEX: no Tithi, Karana or Yoga name table in M1 code."""

    def test_package_source_has_no_forbidden_names(self):
        pattern = re.compile(r"\b(" + "|".join(FORBIDDEN_NAMES) + r")\b", re.IGNORECASE)
        for path in sorted(PKG.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(pattern.search(text), f"{path.name} contains a name string")

    def test_package_imports_no_sunrise_or_crossing_function(self):
        banned = {"rise_trans", "rise_trans_true_hor", "mooncross_ut", "solcross_ut", "mooncross_node_ut",
                  "set_topo", "FLG_SPEED", "FLG_TOPOCTR", "FLG_MOSEPH", "FLG_JPLEPH"}
        for path in sorted(PKG.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)}
            names |= {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
            self.assertFalse(names & banned, f"{path.name}: {sorted(names & banned)}")


def _strings(node, path=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(v, path + (k,))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _strings(v, path + (i,))
    elif isinstance(node, str):
        yield path, node


def _keys(node):
    if isinstance(node, dict):
        for k, v in node.items():
            yield k
            yield from _keys(v)
    elif isinstance(node, list):
        for v in node:
            yield from _keys(v)


@real_data
class OutputContractTest(unittest.TestCase):
    """D02-M1, D07-A, D16-M1-INDEX, D18-A on real documents."""

    @classmethod
    def setUpClass(cls):
        from sabpuja_kundali.panchanga import calculate
        cls.docs = [calculate(request_at_utc(parse_utc(t)), EPHE) for t in
                    ("2026-01-03T07:30:00Z", "2026-05-09T18:00:00Z", "1999-12-31T23:59:59Z", "2075-07-04T12:00:00Z")]

    def test_no_sunrise_dependent_or_later_milestone_field(self):
        for doc in self.docs:
            keys = {str(k).lower() for k in _keys(doc)}
            for bad in FORBIDDEN_KEYS:
                self.assertFalse(any(bad in k for k in keys), bad)

    def test_only_name_strings_are_the_chart_nakshatra_identifiers(self):
        pattern = re.compile(r"\b(" + "|".join(FORBIDDEN_NAMES) + r")\b", re.IGNORECASE)
        for doc in self.docs:
            text = json.dumps(doc)
            self.assertIsNone(pattern.search(text))
            for element in ("tithi", "karana", "yoga", "nakshatra"):
                for path, value in _strings(doc[element]):
                    key = path[-1]
                    allowed = {"paksha": {"shukla", "krishna"}, "name_omitted": {"PANCHANGA_METHOD_NOT_ADOPTED"},
                               "name": set(chart_rules.NAKSHATRAS), "local_rendering": {"rendered", "withheld_outside_envelope"}}
                    if key in ("utc", "local"):
                        continue
                    self.assertIn(key, allowed, (element, path))
                    self.assertIn(value, allowed[key])
            self.assertNotIn("name", doc["karana"])
            self.assertNotIn("name", doc["yoga"])
            self.assertNotIn("name", doc["tithi"])

    def test_tithi_fields_and_ranges(self):
        for doc in self.docs:
            t = doc["tithi"]
            self.assertTrue(1 <= t["number"] <= 30)
            self.assertEqual(t["paksha"], "shukla" if t["number"] <= 15 else "krishna")
            self.assertEqual(t["paksha_day"], (t["number"] - 1) % 15 + 1)
            self.assertTrue(1 <= doc["karana"]["index"] <= 60)
            self.assertTrue(1 <= doc["yoga"]["index"] <= 27)
            self.assertEqual(doc["schema"], "sabpuja-panchanga/1")


if __name__ == "__main__":
    unittest.main()
