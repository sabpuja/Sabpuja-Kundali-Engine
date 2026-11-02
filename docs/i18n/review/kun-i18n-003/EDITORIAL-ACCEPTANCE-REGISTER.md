# Hindi editorial acceptance register

Machine-readable source: `editorial-acceptance-register.json` (validated by
`report/phase1/tests/test_editorial_register.py`). This page explains it and shows its state at
KUN-I18N-003. **Current state: every human and owner layer is PENDING; customer release is PENDING.**

## Layers (kept separate on purpose)

| Layer | Who may record it | What it means | What it does **not** mean |
|---|---|---|---|
| `developer_correction` | Claude (developer) | The developer changed (CORRECTED) or left (NO_CHANGE) the wording, at the named commit | Any kind of review or approval |
| `engineering_rendering_verification` | ChatGPT independent engineering QA (an AI reviewer), citing its PR review | Text renders, shapes, extracts, fits, and passes browser and privacy checks at the named commit | That the Hindi is correct, natural or the right Jyotish term |
| `human_hindi_language` | A named, qualified, independent human Hindi editor | Grammar, spelling, readability, tone accepted / revised / rejected | Jyotish correctness |
| `human_jyotish_terminology` | A named, qualified, independent human Jyotish reviewer | The astrological term is correct and recognised | Language quality |
| `owner_copy` | The Sabpuja owner | Owner decision on items 13 (Change A) and 15 (Change B) | Language or Jyotish review |
| `customer_release` (register level) | The Sabpuja owner | Final acceptance for customers, after every applicable layer is decided | Deployment authorization by itself |

## Rules enforced by the tests

1. A human layer leaves PENDING only with: reviewer name, qualification, independence statement,
   decision date (ISO), the exact reviewed commit (40 hex) and both catalog SHA-256 values,
   and the signed decision sheet as evidence. REVISE needs the replacement wording.
2. A human layer can never carry an AI name (Claude, ChatGPT, GPT, OpenAI, Anthropic, Gemini,
   Copilot, "AI", "assistant", "bot", "LLM").
3. An approval is valid only for the catalog bytes it names. If a catalog changes after a review
   (for example when an approved REVISE or Change A/B is applied), the test fails until the
   reviewer re-confirms against the new hashes.
4. `reviewed_source` must match the catalogs in the same tree, so the packet cannot drift from the code.
5. `customer_release` must stay PENDING while any applicable human or owner layer is PENDING,
   or REJECTED without a replacement.
6. Both catalogs keep their "pending independent human Hindi editorial review" status line.

## How a decision is recorded

When the signed decision sheet comes back, the developer (in a separate exact-SHA commit) copies
each decision into the JSON exactly as signed: `status` (ACCEPTED / REVISED / REJECTED),
`reviewer` `{name, qualification, independence, organisation?}`, `decision_date`,
`reviewed_commit`, `reviewed_ui_catalog_sha256`, `reviewed_pdf_catalog_sha256`,
`evidence` (where the signed sheet is kept and its SHA-256), `decision_text` (replacement wording
or reason). REVISE wording is then applied in another commit, all affected tests are rerun, and
the reviewer re-confirms the new catalog hashes. Nothing is ever entered on a reviewer's behalf.

## State at KUN-I18N-003 (reviewed source `c9f147b`)

| Item | Developer | Engineering QA | Hindi language | Jyotish | Owner copy |
|---|---|---|---|---|---|
| 1 Prepared for | NO_CHANGE | PASS | PENDING | PENDING | n/a |
| 2 चरण | NO_CHANGE | PASS | n/a | PENDING | n/a |
| 3 पूर्ण-राशि भाव | NO_CHANGE | PASS | PENDING | PENDING | n/a |
| 4 मध्यम पात / चंद्र पात | CORRECTED | PASS | n/a | PENDING | n/a |
| 5 स्पष्ट अयनांश | NO_CHANGE | PASS | n/a | PENDING | n/a |
| 6 गुरु | NO_CHANGE | PASS | n/a | PENDING | n/a |
| 7 abbreviations | NO_CHANGE | PASS | PENDING | PENDING | n/a |
| 8 जन्म दिनांक | CORRECTED | PASS | PENDING | n/a | n/a |
| 9 spelling policy | CORRECTED | PASS | PENDING | n/a | n/a |
| 10 places | NO_CHANGE | PASS | PENDING | n/a | n/a |
| 11 Latin kept | NO_CHANGE | PASS | PENDING | n/a | n/a |
| 12 digits | NO_CHANGE | PASS | PENDING | n/a | n/a |
| 13 page 10 line | NO_CHANGE | PASS | PENDING | n/a | PENDING (Change A) |
| 14 sign note | NO_CHANGE | PASS | PENDING | n/a | n/a |
| 15 schema wording | NO_CHANGE | PASS | PENDING | n/a | PENDING (Change B) |
| 16 pickers | NO_CHANGE | PASS | PENDING | n/a | n/a |
| 17 fallback message | NO_CHANGE | PASS | PENDING | n/a | n/a |
| 18 tone | CORRECTED | PASS | PENDING | n/a | n/a |
| C1–C6 KUN-I18N-002 corrections | CORRECTED | PASS | PENDING (C1–C4, C6) | PENDING (C5) | n/a |

Engineering QA: ChatGPT, PR #60 review 5733977880, 2026-11-02, commit `c9f147b`
(KUN-I18N-002-INDEPENDENT-ENGINEERING-QA-PASS). **Customer release: PENDING.** Production NO-GO; PR #1 HOLD.
