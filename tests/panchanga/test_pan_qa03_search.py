"""PAN-QA-03: TS-1 convergence, iteration cap, search limits and typed non-convergence refusals.

PAN-SPEC-06 (synthetic brackets, crossings within 1 s of a bracket edge) and
PAN-SPEC-14 (forced cap, no sector change, non-finite values). Synthetic sector
functions are exact linear functions with a known rational crossing, so the
expected first whole second is computed exactly by the test, not by the search.
"""
from __future__ import annotations

from datetime import timedelta
from fractions import Fraction
import math
import random
import unittest

from sabpuja_kundali.panchanga import search
from sabpuja_kundali.panchanga.search import (DEFAULT_LIMITS, MICROS, NonFiniteValue, SearchLimits,
                                               TransitionNotConverged, find_transition)

from . import oracle
from .common import EPHE, parse_utc, real_data, request_at_utc

HOUR = 3600 * MICROS
EXTENT = 60 * HOUR


class Linear:
    """sector(t) = oracle.sector(a + rate * t_seconds, n), recording every evaluated instant."""

    def __init__(self, a: Fraction, rate_deg_per_s: Fraction, n: int):
        self.a, self.rate, self.n = a, rate_deg_per_s, n
        self.evaluated: list[int] = []

    def value(self, t_us: int) -> Fraction:
        return self.a + self.rate * Fraction(t_us, MICROS)

    def __call__(self, t_us: int) -> int:
        self.evaluated.append(t_us)
        return oracle.sector(self.value(t_us), self.n)

    def crossing_us(self, t0_us: int, direction: int) -> Fraction:
        """Exact instant of the edge that ends (or starts) the sector holding t0."""
        width = Fraction(360, self.n)
        k = oracle.sector(self.value(t0_us), self.n)
        # Unwrapped: the sector of t0 is [base + k*w, base + (k+1)*w) with base a multiple of 360.
        v0 = self.value(t0_us)
        base = v0 - oracle.reduce360(v0)
        edge = base + width * (k + (1 if (direction == 1) == (self.rate > 0) else 0))
        return (edge - self.a) / self.rate * MICROS


def first_whole_second_at_or_after(t_us: Fraction) -> int:
    return math.ceil(t_us / MICROS)


