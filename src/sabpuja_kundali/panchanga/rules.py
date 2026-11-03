"""Pure Panchanga M1 sector rules (KUN-PAN-M1; D08-A, D16-M1-INDEX, D18-A, D07-A).

Inputs are the unrounded sidereal Sun and Moon longitudes (floats from Swiss, or
exact rationals). E and S are formed exactly as rationals, reduced modulo 360
exactly, and classified with the canonical half-open chart helper
(`sabpuja_kundali.rules._sector`). No tolerance, no pre-rounding, no float
addition or subtraction of the two longitudes.

M1 emits indices and machine ids only: no Tithi, Karana or Yoga name strings
(D07-A, D16-M1-INDEX). The Nakshatra and Pada come from the chart's own rule.
"""
from __future__ import annotations

from fractions import Fraction
from numbers import Rational
import math

from ..rules import _sector, nakshatra

TITHI_COUNT = 30
KARANA_COUNT = 60
YOGA_COUNT = 27
NAKSHATRA_COUNT = 27
PADA_COUNT = 108

PAKSHA_SHUKLA = "shukla"
PAKSHA_KRISHNA = "krishna"


def _exact(longitude: float | Rational) -> Fraction:
    if isinstance(longitude, float) and not math.isfinite(longitude):
        raise ValueError("Longitude must be finite")
    if isinstance(longitude, bool) or not isinstance(longitude, (float, int, Rational)):
        raise TypeError("Longitude must be a float or an exact rational")
    return Fraction(longitude)


def elongation(sun: float | Rational, moon: float | Rational) -> Fraction:
    """E = (Moon - Sun) mod 360, exact. A negative raw difference gains 360 exactly."""
    return (_exact(moon) - _exact(sun)) % 360


def yoga_sum(sun: float | Rational, moon: float | Rational) -> Fraction:
    """S = (Sun + Moon) mod 360, exact; the sum is reduced, never the rounded addends."""
    return (_exact(sun) + _exact(moon)) % 360


def tithi_number(e: Rational) -> int:
    """1..30 from the half-open 12-degree sector of E."""
    return _sector(e, TITHI_COUNT) + 1


def paksha(number: int) -> str:
    if not 1 <= number <= TITHI_COUNT:
        raise ValueError("tithi number out of range")
    return PAKSHA_SHUKLA if number <= 15 else PAKSHA_KRISHNA


def paksha_day(number: int) -> int:
    if not 1 <= number <= TITHI_COUNT:
        raise ValueError("tithi number out of range")
    return (number - 1) % 15 + 1


def karana_index(e: Rational) -> int:
    """Half-tithi index 1..60 from the half-open 6-degree sector of E. No name (D07-A)."""
    return _sector(e, KARANA_COUNT) + 1


def yoga_index(s: Rational) -> int:
    """1..27 from the half-open 13 deg 20 min sector of S."""
    return _sector(s, YOGA_COUNT) + 1


def moon_nakshatra(moon: float | Rational) -> dict[str, object]:
    """Exactly the chart's `moon_nakshatra` rule and identifiers (rules.nakshatra)."""
    return nakshatra(moon)


# Zero-based sector of each M1 element at one instant. The transition search only
# compares these integers, so it never reads a rounded value.
def element_sectors(sun: float | Rational, moon: float | Rational) -> dict[str, int]:
    e = elongation(sun, moon)
    s = yoga_sum(sun, moon)
    pada_sector = _sector(moon, PADA_COUNT)
    return {
        "tithi": _sector(e, TITHI_COUNT),
        "karana": _sector(e, KARANA_COUNT),
        "yoga": _sector(s, YOGA_COUNT),
        "nakshatra": pada_sector // 4,
        "pada": pada_sector,
    }


ELEMENTS = ("tithi", "karana", "yoga", "nakshatra", "pada")
