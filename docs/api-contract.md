# Calculation request/output contract, schema v0.2.0

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

Success returns JSON `schema_version` (`"0.2.0"`), `validation_status`, `method`, `birth`, `lagna`, `moon_nakshatra`, `planets` and `calculation_metadata` (KUN-03 P7, see below). Planet values contain longitude, Rashi, D9 sign and whole-sign house. Output is not yet independently verified.

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
- **Outside the supported latitude band** (`UnsupportedInputError`, a `ValueError` subclass carrying `.code`; error text `LATITUDE_OUTSIDE_SUPPORTED_BAND: latitude must be between -66 and 66 (inclusive)`): the latitude is a finite number outside -66.0 to 66.0. It is refused for every date and longitude, before the ephemeris check and before any Swiss Ephemeris call, so such a request never reaches the ascendant calculation. The ascendant vehicle (`b"W"`, SCI-01e) would compute at any latitude, so this band alone decides which locations are accepted. This is the owner-approved SCI-01g initial support policy, not a permanent astronomical limit; any wider support would need a new owner decision. Above 60° (absolute) a successful chart carries the descriptive disclosure `HIGH_LATITUDE_TIME_SENSITIVITY` in its calculation metadata (KUN-03 P7); it never changes acceptance or the chart.
- **Cannot compute** (`ChartComputationError`, error text `ASCENDANT_UNCOMPUTABLE: ...`): defensive only. It is raised if Swiss Ephemeris unexpectedly fails the ascendant call (`houses_ex` with `b"W"`) for an in-band request; this is not expected for valid input. No partial chart is returned and no other house method is substituted.

Lagna (SCI-01e, KUN-03 P3): `ascmc[0]` of `houses_ex(jd_ut, lat, lon, b"W", FLG_SIDEREAL)`, the eastern rising point of the ecliptic minus the true Lahiri ayanamsa. Inside the ±66.0° band it was bit-identical to the previous `b"P"` value at every sampled point (KUN-02 E-A1, 167,612 points; P3 tests and comparison grid), and no accepted chart changed in those samples. This is sampled evidence, not a proof. The vehicle is named in the output under `calculation_metadata.conventions.ascendant` (KUN-03 P7).

Swiss Ephemeris state (KUN-03 P9 and Delta T isolation): pyswisseph settings are process- or thread-wide, so every accepted request, while holding the engine's single Swiss lock and before any calculation, sets the verified ephemeris path, Lahiri sidereal mode and automatic Delta T (`set_delta_t_userdef(DELTAT_AUTOMATIC)`). A path, sidereal mode or user-defined Delta T left by an earlier caller therefore cannot change a chart. Automatic Delta T is Swiss Ephemeris's own model; it is restored, not changed. A refused request never reaches the lock or any of these calls.

Swiss Ephemeris failures (KUN-03 Swiss error contract). Once a request has passed every check above and the ephemeris manifest gate, a `swisseph.Error` from Swiss itself is never passed on: it is replaced by a `ChartComputationError` (a `RuntimeError` carrying `.code`) with fixed text, raised `from None`, so neither the Swiss message (which can include server file paths) nor any request value appears. No partial chart is returned, the engine lock is released, and the next request starts from the full Swiss reset. Through the CLI each one is the usual single JSON error on stderr, empty stdout, exit 2.

| Stage | Code | Fixed detail |
|---|---|---|
| `julday` (UTC instant to Julian day; before the lock) | `SWISS_TIME_CALCULATION_FAILED` | Swiss Ephemeris could not convert the birth time; no chart produced |
| `set_ephe_path`, `set_sid_mode`, `set_delta_t_userdef` (per-request reset, in the lock) | `SWISS_STATE_INITIALIZATION_FAILED` | Swiss Ephemeris could not be initialized for this request; no chart produced |
| `calc_ut`, any of the eight bodies | `SWISS_PLANET_CALCULATION_FAILED` | Swiss Ephemeris could not complete the planetary calculation; no chart produced |
| `houses_ex(..., b"W")` | `ASCENDANT_UNCOMPUTABLE` (unchanged) | Swiss Ephemeris could not compute the ascendant for this location and time; no chart produced |

