"""Independent rule oracle for the Swiss-conformance suite.

Written from the rule definitions, not from sabpuja_kundali.rules, and using
exact rationals only: a longitude is taken as the exact value of its float
(or a Fraction), reduced modulo 360 and floored, so no float division can
move it across a half-open [start, end) segment edge.

- Rashi: 12 x 30 deg from Mesha.
- Nakshatra: 27 x 13 deg 20 min from Ashwini; Pada: 4 x 3 deg 20 min each.
- Navamsa (D9): the 108 Padas map cyclically onto the Rashis from Mesha.
- Whole-sign house: Rashi distance from the Lagna's Rashi, 1..12.
- D9 house: whole-sign distance between the D9 Rashis of body and D9 Lagna.
"""
from __future__ import annotations

from fractions import Fraction
import math

RASHIS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
          "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena")
NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
)
FULL = Fraction(360)
RASHI_SPAN = Fraction(30)
NAKSHATRA_SPAN = Fraction(40, 3)
PADA_SPAN = Fraction(10, 3)


def exact(longitude) -> Fraction:
    """Exact value of a float or rational longitude in [0, 360)."""
    if isinstance(longitude, bool) or not isinstance(longitude, (int, float, Fraction)):
        raise TypeError("longitude must be a number")
    if isinstance(longitude, float) and not math.isfinite(longitude):
        raise ValueError("longitude must be finite")
    return Fraction(longitude) % FULL


def segment(longitude, span: Fraction) -> int:
    return math.floor(exact(longitude) / span)


def rashi_index(longitude) -> int:
    return segment(longitude, RASHI_SPAN)


def rashi(longitude) -> str:
    return RASHIS[rashi_index(longitude)]


def pada_index(longitude) -> int:
    """0..107 over the whole circle."""
    return segment(longitude, PADA_SPAN)


def nakshatra(longitude) -> tuple[str, int]:
    index = pada_index(longitude)
    return NAKSHATRAS[index // 4], index % 4 + 1


def navamsa(longitude) -> str:
    return RASHIS[pada_index(longitude) % 12]


def whole_sign_house(longitude, lagna) -> int:
    return (rashi_index(longitude) - rashi_index(lagna)) % 12 + 1


def d9_house(longitude, lagna) -> int:
    return (pada_index(longitude) % 12 - pada_index(lagna) % 12) % 12 + 1


def boundary_distance(longitude, span: Fraction = PADA_SPAN) -> Fraction:
    """Exact distance in degrees to the nearest segment edge (Pada edges include all others)."""
    r = exact(longitude) % span
    return min(r, span - r)


def gregorian_jd(year: int, month: int, day: int, hour: int = 0, minute: int = 0,
                 second: int = 0, microsecond: int = 0) -> Fraction:
    """Exact Julian Day of a proleptic Gregorian UT instant (Fliegel & Van Flandern day number)."""
    a = (14 - month) // 12
    y = year + 4800 - a
    m = month + 12 * a - 3
    jdn = day + (153 * m + 2) // 5 + 365 * y + y // 4 - y // 100 + y // 400 - 32045
    seconds = Fraction(hour * 3600 + minute * 60 + second) + Fraction(microsecond, 1_000_000)
    return Fraction(jdn) - Fraction(1, 2) + seconds / 86400
