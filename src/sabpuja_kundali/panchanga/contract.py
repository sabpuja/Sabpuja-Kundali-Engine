"""`sabpuja-panchanga/1`: the separate, versioned birth-instant Panchanga document (D12-A).

The request is validated by the unchanged chart engine first (`engine.calculate`),
so every existing refusal keeps its code and its order (D13-A, PAN-QA-09). The
chart itself is not modified or embedded. Then the pinned ephemeris directory is
verified again and every Panchanga longitude comes from `astro.SwissSession`.

Scope (D02-M1, KUN-PAN-M1 section 1): Tithi, Paksha and Paksha day; Karana
index; Yoga index; Moon Nakshatra and Pada; the start and end of the current
Tithi, Karana, Yoga, Nakshatra and Pada. No sunrise, sunset, Vara, Masa,
Samvat, names other than the chart's Nakshatra identifiers, or display text.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
import math

from .. import engine, provenance
from ..engine import EXPECTED_ERRORS as CHART_EXPECTED_ERRORS
from ..ephemeris import load_manifest as load_ephemeris_manifest, verify_ephemeris_dir
from ..timezones import get_zone
from . import rules
from .astro import SwissSession, utc_from_micros, utc_micros
from .search import DEFAULT_LIMITS, MICROS, SearchLimits, TransitionNotConverged, find_transition

SCHEMA = "sabpuja-panchanga/1"
METHOD_ID = "KUN-PAN-M1"
METHOD_REVISION = "SCI-PAN-01 rev 0.5 with KUN-PAN-M1-DEC-001 owner selections (adopted at main 25cfde4)"
DECISIONS = ("D01-A", "D02-M1", "D07-A", "D08-A", "D09-A-M1", "D10-A (TS-1 only)", "D12-A", "D13-A",
             "D14-A-M1", "D15-a-R", "D15-b-R", "D16-M1-INDEX", "D18-A", "D20-M1-SCOPED")
VALIDATION_STATUS = "ENGINEERING_UNVERIFIED_PENDING_INDEPENDENT_QA"

# D13-A: local rendering only for instants whose local civil date lies in the
# envelope. The first date is the day after the historical-clock gate's last
# refused date (1969-12-31); the last is the SCI-03 window end. Tests pin both.
LOCAL_RENDERING_FIRST_DATE = date(1970, 1, 1)
LOCAL_RENDERING_LAST_DATE = engine.SUPPORTED_LOCAL_DATES[1]

NOT_CONVERGED = "PANCHANGA_TRANSITION_NOT_CONVERGED"
IDENTITY_FAILED = "PANCHANGA_CHART_IDENTITY_FAILED"
NAME_NOT_ADOPTED = "PANCHANGA_METHOD_NOT_ADOPTED"


class PanchangaComputationError(RuntimeError):
    """The whole Panchanga document is refused. Fixed text; never birth data or instants."""

    def __init__(self, code: str, detail: str):
        super().__init__(f"{code}: {detail}")
        self.code = code


EXPECTED_ERRORS = CHART_EXPECTED_ERRORS + (PanchangaComputationError,)

_FIXED_DETAIL = {
    NOT_CONVERGED: "a Panchanga transition could not be bracketed and converged within the approved "
                   "limits; no Panchanga produced",
    IDENTITY_FAILED: "the Panchanga Moon Nakshatra did not reproduce the chart; no Panchanga produced",
}


def _check_limits(limits) -> None:
    """D09-A-M1 maxima are frozen: a looser or malformed override is refused, never computed.

    Each field must be a plain positive int no larger than its DEFAULT_LIMITS value
    (max_iterations may be 0). Stricter values (used for failure injection) are allowed,
    and the document's method block then reports the limits actually used. No new
    public code: the existing PANCHANGA_TRANSITION_NOT_CONVERGED refusal is used, whose
    fixed text already states that no Panchanga is produced outside the approved limits.
    """
    if type(limits) is not SearchLimits:
        raise _refuse(NOT_CONVERGED)
    for name in ("step_us", "max_extent_us", "max_iterations", "bracket_max_us"):
        value, frozen = getattr(limits, name), getattr(DEFAULT_LIMITS, name)
        floor = 0 if name == "max_iterations" else 1
        if type(value) is not int or not floor <= value <= frozen:
            raise _refuse(NOT_CONVERGED)


def _refuse(code: str) -> PanchangaComputationError:
    return PanchangaComputationError(code, _FIXED_DETAIL[code])


def _display_deg(value) -> float:
    """8-decimal display of an exact angle in [0, 360); never used for classification."""
    shown = round(float(value), 8)
    return 0.0 if shown == 360.0 else shown


def _iso_utc(second: int) -> str:
    return utc_from_micros(second * MICROS).strftime("%Y-%m-%dT%H:%M:%SZ")


def _instant(second: int, zone, transition) -> dict[str, object]:
    moment = utc_from_micros(second * MICROS)
    local = moment.astimezone(zone)
    out = {"utc": _iso_utc(second)}
    if LOCAL_RENDERING_FIRST_DATE <= local.date() <= LOCAL_RENDERING_LAST_DATE:
        out["local"] = local.isoformat()
        out["local_rendering"] = "rendered"
    else:
        out["local_rendering"] = "withheld_outside_envelope"
    out["search"] = {"bracket_steps": transition.bracket_steps, "iterations": transition.iterations,
                     "final_bracket_us": transition.bracket_us}
    return out


def _method(lim: SearchLimits) -> dict[str, object]:
    return {
        "method_id": METHOD_ID,
        "method_revision": METHOD_REVISION,
        "decisions": list(DECISIONS),
        "longitude_frame": "SCI-01d geocentric apparent sidereal, Lahiri (SIDM_LAHIRI), calc_ut with "
                           "FLG_SWIEPH | FLG_SIDEREAL; the chart's call path",
        "elongation": "E = (Moon - Sun) mod 360 on exact unrounded values",
        "yoga_sum": "S = (Sun + Moon) mod 360 on exact unrounded values",
        "boundary_rule": "half-open [start, end) on exact unrounded values; an edge value belongs to the "
                         "higher sector",
        "tithi_rule": "number = sector(E, 30) + 1; paksha shukla for 1-15, krishna for 16-30; "
                      "paksha_day = ((number - 1) mod 15) + 1",
        "karana_rule": "index = sector(E, 60) + 1; names not adopted",
        "yoga_rule": "index = sector(S, 27) + 1; names not adopted",
        "nakshatra_rule": "the chart moon_nakshatra rule: pada sector(Moon, 108), nakshatra = pada div 4",
        "transition_search": {
            "method": "TS-1 bounded bracketing and bisection",
            "bracket_step_hours": lim.step_us / (3600 * MICROS),
            "bracket_extent_max_days_each_direction": lim.max_extent_us / (86400 * MICROS),
            "bisection_max_iterations": lim.max_iterations,
            "transition_bracket_max_seconds": lim.bracket_max_us / MICROS,
            "output": "first whole UTC second in the new half-open sector, verified at that second and "
                      "the second before",
            "extrapolation": "never",
        },
        "time_scale": "civil UTC treated as UT1 (SCI-01h), as for the chart; Swiss automatic Delta T",
        "precision_note": "whole-second output is a resolution, not an accuracy claim",
    }


def calculate(request: dict[str, object], ephe_path: str | None = None, *,
              limits: SearchLimits = DEFAULT_LIMITS) -> dict[str, object]:
    """Return the `sabpuja-panchanga/1` document, or raise one of EXPECTED_ERRORS."""
    chart = engine.calculate(request, ephe_path)
    # After every chart refusal (their order is unchanged), before any Panchanga computation.
    _check_limits(limits)
    utc = datetime.fromisoformat(chart["birth"]["utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
    zone = get_zone(chart["birth"]["timezone"])
    ephemeris_manifest = load_ephemeris_manifest()
    folder = verify_ephemeris_dir(engine.ephemeris_path(ephe_path), ephemeris_manifest)
    swe = engine.swiss_runtime()
    t0 = utc_micros(utc)
    with SwissSession(swe, folder) as session:
        sun, moon = session.sun_moon(t0)
        # The birth-instant values must reproduce the chart exactly (D01-A, PAN-QA-08).
        if (rules.moon_nakshatra(moon) != chart["moon_nakshatra"]
                or engine._display_deg(moon) != chart["planets"]["moon"]["longitude_deg"]
                or engine._display_deg(sun) != chart["planets"]["sun"]["longitude_deg"]):
            raise _refuse(IDENTITY_FAILED)
        e, s = rules.elongation(sun, moon), rules.yoga_sum(sun, moon)
        transitions = {}
        try:
            for element in rules.ELEMENTS:
                sector_at = lambda t_us, _el=element: rules.element_sectors(*session.sun_moon(t_us))[_el]
                transitions[element] = (find_transition(sector_at, t0, -1, limits),
                                        find_transition(sector_at, t0, 1, limits))
        except TransitionNotConverged:
            raise _refuse(NOT_CONVERGED) from None
        swiss_calls = session.calls

    def span(element: str) -> dict[str, object]:
        start, end = transitions[element]
        return {"start": _instant(start.second, zone, start), "end": _instant(end.second, zone, end)}

    number = rules.tithi_number(e)
    nak = rules.moon_nakshatra(moon)
    metadata = chart[provenance.METADATA_KEY]
    nak_span, pada_span = span("nakshatra"), span("pada")
    return {
        "schema": SCHEMA,
        "validation_status": VALIDATION_STATUS,
        "claim_boundary": "Engineering output for independent QA only. Not customer-facing. Tithi and "
                          "Karana transitions at E = 0, 90, 180, 270 deg are compared with USNO/NASA "
                          "published minutes; everything else is rule-oracle and Swiss-on-Swiss "
                          "conformance, not independent astronomical accuracy.",
        "method": _method(limits),
        "birth": {"utc": chart["birth"]["utc"], "timezone": chart["birth"]["timezone"]},
        "angles": {"elongation_deg": _display_deg(e), "yoga_sum_deg": _display_deg(s),
                   "note": "8-decimal display only; classification uses the unrounded values"},
        "tithi": {"number": number, "paksha": rules.paksha(number), "paksha_day": rules.paksha_day(number),
                  **span("tithi")},
        "karana": {"index": rules.karana_index(e), "name_omitted": NAME_NOT_ADOPTED, **span("karana")},
        "yoga": {"index": rules.yoga_index(s), "name_omitted": NAME_NOT_ADOPTED, **span("yoga")},
        "nakshatra": {**nak, "start": nak_span["start"], "end": nak_span["end"],
                      "pada_start": pada_span["start"], "pada_end": pada_span["end"]},
        "local_rendering": {
            "zone": chart["birth"]["timezone"],
            "offset_rule": "pinned IANA tzdata (SCI-03), converted from the UTC instant; no rounding",
            "envelope_local_dates": {"first": LOCAL_RENDERING_FIRST_DATE.isoformat(),
                                     "last": LOCAL_RENDERING_LAST_DATE.isoformat()},
            "outside_envelope": "withheld_outside_envelope (D13-A); the UTC instant is still reported",
        },
        "provenance": {
            "swiss_ephemeris": metadata["swiss_ephemeris"],
            "ephemeris_manifest_sha256": metadata["ephemeris_data"]["manifest_sha256"],
            "timezone_data": {k: metadata["timezone_data"][k]
                              for k in ("package_version", "iana_version", "manifest_sha256")},
            "swiss_calls": swiss_calls,
            "chart_schema_version_unchanged": provenance.SCHEMA_VERSION,
            "calculation_metadata_schema_unchanged": provenance.METADATA_SCHEMA,
        },
    }