These are server-side calculation failures, not input refusals: they are never reported as `REQUEST_INVALID` or another P5 code, and they are reachable only after every refusal, `TZDATA_*` and `EPHEMERIS_*` check, whose codes and order are unchanged. None is expected for accepted input; in the pinned binding only `calc_ut` and `houses_ex` were seen to raise `swisseph.Error`, and the reset calls are guarded defensively. The existing Moshier refusal ("Swiss ephemeris files unavailable: refused Moshier fallback") is unchanged. Only `swisseph.Error` is translated: any other exception is a programming defect, is not relabelled or swallowed, and ends the CLI with Python's own failure (exit 1, no stdout). This contract covers error handling only; it is not an astronomical certification.

## Calculation metadata (schema 0.2.0, KUN-03 P7)

Every successful chart carries `calculation_metadata` (`metadata_schema` `"sabpuja-calculation-metadata/1"`), built by `src/sabpuja_kundali/provenance.py`. It is **descriptive**: it states the conventions, data and time-scale assumptions that produced the chart. It does not change any position, category, refusal or code, and it adopts no decision-register entry (SCI-01a, SCI-01h and the others stay as recorded there).

**What it is built from.** Only the engine's own constants, the ephemeris manifest that the request was verified against, the pinned timezone loader that verified the zone, and the installed Swiss library and binding versions. The engine loads the ephemeris manifest once per request, verifies the directory against that object and describes the same object, so the metadata cannot name a manifest other than the one checked. Refusals and server faults (`InputRefusalError`, `TZDATA_*`, `EPHEMERIS_*`, `SWISS_*`, `ASCENDANT_UNCOMPUTABLE`) produce no metadata; their codes, text and order are unchanged.

**Deterministic.** No clock, random value, host path, environment value or request text. Two requests in the same era, on the same side of 2050 and with the same disclosures get identical metadata. `TZ`, `PYTHONTZPATH` and the ephemeris directory name do not change it.

### Fields

| Field | Meaning |
|---|---|
| `metadata_schema` | Version of this block. A new key or meaning needs a new value. |
| `conventions.zodiac`, `conventions.ayanamsa` | Sidereal; Lahiri (Chitrapaksha), Swiss `SIDM_LAHIRI` mode 1, IAE 1985 definition, true ayanamsha, Swiss default precession, no `SIDBIT_*` options; set by `set_sid_mode(SIDM_LAHIRI, 0, 0)`. |
| `conventions.planetary_positions` | Geocentric apparent positions on the true ecliptic and equinox of date minus the true ayanamsha: `calc_ut` with `FLG_SWIEPH \| FLG_SIDEREAL` (value 65538) for the eight listed bodies. Moshier fallback is refused. |
| `conventions.nodes` | Mean Rahu (`MEAN_NODE`); Ketu exactly opposite the unrounded Rahu. |
| `conventions.houses` | D1 houses are whole sign: `((rashi(body) - rashi(lagna)) mod 12) + 1`. |
| `conventions.ascendant` | `ascmc[0]` of `houses_ex(jd_ut, lat, lon, b"W", FLG_SIDEREAL)` (flags value 65536). The letter selects the Swiss call only; cusps are not used. |
| `conventions.swiss_state` | The three Swiss settings reset on every request under the engine lock. |
| `conventions.longitude_display`, `conventions.classification` | 8-decimal display in `[0, 360)`; categories from unrounded values on half-open segments. |
| `swiss_ephemeris` | `library_version` (`swe.version`, equal to `method.binding_version`), `python_binding` `"pyswisseph"` and its installed distribution version (pinned in `pyproject.toml`). |
| `ephemeris_data` | Source repository and commit, manifest version, `manifest_sha256` (SHA-256 of the packaged `ephemeris-manifest.json` as canonical JSON: sorted keys, separators `,` and `:`), the required files with size and SHA-256, coverage years. `verified_before_calculation` is always `true`, because a chart is produced only after that check. |
| `timezone_data` | `source`, `package_version`, `iana_version` and `manifest_sha256` of the pinned TZif manifest, exactly as the verifying loader reports them; `host_timezone_database_used` is always `false`. |
| `time_scale` | The pipeline, the UT1 assumption, Delta T source, era, leap-second list expiry and the 2050 sidereal-time model note (below). No per-request number (Julian day, Delta T, sidereal time) is emitted. |
| `input_policy` | The checks this chart passed, read from the engine constants: local date window, historical clock policy (RG-HIST Option B v1, fail closed, refused local dates, exceptions: none), latitude band ±66° inclusive, offset rule and the fixed refusal order. |
| `disclosures` | Zero or more `{code, description}` in fixed order (below). |
| `validation` | `status` (equal to `validation_status`) and the claim boundary. |

