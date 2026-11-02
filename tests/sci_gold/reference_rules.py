"""KUN-SCI-GOLD-001 independent D1/D9 reference rules (test-only, isolated).

Written from the rule text of the canonical decisions (main:docs/DECISIONS.md,
SCI-01f ledger row 12 and SCI-02 C2) and the classical Parashari definition of
the Navamsa, NOT from the production code. It deliberately uses a different
algorithm from production `sabpuja_kundali.rules` (which takes one of 108
segments modulo 12) and from `tests/swiss_conformance/oracle.py`:

* D9 sign: the classical rule. The nine 3 deg 20 min parts of a sign are counted
  from the sign itself for a movable (chara) sign, from the 9th sign for a fixed
  (sthira) sign and from the 5th sign for a dual (dvisvabhava) sign. A second,
  elemental formulation (fire signs from Mesha, earth from Makara, air from
  Tula, water from Karka) is computed too, and the two must agree.
* All arithmetic is exact (fractions.Fraction). A swetest value is parsed from
  its printed decimal text, so no binary rounding enters the classification.

Isolation: this module imports only the standard library. The unit test
`test_sci_gold.IsolationTest` parses this file and fails if it imports the
engine, Swiss Ephemeris, zoneinfo or any other test oracle.
"""
from __future__ import annotations

from fractions import Fraction

RASHIS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
          "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena")
NAKSHATRAS = (
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati")

FULL = Fraction(360)
SIGN = Fraction(30)
NAKSHATRA_SPAN = Fraction(40, 3)   # 13 deg 20 min
PADA_SPAN = Fraction(10, 3)        # 3 deg 20 min = one Navamsa
MOVABLE, FIXED, DUAL = "movable", "fixed", "dual"


def exact(value) -> Fraction:
    """Exact rational from a decimal string, an int, a Fraction or a binary float."""
    if isinstance(value, bool):
        raise TypeError("boolean is not a longitude")
    if isinstance(value, (int, Fraction)):
        return Fraction(value)
    if isinstance(value, float):
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError("non-finite longitude")
        return Fraction(value)            # the exact binary value
    if isinstance(value, str):
        return Fraction(value.strip())    # the exact printed decimal
    raise TypeError("unsupported longitude type")


def norm(value) -> Fraction:
    """Exact longitude in [0, 360)."""
    return exact(value) % FULL


def rashi_index(value) -> int:
    return int(norm(value) // SIGN)


def rashi(value) -> str:
    return RASHIS[rashi_index(value)]


def modality(sign_index: int) -> str:
    return (MOVABLE, FIXED, DUAL)[sign_index % 3]


def nakshatra(value) -> tuple[str, int]:
    lon = norm(value)
    n = int(lon // NAKSHATRA_SPAN)
    pada = int((lon - n * NAKSHATRA_SPAN) // PADA_SPAN) + 1
    return NAKSHATRAS[n], pada


def navamsa_part(value) -> int:
    """0..8: which ninth of its sign the longitude falls in."""
    return int((norm(value) % SIGN) // PADA_SPAN)


def navamsa_index_parashari(value) -> int:
    """D9 sign by the movable / fixed / dual starting-sign rule."""
    s = rashi_index(value)
    start = {MOVABLE: s, FIXED: (s + 8) % 12, DUAL: (s + 4) % 12}[modality(s)]
    return (start + navamsa_part(value)) % 12


def navamsa_index_elemental(value) -> int:
    """D9 sign by the element rule: fire from Mesha, earth from Makara, air from Tula, water from Karka."""
    s = rashi_index(value)
    start = (0, 9, 6, 3)[s % 4]
    return (start + navamsa_part(value)) % 12


def navamsa_index(value) -> int:
    a, b = navamsa_index_parashari(value), navamsa_index_elemental(value)
    if a != b:  # pragma: no cover - would be a defect in this reference itself
        raise AssertionError("reference D9 formulations disagree")
    return a


def navamsa(value) -> str:
    return RASHIS[navamsa_index(value)]


def house(sign_of_body: int, sign_of_lagna: int) -> int:
    """Whole-sign house: house 1 is the Lagna sign."""
    return (sign_of_body - sign_of_lagna) % 12 + 1


def d1_house(value, lagna) -> int:
    return house(rashi_index(value), rashi_index(lagna))


def d9_house(value, lagna) -> int:
    return house(navamsa_index(value), navamsa_index(lagna))


def ketu(rahu) -> Fraction:
    """SCI-01c: Ketu exactly opposite the unrounded mean Rahu."""
    return norm(exact(rahu) + 180)


def edge_distance(value) -> Fraction:
    """Exact distance (degrees) to the nearest Pada edge; every Rashi, Nakshatra and D9 edge is a Pada edge."""
    r = norm(value) % PADA_SPAN
    return min(r, PADA_SPAN - r)


def circular_diff(a, b) -> Fraction:
    """Signed a - b in [-180, 180), exact."""
    return (exact(a) - exact(b) + 180) % FULL - 180


# --- North Indian chart: fixed house cells, signs rotate -------------------

def north_indian_sign_numbers(lagna_sign_index: int) -> dict[int, int]:
    """House h (1..12, fixed cell) shows sign number (Mesha = 1) lagna + h - 1."""
    return {h: (lagna_sign_index + h - 1) % 12 + 1 for h in range(1, 13)}


def north_indian_house_at(u: float, v: float) -> int | None:
    """House cell of a point in the unit chart square (u right, v DOWN from the top edge).

    Conventional North Indian layout: house 1 is the top central diamond and
    the houses run anticlockwise (2 top-left upper triangle, 3 left upper, 4
    left diamond, 5 left lower, 6 bottom-left, 7 bottom diamond, 8
    bottom-right, 9 right lower, 10 right diamond, 11 right upper, 12
    top-right). Returns None for a point outside the square or on a line.
    """
    if not (0 < u < 1 and 0 < v < 1):
        return None
    d1, d2 = v - u, v - (1 - u)          # diagonals: v = u and v = 1 - u
    diamond = abs(u - 0.5) + abs(v - 0.5) - 0.5
    if d1 == 0 or d2 == 0 or diamond == 0:
        return None
    if diamond < 0:                       # inside the central diamond: four kendra cells
        if d1 < 0 and d2 < 0:
            return 1
        if d1 > 0 and d2 < 0:
            return 4
        if d1 > 0 and d2 > 0:
            return 7
        return 10
    if u + v < 0.5:                       # top-left corner triangle, split by v = u
        return 2 if v < u else 3
    if u + (1 - v) < 0.5:                 # bottom-left, split by v = 1 - u
        return 5 if u < 1 - v else 6
    if (1 - u) + (1 - v) < 0.5:           # bottom-right, split by v = u
        return 8 if v > u else 9
    return 11 if (1 - u) < v else 12      # top-right, split by v = 1 - u
