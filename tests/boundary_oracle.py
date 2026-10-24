"""Independent exact reference for sector classification (tests only).

Written separately from sabpuja_kundali.rules: uses fractions.Fraction and
math.floor on the exact binary value, never the production helper.
"""
import math
from fractions import Fraction

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


def exact_angle(value):
    """Exact angle in [0, 360) of a float (its binary value) or Fraction."""
    return Fraction(value) % 360


def exact_index(value, count):
    return math.floor(exact_angle(value) * count / 360)


def expected(value):
    """Expected categories for an exact longitude."""
    sign = exact_index(value, 12)
    nak = exact_index(value, 27)
    pada_segment = exact_index(value, 108)
    return {
        "sign_index": sign,
        "rashi": SIGNS[sign],
        "nakshatra": {"index": nak, "name": NAKSHATRAS[nak], "pada": pada_segment - 4 * nak + 1},
        "navamsa_rashi": SIGNS[pada_segment % 12],
    }


def expected_house(value, ascendant):
    return (exact_index(value, 12) - exact_index(ascendant, 12)) % 12 + 1


def first_float_at_or_above(boundary):
    """Smallest float whose exact value is >= the rational boundary."""
    f = float(boundary)
    if Fraction(f) < boundary:
        f = math.nextafter(f, math.inf)
    return f
