"""Deterministic foundation adapter for locally installed Swiss Ephemeris.

No network use, telemetry, persistence, HTTP listener or generated birthplace
lookup. This adapter is NOT independently reference-chart validated.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from fractions import Fraction
from threading import RLock
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import math
import os
import re

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


class InputRefusalError(ValueError):
    """Input refused before any calculation, with a stable code (KUN-03 P5).

    Every input refusal raises this or its subclass; codes and their fixed order
    are listed in docs/api-contract.md. Messages never contain birth data.
    """

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code


class UnsupportedInputError(InputRefusalError):
    """Valid input outside the supported product envelope (SCI-01g, SCI-03)."""


# SCI-01g: fixed band, the same for every date. The ascendant vehicle (b"W",
# SCI-01e) computes at any latitude, so this band alone decides which locations
# are accepted; it also stays inside the Placidus limit of 90 deg - true
# obliquity (66.5467 to 66.5752 deg over 1900-2100).
SUPPORTED_LATITUDE_DEG = 66.0

# SCI-03 initial window, by local civil birth date (inclusive). Extend only
# after historical-time QA and an owner decision.
SUPPORTED_LOCAL_DATES = (date(1900, 1, 1), date(2100, 12, 31))

# Reserved, not raised yet: TIMEZONE_NOT_LOCATION_BASED (P5-D3, a separate
# pre-release package).
RESERVED_CODES = ("TIMEZONE_NOT_LOCATION_BASED",)

# SCI-03 RG-HIST Option B (owner pre-merge record, PR #20 comment 6336254894;
# P8 choices G1-G5, comment 6350086727): no historical clock is verified, so
# every recognised zone is refused for local civil dates before 1970-01-01.
# Rows are (zone or "*", first refused local date, last refused local date).
# Change only with an owner decision; docs/api-contract.md mirrors this table.
HISTORICAL_CLOCK_POLICY = "SCI-03 RG-HIST Option B, version 1"
HISTORICAL_CLOCK_GATE = (("*", date.min, date(1969, 12, 31)),)
# DATA-01 verified exceptions, same row shape. Empty: each one needs its own
# evidence, QA and owner approval.
HISTORICAL_CLOCK_EXCEPTIONS = ()

# P5-D2 strict profile: YYYY-MM-DDTHH:MM[:SS[.f{1,6}]] then Z or +-HH:MM[:SS].
# ASCII digits only; upper-case T and Z only. The offset is optional here so a
# missing one can be reported as TIME_OFFSET_REQUIRED rather than a format error.
_BIRTH_PATTERN = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2})(?::([0-9]{2})(?:\.([0-9]{1,6}))?)?"
    r"(?:(Z)|([+-])([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?)?")
_FORMAT_DETAIL = "birth_datetime must be YYYY-MM-DDTHH:MM[:SS[.ffffff]] followed by Z or +HH:MM[:SS]/-HH:MM[:SS]"


def _finite_number(value: object, name: str) -> float:
    # bool is an int subclass; exact type check keeps rejecting it.
    if type(value) not in (int, float):
        raise InputRefusalError("COORDINATE_INVALID", f"{name} must be a number")
    try:
        number = float(value)
    except OverflowError:
        raise InputRefusalError("COORDINATE_INVALID", f"{name} must be a finite number") from None
    if not math.isfinite(number):
        raise InputRefusalError("COORDINATE_INVALID", f"{name} must be a finite number")
    return number


def _latitude(value: object) -> float:
    number = _finite_number(value, "latitude")
    if not -SUPPORTED_LATITUDE_DEG <= number <= SUPPORTED_LATITUDE_DEG:
        raise UnsupportedInputError(
            "LATITUDE_OUTSIDE_SUPPORTED_BAND",
            f"latitude must be between -{SUPPORTED_LATITUDE_DEG:g} and {SUPPORTED_LATITUDE_DEG:g} (inclusive)")
    return number


def _coordinate(value: object, name: str, limit: float, inclusive: bool) -> float:
    number = _finite_number(value, name)
    if not (-limit <= number <= limit if inclusive else -limit < number < limit):
        bounds = "inclusive" if inclusive else "exclusive"
        raise InputRefusalError("COORDINATE_INVALID", f"{name} must be between -{limit:g} and {limit:g} ({bounds})")
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


def _historical_clock_unverified(civil: date, tz_name: str) -> bool:
    def covers(rows, wildcard):
        return any((zone == tz_name or (wildcard and zone == "*")) and first <= civil <= last
                   for zone, first, last in rows)
    return covers(HISTORICAL_CLOCK_GATE, True) and not covers(HISTORICAL_CLOCK_EXCEPTIONS, False)


def _parse_birth(birth_datetime: str, tz_name: str) -> datetime:
    """Validate the birth time in the fixed P5 order and return it in UTC.

    TIME_FORMAT_INVALID -> TIME_OFFSET_REQUIRED -> TIME_LEAP_SECOND_UNSUPPORTED
    -> DATE_INVALID -> TIMEZONE_INVALID -> DATE_OUTSIDE_SUPPORTED_RANGE
    -> TIME_NONEXISTENT_LOCAL -> TIME_OFFSET_MISMATCH -> HISTORICAL_CLOCK_UNVERIFIED.
    Nothing is coerced.
    """
    match = _BIRTH_PATTERN.fullmatch(birth_datetime) if isinstance(birth_datetime, str) else None
    if match is None:
        raise InputRefusalError("TIME_FORMAT_INVALID", _FORMAT_DETAIL)
    year, month, day, hour, minute = (int(match.group(i)) for i in range(1, 6))
    second = int(match.group(6) or 0)
    fraction = match.group(7) or ""
    is_utc, sign, off_h, off_m, off_s = match.group(8, 9, 10, 11, 12)
    if hour > 23 or minute > 59 or second > 60 or (sign and (int(off_h) > 23 or int(off_m) > 59 or int(off_s or 0) > 59)):
        raise InputRefusalError("TIME_FORMAT_INVALID", _FORMAT_DETAIL)
    if not is_utc and not sign:
        raise InputRefusalError("TIME_OFFSET_REQUIRED", "Birth datetime requires explicit UTC offset; do not guess")
    if second == 60:
        raise UnsupportedInputError("TIME_LEAP_SECOND_UNSUPPORTED", "a seconds value of 60 (leap second) is not supported")
    try:
        civil = date(year, month, day)
    except ValueError:
        raise InputRefusalError("DATE_INVALID", "birth date does not exist in the Gregorian calendar") from None
    offset = timedelta(0)
    if sign:
        offset = timedelta(hours=int(off_h), minutes=int(off_m), seconds=int(off_s or 0))
        offset = -offset if sign == "-" else offset
    try:
        zone = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, TypeError, ValueError):
        raise InputRefusalError("TIMEZONE_INVALID", "timezone must be a valid IANA timezone identifier") from None
    # SCI-03: the window applies to the local civil date as written, before
    # conversion, so it never depends on the offset (UTC may be 1899 or 2101).
    if not SUPPORTED_LOCAL_DATES[0] <= civil <= SUPPORTED_LOCAL_DATES[1]:
        raise UnsupportedInputError(
            "DATE_OUTSIDE_SUPPORTED_RANGE",
            "local birth date must be between 1900-01-01 and 2100-12-31 (inclusive)")
    wall = datetime(year, month, day, hour, minute, second, int(fraction.ljust(6, "0") or 0))
    # IANA offsets for this wall time: one normally, two in a fold, none in a gap.
    valid = set()
    for fold in (0, 1):
        aware = wall.replace(tzinfo=zone, fold=fold)
        if aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == wall:
            valid.add(aware.utcoffset())
    if not valid:
        raise InputRefusalError("TIME_NONEXISTENT_LOCAL", "birth time does not exist in the IANA timezone (DST or historical gap)")
    if offset not in valid:
        raise InputRefusalError("TIME_OFFSET_MISMATCH", "Birth time/offset does not match IANA timezone (DST or historical rule)")
    # P8: after every other time check and before the coordinates, by the local
    # civil date as written (never the UTC date).
    if _historical_clock_unverified(civil, tz_name):
        raise UnsupportedInputError(
            "HISTORICAL_CLOCK_UNVERIFIED",
            "birth dates before 1970-01-01 need a verified historical clock record")
    return wall.replace(tzinfo=timezone(offset)).astimezone(timezone.utc)


def calculate(request: dict[str, object], ephe_path: str | None = None) -> dict[str, object]:
    """Calculate local sidereal planetary results; fail closed on missing Swiss files.

    Schema is described in docs/api-contract.md. Never write the request to logs.
    """
    if not isinstance(request, dict):
        raise InputRefusalError("REQUEST_INVALID", "JSON input must be an object")
    allowed = {"birth_datetime", "timezone", "latitude", "longitude"}
    if set(request) != allowed:
        raise InputRefusalError("REQUEST_INVALID", "Required keys: birth_datetime, timezone, latitude, longitude (no others)")
    if not isinstance(request["birth_datetime"], str) or not isinstance(request["timezone"], str):
        raise InputRefusalError("REQUEST_INVALID", "birth_datetime and timezone must be strings")
    # P5-D1: every birth-time refusal comes before any coordinate refusal.
    utc = _parse_birth(request["birth_datetime"], request["timezone"])
    # COORDINATE_INVALID for either coordinate before the latitude band.
    _finite_number(request["latitude"], "latitude")
    lon = _coordinate(request["longitude"], "longitude", 180.0, inclusive=True)
    lat = _latitude(request["latitude"])
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
        # Geographic ascendant in explicit Lahiri sidereal mode (SCI-01e): ascmc[0]
        # of the whole-sign call; bit-identical to Placidus at every sampled point
        # where Placidus is defined (KUN-02 E-A1). Swiss is not expected to fail
        # here (E-A2); the refusal is defensive and no other method is substituted.
        try:
            cusps, ascmc = swe.houses_ex(julian_day, lat, lon, b"W", swe.FLG_SIDEREAL)
        except swe.Error:
            raise ChartComputationError(
                "ASCENDANT_UNCOMPUTABLE",
                "Swiss Ephemeris could not compute the ascendant for this location and time; "
                "no chart produced"
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
