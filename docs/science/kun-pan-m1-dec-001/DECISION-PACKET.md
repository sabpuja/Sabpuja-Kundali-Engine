# KUN-PAN-M1-DEC-001: Owner method decisions for Panchanga M1

**PROPOSAL. Every decision below is PENDING. Nothing here is approved, canonical or an implementation authorization.** Claude recommends; the owner decides. Adoption follows the two-step rule in [`docs/DECISIONS.md`](../../DECISIONS.md): an owner-selected pre-merge record, an owner-authorized merge, then a post-merge adoption receipt.

Sources: SCI-PAN-01 rev 0.5 ([proposal](../SCI-PAN-01-PANCHANGA-METHOD-DECISION-PROPOSAL.md), §7 decision matrix) and [PANCHANGA-M1-MILESTONE.md](../kun-sci-pol-002/PANCHANGA-M1-MILESTONE.md) §3, both on `main` `de721d6`.

## 0. How to answer

For each decision the owner can reply with one of the codes in its "Owner options" row, for example "D01-A, D02-M1, D07-A, …". A single reply "approve all recommended options in KUN-PAN-M1-DEC-001 at <SHA>" is enough if the owner accepts every recommendation. Any option can also be modified or rejected.

## 1. M1 scope (preserved, unchanged)

| In M1 (birth instant only) | Not in M1 |
|---|---|
| Tithi 1–30, Paksha, Paksha day 1–15 | Sunrise, sunset, Vara, civil weekday output |
| Karana half-tithi index 1–60, **no names** | Sunrise-based daily Panchanga, kshaya/adhika |
| Yoga index 1–27 | Masa, Samvat, Amanta/Purnimanta |
| Nakshatra and Pada (identical to chart `moon_nakshatra`) | Karana, Yoga and Tithi names; Hindi labels |
| Start and end instants of the current Tithi, Karana, Yoga, Nakshatra (and Pada) | Report text, interpretations, any customer-facing output |
| Separate `sabpuja-panchanga/1` document | Any change to chart schema 0.3.0 or metadata `/3` |

## 2. Decisions needed now (13)

### PAN-D01: Longitude frame

| | |
|---|---|
| Existing proposal | SCI-PAN-01 §3, §6, §7: A, reuse SCI-01d exactly (geocentric apparent sidereal, true Lahiri, `FLG_SWIEPH \| FLG_SIDEREAL`, no Moshier) |
| Recommended | **A** |
| Rationale | No new convention. E is frame-independent, so Tithi and Karana match the USNO/NASA definition (apparent geocentric longitudes). Nakshatra then equals the chart by construction. Transitions are location-independent |
| Alternatives and risks | B topocentric Moon: up to about 1° in λ☾, so ends move by up to about 2 h; no published reference fits; new metadata. C tropical E: identical in theory, but a second code path that could diverge, and a tropical S would shift every Yoga by about 48° |
| Exact M1 scope | All M1 longitudes come from the existing SCI-01d call path, unchanged |
| Implementation consequence | `panchanga_astro` calls the existing engine longitude function. No new Swiss flag |
| Required independent QA | C3 conformance (PAN-D15-b); Nakshatra identity with the chart (PAN-QA-08); a mutation test that a tropical S fails |
| Owner options | **D01-A** reuse SCI-01d · D01-B topocentric · D01-reject |

### PAN-D02: Which Panchanga to output

| | |
|---|---|
| Existing proposal | §5.8: A, birth-time primary plus a separate daily Panchanga |
| Recommended | **D02-M1**: approve the birth-time Panchanga only, for M1. The daily Panchanga is neither approved nor rejected; it stays with PAN-D02 for a later milestone |
| Rationale | The daily object needs sunrise (PAN-D03, still without a recommendation) |
| Alternatives and risks | D02-A in full now: approves a sunrise-dependent output with no sunrise convention. D02-B birth-time only, permanently: closes a product option early |
| Exact M1 scope | Birth-instant elements in §1 |
| Implementation consequence | No sunrise code. The contract has no `vara`, `sunrise`, `sunset` or `sunrise_day` field in M1 (absent, not `unavailable`) |
| Required independent QA | Contract test that no sunrise-dependent field exists |
| Owner options | **D02-M1** · D02-A full · D02-B birth-time only |

### PAN-D07: Karana names