### Time scale and eras

The pipeline is: local civil time with an explicit offset, validated against the pinned IANA zone, converted to civil UTC, then `swe.julday` (Gregorian) and Swiss UT-based calculation. **Civil UTC is treated as UT1.** This is an assumption: no measured UT1 − UTC and no Earth-orientation data are used. TT comes from Swiss's automatic Delta T (`DELTAT_AUTOMATIC`, reset per request; tabulated to 2028 and extrapolated after; no user override and no measured series).

`time_scale.era` is judged on the **converted UTC instant**, not the local date (local `1972-01-01T05:00+05:30` is UTC 1971 and is labelled `UTC_BEFORE_LEAP_SECONDS`). Ranges are half-open, start inclusive:

| Era | UTC range | Disclosure |
|---|---|---|
| `CIVIL_TIME_BEFORE_UTC` | before 1961-01-01 | Reachable only through the test-only historical clock override; production refuses these dates. |
| `UTC_BEFORE_LEAP_SECONDS` | 1961-01-01 to 1972-01-01 | Accepted charts here are 1969-12-31 to 1971-12-31 UTC. UT1 − UTC not sourced: an approximation, not verified UT1. |
| `LEAP_SECOND_UTC` | 1972-01-01 to 2027-06-28 | The IERS rule keeps \|UT1 − UTC\| < 0.9 s; that bound is implied under the Swiss Delta T model, not measured for this calculation. |
| `AFTER_LEAP_SECOND_LIST_EXPIRY` | from 2027-06-28 | After the pinned IERS leap-second list expiry (tz 2026e `leap-seconds.list`): leap seconds and UT1 − UTC unknown, no 0.9 s bound promised (CGPM 2022 Resolution 4 raises it in or before 2035), Delta T extrapolated. Emits `FUTURE_CIVIL_TIME_PROJECTED`. |

The expiry date is a pinned research value; it does not follow later IERS publications, and changing it is a reviewed code change.

`time_scale.sidereal_time_model` records that Swiss 2.10.03 switches its default sidereal-time model at 2050-01-01 0h UT (recorded step −1.908″; Lagna about −1.7″ at New Delhi) and says which side of the switch the chart is on (`before_switch` or `on_or_after_switch`, by UT instant). It is version-specific model behaviour, not a precision guarantee.

### Disclosures

| Code | When | Effect |
|---|---|---|
| `FUTURE_CIVIL_TIME_PROJECTED` | UTC instant on or after 2027-06-28T00:00:00Z | Descriptive only. |
| `HIGH_LATITUDE_TIME_SENSITIVITY` | \|latitude\| strictly above 60.0 (60.0 itself: none) | Descriptive only (SCI-01g); the ±66° band still decides acceptance. |

### Example

Synthetic request `{"birth_datetime":"2030-03-20T09:00:00+00:00","timezone":"UTC","latitude":62.0,"longitude":-18.0}` (chart fields abbreviated):

