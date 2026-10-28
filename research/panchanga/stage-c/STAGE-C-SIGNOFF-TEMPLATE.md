# Stage C independent verification receipt

**UNSIGNED TEMPLATE. No verification has been performed. No part of this receipt may be completed by Claude, by the ChatGPT reviewer, or by anyone on the verifier's behalf.**

A receipt is valid only with the frozen row-level files attached and matching the checksums below. A signature or a GitHub approval without them is not accepted.

## 1. Verifier

| Field | Entry |
|---|---|
| Verifier name | |
| Affiliation (if any) | |
| Attributable identifier (own GitHub login, verified email or other) | |
| Assignment form reference (where the signed form was submitted) | |
| Owner appointment reference | |

## 2. Source

| Field | Entry |
|---|---|
| Publisher | |
| Publication and edition, exactly as shown | |
| Original source URLs consulted (list every URL actually opened) | |
| Verification date(s) and times (UTC) | |
| Language in which the pages were read | |

## 3. Records

| Field | Entry |
|---|---|
| Assigned record count | |
| Completed record count | |
| Checked candidate IDs (list each, or a range with any exclusions) | |
| Blind outcomes: `TRANSCRIBED` | |
| Blind outcomes: `SOURCE_UNAVAILABLE` | |
| Blind outcomes: `DATE_OR_TIME_AMBIGUOUS` | |
| Blind outcomes: `SOURCE_METHOD_UNCLEAR` | |
| Blind outcomes: `REVIEW_INCOMPLETE` | |
| After reconciliation: number matched (`MATCHED_PRIMARY_SOURCE`) | |
| After reconciliation: number disputed (`SOURCE_DISAGREEMENT`) | |
| After reconciliation: number unavailable (`SOURCE_UNAVAILABLE`) | |
| After reconciliation: number unresolved (ambiguous, method unclear or incomplete) | |
| Discrepancy register ids raised | |

The counts in each block must add up to the completed record count.

## 4. Evidence

| File | SHA-256 | Where submitted |
|---|---|---|
| `BLIND-VERIFICATION-SHEET.completed.csv` (independently recorded values) | | |
| `METHOD-FACTS-CHECKLIST.completed.md` (Part A) | | |
| Completed reconciliation (crosswalk `R` columns) | | |
| Completed discrepancy register | | |
| Source-rights section A record | | |

## 5. Attestations

The verifier answers each item yes or no. Any no must be explained in section 6.

| # | Statement | Yes / No |
|---|---|---|
| 1 | I personally read the official IMD publication for every record I report as completed | |
| 2 | I performed the source checks independently of the original ChatGPT (Stage A/B) and Claude transcriptions | |
| 3 | I recorded every value from the primary source before I saw any candidate value, and I froze my files before reconciliation | |
| 4 | I did not open the crosswalk, Part B, the capture template, the source register section 5, SCI-PAN-01, the WP-B2 draft or the PR #51 comments and reviews before freezing | |
| 5 | I did not use commercial Panchanga websites, software calculations or other people's transcriptions as a source | |
| 6 | I did not get around any website access restriction | |
| 7 | I recorded `SOURCE_UNAVAILABLE` wherever I could not read the source, and invented no value | |
| 8 | I am a human being, and no automated tool read the source on my behalf | |

## 6. Conflicts, qualifications and limitations

| Field | Entry |
|---|---|
| Conflicts of interest (or "none") | |
| Accidental exposure to expected values (records affected, or "none") | |
| Limitations of this verification | |

## 7. Signature

| Field | Entry |
|---|---|
| Verifier signature, or reference to an authenticated approval made by the verifier's own identity | |
| Date | |

## 8. Receipt handling (not completed by the verifier)

| Field | Entry |
|---|---|
| Received by | |
| Checksums verified against submitted files (yes or no) | |
| QA acceptance outcome ([STAGE-C-QA-ACCEPTANCE.md](STAGE-C-QA-ACCEPTANCE.md)) | |
| Owner disposition | |
