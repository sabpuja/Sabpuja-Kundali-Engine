# Owner copy attestation: Changes A and B (register items 13 and 15)

**To be completed and signed by the Sabpuja owner only. Nothing on this form has been filled in by the
developer or by any AI assistant (Claude, ChatGPT or any other), and none of them can sign it.**

## Governance note (what has and has not happened)

On 2026-11-04 (Asia/Kolkata) the owner replied "i will go with your recommendation" to the question "Do you
approve both proposed wording changes, A (English PDF page 10) and B (English/Hindi chart-schema wording),
exactly as documented?" (issue #73, KUN-I18N-COPY-005). That decision authorized **implementation and
exact-SHA independent QA** of the two strings below. It is recorded here as a chat decision only.

It is **not** a signed owner attestation, a merge, a deployment, a customer release or a Hindi language
review. Register items 13 and 15 keep `owner_copy` **PENDING** until this form is signed and committed under
`signed/` and recorded in `editorial-acceptance-register.json` by the procedure in
`EDITORIAL-ACCEPTANCE-REGISTER.md`. The Hindi wording of item 15 still needs the independent human Hindi
language reviewer (row L-15); the owner's copy decision does not replace that review.

## The two exact strings

| | Change A (register item 13) | Change B (register item 15) |
|---|---|---|
| Catalog and key | `report/phase1/report_i18n.json` `method.exc5` (English PDF page 10) | `prototype/kundali_prototype/static/i18n.json` `ui.d9.footnote`, and the English fallback in `prototype/kundali_prototype/static/index.html` |
| Before | `Hindi edition` | EN `The D9 house fields use the owner-approved chart schema 0.3.0.` / HI `D9 भाव के फ़ील्ड स्वीकृत चार्ट स्कीमा 0.3.0 के अनुसार हैं।` |
| After | `Hindi text (available as a separate edition)` | EN `The D9 house fields use chart schema 0.3.0.` / HI `D9 भाव के फ़ील्ड चार्ट स्कीमा 0.3.0 के अनुसार हैं।` |
| Unchanged | Hindi `अंग्रेज़ी पाठ (अलग संस्करण में उपलब्ध)`; all Hindi PDFs | Schema `0.3.0`, `/api/chart`, every PDF |

Specifications: `CHANGE-A-ENGLISH-PAGE10.md`, `CHANGE-B-SCHEMA-WORDING.md`.

## Owner record (owner only)

| Decision | Approve / Reject | Exact commit approved (40 hex) | Date (YYYY-MM-DD) | Signature |
|---|---|---|---|---|
| Change A: `Hindi text (available as a separate edition)` | | | | |
| Change B: `chart schema 0.3.0` / `चार्ट स्कीमा 0.3.0` | | | | |

| | |
|---|---|
| Owner full name | |
| Web catalog SHA-256 approved (copy from the register's `reviewed_source`) | |
| PDF catalog SHA-256 approved (copy from the register's `reviewed_source`) | |
| Signature | |
