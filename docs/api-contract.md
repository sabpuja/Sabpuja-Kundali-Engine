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
- `birth_datetime` is exact birth-local ISO-8601 with an explicit UTC offset.
- `timezone` is the IANA timezone identifier; conversion must match the offset, including DST/historical rules.
- Supported birth dates (SCI-03 initial window): the **local civil date** as written in `birth_datetime` must be 1900-01-01 to 2100-12-31 inclusive. It is checked before conversion (after the timezone is recognised and before the offset is matched), so the UTC instant may be as early as 1899-12-31T10:00:00Z (local 1900-01-01T00:00:00 at UTC+14) or as late as 2101-01-01T11:59:59.999999Z (local 2100-12-31T23:59:59.999999 at UTC−12; microsecond precision is accepted). A date outside is refused with `DATE_OUTSIDE_SUPPORTED_RANGE` (`UnsupportedInputError`, a `ValueError` subclass carrying `.code`). Historical-clock refusals (SCI-03 RG-HIST) are a separate, later gate (P8).
- Latitude decimal north-positive, longitude east-positive. Both must be JSON numbers (not booleans or strings), finite (no `NaN`/`Infinity`, no integers too large for a float) and within the accepted range: latitude -66.0 to 66.0 inclusive (SCI-01g supported band, the same for every date), longitude -180 to 180 inclusive. A finite latitude outside the band is refused with `LATITUDE_OUTSIDE_SUPPORTED_BAND` before any Swiss call; non-numbers and non-finite values keep their existing input errors.
- No name, email, phone, address, account ID or other identifying attributes in the calculation request.
- A birthplace autocomplete service is future work and must be offline/self-hosted.

Success returns JSON `schema_version`, `validation_status`, `method`, `birth`, `lagna`, `moon_nakshatra` and `planets`. Planet values contain longitude, Rashi, D9 sign and whole-sign house. Output is not yet independently verified.

Longitude and category semantics:
- Rashi (30°), Nakshatra (40/3°) and Pada/D9 (10/3°) segments are half-open, `[start, end)`. Every category, house, Moon Nakshatra and Ketu (exactly opposite Rahu) is derived from the unrounded Swiss Ephemeris value with exact arithmetic, never from the displayed number.
- `longitude_deg` is display only: the value normalized to `[0, 360)` and rounded to 8 decimals. A rounding that reaches 360 is shown as `0.0`; `360.0` is never emitted.
- Near-boundary display ambiguity: within 5e-9° below a boundary, the displayed value can equal the boundary while the category is the segment before it (raw 29.999999996 is shown as `30.0` and stays Mesha; raw 359.999999996 is shown as `0.0` and stays Meena). Do not re-derive categories from `longitude_deg`; use the category fields.

Errors: CLI writes JSON `{"error":"..."}` to stderr, writes nothing to stdout, prints no traceback and exits 2. Error text never repeats the birth time, timezone or coordinates. No HTTP response codes are promised yet. Network service contracts must be separately reviewed and versioned.

Three coordinate failures are deliberately distinct:
- **Invalid latitude/longitude** (`ValueError`, input error): the value is not a usable number, or the longitude is outside -180 to 180, for example `"latitude must be a number"`, `"latitude must be a finite number"` or `"longitude must be between -180 and 180 (inclusive)"`. The caller must correct the input.
- **Outside the supported latitude band** (`UnsupportedInputError`, a `ValueError` subclass carrying `.code`; error text `LATITUDE_OUTSIDE_SUPPORTED_BAND: latitude must be between -66 and 66 (inclusive)`): the latitude is a finite number outside -66.0 to 66.0. It is refused for every date and longitude, before the ephemeris check and before any Swiss Ephemeris call, so such a request never reaches the ascendant calculation. The ascendant vehicle (`b"W"`, SCI-01e) would compute at any latitude, so this band alone decides which locations are accepted. This is the owner-approved SCI-01g initial support policy, not a permanent astronomical limit; any wider support would need a new owner decision. A disclosure of birth-time sensitivity above 60° (`HIGH_LATITUDE_TIME_SENSITIVITY`) is not emitted yet; it is assigned to future P7 calculation metadata.
- **Cannot compute** (`ChartComputationError`, error text `ASCENDANT_UNCOMPUTABLE: ...`): defensive only. It is raised if Swiss Ephemeris unexpectedly fails the ascendant call (`houses_ex` with `b"W"`) for an in-band request; this is not expected for valid input. No partial chart is returned and no other house method is substituted.

Lagna (SCI-01e, KUN-03 P3): `ascmc[0]` of `houses_ex(jd_ut, lat, lon, b"W", FLG_SIDEREAL)`, the eastern rising point of the ecliptic minus the true Lahiri ayanamsa. Inside the ±66.0° band it was bit-identical to the previous `b"P"` value at every sampled point (KUN-02 E-A1, 167,612 points; P3 tests and comparison grid), and no accepted chart changed in those samples. This is sampled evidence, not a proof. The vehicle is not yet named in the output; it is recorded in P7 calculation metadata.

**Privacy**: CLI retains no state; stdout contains sensitive birth timestamp/coordinates and must be protected by the caller. Never send customer content to telemetry or GitHub.