| | |
|---|---|
| Existing proposal | §5.5, §5.5.1: A, index only until a verified primary source is adopted |
| Recommended | **A** |
| Rationale | The only secondary source read contradicts itself. The IMD list is reviewer-mediated, Stage C 0/46. The 60-position mapping still lacks verified Shakuni and Chatushpada rows |
| Alternatives and risks | B adopt the cyclic rule now: names may be wrong in a customer-visible field |
| Exact M1 scope | Output `karana.index` 1–60 only. The name field is absent, with reason `PANCHANGA_METHOD_NOT_ADOPTED` |
| Implementation consequence | No Karana name table in code |
| Required independent QA | Contract test: no Karana name string anywhere in M1 output or code tables |
| Owner options | **D07-A** · D07-B |

### PAN-D08: Boundary rule

| | |
|---|---|
| Existing proposal | §5, §7: A, half-open, exact, on unrounded values (same as the chart, SCI-01f) |
| Recommended | **A** |
| Rationale | Same rule as the approved chart, so Nakshatra identity holds by construction. A tolerance band would create two answers for one instant |
| Alternatives and risks | B tolerance band: non-deterministic edge, conflicts with SCI-01f |
| Exact M1 scope | `sector(x, n)` on the exact binary value for E (30, 60), S (27) and λ☾ (27, 108). A value exactly on an edge belongs to the higher sector. A raw negative difference is reduced by adding 360 exactly |
| Implementation consequence | Reuse the canonical `rules._sector` helper |
| Required independent QA | PAN-SPEC-01 to 05 with an independently coded rational oracle; the 0/360 wrap |
| Owner options | **D08-A** · D08-B |

### PAN-D09: Precision and display

| | |
|---|---|
| Existing proposal | §7: A, converge ≤ 0.5 s; machine output UTC to the second; local display to the minute; flag births within ±2 min of a transition |
| Recommended | **D09-A-M1**: approve convergence ≤ 0.5 s and machine output in UTC to the whole second. **Defer** the local display rule and the ±2 min flag, because M1 has no display, and the flag would be an extension of SCI-06, which covers six chart items only |
| Rationale | Separates C1 (convergence) from display. Does not silently extend SCI-06 |
| Alternatives and risks | D09-A in full: approves a display and a near-boundary flag with no wording, no report task and no SCI-06 extension decision |
| Exact M1 scope | Every transition instant is the first whole second at which the new sector holds, from a bracket ≤ 0.5 s, as ISO 8601 UTC with `Z` |
| Implementation consequence | No local-time rounding code in M1. Local rendering is limited to what PAN-D13 allows, as machine data |
| Required independent QA | PAN-QA-03 (bracket width, caps); rounding direction test at a synthetic crossing |
| Owner options | **D09-A-M1** · D09-A full · D09-modify |

### PAN-D10: Numerical method

| | |
|---|---|
| Existing proposal | §5.7: A, TS-1 bounded bisection (optional TS-2), `FLG_SWIEPH` checked on every call, no `swe_mooncross_ut` |
| Recommended | **A, TS-1 only for M1.** TS-2 acceleration is not needed for performance today and adds a second code path |
| Rationale | Monotonicity of E, S and λ☾ guarantees a unique crossing per bracket. About 18 bisections from 1.5 days to 0.5 s. `swe_mooncross_ut` has an unbounded loop and no ephemeris-flag check in 2.10.03 |
| Alternatives and risks | TS-2: fewer calls, more code, finite-difference speeds. TS-3 Swiss crossing functions: no E/S support, unbounded loop |
| Exact M1 scope | Step 6 h from the birth instant until the sector changes, ≤ 2.5 days each way; bisect ≤ 64 iterations to ≤ 0.5 s; never extrapolate |
| Implementation consequence | `panchanga_search` module, pure apart from the injected longitude function |
| Required independent QA | PAN-SPEC-06, -14; forced iteration cap 1 → `PANCHANGA_TRANSITION_NOT_CONVERGED`; bracket without a sector change; non-finite input |
| Owner options | **D10-A (TS-1 only)** · D10-A with TS-2 · D10-B |

### PAN-D12: Output contract and version

| | |
|---|---|
| Existing proposal | WP-B2 §3, §5, §8: A, separate `sabpuja-panchanga/1` document with its own metadata |
| Recommended | **A** |
| Rationale | Chart schema 0.3.0 and metadata `/3` stay byte-identical. Panchanga can evolve without re-validating the chart |
| Alternatives and risks | B chart 0.4.0: new compatibility evidence and a change to the canonical chart contract |
| Exact M1 scope | A JSON document `sabpuja-panchanga/1` with method id and version (`KUN-PAN-M1`, SCI-PAN-01 rev 0.5 plus these decisions), the Swiss version and ephemeris manifest hash, and the M1 elements only |
| Implementation consequence | New contract module; chart code untouched |
| Required independent QA | PAN-QA-08 byte identity of chart 0.3.0 with and without a Panchanga call in the same process |
| Owner options | **D12-A** · D12-B |

