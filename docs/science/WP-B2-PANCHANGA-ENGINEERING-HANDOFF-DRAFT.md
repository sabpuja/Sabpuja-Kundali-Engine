# WP-B2 Panchanga engineering handoff (draft)

**DRAFT SPECIFICATION — NOT AN IMPLEMENTATION AUTHORIZATION — DEPENDS ON OWNER DECISIONS IN SCI-PAN-01**

| Field | Value |
|---|---|
| Prepared by | Claude (Lead Developer), WP-B1, 2026-10-28 |
| Baseline | `main` `5395d2bc33847d1363e6d838f6109bad552221e3` |
| Method source | [SCI-PAN-01 proposal](SCI-PAN-01-PANCHANGA-METHOD-DECISION-PROPOSAL.md) (PROPOSED, not canonical) |
| Requirement | Proposed KUN-A01 Birth Panchanga (PRD 12.1), Gate ENG (PRD 13) |
| Status | Revision 0.4-draft (after ChatGPT reviews 5679285841 and 5679456114, and the reviewer-mediated IMD evidence; the 46 IMD candidates are not usable as WP-B2 fixtures until promoted under SCI-PAN-01 section 8.1). Every choice below assumes the **recommended** SCI-PAN-01 option. SCI-PAN-01 0.2 makes **no** sunrise-convention recommendation, so the sunrise convention is a parameter here. If the owner selects otherwise on any item, this draft is revised before WP-B2 starts. **Readiness: BLOCKED** |

Nothing here authorizes an endpoint, engine change, PDF feature, UI change, merge or deployment. WP-B2 needs its own scoped ticket and owner authorization.

## 1. Readiness preconditions

WP-B2 should start only when all of these hold:

