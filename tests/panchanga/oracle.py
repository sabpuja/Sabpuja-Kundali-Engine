"""Independent exact-rational Panchanga rule oracle (PAN-QA-01). Standard library only.

Written separately from production: it never imports `sabpuja_kundali`, never
uses floor division of a scaled value, and finds a sector by comparing the
exact value with explicitly constructed rational edges k * 360 / n. Every float
is converted to its exact binary value with Fraction before any arithmetic.
"""
from __future__ import annotations

from fractions import Fraction

FULL = Fraction(360)


def exact(x) -> Fraction:
    if isinstance(x, bool):
        raise TypeError("bool is not a longitude")
    return Fraction(x)


def reduce360(x) -> Fraction:
    """Exact reduction into [0, 360) by repeated whole-circle steps, not by %."""
    value = exact(x)
    if value >= 0:
        turns = value.numerator // (value.denominator * 360)
    else:
        turns = -((-value.numerator) // (value.denominator * 360)) - (0 if (-value) % 360 == 0 else 1)
    value -= turns * FULL
    while value < 0:
        value += FULL
    while value >= FULL:
        value -= FULL
    return value


def sector(x, n: int) -> int:
    """Zero-based k with k*360/n <= x < (k+1)*360/n, by bisection over the edge list."""
    value = reduce360(x)
    lo, hi = 0, n            # invariant: edge(lo) <= value < edge(hi)
    edge = lambda k: Fraction(360 * k, n)
    assert edge(lo) <= value < edge(hi)
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if edge(mid) <= value:
            lo = mid
        else:
            hi = mid
    return lo


def elongation(sun, moon) -> Fraction:
    return reduce360(exact(moon) - exact(sun))


def yoga_sum(sun, moon) -> Fraction:
    return reduce360(exact(sun) + exact(moon))


def tithi(sun, moon) -> dict:
    n = sector(elongation(sun, moon), 30) + 1
    return {"number": n, "paksha": "shukla" if n < 16 else "krishna",
            "paksha_day": n if n < 16 else n - 15}


def karana_index(sun, moon) -> int:
    return sector(elongation(sun, moon), 60) + 1


def yoga_index(sun, moon) -> int:
    return sector(yoga_sum(sun, moon), 27) + 1


def nakshatra_pada(moon) -> tuple[int, int]:
    """(zero-based nakshatra, pada 1..4) from 108 explicit edges."""
    p = sector(moon, 108)
    return p // 4, p - 4 * (p // 4) + 1


def all_sectors(sun, moon) -> dict:
    e, s = elongation(sun, moon), yoga_sum(sun, moon)
    return {"tithi": sector(e, 30), "karana": sector(e, 60), "yoga": sector(s, 27),
            "nakshatra": sector(moon, 27), "pada": sector(moon, 108)}


def distance_to_nearest_edge(x, n: int) -> Fraction:
    """Exact distance (degrees) from x to the nearest k*360/n edge, wrap included."""
    value = reduce360(x)
    k = sector(value, n)
    below = value - Fraction(360 * k, n)
    above = Fraction(360 * (k + 1), n) - value
    return min(below, above)
