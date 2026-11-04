# Hindi editorial acceptance register

Machine-readable source: `editorial-acceptance-register.json` (validated by
`report/phase1/tests/test_editorial_register.py`). The JSON is the live record and holds the current
state; this page explains the rules. The state tables below are dated snapshots.

**Owner policy (KUN-GOV-SIMPLE-001, issue #75): the owner explicitly approves in chat; the approval is
recorded accurately in GitHub; work continues.** No PDF, signed sheet, attestation form, signature,
qualification statement, second owner confirmation or evidence-ingest commit is required.

## Layers (kept separate on purpose)

| Layer | Who may record it | What it means | What it does **not** mean |
|---|---|---|---|
| `developer_correction` | Claude (developer) | The developer changed (CORRECTED) or left (NO_CHANGE) the wording, at the named commit | Any kind of review or approval |
| `engineering_rendering_verification` | ChatGPT independent engineering QA (an AI reviewer), citing its PR review | Text renders, shapes, extracts, fits, and passes browser and privacy checks at the named commit | That the Hindi is correct, natural or the right Jyotish term |
| `human_hindi_language` | A named independent human Hindi editor | Grammar, spelling, readability, tone accepted / revised / rejected | Jyotish correctness |
| `human_jyotish_terminology` | A named independent human Jyotish reviewer | The astrological term is correct and recognised | Language quality |
| `owner_copy` | The Sabpuja owner (decides in chat; anyone may record it in GitHub) | Owner decision on items 13 (Change A) and 15 (Change B) | Language or Jyotish review |
| `customer_release` (register level) | The Sabpuja owner, by a separate explicit release instruction | Final acceptance for customers, after every applicable layer is decided | Deployment authorization by itself |

## Rules enforced by the tests

`register_problems()` in the test is the gate. It only refuses; it never records or decides.

1. **Canonical required-layer matrix**, fixed in the test (the register's own `review_layers`
   field cannot relax it): Hindi language for items 1, 3, 7, 8–18, C1–C4, C6; Jyotish for items
   1–7 and C5; owner copy for item 13 (Change A) and item 15 (Change B). A required layer may only
   be PENDING, ACCEPTED, REVISED or REJECTED; `NOT_APPLICABLE` or any other status on a required
   layer fails. A layer the matrix does not require must be `NOT_APPLICABLE`.
2. **Other statuses are closed sets:** developer CORRECTED / NO_CHANGE (and must say it is not a
   review); engineering PASS with an AI verifier labelled "not a human language review" and a
   40-hex commit; `customer_release` PENDING or APPROVED only.
3. **A decided owner layer** (ACCEPTED, REVISED, REJECTED) records: `decided_by` (a named human, the
   owner), `source` (for example "chat owner instruction recorded in GitHub issue"), `record` (the
   GitHub issue, PR or comment URL in this repository where the decision is written down),
   `decision_date`, `decision_text` (the decision as given), the exact `reviewed_commit` and both
   catalog SHA-256 values. `recorded_by` may name whoever transcribed it, including an AI.
4. **A decided human Hindi or Jyotish layer** records: `reviewer.name` (a named human), the GitHub
   `record` of their feedback (for example their issue or PR comment), `decision_date`, the exact
   `reviewed_commit` and both catalog SHA-256 values. REVISED and REJECTED need the replacement wording
   or reason. An owner decision never fills a human layer.
5. **No AI decides** a human layer, an owner layer or the release (Claude, ChatGPT, GPT, OpenAI,
   Anthropic, Gemini, Copilot, "AI", "assistant", "bot", "LLM", "language model"). An AI may record
   someone else's decision.
6. **Stale decisions fail:** a decision is valid only for the catalog bytes it names. When a
   catalog changes (an approved REVISE, for example), the decider re-confirms.
7. **`reviewed_source`** must equal the catalogs in the same tree, by SHA-256 and git blob ID.
8. **Release:** `customer_release` APPROVED requires every required layer of every item to be
   **ACCEPTED** (REVISED and REJECTED are decisions, never approvals) and a **separate, explicit owner
   release directive** recorded in GitHub (`approved_by`, `source`, `record`, `date`,
   `decision_text`). An owner copy decision (Changes A and B) is never a release: its record cannot be
   reused for the release.
9. **Exact git identity, not SHA format (KUN-I18N-003B).** Every decision's `reviewed_commit` must
   equal `reviewed_source.commit`. Where the git object database is present, the reviewed source
   commit must exist, have the named tree and contain the named catalog blobs. An APPROVED release
   names an explicit `release_candidate` (commit, tree, catalog SHA-256 and blob IDs) that exists in
   git, carries the reviewed catalog bytes and contains the reviewed source commit;
   `customer_release.commit` equals it (`refresh_manifest.py --release-candidate <commit>` fills the
   candidate facts from git).
10. **`git archive` mode:** with no object database, decisions are still bound to the catalogs by
    SHA-256 and blob ID; an approved release is refused as unverifiable. Run release checks in a clone.

What the gate does not prove: who decided. A GitHub record relaying a chat decision is an audit note,
not proof of the chat author's GitHub identity, and the gate does not judge whether Hindi or Jyotish
wording is correct. Tests never validate language or cultural correctness.

## How a decision is recorded

1. **Owner decision** (copy change, merge, release): the owner says it explicitly in chat. Whoever
   relays it writes the exact decision, date and scope in the relevant GitHub issue or PR. If it is an
   owner copy decision, the developer copies it into the JSON (`decided_by`, `source`, `record`,
   `decision_date`, `decision_text`, `reviewed_commit` and the catalog hashes) and nothing else. Merge,
   deployment and customer release stay separate actions, each needing its own explicit owner
   instruction, given in ordinary chat and recorded in GitHub.
2. **Human Hindi or Jyotish reviewer:** the reviewer gives feedback as a GitHub issue or PR comment (or
   ordinary editorial feedback that the owner posts there). The developer records it in the JSON with
   the reviewer's name, the comment URL and the exact hashes reviewed. No form or signature is needed.
   A review not yet given stays PENDING; nothing is ever entered on a reviewer's behalf.
3. A REVISE is applied in a separate change, all affected tests are rerun, and the decider re-confirms
   against the new catalog hashes.

Recording a decision changes only the decision fields of `editorial-acceptance-register.json`. The
PAN-QA-08 v5 identity check (`tests/panchanga/identity_v5.py`) accepts such a record edit without a new
overlay version; it still refuses any change to the catalogs, application code, tests, numerical
manifests or the rest of the packet.

The former signed-sheet procedure (KUN-I18N-003C: signed files under `signed/`, chained
evidence-ingest commits) and `OWNER-COPY-ATTESTATION.md` are retired; they remain in git history.

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

## State at KUN-I18N-COPY-005 (reviewed source `84fe981`; the signature requirement below was retired by KUN-GOV-SIMPLE-001)

The owner approved Changes A and B in chat for implementation and exact-SHA independent QA (issue #73). They
are applied at `84fe981c79573ab753b5d7baadf2ff4aa49e819c`, and `reviewed_source` is re-pinned to that commit
(new web catalog SHA-256 `06c0f071…4627`, PDF catalog SHA-256 `1483e1fa…f81e`). Items 13 and 15 now show
the developer layer as CORRECTED at that commit. **Every human Hindi language, Jyotish, owner copy and
customer release layer stays PENDING**: the chat approval is not a signed owner attestation
(`OWNER-COPY-ATTESTATION.md` is blank), and no reviewer has seen the new catalogs. The engineering QA layer
still names its own verified commit `c9f147b`; independent engineering QA of `84fe981` and the pin commit is
pending on the KUN-I18N-COPY-005 draft PR. A later signed-decision intake needs its own versioned PAN-QA-08
identity overlay, because the v4 overlay fixes this packet's exact file inventory.

## State at KUN-GOV-SIMPLE-001 (issue #75)

The owner's chat approval of Changes A and B (issue #73), the independently tested implementation and the
owner-authorized merge of PR #74 are recognized as the owner's decision under the simplified policy. Items 13
and 15 `owner_copy` are recorded as ACCEPTED, with `record` issue #75 and the exact reviewed source
`84fe981`. The 19 human Hindi language and 8 Jyotish decisions are **not yet given** (PENDING), and
`customer_release` stays **PENDING** until the owner separately instructs a release. Production NO-GO.