1. The owner has recorded SCI-PAN-01 decisions PAN-D01 to PAN-D20 under the two-step rule in [DECISIONS.md](../DECISIONS.md).
2. IMD Rashtriya Panchang method facts and the SCI-PAN-01 section 8.1 coverage (at least 34 rows) are captured into the [capture template](../../research/panchanga/reference-fixtures/imd-rashtriya-panchang-capture-template.json) **from the primary source** and second-person checked. Alternatively, the owner explicitly accepts PAN-D20 option B. Reviewer-reported candidates do not count.
3. The engine base for WP-B2 is fixed. Today the engine (`src/sabpuja_kundali/…`, chart schema `0.3.0`) lives on the draft stack (PR #42 `185353a`, not merged into `main`; PR #1 HOLD active). WP-B2 must name its base SHA and must not stack onto an unresolved branch without the owner's OD-09 merge plan.
4. Karana naming source decided (PAN-D07), or WP-B2 ships with the index only.
5. Hindi reviewer named (OD-08) before any Hindi Panchanga label reaches a report.

## 2. Proposed module boundaries

| Module (proposed) | Responsibility | Must not |
|---|---|---|
| `panchanga_rules` | Pure functions: tithi, paksha, nakshatra/pada (delegating to the existing chart `rules.nakshatra`), yoga, karana index and name (when adopted), vara mapping, name tables | Call Swiss; read clocks; round |
| `panchanga_astro` | Sun and Moon longitudes at an instant through the **existing** SCI-01d path; sunrise and sunset through `swe.rise_trans` with the adopted flags; all Swiss calls under the existing Swiss lock with per-request state reset (sidereal mode, ΔT, topo) | Introduce new Swiss flags for longitudes; fall back to Moshier; call `mooncross`/`solcross` |
| `panchanga_search` | Bounded transition search (TS-1 with optional TS-2) over E, S, λ☾ and the sunrise bracket | Unbounded loops; extrapolation |
| `panchanga_contract` | Builds the `sabpuja-panchanga/1` document, provenance and refusals | Modify the chart document or metadata `/3` |

The existing chart engine stays the only producer of chart `0.3.0`. Panchanga reads the same validated request (birth instant, coordinates, zone) after the same SCI-03 validation and refusal order.

## 3. Input and output contract (proposed `sabpuja-panchanga/1`)

**Input:** the same validated birth request as the chart. No new personal fields. Elevation is not accepted (PAN-D04 with SUN-B).

**Output (illustrative shape, not a frozen schema):**

```json
{
  "panchanga_schema": "sabpuja-panchanga/1",
  "method": {
    "id": "SCI-PAN-01",
    "version": "<adopted revision>",
    "longitude_frame": "SCI-01d geocentric apparent sidereal, SCI-01a Lahiri true",
    "sunrise_convention": "<adopted, e.g. swiss_hindu_rising: disc centre, no refraction, geocentric, ecliptic latitude 0>",
    "vara_convention": "sunrise_to_sunrise",
    "boundary_rule": "half_open_exact",
    "solver_convergence_s": 0.5,
    "method_accuracy_note": "convergence is a solver property, not an accuracy claim (SCI-PAN-01 section 5.9)"
  },
  "birth_time": {
    "instant_utc": "YYYY-MM-DDThh:mm:ssZ",
    "tithi": {"number": 1, "paksha": "shukla", "paksha_day": 1, "id": "pratipada",
              "starts_utc": "…", "ends_utc": "…", "near_boundary": false},
    "nakshatra": {"index": 0, "id": "ashwini", "pada": 1, "starts_utc": "…", "ends_utc": "…", "near_boundary": false},
    "yoga": {"number": 1, "id": "vishkambha", "starts_utc": "…", "ends_utc": "…", "near_boundary": false},
    "karana": {"half_tithi_index": 1, "id": null, "name_status": "not_adopted", "starts_utc": "…", "ends_utc": "…"},
    "vara": {"id": "sunday", "governing_sunrise_utc": "…"},
    "civil_weekday": {"id": "sunday", "local_date": "YYYY-MM-DD"},
    "sunrise_utc": "…",
    "sunset_utc": "…"
  },
  "sunrise_day": {
    "local_date": "YYYY-MM-DD",
    "sunrise_utc": "…",
    "next_sunrise_utc": "…",
    "at_sunrise": {"tithi": {}, "nakshatra": {}, "yoga": {}, "karana": {}, "vara": {}},
    "transitions": [{"element": "tithi", "from": 30, "to": 1, "instant_utc": "…"}]
  },
  "local_rendering": {"zone": "Asia/Kolkata", "offset_rule": "SCI-03 pinned tzdata", "withheld_instants": []},
  "provenance": {
    "swiss_version": "2.10.03", "ephemeris_manifest_sha256": "…", "tzdata": "2026.5",
    "chart_schema_unchanged": "0.3.0", "calculation_metadata_unchanged": "sabpuja-calculation-metadata/3"
  }
}
```

Rules:
- All instants are in UTC to the whole second in the machine output (PAN-D09). Whole seconds are an output resolution, not a statement of accuracy: method accuracy is at minute level for sunrise and is unquantified for lunar events until reference comparisons run. Local rendering is a presentation layer that uses the pinned tzdata and the SCI-03 rules. It is withheld, with a flag, for instants before 1970-01-01 local or after 2100-12-31 local (PAN-D13).
- `near_boundary` is true when the birth instant lies within 120 s of the element's start or end.
- `karana.id` stays `null`, with `name_status: "not_adopted"`, until PAN-D07 is decided.
- The illustration shows the case where the governing sunrise exists. When it is physically undefined, the outcome depends on PAN-D11 (PENDING; section 6): under D11-A no document is produced; under the proposed D11-B, `vara`, the sunrise and sunset fields and `sunrise_day` carry `{"status": "unavailable", "reason": "PANCHANGA_SUNRISE_UNDEFINED"}`.
- No field of the chart document changes. The Panchanga document references the chart only by sharing the request; it never embeds birth details beyond what the chart already returns.

## 4. Naming and identifiers

- Machine ids: lower-snake-case ASCII as in SCI-PAN-01 Appendix A. Ids never change with locale.
- Display names come from a locale table (`en`, `hi`). Numeric content is identical across locales (QA-015 pattern).
- Nakshatra ids derive from the existing chart engine names, so the chart and the Panchanga never diverge.

## 5. Versioning strategy

| Item | Proposal |
|---|---|
| Output | `sabpuja-panchanga/1`, independent of chart schema `0.3.0` |
| Method | `method.id` + `method.version` record the adopted SCI-PAN-01 revision; any convention change bumps the method version and needs owner approval |
| Chart | `0.3.0` byte-identical; `sabpuja-calculation-metadata/3` unchanged |
| Breaking change | A new major `sabpuja-panchanga/2`; the previous version is kept for reproducibility of issued reports |

## 6. Error and refusal contract (proposed)

Existing codes keep their canonical order exactly as implemented on the WP-B2 engine base (P5 D1: birth-time errors before coordinate errors; P8 G5: `HISTORICAL_CLOCK_UNVERIFIED` after `TIME_OFFSET_MISMATCH` and before `COORDINATE_INVALID`; then the latitude band and ephemeris checks as the engine orders them). Panchanga-specific codes come after all of them:

| Code (proposed) | When | Output |
|---|---|---|
| `PANCHANGA_SUNRISE_UNDEFINED` | Swiss −2 for rise, consistent with the geometric expectation (physically no sunrise) | Under proposed D11-B: sunrise-independent elements and `civil_weekday` returned; `vara`, sunrise, sunset and `sunrise_day` returned as `{"status": "unavailable", "reason": "PANCHANGA_SUNRISE_UNDEFINED"}`. Under D11-A: whole object refused |
| `PANCHANGA_SUNSET_UNDEFINED` | Same for set | Same as above |
| `PANCHANGA_TRANSITION_NOT_CONVERGED` | Iteration cap reached, no sector change in the bracket, non-finite value, sunrise residual-altitude check failed, or no sunrise bracketed although geometry says one exists | Whole Panchanga refused (every option) |
| `PANCHANGA_METHOD_NOT_ADOPTED` | A requested element (for example Karana names) has no adopted method | That field omitted with reason; not an error for the document |

Error messages follow the canonical CLI contract (D4: JSON error, exit 2, fixed privacy-safe message, no traceback, no birth data).

## 7. Transition-search algorithm (proposed)

For an element with monotone angle f(t) ∈ {E, S, λ☾} and sector width w:
1. k = sector index of f(t_birth). Target angles a_start = k·w and a_end = (k+1)·w.
2. Bracket forward: step from t_birth by 6 h until the sector changes, up to 2.5 days. Bracket backward the same way.
3. Bisect each bracket until it is ≤ 0.5 s, with at most 64 iterations.
4. Every Swiss call checks the returned `FLG_SWIEPH`. On failure, use the existing ephemeris refusal.
5. Report the first instant at which the new sector holds (half-open), rounded to the whole second only for output.

Sunrise and sunset:
1. Governing sunrise for the birth = latest sunrise ≤ birth instant: call `rise_trans(t_birth − 1.5 d, Sun, rise | adopted flags)` and step forward until the next rise would pass the birth instant (bounded to 3 calls).
2. Verify `FLG_SWIEPH` by a `calc_ut` call at the returned instant.
3. Residual check: recompute the Sun's altitude at the returned instant with the convention's definition. Refuse if the residual exceeds the bound fixed by QA (proposed 1 arcsecond, about 0.25 s).
4. Return code −2 → `PANCHANGA_SUNRISE_UNDEFINED`.

## 8. Compatibility rules for chart schema 0.3.0

- Chart CLI and HTTP outputs are byte-identical before and after WP-B2 on the existing regression sets of the engine base (for example the earlier byte-identity chart sets and the Gate 3E fixtures), with and without a Panchanga call in the same process.
- `calculation_metadata` `/3` gets no new keys.
- The Panchanga Nakshatra/Pada equals `moon_nakshatra` for every regression request.
- Legacy `0.1.0`/`0.2.0` projections are unaffected.

## 9. Reference fixture integration plan

| Fixture set | How WP-B2 uses it | Pass rule |
|---|---|---|
| PAN-REF-PHASE-2026 (50 whole-minute events) | Search for E = 0/180 crossings (25 Tithi + Karana boundaries) and E = 90/270 crossings (25 Karana-only boundaries); check the Tithi/Karana index on both sides | Instant inside each fixture's provisional `accept_window_utc`. This shows minute-level agreement only, not second-level accuracy |
| PAN-REF-SUN-2026 (14) | SUN-A absolute check if SUN-A is adopted; for SUN-B, a differential check against an independently coded spherical-astronomy oracle anchored on the USNO time | ±120 s (SUN-A); oracle-defined bound (SUN-B); negative cases give `PANCHANGA_SUNRISE_UNDEFINED` (whole-object refusal under D11-A, typed `unavailable` sunrise fields under D11-B) |
| PAN-DER-2026 (8) | Classification tests; convention-sensitive cases assert the adopted convention's branch | Exact classification; margins reported |
| PAN-SPEC-BOUNDARY (16) | Each spec becomes unit, property or contract tests | As specified |
| PAN-REF-IMD (to be captured) | Tithi/Nakshatra/Yoga/Karana ends; IMD Central Station sunrise (only if SUN-D is adopted, and never against city coordinates); 24-hour-plus times converted as a derived field | Per PAN-D15, fixed before running. Nakshatra/Yoga rows are pass/fail oracles only if the SCI-PAN-01 section 3.1 ayanamsa check passes; otherwise they are reported as method differences |

The fixtures stay data. WP-B2 adds the executable harness in its own PR, and it may not edit a fixture's expected value without a new source citation.

### 9.1 How WP-B2 validation accounts for method differences (proposed)

| Factor | Rule for every reference comparison |
|---|---|
| Adopted ayanamsa | Engine values always use canonical SCI-01a. A reference row whose ayanamsa differs is either converted, with the difference stated (only when the reference publishes its definition), or used as a method-difference report rather than pass/fail. Tithi and Karana comparisons are ayanamsa-free (SCI-PAN-01 section 3.1) |
| IMD conventions | IMD sunrise is compared only at the IMD Central Station, only under the convention IMD states, and only after that statement is captured verbatim. IMD ending times are compared as geocentric IST moments. 24-hour-plus times are converted to the next civil date as a derived field, and the printed value is retained |
| Location-specific sunrise | USNO rows are compared only at their exact queried coordinates, under SUN-A (or SUN-D with the documented 3′ correction). No sunrise reference is reused for another location, and no station value is compared with a city |
| Publisher rounding | Each source's rounding rule (truncate or round) is recorded. Until it is known, the acceptance window spans both interpretations ([printed − 60 s, printed + 60 s]), or the union across sources as in PAN-REF-PHASE |
| Solver vs accuracy | Solver convergence (≤ 0.5 s) is reported separately from the residual against each reference. A pass means "within the pre-declared window", never "accurate to 0.5 s" |
| Tolerances | Fixed and committed before any evaluation run (PAN-D15), and reviewed by ChatGPT |

These rules add to Gate ENG and REL-01 and change neither. REL-01's mandatory Swiss CLI conformance, independent rule and formula checks, boundary and refusal fixtures, and data and state safeguards all still apply. Independent JPL/INPOP assurance remains optional, and only needed for an independent-accuracy claim.

## 10. Performance and determinism targets (proposed)

| Target | Proposal |
|---|---|
| Determinism | Identical input → byte-identical Panchanga document across runs, processes and locales |
| Latency | Birth-time + daily Panchanga p95 < 300 ms on the PERF-01 reference VPS (in addition to the chart); under PERF-01's pending budget |
| Swiss calls | About ≤ 400 per request (8 transitions × ≤ 2 brackets × ≤ ~25 evaluations, plus sunrise) |
| Concurrency | Same Swiss lock as the chart; no global state leaks (PAN-SPEC-15) |

## 11. QA matrix (proposed; IDs to be added to the acceptance matrix by a separately authorized change)

| Proposed ID | Level | Check |
|---|---|---|
| PAN-QA-01 | Unit | Rule oracles for Tithi, Nakshatra/Pada, Yoga, Karana index; half-open exact boundaries; 0/360 (PAN-SPEC-01 to -05) |
| PAN-QA-02 | Unit | Name tables: counts, order, ids stable, EN/HI parity |
| PAN-QA-03 | Boundary | Transition search convergence, caps and refusal (PAN-SPEC-06, -14) |
| PAN-QA-04 | Reference | 50 phase events within tolerance (independent) |
| PAN-QA-05 | Reference | Sunrise/sunset per the adopted convention; negative cases give `PANCHANGA_SUNRISE_UNDEFINED` per the PAN-D11 option adopted (PAN-SPEC-07, -11) |
| PAN-QA-06 | Reference | IMD rows within tolerance (after capture) |
| PAN-QA-07 | Conformance | Swiss CLI (`swetest`) conformance for Sun/Moon longitudes and rise/set at the same instants, per REL-01 |
| PAN-QA-08 | Integration | Chart `0.3.0` byte identity; Nakshatra identity; metadata `/3` unchanged |
| PAN-QA-09 | Contract | Refusal order and codes; no birth data in errors; CLI D4 format (PAN-SPEC-09, -10, -12, -13) |
| PAN-QA-10 | Determinism | Repeat runs, process isolation, locale invariance |
| PAN-QA-11 | Performance | Latency and Swiss-call budget |

## 12. ENG gate acceptance requirements for KUN-A01 (proposed)

Gate ENG PASS for WP-B2 requires, on the exact SHA:
1. Owner-adopted SCI-PAN-01 decisions are cited, and the implementation matches them.
2. PAN-QA-01 to PAN-QA-11 pass with raw logs. PAN-QA-06 passes, or its absence is covered by an explicit owner decision (PAN-D20).
3. No change to chart `0.3.0`, metadata `/3`, D1/D9 outputs or canonical refusal order; byte-identity evidence is supplied.
4. No Moshier fallback is reachable; ephemeris and tzdata manifests are verified.
5. Every expected value used in tests traces to a fixture with a source or to a rule oracle; none comes from the implementation under test or from PR #48.
6. ChatGPT independent review and re-execution, followed by the owner's merge decision. Gate RPT applies separately to any explanatory text.

## Revision history

| Version | Date | Author | Change | Approval |
|---|---|---|---|---|
| 0.1-draft | 2026-10-28 | Claude, WP-B1 | Initial handoff draft | ChatGPT review 5679285841: CHANGES REQUESTED |
| 0.2-draft | 2026-10-28 | Claude, WP-B1 | Sunrise convention parameterised; D11-B partial-output contract; IMD coverage precondition; precision wording | PENDING |
