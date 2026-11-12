"""Sunrise, sunset and Vara for Panchanga M2 (KUN-PAN-M2-SUN-001).

Status: ENGINEERING_TESTED_AND_INDEPENDENTLY_REVIEWED (KUN-PAN-VARA-G2-001). Engineering
tests and independent QA (PR #82 at c759c41), and an independent scientific review of
sunrise, sunset and Vara (KUN-PAN-VARA-RELEASE-001: an independent ERFA solar model and
published USNO and IMD times). Calculated under stated model assumptions, not observed;
no physical sunrise accuracy is certified. Not wired into `sabpuja-panchanga/1` or the
chart; the only report use is through `vara.py`, with `SUN-D-IMD-47`.

The owner adopted PAN-D03 (`SUN-D-IMD-47` at the birthplace), PAN-D05, PAN-D11-B and
PAN-D17 on 2026-11-12 for customer release of the 14-page English Janam Kundali
Essentials edition only (PR #93 comment 6822876554). `SUN-A-USNO-50` stays a comparison
convention and is not adopted for any report.

No default convention. Every call names one of `CONVENTIONS` explicitly; a missing,
unknown or non-string value is refused (`SUNRISE_CONVENTION_REQUIRED`). The two
conventions are never combined or blended:

* `SUN-D-IMD-47`: Rashtriya Panchang (IMD Positional Astronomy Centre). Upper limb on
  the horizon with 31' horizontal refraction and 16' semidiameter, so the Sun's centre
  is geometrically 47' below the horizon.
* `SUN-A-USNO-50`: USNO astronomical sunrise. Upper limb with 34' refraction and 16'
  semidiameter: centre geometrically 50' below the horizon.

Both are fixed-depression definitions, so both are realised by the same code with a
different constant. The event is the instant at which the geometric (unrefracted)
altitude of the Sun's centre equals -depression:

* position: Swiss `calc_ut(jd_ut, SUN, FLG_SWIEPH | FLG_EQUATORIAL)`, i.e. geocentric
  apparent right ascension and declination of date (the Sun's horizontal parallax,
  8.8", is below 1 s of time and is ignored, as for the Panchanga Sun, D01-A);
* local hour angle from Swiss apparent sidereal time `sidtime(jd_ut)` plus east longitude;
* sea-level observer, level horizon, no pressure or temperature model, no dip;
* UTC treated as UT1 (SCI-01h) and Swiss automatic Delta T.

`FLG_SWIEPH` is checked on every call (no Moshier fallback). Swiss rise/set routines
(`rise_trans`, `rise_trans_true_hor`) are deliberately NOT used for the result: they do
not report the ephemeris actually used, and `rise_set_fast` runs a fixed number of
iterations without a convergence test (SCI-PAN-01 5.6.3). They are used only as a
cross-check in the tests. The root is bracketed by 5-minute samples plus the refined
daily altitude extrema, then bisected on integer microseconds, so a found event is
converged by construction; the residual altitude is still checked.

Day convention (PAN-D05, adopted 2026-11-12): the sunrise of local civil date D is the rising
that falls in [00:00 D, 00:00 D+1) of the IANA zone (DST days are 23 or 25 hours long).
The sunset of that day is the first setting after that sunrise, within 24 hours.
Vara is the weekday of the local civil date of the most recent sunrise at or before
the birth instant: [sunrise_D, sunrise_D+1) is Vara(D). The civil weekday is always
reported beside it; Vara is never filled from it.

A physically undefined event (Sun continuously above, or no crossing on that local
date) is a typed `unavailable` with reason `PANCHANGA_SUNRISE_UNDEFINED`
(PAN-D11-B, adopted 2026-11-12). Ephemeris, Swiss and numerical failures raise.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import math
import re

from .. import engine, zone_policy
from ..engine import ChartComputationError, InputRefusalError, UnsupportedInputError
from ..ephemeris import load_manifest as load_ephemeris_manifest, verify_ephemeris_dir
from ..timezones import get_zone

SCHEMA = "sabpuja-panchanga-sun/0 (validation only, not a customer contract)"
METHOD_ID = "KUN-PAN-M2-SUN-001"
VALIDATION_STATUS = "ENGINEERING_TESTED_AND_INDEPENDENTLY_REVIEWED"
# Owner decision per convention. Only SUN-D-IMD-47 is adopted, and only for the Essentials edition.
CONVENTION_STATUS = {
    "SUN-D-IMD-47": "ADOPTED by the owner as PAN-D03 at the birthplace, 2026-11-12, for customer release of "
                    "janam-kundali-essentials-en/1 only (PR #93 comment 6822876554); named explicitly by the "
                    "caller, no default",
    "SUN-A-USNO-50": "COMPARISON ONLY: not adopted for any report; named explicitly by the caller, no default",
}

CONVENTIONS = {
    "SUN-D-IMD-47": {
        "depression_arcmin": 47,
        "refraction_arcmin": 31,
        "semidiameter_arcmin": 16,
        "reference_point": "upper limb",
        "source": "IMD Positional Astronomy Centre, Rashtriya Panchang explanation page "
                  "(https://packolkata.imd.gov.in/panchang/en/explanation, read 2026-11-06)",
    },
    "SUN-A-USNO-50": {
        "depression_arcmin": 50,
        "refraction_arcmin": 34,
        "semidiameter_arcmin": 16,
        "reference_point": "upper limb",
        "source": "US Naval Observatory, rise/set definitions and RSTT API (fixture PAN-REF-SUN-2026)",
    },
}

# D13-A local rendering envelope, as M1 (contract.LOCAL_RENDERING_*).
FIRST_DATE = date(1970, 1, 1)
LAST_DATE = engine.SUPPORTED_LOCAL_DATES[1]

UNDEFINED = "PANCHANGA_SUNRISE_UNDEFINED"
OUTSIDE_ENVELOPE = "PANCHANGA_SUNRISE_OUTSIDE_ENVELOPE"
NOT_CONVERGED = "PANCHANGA_SUNRISE_NOT_CONVERGED"
AMBIGUOUS = "PANCHANGA_SUNRISE_AMBIGUOUS"

MICROS = 1_000_000
SAMPLE_STEP_US = 300 * MICROS          # 5-minute bracketing samples
MAX_BISECTIONS = 64
RESIDUAL_LIMIT_DEG = 1.0 / 3600         # 1" of altitude at the returned instant

VARA_IDS = ("ravivara", "somavara", "mangalavara", "budhavara", "guruvara", "shukravara", "shanivara")
CIVIL_IDS = ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday")

_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)


class SunComputationError(RuntimeError):
    """A sunrise computation failed for valid input (numerical or ambiguous result)."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code


