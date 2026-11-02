# Change B: customer-facing chart schema wording (owner-controlled)

**Status: SPECIFICATION AND UNAPPLIED PATCH. Not authorized. The canonical catalogs are unchanged.**
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
