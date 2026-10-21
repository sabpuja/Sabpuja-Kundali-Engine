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
- Latitude decimal north-positive, longitude east-positive. Both must be JSON numbers (not booleans or strings), finite (no `NaN`/`Infinity`, no integers too large for a float) and within the accepted range: latitude strictly between -89 and 89, longitude -180 to 180 inclusive. This range is unchanged pending the owner's high-latitude method decision (SCI-01).
- No name, email, phone, address, account ID or other identifying attributes in the calculation request.
- A birthplace autocomplete service is future work and must be offline/self-hosted.

Success returns JSON `schema_version`, `validation_status`, `method`, `birth`, `lagna`, `moon_nakshatra` and `planets`. Planet values contain longitude, Rashi, D9 sign and whole-sign house. Output is not yet independently verified.

Longitude and category semantics:
- Rashi (30°), Nakshatra (40/3°) and Pada/D9 (10/3°) segments are half-open, `[start, end)`. Every category, house, Moon Nakshatra and Ketu (exactly opposite Rahu) is derived from the unrounded Swiss Ephemeris value with exact arithmetic, never from the displayed number.
- `longitude_deg` is display only: the value normalized to `[0, 360)` and rounded to 8 decimals. A rounding that reaches 360 is shown as `0.0`; `360.0` is never emitted.
- Near-boundary display ambiguity: within 5e-9° below a boundary, the displayed value can equal the boundary while the category is the segment before it (raw 29.999999996 is shown as `30.0` and stays Mesha; raw 359.999999996 is shown as `0.0` and stays Meena). Do not re-derive categories from `longitude_deg`; use the category fields.

Errors: CLI writes JSON `{"error":"..."}` to stderr, writes nothing to stdout, prints no traceback and exits 2. Error text never repeats the birth time, timezone or coordinates. No HTTP response codes are promised yet. Network service contracts must be separately reviewed and versioned.

Two coordinate failures are deliberately distinct:
- **Invalid latitude/longitude** (input error): the value is not a usable number or is outside the accepted range, for example `"latitude must be a finite number"` or `"latitude must be between -89 and 89 (exclusive)"`. The caller must correct the input.
- **Cannot compute reliably with the current method** (`ASCENDANT_UNCOMPUTABLE: ...`): the input is valid, but Swiss Ephemeris cannot compute the ascendant there with the house call the engine currently uses (Placidus, `houses_ex` with `b"P"`), which is undefined beyond the polar circles (roughly |latitude| > 66.5°; the exact edge depends on date and time). No partial chart is returned and no other house method is substituted. This is a limitation of the current foundation method, not a statement that these regions are permanently unsupported; broader high-latitude support is an open owner decision (SCI-01).

**Privacy**: CLI retains no state; stdout contains sensitive birth timestamp/coordinates and must be protected by the caller. Never send customer content to telemetry or GitHub.