EXPECTED_ERRORS = engine.EXPECTED_ERRORS + (SunComputationError,)


# ---------------------------------------------------------------- input validation

def _convention(value: object) -> dict:
    if type(value) is not str or value not in CONVENTIONS:
        raise InputRefusalError(
            "SUNRISE_CONVENTION_REQUIRED",
            "convention must be named explicitly: one of " + ", ".join(CONVENTIONS) + "; there is no default")
    return CONVENTIONS[value]


def _zone(tz_name: object):
    if type(tz_name) is not str:
        raise InputRefusalError("TIMEZONE_INVALID", "timezone must be a valid IANA timezone identifier")
    try:
        zone = get_zone(tz_name)
    except ValueError:
        raise InputRefusalError("TIMEZONE_INVALID", "timezone must be a valid IANA timezone identifier") from None
    if not zone_policy.is_location_based(tz_name):
        raise InputRefusalError("TIMEZONE_NOT_LOCATION_BASED",
                                "birthplace timezone must be a geographic IANA timezone identifier")
    return zone


def _local_date(value: object) -> date:
    match = _DATE.fullmatch(value) if type(value) is str else None
    if match is None:
        raise InputRefusalError("DATE_INVALID", "local_date must be YYYY-MM-DD")
    try:
        civil = date(*(int(g) for g in match.groups()))
    except ValueError:
        raise InputRefusalError("DATE_INVALID", "local_date does not exist in the Gregorian calendar") from None
    if not FIRST_DATE <= civil <= LAST_DATE:
        raise UnsupportedInputError(
            "DATE_OUTSIDE_SUPPORTED_RANGE",
            f"sunrise local dates must be between {FIRST_DATE} and {LAST_DATE} (inclusive, D13-A)")
    return civil


