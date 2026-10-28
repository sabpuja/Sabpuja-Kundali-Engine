# Stage C QA acceptance criteria

**Criteria only. No Stage C evidence has been received or accepted.**

Independent QA applies these criteria to returned Stage C evidence. Accepting it is a QA recommendation followed by an owner decision. Acceptance of Stage C does **not** complete any Stage D gate (see [STAGE-D-READINESS-CHECKLIST.md](STAGE-D-READINESS-CHECKLIST.md)).

## 1. Verifier eligibility

| # | Criterion | Rejection if |
|---|---|---|
| E1 | The assignment form is complete and signed by the verifier | Any required field blank, or signed by someone else |
| E2 | The owner appointed the verifier before the work started | No owner appointment, or appointment dated after the review |
| E3 | The verifier is a human who is not the Stage A/B ChatGPT reviewer, not Claude and not an automated process | Any of these, or the identity cannot be established |
| E4 | The verifier's identifier is attributable to that person alone | Only a shared account, such as the owner account through which earlier reviews were posted |
| E5 | Conflicts are disclosed and the owner has decided on any yes answer | Undisclosed or undecided conflict |

## 2. Blind process

| # | Criterion | Rejection if |
|---|---|---|
| B1 | A frozen blind sheet and Part A were submitted, with SHA-256 checksums, before reconciliation | Checksums missing, or submitted after the crosswalk was shared |
| B2 | The submitted files match their checksums | Mismatch |
| B3 | Columns to the left of `V01` are unchanged from the package version given to the verifier | Any change to IDs, dates, URLs or locators |
| B4 | Each completed row has `V01`, `V03`, `V04`, `V07`, `V12` and `V13`, and `V05` for named elements | Missing fields on a row reported as completed |
| B5 | Attestations 1 to 8 in the signoff are all yes, or every no is explained and QA finds the explanation acceptable | Unexplained no |
| B6 | Any accidental exposure to expected values is disclosed, with the affected rows | Exposure found but not disclosed |

## 3. Source handling

| # | Criterion | Rejection if |
|---|---|---|
| S1 | Every URL in `V03` is on `packolkata.imd.gov.in` | Any other domain, a cache, an archive or a search snippet |
| S2 | The edition shown on the source is recorded | Not recorded |
| S3 | Unreadable sources are recorded as `SOURCE_UNAVAILABLE`, not filled | A value recorded for a row marked unavailable, or a value with no accessible source |
| S4 | No access restriction was circumvented | Any evidence of a bypass |
| S5 | No page copies, screenshots or bulk tables were committed to the repository | Committed |

## 4. Reconciliation

| # | Criterion | Rejection if |
|---|---|---|
| R1 | Every row has an `R06` outcome from the defined list | Missing or undefined outcome |
| R2 | Comparison is exact (no tolerance), and notation-only differences are labelled as such | Tolerances applied |
| R3 | All 8 extended-hour rows (SC-13, -17, -20, -24, -29, -39, -42, -44) have an `R05` result, and the verifier's `V09` was produced from IMD's rule as recorded in M-CAL-01 | Missing, or the rule came from somewhere other than the source |
| R4 | Every outcome other than `MATCHED_PRIMARY_SOURCE` has a discrepancy register entry with all required fields | Missing entry or fields |
| R5 | No candidate in the capture template was edited during Stage C | Any edit |
| R6 | Proposed corrections are in a separate change for QA review and owner approval | Correction made directly |
| R7 | Part B method items are reconciled, and NOT STATED items are listed as open questions rather than confirmed facts | Unstated facts treated as confirmed |

## 5. Outcome

| Result | Meaning |
|---|---|
| ACCEPT | All criteria met. Rows with `MATCHED_PRIMARY_SOURCE` may be recorded as Stage C done, in a separate change approved by the owner |
| ACCEPT IN PART | Criteria met for named rows only. Other rows stay Stage C pending |
| RETURN | Fixable gaps (for example missing fields). The verifier submits a new, separately checksummed version |
| REJECT | An eligibility, independence or source-handling criterion failed. The rows stay Stage C pending and may need a different verifier |

Updating any candidate's Stage C status in the capture template is itself a separate, owner-approved change. This file does not perform it.

| Field | Entry |
|---|---|
| QA reviewer | |
| Evidence package and checksums reviewed | |
| Result | |
| Rows accepted | |
| Date | |
| Owner decision | |
