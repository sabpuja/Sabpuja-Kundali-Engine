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

`register_problems()` in the test is the gate. It only refuses; it never records or decides.

1. **Canonical required-layer matrix**, fixed in the test (the register's own `review_layers`
   field cannot relax it): Hindi language for items 1, 3, 7, 8–18, C1–C4, C6; Jyotish for items
   1–7 and C5; owner copy for item 13 (Change A) and item 15 (Change B). A required layer may only
   be PENDING, ACCEPTED, REVISED or REJECTED; `NOT_APPLICABLE` or any other status on a required
   layer fails. A layer the matrix does not require must be `NOT_APPLICABLE`.
2. **Other statuses are closed sets:** developer CORRECTED / NO_CHANGE (and must say it is not a
   review); engineering PASS with an AI verifier labelled "not a human language review" and a
   40-hex commit; `customer_release` PENDING or APPROVED only.
3. **A decided human or owner layer** (ACCEPTED, REVISED, REJECTED) needs: reviewer name,
   qualification and independence statement; ISO decision date; the exact reviewed commit (40
   hex) and both catalog SHA-256 values; and `evidence` `{"path", "sha256", "commit"}` naming a
   signed sheet under `signed/` in this package and the commit that holds it. **KUN-I18N-003C:**
   the file must be a regular file with no symlink on its path, resolved inside `signed/`; the
   commit must exist and be in the history of the checked-out HEAD; the file's git blob at that
   commit, at HEAD, in the index and in the working tree must be identical, and its SHA-256 the
   stated one. Untracked, staged-only, modified, deleted, replaced, symlinked or escaping files,
   URLs and free text fail; without the git object database a decided record fails closed. The
   same applies to the release record. REVISED and REJECTED need the replacement wording or reason.
4. **No AI signs** a human layer, an owner layer or the release (Claude, ChatGPT, GPT, OpenAI,
   Anthropic, Gemini, Copilot, "AI", "assistant", "bot", "LLM", "language model").
5. **Stale decisions fail:** a decision is valid only for the catalog bytes it names. When a
   catalog changes (an approved REVISE, Change A or B), the reviewer must re-confirm.
6. **`reviewed_source`** must equal the catalogs in the same tree.
7. **Release:** `customer_release` APPROVED requires every required layer of every item to be
   **ACCEPTED** (current, signed); REVISED and REJECTED are decisions, never approvals, even with a
   reason or replacement. It also needs a non-AI owner name, ISO date, 40-hex commit and a signed
   release record under `signed/` with matching hash.
8. **Exact git identity, not SHA format (KUN-I18N-003B).** Every decision's `reviewed_commit`
   must equal `reviewed_source.commit`. `reviewed_source` names the commit, its tree and the git
   blob IDs of both catalogs; the blob IDs must equal the catalogs in this tree, and where the git
   object database is present the commit must exist, have that tree and contain those blobs. An
   APPROVED release must name an explicit `release_candidate` (commit, tree, catalog SHA-256 and
   blob IDs) that exists in git, has that tree, carries the reviewed catalog bytes and contains the
   reviewed source commit in its history; `customer_release.commit` must equal it. No future release
   SHA is hard-coded: the owner names the candidate when releasing.
9. **`git archive` mode:** with no object database the catalogs are still bound by blob ID, but a
   register with any decided layer or an approved release is refused as unverifiable; run the
   check in a clone. The canonical register (all PENDING) passes in both modes.
10. In this tree every required layer and the release are PENDING and no release candidate is named
    (tests assert this), and both catalogs keep their "pending independent human Hindi editorial
    review" status line.

Signed-evidence cases (`SignedEvidenceInGit`, KUN-I18N-003C, same synthetic repository): QA's
untracked-file bypass (every evidence reference replaced by a never-committed file with its true
hash); staged but not committed; tracked but modified (with the old and the new hash); deleted
(working tree, and staged deletion); replaced in a later commit; symlink to a file inside and to a
file outside `signed/`; absolute path, `..` escape, wrong directory, directory path; blob missing
from the named commit; commit outside this checkout's history; nonexistent commit; decided
evidence without git; positive control with the committed blob.