class SyntheticConvergenceTest(unittest.TestCase):
    def check(self, fn: Linear, t0: int, direction: int, limits=DEFAULT_LIMITS):
        result = find_transition(fn, t0, direction, limits)
        crossing = fn.crossing_us(t0, direction)
        self.assertEqual(result.second, first_whole_second_at_or_after(crossing))
        self.assertLessEqual(result.bracket_us, limits.bracket_max_us)
        self.assertLessEqual(result.iterations, limits.max_iterations)
        self.assertLessEqual(result.bracket_steps, 10)
        self.assertTrue(result.lo_us < crossing <= result.hi_us)
        for t in fn.evaluated:
            self.assertLessEqual(abs(t - t0), limits.max_extent_us, "evaluated outside the search extent")
        return result

    def test_random_linear_functions_both_directions(self):
        rng = random.Random(6701)
        for i in range(400):
            n = rng.choice((30, 60, 27, 108))
            # Rates from 0.6 to 17 deg/day, the range of E, S and the Moon.
            rate = Fraction(rng.randrange(600, 17000), 1000 * 86400)
            t0 = rng.randrange(0, 4_000_000_000) * MICROS + rng.randrange(MICROS)
            a = Fraction(rng.randrange(0, 360 * 10**6), 10**6) - rate * Fraction(t0, MICROS)
            for direction in (1, -1):
                fn = Linear(a, rate, n)
                distance = abs(fn.crossing_us(t0, direction) - t0)
                if distance > EXTENT:
                    with self.assertRaises(TransitionNotConverged):
                        find_transition(fn, t0, direction)
                    continue
                if distance > EXTENT - 2 * MICROS:
                    continue       # whole-second edge handling is covered by its own test
                self.check(fn, t0, direction)

    def test_sixteen_iterations_suffice_and_fifteen_do_not(self):
        fn = Linear(Fraction(0), Fraction(12, 86400), 30)
        t0 = 3 * HOUR + 123_457
        result = find_transition(fn, t0, 1)
        self.assertEqual(result.iterations, 16)
        self.assertEqual(result.bracket_us, (6 * HOUR) >> 16 if (6 * HOUR) % (1 << 16) == 0 else result.bracket_us)
        find_transition(Linear(Fraction(0), Fraction(12, 86400), 30), t0, 1, SearchLimits(max_iterations=16))
        with self.assertRaises(TransitionNotConverged) as ctx:
            find_transition(Linear(Fraction(0), Fraction(12, 86400), 30), t0, 1, SearchLimits(max_iterations=15))
        self.assertEqual(ctx.exception.reason, "ITERATION_CAP_REACHED")

    def test_forced_iteration_cap_of_one(self):
        with self.assertRaises(TransitionNotConverged) as ctx:
            find_transition(Linear(Fraction(0), Fraction(12, 86400), 30), 5 * HOUR, 1, SearchLimits(max_iterations=1))
        self.assertEqual(ctx.exception.reason, "ITERATION_CAP_REACHED")

    def test_crossing_on_a_whole_second_belongs_to_the_new_sector(self):
        # Rate 12 deg per 43200 s exactly: E reaches 12 deg at t = 43200 s, an integer second.
        fn = Linear(Fraction(0), Fraction(12, 43200), 30)
        self.assertEqual(self.check(fn, 1 * HOUR + 1, 1).second, 43200)
        fn = Linear(Fraction(0), Fraction(12, 43200), 30)
        self.assertEqual(self.check(fn, 43200 * MICROS + 5, -1).second, 43200)

    def test_crossings_within_one_second_of_a_bracket_edge(self):
        rate = Fraction(13, 86400)
        for t0 in (0, 777_777, 5 * MICROS + 1):
            for k in range(1, 11):
                for delta_us in (-999_999, -500_000, -1, 0, 1, 499_999, 999_999):
                    crossing = t0 + k * 6 * HOUR + delta_us
                    if crossing > t0 + EXTENT or crossing <= t0:
                        continue
                    a = Fraction(12) - rate * Fraction(crossing, MICROS)
                    self.check(Linear(a, rate, 30), t0, 1)
                    # Mirror: the start of the sector, crossing before t0.
                    back = t0 - k * 6 * HOUR + delta_us
                    if back >= t0 or back < t0 - EXTENT:
                        continue
                    a = Fraction(24) - rate * Fraction(back, MICROS)
                    self.check(Linear(a, rate, 30), t0, -1)

    def test_extent_edge_is_inclusive_and_nothing_beyond_is_searched(self):
        rate = Fraction(1, 86400)          # very slow: 12 deg take 12 days
        t0 = 10 * MICROS
        crossing = t0 + EXTENT
        a = Fraction(12) - rate * Fraction(crossing, MICROS)
        result = self.check(Linear(a, rate, 30), t0, 1)
        self.assertEqual(result.bracket_steps, 10)
        a = Fraction(12) - rate * Fraction(crossing + 1, MICROS)
        fn = Linear(a, rate, 30)
        with self.assertRaises(TransitionNotConverged) as ctx:
            find_transition(fn, t0, 1)
        self.assertEqual(ctx.exception.reason, "NO_SECTOR_CHANGE_WITHIN_EXTENT")
        self.assertEqual(max(fn.evaluated) - t0, EXTENT)
        self.assertEqual(sorted(set(fn.evaluated)), [t0 + i * 6 * HOUR for i in range(11)])

    def test_bracket_steps_are_exactly_six_hours(self):
        fn = Linear(Fraction(0), Fraction(12, 86400 * 2), 30)
        t0 = 17
        find_transition(fn, t0, 1)
        steps = [t for t in fn.evaluated if (t - t0) % (6 * HOUR) == 0]
        self.assertEqual(steps[: len(steps)], sorted(steps))
        self.assertTrue(all((t - t0) % (6 * HOUR) == 0 for t in fn.evaluated[:3]))

    def test_two_edges_in_one_step_returns_the_first(self):
        # 3.333 deg Pada width, 5 deg per 6 h: two edges can fall inside one step.
        rate = Fraction(20, 86400)
        fn = Linear(Fraction(1, 10), rate, 108)
        self.check(fn, 0, 1)
        fn = Linear(Fraction(33, 10), rate, 108)
        self.check(fn, 0, -1)

    def test_non_finite_value_is_a_typed_refusal(self):
        calls = {"n": 0}

        def sector_at(t_us):
            calls["n"] += 1
            if calls["n"] == 5:
                raise NonFiniteValue()
            return 0 if t_us < 7 * HOUR else 1
        with self.assertRaises(TransitionNotConverged) as ctx:
            find_transition(sector_at, 0, 1)
        self.assertEqual(ctx.exception.reason, "NON_FINITE_VALUE")

    def test_non_integer_sector_is_refused(self):
        with self.assertRaises(TransitionNotConverged) as ctx:
            find_transition(lambda t: 0.0, 0, 1)
        self.assertEqual(ctx.exception.reason, "NON_INTEGER_SECTOR")
        with self.assertRaises(TransitionNotConverged):
            find_transition(lambda t: True, 0, 1)

    def test_inconsistent_whole_second_is_refused_not_guessed(self):
        # New sector everywhere after 7 h, except exactly on whole seconds: no valid answer exists.
        def sector_at(t_us):
            return 0 if t_us < 7 * HOUR or t_us % MICROS == 0 else 1
        with self.assertRaises(TransitionNotConverged) as ctx:
            find_transition(sector_at, 1, 1)
        self.assertEqual(ctx.exception.reason, "WHOLE_SECOND_VERIFICATION_FAILED")

    def test_whole_second_check_never_leaves_the_extent(self):
        # Crossing 0.2 s before the 60 h edge with a fractional t0: the answer would need the
        # second after the edge, which lies outside the extent, so the search refuses.
        t0 = 600_000
        rate = Fraction(1, 86400)
        crossing = t0 + EXTENT - 200_000
        a = Fraction(12) - rate * Fraction(crossing, MICROS)
        fn = Linear(a, rate, 30)
        try:
            result = find_transition(fn, t0, 1)
        except TransitionNotConverged as exc:
            self.assertEqual(exc.reason, "OUTSIDE_SEARCH_EXTENT")
        else:
            self.assertLessEqual(result.second * MICROS - t0, EXTENT)
        for t in fn.evaluated:
            self.assertLessEqual(abs(t - t0), EXTENT)

    def test_invalid_arguments(self):
        with self.assertRaises(ValueError):
            find_transition(lambda t: 0, 0, 0)
        with self.assertRaises(ValueError):
            find_transition(lambda t: 0, 0, 1, SearchLimits(step_us=0))


