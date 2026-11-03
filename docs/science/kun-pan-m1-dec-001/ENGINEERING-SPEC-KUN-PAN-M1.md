# KUN-PAN-M1: Panchanga birth-instant calculation engine (bounded specification)

**PREPARED, NOT EXECUTED. Not authorized.** Engineering starts only after the blockers in §10 are cleared and ChatGPT issues a numbered task. Option codes refer to [DECISION-PACKET.md](DECISION-PACKET.md) and assume its recommendations; if the owner picks otherwise, this spec is revised first.

## 1. Base SHA strategy

`main` (`de721d665ed80ed58291f59962677065a73f0b26`) has documentation and research only. The engine lives on the unmerged draft stack:

| Candidate base | Head | Tree | Holds |
|---|---|---|---|
| PR #58 `feat/kun-ux-name-001-report-full-name` | `fde3ec670618a02f2b913e9bbbedd1521d3840c7` | `da8112a1788f16c3f2f5ab94d46278d279c09278` | Engine (`src/sabpuja_kundali/`, schema 0.3.0), report, preview |
| **PR #62 `test/kun-sci-gold-001-golden-reference`** (on #58) | `6722b5c46c3fb510495d8587b7b613f32691d97a` | `84816a56f388ac5e07bae3f63e24740b191da96c` | The above plus `tests/sci_gold/` (gold matrix, `swetest` harness, receipts); independent QA PASS 5747720823 |

**Recommended:** a new branch `feat/kun-pan-m1-birth-instant` stacked on PR #62 head `6722b5c`, because M1's C3 conformance reuses the gold matrix instants and the existing `swetest` harness. The KUN-SCI-IMPL-B1/B3 branches, if they exist by then, are siblings and are not needed.

Rules:
- The owner decides OD-09 (stack merge plan) or explicitly authorizes stacking on `6722b5c` first. PANCHANGA-M1-MILESTONE §5 item 4 forbids stacking on an unresolved branch without that plan.
- No rebase or rewrite of any other PR's branch. PR #1 HOLD stays; PR #1 is not a base.
- The PR records base SHA and tree, and the diff is checked to touch only the paths in §2.
- If the stack moves before engineering starts, the base is re-chosen explicitly, never silently.

## 2. Change boundary

| May add | Must not change |
|---|---|
| `src/sabpuja_kundali/panchanga/` (`rules.py`, `search.py`, `contract.py`, `astro.py`) | `engine.py`, `rules.py`, `ephemeris.py`, `provenance.py` behaviour; chart schema 0.3.0; metadata `/3` |
| A CLI subcommand or separate entry point for Panchanga JSON, if the task asks for one | The existing chart CLI output and error contract |
| `tests/panchanga/` (oracles, fixtures, tolerance file, runner) | The gold matrix, receipts, `spec.json`, D1/D9 reference data |
| | Report renderer, PDF, Hindi catalogue, private preview, Shopify, DNS, CI |

## 3. Reuse of canonical Swiss calculations

- Sun and Moon longitudes come only from the existing SCI-01d function (`calc_ut(jd_ut, body, FLG_SWIEPH | FLG_SIDEREAL)`), under the existing Swiss lock, with the existing per-request reset of sidereal mode and ΔT (SCI-01a, SCI-01h).
- The returned flag is checked for `FLG_SWIEPH` on every call, including every bisection step. A missing flag gives the existing ephemeris refusal. **No Moshier or JPL fallback, no unverified files**: the pinned ephemeris manifest check runs exactly as for the chart.
- No `swe_mooncross_ut`, `swe_solcross_ut`, `swe_rise_trans`, `swe_set_topo` or `FLG_SPEED`.
- UTC is passed as UT1 (SCI-01h) and disclosed in the metadata.

## 4. Rule oracles (`panchanga/rules.py`, pure)

With E = (λ☾ − λ☉) mod 360 and S = (λ☉ + λ☾) mod 360 on unrounded floats, and `sector` the canonical half-open helper:

| Element | Rule |
|---|---|
| Tithi | n = sector(E, 30) + 1; paksha `shukla` if n ≤ 15 else `krishna`; paksha_day = ((n − 1) mod 15) + 1 |
| Karana index | sector(E, 60) + 1, 1..60; no name (D07-A) |
| Yoga index | sector(S, 27) + 1, 1..27 |
| Nakshatra, Pada | Delegates to the chart's Nakshatra rule (sector(λ☾, 108)); same identifiers |

The **test oracle** is independent code in `tests/panchanga/` using exact rational arithmetic (`fractions.Fraction` of the binary float), not the production helper.

## 5. Boundary bracketing and bisection (`panchanga/search.py`)

For f ∈ {E, S, λ☾} and sector width w:
1. k = sector of f(t_birth). Start target k·w, end target (k + 1)·w, with the 0/360 wrap handled by working on the unwrapped increment from t_birth.
2. Step ±6 h until the sector index changes; cap ±2.5 days.
3. Bisect to a bracket ≤ 0.5 s, ≤ 64 iterations.
4. Output the first whole UTC second at which the new sector holds.
5. Any cap reached, no sector change, or a non-finite value → `PANCHANGA_TRANSITION_NOT_CONVERGED`. Never extrapolate.

