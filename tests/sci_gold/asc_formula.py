"""KUN-SCI-GOLD-001 independent ascendant formula (test-only, isolated).

The ecliptic longitude of the eastern horizon from the sidereal time (ARMC),
the true obliquity and the geographic latitude, by the standard spherical-
astronomy relation (Meeus, Astronomical Algorithms, 2nd ed., ch. 14, the
ecliptic point on the horizon), written in the quadrant-safe two-argument form
that selects the EASTERN intersection:

    Asc = atan2(cos(ARMC), -(sin(ARMC) * cos(eps) + tan(phi) * sin(eps)))

(The bare quotient tan(Asc) = -cos(ARMC) / (...) is ambiguous by 180 deg; the
other root is the descendant.) The
sidereal Lagna is then the tropical ascendant minus the ayanamsha.

The inputs (ARMC, true obliquity, true ayanamsha) are Swiss Ephemeris values
printed by swetest, so this checks the *transformation* from those inputs to
the Lagna (formula, quadrant and ayanamsha subtraction), not the sidereal time,
nutation or precession models themselves.
"""
from __future__ import annotations

import math


def tropical_ascendant(armc_deg: float, eps_deg: float, lat_deg: float) -> float:
    ra, eps, phi = (math.radians(x) for x in (armc_deg, eps_deg, lat_deg))
    y = math.cos(ra)
    x = -(math.sin(ra) * math.cos(eps) + math.tan(phi) * math.sin(eps))
    return math.degrees(math.atan2(y, x)) % 360.0


def sidereal_ascendant(armc_deg: float, eps_deg: float, lat_deg: float, ayanamsa_deg: float) -> float:
    return (tropical_ascendant(armc_deg, eps_deg, lat_deg) - ayanamsa_deg) % 360.0