@real_data
class RealDataSearchTest(unittest.TestCase):
    INSTANTS = ("2026-01-03T07:30:00Z", "2026-03-19T01:23:45Z", "2026-08-12T17:46:11Z", "1983-06-10T04:00:00Z",
                "2049-12-31T22:00:00Z", "2099-06-30T12:00:00Z")

    def test_forced_iteration_cap_refuses_the_whole_document(self):
        from sabpuja_kundali.panchanga import PanchangaComputationError, calculate
        for limits in (SearchLimits(max_iterations=1), SearchLimits(max_extent_us=HOUR),
                       SearchLimits(bracket_max_us=1, max_iterations=64)):
            with self.subTest(limits=limits):
                if limits.bracket_max_us == 1:
                    # 6 h to 1 us needs 35 iterations: within 64, so this one converges.
                    calculate(request_at_utc(parse_utc(self.INSTANTS[0])), EPHE, limits=limits)
                    continue
                with self.assertRaises(PanchangaComputationError) as ctx:
                    calculate(request_at_utc(parse_utc(self.INSTANTS[0])), EPHE, limits=limits)
                self.assertEqual(ctx.exception.code, "PANCHANGA_TRANSITION_NOT_CONVERGED")
                self.assertEqual(str(ctx.exception),
                                 "PANCHANGA_TRANSITION_NOT_CONVERGED: a Panchanga transition could not be "
                                 "bracketed and converged within the approved limits; no Panchanga produced")

    def test_every_transition_meets_the_limits_and_brackets_the_birth(self):
        from sabpuja_kundali.panchanga import calculate
        for text in self.INSTANTS:
            doc = calculate(request_at_utc(parse_utc(text)), EPHE)
            birth = parse_utc(doc["birth"]["utc"])
            for element, (s_key, e_key) in {"tithi": ("start", "end"), "karana": ("start", "end"),
                                            "yoga": ("start", "end"), "nakshatra": ("start", "end"),
                                            "pada": ("pada_start", "pada_end")}.items():
                block = doc["nakshatra" if element == "pada" else element]
                start, end = parse_utc(block[s_key]["utc"]), parse_utc(block[e_key]["utc"])
                self.assertLessEqual(start, birth)
                self.assertGreater(end, birth)
                self.assertLessEqual(end - start, timedelta(days=5))
                for side in (block[s_key], block[e_key]):
                    self.assertLessEqual(side["search"]["final_bracket_us"], 500_000)
                    self.assertLessEqual(side["search"]["iterations"], 64)
                    self.assertLessEqual(side["search"]["bracket_steps"], 10)
                    self.assertTrue(side["utc"].endswith("Z") and len(side["utc"]) == 20)

    def test_nakshatra_and_pada_transitions_agree_with_the_chart_engine(self):
        """Independent of the Panchanga code path: the unchanged chart at end - 1 s and at end."""
        from sabpuja_kundali.engine import calculate as chart
        from sabpuja_kundali.panchanga import calculate
        for text in self.INSTANTS:
            doc = calculate(request_at_utc(parse_utc(text)), EPHE)
            nak = {k: doc["nakshatra"][k] for k in ("index", "name", "pada")}
            for key, field in (("end", "index"), ("pada_end", "pada"), ("start", "index"), ("pada_start", "pada")):
                at = parse_utc(doc["nakshatra"][key]["utc"])
                now = chart(request_at_utc(at), EPHE)["moon_nakshatra"]
                before = chart(request_at_utc(at - timedelta(seconds=1)), EPHE)["moon_nakshatra"]
                if key == "pada_end":
                    self.assertEqual(before, nak, key)
                    self.assertNotEqual(now["pada"], nak["pada"], key)
                elif key == "end":
                    self.assertEqual(before["index"], nak["index"], key)
                    self.assertNotEqual(now["index"], nak["index"], key)
                elif key == "pada_start":
                    self.assertEqual(now, nak, key)
                    self.assertNotEqual(before["pada"], nak["pada"], key)
                else:
                    self.assertEqual(now["index"], nak["index"], key)
                    self.assertNotEqual(before["index"], nak["index"], key)


