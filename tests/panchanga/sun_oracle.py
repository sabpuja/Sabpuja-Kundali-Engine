"""Independent sunrise oracle for KUN-PAN-M2-SUN-001: pure Python, no Swiss Ephemeris.

Different theory, different code and a different root-finding method from
`sabpuja_kundali.panchanga.sun`:

* Sun: Meeus, Astronomical Algorithms (2nd ed.), ch. 25 "low accuracy" solar
  coordinates (geometric longitude to about 0.01 deg), with the ch. 22 principal
  nutation terms and the annual aberration (-20.4898"/R) for the apparent place;
* obliquity: Meeus 22.2 (IAU 1980 mean) plus nutation in obliquity;
* sidereal time: Meeus 12.4 (GMST) plus the equation of the equinoxes;
* Delta T: Espenak and Meeus (NASA, 2006) polynomials for 1961-2150;
* root: classical hour-angle iteration, cos H0 = (sin h0 - sin phi sin d) / (cos phi cos d),
  re-evaluated at each new instant until it moves less than 1 ms.

Its own accuracy is a few seconds of time at Indian latitudes (measured in the tests
against the engine, and stated in the evidence); that is enough to separate the 47'
and 50' conventions, which differ by 12 to 17 s in India.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import math

_J2000 = 2451545.0


def julian_day_utc(moment: datetime) -> float:
    u = moment.astimezone(timezone.utc)
    return 2440587.5 + (u - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds() / 86400.0


def delta_t_seconds(year_fraction: float) -> float:
    y = year_fraction
    if 1961 <= y < 1986:
        t = y - 1975
        return 45.45 + 1.067 * t - t * t / 260 - t ** 3 / 718
    if 1986 <= y < 2005:
        t = y - 2000
        return 63.86 + 0.3345 * t - 0.060374 * t ** 2 + 0.0017275 * t ** 3 + 0.000651814 * t ** 4 \
            + 0.00002373599 * t ** 5
    if 2005 <= y < 2050:
        t = y - 2000
        return 62.92 + 0.32217 * t + 0.005589 * t * t
    if 2050 <= y <= 2150:
        return -20 + 32 * ((y - 1820) / 100) ** 2 - 0.5628 * (2150 - y)
    raise ValueError("oracle Delta T covers 1961-2150 only")


def _sun_ra_dec(jd_ut: float) -> tuple[float, float, float]:
    """Apparent geocentric RA, Dec (degrees) and the equation of the equinoxes (degrees)."""
    year = 2000 + (jd_ut - _J2000) / 365.25
    jde = jd_ut + delta_t_seconds(year) / 86400.0
    T = (jde - _J2000) / 36525.0
    L0 = 280.46646 + 36000.76983 * T + 0.0003032 * T * T
    M = math.radians(357.52911 + 35999.05029 * T - 0.0001537 * T * T)
    e = 0.016708634 - 0.000042037 * T - 0.0000001267 * T * T
    C = ((1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M)
         + (0.019993 - 0.000101 * T) * math.sin(2 * M) + 0.000289 * math.sin(3 * M))
    true_lon = L0 + C
    nu = M + math.radians(C)
    R = 1.000001018 * (1 - e * e) / (1 + e * math.cos(nu))
    # Principal nutation terms (Meeus ch. 22, accurate to about 0.5" and 0.1").
    omega = math.radians(125.04452 - 1934.136261 * T)
    Ls = math.radians(280.4665 + 36000.7698 * T)
    Lm = math.radians(218.3165 + 481267.8813 * T)
    dpsi = (-17.20 * math.sin(omega) - 1.32 * math.sin(2 * Ls) - 0.23 * math.sin(2 * Lm)
            + 0.21 * math.sin(2 * omega)) / 3600.0
    deps = (9.20 * math.cos(omega) + 0.57 * math.cos(2 * Ls) + 0.10 * math.cos(2 * Lm)
            - 0.09 * math.cos(2 * omega)) / 3600.0
    eps0 = 23.0 + 26.0 / 60 + 21.448 / 3600 - (46.8150 * T + 0.00059 * T * T - 0.001813 * T ** 3) / 3600.0
    eps = math.radians(eps0 + deps)
    lam = math.radians(true_lon + dpsi - 20.4898 / 3600.0 / R)
    ra = math.degrees(math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))) % 360.0
    dec = math.degrees(math.asin(math.sin(eps) * math.sin(lam)))
    return ra, dec, dpsi * math.cos(eps)


def _gast_deg(jd_ut: float, eq_equinox_deg: float) -> float:
    T = (jd_ut - _J2000) / 36525.0
    gmst = 280.46061837 + 360.98564736629 * (jd_ut - _J2000) + 0.000387933 * T * T - T ** 3 / 38710000.0
    return (gmst + eq_equinox_deg) % 360.0


def altitude_deg(jd_ut: float, lat: float, lon: float) -> float:
    ra, dec, eqe = _sun_ra_dec(jd_ut)
    H = math.radians(_gast_deg(jd_ut, eqe) + lon - ra)
    phi, d = math.radians(lat), math.radians(dec)
    return math.degrees(math.asin(math.sin(phi) * math.sin(d) + math.cos(phi) * math.cos(d) * math.cos(H)))


def event_utc(guess_utc: datetime, lat: float, lon: float, depression_arcmin: float, kind: str):
    """Rise or set nearest the guess by hour-angle iteration; None if the Sun does not reach h0."""
    h0 = math.radians(-depression_arcmin / 60.0)
    phi = math.radians(lat)
    jd = julian_day_utc(guess_utc)
    for _ in range(50):
        ra, dec, eqe = _sun_ra_dec(jd)
        d = math.radians(dec)
        cos_h0 = (math.sin(h0) - math.sin(phi) * math.sin(d)) / (math.cos(phi) * math.cos(d))
        if not -1.0 <= cos_h0 <= 1.0:
            return None
        H0 = math.degrees(math.acos(cos_h0))
        target_ha = -H0 if kind == "rise" else H0
        current_ha = (_gast_deg(jd, eqe) + lon - ra + 180.0) % 360.0 - 180.0
        # Hour angle advances 360.9856 deg per day of UT (mean rate is ample for the step).
        step = ((target_ha - current_ha + 180.0) % 360.0 - 180.0) / 360.98564736629
        jd += step
        if abs(step) * 86400.0 < 1e-3:
            break
    else:
        raise RuntimeError("oracle did not converge")
    return datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=(jd - 2440587.5) * 86400.0)