def _coordinates(latitude: object, longitude: object) -> tuple[float, float]:
    # Same codes and order as the chart: COORDINATE_INVALID for either, then the band.
    engine._finite_number(latitude, "latitude")
    lon = engine._coordinate(longitude, "longitude", 180.0, inclusive=True)
    lat = engine._latitude(latitude)
    return lat, lon


# ---------------------------------------------------------------- time helpers

def _us(moment: datetime) -> int:
    delta = moment - _EPOCH
    return (delta.days * 86400 + delta.seconds) * MICROS + delta.microseconds


def _dt(t_us: int) -> datetime:
    return _EPOCH + timedelta(microseconds=t_us)


def _local_midnight_us(civil: date, zone) -> int:
    # Midnight exists in every pinned zone used here; if a zone skips it, the first
    # valid local instant of the day is the start (fold handling as the chart).
    wall = datetime(civil.year, civil.month, civil.day)
    for fold in (0, 1):
        aware = wall.replace(tzinfo=zone, fold=fold)
        if aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == wall:
            return _us(aware.astimezone(timezone.utc))
    # Gap at midnight: scan forward minute by minute to the first existing wall time.
    for minutes in range(1, 181):
        candidate = wall + timedelta(minutes=minutes)
        aware = candidate.replace(tzinfo=zone)
        if aware.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) == candidate:
            return _us(aware.astimezone(timezone.utc))
    raise SunComputationError(NOT_CONVERGED, "local midnight could not be resolved in the zone")


def _instant(t_us: int, zone) -> dict[str, object]:
    utc = _dt(t_us)
    second = utc.replace(microsecond=0)
    if utc.microsecond >= 500_000:
        second += timedelta(seconds=1)
    local = second.astimezone(zone)
    return {
        "utc_us": t_us,
        "utc": second.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local": local.isoformat(),
        "local_date": local.date().isoformat(),
        "rounding": "UTC instant rounded half up to the second, then converted with pinned tzdata",
    }


# ---------------------------------------------------------------- Swiss session

class _SunSession:
    """Holds the chart's Swiss lock for one request; geometric altitude of the Sun's centre."""

    def __init__(self, swe, folder: str, lat: float, lon: float):
        self._swe, self._folder = swe, str(folder)
        self._sin_lat, self._cos_lat = math.sin(math.radians(lat)), math.cos(math.radians(lat))
        self._lon = lon
        self.calls = 0

    def __enter__(self) -> "_SunSession":
        engine._SWISS_LOCK.acquire()
        swe = self._swe
        try:
            swe.set_ephe_path(self._folder)
            swe.set_delta_t_userdef(swe.DELTAT_AUTOMATIC)
        except swe.Error:
            engine._SWISS_LOCK.release()
            raise ChartComputationError(
                "SWISS_STATE_INITIALIZATION_FAILED",
                "Swiss Ephemeris could not be initialized for this request; no chart produced") from None
        except BaseException:
            engine._SWISS_LOCK.release()
            raise
        return self

    def __exit__(self, *exc) -> None:
        engine._SWISS_LOCK.release()

    def altitude(self, t_us: int) -> float:
        """Geometric altitude (degrees) of the Sun's centre, geocentric apparent RA/Dec of date."""
        swe = self._swe
        utc = _dt(t_us)
        try:
            jd = swe.julday(utc.year, utc.month, utc.day,
                            utc.hour + utc.minute / 60 + (utc.second + utc.microsecond / 1_000_000) / 3600)
            pos, flags = swe.calc_ut(jd, swe.SUN, swe.FLG_SWIEPH | swe.FLG_EQUATORIAL)
            sidereal_hours = swe.sidtime(jd)
        except swe.Error:
            raise ChartComputationError(
                "SWISS_PLANET_CALCULATION_FAILED",
                "Swiss Ephemeris could not complete the planetary calculation; no chart produced") from None
        self.calls += 1
        if not (flags & swe.FLG_SWIEPH):
            raise ChartComputationError(
                "SWISS_EPHEMERIS_FALLBACK_REFUSED",
                "Swiss Ephemeris did not use the verified local files; refused Moshier fallback; "
                "no chart produced")
        ra, dec = math.radians(pos[0]), math.radians(pos[1])
        hour_angle = math.radians(sidereal_hours * 15.0 + self._lon) - ra
        value = math.degrees(math.asin(max(-1.0, min(1.0,
            self._sin_lat * math.sin(dec) + self._cos_lat * math.cos(dec) * math.cos(hour_angle)))))
        if not math.isfinite(value):
            raise SunComputationError(NOT_CONVERGED, "non-finite solar altitude")
        return value