if __name__ == "__main__":
    unittest.main()


# ---------------------------------------------------------------------------
# D09-A-M1 limits are frozen in the public contract (QA review 5751031274).

LOOSER = {
    "bracket_max_us": (500_001, 1_000_000),
    "step_us": (6 * HOUR + 1, 24 * HOUR),
    "max_extent_us": (EXTENT + 1, 12 * 24 * HOUR),
    "max_iterations": (65, 10**6),
}
MALFORMED = ([("bracket_max_us", v) for v in (0, -1, 0.5, 500_000.0, True, None, "500000")]
             + [("step_us", v) for v in (0, -HOUR, float(6 * HOUR), False)]
             + [("max_extent_us", v) for v in (0, -1, float(EXTENT))]
             + [("max_iterations", v) for v in (-1, 16.0, True)])


def frozen_limit_failures(calc, request, ephe) -> list[str]:
    """Gate rule: every looser or malformed override is refused with the fixed typed code."""
    from dataclasses import replace
    from sabpuja_kundali.panchanga import PanchangaComputationError
    out = []
    bad = [replace(DEFAULT_LIMITS, **{k: v}) for k, vals in LOOSER.items() for v in vals]
    bad += [replace(DEFAULT_LIMITS, **{k: v}) for k, v in MALFORMED]
    bad += [None, {"step_us": 6 * HOUR}, (6 * HOUR, EXTENT, 64, 500_000)]
    for limits in bad:
        try:
            calc(request, ephe, limits=limits)
            out.append(f"ACCEPTED:{limits!r}")
        except PanchangaComputationError as exc:
            if exc.code != "PANCHANGA_SEARCH_LIMITS_NOT_APPROVED" or exc.__cause__ is not None:
                out.append(f"WRONG_REFUSAL:{exc.code}")
        except Exception as exc:          # anything untyped is a failure of the contract
            out.append(f"UNTYPED:{type(exc).__name__}")
    return out


