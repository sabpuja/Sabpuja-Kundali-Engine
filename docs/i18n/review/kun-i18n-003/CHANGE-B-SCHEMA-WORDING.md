# Change B: customer-facing chart schema wording (owner-controlled)

**Status: APPLIED (KUN-I18N-COPY-005, issue #73).** The owner approved this change for implementation and exact-SHA independent QA in chat on 2026-11-04 ("i will go with your recommendation", in reply to the question whether to approve Changes A and B exactly as documented). Merged on owner instruction (PR #74). Under owner policy KUN-GOV-SIMPLE-001 (issue #75) the chat decision is the owner's decision: register item 15 `owner_copy` is recorded as ACCEPTED with issue #75 as its audit reference; no attestation or signature is required. Not released. The text below is the original specification, kept for traceability; the patch under `patches/` is the historical proposal and is not re-applied.
Apply only after the owner's explicit approval, recorded with attribution in
`editorial-acceptance-register.json` (item 15, `owner_copy`) in the same commit. The Hindi
replacement still needs the human language reviewer's acceptance (item 15, `human_hindi_language`).

## Change (web page only)

| Where | Current | Proposed |
|---|---|---|
| `prototype/kundali_prototype/static/i18n.json` `ui.d9.footnote` (en) | "… The D9 house fields use the owner-approved chart schema 0.3.0." | "… The D9 house fields use chart schema 0.3.0." |
| same key (hi) | "… D9 भाव के फ़ील्ड स्वीकृत चार्ट स्कीमा 0.3.0 के अनुसार हैं।" | "… D9 भाव के फ़ील्ड चार्ट स्कीमा 0.3.0 के अनुसार हैं।" |
| `prototype/kundali_prototype/static/index.html` line 166 (the English text served before the catalog loads) | same English as the catalog | same English as the new catalog value |

Only the approval adjective is removed. The customer line then names the version the owner asked
for: "Chart schema 0.3.0" / "चार्ट स्कीमा 0.3.0".

**Preserved:** schema `0.3.0` itself (`/api/chart` still returns `schema_version` `0.3.0`), the
engine, the API contract, `docs/DECISIONS.md` and every engineering approval record for the schema.
Only customer copy changes; the internal decision evidence stays where it is.

## Patch

`patches/change-b-schema-wording.patch` (applies cleanly on this branch's head with or without
Change A, in either order). It changes the two files above and adds
`report/phase1/tests/test_owner_copy_change_b.py` (exact wording in both languages, no
"owner-approved" in any English UI string or in `index.html`, no स्वीकृत in any Hindi UI string), and
updates the register's `reviewed_source` web catalog hash.

After `git apply`, run `PYTHONPATH=src:prototype python docs/i18n/review/kun-i18n-003/refresh_manifest.py`: the patch changes `editorial-acceptance-register.json`, so the packet manifest must be refreshed in the same commit, or `test_review_packet_assets.py` fails (by design). The patch updates only the register's catalog SHA-256, so
`test_editorial_register.py` also fails on the patched tree until the source is re-pinned
(KUN-I18N-003B, by design): commit the approved change as `X`, then in a follow-up commit run
`refresh_manifest.py --pin-source X` (commit, tree, SHA-256 and blob IDs read from git) and rerun
the suites. Any decision recorded before the change is then stale and must be re-confirmed. The sample PDFs do not change; only the register row of the manifest does.

## Measured impact (scratch copy at the packet commit)

- **PDFs: 104/104 byte-identical** (13 scenarios × English and Hindi × customer, sample, two named
  samples; `evidence/10-change-b-pdf-bytes.txt`). The footnote is not in the PDF. No pinned hash changes.
- Web: one sentence in the D9 footnote changes in both languages; the page-text-equals-catalog
  tests compare against the catalog, so they follow the change.

## Acceptance criteria

1. Owner approval recorded with attribution in the register (item 15 `owner_copy`); Hindi wording
   accepted by the human language reviewer (item 15 `human_hindi_language`), or applied as
   developer wording with that layer left PENDING and said so.
2. One exact-SHA commit containing only the files above.
3. Exact strings as in the table; `index.html` and the catalog English identical.
4. `/api/chart` byte identity against the previous head (schema 0.3.0 unchanged); all 104 PDFs
   byte-identical; all 26 English pins unchanged (unless Change A is in the same release).
5. Full suites green on the commit: prototype (including page text equals catalog), report,
   browser e2e / name / i18n at 280/375/768/1440, gateway locale and name privacy stacks.
6. Independent QA verdict on that exact SHA; still no release.