def _refine_extremum(f, t_lo: int, t_hi: int, maximum: bool) -> int:
    """Golden-section search for the altitude extremum in [t_lo, t_hi] (smooth, unimodal there)."""
    sign = -1.0 if maximum else 1.0
    g = (math.sqrt(5) - 1) / 2
    a, b = t_lo, t_hi
    c, d = b - int((b - a) * g), a + int((b - a) * g)
    fc, fd = sign * f(c), sign * f(d)
    while b - a > MICROS:   # 1 s is ample: the extremum only has to fall between the right samples
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - int((b - a) * g)
            fc = sign * f(c)
        else:
            a, c, fc = c, d, fd
            d = a + int((b - a) * g)
            fd = sign * f(d)
    return (a + b) // 2


def _crossings(f, start: int, end: int, step: int = SAMPLE_STEP_US) -> list[tuple[int, str]]:
    """All crossings of f = 0 in [start, end): rising ('rise') or setting ('set'), bisected to 1 us."""
    times = list(range(start, end, step)) + [end]
    values = [f(t) for t in times]
    # Insert the refined daily maximum and minimum, so a crossing pair between two samples
    # (a grazing Sun near the polar limit) cannot be missed.
    extra = []
    for maximum in (True, False):
        k = max(range(len(values)), key=lambda i: values[i] if maximum else -values[i])
        lo, hi = times[max(k - 1, 0)], times[min(k + 1, len(times) - 1)]
        if hi > lo:
            extra.append(_refine_extremum(f, lo, hi, maximum))
    for t in extra:
        if start < t < end and t not in times:
            times.append(t)
    known = dict(zip(times, values))
    times = sorted(set(times))
    values = [known[t] if t in known else f(t) for t in times]
    found = []
    for i in range(len(times) - 1):
        a, b, fa, fb = times[i], times[i + 1], values[i], values[i + 1]
        if (fa < 0) == (fb < 0):
            continue
        kind = "rise" if fa < 0 else "set"
        for _ in range(MAX_BISECTIONS):
            if b - a <= 1:
                break
            m = (a + b) // 2
            fm = f(m)
            if (fm < 0) == (fa < 0):
                a, fa = m, fm
            else:
                b, fb = m, fm
        if b - a > 1:
            raise SunComputationError(NOT_CONVERGED, "sunrise or sunset bisection did not converge")
        # The event is the first instant at or after the crossing: the later bracket end.
        found.append((b, kind))
    return found


def _check_residual(f, t_us: int) -> float:
    residual = f(t_us)
    if abs(residual) > RESIDUAL_LIMIT_DEG:
        raise SunComputationError(NOT_CONVERGED, "residual altitude at the event exceeds 1 arcsecond")
    return residual


