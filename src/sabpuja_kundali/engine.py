"""Deterministic foundation adapter for locally installed Swiss Ephemeris.

No network use, telemetry, persistence, HTTP listener or generated birthplace
lookup. This adapter is NOT independently reference-chart validated.
"""
from __future__ import annotations

from datetime import datetime, timezone
from fractions import Fraction
from threading import RLock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import math
import os

from .ephemeris import verify_ephemeris_dir
from .rules import nakshatra, normalize, sign, navamsa_sign, whole_sign_house

_SWISS_LOCK = RLock()


class ChartComputationError(RuntimeError):
    """Swiss Ephemeris could not compute part of the chart for valid input.

    Distinct from invalid input (ValueError). Messages never contain birth data.
    """

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code


def _coordinate(value: object, name: str, limit: float, inclusive: bool) -> float:
    # bool is an int subclass; exact type check keeps rejecting it.
    if type(value) not in (int, float):
        raise ValueError(f"{name} must be a number")
    try:
        number = float(value)
    except OverflowError:
        raise ValueError(f"{name} must be a finite number") from None
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    if not (-limit <= number <= limit if inclusive else -limit < number < limit):
        bounds = "inclusive" if inclusive else "exclusive"
        raise ValueError(f"{name} must be between -{limit:g} and {limit:g} ({bounds})")
    return number


def _display_deg(longitude: float) -> float:
    """8-decimal display value in [0, 360). Never used for classification.

    Rounding can land on a boundary the raw value has not reached (29.999999996
    shows as 30.0 while staying Mesha); 360.0 is shown as its equal, 0.0.
    """
    shown = round(normalize(longitude), 8)
    return 0.0 if shown == 360.0 else shown


def _placement(longitude: float | Fraction) -> dict[str, object]:
    return {"rashi": sign(longitude), "navamsa_rashi": navamsa_sign(longitude)}


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
    # Accepted range is unchanged pending the owner's high-latitude decision (SCI-01).
    lat = _coordinate(request["latitude"], "latitude", 89.0, inclusive=False)
    lon = _coordinate(request["longitude"], "longitude", 180.0, inclusive=True)
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
        # Categories (Rashi, D9, house, Nakshatra) are always derived from these
        # unrounded Swiss values; the 8-decimal output is display only.
        raw = {}
        for name, body in bodies.items():
            pos, flags = swe.calc_ut(julian_day, body, requested_flags)
            if not (flags & swe.FLG_SWIEPH):
                raise RuntimeError("Swiss ephemeris files unavailable: refused Moshier fallback")
            raw[name] = float(pos[0])
        # Geographic ascendant in explicit Lahiri sidereal mode.
        # Placidus is undefined beyond the polar circles; Swiss then raises
        # swisseph.Error. Refuse the chart rather than substitute another method.
        try:
            cusps, ascmc = swe.houses_ex(julian_day, lat, lon, b"P", swe.FLG_SIDEREAL)
        except swe.Error:
            raise ChartComputationError(
                "ASCENDANT_UNCOMPUTABLE",
                "Swiss Ephemeris could not compute the ascendant for this location and time "
                "with the current method (expected beyond the polar circles); no chart produced"
            ) from None
        lagna = float(ascmc[0])
        # Ketu is exactly opposite unrounded Rahu. Classify the exact sum: a float
        # rahu + 180.0 can round onto the next segment boundary.
        ketu_exact = Fraction(raw["rahu_mean"]) + 180
        planets = {
            name: {"longitude_deg": _display_deg(deg), **_placement(deg)}
            for name, deg in raw.items()
        }
        planets["ketu_mean"] = {
            "longitude_deg": _display_deg(raw["rahu_mean"] + 180.0),
            **_placement(ketu_exact),
        }
        sources = {**raw, "ketu_mean": ketu_exact}
        for name, val in planets.items():
            val["whole_sign_house"] = whole_sign_house(sources[name], lagna)
        moon_nakshatra = nakshatra(raw["moon"])
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
            "lagna": {"longitude_deg": _display_deg(lagna), **_placement(lagna)},
            "moon_nakshatra": moon_nakshatra,
            "planets": planets,
        }
