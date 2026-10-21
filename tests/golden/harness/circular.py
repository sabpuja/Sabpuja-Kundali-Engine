"""Circular angle arithmetic for golden comparisons.

Differences are always taken on the circle: 359.9999 vs 0.0001 is 0.72",
never 359.9998 degrees. Boundary distances use exact rationals so a float
division can never move a longitude across a segment edge.
"""
from __future__ import annotations

from fractions import Fraction
import math

ARCSEC_PER_DEG = 3600


def _finite(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return float(value)


def circular_diff_deg(engine_deg: float, reference_deg: float) -> float:
    """Signed engine - reference in degrees, in [-180, 180)."""
    a = Fraction(_finite(engine_deg, "engine_deg"))
    b = Fraction(_finite(reference_deg, "reference_deg"))
    return float((a - b + 180) % 360 - 180)


def circular_diff_arcsec(engine_deg: float, reference_deg: float) -> float:
    """Signed engine - reference in arcseconds, in [-648000, 648000)."""
    a = Fraction(_finite(engine_deg, "engine_deg"))
    b = Fraction(_finite(reference_deg, "reference_deg"))
    return float(((a - b + 180) % 360 - 180) * ARCSEC_PER_DEG)


def boundary_distance_arcsec(longitude_deg: float, segment_deg: Fraction) -> float:
    """Distance in arcseconds from longitude to the nearest multiple of segment_deg.

    segment_deg is exact: Fraction(30), Fraction(40, 3), Fraction(10, 3).
    """
    if not isinstance(segment_deg, Fraction) or segment_deg <= 0 or 360 % segment_deg:
        raise ValueError("segment_deg must be an exact Fraction dividing 360")
    r = Fraction(_finite(longitude_deg, "longitude_deg")) % segment_deg
    return float(min(r, segment_deg - r) * ARCSEC_PER_DEG)


RASHI_DEG = Fraction(30)
NAKSHATRA_DEG = Fraction(40, 3)
PADA_DEG = Fraction(10, 3)  # also the Navamsa (D9) segment
