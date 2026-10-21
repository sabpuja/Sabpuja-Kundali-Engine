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
- Latitude decimal north-positive, longitude east-positive; polar edge cases are out of initial scope.
- No name, email, phone, address, account ID or other identifying attributes in the calculation request.
- A birthplace autocomplete service is future work and must be offline/self-hosted.

Success returns JSON `schema_version`, `validation_status`, `method`, `birth`, `lagna`, `moon_nakshatra` and `planets`. Planet values contain longitude, Rashi, D9 sign and whole-sign house. Output is not yet independently verified.

Errors: CLI writes JSON `{"error":"..."}` to stderr and exits nonzero. No HTTP response codes are promised yet. Network service contracts must be separately reviewed and versioned.

**Privacy**: CLI retains no state; stdout contains sensitive birth timestamp/coordinates and must be protected by the caller. Never send customer content to telemetry or GitHub.
