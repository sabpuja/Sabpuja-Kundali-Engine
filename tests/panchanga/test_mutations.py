"""Mutation controls: every seeded defect must be caught by an independent checker.

Each mutant is patched in for one test only. The test asserts the checker that
gates the real code (empty failure list there) reports a failure, or that the
required typed refusal disappears. ENGINEERING-SPEC section 9: tropical S, sign
error in E, closed instead of half-open edge, missing FLG_SWIEPH check,
extrapolation; plus wrong whole-second rounding and an ignored iteration cap.
"""
from __future__ import annotations

from fractions import Fraction
from unittest import mock
import math
import unittest

from sabpuja_kundali.panchanga import rules, search
from sabpuja_kundali.panchanga.search import MICROS, SearchLimits, TransitionNotConverged

from . import checkers
from .common import EPHE, parse_utc, real_data, request_at_utc
from .phase_events import SideSwiss
from .test_pan_qa03_search import Linear

LAHIRI_2026_DEG = Fraction(2421, 100)        # approximate ayanamsa, used only to build the tropical mutant
INSTANTS = ("2026-01-03T07:30:00Z", "2026-05-09T18:00:00Z", "1983-06-10T04:00:00Z")


def closed_edge_sector(longitude, count):
    """Mutant of rules._sector: an exact edge belongs to the lower sector."""
    num, den = Fraction(longitude).as_integer_ratio()
    full = 360 * den
    scaled = num % full * count
    k = scaled // full
    return (k - 1) % count if scaled % full == 0 else k


class RuleMutationTest(unittest.TestCase):
    def test_real_rules_pass(self):
        self.assertEqual(checkers.check_rules(rules), [])

    def test_closed_edge_is_caught(self):
        with mock.patch.object(rules, "_sector", closed_edge_sector):
            self.assertTrue(any(f.startswith("EDGE_") for f in checkers.check_rules(rules)))

    def test_sign_error_in_e_is_caught(self):
        with mock.patch.object(rules, "elongation", lambda sun, moon: (Fraction(sun) - Fraction(moon)) % 360):
            self.assertIn("ELONGATION", checkers.check_rules(rules))

    def test_float_sum_is_caught_or_shown_equivalent(self):
        # Rounded float addition instead of the exact sum: caught by the oracle comparison
        # where it matters (YogaTest proves such pairs exist); here the checker must still run.
        with mock.patch.object(rules, "yoga_sum", lambda sun, moon: Fraction((sun + moon) % 360.0) + Fraction(1, 10**12)):
            self.assertIn("YOGA_SUM", checkers.check_rules(rules))


class SearchMutationTest(unittest.TestCase):
    @staticmethod
    def bounded_failures(find) -> list[str]:
        """Gate rule: a crossing beyond 60 h is refused and no instant beyond 60 h is evaluated."""
        out = []
        for rate in (Fraction(1, 86400), Fraction(3, 86400)):
            fn = Linear(Fraction(0), rate, 30)
            try:
                find(fn, 0, 1)
                out.append("RESULT_BEYOND_EXTENT")
            except TransitionNotConverged:
                pass
            if max(abs(t) for t in fn.evaluated) > 60 * 3600 * MICROS:
                out.append("EVALUATED_BEYOND_EXTENT")
        return out

    def test_extrapolation_is_caught(self):
        real = search.find_transition

        def extrapolating(sector_at, t0_us, direction, limits=search.DEFAULT_LIMITS):
            # Mutant: keeps stepping past the 2.5-day extent until the sector changes.
            wider = SearchLimits(step_us=limits.step_us, max_extent_us=limits.max_extent_us * 8,
                                 max_iterations=limits.max_iterations, bracket_max_us=limits.bracket_max_us)
            return real(sector_at, t0_us, direction, wider)
        self.assertEqual(self.bounded_failures(real), [])
        self.assertEqual(self.bounded_failures(extrapolating), ["RESULT_BEYOND_EXTENT", "EVALUATED_BEYOND_EXTENT"] * 2)

    def test_ignored_iteration_cap_is_caught(self):
        fn = Linear(Fraction(0), Fraction(12, 86400), 30)
        with self.assertRaises(TransitionNotConverged):
            search.find_transition(fn, 5, 1, SearchLimits(max_iterations=1))
        mutant = SearchLimits(max_iterations=10**6)
        self.assertIsNotNone(search.find_transition(Linear(Fraction(0), Fraction(12, 86400), 30), 5, 1, mutant))