```json
{
  "schema_version": "0.2.0",
  "validation_status": "UNVERIFIED_GOLDEN_CHARTS",
  "method": {"ayanamsa": "Lahiri", "nodes": "mean", "houses": "whole_sign", "ephemeris": "Swiss Ephemeris, local .se1", "binding_version": "2.10.03"},
  "birth": {"utc": "2030-03-20T09:00:00Z", "timezone": "UTC", "latitude": 62.0, "longitude": -18.0},
  "lagna": {"longitude_deg": 54.46189408, "rashi": "Vrishabha", "navamsa_rashi": "Simha"},
  "moon_nakshatra": {"index": 12, "name": "Hasta", "pada": 2},
  "planets": {"...": "unchanged from 0.1.0"},
  "calculation_metadata": {
    "metadata_schema": "sabpuja-calculation-metadata/1",
    "conventions": {
      "zodiac": "sidereal",
      "ayanamsa": {"name": "Lahiri", "swiss_mode": "SIDM_LAHIRI", "swiss_mode_number": 1, "swiss_call": "set_sid_mode(SIDM_LAHIRI, 0, 0)", "kind": "true_ayanamsha", "definition": "Lahiri (Chitrapaksha), Swiss Ephemeris SE_SIDM_LAHIRI (mode 1), IAE 1985 definition, true ayanamsha, Swiss default precession; no SIDBIT options"},
      "planetary_positions": {"center": "geocentric", "position": "apparent", "frame": "true ecliptic and equinox of date, minus the true ayanamsha", "swiss_function": "calc_ut", "swiss_flags": ["FLG_SWIEPH", "FLG_SIDEREAL"], "swiss_flags_value": 65538, "swiss_bodies": ["SUN", "MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN", "MEAN_NODE"], "moshier_fallback": "refused"},
      "nodes": {"rahu": "mean", "rahu_swiss_body": "MEAN_NODE", "ketu": "exactly opposite the unrounded mean Rahu; categories from the exact sum Rahu + 180"},
      "houses": {"d1_model": "whole_sign", "rule": "house = ((rashi(body) - rashi(lagna)) mod 12) + 1"},
      "ascendant": {"definition": "eastern rising point of the ecliptic, minus the true Lahiri ayanamsha", "swiss_function": "houses_ex", "swiss_house_system": "W", "swiss_flags": ["FLG_SIDEREAL"], "swiss_flags_value": 65536, "value": "ascmc[0]", "note": "The house-system argument selects the Swiss call only; the D1 house model is whole_sign. Cusps are not used."},
      "swiss_state": {"reset_per_request_under_lock": ["set_ephe_path(verified directory)", "set_sid_mode(SIDM_LAHIRI, 0, 0)", "set_delta_t_userdef(DELTAT_AUTOMATIC)"]},
      "longitude_display": {"range": "[0, 360)", "decimals": 8, "note": "360 is shown as 0"},
      "classification": "Rashi, Navamsa, Nakshatra, Pada and houses use unrounded longitudes on half-open segments, never the 8-decimal display"
    },
    "swiss_ephemeris": {"library_version": "2.10.03", "python_binding": "pyswisseph", "python_binding_version": "2.10.3.2"},
    "ephemeris_data": {
      "source_repository": "https://github.com/aloistr/swisseph",
      "source_commit": "c69c14adb7a0f94829586ffd92cd422aacb21e86",
      "manifest_version": "1.0.0",
      "manifest_sha256": "1aaca24868bb9cde8558f891038ae239d8dce64beb77b90f963bb185e99b2e34",
      "manifest_sha256_method": "SHA-256 of the packaged ephemeris-manifest.json as canonical JSON (sorted keys, separators ',' and ':')",
      "required_files": [
        {"name": "sepl_18.se1", "size_bytes": 484061, "sha256": "ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66"},
        {"name": "semo_18.se1", "size_bytes": 1304771, "sha256": "1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7"}
      ],
      "verified_before_calculation": true,
      "verification": "every required file matched its size and SHA-256 before any Swiss call",
      "coverage_years": [1800, 2399]
    },
    "timezone_data": {"source": "PyPI tzdata", "package_version": "2026.5", "iana_version": "2026e", "manifest_sha256": "11e070e7a29c0c79a495d8bf9517215f0f1e6c8e7c92f3e75d8a485773953532", "host_timezone_database_used": false, "verification": "the zone file matched the pinned manifest SHA-256 before use"},
    "time_scale": {
      "pipeline": "local civil time + explicit offset -> validated against the pinned IANA zone -> civil UTC -> swe.julday (Gregorian) -> Swiss UT-based calculation; TT from the Swiss automatic Delta T",
      "ut1_assumption": "civil UTC is treated as UT1 (an assumption, not a measured UT1 correction)",
      "measured_ut1_minus_utc_used": false,
      "earth_orientation_data_used": false,
      "delta_t": {"source": "Swiss Ephemeris automatic Delta T (DELTAT_AUTOMATIC, reset per request)", "user_override_used": false, "measured_series_used": false, "note": "Swiss 2.10.03 tabulates Delta T to 2028 and extrapolates afterwards; future Delta T is a model projection"},
      "era": "AFTER_LEAP_SECOND_LIST_EXPIRY",
      "era_basis": "converted UTC instant",
      "era_description": "After the pinned IERS leap-second list expiry: future leap seconds and UT1-UTC are not known. The converted UTC is treated as UT1 by projection; no |UT1-UTC| bound is promised (CGPM 2022 Resolution 4 raises the 0.9 s limit in or before 2035), and Swiss Delta T is extrapolated.",
      "leap_second_list_expiry_utc": "2027-06-28T00:00:00Z",
      "leap_second_list_source": "IERS leap-seconds.list as shipped in tz 2026e (pinned research value; later IERS publications are not reflected)",
      "sidereal_time_model": {"switch_ut": "2050-01-01T00:00:00Z", "recorded_step_arcsec": -1.908, "chart_side": "before_switch", "note": "Swiss 2.10.03 switches its default sidereal-time model at 2050-01-01 0h UT (recorded step about -1.908 arcsec, Lagna about -1.7 arcsec at New Delhi). Version-specific model behaviour, not a precision guarantee."}
    },
    "input_policy": {
      "local_date_window": {"first": "1900-01-01", "last": "2100-12-31", "basis": "local civil date as written, before conversion"},
      "historical_clock": {"policy": "SCI-03 RG-HIST Option B, version 1", "mode": "fail_closed", "refused_local_dates": [{"zone": "*", "first_local_date": null, "last_local_date": "1969-12-31"}], "exceptions": []},
      "latitude_band_deg": {"min": -66.0, "max": 66.0, "inclusive": true},
      "time_offset": "explicit UTC offset required and must be an offset the pinned IANA zone gives for that wall time; nonexistent local times are refused; a repeated hour is resolved by the offset",
      "refusal_order": "fixed P5 order (docs/api-contract.md)"
    },
    "disclosures": [
      {"code": "FUTURE_CIVIL_TIME_PROJECTED", "description": "The birth instant is after the pinned IERS leap-second list expiry (2027-06-28): civil-time rules, leap seconds, UT1-UTC and Delta T are projections, not records."},
      {"code": "HIGH_LATITUDE_TIME_SENSITIVITY", "description": "Absolute latitude above 60 deg: the Lagna moves faster per second of birth time, so birth-time error has a larger effect. Descriptive only; the chart is computed the same way."}
    ],
    "validation": {"status": "UNVERIFIED_GOLDEN_CHARTS", "claim_boundary": "Swiss-on-Swiss integration conformance only; not independent astronomical validation, mathematical verification or historical clock verification"}
  }
}
```

