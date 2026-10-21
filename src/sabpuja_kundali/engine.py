"""Deterministic foundation adapter for locally installed Swiss Ephemeris.

No network use, telemetry, persistence, HTTP listener or generated birthplace
lookup. This adapter is NOT independently reference-chart validated.
"""
from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import math
import os

from .ephemeris import verify_ephemeris_dir
from .rules import nakshatra, normalize, sign, navamsa_sign, whole_sign_house

_SWISS_LOCK = RLock()


def _parse_birth(birth_datetime: str, tz_name: str) -> datetime:
    try:
        local = datetime.fromisoformat(birth_datetime)
    except (ValueError, TypeError) as exc:
        raise ValueError("birth_datetime must be ISO 8601 with an explicit UTC offset") from exc
    if local.tzinfo is None or local.utcoffset() is None:
        raise ValueError("Birth datetime requires explicit UTC offset; do not guess")
    try:
        zone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, TypeError, ValueError) as exc:
        raise ValueError("timezone must be a valid IANA timezone identifier") from exc
    actual = local.astimezone(zone)
    if actual.replace(tzinfo=None) != local.replace(tzinfo=None) or actual.utcoffset() != local.utcoffset():
        raise ValueError("Birth time/offset does not match IANA timezone (DST or historical rule)")
    utc = local.astimezone(timezone.utc)
    # Initial supported accuracy envelope. Extend only after historical time QA.
    if not 1900 <= utc.year <= 2100:
        raise ValueError("Initial build supports births from 1900 through 2100 only")
    return utc


def calculate(request: dict[str, object], ephe_path: str | None = None) -> dict[str, object]:
    """Calculate local sidereal planetary results; fail closed on missing Swiss files.

    Schema is described in docs/api-contract.md. Never write the request to logs.
    """
    if not isinstance(request, dict):
        raise ValueError("JSON input must be an object")
    allowed = {"birth_datetime", "timezone", "latitude", "longitude"}
    if set(request) != allowed:
        raise ValueError("Required keys: birth_datetime, timezone, latitude, longitude (no others)")
    if not isinstance(request["birth_datetime"], str) or not isinstance(request["timezone"], str):
        raise ValueError("birth_datetime and timezone must be strings")
    if type(request["latitude"]) not in (int, float) or type(request["longitude"]) not in (int, float):
        raise ValueError("latitude and longitude must be numbers")
    lat = float(request["latitude"])
    lon = float(request["longitude"])
    if not math.isfinite(lat) or not math.isfinite(lon) or not (-89.0 < lat < 89.0) or not (-180 <= lon <= 180):
        raise ValueError("Invalid or unsupported latitude/longitude")
    utc = _parse_birth(request["birth_datetime"], request["timezone"])
    # Every required manifest file must match its pinned SHA-256 before Swiss runs.
    folder = verify_ephemeris_dir(ephe_path or os.environ.get("SABPUJA_EPHE_PATH", ""))
    try:
        import swisseph as swe
    except ImportError as exc:
        raise RuntimeError("Install pinned local pyswisseph package") from exc
    julian_day = swe.julday(
        utc.year, utc.month, utc.day,
        utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1_000_000) / 3600
    )
    bodies = {
        "sun": swe.SUN, "moon": swe.MOON, "mars": swe.MARS,
        "mercury": swe.MERCURY, "jupiter": swe.JUPITER, "venus": swe.VENUS,
        "saturn": swe.SATURN, "rahu_mean": swe.MEAN_NODE,
    }
    with _SWISS_LOCK:
        swe.set_ephe_path(str(folder))
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        requested_flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
        planets = {}
        for name, body in bodies.items():
            pos, flags = swe.calc_ut(julian_day, body, requested_flags)
            if not (flags & swe.FLG_SWIEPH):
                raise RuntimeError("Swiss ephemeris files unavailable: refused Moshier fallback")
            deg = normalize(float(pos[0]))
            planets[name] = {
                "longitude_deg": round(deg, 8),
                "rashi": sign(deg),
                "navamsa_rashi": navamsa_sign(deg),
            }
        # Geographic ascendant in explicit Lahiri sidereal mode.
        cusps, ascmc = swe.houses_ex(julian_day, lat, lon, b"P", swe.FLG_SIDEREAL)
        lagna = normalize(float(ascmc[0]))
        rahu = float(planets["rahu_mean"]["longitude_deg"])
        ketu = normalize(rahu + 180.0)
        planets["ketu_mean"] = {
            "longitude_deg": round(ketu, 8),
            "rashi": sign(ketu),
            "navamsa_rashi": navamsa_sign(ketu),
        }
        for val in planets.values():
            val["whole_sign_house"] = whole_sign_house(float(val["longitude_deg"]), lagna)
        moon_nakshatra = nakshatra(float(planets["moon"]["longitude_deg"]))
        return {
            "schema_version": "0.1.0",
            "validation_status": "UNVERIFIED_GOLDEN_CHARTS",
            "method": {
                "ayanamsa": "Lahiri", "nodes": "mean", "houses": "whole_sign",
                "ephemeris": "Swiss Ephemeris, local .se1", "binding_version": swe.version
            },
            "birth": {
                "utc": utc.isoformat().replace("+00:00", "Z"),
                "timezone": request["timezone"],
                "latitude": lat, "longitude": lon
            },
            "lagna": {
                "longitude_deg": round(lagna, 8),
                "rashi": sign(lagna), "navamsa_rashi": navamsa_sign(lagna)
            },
            "moon_nakshatra": moon_nakshatra,
            "planets": planets,
        }
