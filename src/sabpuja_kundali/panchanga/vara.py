"""Sunrise, sunset and sunrise-based Vara at birth for the extended report (KUN-PAN-RPT-002, issue #83).

Produces the versioned document `sabpuja-panchanga-vara/1`, the only input of the opt-in sunrise/Vara
report page. It adds no astronomy of its own: every instant comes from the independently QA-accepted
validation module `sun.py` (PR #82 at c759c41, ENGINEERING PASS), called only through its public
functions `vara()` and `sun_day()` with one fixed convention.

Convention: adopted by the owner on 2026-11-12 for customer release of the 14-page English Janam Kundali
Essentials edition (`janam-kundali-essentials-en/1`) only, recorded on PR #93, comment 6822876554, and in
docs/DECISIONS.md (KUN-PAN-VARA-G2-001). Earlier development-stage decision: PR #82, comment 6681108990.

* PAN-D03: `SUN-D-IMD-47`, the IMD definition (upper limb, 31' refraction + 16' semidiameter, centre 47'
  below a level sea-level horizon), applied at the BIRTHPLACE coordinates. This is Sabpuja's birthplace
  implementation of the IMD definition, not a reproduction of IMD's Central Station or city tables.
  `SUN-A-USNO-50` stays test-only and is never used or offered here.
* PAN-D05: Vara is the weekday of the local civil date of the latest sunrise at or before the birth
  instant, half-open [sunrise_D, sunrise_D+1). The civil weekday of the birth date is reported beside
  it and is never substituted for it.
* PAN-D11-B: a physically undefined sunrise is a typed `unavailable`, never inferred.
* PAN-D17: the sunset is the first setting after the governing sunrise, under the same 47' rule.

Beyond `sun.vara()` this module requires the next sunrise to exist, because the Vara day is the
interval up to it: if the sunrise that ends the day is physically undefined (polar day or night begins),
the Vara is withheld as `unavailable` (`VARA_DAY_END_UNDEFINED`) rather than shown as a day without an
end. A next sunrise beyond the supported local dates (D13-A, after 2100-12-31) is only not computed; the
Vara itself is then still defined by its sunrise.

Near-sunrise caution: `boundary.near_sunrise` is true when the birth instant is within 300 s (inclusive)
of the governing or of the next sunrise, computed on the unrounded microsecond instants. The 300 s band is
a conservative PRESENTATION heuristic that tells the reader to check the recorded birth time; it is not a
measured or claimed physical accuracy.

The chart request is validated and computed by the chart engine first, so every chart refusal keeps its
code, text and order; the sun module's own refusals follow. Ephemeris, Swiss and numerical failures raise.
Birth details are never logged. Status: owner-adopted method for the English Essentials edition, with
engineering tests and an independent scientific review (KUN-PAN-VARA-RELEASE-001); calculated, not observed.

CLI (same input contract as the chart and M1 CLIs):  python -m sabpuja_kundali.panchanga.vara < request.json
"""
from __future__ import annotations

from datetime import date, timedelta
import json
import sys

from .. import engine, provenance
from ..engine import InputRefusalError
from . import sun as _sun

SCHEMA = "sabpuja-panchanga-vara/1"
STATUS = "OWNER_ADOPTED_FOR_ESSENTIALS_EN_CUSTOMER_RELEASE"
METHOD_ID = "KUN-PAN-RPT-002"
CONVENTION = "SUN-D-IMD-47"
NEAR_SUNRISE_SECONDS = 300
CLAIM_BOUNDARY = ("Owner-adopted method (PAN-D03, PAN-D05, PAN-D11-B, PAN-D17; PR #93 comment 6822876554) "
                  "for customer release of the English Janam Kundali Essentials edition only, with engineering "
                  "tests and an independent scientific review. Sunrise and sunset are calculated for the "
                  "birthplace with a sea-level, level-horizon, geocentric model under the IMD 47' definition; "
                  "they are not observations, do not establish when the Sun was actually visible, and no "
                  "physical accuracy is certified. Times are approximate to the minute. Other Panchangs may use "
                  "another sunrise rule or reference place and can differ.")