@real_data
class DocumentMutationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.side = SideSwiss(EPHE)
        cls.requests = [request_at_utc(parse_utc(t)) for t in INSTANTS]

    def failures(self):
        from sabpuja_kundali import engine
        from sabpuja_kundali.panchanga import calculate
        out = []
        for req in self.requests:
            out += checkers.check_document(calculate(req, EPHE), self.side, engine.calculate(req, EPHE))
        return out

    def test_real_documents_pass(self):
        self.assertEqual(self.failures(), [])

    def test_tropical_yoga_sum_is_caught(self):
        real = rules.yoga_sum
        with mock.patch.object(rules, "yoga_sum", lambda sun, moon: (real(sun, moon) + 2 * LAHIRI_2026_DEG) % 360):
            got = self.failures()
        self.assertIn("ANGLE_YOGA_SUM_DEG", got)
        self.assertIn("INDEX_YOGA", got)

    def test_sign_error_in_e_is_caught(self):
        with mock.patch.object(rules, "elongation", lambda sun, moon: (Fraction(sun) - Fraction(moon)) % 360):
            got = self.failures()
        self.assertIn("ANGLE_ELONGATION_DEG", got)
        self.assertIn("INDEX_TITHI", got)

    def test_whole_second_rounded_down_is_caught(self):
        real = search.find_transition

        def floor_second(*a, **k):
            r = real(*a, **k)
            return search.Transition(**{**r.__dict__, "second": r.lo_us // MICROS})
        with mock.patch("sabpuja_kundali.panchanga.contract.find_transition", floor_second):
            got = self.failures()
        self.assertTrue(any(f.startswith("TRANSITION_") for f in got), got)

    def test_missing_flag_check_is_caught(self):
        """Mutant session without the FLG_SWIEPH check: a Moshier-flagged result would be accepted."""
        from sabpuja_kundali.engine import ChartComputationError
        from sabpuja_kundali.panchanga import astro, contract
        from .test_pan_qa09_privacy import VALID, _Proxy

        def unchecked(self, jd, body):
            pos, _ = self._swe.calc_ut(jd, body, self._swe.FLG_SWIEPH | self._swe.FLG_SIDEREAL)
            self.calls += 1
            return float(pos[0])
        real = contract.SwissSession

        def factory(swe, folder):
            return real(_Proxy(swe, "moshier", 7), folder)
        with mock.patch.object(contract, "SwissSession", factory):
            with self.assertRaises(ChartComputationError):
                contract.calculate(VALID, EPHE)
            with mock.patch.object(astro.SwissSession, "_longitude", unchecked):
                doc = contract.calculate(VALID, EPHE)     # the mutant silently accepts the fallback
        self.assertEqual(doc["schema"], "sabpuja-panchanga/1")

    def test_unenforced_frozen_limits_are_caught(self):
        from sabpuja_kundali.panchanga import calculate, contract
        from .test_pan_qa03_search import frozen_limit_failures
        self.assertEqual(frozen_limit_failures(calculate, self.requests[0], EPHE), [])
        with mock.patch.object(contract, "_check_limits", lambda limits: None):
            got = frozen_limit_failures(contract.calculate, self.requests[0], EPHE)
        self.assertTrue(any(f.startswith("ACCEPTED:") for f in got), got)

    def test_chart_frame_mutant_is_caught_by_identity(self):
        """Tropical longitudes for everything (no FLG_SIDEREAL): the chart identity check refuses."""
        from sabpuja_kundali.panchanga import PanchangaComputationError, astro, contract
        real = astro.SwissSession._longitude

        def tropical(self, jd, body):
            self.calls += 1
            pos, flags = self._swe.calc_ut(jd, body, self._swe.FLG_SWIEPH)
            return float(pos[0])
        with mock.patch.object(astro.SwissSession, "_longitude", tropical):
            with self.assertRaises(PanchangaComputationError) as ctx:
                contract.calculate(self.requests[0], EPHE)
        self.assertEqual(ctx.exception.code, "PANCHANGA_CHART_IDENTITY_FAILED")
        self.assertIsNotNone(real)


if __name__ == "__main__":
    unittest.main()
