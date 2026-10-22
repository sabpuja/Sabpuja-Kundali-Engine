"""Shared helpers for the KUN-02 scientific probes (test-only, never imported by the engine).

Every probe result carries one evidence class so Swiss-on-Swiss agreement is
never presented as independent accuracy:

- SWISS_CONFORMANCE: Swiss Ephemeris compared with itself (other call, flag or
  house system). Shows equivalence of two Swiss paths, nothing more.
- INDEPENDENT_MATHEMATICS: our own formula (spherical trigonometry, IAU
  expressions, exact rationals) applied to Swiss inputs or to definitions.
- TIMEKEEPING: civil-time and time-scale behaviour (IANA tzdata, IERS leap
  seconds, Delta T), checked against transcribed authoritative records.
- ENGINE_BEHAVIOUR: what the current production engine accepts or refuses.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json
import math
import os

from sabpuja_kundali.ephemeris import verify_ephemeris_dir

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
DATA_ENV = "SABPUJA_TEST_EPHE_PATH"

SWISS_CONFORMANCE = "SWISS_CONFORMANCE"
INDEPENDENT_MATHEMATICS = "INDEPENDENT_MATHEMATICS"
TIMEKEEPING = "TIMEKEEPING"
ENGINE_BEHAVIOUR = "ENGINE_BEHAVIOUR"

ARCSEC = 3600.0


def load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def ephe_dir(explicit: str | None = None) -> Path:
    """The verified pinned data directory; raises EphemerisDataError otherwise."""
    return verify_ephemeris_dir(explicit if explicit is not None else os.environ.get(DATA_ENV, ""))


def swiss(folder: Path):
    """Import swisseph and apply the engine's exact global configuration."""
    import swisseph as swe
    swe.set_ephe_path(str(folder))
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    return swe


def engine_jd(swe, utc: datetime) -> float:
    """Julian day exactly as engine.calculate builds it (UTC passed as UT)."""
    return swe.julday(
        utc.year, utc.month, utc.day,
        utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1_000_000) / 3600)


def signed_delta(a: float, b: float) -> float:
    """a - b reduced to [-180, 180) degrees."""
    return (a - b + 180.0) % 360.0 - 180.0


def houses(swe, jd: float, lat: float, lon: float, hsys: bytes, flags: int):
    """(cusps, ascmc) or None when Swiss raises (Placidus beyond the polar circle)."""
    try:
        return swe.houses_ex(jd, lat, lon, hsys, flags)
    except swe.Error:
        return None


def true_obliquity(swe, jd_ut: float) -> float:
    return swe.calc_ut(jd_ut, swe.ECL_NUT, 0)[0][0]


def finite_max(values) -> float:
    values = [abs(v) for v in values]
    return max(values) if values else 0.0


def rad(x: float) -> float:
    return math.radians(x)
