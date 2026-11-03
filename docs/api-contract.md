# Calculation request/output contract, schema v0.2.0 (canonical baseline) and v0.3.0 (PROPOSED, Gate 3E)

> **Gate 3E (draft, unmerged):** the engine on this branch emits the **proposed** schema `0.3.0`,
> which adds D9 whole-sign house fields (see "Proposed schema 0.3.0" below). `0.3.0` is a candidate
> pending independent QA and a separate owner decision; it is **not canonical**. The owner-approved
> engineering baseline remains `0.2.0` (SCI-02, ledger row 9), recovered exactly by
> `provenance.baseline_projection`.

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
- `timezone` is the IANA timezone identifier of the birthplace; conversion must match the offset, including DST/historical rules. It must name a place: `UTC`, `GMT`, every `Etc/*` key, their aliases, `Factory` and the US-rules zones `CST6CDT`, `EST5EDT`, `MST7MDT` and `PST8PDT` are refused with `TIMEZONE_NOT_LOCATION_BASED` (KUN-03 D3, zone policy version 2, see "Birthplace timezone policy" below).
- Timezone rules come only from the pinned PyPI `tzdata==2026.5` (IANA 2026e), each TZif file verified against `src/sabpuja_kundali/tzif-manifest.json`; the host's system zoneinfo, `PYTHONTZPATH` and `TZ` are never used. A key not in the manifest is invalid input. Missing, mismatched or wrong-version timezone data fails closed with a `TZDATA_*` code (no host fallback).
- Supported birth dates (SCI-03 initial window): the **local civil date** as written in `birth_datetime` must be 1900-01-01 to 2100-12-31 inclusive. It is checked before conversion (after the timezone is recognised and before the offset is matched), so the UTC instant may be as early as 1899-12-31T11:40:48Z (local 1900-01-01T00:00:00 at UTC+12:19:12, `Pacific/Tongatapu` local mean time) or as late as 2101-01-01T10:59:59.999999Z (local 2100-12-31T23:59:59.999999 at UTC−11, for example `Pacific/Pago_Pago`; microsecond precision is accepted). Before KUN-03 D3 the extremes were 1899-12-31T10:00:00Z and 2101-01-01T11:59:59.999999Z, reachable only through `Etc/GMT-14` and `Etc/GMT+12`, which D3 refuses; the window rule itself is unchanged. A date outside is refused with `DATE_OUTSIDE_SUPPORTED_RANGE` (`UnsupportedInputError`, a `ValueError` subclass carrying `.code`). Within the window, the historical-clock gate below then refuses every local date before 1970-01-01, so the earliest instant actually charted today is 1969-12-31T11:00:00Z (local 1970-01-01T00:00:00 at UTC+13, `Pacific/Tongatapu` or `Asia/Anadyr`; 1969-12-31T10:00:00Z through `Etc/GMT-14` before D3).
- Historical clocks (SCI-03 RG-HIST Option B, KUN-03 P8): no birthplace clock before 1970 is verified, so a birth whose **local civil date** is before 1970-01-01 is refused with `HISTORICAL_CLOCK_UNVERIFIED` (`UnsupportedInputError`) in **every** recognised zone (`UTC`, `GMT` and `Etc/*` are refused earlier by D3). It is judged on the date as written, never the UTC date, after all other time checks and before the coordinates. The detail text is fixed and repeats nothing from the request. The rule is the versioned table `HISTORICAL_CLOCK_GATE` in `engine.py` ("SCI-03 RG-HIST Option B, version 1"; owner records on PR #20, comments 6336254894 and 6350086727):

  | Zone | Refused local dates | Policy |
  |---|---|---|
  | every recognised zone | up to and including 1969-12-31 | refuse: `HISTORICAL_CLOCK_UNVERIFIED` |

  Verified exceptions (`HISTORICAL_CLOCK_EXCEPTIONS`: zone, first and last local date) are empty. Each one needs DATA-01 evidence, QA and its own owner approval; a wildcard exception is ignored. There is no runtime, CLI or environment switch for the gate.
- Latitude decimal north-positive, longitude east-positive. Both must be JSON numbers (not booleans or strings), finite (no `NaN`/`Infinity`, no integers too large for a float) and within the accepted range: latitude -66.0 to 66.0 inclusive (SCI-01g supported band, the same for every date), longitude -180 to 180 inclusive. A finite latitude outside the band is refused with `LATITUDE_OUTSIDE_SUPPORTED_BAND` before any Swiss call; non-numbers and non-finite values are refused first with `COORDINATE_INVALID`.
- No name, email, phone, address, account ID or other identifying attributes in the calculation request.
- A birthplace autocomplete service is future work and must be offline/self-hosted.

Success returns JSON `schema_version` (`"0.3.0"` proposed on this branch; `"0.2.0"` baseline), `validation_status`, `method`, `birth`, `lagna`, `moon_nakshatra`, `planets`, `calculation_metadata` (KUN-03 P7, see below) and, in proposed 0.3.0 only, `d9`. Planet values contain longitude, Rashi, D9 sign and whole-sign house, and in proposed 0.3.0 also the D9 whole-sign house. Output is not yet independently verified.

Longitude and category semantics:
- Rashi (30°), Nakshatra (40/3°) and Pada/D9 (10/3°) segments are half-open, `[start, end)`. Every category, house, Moon Nakshatra and Ketu (exactly opposite Rahu) is derived from the unrounded Swiss Ephemeris value with exact arithmetic, never from the displayed number.
- `longitude_deg` is display only: the value normalized to `[0, 360)` and rounded to 8 decimals. A rounding that reaches 360 is shown as `0.0`; `360.0` is never emitted.
- Near-boundary display ambiguity: within 5e-9° below a boundary, the displayed value can equal the boundary while the category is the segment before it (raw 29.999999996 is shown as `30.0` and stays Mesha; raw 359.999999996 is shown as `0.0` and stays Meena). Do not re-derive categories from `longitude_deg`; use the category fields.

Errors: CLI writes JSON `{"error":"CODE: detail"}` to stderr, writes nothing to stdout, prints no traceback and exits 2. Error text never repeats the birth time, timezone or coordinates. No HTTP response codes are promised yet. Network service contracts must be separately reviewed and versioned.

Only the typed engine errors are reported this way: `InputRefusalError` (and `UnsupportedInputError`), `ChartComputationError`, `EphemerisDataError` and `TimezoneDataError`, listed together as `engine.EXPECTED_ERRORS`. Each carries `.code` and fixed text. Any other exception, including an untyped `ValueError` or `RuntimeError`, is a programming defect: it is not relabelled as a refusal and ends the CLI with Python's own failure (exit 1, no stdout). Before Gate 3C the CLI also printed an untyped `ValueError` or `RuntimeError` as an exit-2 `{"error"}`; no accepted or refused request reached that path (Gate 3C invariance corpus).

Input refusal codes (KUN-03 P5, D1/D4). Every input refusal raises `InputRefusalError` (a `ValueError` carrying `.code`; `UnsupportedInputError` is its subclass for valid input outside the supported envelope). Checks run in this fixed order and the first failing check decides the code, so one input always gets the same code; every birth-time check comes before any coordinate check:

| Order | Code | Refused when | Class |
|---|---|---|---|
| 1 | `REQUEST_INVALID` | not one JSON object, over 4,096 bytes (counted before UTF-8 decoding), not UTF-8, wrong keys, or `birth_datetime`/`timezone` not strings | `InputRefusalError` |
| 2 | `TIME_FORMAT_INVALID` | outside the strict profile, including hour > 23, minute > 59, second > 60, offset hour > 23 or offset minute/second > 59 | `InputRefusalError` |
| 3 | `TIME_OFFSET_REQUIRED` | a profile-conforming local time with no offset | `InputRefusalError` |
| 4 | `TIME_LEAP_SECOND_UNSUPPORTED` | seconds field `60` | `UnsupportedInputError` |
| 5 | `DATE_INVALID` | the calendar date does not exist (for example 1900-02-29, 2100-02-29, month 13, year 0000) | `InputRefusalError` |
| 6 | `TIMEZONE_INVALID` | not a key in the pinned TZif manifest (P1) | `InputRefusalError` |
| 7 | `TIMEZONE_NOT_LOCATION_BASED` | a recognised, verified key that names no place: `UTC`, `UCT`, `Universal`, `Zulu`, `GMT`, `GMT+0`, `GMT-0`, `GMT0`, `Greenwich`, `Factory`, `CST6CDT`, `EST5EDT`, `MST7MDT`, `PST8PDT` or any `Etc/*` key (KUN-03 D3, zone policy version 2) | `InputRefusalError` |
| 8 | `DATE_OUTSIDE_SUPPORTED_RANGE` | local civil date outside 1900-01-01 to 2100-12-31 (SCI-03, P4) | `UnsupportedInputError` |
| 9 | `TIME_NONEXISTENT_LOCAL` | the wall time does not exist in the zone (DST or historical gap), whatever the offset | `InputRefusalError` |
| 10 | `TIME_OFFSET_MISMATCH` | the wall time exists but the offset is not one IANA gives for it (one offset normally, two in a fold) | `InputRefusalError` |
| 11 | `HISTORICAL_CLOCK_UNVERIFIED` | local civil date before 1970-01-01 in any zone, unless a verified exception covers it (none yet; SCI-03 RG-HIST Option B, P8) | `UnsupportedInputError` |
| 12 | `COORDINATE_INVALID` | latitude or longitude not a JSON number (booleans and strings included), not finite, or longitude outside -180 to 180 | `InputRefusalError` |
| 13 | `LATITUDE_OUTSIDE_SUPPORTED_BAND` | finite latitude outside -66.0 to 66.0 (SCI-01g, P2) | `UnsupportedInputError` |

Timezone-data failures are server faults, not input refusals: when the pinned data is missing, of the wrong version or fails its SHA-256 check, loading the zone at step 6 raises a `TZDATA_*` `RuntimeError` (`TimezoneDataError`, carrying `.code`) instead of `TIMEZONE_INVALID`, also for a key D3 would refuse. Steps 7–13 and Swiss are then never reached, and nothing falls back to the host zoneinfo. A fold (repeated hour) is not refused: the given offset selects the instant. Gaps and offsets are judged from IANA data only; no offset is ever inferred. `EPHEMERIS_*`, `ASCENDANT_UNCOMPUTABLE` and other `RuntimeError`s come after these checks and are unchanged.

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

These are server-side calculation failures, not input refusals: they are never reported as `REQUEST_INVALID` or another P5 code, and they are reachable only after every refusal, `TZDATA_*` and `EPHEMERIS_*` check, whose codes and order are unchanged. None is expected for accepted input; in the pinned binding only `calc_ut` and `houses_ex` were seen to raise `swisseph.Error`, and the reset calls are guarded defensively. Only `swisseph.Error` is translated: any other exception is a programming defect, is not relabelled or swallowed, and ends the CLI with Python's own failure (exit 1, no stdout). This contract covers error handling only; it is not an astronomical certification.

Swiss runtime faults (Gate 3C, PKG-2). Two refusals that were uncoded `RuntimeError`s before Gate 3C, and the run-time version pins, are `ChartComputationError`s with fixed text (no version string, path, Swiss text or request value):

| Stage | Code | Fixed detail |
|---|---|---|
| `import swisseph` (after the ephemeris gate) | `SWISS_BINDING_MISSING` | the pinned Swiss Ephemeris Python binding is not installed; no chart produced |
| `swe.version` is not exactly `2.10.03` (missing, malformed, older or newer) | `SWISS_LIBRARY_VERSION_MISMATCH` | the Swiss Ephemeris library is not the pinned version; no chart produced |
| no `pyswisseph` distribution metadata, or no usable `Version` field | `SWISS_BINDING_METADATA_MISSING` | the Swiss Ephemeris binding version cannot be verified; no chart produced |
| `pyswisseph` distribution version is not exactly `2.10.3.2` | `SWISS_BINDING_VERSION_MISMATCH` | the Swiss Ephemeris binding is not the pinned version; no chart produced |
| `calc_ut` returned without `FLG_SWIEPH` for any body (Moshier or other fallback) | `SWISS_EPHEMERIS_FALLBACK_REFUSED` | Swiss Ephemeris did not use the verified local files; refused Moshier fallback; no chart produced |

The binding and version checks (`engine.swiss_runtime()`) run on every request after every input refusal and the `EPHEMERIS_*` gate, in the order above, and before `julday`: a version failure makes no Swiss call and takes no lock. The pins are exact string matches with no range, environment switch or bypass, and nothing is installed or downloaded. Unavailable metadata is a refusal, never evidence of compatibility. The binding's distribution version is read once per process (`provenance.binding_distribution_version`, cached), the library version on every request. The fallback refusal stops at the first body whose result lacks `FLG_SWIEPH`: no later body, no ascendant, no substitute value and no partial chart. Its text keeps the phrase "refused Moshier fallback"; before Gate 3C it was `RuntimeError("Swiss ephemeris files unavailable: refused Moshier fallback")`. A missing binding was `RuntimeError("Install pinned local pyswisseph package")` and a version mismatch was not refused (only reported in the metadata). The packaged ephemeris manifest is refused with the existing `EPHEMERIS_MANIFEST_INVALID` if it is unreadable, is not a JSON object with a `files` list, or has a field the gate or the calculation metadata reads in the wrong shape: every `files` entry must be an object with a boolean `required`; a required entry needs a plain file `name` (no `/`, `\` or NUL, not `.` or `..`), a non-negative integer `size_bytes` and a 64-character lowercase hex `sha256`; and `manifest_version`, `source.repository` and `source.commit` must be strings and `coverage.start_year` and `coverage.end_year` integers. Before Gate 3C these were a JSON decoder message, or an `AttributeError`, `KeyError` or `TypeError` traceback. The text is fixed (`ephemeris manifest has an unexpected structure`) and never echoes a manifest value. The check runs at the same point as before, so the refusal order is unchanged, and the packaged manifest bytes are unchanged.

Start-up preflight (Gate 3C, `readiness.py`). A future service must call `readiness.require_ready()` (or `readiness.preflight()`) before it opens a listener or accepts a request; see [engine-readiness.md](engine-readiness.md).

## Birthplace timezone policy (KUN-03 D3)

**Rule.** `timezone` must be a geographic IANA identifier: a key that names a place, whose rules record that place's civil clock. A recognised, verified key that names no place is refused with `TIMEZONE_NOT_LOCATION_BASED` (`InputRefusalError`, a `ValueError` carrying `.code`; not `UnsupportedInputError`), fixed text `TIMEZONE_NOT_LOCATION_BASED: birthplace timezone must be a geographic IANA timezone identifier`. Through the CLI it is the single line `{"error": "TIMEZONE_NOT_LOCATION_BASED: birthplace timezone must be a geographic IANA timezone identifier"}` on stderr, empty stdout, exit 2, no traceback; the key and every other request value are never repeated. It is never reported as `TIMEZONE_INVALID`, which stays the code for a key outside the pinned manifest. The policy is the versioned table in `src/sabpuja_kundali/zone_policy.py`, now "KUN-03 D3 location-based birthplace timezone, version 2" (D3 authorized on PR #20, comment 6373261419; version 2 is the owner's Option B, PR #20 comment 6377855934). There is no runtime, CLI or environment switch, and no UTC fallback, offset substitution or zone inference.

**Order.** Step 7 of the fixed order: after the syntax checks (1–5), `TIMEZONE_INVALID` (6) and any `TZDATA_*` fault while loading the zone, and before the window (8), gap (9), offset (10), historical clock (11) and coordinate (12–13) checks. A D3 refusal reaches neither the ephemeris check nor any Swiss call. A request that would also fail a later check (for example `UTC` with a 1950 date, an offset mismatch or latitude 70) gets `TIMEZONE_NOT_LOCATION_BASED`; the same fields on a geographic zone still get the later code.

**Refused identifiers (49 of the 598 manifest keys; 45 in version 1).** Classified by exact, case-sensitive name from the IANA tz 2026e source files that define them (tz git tag `2026e`, commit `039ef27cc5f062a2055cb67435d6d71adbefd27d`), never by offset or TZif bytes:

| Identifier | In manifest | IANA meaning / source | Class | Action | Compatibility impact |
|---|---|---|---|---|---|
| `Etc/UTC`, `Etc/GMT` | yes | `etcetera`: Zone definitions of UTC and GMT, "ships at sea and other miscellany" | non-geographic | refuse | requests using them, accepted before, now refused |
| `Etc/GMT+1` … `Etc/GMT+12`, `Etc/GMT-1` … `Etc/GMT-14` (26) | yes | `etcetera`: fixed offsets with POSIX-inverted signs (`Etc/GMT-5` is UTC+05:00) | non-geographic | refuse | as above |
| `Etc/GMT+0`, `Etc/GMT-0`, `Etc/GMT0`, `Etc/Greenwich` | yes | `backward`: links to `Etc/GMT` | non-geographic | refuse | as above |
| `Etc/UCT`, `Etc/Universal`, `Etc/Zulu` | yes | `backward`: links to `Etc/UTC` | non-geographic | refuse | as above |
| `UTC`, `UCT`, `Universal`, `Zulu` | yes | `backward`: links to `Etc/UTC` | non-geographic | refuse | as above; `UTC` was the most common key in earlier fixtures |
| `GMT` | yes | `etcetera`: link to `Etc/GMT` | non-geographic | refuse | as above |
| `GMT+0`, `GMT-0`, `GMT0`, `Greenwich` | yes | `backward`: links to `Etc/GMT` | non-geographic | refuse | as above |
| `Factory` | yes | `factory`: `Zone Factory 0 - -00`, "the actual time zone is unknown" | non-geographic | refuse (audited inclusion beyond UTC/GMT/Etc) | as above |
| `CST6CDT`, `EST5EDT`, `MST7MDT`, `PST8PDT` | yes | `backward`: `Zone CST6CDT -6:00 USback C%sT` (and `EST5EDT`, `MST7MDT`, `PST8PDT` likewise), a fixed standard offset with ahistorical US rules; `theory.html` lists them with the `Etc` names as legacy names "incompatible with the first guideline of location names" | non-geographic (US rules, no place) | refuse **since version 2** (owner Option B) | accepted by version 1; refused from version 2 |

**What stays accepted (549 keys; 553 in version 1).** Every other manifest key, including zones with a zero offset (`Africa/Abidjan`, `Atlantic/Reykjavik`, `Europe/London` in winter), legacy and backward-compatible spellings (`Asia/Calcutta`, `Iceland`, `GB`, `US/Eastern`, `Japan` and the other `backward` links to geographic zones), zones with local mean time history (`Asia/Kolkata`), zones whose TZif bytes equal another zone's, and zones with no current DST. tz 2026e `theory.html` names the `etcetera` names and the `backward` names `Etc/GMT0`, `Etc/GMT-0`, `Etc/GMT+0`, `GMT0`, `GMT-0`, `GMT+0` as legacy names "incompatible with the first guideline of location names"; `zone1970.tab` lists the geographic locations.

**Reviewed by the owner and kept accepted (version 2).** These seven names are abbreviation-style rather than location names, but tz 2026e defines each as a link to one geographic zone, so the owner's Option B keeps them accepted:

| Identifier | IANA source (2026e) | Note |
|---|---|---|
| `CET`, `MET` | `backward`: links to `Europe/Brussels` | `theory.html`: "old-fashioned names" from the older naming scheme, like `US/Eastern`; the rules are one place's |
| `EET` | `backward`: link to `Europe/Athens` | |
| `WET` | `backward`: link to `Europe/Lisbon` | |
| `EST` | `backward`: link to `America/Panama` | fixed −05:00 today |
| `MST` | `backward`: link to `America/Phoenix` | fixed −07:00 today |
| `HST` | `backward`: link to `Pacific/Honolulu` | fixed −10:00 today |

**Version 1 to version 2.** Version 1 (45 refused, 553 accepted; ChatGPT engineering QA PASS at `8b6507b`) left eleven abbreviation-style names accepted pending an owner decision. Version 2 refuses exactly the four US-rules zones and keeps the seven above; nothing else changes (same exact, case-sensitive match, same `Etc/` prefix, same step 7, same code and text). Callers that sent `CST6CDT`, `EST5EDT`, `MST7MDT` or `PST8PDT` now get `TIMEZONE_NOT_LOCATION_BASED` and should send the birthplace's geographic zone (for example `America/Chicago`, `America/New_York`, `America/Denver`, `America/Los_Angeles`); no other request changes outcome. Any further identifier needs a new owner decision.

**Zone and coordinates are not cross-validated.** D3 judges the identifier only. `Asia/Kolkata` with New York coordinates is still accepted (KUN-02 T63), a `+00:00` geographic zone can be used for any coordinates, and no zone is ever looked up or inferred from latitude and longitude. A birthplace gazetteer or coordinate-to-zone lookup (DATA-01) is future work and is not authorized by D3.

**Calculation metadata (P7).** Successful charts now carry `input_policy.timezone_identifier` (`policy`, `mode` `"fail_closed"`, `rule`, `refused_identifiers`, `refused_prefixes`, `zone_matches_coordinates_verified` `false`), read from `zone_policy.py`. Because this is a new key, `metadata_schema` became `"sabpuja-calculation-metadata/2"` (now `/3`, see "Time scale and eras"); `schema_version` stays `"0.2.0"` and no other chart or metadata value changes. Version 2 changes only the values of `policy` (now "…version 2") and `refused_identifiers` (four more names); the shape, and so `metadata_schema` `/2`, is unchanged. `provenance.legacy_projection` drops the whole metadata block, so 0.1.0 output of an accepted request is unchanged.

**Fixture reconciliation.** Frozen fixtures are not edited. KUN-02 T56 (`Etc/GMT-5`) and T57 (`UTC`) were versioned to the proposed `TIMEZONE_NOT_LOCATION_BASED`; their instants are checked on `Asia/Karachi` and `Africa/Abidjan`. Of the ten P7 legacy golden requests, seven use `UTC`: their PR #33 golden (`be619e62…`) is still reproduced with a test-only D3 bypass, and the same instants and coordinates on geographic zones have their own PR #33 golden (`8c790777…`). The Swiss conformance cases keep `spec.json`, `cases.json` and profile v1 byte-identical. The active D3 profile is `tests/swiss_conformance/profiles/kun03-d3-v2.json` (SHA-256 `a9aa1a4b…e5e7`, zone policy version 2, run with `python -m tests.swiss_conformance.run_d3`); the D3 profile v1 `kun03-d3-v1.json` (SHA-256 `942a0eac…b980`, zone policy version 1) is kept byte-identical as the archived record, and v2 must equal it in every case, count, continuation and divergence field (no frozen request uses the four US-rules names), with the v1-to-v2 policy delta in its `lineage` block. The runner also reproduces the archived v1 policy in a test-only, versioned context (engine outcomes only). The profiles record all 24 cases with their v1 and D3 outcomes (7 charts, 17 refusals: nine former UTC charts and six former refusals now stop at D3). All 784 v1 comparison checks still run: 343 on the seven D3 charts, 147 on geographic equivalents of SC-01, SC-04 and SC-24 in production (each proven equal to its original request), and 294 on SC-11, SC-14, SC-15, SC-16, SC-19 and SC-20 with a test-only D3 bypass (no geographic equivalent: local 2101 in Tokyo, or open ocean). The unchanged v1 and archival PR #18 runners must diverge from the D3 engine exactly as recorded in the profile.

**Limits.** The table is tied to the pinned tz 2026e manifest; a tzdata update is a reviewed change that must re-audit new names (`Etc/*` is refused by prefix, a new root-level non-location name needs a code change). Classification is by name and does not certify that a geographic zone's historical rules are right for a birthplace (see the historical clock gate), and it is not geolocation.

## Calculation metadata (schema 0.2.0, KUN-03 P7)

Every successful chart carries `calculation_metadata` (`metadata_schema` `"sabpuja-calculation-metadata/3"` since KUN-03 P7 Option 2, which changed the `time_scale.era` values and meanings; `/2` from KUN-03 D3; `/1` before it, without `input_policy.timezone_identifier`), built by `src/sabpuja_kundali/provenance.py`. It is **descriptive**: it states the conventions, data and time-scale assumptions that produced the chart. It does not change any position, category, refusal or code, and it adopts no decision-register entry (SCI-01a, SCI-01h and the others stay as recorded there).

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
| `input_policy` | The checks this chart passed, read from the engine constants: local date window, historical clock policy (RG-HIST Option B v1, fail closed, refused local dates, exceptions: none), latitude band ±66° inclusive, timezone identifier policy (D3 zone policy version 2: refused identifiers and prefixes; zone and coordinates not cross-validated), offset rule and the fixed refusal order. |
| `disclosures` | Zero or more `{code, description}` in fixed order (below). |
| `validation` | `status` (equal to `validation_status`) and the claim boundary. |

### Time scale and eras

The pipeline is: local civil time with an explicit offset, validated against the pinned IANA zone, converted to civil UTC, then `swe.julday` (Gregorian) and Swiss UT-based calculation. **Civil UTC is treated as UT1.** This is an assumption: no measured UT1 − UTC and no Earth-orientation data are used. TT comes from Swiss's automatic Delta T (`DELTAT_AUTOMATIC`, reset per request; tabulated to 2028 and extrapolated after; no user override and no measured series).

`time_scale.era` is judged on the **converted UTC instant**, not the local date (local `1972-01-01T05:00+05:30` is UTC 1971 and is labelled `UTC_BEFORE_LEAP_SECONDS`). Ranges are half-open, start inclusive:

| Era | UTC range | Disclosure |
|---|---|---|
| `CIVIL_TIME_BEFORE_UTC` | before 1961-01-01 | Reachable only through the test-only historical clock override; production refuses these dates. |
| `UTC_BEFORE_LEAP_SECONDS` | 1961-01-01 to 1972-01-01 | Accepted charts here are 1969-12-31 to 1971-12-31 UTC. UT1 − UTC not sourced: an approximation, not verified UT1. |
| `LEAP_SECOND_UTC` | 1972-01-01 to 2027-05-20 | Leap-second UTC (UTC dates up to 2027-05-19). In this regime the IERS rule keeps \|UT1 − UTC\| < 0.9 s; that bound is implied under the Swiss Delta T model, not measured for this calculation. |
| `CONTINUOUS_UTC_TRANSITION_DATE` | 2027-05-20 to 2027-05-21 | The UTC date 2027-05-20, on which [BIPM 28th CGPM (2026) Resolution 5](https://www.bipm.org/en/cgpm-2026/resolution-5) makes continuous UTC effective. The official effective hour and its time scale are not stated in the reviewed primary sources, so no claim is made that the 0.9 s rule has ended or still applies at any particular time on this date. |
| `CONTINUOUS_UTC_AFTER_TRANSITION_DATE` | 2027-05-21 to 2027-06-28 | Continuous UTC under Resolution 5, no leap seconds. Resolution 5 permits \|UT1 − UTC\| up to 3 600 s: a policy ceiling, not a measured UT1 − UTC or an engine error. |
| `AFTER_LEAP_SECOND_LIST_EXPIRY` | from 2027-06-28 | After the pinned IERS leap-second list expiry (tz 2026e `leap-seconds.list`): continuous UTC under Resolution 5 (3 600 s policy ceiling, not a measured value), UT1 − UTC unknown, converted UTC treated as UT1 by projection, Delta T extrapolated. Emits `FUTURE_CIVIL_TIME_PROJECTED`. |

The expiry date is a pinned research value; it does not follow later IERS publications, and changing it is a reviewed code change.

**Date-granular transition (KUN-03 P7, owner Option 2, PR #20 comments 6381685709 and 6381922281).** Resolution 5 gives the effective date, 20 May 2027, but the reviewed primary sources (BIPM Resolution 5, CIPM decision 115-5, the CCTF report on Draft Resolution C, IERS Bulletin C 72) give no hour or time scale. The engine therefore groups by **UTC calendar date**: the 2027-05-20 and 2027-05-21 boundaries at 00:00 UTC are a reporting convention, **not** the official effective instant, and may be adjusted by a reviewed code change once an official instant is published. The date is that of the converted UTC instant, not the local date: local `2027-05-20T05:29:59+05:30` is UTC 2027-05-19 and is `LEAP_SECOND_UTC`; local `2027-05-20T05:30:00+05:30` is UTC 2027-05-20 00:00 and is `CONTINUOUS_UTC_TRANSITION_DATE`. No calculation reads the era: positions, Delta T and every chart number are the same on both sides of each boundary.

**Compatibility.** KUN-03 P7 Option 2 added the two `CONTINUOUS_UTC_*` values and moved the end of `LEAP_SECOND_UTC` from 2027-06-28 to 2027-05-20, so a chart dated 2027-05-20 to 2027-06-27 UTC now reports one of the new values, and the `era_description` text of `LEAP_SECOND_UTC` and `AFTER_LEAP_SECOND_LIST_EXPIRY` changed. Keys and value types are unchanged; because the meaning of `era` values changed, `metadata_schema` is `"sabpuja-calculation-metadata/3"` (chart `schema_version` stays `"0.2.0"`). A consumer that accepts only the earlier four `era` values, or that keys on `era_description` text, must be updated; treat `era` as an open set of strings.

`time_scale.sidereal_time_model` records that Swiss 2.10.03 switches its default sidereal-time model at 2050-01-01 0h UT (recorded step −1.908″; Lagna about −1.7″ at New Delhi) and says which side of the switch the chart is on (`before_switch` or `on_or_after_switch`, by UT instant). It is version-specific model behaviour, not a precision guarantee.

### Disclosures

| Code | When | Effect |
|---|---|---|
| `FUTURE_CIVIL_TIME_PROJECTED` | UTC instant on or after 2027-06-28T00:00:00Z | Descriptive only. |
| `HIGH_LATITUDE_TIME_SENSITIVITY` | \|latitude\| strictly above 60.0 (60.0 itself: none) | Descriptive only (SCI-01g); the ±66° band still decides acceptance. Ascendant sensitivity to birth-time uncertainty can be greater at high latitude for some dates and sidereal times, but not at all of them (for example at 0° E on 2024-06-15 it moves 0.0188°/s at 62° N vs 0.0045°/s at the equator at 00:00 UT, but 0.0025°/s vs 0.0038°/s at 06:00 UT), so the text makes no uniform claim. |

### Example

Synthetic request `{"birth_datetime":"2030-03-20T09:00:00+00:00","timezone":"Atlantic/Reykjavik","latitude":62.0,"longitude":-18.0}` (chart fields abbreviated):

```json
{
  "schema_version": "0.2.0",
  "validation_status": "UNVERIFIED_GOLDEN_CHARTS",
  "method": {"ayanamsa": "Lahiri", "nodes": "mean", "houses": "whole_sign", "ephemeris": "Swiss Ephemeris, local .se1", "binding_version": "2.10.03"},
  "birth": {"utc": "2030-03-20T09:00:00Z", "timezone": "Atlantic/Reykjavik", "latitude": 62.0, "longitude": -18.0},
  "lagna": {"longitude_deg": 54.46189408, "rashi": "Vrishabha", "navamsa_rashi": "Simha"},
  "moon_nakshatra": {"index": 12, "name": "Hasta", "pada": 2},
  "planets": {"...": "unchanged from 0.1.0"},
  "calculation_metadata": {
    "metadata_schema": "sabpuja-calculation-metadata/3",
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
      "era_description": "After the pinned IERS leap-second list expiry (2027-06-28): continuous UTC under BIPM CGPM 2026 Resolution 5, whose 3 600 s maximum for |UT1-UTC| is a policy ceiling, not a measured value. Civil-time rules and UT1-UTC are not known; the converted UTC is treated as UT1 by projection, and Swiss Delta T is extrapolated.",
      "leap_second_list_expiry_utc": "2027-06-28T00:00:00Z",
      "leap_second_list_source": "IERS leap-seconds.list as shipped in tz 2026e (pinned research value; later IERS publications are not reflected)",
      "sidereal_time_model": {"switch_ut": "2050-01-01T00:00:00Z", "recorded_step_arcsec": -1.908, "chart_side": "before_switch", "note": "Swiss 2.10.03 switches its default sidereal-time model at 2050-01-01 0h UT (recorded step about -1.908 arcsec, Lagna about -1.7 arcsec at New Delhi). Version-specific model behaviour, not a precision guarantee."}
    },
    "input_policy": {
      "local_date_window": {"first": "1900-01-01", "last": "2100-12-31", "basis": "local civil date as written, before conversion"},
      "historical_clock": {"policy": "SCI-03 RG-HIST Option B, version 1", "mode": "fail_closed", "refused_local_dates": [{"zone": "*", "first_local_date": null, "last_local_date": "1969-12-31"}], "exceptions": []},
      "latitude_band_deg": {"min": -66.0, "max": 66.0, "inclusive": true},
      "timezone_identifier": {"policy": "KUN-03 D3 location-based birthplace timezone, version 2", "mode": "fail_closed", "rule": "geographic IANA timezone identifier required (exact match)", "refused_identifiers": ["UTC", "UCT", "Universal", "Zulu", "GMT", "GMT+0", "GMT-0", "GMT0", "Greenwich", "Factory", "CST6CDT", "EST5EDT", "MST7MDT", "PST8PDT"], "refused_prefixes": ["Etc/"], "zone_matches_coordinates_verified": false},
      "time_offset": "explicit UTC offset required and must be an offset the pinned IANA zone gives for that wall time; nonexistent local times are refused; a repeated hour is resolved by the offset",
      "refusal_order": "fixed P5 order (docs/api-contract.md)"
    },
    "disclosures": [
      {"code": "FUTURE_CIVIL_TIME_PROJECTED", "description": "The birth instant is after the pinned IERS leap-second list expiry (2027-06-28): civil-time rules, leap seconds, UT1-UTC and Delta T are projections, not records."},
      {"code": "HIGH_LATITUDE_TIME_SENSITIVITY", "description": "Absolute latitude above 60 deg: ascendant sensitivity to birth-time uncertainty can be greater for some dates and sidereal times, but is not uniformly greater. An accurate recorded birth time is important. Descriptive only; calculation and acceptance are unchanged."}
    ],
    "validation": {"status": "UNVERIFIED_GOLDEN_CHARTS", "claim_boundary": "Swiss-on-Swiss integration conformance only; not independent astronomical validation, mathematical verification or historical clock verification"}
  }
}
```

### Limitations and claim boundary

- The metadata reports what the engine did and which pinned data it used. It is not evidence that the chart is astronomically correct, and it is not independent validation, mathematical verification or historical clock verification.
- UT1 is not measured; Delta T after 2028 and UT1 − UTC after 2027-06-28 are model projections.
- The ±66° band, the 1900–2100 window, the pre-1970 refusal and the D3 timezone policy are support policy, not astronomical limits; D3 is not geolocation. The high-latitude disclosure is descriptive only.
- Per-zone TZif hashes are not listed; the manifest SHA-256 covers them.

### Migration from 0.1.0

- All 0.1.0 keys, values and their order are unchanged; `method` keeps its five keys. `schema_version` becomes `"0.2.0"` and `calculation_metadata` is appended last.
- A 0.1.0 consumer that ignores unknown keys keeps working once it accepts `"0.2.0"`. A consumer that pins `"0.1.0"` must be updated.
- `provenance.legacy_projection(chart)` drops `calculation_metadata` and restores `"0.1.0"`. For every accepted request it equals the KUN-03 conformance engine output (PR #33, `bec4641`) byte for byte under canonical JSON; `tests/test_calculation_metadata.py` pins this for ten synthetic boundary requests (seven of them on `UTC`, reproduced with a test-only D3 bypass, and again on geographic zones; see D3 above).

## Proposed schema 0.3.0: D9 whole-sign houses (Gate 3E, PENDING OWNER APPROVAL)

**Status.** Proposed candidate only. Built under the owner's Gate 3E instruction for isolated development; it does not canonize a schema, does not lift any merge or release gate and does not satisfy the remaining KUN-F06 items (Nakshatra/Pada for all bodies and the Lagna stay deferred). Adoption needs independent QA and a separate owner decision.

**Convention (SCI-01f, unchanged).** D9 sign = Navamsa sign of the unrounded longitude (108 half-open 3°20′ segments from Mesha); D9 Lagna = Navamsa sign of the unrounded Lagna (no second Swiss call); D9 house = `((D9 sign index of body − D9 sign index of Lagna) mod 12) + 1`, sign indices 0 Mesha … 11 Meena. Ketu is classified from the exact sum Rahu + 180. No new Swiss computation.

**Old versus new.**

| | 0.2.0 (canonical baseline) | 0.3.0 (proposed) |
|---|---|---|
| `schema_version` | `"0.2.0"` | `"0.3.0"` |
| `planets.<body>` keys | `longitude_deg`, `rashi`, `navamsa_rashi`, `whole_sign_house` | the same four, then `navamsa_whole_sign_house` |
| top-level keys | … `planets`, `calculation_metadata` | the same, then `d9` (last) |
| `lagna` | unchanged | unchanged (its D9 house is 1 by definition) |
| `calculation_metadata` | `/3` | unchanged, still `/3` (see "Metadata" below) |

**New fields.**

| Field | Meaning |
|---|---|
| `planets.<body>.navamsa_whole_sign_house` | Integer 1–12: D9 whole-sign house of the body counted from the D9 Lagna sign (house 1). The one source of each body's D9 house. |
| `d9.house_system` | `"whole_sign"`. |
| `d9.lagna_rashi` | D9 Lagna sign; always equals `lagna.navamsa_rashi`. |
| `d9.houses` | Twelve objects in house order 1–12 (the order North Indian charts number houses): `house` (1–12), `rashi` (D9 sign of that house, `SIGNS[(D9 Lagna + house − 1) mod 12]`), `grahas` (body keys whose `navamsa_whole_sign_house` equals `house`, in `planets` order; may be empty). |

`d9` is built only from the per-body fields after they are set (`engine._d9_chart`), so it cannot be an independent or inconsistent source: every body is listed exactly once, in its own house, and that house's `rashi` equals the body's `navamsa_rashi`. Consumers that receive a chart where these disagree must refuse to present it (the prototype does).

**Compatibility.**
- Additive only: every 0.2.0 key, value and key order is unchanged; the new per-body key is appended after `whole_sign_house` and `d9` after `calculation_metadata`.
- `provenance.baseline_projection(chart)` removes `d9` and every `navamsa_whole_sign_house` and restores `"0.2.0"`; for every accepted request it is meant to equal Gate 3D (`6c9e670`) output byte for byte (Gate 3E invariance evidence on the 3,301-case CLI corpus and the 1,229-request HTTP corpus). `provenance.legacy_projection` now applies the baseline projection first, so 0.1.0 output is unchanged (the PR #33 golden tests still pass).
- A consumer that ignores unknown keys keeps working once it accepts `"0.3.0"`; a consumer that pins `"0.2.0"` must be updated or fed `baseline_projection`. Refusals, refusal order, error codes and texts are unchanged.
- Readiness (`output_contract`) now also requires a `d9` block with `house_system` `"whole_sign"` and checks `schema_version` against the engine constant (`0.3.0` here).

**Metadata.** No metadata change is made in this proposal, so `metadata_schema` stays `/3` and every metadata value is unchanged. `conventions.houses` still describes only the D1 model. Recording the D9 house rule there (`d9_model`, `d9_rule`) would be a new key and need `/4`; that is left as an owner option.

**Regression expectations.** For every request: identical refusal (exit code, code, text); for every accepted request: `baseline_projection(new)` equals the Gate 3D chart exactly, including longitudes, D1 houses, D9 signs, D1 Lagna, Moon Nakshatra/Pada, UTC conversion and metadata. Golden references are not regenerated from the new code.

### Reproduction requirements

To get the same output, including the metadata: `pyswisseph==2.10.3.2` (Swiss 2.10.03), `tzdata==2026.5` (IANA 2026e) with the packaged TZif manifest, and the two ephemeris files matching the packaged ephemeris manifest. A different binding, library, tzdata or ephemeris file fails closed (`SWISS_*` since Gate 3C, `TZDATA_*`, `EPHEMERIS_*`).

**Privacy**: CLI retains no state; stdout contains sensitive birth timestamp/coordinates and must be protected by the caller. Never send customer content to telemetry or GitHub.
