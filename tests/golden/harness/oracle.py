"""Category oracle for reference longitudes (QA harness side only).

Written from the rule definitions in docs/accuracy/scientific-decisions.md
(SCI-02), not from sabpuja_kundali.rules, which it must never import.
Twelve 30-degree Rashis from Mesha; 27 Nakshatras of 13 deg 20 min from
Ashwini; four Padas of 3 deg 20 min; Navamsa counted cyclically from Mesha in
3 deg 20 min steps; whole-sign houses counted from the Lagna's Rashi.
Segments are half-open [start, end).
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
    "Uttara Bhadrapada", "Revati"
)


def _index(longitude_deg: float, count: int) -> int:
    if not math.isfinite(longitude_deg):
        raise ValueError("longitude must be finite")
    return math.floor(Fraction(longitude_deg) % 360 * count / 360)


def rashi(longitude_deg: float) -> str:
    return RASHIS[_index(longitude_deg, 12)]


def nakshatra(longitude_deg: float) -> tuple[str, int]:
    pada_index = _index(longitude_deg, 108)
    return NAKSHATRAS[pada_index // 4], pada_index % 4 + 1


def navamsa(longitude_deg: float) -> str:
    return RASHIS[_index(longitude_deg, 108) % 12]


def whole_sign_house(longitude_deg: float, lagna_deg: float) -> int:
    return (_index(longitude_deg, 12) - _index(lagna_deg, 12)) % 12 + 1


def d9_house(longitude_deg: float, lagna_deg: float) -> int:
    return (_index(longitude_deg, 108) % 12 - _index(lagna_deg, 108) % 12) % 12 + 1
