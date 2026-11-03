"""Independent D9 (Navamsa) sign and whole-sign house reference (Gate 3E, tests only).

Written separately from sabpuja_kundali.rules and from tests/boundary_oracle.py.
It never calls the production helpers. Instead of the continuous 108-segment
formula it uses the classical Parashari element rule, with exact integer and
Fraction arithmetic on the exact binary value of a float:

- Rashi r = floor(L / 30); position in the Rashi p = L - 30 r;
- pada k = floor(p / (10/3)), in 0..8 (nine half-open 3 deg 20 min parts);
- the first Navamsa of a movable Rashi (Mesha, Karka, Tula, Makara) is the
  Rashi itself, of a fixed Rashi (Vrishabha, Simha, Vrischika, Kumbha) the 9th
  from it, and of a dual Rashi (Mithuna, Kanya, Dhanu, Meena) the 5th from it;
- D9 sign = (first Navamsa + k) mod 12.

D9 houses (SCI-01f, whole sign from the D9 Lagna) are found by counting
signs forward from the D9 Lagna sign one at a time, not by a modular formula.
No tolerance, rounding or display value is used anywhere.
"""
from fractions import Fraction

SIGNS = ("Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
         "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena")
NAVAMSA_ARC = Fraction(10, 3)  # 3 deg 20 min
# Offset of the first Navamsa from its own Rashi: movable 0, fixed +8 (9th), dual +4 (5th).
_FIRST_NAVAMSA_OFFSET = {0: 0, 1: 8, 2: 4}


def exact(value):
    """Exact angle in [0, 360) of a float (its binary value), int or Fraction."""
    angle = Fraction(value)
    while angle < 0:
        angle += 360
    while angle >= 360:
        angle -= 360
    return angle


def rashi_index(value):
    angle = exact(value)
    r = 0
    while angle >= 30 * (r + 1):
        r += 1
    return r


def navamsa_pada_in_rashi(value):
    """0..8: which 3 deg 20 min part of its Rashi the value lies in (half-open)."""
    position = exact(value) - 30 * rashi_index(value)
    k = 0
    while position >= NAVAMSA_ARC * (k + 1):
        k += 1
    assert 0 <= k <= 8
    return k


def d9_sign_index(value):
    r = rashi_index(value)
    first = (r + _FIRST_NAVAMSA_OFFSET[r % 3]) % 12
    return (first + navamsa_pada_in_rashi(value)) % 12


def d9_sign(value):
    return SIGNS[d9_sign_index(value)]


def d9_house(value, lagna):
    """Count from the D9 Lagna sign (house 1) forward until the body's D9 sign."""
    target, current, house = d9_sign_index(value), d9_sign_index(lagna), 1
    while current != target:
        current = 0 if current == 11 else current + 1
        house += 1
    assert 1 <= house <= 12
    return house


def d9_house_rashis(lagna):
    """The twelve D9 house signs in house order 1..12 (North Indian house order)."""
    out, current = [], d9_sign_index(lagna)
    for _ in range(12):
        out.append(SIGNS[current])
        current = 0 if current == 11 else current + 1
    return out
