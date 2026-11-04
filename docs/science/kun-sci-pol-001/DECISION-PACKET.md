# KUN-SCI-POL-001 owner decision packet: B-1, B-3, B-6

**All three items: PENDING OWNER APPROVAL.** Nothing in this packet is frozen, approved or implemented. Each proposed value and each piece of wording is a recommendation only. Once ChatGPT has reviewed the packet independently, the owner chooses by filling in the forms in §4. Adoption then follows the two-step rule in `docs/DECISIONS.md`: an approval record first, then an authorized register merge.

Evidence base:
- PR #62 head `6722b5c46c3fb510495d8587b7b613f32691d97a`, tree `84816a56f388ac5e07bae3f63e24740b191da96c`. Independent QA passed in review [5747720823](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/62#pullrequestreview-5747720823). The PR is draft and unmerged.
- Gold report `sci-gold-6722b5c46c3f.json`, sha256 `edb8aab5459a326b57b4abcffc7e8f44a79be2a966baf549e97162d8d4e24bef`.
- Analysis in [`analysis/results.json`](analysis/results.json).

## 1. B-1: Lagna formula tolerance ([detail](B1-LAGNA-FORMULA-TOLERANCE.md))

| | |
|---|---|
| Existing approved method | SCI-01e: Lagna = `houses_ex(…, b"W", FLG_SIDEREAL)` `ascmc[0]`. REL-01 makes an independent formula check mandatory. **No tolerance is frozen**, so LAGNA-F is BLOCKED on all 50 charts |
| Evidence | \|formula − swetest\|: max 4.33e-11°, median 2.5e-12°. Consistent with swetest print quantisation (at most 0.80 of each chart's bound); no discrepancy is resolved at that precision. float64 error at most 9e-14°. The worst-case bound inside \|lat\| ≤ 66° is estimated at 4.8e-10° from a sampled grid sweep (not a certified supremum). The smallest realistic defect (mean instead of true obliquity) is 1.1e-7° |
| Recommended | **1e-9°**, fixed, for the whole canonical envelope |
| Alternatives | 5e-10° (no margin), 1e-10° (false FAILs above about 64°), adaptive 2× per-chart bound (complex), 1e-8° (10× defect margin), status quo (unscored) |
| Implementation | Test-only: LAGNA-F classifies against the value. No engine, schema or report change |
| Tests after approval | 50 PASS. Mutation FAILs (western root, ayanamsha sign, mean obliquity). A ±66° envelope case. Full suite, D3 and live gold run, then independent QA |

## 2. B-3: Applying the frozen Swiss tolerances to the gold matrix ([detail](B3-SWISS-TOLERANCE-APPLICABILITY.md))

| | |
|---|---|
| Existing approved method | `engine_vs_swetest` 1e-8° and `binding_vs_swetest` 1e-9°, **frozen for the KUN-01-SWISS-01 SC cases** (`spec.json` `642a770d…`). PR #62 reuses them by reference, without any scope approval |
| Evidence | 500/500 engine values are exactly the 8-decimal rounding of swetest. Max \|d\| = 4.999992e-9° = 0.50 × tolerance, against a theoretical 5.005e-9°. Only GOLD-E01 lies within 1e-9° of an edge. The next nearest is at 2.4e-4°, so any band from 7.1e-10° to 2.4e-4° gives the same classifications. Coverage is wider than the SC cases: ±66°, 10 zones, 20 boundary pairs |
| Recommended | **Reuse both values unchanged**, recorded as an explicit **scope extension** to the KUN-SCI-GOLD-001 matrix. This is not a new tolerance |
| Alternatives | Reuse and amend the basis text (needs QA). Tighten to about 5.1e-9° (fragile). Separate gold tolerances (no gain). Do not approve (the SWISS rows cannot count) |
| Implementation | Register entry only. No code, schema or report change |
| Tests after approval | None new. A rerun on the approving SHA must confirm 500 PASS and 1 BOUNDARY-INDETERMINATE |

## 3. B-6: Near-boundary disclosure ([detail](B6-NEAR-BOUNDARY-DISCLOSURE.md))

| | |
|---|---|
| Existing approved method | SCI-01f half-open classification on unrounded values. **No disclosure policy exists.** GOLD-E01 is BOUNDARY-INDETERMINATE on 6 comparisons, while engine and reference agree |
| Evidence | Numerical indeterminacy is below 1e-9°. It occurs only in the designed exact-edge fixture, where the crossing is well below one second and its exact time is unresolved at float64 JD precision. Birth-time sensitivity is much larger. In an illustrative synthetic sample of 20,000 charts (not a population prevalence), a 2-minute birth-time error changes the Lagna Navamsa in 29%, the Lagna Rashi in 3.5%, the Moon Pada in 1.1% and the Moon Nakshatra in 0.3% |
| Recommended | **Option 1**: show the calculated result, with a short birth-time note when an item changes within **W = 2 min**, plus an exact-boundary note. Option 2's longer explanation goes in an optional premium appendix. Option 3 (withhold) is not recommended |
| Alternatives | Option 2 alone (more text). Option 3 (withhold: about 29% of Lagna Navamsas at W = 2). W = 1 or 5 min |
| Implementation | A new versioned sensitivity computation, an additive schema field (a new version; 0.3.0 unchanged), EN/HI renderer and catalogue entries. Each is a separate authorized task through the ENG and RPT gates |
| Tests after approval | Bracketing and bisection against independent swetest bisection. Trigger exactly at W in both directions, at low latitude and at ±66°. GOLD-E01 exact-boundary text. Byte-identical classifications. EN/HI parity. PDF fidelity. Hindi editorial and owner copy sign-off |

## 4. Owner decision forms

Tick one box per item. "Approve" means approval of the stated scope only. It does not authorize a merge, a deployment or a release.

**Form B-1: Lagna formula tolerance**
- [ ] Approve R: freeze LAGNA-F tolerance = **1e-9°** for \|lat\| ≤ 66.0°
- [ ] Approve alternative: ______ (A1 5e-10° / A2 1e-10° / A3 adaptive / A4 1e-8°)
- [ ] Keep unscored (A5): LAGNA-F stays BLOCKED
- [ ] Defer, with this question for QA: ______

Owner: ______ Date: ______ Link to record: ______ SHA reviewed: ______

**Form B-3: Swiss tolerance applicability**
- [ ] Approve R: reuse `engine_vs_swetest` 1e-8° and `binding_vs_swetest` 1e-9° **unchanged** for the KUN-SCI-GOLD-001 matrix (scope extension only)
- [ ] Approve A1: reuse and amend the recorded basis text
- [ ] Approve alternative: ______
- [ ] Do not approve: the SWISS rows remain unscored evidence

Owner: ______ Date: ______ Link to record: ______ SHA reviewed: ______

**Form B-6: Near-boundary disclosure**
- [ ] Approve Option 1 with the optional Option 2 appendix, W = 2 min, for: Lagna Rashi, Lagna Navamsa, Moon Rashi, Navamsa, Nakshatra and Pada
- [ ] Approve Option 1 with W = ______ min, or for a different item list: ______
- [ ] Approve Option 2 only
- [ ] Approve Option 3 (withhold) for: ______
- [ ] Defer

Wording approval is separate and required. The drafts in B-6 §5 still need human Hindi and Jyotish editorial review.

Owner: ______ Date: ______ Link to record: ______ SHA reviewed: ______

## 5. Remaining blockers, unchanged by this packet
- DATA-01: historical civil-clock and birthplace verification. Pre-1970 dates stay refused.
- JPL/INPOP independent astronomy: optional and deferred (issue #15, OD-05). The ASTRO layer stays BLOCKED, and no independent-accuracy claim is possible.
- Hindi place coverage for 11 synthetic places (localization workstream).
- UX-01, UX-02, UX-03, SEC-01, LEG-01 and PERF-01 remain PENDING.
- PR #62 remains draft. PR #1 remains HOLD. **Production remains NO-GO.**
