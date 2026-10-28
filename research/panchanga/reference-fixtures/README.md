# Panchanga reference fixtures (WP-B1)

**PROPOSED — NOT CANONICAL — non-executable research data.** No test harness reads these files yet. WP-B2, if authorized, adds the harness in its own PR.

| File | Fixture set | Class | Cases |
|---|---|---|---|
| [geocentric-lunar-phase-events-2026.json](geocentric-lunar-phase-events-2026.json) | PAN-REF-PHASE-2026 | Direct published, two independent publishers (USNO, NASA), whole minutes | 50 (25 Tithi + Karana boundaries, 25 Karana-only boundaries) |
| [usno-sunrise-sunset-2026.json](usno-sunrise-sunset-2026.json) | PAN-REF-SUN-2026 | Direct published, one publisher (USNO) | 14 (12 positive, 2 negative) |
| [derived-classification-cases.json](derived-classification-cases.json) | PAN-DER-2026 | Derived from the two sets above | 8 |
| [boundary-test-specifications.json](boundary-test-specifications.json) | PAN-SPEC-BOUNDARY | Specifications, no numerical expectations | 16 |
| [imd-rashtriya-panchang-capture-template.json](imd-rashtriya-panchang-capture-template.json) | PAN-REF-IMD | Empty template; IMD not retrievable on 2026-10-28. Holds reviewer-reported **unverified** candidates, which are not counted | 0 |

## Classes

- **DIRECT_PUBLISHED_GEOCENTRIC_EVENT**: an instant published by an independent source for a location-independent event, such as a lunar phase. Usable for every location.
- **DIRECT_PUBLISHED_LOCATION_EVENT**: a published value for **one exact coordinate pair** and convention. It is not valid for another point in the same city, or for a station.
- **DIRECT_PUBLISHED_NEGATIVE_EVENT**: a published statement that an event does not occur, for example no sunrise.
- **DERIVED**: built from published values plus stated arithmetic or an explicitly labelled estimate. Never presented as published.

## Field conventions

- `published_*` / `published_values`: values exactly as published (whole minutes), with the source id from [../SOURCE-REGISTER.md](../SOURCE-REGISTER.md).
- `derived_local_display`: arithmetic conversions (for example UT + 05:30). Not published.
- `proposed_tolerance`: a proposal only, with justification. QA and the owner fix tolerances before any evaluation (PAN-D15).
- `status`: `VERIFIED_TWO_INDEPENDENT_PUBLISHERS`, `VERIFIED_SINGLE_PUBLISHER`, `DERIVED`, `DERIVED - CONVENTION-SENSITIVE` or `UNVERIFIED`.

## Independence

No expected value was produced by the Sabpuja engine, Swiss Ephemeris or PR #48. The synthetic birth instants in the derived cases are test inputs, not personal data.