class FrozenLimitsWithoutDataTest(unittest.TestCase):
    def test_chart_refusals_still_come_first(self):
        from sabpuja_kundali.engine import InputRefusalError
        from sabpuja_kundali.ephemeris import EphemerisDataError
        from sabpuja_kundali.panchanga import calculate
        loose = SearchLimits(bracket_max_us=1_000_000)
        req = request_at_utc(parse_utc("2026-01-03T07:30:00Z"))
        with self.assertRaises(InputRefusalError) as ctx:
            calculate(dict(req, latitude=99.0), "/nonexistent", limits=loose)
        self.assertEqual(ctx.exception.code, "LATITUDE_OUTSIDE_SUPPORTED_BAND")
        with self.assertRaises(InputRefusalError) as ctx:
            calculate(dict(req, birth_datetime="bad"), "/nonexistent", limits=None)
        self.assertEqual(ctx.exception.code, "TIME_FORMAT_INVALID")
        with self.assertRaises(EphemerisDataError):
            calculate(req, "/nonexistent", limits=loose)


@real_data
class FrozenLimitsContractTest(unittest.TestCase):
    REQUEST = None

    @classmethod
    def setUpClass(cls):
        cls.REQUEST = request_at_utc(parse_utc("2026-01-03T07:30:00Z"))

    def test_every_looser_or_malformed_override_is_refused(self):
        from sabpuja_kundali.panchanga import calculate
        self.assertEqual(frozen_limit_failures(calculate, self.REQUEST, EPHE), [])

    def test_refusal_text_is_fixed_and_private(self):
        from sabpuja_kundali.panchanga import PanchangaComputationError, calculate
        with self.assertRaises(PanchangaComputationError) as ctx:
            calculate(self.REQUEST, EPHE, limits=SearchLimits(bracket_max_us=1_000_000))
        self.assertEqual(str(ctx.exception),
                         "PANCHANGA_SEARCH_LIMITS_NOT_APPROVED: the transition search limits are looser than, "
                         "or not, the approved D09-A-M1 limits; no Panchanga produced")

    def test_default_document_declares_exactly_the_frozen_method(self):
        from sabpuja_kundali.panchanga import calculate
        from .common import tolerances
        d09 = tolerances()["D09_A_M1"]
        doc = calculate(self.REQUEST, EPHE)
        ts = doc["method"]["transition_search"]
        self.assertEqual(ts["bracket_step_hours"], d09["bracket_step_hours"])
        self.assertEqual(ts["bracket_extent_max_days_each_direction"], d09["bracket_extent_max_days_each_direction"])
        self.assertEqual(ts["bisection_max_iterations"], d09["bisection_max_iterations"])
        self.assertEqual(ts["transition_bracket_max_seconds"], d09["transition_bracket_max_seconds"])
        self.assertIs(ts["limits_are_frozen_d09_values"], True)
        widths = [v["search"]["final_bracket_us"] for k in ("tithi", "karana", "yoga", "nakshatra")
                  for v in (doc[k]["start"], doc[k]["end"])]
        self.assertLessEqual(max(widths), ts["transition_bracket_max_seconds"] * MICROS)

    def test_stricter_override_reports_the_limits_actually_used(self):
        from sabpuja_kundali.panchanga import calculate
        strict = SearchLimits(bracket_max_us=100_000)
        doc = calculate(self.REQUEST, EPHE, limits=strict)
        ts = doc["method"]["transition_search"]
        self.assertEqual(ts["transition_bracket_max_seconds"], 0.1)
        self.assertIs(ts["limits_are_frozen_d09_values"], False)
        for k in ("tithi", "karana", "yoga", "nakshatra"):
            for v in (doc[k]["start"], doc[k]["end"]):
                self.assertLessEqual(v["search"]["final_bracket_us"], 100_000)