Monotonicity of E, S and λ☾ (SCI-PAN-01 §3) makes each bracket contain exactly one crossing.

## 6. Typed errors and refusal order

- Existing chart validation runs first, in its canonical order (birth time, offset, historical clock, coordinates, latitude band, ephemeris).
- Then Panchanga codes: `PANCHANGA_TRANSITION_NOT_CONVERGED` (whole document refused) and `PANCHANGA_METHOD_NOT_ADOPTED` (field omitted with reason, not an error). No sunrise codes in M1.
- Error output follows the existing CLI contract (JSON error, exit 2, fixed message, no traceback).

## 7. Privacy-safe logging

No birth date, time, place, coordinates, name or computed instant appears in logs, error messages or exceptions. Logs may carry request-independent facts only (method version, ephemeris manifest hash, error code). Tests assert this by scanning captured logs and error output for the synthetic inputs.

## 8. Fixtures and tolerance file

| Set | Use | Precondition |
|---|---|---|
| PAN-REF-PHASE-2026 (50) | C2 window (D15-a) | Independent recheck (PHASE-EVENT-VERIFICATION §6); only rechecked ids listed in the tolerance file |
| KUN-SCI-GOLD-001 instants (50) | C3 conformance and C1 at real birth instants | Already hashed in PR #62 |
| PAN-DER-07, -08 | Civil-date rollover, post-midnight Karana | Existing derived set |
| PAN-SPEC-01 to 06, 08 to 10, 12 to 15 | Specifications | Existing |
| `tests/panchanga/tolerances.json` | D15-a, D15-b values, decision record link, adoption merge SHA, list of rechecked case ids | **First commit of the branch, before any run** |

All new fixture instants are synthetic or already public; no customer data.

## 9. Gates and tests

### ENG gate (scientific), all on the exact SHA with raw logs

| ID | Test |
|---|---|
| PAN-QA-01 | Rule oracles, exact half-open edges, 0/360 wrap (SPEC-01 to 05) |
| PAN-QA-03 | Convergence ≤ 0.5 s, caps, typed refusal (SPEC-06, -14) |
| PAN-QA-04 | 50 phase events inside the D15-a window, indices right at ±1 s, residuals and `NEAR_WINDOW_EDGE` reported. Reported as "inside the declared window" only |
| PAN-QA-07 | D15-b Swiss conformance on all instant sets |
| PAN-QA-08 | Chart 0.3.0 byte identity with and without a Panchanga call; Nakshatra identity; metadata `/3` unchanged |
| PAN-QA-09 | Refusal order and codes; no birth data in errors or logs |
| PAN-QA-10 | Determinism across runs, processes and locales; Swiss state isolation (SPEC-15) |
| Regression | Full existing suite (chart, gold, Swiss conformance) unchanged and passing on the same SHA, in pinned-data, unset and wrong-path modes, as in earlier tasks |
| Mutation | Tropical S, sign error in E, closed instead of half-open edge, missing `FLG_SWIEPH` check, extrapolation: each must fail |

### RPT gate (premium report), separate and later

Not part of KUN-PAN-M1. Any Panchanga line in the PDF or browser needs PAN-D16 names, OD-08 Hindi review, owner copy approval and its own RPT task. M1 produces machine JSON only.

## 10. Blockers before engineering starts

| # | Blocker | Owner of the action |
|---|---|---|
| 1 | Owner selections for the 13 decisions in DECISION-PACKET §2, then merge and adoption receipt | Owner, then ChatGPT/Claude record |
| 2 | Independent recheck of the 50 phase events (not by Claude) | ChatGPT QA or a human verifier |
| 3 | OD-09 merge plan, or explicit owner authorization to stack on PR #62 `6722b5c` | Owner |
| 4 | A numbered, bounded KUN-PAN-M1 task from ChatGPT with KUN-A01 and QA links | ChatGPT |
| 5 | `swetest` 2.10.03 and the pinned ephemeris files available in the test environment, as for KUN-01-SWISS-01 | Already available in earlier tasks; re-confirmed at the start |

No method blocker remains for M1 if the recommendations are accepted. The evidence blocker is item 2. Known evidence gaps that do not block M1 but limit its claims: no external Yoga or Nakshatra end-time reference; only 4 of 60 Karana angles and 2 of 30 Tithi angles externally referenced; no source rounding rule.

## 11. Proposed sequence

1. Owner decisions (this packet) → pre-merge record → merge → adoption receipt.
2. Independent phase-event recheck, in parallel with step 1.
3. OD-09 decision or stacking authorization.
4. ChatGPT issues KUN-PAN-M1.
5. Branch on the base; first commit = tolerance file with rechecked ids.
6. Rule oracles and contract, then search, then astro wiring.
7. ENG run on the exact SHA; evidence; draft PR; independent QA.
8. Later and separate: RPT task, names, sunrise milestone after IMD gates.
