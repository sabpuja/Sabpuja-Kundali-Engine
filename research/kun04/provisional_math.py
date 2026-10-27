"""NON-CANONICAL arithmetic exploration for KUN-04.

The research module proves some rational, zero-boundary invariants only.
It does NOT compute or expose Panchanga, Vimshottari calendar dates,
sunrise, end times, Sanskrit names, interpretations or valid natal output.
It MUST NOT be imported by production or PDF generation.
Scientific choices remain pending owner approval (see PR #47).
"""
from __future__ import annotations

from fractions import Fraction
from math import isfinite

DEGREES = Fraction(360)
NAKSHATRA_WIDTH = Fraction(40, 3)    # 13 degrees 20 arcminutes
PADA_WIDTH = Fraction(10, 3)
TITHI_WIDTH = Fraction(12)
KARANA_WIDTH = Fraction(6)

VIMSHOTTARI_ORDER = (
    "ketu", "venus", "sun", "moon", "mars",
    "rahu", "jupiter", "saturn", "mercury",
)
VIMSHOTTARI_NOMINAL_YEARS = (7, 20, 6, 10, 7, 18, 16, 19, 17)
assert sum(VIMSHOTTARI_NOMINAL_YEARS) == 120


def rational(value: object) -> Fraction:
    """Parse bounded exact numeric vectors; do not coerce nonfinite floats."""
    if isinstance(value, bool):
        raise ValueError("Boolean longitude is not numeric")
    if isinstance(value, float) and not isfinite(value):
        raise ValueError("Longitude must be finite")
    token = str(value)
    if len(token) > 72:
        raise ValueError("Too many input digits")
    try:
        out = Fraction(token)
    except (ValueError, ZeroDivisionError, TypeError, OverflowError) as exc:
        raise ValueError("Invalid numeric input") from exc
    if abs(out) > 10 ** 18:
        raise ValueError("Magnitude out of research range")
    return out


def longitude(value: object) -> Fraction:
    """Half-open [0,360) normalization using exact fractions."""
    return rational(value) % DEGREES


def panchanga_segment_numbers(sun_sidereal: object, moon_sidereal: object) -> dict:
    """Provisional segment NUMBERS ONLY, not an approved Panchanga."""
    sun = longitude(sun_sidereal)
    moon = longitude(moon_sidereal)
    elongation = (moon - sun) % DEGREES
    yoga_angle = (sun + moon) % DEGREES
    tithi = int(elongation // TITHI_WIDTH) + 1
    karana_slot = int(elongation // KARANA_WIDTH) + 1
    nakshatra = int(moon // NAKSHATRA_WIDTH) + 1
    pada = int((moon % NAKSHATRA_WIDTH) // PADA_WIDTH) + 1
    yoga = int(yoga_angle // NAKSHATRA_WIDTH) + 1
    assert 1 <= tithi <= 30 and 1 <= karana_slot <= 60
    assert 1 <= nakshatra <= 27 and 1 <= yoga <= 27 and 1 <= pada <= 4
    return dict(tithi_number=tithi, karana_half_tithi_slot=karana_slot,
                nakshatra_number=nakshatra, pada=pada, yoga_number=yoga)


def natal_vimshottari_nominal_balance(moon_sidereal: object) -> dict:
    """Moon-Nakshatra lord and nominal-year fraction, with NO time arithmetic."""
    moon = longitude(moon_sidereal)
    nak_zero = int(moon // NAKSHATRA_WIDTH)
    elapsed_fraction = (moon % NAKSHATRA_WIDTH) / NAKSHATRA_WIDTH
    lord_i = nak_zero % 9
    nominal = Fraction(VIMSHOTTARI_NOMINAL_YEARS[lord_i])
    return dict(nakshatra_number=nak_zero + 1,
                lord=VIMSHOTTARI_ORDER[lord_i],
                fraction_elapsed=elapsed_fraction,
                nominal_years=nominal,
                balance_nominal_years=nominal * (1 - elapsed_fraction))


def nominal_subperiods(duration: object, first_lord: str) -> list[dict]:
    """Partition an abstract rational duration; NOT calendar periods."""
    total = rational(duration)
    if total < 0:
        raise ValueError("Duration must be nonnegative")
    if first_lord not in VIMSHOTTARI_ORDER:
        raise ValueError("Unknown starting lord")
    start_i = VIMSHOTTARI_ORDER.index(first_lord)
    cursor = Fraction(0)
    parts = []
    for offset in range(9):
        index = (start_i + offset) % 9
        segment = total * Fraction(VIMSHOTTARI_NOMINAL_YEARS[index], 120)
        parts.append({"lord": VIMSHOTTARI_ORDER[index],
                      "start": cursor, "end": cursor + segment})
        cursor += segment
    assert cursor == total
    return parts