DAY_END_UNDEFINED = "VARA_DAY_END_UNDEFINED"
NEXT_OUTSIDE = "NEXT_SUNRISE_OUTSIDE_ENVELOPE"

METHOD = {
    "method_id": METHOD_ID,
    "sun_module": {"method_id": _sun.METHOD_ID, "accepted_at": "c759c412b22753f7f5b6134e2aaaad0f04412007",
                   "functions": "sun.vara and sun.sun_day only"},
    "convention": CONVENTION,
    "convention_decision": "PAN-D03 SUN-D-IMD-47 at the birthplace, with PAN-D05, PAN-D11-B and PAN-D17, "
                           "adopted by the owner on 2026-11-12 for customer release of "
                           "janam-kundali-essentials-en/1 only (PR #93 comment 6822876554); development stage "
                           "earlier (PR #82 comment 6681108990)",
    "depression_arcmin": _sun.CONVENTIONS[CONVENTION]["depression_arcmin"],
    "refraction_arcmin": _sun.CONVENTIONS[CONVENTION]["refraction_arcmin"],
    "semidiameter_arcmin": _sun.CONVENTIONS[CONVENTION]["semidiameter_arcmin"],
    "place": "birthplace latitude and longitude of the chart request",
    "observer": "sea level, level horizon, geocentric; no weather, elevation, terrain or dip model",
    "vara_rule": "PAN-D05: weekday of the local civil date of the latest sunrise at or before the birth "
                 "instant, [sunrise_D, sunrise_D+1); the civil weekday is shown separately, never substituted",
    "day_end": "the Vara is withheld when the next sunrise is physically undefined; a next sunrise after "
               "the supported local dates is not computed",
    "sunset": "PAN-D17: first setting after the governing sunrise, same 47' rule",
    "unavailable": "PAN-D11-B: typed unavailable, never inferred",
    "near_sunrise": f"birth within {NEAR_SUNRISE_SECONDS} s (inclusive) of the governing or next sunrise, on "
                    "unrounded instants; a presentation heuristic, not an accuracy bound",
    "display": "instants are whole UTC seconds here; reports round to the minute and mark them approximate",
}


def _unavailable(reason: str, condition: str) -> dict:
    return {"status": "unavailable", "reason": reason, "condition": condition}


def _event(value: dict) -> dict:
    if value.get("status") != "available":
        return dict(value)
    return {k: value[k] for k in ("status", "utc_us", "utc", "local", "local_date")}


