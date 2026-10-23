# Calculation request/output contract, foundation v0.1.0

**Status: local CLI interface implemented; HTTP API not implemented.**

Input from stdin (JSON object, max 4KB):
```json
{
  "birth_datetime": "2000-01-01T17:30:00+05:30",
  "timezone": "Asia/Kolkata",
  "latitude": 28.6139,
  "longitude": 77.2090
}
```

Requirements:
- `birth_datetime` is the exact birth-local time in one strict profile (KUN-03 P5, D2): `YYYY-MM-DDTHH:MM[:SS[.f]]` (1–6 fraction digits, ASCII digits, upper-case `T`) followed by `Z` or `±HH:MM[:SS]` (offset seconds allowed for historical IANA offsets such as `+05:21:10`). Represented microseconds are kept; nothing is rounded, truncated or coerced. Space separators, lower-case `t`/`z`, ISO basic or week/ordinal dates, `,` decimals, more than 6 fraction digits and other offset spellings are refused. `-00:00` is read as a zero offset.
- `timezone` is the IANA timezone identifier; conversion must match the offset, including DST/historical rules.
- Timezone rules come only from the pinned PyPI `tzdata==2026.5` (IANA 2026e), each TZif file verified against `src/sabpuja_kundali/tzif-manifest.json`; the host's system zoneinfo, `PYTHONTZPATH` and `TZ` are never used. A key not in the manifest is invalid input. Missing, mismatched or wrong-version timezone data fails closed with a `TZDATA_*` code (no host fallback).
- Supported birth dates (SCI-03 initial window): the **local civil date** as written in `birth_datetime` must be 1900-01-01 to 2100-12-31 inclusive. It is checked before conversion (after the timezone is recognised and before the offset is matched), so the UTC instant may be as early as 1899-12-31T10:00:00Z (local 1900-01-01T00:00:00 at UTC+14) or as late as 2101-01-01T11:59:59.999999Z (local 2100-12-31T23:59:59.999999 at UTC−12; microsecond precision is accepted). A date outside is refused with `DATE_OUTSIDE_SUPPORTED_RANGE` (`UnsupportedInputError`, a `ValueError` subclass carrying `.code`). Within the window, the historical-clock gate below then refuses every local date before 1970-01-01, so the earliest instant actually charted today is 1969-12-31T10:00:00Z (local 1970-01-01T00:00:00 at UTC+14).
- Historical clocks (SCI-03 RG-HIST Option B, KUN-03 P8): no birthplace clock before 1970 is verified, so a birth whose **local civil date** is before 1970-01-01 is refused with `HISTORICAL_CLOCK_UNVERIFIED` (`UnsupportedInputError`) in **every** recognised zone, including `UTC`, `GMT` and `Etc/*`. It is judged on the date as written, never the UTC date, after all other time checks and before the coordinates. The detail text is fixed and repeats nothing from the request. The rule is the versioned table `HISTORICAL_CLOCK_GATE` in `engine.py` ("SCI-03 RG-HIST Option B, version 1"; owner records on PR #20, comments 6336254894 and 6350086727):

  | Zone | Refused local dates | Policy |
  |---|---|---|
  | every recognised zone | up to and including 1969-12-31 | refuse: `HISTORICAL_CLOCK_UNVERIFIED` |

  Verified exceptions (`HISTORICAL_CLOCK_EXCEPTIONS`: zone, first and last local date) are empty. Each one needs DATA-01 evidence, QA and its own owner approval; a wildcard exception is ignored. There is no runtime, CLI or environment switch for the gate.
- Latitude decimal north-positive, longitude east-positive. Both must be JSON numbers (not booleans or strings), finite (no `NaN`/`Infinity`, no integers too large for a float) and within the accepted range: latitude -66.0 to 66.0 inclusive (SCI-01g supported band, the same for every date), longitude -180 to 180 inclusive. A finite latitude outside the band is refused with `LATITUDE_OUTSIDE_SUPPORTED_BAND` before any Swiss call; non-numbers and non-finite values are refused first with `COORDINATE_INVALID`.
- No name, email, phone, address, account ID or other identifying attributes in the calculation request.
- A birthplace autocomplete service is future work and must be offline/self-hosted.

Success returns JSON `schema_version`, `validation_status`, `method`, `birth`, `lagna`, `moon_nakshatra` and `planets`. Planet values contain longitude, Rashi, D9 sign and whole-sign house. Output is not yet independently verified.

Longitude and category semantics:
- Rashi (30°), Nakshatra (40/3°) and Pada/D9 (10/3°) segments are half-open, `[start, end)`. Every category, house, Moon Nakshatra and Ketu (exactly opposite Rahu) is derived from the unrounded Swiss Ephemeris value with exact arithmetic, never from the displayed number.
- `longitude_deg` is display only: the value normalized to `[0, 360)` and rounded to 8 decimals. A rounding that reaches 360 is shown as `0.0`; `360.0` is never emitted.
- Near-boundary display ambiguity: within 5e-9° below a boundary, the displayed value can equal the boundary while the category is the segment before it (raw 29.999999996 is shown as `30.0` and stays Mesha; raw 359.999999996 is shown as `0.0` and stays Meena). Do not re-derive categories from `longitude_deg`; use the category fields.

Errors: CLI writes JSON `{"error":"CODE: detail"}` to stderr, writes nothing to stdout, prints no traceback and exits 2. Error text never repeats the birth time, timezone or coordinates. No HTTP response codes are promised yet. Network service contracts must be separately reviewed and versioned.

Input refusal codes (KUN-03 P5, D1/D4). Every input refusal raises `InputRefusalError` (a `ValueError` carrying `.code`; `UnsupportedInputError` is its subclass for valid input outside the supported envelope). Checks run in this fixed order and the first failing check decides the code, so one input always gets the same code; every birth-time check comes before any coordinate check:

| Order | Code | Refused when | Class |
|---|---|---|---|
| 1 | `REQUEST_INVALID` | not one JSON object, over 4,096 bytes (counted before UTF-8 decoding), not UTF-8, wrong keys, or `birth_datetime`/`timezone` not strings | `InputRefusalError` |
| 2 | `TIME_FORMAT_INVALID` | outside the strict profile, including hour > 23, minute > 59, second > 60, offset hour > 23 or offset minute/second > 59 | `InputRefusalError` |
| 3 | `TIME_OFFSET_REQUIRED` | a profile-conforming local time with no offset | `InputRefusalError` |
| 4 | `TIME_LEAP_SECOND_UNSUPPORTED` | seconds field `60` | `UnsupportedInputError` |
| 5 | `DATE_INVALID` | the calendar date does not exist (for example 1900-02-29, 2100-02-29, month 13, year 0000) | `InputRefusalError` |
| 6 | `TIMEZONE_INVALID` | not a key in the pinned TZif manifest (P1) | `InputRefusalError` |
| 7 | `TIMEZONE_NOT_LOCATION_BASED` | **reserved, not raised** (D3: `UTC`, `GMT`, `Etc/*` stay accepted until a separate pre-release package) | — |
| 8 | `DATE_OUTSIDE_SUPPORTED_RANGE` | local civil date outside 1900-01-01 to 2100-12-31 (SCI-03, P4) | `UnsupportedInputError` |
| 9 | `TIME_NONEXISTENT_LOCAL` | the wall time does not exist in the zone (DST or historical gap), whatever the offset | `InputRefusalError` |
| 10 | `TIME_OFFSET_MISMATCH` | the wall time exists but the offset is not one IANA gives for it (one offset normally, two in a fold) | `InputRefusalError` |
| 11 | `HISTORICAL_CLOCK_UNVERIFIED` | local civil date before 1970-01-01 in any zone, unless a verified exception covers it (none yet; SCI-03 RG-HIST Option B, P8) | `UnsupportedInputError` |
| 12 | `COORDINATE_INVALID` | latitude or longitude not a JSON number (booleans and strings included), not finite, or longitude outside -180 to 180 | `InputRefusalError` |
| 13 | `LATITUDE_OUTSIDE_SUPPORTED_BAND` | finite latitude outside -66.0 to 66.0 (SCI-01g, P2) | `UnsupportedInputError` |

Timezone-data failures are server faults, not input refusals: when the pinned data is missing, of the wrong version or fails its SHA-256 check, loading the zone at step 6 raises a `TZDATA_*` `RuntimeError` (`TimezoneDataError`, carrying `.code`) instead of `TIMEZONE_INVALID`. Steps 7–13 and Swiss are then never reached, and nothing falls back to the host zoneinfo. A fold (repeated hour) is not refused: the given offset selects the instant. Gaps and offsets are judged from IANA data only; no offset is ever inferred. `EPHEMERIS_*`, `ASCENDANT_UNCOMPUTABLE` and other `RuntimeError`s come after these checks and are unchanged.

Three coordinate failures are deliberately distinct:
- **Invalid latitude/longitude** (`COORDINATE_INVALID`, `InputRefusalError`): the value is not a usable number, or the longitude is outside -180 to 180, for example `"COORDINATE_INVALID: latitude must be a number"`, `"COORDINATE_INVALID: latitude must be a finite number"` or `"COORDINATE_INVALID: longitude must be between -180 and 180 (inclusive)"`. The caller must correct the input.
- **Outside the supported latitude band** (`UnsupportedInputError`, a `ValueError` subclass carrying `.code`; error text `LATITUDE_OUTSIDE_SUPPORTED_BAND: latitude must be between -66 and 66 (inclusive)`): the latitude is a finite number outside -66.0 to 66.0. It is refused for every date and longitude, before the ephemeris check and before any Swiss Ephemeris call, so such a request never reaches the ascendant calculation. The ascendant vehicle (`b"W"`, SCI-01e) would compute at any latitude, so this band alone decides which locations are accepted. This is the owner-approved SCI-01g initial support policy, not a permanent astronomical limit; any wider support would need a new owner decision. A disclosure of birth-time sensitivity above 60° (`HIGH_LATITUDE_TIME_SENSITIVITY`) is not emitted yet; it is assigned to future P7 calculation metadata.
- **Cannot compute** (`ChartComputationError`, error text `ASCENDANT_UNCOMPUTABLE: ...`): defensive only. It is raised if Swiss Ephemeris unexpectedly fails the ascendant call (`houses_ex` with `b"W"`) for an in-band request; this is not expected for valid input. No partial chart is returned and no other house method is substituted.

Lagna (SCI-01e, KUN-03 P3): `ascmc[0]` of `houses_ex(jd_ut, lat, lon, b"W", FLG_SIDEREAL)`, the eastern rising point of the ecliptic minus the true Lahiri ayanamsa. Inside the ±66.0° band it was bit-identical to the previous `b"P"` value at every sampled point (KUN-02 E-A1, 167,612 points; P3 tests and comparison grid), and no accepted chart changed in those samples. This is sampled evidence, not a proof. The vehicle is not yet named in the output; it is recorded in P7 calculation metadata.

**Privacy**: CLI retains no state; stdout contains sensitive birth timestamp/coordinates and must be protected by the caller. Never send customer content to telemetry or GitHub.