Exact-commit cases (`ExactCommitBinding`, against a throwaway synthetic git repository in a
temporary directory holding byte-identical copies of the catalogs): all-zero, all-`f` and real-but-
wrong review SHAs (a later commit, a catalog-change commit, an unrelated root); wrong final release
SHA (all-zero, all-`f`, the reviewed source instead of the named candidate); missing or nonexistent
release candidate; candidate with the wrong tree, with changed catalogs, with history that does not
contain the review, with a wrong catalog hash; tampered `reviewed_source` commit, tree, blob IDs or
malformed fields; a decided register without the git object database; positive control bound to
real objects, with a candidate distinct from the reviewed source.

Adversarial registers the tests refuse (built in memory; nothing is written to the repository):
all layers `NOT_APPLICABLE` with release APPROVED; one required layer `NOT_APPLICABLE` (Jyotish on
item 1, owner on item 15); `review_layers` edited to drop the owner on item 13; unknown layer and
release statuses; REJECTED or REVISED with text plus release APPROVED; REJECTED without a reason;
forged or unverifiable evidence (free text, URL, `..` escape, missing file, wrong or malformed
hash); stale catalog hash; AI signer on a layer or on the release; unattributed or untraceable
decisions; release without a signed record or commit; a missing item; `reviewed_source` drift;
developer or AI QA posing as review. Control: a complete, fully signed in-memory register passes.

### KUN-I18N-003A adversarial cases (all in `AdversarialRegisters`, isolated in-memory registers)

| # | Case | Test |
|---|---|---|
| 1 | All mandatory layers NOT_APPLICABLE, release APPROVED | `test_all_not_applicable_with_release_approved` |
| 2 | One mandatory Hindi layer NOT_APPLICABLE (item 8) | `test_one_mandatory_hindi_layer_not_applicable` |
| 3 | One mandatory Jyotish layer NOT_APPLICABLE (items 1, 5) | `test_one_mandatory_jyotish_layer_not_applicable`, `test_partial_not_applicable` |
| 4 | Owner item 13 approval missing (deleted, empty, PENDING; N/A via `review_layers`) | `test_owner_approval_missing_for_item_13_or_15`, `test_review_layers_field_cannot_relax_the_matrix` |
| 5 | Owner item 15 approval missing (deleted, empty, PENDING, N/A) | `test_owner_approval_missing_for_item_13_or_15`, `test_partial_not_applicable` |
| 6 | REJECTED (or REVISED) with reason treated as approved | `test_rejected_or_revised_with_text_is_not_approval` |
| 7 | Nonexistent signed-evidence file (and URL, free text, `..` escape) | `test_forged_or_unverifiable_evidence` |
| 8 | Wrong or malformed evidence checksum | `test_forged_or_unverifiable_evidence` |
| 9 | AI attribution in a human layer, or on the release | `test_unauthorized_ai_approval` |
| 10 | Stale UI catalog checksum | `test_stale_ui_catalog_hash` |
| 11 | Stale PDF catalog checksum; catalog changed after review | `test_stale_pdf_catalog_hash`, `test_catalog_change_after_review_makes_every_decision_stale` |
| 12 | Unknown release and layer status values | `test_unknown_statuses` |
| 13 | Partial approval followed by customer release | `test_partial_approval_then_release` |
| 14 | Valid fully attributed synthetic control passes | `test_control_complete_signed_register_passes`; optional layers not demanded: `test_optional_layer_is_not_a_missing_mandatory_approval` |

### KUN-I18N-003C signed-evidence cases

| # | Case | Test |
|---|---|---|
| 1 | Untracked evidence with a valid hash (QA reproduction) | `SignedEvidenceInGit.test_untracked_signed_file_is_refused` |
| 2 | Staged-only evidence | `test_staged_but_not_committed_is_refused` |
| 3 | Tracked evidence modified after commit | `test_tracked_but_modified_is_refused` |
| 4 | Deleted evidence (working tree, staged deletion, dropped in the approval record) | `test_deleted_is_refused`, `ApprovalRecordCommit.test_approval_record_that_drops_its_evidence` |
| 5 | Symlink to a file outside (and inside) `signed/` | `test_symlinks_and_escapes_are_refused` |
| 6 | Relative path traversal, absolute path, wrong directory | `test_symlinks_and_escapes_are_refused`, `AdversarialRegisters.test_forged_or_unverifiable_evidence` |
| 7 | Git blob mismatch | `ApprovalRecordCommit.test_git_blob_mismatch` |
| 8 | Valid SHA-256 but no blob in the named commit | `test_blob_missing_from_the_named_commit` |
| 9 | Evidence from an incorrect commit (unrelated history, nonexistent, replaced later) | `test_blob_missing_from_the_named_commit`, `test_replaced_after_the_evidence_commit_is_refused`, `ApprovalRecordCommit.test_approval_record_with_a_forged_evidence_commit` |
| 10 | Correctly committed signed evidence | `test_positive_control_uses_committed_evidence` |
| 11 | Genuine approval-record commit with valid evidence | `ApprovalRecordCommit.test_genuine_approval_record_commit_with_committed_evidence` |
| 12 | Objectless archive with a decided approval fails closed | `ApprovalRecordCommit.test_objectless_archive_with_decided_approval_fails_closed`, `SignedEvidenceInGit.test_decided_evidence_without_git_fails_closed` |

