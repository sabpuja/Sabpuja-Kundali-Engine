# WP-B1 Stage C: independent IMD verification package

**PREPARATION ONLY. No verifier has been appointed. No Stage C or Stage D verification has been performed, signed or approved. Production: NO-GO.**

This folder lets a separately authorized human verifier check the 46 IMD Rashtriya Panchang candidate records merged in PR #51 against the official government publication, without first seeing the values already recorded for them. It contains documentation and non-executable data only. It changes no candidate record, fixture, decision or engine file.

## Current state (baseline `main` `a2bb906223d84945fad53cd3c7353e29f18a7432`)

| Item | State |
|---|---|
| IMD candidates in [the capture template](../reference-fixtures/imd-rashtriya-panchang-capture-template.json) | 46, all `REVIEWER_SOURCED_PENDING_VERIFICATION` |
| Verified `rows` | 0 (empty) |
| Stage A, reviewer-sourced | 46 (30 opened official HTML, 16 official-domain index text only) |
| Stage B, primary page rechecked | 46, by the same ChatGPT reviewer who performed Stage A; not independent |
| Stage C, independent second-person verification | **0** |
| Stage D, engineering reference acceptance | **0** |
| PAN-D01 to PAN-D20 | All PENDING |
| WP-B2 | BLOCKED |

## Who gets which file

The package is split so that the verifier transcribes the source before seeing any expected answer.

| File | Given to the verifier | Purpose |
|---|---|---|
| [INDEPENDENT-VERIFIER-PROTOCOL.md](INDEPENDENT-VERIFIER-PROTOCOL.md) | Yes, first | Eligibility, independence rules and the step-by-step procedure |
| [VERIFIER-ASSIGNMENT-TEMPLATE.md](VERIFIER-ASSIGNMENT-TEMPLATE.md) | Yes | Identity, qualifications, conflicts and independence declaration, completed before work starts |
| [SOURCE-ACCESS-GUIDE.md](SOURCE-ACCESS-GUIDE.md) | Yes | Official IMD pages and how to find the Gregorian-date rows |
| [BLIND-VERIFICATION-SHEET.csv](BLIND-VERIFICATION-SHEET.csv) | Yes | 46 assignments with locators and empty fields; no expected values |
| [METHOD-FACTS-CHECKLIST.md](METHOD-FACTS-CHECKLIST.md) | Yes | Part A: blind record of IMD's stated methods and names (not part of the 46) |
| [STAGE-C-SIGNOFF-TEMPLATE.md](STAGE-C-SIGNOFF-TEMPLATE.md) | Yes, at the end | Attributable, record-level verification receipt |
| [DISCREPANCY-REGISTER.csv](DISCREPANCY-REGISTER.csv) | After freeze | Every difference, unavailable source or open question, with its reporting path |
| [REFERENCE-CROSSWALK.csv](REFERENCE-CROSSWALK.csv) | **No, only after freeze** | Existing candidate values, Stage A tiers and interpretations, with empty reconciliation columns |
| [METHOD-FACTS-RECONCILIATION.md](METHOD-FACTS-RECONCILIATION.md) | **No, only after freeze** | Part B: method facts already reported by the Stage A/B reviewer and the method candidates under consideration |
| [STAGE-C-QA-ACCEPTANCE.md](STAGE-C-QA-ACCEPTANCE.md) | QA and owner | Criteria for accepting or rejecting returned Stage C evidence |
| [STAGE-D-READINESS-CHECKLIST.md](STAGE-D-READINESS-CHECKLIST.md) | QA and owner | Separate gates for engineering acceptance; none complete |
| [SOURCE-RIGHTS-CHECKLIST.md](SOURCE-RIGHTS-CHECKLIST.md) | Verifier records facts; owner and legal reviewer decide | Publication identity, rights notice and permission questions |

The repository is readable by anyone with access, so the separation depends on the verifier's attested discipline. The protocol therefore lists the files and pages the verifier must not open before freezing their transcription, and the signoff asks them to attest to it.

## Workflow

1. **Owner** appoints a verifier (not done; the owner decides separately).
2. **Verifier** completes the assignment form and declarations.
3. **Verifier** reads the official IMD pages and fills a copy of the blind sheet and Part A of the method checklist from the source alone.
4. **Verifier freezes** both files and records their SHA-256 checksums. Frozen files are never edited afterwards.
5. **Reconciliation:** the frozen transcription is compared with the crosswalk and Part B. Every non-match goes to the discrepancy register. Candidate records are not rewritten.
6. **Verifier signs** the Stage C receipt with the row-level evidence attached.
7. **Independent QA** applies the acceptance criteria. **Owner** decides on acceptance.
8. Stage D is a separate, later process (see the readiness checklist).

## Counts

46 assignments, `SC-01` to `SC-46`, one for each `PAN-CAND-IMD-01` to `-46`, IDs unchanged.

| Element | Records |
|---|---:|
| Tithi | 7 |
| Nakshatra | 6 |
| Yoga | 7 |
| Karana | 14 |
| Sunrise | 6 |
| Sunset | 6 |
| **Total** | **46** |

Dates: 2026-03-22 and 2026-03-23 (Chaitra page), 2026-07-14 and 2026-07-17 (Ashadha page), 2026-10-26 and 2026-10-28 (Kartika page). Stage A tiers are kept as recorded: 30 opened official HTML (Chaitra and Kartika), 16 official-domain index text only (Ashadha). The Stage B direct reopening of the Ashadha page by the same reviewer does not change those tiers and is not Stage C.

## Data files

- **Blind sheet:** the columns up to `station_or_location` are locators. `V01` to `V14` are empty, for the verifier. `saka_date_locator_aid` is derived by Claude to help find the row and is not evidence. `row_locator` counts entries of the same element in printed order.
- **Crosswalk:** values copied unchanged from the capture template. Columns ending in `_claude` are Claude's derived values, not printed values. `stage_a_retrieval_tier` is the original Stage A tier. `R01` to `R10` are empty, for reconciliation.
- **Discrepancy register:** header only. Entries are added during reconciliation.

All three were generated from the capture template at the baseline commit by a scratch script that is deliberately not committed (this package contains no executable content). The QA checks in the PR description can be repeated by hand or with any CSV reader.

## What this package does not do

- It does not appoint, name or impersonate a verifier, and contains no completed signature.
- It does not claim that any human verification has occurred.
- It does not change the 46 candidates, any fixture, `docs/DECISIONS.md`, SCI-PAN-01, the WP-B2 draft or any engine file.
- It does not adopt any sunrise, ayanamsa, Karana or naming convention.
- It does not reproduce IMD pages, screenshots or tables.
- It contains no scraper, test, script, workflow or other executable content.
