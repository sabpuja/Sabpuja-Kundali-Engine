"""Calculation metadata for successful charts (KUN-03 P7).

Describes the conventions and pinned data that produced a chart. It is built
only from the engine's own constants, the ephemeris manifest the request was
verified against and the pinned timezone loader, so it cannot name a dataset
other than the one used. Deterministic: no clock, host path, random value or
request text. Recorded research values (the 2050 sidereal-time step, the
leap-second list expiry) are labelled with their source; nothing here is an
independent accuracy claim.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from functools import lru_cache
from importlib import metadata
import hashlib
import json

SCHEMA_VERSION = "0.2.0"
LEGACY_SCHEMA_VERSION = "0.1.0"
METADATA_SCHEMA = "sabpuja-calculation-metadata/2"
METADATA_KEY = "calculation_metadata"

# The engine's Swiss calls, by name. Tests check the recorded calls against these.
PLANET_FLAG_NAMES = ("FLG_SWIEPH", "FLG_SIDEREAL")
ASCENDANT_FLAG_NAMES = ("FLG_SIDEREAL",)
ASCENDANT_HOUSE_SYSTEM = "W"
PLANET_BODIES = ("SUN", "MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN", "MEAN_NODE")
HIGH_LATITUDE_DISCLOSURE_DEG = 60.0  # SCI-01g: disclosure above 60 deg, no refusal

# SCI-01h time-scale eras, by the converted UTC instant (half-open, start inclusive).
UTC_START = datetime(1961, 1, 1, tzinfo=timezone.utc)
LEAP_SECOND_UTC_START = datetime(1972, 1, 1, tzinfo=timezone.utc)
# IERS leap-seconds.list via tz 2026e (SHA-256 db5a895f...3433): "File expires on 28 June 2027".
# Pinned research value; it does not follow later IERS publications.
LEAP_SECOND_LIST_EXPIRY = datetime(2027, 6, 28, tzinfo=timezone.utc)
# Swiss 2.10.03 switches its default sidereal-time model here (KUN-02 E-SIDT, recorded step).
SIDEREAL_MODEL_SWITCH = datetime(2050, 1, 1, tzinfo=timezone.utc)
SIDEREAL_MODEL_STEP_ARCSEC = -1.908

ERAS = (
    ("CIVIL_TIME_BEFORE_UTC", None, UTC_START,
     "Before 1961 no UTC existed: a civil clock reading converted with the IANA offset, treated as UT1. "
     "UT1 is a reconstruction. Reachable only through the test-only historical clock override."),
    ("UTC_BEFORE_LEAP_SECONDS", UTC_START, LEAP_SECOND_UTC_START,
     "1961-1971 UTC with frequency offsets and steps, before leap-second UTC began (for accepted charts, "
     "1969-12-31 to 1971-12-31 UTC). The converted UTC is treated as UT1; UT1-UTC for this era is not "
     "sourced, so the time scale is an approximation, not a verified UT1 measurement."),
    ("LEAP_SECOND_UTC", LEAP_SECOND_UTC_START, LEAP_SECOND_LIST_EXPIRY,
     "Leap-second UTC, up to the pinned IERS leap-second list expiry (2027-06-28). The converted UTC is "
     "treated as UT1. The IERS rule keeps |UT1-UTC| below 0.9 s; that bound is implied under the Swiss "
     "Delta T model, not a measured UT1-UTC for this calculation."),
    ("AFTER_LEAP_SECOND_LIST_EXPIRY", LEAP_SECOND_LIST_EXPIRY, None,
     "After the pinned IERS leap-second list expiry: future leap seconds and UT1-UTC are not known. The "
     "converted UTC is treated as UT1 by projection; no |UT1-UTC| bound is promised (CGPM 2022 "
     "Resolution 4 raises the 0.9 s limit in or before 2035), and Swiss Delta T is extrapolated."),
)


def _iso(moment: datetime) -> str:
    return moment.isoformat().replace("+00:00", "Z")


def era(utc: datetime) -> str:
    for code, start, end, _ in ERAS:
        if (start is None or utc >= start) and (end is None or utc < end):
            return code
    raise AssertionError("eras cover every instant")


def canonical_sha256(document: dict) -> str:
    """SHA-256 of canonical JSON (sorted keys, compact separators), as the TZif manifest digest."""
    return hashlib.sha256(json.dumps(document, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


@lru_cache(maxsize=1)
def binding_distribution_version() -> str | None:
    """Installed pyswisseph distribution version; None if the binding has no distribution metadata."""
    try:
        return metadata.version("pyswisseph")
    except metadata.PackageNotFoundError:
        return None


def _flags(swe, names: tuple[str, ...]) -> int:
    value = 0
    for name in names:
        value |= getattr(swe, name)
    return value


def _ephemeris(manifest: dict) -> dict:
    required = [e for e in manifest["files"] if e.get("required") is True]
    return {
        "source_repository": manifest["source"]["repository"],
        "source_commit": manifest["source"]["commit"],
        "manifest_version": manifest["manifest_version"],
        "manifest_sha256": canonical_sha256(manifest),
        "manifest_sha256_method": "SHA-256 of the packaged ephemeris-manifest.json as canonical JSON "
                                  "(sorted keys, separators ',' and ':')",
        "required_files": [{"name": e["name"], "size_bytes": e["size_bytes"], "sha256": e["sha256"]}
                           for e in required],
        "verified_before_calculation": True,
        "verification": "every required file matched its size and SHA-256 before any Swiss call",
        "coverage_years": [manifest["coverage"]["start_year"], manifest["coverage"]["end_year"]],
    }


def _disclosures(utc: datetime, latitude: float) -> list[dict]:
    out = []
    if utc >= LEAP_SECOND_LIST_EXPIRY:
        out.append({"code": "FUTURE_CIVIL_TIME_PROJECTED",
                    "description": "The birth instant is after the pinned IERS leap-second list expiry "
                                   "(2027-06-28): civil-time rules, leap seconds, UT1-UTC and Delta T are "
                                   "projections, not records."})
    if abs(latitude) > HIGH_LATITUDE_DISCLOSURE_DEG:
        out.append({"code": "HIGH_LATITUDE_TIME_SENSITIVITY",
                    "description": "Absolute latitude above 60 deg: ascendant sensitivity to birth-time uncertainty "
                                   "can be greater for some dates and sidereal times, but is not uniformly "
                                   "greater. An accurate recorded birth time is important. Descriptive only; "
                                   "calculation and acceptance are unchanged."})
    return out


def calculation_metadata(*, utc: datetime, latitude: float, swe, ephemeris_manifest: dict,
                         timezone_provenance: dict, input_policy: dict, validation_status: str) -> dict:
    side = "on_or_after_switch" if utc >= SIDEREAL_MODEL_SWITCH else "before_switch"
    current_era = era(utc)
    return {
        "metadata_schema": METADATA_SCHEMA,
        "conventions": {
            "zodiac": "sidereal",
            "ayanamsa": {
                "name": "Lahiri",
                "swiss_mode": "SIDM_LAHIRI",
                "swiss_mode_number": swe.SIDM_LAHIRI,
                "swiss_call": "set_sid_mode(SIDM_LAHIRI, 0, 0)",
                "kind": "true_ayanamsha",
                "definition": "Lahiri (Chitrapaksha), Swiss Ephemeris SE_SIDM_LAHIRI (mode 1), IAE 1985 "
                              "definition, true ayanamsha, Swiss default precession; no SIDBIT options",
            },
            "planetary_positions": {
                "center": "geocentric",
                "position": "apparent",
                "frame": "true ecliptic and equinox of date, minus the true ayanamsha",
                "swiss_function": "calc_ut",
                "swiss_flags": list(PLANET_FLAG_NAMES),
                "swiss_flags_value": _flags(swe, PLANET_FLAG_NAMES),
                "swiss_bodies": list(PLANET_BODIES),
                "moshier_fallback": "refused",
            },
            "nodes": {
                "rahu": "mean",
                "rahu_swiss_body": "MEAN_NODE",
                "ketu": "exactly opposite the unrounded mean Rahu; categories from the exact sum Rahu + 180",
            },
            "houses": {
                "d1_model": "whole_sign",
                "rule": "house = ((rashi(body) - rashi(lagna)) mod 12) + 1",
            },
            "ascendant": {
                "definition": "eastern rising point of the ecliptic, minus the true Lahiri ayanamsha",
                "swiss_function": "houses_ex",
                "swiss_house_system": ASCENDANT_HOUSE_SYSTEM,
                "swiss_flags": list(ASCENDANT_FLAG_NAMES),
                "swiss_flags_value": _flags(swe, ASCENDANT_FLAG_NAMES),
                "value": "ascmc[0]",
                "note": "The house-system argument selects the Swiss call only; the D1 house model is "
                        "whole_sign. Cusps are not used.",
            },
            "swiss_state": {
                "reset_per_request_under_lock": ["set_ephe_path(verified directory)",
                                                 "set_sid_mode(SIDM_LAHIRI, 0, 0)",
                                                 "set_delta_t_userdef(DELTAT_AUTOMATIC)"],
            },
            "longitude_display": {"range": "[0, 360)", "decimals": 8, "note": "360 is shown as 0"},
            "classification": "Rashi, Navamsa, Nakshatra, Pada and houses use unrounded longitudes on "
                              "half-open segments, never the 8-decimal display",
        },
        "swiss_ephemeris": {
            "library_version": swe.version,
            "python_binding": "pyswisseph",
            "python_binding_version": binding_distribution_version(),
        },
        "ephemeris_data": _ephemeris(ephemeris_manifest),
        "timezone_data": {**timezone_provenance, "host_timezone_database_used": False,
                          "verification": "the zone file matched the pinned manifest SHA-256 before use"},
        "time_scale": {
            "pipeline": "local civil time + explicit offset -> validated against the pinned IANA zone -> "
                        "civil UTC -> swe.julday (Gregorian) -> Swiss UT-based calculation; TT from the "
                        "Swiss automatic Delta T",
            "ut1_assumption": "civil UTC is treated as UT1 (an assumption, not a measured UT1 correction)",
            "measured_ut1_minus_utc_used": False,
            "earth_orientation_data_used": False,
            "delta_t": {
                "source": "Swiss Ephemeris automatic Delta T (DELTAT_AUTOMATIC, reset per request)",
                "user_override_used": False,
                "measured_series_used": False,
                "note": "Swiss 2.10.03 tabulates Delta T to 2028 and extrapolates afterwards; future Delta T "
                        "is a model projection",
            },
            "era": current_era,
            "era_basis": "converted UTC instant",
            "era_description": next(text for code, _, _, text in ERAS if code == current_era),
            "leap_second_list_expiry_utc": _iso(LEAP_SECOND_LIST_EXPIRY),
            "leap_second_list_source": "IERS leap-seconds.list as shipped in tz 2026e (pinned research value; "
                                       "later IERS publications are not reflected)",
            "sidereal_time_model": {
                "switch_ut": _iso(SIDEREAL_MODEL_SWITCH),
                "recorded_step_arcsec": SIDEREAL_MODEL_STEP_ARCSEC,
                "chart_side": side,
                "note": "Swiss 2.10.03 switches its default sidereal-time model at 2050-01-01 0h UT "
                        "(recorded step about -1.908 arcsec, Lagna about -1.7 arcsec at New Delhi). "
                        "Version-specific model behaviour, not a precision guarantee.",
            },
        },
        "input_policy": input_policy,
        "disclosures": _disclosures(utc, latitude),
        "validation": {
            "status": validation_status,
            "claim_boundary": "Swiss-on-Swiss integration conformance only; not independent astronomical "
                              "validation, mathematical verification or historical clock verification",
        },
    }


def legacy_projection(chart: dict) -> dict:
    """The 0.1.0 output: drop the P7 block and restore the previous schema version."""
    if chart.get("schema_version") != SCHEMA_VERSION or METADATA_KEY not in chart:
        raise ValueError("not a P7 chart")
    legacy = {k: v for k, v in chart.items() if k != METADATA_KEY}
    legacy["schema_version"] = LEGACY_SCHEMA_VERSION
    return legacy


def date_text(value: date) -> str | None:
    return None if value == date.min else value.isoformat()