### PAN-D13: Instants outside the SCI-03 envelope

| | |
|---|---|
| Existing proposal | §7, PAN-SPEC-12: A, always report UTC; withhold local rendering for instants before 1970-01-01 local or after 2100-12-31 local |
| Recommended | **A** |
| Rationale | A Tithi of a 1970-01-01 00:30 birth can start in 1969, where offsets are `HISTORICAL_CLOCK_UNVERIFIED`. The UTC instant is still sound |
| Alternatives and risks | B render with unverified offsets: silent historical-clock error. C refuse: loses a correct result |
| Exact M1 scope | Birth instants are validated exactly as for the chart (same refusals, same order). Transition instants outside the envelope carry UTC and a flag `local_rendering: withheld_outside_envelope` |
| Implementation consequence | No new tzdata logic; a bounds check before local rendering |
| Required independent QA | PAN-SPEC-12 |
| Owner options | **D13-A** · D13-B · D13-C |

### PAN-D14: Reference hierarchy

| | |
|---|---|
| Existing proposal | §7: A, IMD for Panchanga conventions; USNO/NASA for ayanamsa-free events and SUN-A; Swiss documentation for behaviour only; no commercial websites |
| Recommended | **D14-A-M1**: adopt A, noting that for M1 the only external reference used is USNO/NASA phase events. IMD is not used in M1 |
| Rationale | Keeps commercial Panchang sites out of ground truth |
| Alternatives and risks | B commercial websites: unknown methods and ayanamsa |
| Exact M1 scope | PAN-REF-PHASE-2026 (after independent recheck) for C2; Swiss for C3 |
| Implementation consequence | None in code; fixture provenance fields cite the source ids |
| Required independent QA | Fixture provenance check |
| Owner options | **D14-A-M1** · D14-A · D14-B |

### PAN-D15: Tolerances (split into parts)

Full evaluation: [PAN-D15-TOLERANCE-EVALUATION.md](PAN-D15-TOLERANCE-EVALUATION.md).

| Part | Recommended | Status |
|---|---|---|
| **D15-a phase-event window (C2)** | [M_min − 60 s, M_max + 60 s], closed, unchanged from the fixture; residuals reported; `NEAR_WINDOW_EDGE` within 10 s listed for QA; applies only to independently rechecked events | Needed now |
| **D15-b Panchanga Swiss conformance (C3)** | 1e-8° engine and 1e-9° binding vs `swetest` for λ☉ and λ☾ (values unchanged, new scope); 2e-8° for E and S; identical indices with BOUNDARY-INDETERMINATE inside tolerance; ≤ 1.0 s transition agreement with an independent oracle | Needed now. **SCI-05 does not cover this**; it is a separate scope approval |
| D15-c convergence (C1) | ≤ 0.5 s, decided under PAN-D09 | Cross-reference |
| D15-d IMD, sunrise | — | Deferred |

| | |
|---|---|
| Alternatives and risks | Windows A1 to A3 in the evaluation §2.4. For D15-b, a separate tighter tolerance would need new evidence and gives no extra assurance, because both sides are Swiss |
| Implementation consequence | A test-side tolerance file committed and hashed before any run |
| Required independent QA | Commit order (tolerance before run); hash of the tolerance file cited in the run report |
| Owner options | **D15-a-R** · D15-a-A1 · D15-a-A2 · D15-a-A3; **D15-b-R** · D15-b-modify · D15-b-reject |

### PAN-D16: Names and localisation

| | |
|---|---|
| Existing proposal | §7: A now (engine Nakshatra names; Appendix A English for Yoga, Tithi, Karana; Hindi pending OD-08), B once IMD is captured. The M1 milestone recommends indices only |
| Recommended | **D16-M1-INDEX**: M1 emits indices and machine ids only: Tithi number, `paksha` as `shukla` / `krishna`, Paksha day, Karana index, Yoga index. Nakshatra uses the chart's existing identifier unchanged (it is already in schema 0.3.0). No Tithi, Yoga or Karana name strings, English or Hindi. The full D16 choice stays open |
| Rationale | No name ships before OD-08 Hindi review and before a primary Yoga list is transcribed. M1 has no customer surface |
| Alternatives and risks | D16-A now: ships an English Yoga list resting on one secondary source |
| Exact M1 scope | As above |
| Implementation consequence | No name tables in the M1 code |
| Required independent QA | Contract test that the only name strings are the chart's Nakshatra identifiers |
| Owner options | **D16-M1-INDEX** · D16-A · D16-B |

### PAN-D18: Tithi numbering