### Limitations and claim boundary

- The metadata reports what the engine did and which pinned data it used. It is not evidence that the chart is astronomically correct, and it is not independent validation, mathematical verification or historical clock verification.
- UT1 is not measured; Delta T after 2028 and UT1 − UTC after 2027-06-28 are model projections.
- The ±66° band, the 1900–2100 window and the pre-1970 refusal are support policy, not astronomical limits. The high-latitude disclosure is descriptive only.
- Per-zone TZif hashes are not listed; the manifest SHA-256 covers them.

### Migration from 0.1.0

- All 0.1.0 keys, values and their order are unchanged; `method` keeps its five keys. `schema_version` becomes `"0.2.0"` and `calculation_metadata` is appended last.
- A 0.1.0 consumer that ignores unknown keys keeps working once it accepts `"0.2.0"`. A consumer that pins `"0.1.0"` must be updated.
- `provenance.legacy_projection(chart)` drops `calculation_metadata` and restores `"0.1.0"`. For every request it equals the KUN-03 conformance engine output (PR #33, `bec4641`) byte for byte under canonical JSON; `tests/test_calculation_metadata.py` pins this for ten synthetic boundary requests.

### Reproduction requirements

To get the same output, including the metadata: `pyswisseph==2.10.3.2` (Swiss 2.10.03), `tzdata==2026.5` (IANA 2026e) with the packaged TZif manifest, and the two ephemeris files matching the packaged ephemeris manifest. A different binding, tzdata or ephemeris file either fails closed (`TZDATA_*`, `EPHEMERIS_*`) or is reported in the metadata.

**Privacy**: CLI retains no state; stdout contains sensitive birth timestamp/coordinates and must be protected by the caller. Never send customer content to telemetry or GitHub.
