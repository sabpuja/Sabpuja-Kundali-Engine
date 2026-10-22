# KUN-02 implementation plan: prioritized, independently reviewable changes

**Status:** PLAN ONLY. No package below is authorized. Each one needs the named owner decision recorded in `main:docs/DECISIONS.md`, ChatGPT QA of its own draft PR, and owner approval to merge. Each is small enough to review alone, targets the foundation branch, and carries its own tests and evidence.

Order matters in one place: **P2 (latitude band) must land before or with P3 (`b"W"`)**, otherwise P3 alone would begin accepting polar births.

| Priority | Package | Decision needed | Numeric change | Input change | Size |
|---|---|---|---|---|---|
| P1 | Pin tzdata and record it (engineering fix) | depends on SCI-03 reproducibility policy | none for Asia/Kolkata; possible pre-1956 changes in 8 Asian zones vs a backzone host | none | S |
| P2 | Latitude band \|lat\| ≤ 66.0° | SCI-01g | none | refuses \|lat\| > 66.0 | S |
| P3 | Ascendant via `b"W"` | SCI-01e (after P2) | none (bit-identical) | none once P2 is in | XS |
| P4 | Local-civil-date window | SCI-03 | none | edge dates only | S |
| P5 | Structured time refusals and strict format | SCI-03 / API contract | none | refuses non-RFC 3339 forms | M |
| P6 | D9 whole-sign houses (and optional all-body Nakshatra) | SCI-01f, SCI-02 | additive fields | none | M |
| P7 | Method and time-scale metadata | SCI-01a, d, h | additive fields | none | S |
| P8 | RG-HIST fail-closed gate | SCI-03 (RG-HIST scope) | none | refuses gated historical births | M |
| P9 | Promote the KUN-02 Swiss-state test into the main suite | none beyond QA | none | none | XS |

## P1. Pin tzdata and record it

- **Nature:** an engineering reproducibility fix that depends on the SCI-03 policy, not an astrological convention. It needs its own draft PR and QA.
- **Change:** pin `tzdata==2026.5` **and** a committed manifest of SHA-256 hashes of the TZif bytes the engine uses (at least every key accepted for births); load zones deterministically, either by setting an empty `PYTHONTZPATH` in the service environment before the interpreter starts, or through an isolated loader (`ZoneInfo.from_file` on package resources, keyed in the engine's own cache). Do **not** call the global `zoneinfo.reset_tzpath()` inside a running multi-request process: it changes behaviour for every caller and `ZoneInfo` instances already cached keep their old data. Add `method.tzdata_version` and the manifest hash to output; document backward-incompatible changes between tzdata versions.
- **Why:** Ubuntu tzdata 2026e and PyPI tzdata 2026.5 disagree for 8 Asian zones before 1956 (backzone build); results must not depend on the host image. The same IANA version does not guarantee identical pre-1970 binaries.
- **Tests:** the loaded bytes match the manifest; `IANA_VERSION` is recorded; cache behaviour (repeated loads, concurrent requests, no stale instance from the system path); a two-host reproducibility check (system tzdata with and without `backzone`) giving identical output; the KUN-02 IANA cross-check run against the package; the tzdata agreement probe listing expected differences.
- **Acceptance:** all 63 KUN-02 time cases unchanged; Asia/Kolkata offsets unchanged; identical output on both hosts.

## P2. Latitude band

- **Change:** `_coordinate(..., "latitude", 66.0, inclusive=True)` style check with code `LATITUDE_OUTSIDE_SUPPORTED_BAND`; longitude unchanged.
- **Tests:** ±66.0 accepted; `nextafter(66.0, inf)` and ±66.55 refused on every date; 1900 and 2100 behave the same; existing polar tests updated to expect the new code.
- **Acceptance:** no change to any accepted chart.

## P3. Ascendant via `b"W"`

- **Change:** `b"P"` → `b"W"` in `engine.py:130`; keep the `ASCENDANT_UNCOMPUTABLE` handler as defensive code; set `method.ascendant = "houses_ex W, sidereal, Lahiri"`.
- **Tests:** regression comparing the engine's Lagna to the `b"P"` value on the KUN-02 grid inside the band (bit-identical); the existing Swiss-conformance suite (PR #18) Lagna checks re-run with `-houseW`-equivalent arguments.
- **Acceptance:** zero numeric differences on the KUN-02 grid and on the PR #18 cases.

## P4. Local-civil-date window

- **Change:** validate `local.date()` within 1900-01-01..2100-12-31 before converting; code `DATE_OUTSIDE_SUPPORTED_RANGE`.
- **Tests:** KUN-02 T46–T51 flip to the proposed outcomes; first/last accepted local seconds in UTC+14 and UTC−12 zones; 29 February rules.

## P5. Structured time refusals and strict format

- **Change:** an explicit RFC 3339 profile parser (no reliance on `fromisoformat` widening); codes `TIME_FORMAT_INVALID`, `TIME_OFFSET_REQUIRED`, `TIME_LEAP_SECOND_UNSUPPORTED`, `DATE_INVALID`, `TIMEZONE_INVALID`, `TIME_NONEXISTENT_LOCAL`, `TIME_OFFSET_MISMATCH`; optional `TIMEZONE_NOT_LOCATION_BASED`.
- **Gap versus mismatch rule:** compute IANA's offsets for the wall time with `fold=0` and `fold=1`; if neither maps back to the same wall time, it is a gap; otherwise the given offset must be one of them.
- **Tests:** every KUN-02 time case gets its proposed code; messages contain no birth data.

## P6. D9 houses (and optional all-body Nakshatra)

- **Change:** `planets.<body>.d9_whole_sign_house` from the D9 Lagna; optional `nakshatra` per body and Lagna if the owner chooses.
- **Tests:** classical-rule oracle (as in KUN-02 A10) at all 108 Navamsa edges and float neighbours; schema version bump.

## P7. Method and time-scale metadata

- **Change:** method fields naming the Lahiri definition, frame, node, house model, ascendant vehicle, sidereal-time model note (2050 switch), time-scale assumption by era, ΔT source, Swiss version, ephemeris manifest SHA-256 and tzdata version.
- **Tests:** contract test for the fields; no numeric change.

## P8. RG-HIST gate

- **Change:** a reviewed, versioned gate table (zone, start, end, policy), minimum `Asia/Kolkata` before 1956-01-01, policy `fail_closed`; code `HISTORICAL_CLOCK_UNVERIFIED`. The minimum is a temporary conservative MVP policy, not a certification of clocks outside it. Verified clock selection is a later DATA-01 package with sourced offsets (historical birthplace, clock source, place-to-zone provenance, jurisdiction-specific date coverage; birth-time report §7); this package invents no offset.
- **Tests:** dates on both sides of each gate edge; zones outside the gate unaffected.

## P9. Swiss state isolation test

- **Change:** move `test_engine_resets_leaked_swiss_state` into the main suite and document that swisseph may be called only inside `_SWISS_LOCK`.

## Evidence each package must attach

Exact base and head SHA; the full test log with 0 skipped tests against the pinned data; the KUN-02 runner report (`python -m tests.kun02.run`) before and after, with the expected differences listed; Swiss and tzdata versions; confirmation that PR #11, #14 and #18 were not modified.