def _day_events(session: _SunSession, civil: date, zone, depression_deg: float) -> dict[str, object]:
    threshold = -depression_deg
    f = lambda t: session.altitude(t) - threshold
    day_start = _local_midnight_us(civil, zone)
    day_end = _local_midnight_us(civil + timedelta(days=1), zone)
    crossings = _crossings(f, day_start, day_end)
    rises = [t for t, k in crossings if k == "rise"]
    if len(rises) > 1:
        raise SunComputationError(AMBIGUOUS, "more than one sunrise on the local date")
    if not rises:
        if crossings:
            condition = "NO_SUNRISE_ON_LOCAL_DATE"
        elif f(day_start) >= 0:
            condition = "SUN_ABOVE_DEPRESSION_ALL_DAY"
        else:
            condition = "SUN_BELOW_DEPRESSION_ALL_DAY"
        unavailable = {"status": "unavailable", "reason": UNDEFINED, "condition": condition}
        return {"sunrise": unavailable, "sunset": dict(unavailable), "_sunrise_us": None}
    sunrise = rises[0]
    residual_rise = _check_residual(f, sunrise)
    sets = [t for t, k in _crossings(f, sunrise + 1, sunrise + 86400 * MICROS) if k == "set"]
    if not sets:
        sunset = {"status": "unavailable", "reason": UNDEFINED,
                  "condition": "NO_SUNSET_WITHIN_24_HOURS_OF_SUNRISE"}
        residual_set = None
    else:
        residual_set = _check_residual(f, sets[0])
        sunset = {"status": "available", **_instant(sets[0], zone)}
    return {
        "sunrise": {"status": "available", **_instant(sunrise, zone)},
        "sunset": sunset,
        "residual_altitude_arcsec": {
            "sunrise": round(residual_rise * 3600, 6),
            "sunset": None if residual_set is None else round(residual_set * 3600, 6),
        },
        "_sunrise_us": sunrise,
    }


def _prepare(ephe_path):
    folder = verify_ephemeris_dir(engine.ephemeris_path(ephe_path), load_ephemeris_manifest())
    return engine.swiss_runtime(), folder


def _method(name: str, conv: dict) -> dict[str, object]:
    return {
        "method_id": METHOD_ID,
        "validation_status": VALIDATION_STATUS,
        "convention": name,
        "convention_status": CONVENTION_STATUS[name],
        "depression_arcmin": conv["depression_arcmin"],
        "refraction_arcmin": conv["refraction_arcmin"],
        "semidiameter_arcmin": conv["semidiameter_arcmin"],
        "condition": f"geometric altitude of the Sun's centre = -{conv['depression_arcmin']}'",
        "position": "Swiss calc_ut SUN, FLG_SWIEPH | FLG_EQUATORIAL (geocentric apparent RA/Dec); "
                    "Swiss apparent sidereal time; UTC as UT1; automatic Delta T",
        "observer": "sea level, level horizon, no pressure/temperature model, no dip, no terrain",
        "search": "5-minute samples plus refined altitude extrema, bisection on integer microseconds; "
                  "residual altitude <= 1 arcsecond",
        "day": "sunrise of local civil date D lies in [00:00 D, 00:00 D+1) of the IANA zone; "
               "sunset is the first setting within 24 h after it",
        "source": conv["source"],
    }


# ---------------------------------------------------------------- public API

def sun_day(local_date: object, latitude: object, longitude: object, timezone_name: object, *,
            convention: object, ephe_path: str | None = None) -> dict[str, object]:
    """Sunrise and sunset of a local civil date at a place, under the named convention only."""
    conv = _convention(convention)
    civil = _local_date(local_date)
    zone = _zone(timezone_name)
    lat, lon = _coordinates(latitude, longitude)
    swe, folder = _prepare(ephe_path)
    with _SunSession(swe, folder, lat, lon) as session:
        events = _day_events(session, civil, zone, conv["depression_arcmin"] / 60.0)
        calls = session.calls
    events.pop("_sunrise_us")
    return {
        "schema": SCHEMA,
        "validation_status": VALIDATION_STATUS,
        "claim_boundary": "Calculated sunrise and sunset under the named convention and stated model assumptions, "
                          "not observations; no physical accuracy is certified. Reports use them only through "
                          "the Vara document; not part of sabpuja-panchanga/1.",
        "method": _method(convention, conv),
        "local_date": civil.isoformat(),
        "civil_weekday": CIVIL_IDS[(civil.weekday() + 1) % 7],
        **events,
        "swiss_calls": calls,
    }