def calculate(request: object, ephe_path: str | None = None) -> dict:
    """Return the `sabpuja-panchanga-vara/1` document, or raise one of EXPECTED_ERRORS."""
    chart = engine.calculate(request, ephe_path)        # chart refusals first, unchanged
    v = _sun.vara(request, convention=CONVENTION, ephe_path=ephe_path)
    calls = v["swiss_calls"]
    birth_utc = chart["birth"]["utc"]
    birth_us = _sun._us(engine._parse_birth(request["birth_datetime"], request["timezone"]))
    lat, lon, tz = request["latitude"], request["longitude"], request["timezone"]
    vara, governing = v["vara"], _event(v["governing_sunrise"])
    sunset = next_sunrise = None
    boundary = {"status": "not_assessed", "reason": "VARA_UNAVAILABLE"}
    differs = v["vara_differs_from_civil_weekday"]
    if vara["status"] == "available":
        gdate = date.fromisoformat(vara["sunrise_local_date"])
        day = _sun.sun_day(gdate.isoformat(), lat, lon, tz, convention=CONVENTION, ephe_path=ephe_path)
        calls += day["swiss_calls"]
        if day["sunrise"].get("utc_us") != governing["utc_us"]:
            raise _sun.SunComputationError(_sun.AMBIGUOUS, "governing sunrise not reproduced")
        sunset = _event(day["sunset"])
        ndate = gdate + timedelta(days=1)
        if ndate > _sun.LAST_DATE:
            next_sunrise = _unavailable(_sun.OUTSIDE_ENVELOPE, NEXT_OUTSIDE)
        else:
            nxt = _sun.sun_day(ndate.isoformat(), lat, lon, tz, convention=CONVENTION, ephe_path=ephe_path)
            calls += nxt["swiss_calls"]
            next_sunrise = _event(nxt["sunrise"])
        if next_sunrise["status"] == "available" and not birth_us < next_sunrise["utc_us"]:
            raise _sun.SunComputationError(_sun.AMBIGUOUS, "birth is not before the next sunrise")
        if not governing["utc_us"] <= birth_us:
            raise _sun.SunComputationError(_sun.AMBIGUOUS, "birth is before the governing sunrise")
        if next_sunrise["status"] == "unavailable" and next_sunrise["reason"] == _sun.UNDEFINED:
            withheld = _unavailable(_sun.UNDEFINED, DAY_END_UNDEFINED)
            vara, differs = withheld, None
            boundary = {"status": "not_assessed", "reason": "VARA_UNAVAILABLE"}
        else:
            window = NEAR_SUNRISE_SECONDS * _sun.MICROS
            after = birth_us - governing["utc_us"]
            before = next_sunrise["utc_us"] - birth_us if next_sunrise["status"] == "available" else None
            near = after <= window or (before is not None and before <= window)
            boundary = {"status": "assessed" if before is not None or near else "partial",
                        "window_seconds": NEAR_SUNRISE_SECONDS,
                        "after_governing_sunrise_us": after,
                        "before_next_sunrise_us": before,
                        "near_sunrise": near,
                        "nearest": None if not near else ("governing" if before is None or after <= before
                                                          else "next")}
            if boundary["status"] == "partial":
                boundary["reason"] = NEXT_OUTSIDE
    else:
        governing = dict(vara)
    if sunset is None:
        sunset = dict(vara if vara["status"] == "unavailable" else governing)
    if next_sunrise is None:
        next_sunrise = dict(vara)
    meta = chart[provenance.METADATA_KEY]
    return {
        "schema": SCHEMA,
        "status": STATUS,
        "claim_boundary": CLAIM_BOUNDARY,
        "method": METHOD,
        "birth": {"utc": birth_utc, "timezone": tz, "latitude": lat, "longitude": lon},
        "civil": {"date": v["civil_date"], "weekday": v["civil_weekday"]},
        "vara": dict(vara),
        "vara_differs_from_civil_weekday": differs,
        "governing_sunrise": governing,
        "sunset": sunset,
        "next_sunrise": next_sunrise,
        "boundary": boundary,
        "provenance": {
            "swiss_ephemeris": meta["swiss_ephemeris"],
            "ephemeris_manifest_sha256": meta["ephemeris_data"]["manifest_sha256"],
            "timezone_data": {k: meta["timezone_data"][k]
                              for k in ("package_version", "iana_version", "manifest_sha256")},
            "swiss_calls": calls,
            "chart_schema_version_unchanged": provenance.SCHEMA_VERSION,
            "calculation_metadata_schema_unchanged": provenance.METADATA_SCHEMA,
        },
    }


EXPECTED_ERRORS = _sun.EXPECTED_ERRORS


def main() -> int:
    try:
        data = sys.stdin.buffer.read(4097)
        if len(data) > 4096:
            raise InputRefusalError("REQUEST_INVALID", "Input exceeds 4 KB limit")
        try:
            request = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, ValueError, RecursionError):
            raise InputRefusalError("REQUEST_INVALID", "input must be one JSON object") from None
        result = calculate(request)
    except EXPECTED_ERRORS as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