| | |
|---|---|
| Existing proposal | §5.1: A, output both 1–30 and Paksha + day 1–15 |
| Recommended | **A** |
| Rationale | Both forms are used; deriving one from the other in the report layer invites inconsistency |
| Alternatives and risks | One form only: later report code would compute the other |
| Exact M1 scope | `tithi.number` 1–30; `tithi.paksha` `shukla` for 1–15, `krishna` for 16–30; `tithi.paksha_day` = ((n − 1) mod 15) + 1 |
| Implementation consequence | Pure rule function |
| Required independent QA | Oracle over all 30 values |
| Owner options | **D18-A** · D18-B |

### PAN-D20 (scoped): May M1 proceed without IMD?

| | |
|---|---|
| Existing proposal | §7: A, WP-B2 BLOCKED until IMD conventions and §8.1 coverage are verified. The M1 milestone adds a scoped question |
| Question for the owner | May the sunrise-independent Panchanga M1 proceed using the independently checked USNO/NASA phase references and Swiss conformance, while sunrise-dependent work remains blocked until the IMD reference verification gates are satisfied? |
| Recommended | **D20-M1-SCOPED: yes, with conditions.** (1) Only the M1 scope in §1. (2) The 50 phase events count only after the independent recheck in [PHASE-EVENT-VERIFICATION.md](PHASE-EVENT-VERIFICATION.md) §6, done by someone other than Claude; unchecked events are excluded. (3) D15-a and D15-b are approved and committed before any run. (4) Claims are limited to: Tithi and Karana transitions at E = 0°, 90°, 180°, 270° agree with USNO/NASA within the declared window; everything else is rule-oracle plus Swiss-on-Swiss. (5) No customer-facing output, report or name. (6) Everything sunrise-dependent, and any IMD-based claim, stays BLOCKED (original D20-A) |
| Rationale | Tithi and Karana are ayanamsa-free, so USNO/NASA are direct references for four angles. Nakshatra is already chart-verified. Yoga uses the same two longitudes as the chart. Nothing in M1 depends on the IMD facts that are still unverified (sunrise, rounding, ayanamsa wording, names) |
| Alternatives and risks | D20-A keep all of WP-B2 blocked: safest, but no Panchanga progress until IMD Stage C/D, which has no date. D20-B unscoped: would let sunrise and Yoga/Nakshatra end-time claims rest on Swiss-on-Swiss only, which REL-01 does not treat as independent |
| Residual risk of the recommendation | Yoga and Nakshatra end times have no external reference. An error common to Swiss and the engine (for example a wrong ayanamsa convention) would not be caught by C3. It is mitigated by SCI-01a being canonical and by the chart's own gold validation, not eliminated |
| Exact M1 scope | §1 |
| Required independent QA | ChatGPT confirms the claim boundary in the PR, run report and any document |
| Owner options | **D20-M1-SCOPED** · D20-A (stay blocked) · D20-B (unscoped) |

## 3. Decisions that stay deferred (no answer needed now)

| ID | Topic | Why it can wait |
|---|---|---|
| PAN-D03 | Sunrise convention | No sunrise in M1. Still no recommendation (IMD SUN-D unverified) |
| PAN-D04 | Sunrise parameters | Follows D03 |
| PAN-D05 | Vara boundary | Needs sunrise |
| PAN-D06 | Sunrise-day element rule | Needs sunrise |
| PAN-D11 | Undefined sunrise | Needs sunrise |
| PAN-D17 | Sunset | Needs sunrise |
| PAN-D19 | Masa, Samvat | Out of scope |
| D02 (daily part), D09 (display and ±2 min flag), D14 (IMD part), D15-d, D16 (names) | Remainders of decisions approved only for M1 above | Need sunrise, IMD, OD-08 or report work |
| SCI-06 extension | Birth-time sensitivity for Panchanga end times | Separate owner decision if ever wanted; not assumed |
| OD-09 | Merge plan for the draft stack | Not a Panchanga method decision, but it gates the engineering base (ENGINEERING-SPEC §1) |

## 4. One-line summary of recommendations

D01-A · D02-M1 · D07-A · D08-A · D09-A-M1 · D10-A (TS-1 only) · D12-A · D13-A · D14-A-M1 · D15-a-R · D15-b-R · D16-M1-INDEX · D18-A · D20-M1-SCOPED.

## 5. Owner approval fields (to be filled by the owner, not by Claude or ChatGPT)

| Field | Value |
|---|---|
| Reviewed packet SHA | |
| Selections (codes) | |
| Modifications | |
| Date (Asia/Kolkata) | |
| Where recorded (link) | |
| Pre-merge record PR | |
| Post-merge adoption receipt | |
