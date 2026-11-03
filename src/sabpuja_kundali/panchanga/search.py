"""TS-1 bounded bracketing and bisection for sector transitions (D10-A, D09-A-M1).

Pure apart from the injected `sector_at(t_us) -> int`. Time is an exact integer
count of UTC microseconds since 1970-01-01T00:00:00Z (civil UTC labels, as the
chart uses them; SCI-01h treats civil UTC as UT1). No float time arithmetic.

From the reference instant t0, step 6 h in one direction until the sector
differs from the sector at t0, never further than 2.5 days; then bisect on the
predicate "sector equals the t0 sector" until the bracket is at most 0.5 s, in
at most 64 iterations. The result is the first whole UTC second at which the
far side of the bracket holds, verified by direct evaluation at that second
and the second before it. Nothing is extrapolated: no instant outside
t0 +/- 2.5 days is ever evaluated. Any cap, missing sector change or failed
verification is a typed `TransitionNotConverged`.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

MICROS = 1_000_000


@dataclass(frozen=True)
class SearchLimits:
    step_us: int = 6 * 3600 * MICROS                 # D09-A-M1 bracket_step_hours = 6
    max_extent_us: int = 5 * 12 * 3600 * MICROS      # 2.5 days = 60 h each direction
    max_iterations: int = 64                         # bisection_max_iterations
    bracket_max_us: int = MICROS // 2                # transition_bracket_max_seconds = 0.5


DEFAULT_LIMITS = SearchLimits()


class TransitionNotConverged(Exception):
    """Internal: the search could not safely produce an instant. `reason` is a fixed code."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


class NonFiniteValue(Exception):
    """Raised by a sector function when the underlying longitude is not finite."""


@dataclass(frozen=True)
class Transition:
    second: int              # first whole UTC second (Unix seconds) in the new sector
    direction: int           # +1 end of the current sector, -1 start
    bracket_steps: int       # 6 h steps taken until the sector changed
    iterations: int          # bisection iterations
    bracket_us: int          # final bracket width, microseconds (<= bracket_max_us)
    lo_us: int               # final bracket, time order
    hi_us: int


def _evaluate(sector_at: Callable[[int], int], t_us: int) -> int:
    try:
        value = sector_at(t_us)
    except NonFiniteValue:
        raise TransitionNotConverged("NON_FINITE_VALUE") from None
    if type(value) is not int:
        raise TransitionNotConverged("NON_INTEGER_SECTOR")
    return value


def _within_extent(t_us: int, t0_us: int, limits: SearchLimits) -> None:
    if abs(t_us - t0_us) > limits.max_extent_us:
        raise TransitionNotConverged("OUTSIDE_SEARCH_EXTENT")


def find_transition(sector_at: Callable[[int], int], t0_us: int, direction: int,
                    limits: SearchLimits = DEFAULT_LIMITS) -> Transition:
    """Find the end (direction +1) or the start (direction -1) of the sector holding t0."""
    if direction not in (1, -1):
        raise ValueError("direction must be +1 or -1")
    if (limits.step_us <= 0 or limits.max_extent_us <= 0 or limits.max_iterations < 0
            or limits.bracket_max_us <= 0):
        raise ValueError("invalid search limits")
    k0 = _evaluate(sector_at, t0_us)
    inside = t0_us
    outside = None
    steps = 0
    while True:
        offset = (steps + 1) * limits.step_us
        if offset > limits.max_extent_us:
            break
        steps += 1
        t = t0_us + direction * offset
        if _evaluate(sector_at, t) != k0:
            outside = t
            break
        inside = t
    if outside is None:
        raise TransitionNotConverged("NO_SECTOR_CHANGE_WITHIN_EXTENT")
    # Time-ordered bracket; `in_lo` is the predicate value at lo.
    lo, hi = (inside, outside) if direction == 1 else (outside, inside)
    in_lo = direction == 1
    iterations = 0
    while hi - lo > limits.bracket_max_us:
        if iterations >= limits.max_iterations:
            raise TransitionNotConverged("ITERATION_CAP_REACHED")
        iterations += 1
        mid = (lo + hi) // 2
        if (_evaluate(sector_at, mid) == k0) == in_lo:
            lo = mid
        else:
            hi = mid
    # First whole second strictly after lo (lo itself is on the old side).
    candidate = lo // MICROS + 1
    if candidate * MICROS < hi:
        _within_extent(candidate * MICROS, t0_us, limits)
        if (_evaluate(sector_at, candidate * MICROS) == k0) == in_lo:
            candidate += 1
    # Verify by direct evaluation: the second before is on lo's side, the result on hi's side.
    # Both instants must lie inside the search extent; nothing outside it is evaluated.
    for t in (candidate * MICROS, (candidate - 1) * MICROS):
        _within_extent(t, t0_us, limits)
    if ((_evaluate(sector_at, candidate * MICROS) == k0) == in_lo
            or (_evaluate(sector_at, (candidate - 1) * MICROS) == k0) != in_lo):
        raise TransitionNotConverged("WHOLE_SECOND_VERIFICATION_FAILED")
    return Transition(second=candidate, direction=direction, bracket_steps=steps,
                      iterations=iterations, bracket_us=hi - lo, lo_us=lo, hi_us=hi)