def vara(request: object, *, convention: object, ephe_path: str | None = None) -> dict[str, object]:
    """Vara (sunrise weekday) and civil weekday for a chart-shaped birth request.

    `request` has exactly the chart keys {birth_datetime, timezone, latitude, longitude} and is
    validated with the chart's own refusal order. The birth instant is never logged.
    """
    conv = _convention(convention)
    if not isinstance(request, dict):
        raise InputRefusalError("REQUEST_INVALID", "JSON input must be an object")
    if set(request) != {"birth_datetime", "timezone", "latitude", "longitude"}:
        raise InputRefusalError("REQUEST_INVALID",
                                "Required keys: birth_datetime, timezone, latitude, longitude (no others)")
    if not isinstance(request["birth_datetime"], str) or not isinstance(request["timezone"], str):
        raise InputRefusalError("REQUEST_INVALID", "birth_datetime and timezone must be strings")
    utc = engine._parse_birth(request["birth_datetime"], request["timezone"])
    lat, lon = _coordinates(request["latitude"], request["longitude"])
    zone = get_zone(request["timezone"])
    birth_us = _us(utc)
    civil = utc.astimezone(zone).date()
    civil_weekday = CIVIL_IDS[(civil.weekday() + 1) % 7]
    swe, folder = _prepare(ephe_path)
    result = {
        "schema": SCHEMA,
        "validation_status": VALIDATION_STATUS,
        "method": {**_method(convention, conv),
                   "vara_rule": "weekday of the local civil date of the latest sunrise at or before the "
                                "birth instant; day = [sunrise_D, sunrise_D+1)"},
        "civil_date": civil.isoformat(),
        "civil_weekday": civil_weekday,
    }
    with _SunSession(swe, folder, lat, lon) as session:
        if not FIRST_DATE <= civil <= LAST_DATE:
            governing = None
            reason = {"status": "unavailable", "reason": OUTSIDE_ENVELOPE,
                      "condition": "BIRTH_LOCAL_DATE_OUTSIDE_D13_A"}
        else:
            today = _day_events(session, civil, zone, conv["depression_arcmin"] / 60.0)
            if today["_sunrise_us"] is None:
                governing, reason = None, today["sunrise"]
            elif birth_us >= today["_sunrise_us"]:
                governing, reason = (civil, today), None
            elif civil - timedelta(days=1) < FIRST_DATE:
                governing = None
                reason = {"status": "unavailable", "reason": OUTSIDE_ENVELOPE,
                          "condition": "GOVERNING_SUNRISE_BEFORE_1970_01_01"}
            else:
                previous = _day_events(session, civil - timedelta(days=1), zone, conv["depression_arcmin"] / 60.0)
                if previous["_sunrise_us"] is None:
                    governing, reason = None, previous["sunrise"]
                else:
                    governing, reason = (civil - timedelta(days=1), previous), None
        result["swiss_calls"] = session.calls
    if governing is None:
        result["vara"] = dict(reason)
        result["governing_sunrise"] = dict(reason)
        result["vara_differs_from_civil_weekday"] = None
        return result
    gdate, events = governing
    vid = VARA_IDS[(gdate.weekday() + 1) % 7]
    result["vara"] = {"status": "available", "vara_id": vid, "sunrise_local_date": gdate.isoformat()}
    result["governing_sunrise"] = events["sunrise"]
    result["vara_differs_from_civil_weekday"] = CIVIL_IDS.index(civil_weekday) != VARA_IDS.index(vid)
    result["seconds_after_governing_sunrise"] = (birth_us - events["_sunrise_us"]) // MICROS
    return result
