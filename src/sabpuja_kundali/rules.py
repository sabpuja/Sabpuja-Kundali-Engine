"""Pure Vedic chart helpers. Longitude must be sidereal degrees.

Sector selection is exact: the longitude's exact binary value (or an exact
rational such as a Fraction) is reduced modulo 360 and floored with integer
arithmetic, so no float division can move a value across a half-open
[start, end) boundary. No tolerance or pre-rounding is applied.
"""
from __future__ import annotations

import math
from numbers import Rational

SIGNS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena")
NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati"
)

# Largest float below 360: the top of the normalized range [0, 360).
_BELOW_360 = math.nextafter(360.0, 0.0)


def normalize(longitude: float) -> float:
    """Return a float in [0, 360) for display; classification never reads it."""
    if not math.isfinite(longitude):
        raise ValueError("Longitude must be finite")
    pos = longitude % 360.0
    # A negative input within half an ulp of a multiple of 360 rounds up to
    # 360.0. Its true angle lies just below 360, so keep it in the last sector.
    return _BELOW_360 if pos == 360.0 else pos


def _sector(longitude: float | Rational, count: int) -> int:
    """Zero-based index of the half-open 360/count degree sector holding longitude."""
    if isinstance(longitude, float) and not math.isfinite(longitude):
        raise ValueError("Longitude must be finite")
    num, den = longitude.as_integer_ratio()
    full_circle = 360 * den
    return num % full_circle * count // full_circle


def sign_index(longitude: float | Rational) -> int:
    return _sector(longitude, 12)


def sign(longitude: float | Rational) -> str:
    return SIGNS[sign_index(longitude)]


def nakshatra(longitude: float | Rational) -> dict[str, object]:
    pada_index = _sector(longitude, 108)
    index = pada_index // 4
    return {"index": index, "name": NAKSHATRAS[index], "pada": pada_index % 4 + 1}


def navamsa_sign(longitude: float | Rational) -> str:
    """D9 sign by 3 degree 20 minute sidereal segments across zodiac."""
    return SIGNS[_sector(longitude, 108) % 12]


def whole_sign_house(longitude: float | Rational, ascendant: float | Rational) -> int:
    return (sign_index(longitude) - sign_index(ascendant)) % 12 + 1


def navamsa_sign_index(longitude: float | Rational) -> int:
    """Zero-based D9 sign (0 Mesha .. 11 Meena); navamsa_sign names the same index."""
    return _sector(longitude, 108) % 12


def navamsa_whole_sign_house(longitude: float | Rational, ascendant: float | Rational) -> int:
    """D9 whole-sign house counted from the D9 Lagna sign (SCI-01f; Gate 3E proposal)."""
    return (navamsa_sign_index(longitude) - navamsa_sign_index(ascendant)) % 12 + 1
