# KUN-SCI-POL-002: Approval records for B-1, B-3 and B-6

**Status of all three records: OWNER SELECTED PRE-MERGE - CANONICAL ADOPTION PENDING.**

These are **step-1 pre-merge approval records** under the two-step rule in [`docs/DECISIONS.md`](../../DECISIONS.md#owner-pre-merge-selection-ledger). A record becomes OWNER APPROVED / CANONICAL only after step 2: an owner-authorized merge of this register amendment into `main`, followed by a post-merge adoption receipt that gives the merge SHA and date. A ChatGPT QA review alone never changes a status.

None of these records authorizes a code change, a merge, a deployment, a release or customer-facing copy. The English and Hindi wording in PR #63 B-6 §5 stays a **draft** that needs human Hindi and Jyotish editorial review and separate owner copy approval.

## 1. Provenance of the owner approval

The owner's choice is documented by three linked items. None of them is an independently authenticated owner signature on GitHub, and this record does not claim one.

| # | Item | What it is | What it is not |
|---|---|---|---|
| P1 | Owner statement in the owner's ChatGPT conversation, 2026-11-03 (Asia/Kolkata): **"i will go with your recommendation"**, given right after the three recommendations from PR #63 at `1b70927` were presented | The owner's decision, in the owner's words | Not visible on GitHub. Its wording is known only through P2 |
| P2 | [PR #63 comment 6598001352](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/63#issuecomment-6598001352), created 2026-11-03T07:32:47Z by the GitHub account `ubermensch-site` | ChatGPT's **transcription** of P1, with the selected options, their scope, conditions and limits | It says of itself that it is "a record/transcription of the owner's explicit chat approval by ChatGPT, not an independently authenticated GitHub owner signature". The same GitHub account is used by the connected tooling, so the GitHub author field does not identify the human owner |
| P3 | The owner's own task message **KUN-SCI-POL-002**, written by the owner (display name "Sabpuja") in the Sabpuja Kundali Engine Claude project chat, 2026-11-03T07:43:04Z | The owner, directly to Claude, names the three selections, calls P2 the "Owner approval record", and instructs Claude to prepare these records. Claude transcribes it on this PR (see the PR description) | Not a GitHub record. Claude's transcription is not an owner signature either |

**Reading.** P3 is the owner's own direct confirmation of the selections transcribed in P2. Together they satisfy the step-1 contents the register requires (choice, date, approval link, scope, reviewed SHA). This follows the precedent of SCI-02 C2, where the owner decided in the project conversation and Claude recorded the decision at the owner's instruction.

**Optional strengthening, not required by the register procedure.** If the owner wants a GitHub-native signature, the owner can add a one-line comment on this PR from a GitHub account that only the owner controls, for example "Approve SCI-04, SCI-05 and SCI-06 as recorded at <SHA>". Claude and ChatGPT will not write such a comment on the owner's behalf.

## 2. Reviewed evidence

| Item | Value |
|---|---|
| Decision package | Draft PR [#63](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/63), head `1b70927bed1e040f55441b5b710600ae6fe11216`, tree `c3f86350e888adf2993726bcddf3112af852e324` |
| Independent QA of the package | [Review 5748551920](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/63#pullrequestreview-5748551920): `KUN-SCI-POL-001A-INDEPENDENT-QA-PASS`. This covers evidence reproducibility and the stated limits. It is not owner authorization, mathematical certification, independent astronomy or Hindi/Jyotish sign-off |
| Analysis output | PR #63 `docs/science/kun-sci-pol-001/analysis/results.json`, sha256 `cc402c73d0d820fed5271d7dedd2e534a1a407685574c44d62b306d6467e82d2` |
| Underlying gold evidence | Draft PR [#62](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/62) head `6722b5c46c3fb510495d8587b7b613f32691d97a` (tree `84816a56f388ac5e07bae3f63e24740b191da96c`), independent QA PASS [5747720823](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/62#pullrequestreview-5747720823). Gold report sha256 `edb8aab5459a326b57b4abcffc7e8f44a79be2a966baf549e97162d8d4e24bef` |

PR #62 and PR #63 are draft and unmerged. Neither is changed by this PR.

## 3. Records

The IDs SCI-04, SCI-05 and SCI-06 are proposed as the next free register IDs after SCI-03. They are labels only and can be renamed before the merge without changing any scope.

### SCI-04 (B-1): LAGNA-F independent formula tolerance

| Field | Record |
|---|---|
| ID | SCI-04 (PR #63 item B-1) |
| Options reviewed and evidence | R 1e-9°; A1 5e-10°; A2 1e-10°; A3 adaptive 2 × per-chart bound; A4 1e-8°; A5 no tolerance. PR #63 `B1-LAGNA-FORMULA-TOLERANCE.md` at `1b70927`: observed \|formula − swetest\| max 4.33e-11°, at most 0.80 of each chart's print-quantisation bound; sampled-grid worst-case estimate 4.8e-10° (not a certified supremum); smallest realistic defect 1.1e-7° |
| Recommended choice | R |
| Owner decision | **Approve R**, unmodified |
| Effective scope | The test-only `LAGNA-F` comparison of the closed-form ascendant formula against the swetest Ascendant, on Swiss-printed ARMC, true obliquity and true Lahiri ayanamsha, with tolerance **1e-9°**, for the supported envelope **\|latitude\| ≤ 66.0°** (SCI-01g). A Lagna category compared through the formula is BOUNDARY-INDETERMINATE when the swetest Lagna lies within 1e-9° of an edge |
| Not in scope | Any engine calculation, the SCI-01e definition, any other tolerance, any latitude outside ±66.0°, any independent-astronomy or public accuracy claim |
| Date | 2026-11-03 (Asia/Kolkata) |
| Approval links | P2 [6598001352](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/63#issuecomment-6598001352); P3 (owner task KUN-SCI-POL-002, transcribed in this PR's description) |
| Reviewed SHA | PR #63 `1b70927bed1e040f55441b5b710600ae6fe11216` |
| Change request needed | YES: implementation task KUN-SCI-IMPL-B1 ([IMPLEMENTATION-TASKS.md](IMPLEMENTATION-TASKS.md)) |
| Status | **OWNER SELECTED PRE-MERGE - CANONICAL ADOPTION PENDING** |

### SCI-05 (B-3): Scope extension of the frozen Swiss tolerances

| Field | Record |
|---|---|
| ID | SCI-05 (PR #63 item B-3) |
| Options reviewed and evidence | R reuse unchanged as a scope extension; A1 reuse and amend basis text; A2 tighten to about 5.1e-9°; A3 separate gold tolerances; A4 do not approve. PR #63 `B3-SWISS-TOLERANCE-APPLICABILITY.md` at `1b70927`: 500/500 engine longitudes equal round(swetest, 8); max \|d\| 4.999992e-9° = 0.50 × 1e-8°; only GOLD-E01 lies within 1e-9° of an edge, the next nearest at 2.4e-4° |
| Recommended choice | R |
| Owner decision | **Approve R**, unmodified |
| Effective scope | The existing frozen values `engine_vs_swetest` = **1e-8°** and `binding_vs_swetest` = **1e-9°** (KUN-01-SWISS-01 `spec.json` sha256 `642a770d713c11bc42fc92fe441da02e4848522fc4978ae3049dddbea33d12a8`) also apply, **unchanged**, to the KUN-SCI-GOLD-001 50-chart matrix (`matrix.json` sha256 `bc27314f4d243cb673debccf970dd20f8916fdb8d7661262495398556bd0e9c1`) |
| Not in scope | Any new or changed tolerance value; any global tolerance for other matrices; any edit of the frozen `spec.json`; any accuracy claim beyond Swiss-on-Swiss conformance |
| Date | 2026-11-03 (Asia/Kolkata) |
| Approval links | P2 [6598001352](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/63#issuecomment-6598001352); P3 |
| Reviewed SHA | PR #63 `1b70927bed1e040f55441b5b710600ae6fe11216` |
| Change request needed | YES, small: KUN-SCI-IMPL-B3 (register citation in the gold runner; no new tolerance) |
| Status | **OWNER SELECTED PRE-MERGE - CANONICAL ADOPTION PENDING** |

### SCI-06 (B-6): Birth-time sensitivity disclosure

| Field | Record |
|---|---|
| ID | SCI-06 (PR #63 item B-6) |
| Options reviewed and evidence | Option 1 short disclosure; Option 2 expanded explanation; Option 3 withhold; windows W = 1, 2 or 5 min. PR #63 `B6-NEAR-BOUNDARY-DISCLOSURE.md` at `1b70927`: numerical indeterminacy only below 1e-9° (GOLD-E01, crossing time unresolved at float64 JD precision); illustrative synthetic sample (not a population prevalence): a ±2 min change alters the Lagna Navamsa in 29.4% and the Lagna Rashi in 3.5% of 20,000 charts |
| Recommended choice | Option 1, W = 2 min, plus Option 2 as an optional premium appendix |
| Owner decision | **Approve Option 1** as recommended |
| Effective scope | (a) Keep the engine's calculated classifications unchanged (SCI-01f half-open rule on unrounded values). (b) Show a **brief birth-time sensitivity note** when the **Lagna Rashi, Lagna Navamsa, Moon Rashi, Moon Navamsa, Moon Nakshatra or Moon Pada** would change within **±2 minutes** of the entered birth time. (c) Include a suitable **near-exact-boundary note** for numerical exact-edge cases. (d) Offer Option 2's expanded explanation as an **optional premium appendix**. (e) The 2-minute window is a disclosure policy, not an assumption that a customer's recorded time is wrong |
| Not in scope | Any change to a classification, degree, boundary convention, schema 0.3.0, calculation metadata `/3`, reference receipt, customer PDF or live preview; any item outside the six listed; any approval of English or Hindi wording; Option 3 (withholding) |
| Conditions | Wording needs human Hindi and Jyotish editorial review and separate owner copy sign-off. The versioned sensitivity computation, the schema strategy and the report/UI work each need their own authorized task, engineering QA and, where applicable, report QA before activation |
| Date | 2026-11-03 (Asia/Kolkata) |
| Approval links | P2 [6598001352](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/63#issuecomment-6598001352); P3 |
| Reviewed SHA | PR #63 `1b70927bed1e040f55441b5b710600ae6fe11216` |
| Change request needed | YES: KUN-SCI-IMPL-B6a to B6d |
| Status | **OWNER SELECTED PRE-MERGE - CANONICAL ADOPTION PENDING** |

## 4. Step 2 (not done by this PR)

1. The owner explicitly authorizes the merge of this documentation-only PR. Claude does not merge it.
2. After the merge, a post-merge adoption receipt records the merge SHA and date, in a follow-up commit or a comment linked from the merged PR.
3. Only then do SCI-04, SCI-05 and SCI-06 read OWNER APPROVED / CANONICAL, each to the scope above.

Until step 2, the implementation tasks that depend on these records are unauthorized for merge.