### Trust boundary: what the gate proves and what it does not

**Proves (mechanically, from git objects):** the register as committed at the approval-record
revision (`committed_register_problems(revision)`, which reads the register from git rather than the
working tree) names, for every decision, the exact reviewed source commit, whose tree and catalog
blobs it checks; each evidence file is a regular file in `signed/`, committed at the named evidence
commit in the history of the approval-record revision, unchanged since, identical in the index and
working tree, with the stated SHA-256; a release names a candidate commit that exists, contains the
reviewed source and carries the reviewed catalogs. Source review, evidence and release candidate
are separate commits, and no register names its own commit: the approval-record revision is
supplied by whoever validates (for a release, the owner's release candidate or a later commit).

**Does not prove:** who signed. The gate cannot authenticate a handwritten or electronic signature,
confirm a reviewer's identity, qualification or independence, or tell a genuine sheet from a forged
one that was committed. Those remain independent human checks by whoever accepts the release
(for example, the owner confirming the reviewer directly). Git authorship is not used as identity.

## How a decision is recorded

When the signed decision sheet comes back, the developer (in a separate exact-SHA commit) commits
the signed sheet under `signed/` (it is then listed in `EVIDENCE-MANIFEST.md`) and, in a later
commit, copies each decision into the JSON exactly as signed, with `evidence.commit` set to the
commit that added the sheet: `status` (ACCEPTED / REVISED / REJECTED), `reviewer`
`{name, qualification, independence, organisation?}`, `decision_date`, `reviewed_commit`,
`reviewed_ui_catalog_sha256`, `reviewed_pdf_catalog_sha256`, `evidence`
`{"path": "docs/i18n/review/kun-i18n-003/signed/<file>", "sha256": "<hash>", "commit": "<commit that added it>"}`, `decision_text`
(replacement wording or reason), and updates `test_no_human_or_owner_decision_is_recorded_yet` in
the same commit. Each `reviewed_commit` is the register's `reviewed_source.commit`, which
is the exact commit the reviewer was given. To release, the owner names the release candidate in
`customer_release.release_candidate` (filled from git with `refresh_manifest.py --release-candidate
<commit>`, which records facts and no decision) and the same SHA in `customer_release.commit`. REVISE wording is then applied in another commit, all affected tests are rerun,
and the reviewer re-confirms against the new catalog hashes. Nothing is ever entered on a
reviewer's behalf.

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

## State at KUN-I18N-COPY-005 (reviewed source `84fe981`)

The owner approved Changes A and B in chat for implementation and exact-SHA independent QA (issue #73). They
are applied at `84fe981c79573ab753b5d7baadf2ff4aa49e819c`, and `reviewed_source` is re-pinned to that commit
(new web catalog SHA-256 `06c0f071…4627`, PDF catalog SHA-256 `1483e1fa…f81e`). Items 13 and 15 now show
the developer layer as CORRECTED at that commit. **Every human Hindi language, Jyotish, owner copy and
customer release layer stays PENDING**: the chat approval is not a signed owner attestation
(`OWNER-COPY-ATTESTATION.md` is blank), and no reviewer has seen the new catalogs. The engineering QA layer
still names its own verified commit `c9f147b`; independent engineering QA of `84fe981` and the pin commit is
pending on the KUN-I18N-COPY-005 draft PR. A later signed-decision intake needs its own versioned PAN-QA-08
identity overlay, because the v4 overlay fixes this packet's exact file inventory.
