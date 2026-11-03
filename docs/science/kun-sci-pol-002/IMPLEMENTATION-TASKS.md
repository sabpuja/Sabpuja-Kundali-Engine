# Proposed implementation tasks for SCI-04 (B-1), SCI-05 (B-3) and SCI-06 (B-6)

**PROPOSAL ONLY. No task below is authorized.** Each one needs a numbered, bounded task from ChatGPT, owner authorization and its own draft PR. Each one also depends on the decision records in [DECISION-RECORDS.md](DECISION-RECORDS.md) having become canonical. The order is:
1. The pre-merge records in this decision-record PR (step 1, done).
2. A separately owner-authorized merge of this decision-record PR into `main` (step 2a).
3. A post-merge adoption receipt giving the merge SHA and date (step 2b).

Only the **implementation** PRs below wait for step 2b. Nothing in this document authorizes the merge of the decision-record PR itself; that remains the owner's separate decision.

## 0. Constraint every task inherits: the engine base

`main` (`1d4bcb6`) holds documentation and research only. The engine, the tests and the gold runner all live on the unmerged draft stack:

| Branch | PR | Holds |
|---|---|---|
| … → `feat/kun-ux-name-001-report-full-name` | #58 (draft) | Engine at schema 0.3.0, report renderer, private preview |
| `test/kun-sci-gold-001-golden-reference` | #62 (draft, QA PASS at `6722b5c`), base #58 | `tests/sci_gold/` gold runner, receipts, matrix |

This leaves two options:
- Every task stacks on a named exact SHA of that stack, as PR #62 does.
- The owner first decides the OD-09 merge plan for the stack.

PR #1 stays on HOLD and is not a base. Each task must state its base SHA, and must not rebase or rewrite another PR's branch.

## 1. KUN-SCI-IMPL-B1: score LAGNA-F at 1e-9° (test-only)

| | |
|---|---|
| Decision | SCI-04 |
| Base | PR #62 head `6722b5c46c3fb510495d8587b7b613f32691d97a`, as a new stacked branch. PR #62 itself stays at its QA-passed head |
| Changes | `tests/sci_gold/run.py` `lagna_formula_layer`: classify PASS when the difference is ≤ 1e-9°, FAIL when it is above, BOUNDARY-INDETERMINATE when the swetest Lagna lies within 1e-9° of a category edge. Do this only for \|lat\| ≤ 66.0°; outside that band the row stays BLOCKED (the engine already refuses such charts). Record the tolerance in a new test-side file, for example `tests/sci_gold/receipts/lagna-formula-tolerance.json`, carrying the value, its basis, the SCI-04 record link and the approving merge SHA. Add the file to `SHA256SUMS` and `PINS.json`. The frozen KUN-01-SWISS-01 `spec.json` is not edited |
| Must not change | Engine, schema 0.3.0, report, fixtures, the matrix, the Swiss tolerances, other layers' classification |
| Tests | All 50 LAGNA-F rows PASS. Mutation FAILs on a western root, an ayanamsha sign error, mean instead of true obliquity, and an offset of 2 × tolerance. A synthetic envelope case at lat ±66.0° with ARMC near 90° or 270°, with its difference recorded and no claim that it bounds every chart. GOLD-E01 and every other row are unchanged. A missing or unverified tolerance file gives BLOCKED, not FAIL (the KUN-SCI-GOLD-001A/B fail-closed rule) |
| Evidence | Full suite, D3 conformance and the live gold run on the exact SHA, plus raw logs, hashes and a before/after verdict diff. Then independent QA |
| QA links | KUN-F04, KUN-F16; QA-009, QA-010, QA-012 (per REL-01) |
| Risk / rollback | Test-only. Revert the commit and LAGNA-F returns to BLOCKED |

## 2. KUN-SCI-IMPL-B3: cite the scope extension in the gold runner (test-only)

| | |
|---|---|
| Decision | SCI-05 |
| Base | The same stacked branch as B1, or a sibling on `6722b5c` |
| Changes | Replace PR #62's "reused by reference, without scope approval" note with a citation of the SCI-05 record and its adoption merge SHA, in the run report metadata and the gold README. The tolerance values and their source stay `spec.json` `642a770d…`. No value changes |
| Tests | No new numerical tests. A rerun on the exact SHA must still give 500 SWISS-CONFORMANCE PASS and 1 BOUNDARY-INDETERMINATE (GOLD-E01). A unit test checks that the cited spec hash equals the pinned one |
| Evidence | The gold report on the exact SHA, with a diff that shows only the citation metadata changed |
| Risk / rollback | Documentation-level change inside the tests. Revert to restore |

B1 and B3 can be a single PR if ChatGPT prefers that. They are listed apart so that each decision has its own evidence.

## 3. KUN-SCI-IMPL-B6: birth-time sensitivity disclosure (four tasks, in order)

The calculated classifications never change. The tasks are split so that the ENG gate (calculation) and the RPT gate (report wording) stay separate.

| Task | Content | Gate | Depends on |
|---|---|---|---|
| **B6a: sensitivity computation** | A new, versioned pure function. For each of the six items (Lagna Rashi, Lagna Navamsa, Moon Rashi, Navamsa, Nakshatra, Pada) it gives the signed time to the nearest change before and after the birth instant, the neighbouring category, and whether \|Δt\| ≤ 120 s. It uses bracketing and bisection on the canonical SCI-01d/SCI-01e calls under the Swiss lock, with `FLG_SWIEPH` checked on every call and no Moshier fallback. It reports its own time resolution: a result finer than the float64 JD spacing (about 4e-5 s) is `RESOLUTION_LIMITED`, never a measured time. Exact-edge numerical cases (within 1e-9°) are flagged separately | ENG | Engine base SHA (§0); SCI-06 adopted |
| **B6b: output contract** | Owner choice between an additive field in a new chart schema version (proposed 0.4.0) and report-only metadata. Schema 0.3.0 and metadata `/3` stay byte-identical. This is its own small owner decision, with a proposal, before B6a output is wired | Owner decision, then ENG | B6a |
| **B6c: report and UI** | Option 1 note lines next to the affected items, the near-exact-boundary note, and the optional Option 2 premium appendix page, in EN and HI. Catalogue keys added; no existing key changed. Placeholders only until wording is approved | RPT | B6a, B6b |
| **B6d: wording approval** | Human Hindi editorial review, Jyotish terminology review and owner copy sign-off of the PR #63 B-6 §5 drafts. Not a Claude task: Claude prepares the review packet in the PR #61 style | Editorial + owner | None (can start now as documentation) |

**B6a tests.** Independent bisection on swetest values at designed boundary pairs, with a time tolerance stated in seconds. Trigger exactly at 120 s and not at 121 s, before and after the birth instant, for the Lagna at low latitude and at ±66.0° and for the Moon. GOLD-E01 gives the exact-boundary flag and keeps Simha, Mesha, Magha 1. Byte-identical classifications and degrees on all 50 gold charts. No birth data in logs. Determinism across runs.

**B6c tests.** EN/HI key parity, PDF fidelity and an accessibility check of the note placement, plus Gate RPT sign-off. The wording stays placeholder text until B6d completes.

## 4. Proposed order

1. B6d review packet (documentation; can run in parallel with everything else).
2. B1 + B3 (test-only, smallest, on `6722b5c`).
3. B6a (ENG), then the B6b owner decision.
4. B6c (RPT), once B6d wording is approved.

None of this lifts the PR #1 HOLD, and none of it changes the production NO-GO.
