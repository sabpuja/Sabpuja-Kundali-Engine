# KUN-B6D-REVIEW-001 (A4): where approved B-6 wording would appear

**Specification only. Nothing here changes the PDF renderer, the interface, the catalogs, the calculations or chart classifications.** It records where the wording in [`REVIEW-PACKET.md`](REVIEW-PACKET.md) would go *after* human editorial review and owner copy approval, so that the later implementation task (with its own ENG and RPT gates) has a fixed target.

## 1. Sources for the current layout

| Surface | Source used | Notes |
|---|---|---|
| Ten-page PDF, English and Hindi | Synthetic sample PDFs from the KUN-I18N-003 packet (draft PR #61 head `fee3967`): `sample-en-anonymous.pdf` SHA-256 `37b77f9a4013d5fb6ccfa379ac71c2bcd186f28428f1b010ff52ee63426010ea`, `sample-hi-anonymous.pdf` SHA-256 `7590ea3a5b094e1f92e27ea975af262219a3bef4cd49219e48882944282588c7`; catalog `report/phase1/report_i18n.json` SHA-256 `324b19ec2269b578f026b4b1dbebbd73d9b3b2f3d4879e2cca9dedb325ac0145` | Read with `pdftotext`. The PDF is on an unmerged draft stack (PRs #56 to #61); positions below refer to that stack |
| Browser interface | Catalog `prototype/kundali_prototype/static/i18n.json` SHA-256 `5cf9e5fcb4234dd971fa1c512c6c6da6567918d38a0c7e61c9e6d8cd496b17f1` at `fee3967` | Section names taken from catalog headings |
| Design system | Foundations palette and type as applied in the Gate 3B round-2 restyle (`sabpuja/theme` `gh-pages` `foundations/index.html` at `1aa273d`; `sabpuja/design-system` `af3825f` tokens): Saffron `#D35400`, Saffron 700 `#C84700`, Temple Gold `#F4B400`, Sacred Brown `#4E342E`, Deep Brown `#33241F`, Light Cream `#FFF8E7`, Ivory `#FFFBEF`; Poppins headings, Inter body; Poppins Devanagari for Hindi | Not re-read live for this task. Contrast values below are computed by `check_packet.py` |

Current PDF page plan (both languages): 1 Cover, 2 Overview, 3 Reading guide, 4 Birth details, 5 D1 Lagna chart, 6 D9 Navamsa chart, 7 Planetary positions, 8 Navamsa placements, 9 House directory, 10 Methodology.

## 2. Principle: full text in one place, a tag where each value appears

Page 4 already tells the reader to "check these values against the birth record before reading the charts: every placement depends on them". It is the natural home for the full notes. Every other place an affected value appears gets only a short tag pointing to page 4, so that tiles, chart labels and table rows keep their current size and the page count stays at ten.

## 3. PDF placement (standard ten-page report)

| Page | Element today | B-6 addition when a note applies | Strings |
|---|---|---|---|
| 1 Cover | Caption "Lagna {lagna} · Moon Nakshatra {nakshatra}" | **None.** The cover stays clean | - |
| 2 Overview | Tiles D1 LAGNA (p. 7), MOON RASHI (p. 7), MOON NAKSHATRA (p. 7), D9 LAGNA (p. 6) | One extra line in the affected tile, below the existing value line: the tag | `tag.note.pdf` or `tag.boundary.pdf` with `{page}` = 4 |
| 4 Birth details | Birth record, Calculation context, "How the time was converted" panel, method reference line | A new **Birth-time notes** panel directly after "How the time was converted" and before the page-10 reference: the summary, then each item note in the fixed order of `REVIEW-PACKET.md` §3.8 | `label.note` / `label.boundary`, `summary.body`, `summary.record`, `note.*`, `boundary.*` |
| 5 D1 Lagna chart | Lagna label line "{rashi} · {dms} within the Rashi · house 1 (shaded)" | Tag after the Lagna label line, only if the Lagna Rashi note applies | `tag.*.pdf` |
| 6 D9 Navamsa chart | D9 Lagna label line | Tag, only if the D9 Lagna note applies | `tag.*.pdf` |
| 7 Planetary positions | Lagna and Moon rows; "Moon Nakshatra and Pada" block | Tag in the Lagna row and the Moon row (Rashi note); tag in the Moon Nakshatra block (Nakshatra/Pada note) | `tag.*.pdf` |
| 8 Navamsa placements | Lagna and Moon rows (D9 Rashi) | Tag in the D9 Lagna row and the Moon row (D9 notes) | `tag.*.pdf` |
| 9 House directory | Twelve rows | **None.** A Lagna change would affect every row; the page-4 note already says so | - |
| 10 Methodology | Convention table rows | One static row **Birth-time notes**, after "Precision", on every report (with or without notes) | `method.row.label`, `method.row.value` |

Rules:
- The tag is text, never only a colour or an icon, so it survives greyscale printing, copy, search and screen readers (the PDF already overlays real text on shaped Devanagari).
- Tags and notes never move, round or restyle any existing value. All values and classifications stay byte-identical to the current output.
- Space: the longest page-4 note is `boundary.nakshatra_pada` (EN 336 / HI 307 code points); a page-4 panel with the summary and three Moon notes is about 900 EN characters. If the page-4 panel does not fit in the existing page, the implementation task must report it as a layout finding for the owner rather than shrink type below the current 8 pt minimum or drop content.

## 4. Optional premium appendix (SCI-06 Option 2)

Recommended (owner decision B6D-Q3): a **conditional page after Methodology** in a premium edition only, titled `appendix.title`, containing `appendix.p1`, `appendix.p2`, the table (`appendix.col.*`), `appendix.p3`, `appendix.p4_boundary` (only with a boundary row) and `appendix.p5_scope`. The footer then reads "Page 11 of 11" from the existing `footer.page` string.

Why not inside the ten pages: page 4 carries the short notes already, and the PRD asks for no padded pages (KUN-A09), so the appendix should exist only when there is something to explain and only in the edition that offers it. Alternatives for the owner: (b) no appendix in the PDF, browser explanation only; (c) a fixed appendix page in every premium report (not recommended: an empty appendix suggests a problem).

## 5. Browser placement

| Section (catalog heading) | B-6 addition | Strings |
|---|---|---|
| **Key placements** (`ui.key.heading`) | Under each affected placement: the label and the full note, in a note block (see §6) | `label.*`, `note.*`, `boundary.*` |
| **Confirmed birth details** (`ui.confirm.heading`) | The summary as the last item, plus a disclosure link "What does this mean?" that expands the appendix text in place (no new page, no modal) | `summary.*`, `label.more`, `appendix.*` with `ref.*.web` |
| **D1 Rashi chart** / **D9 Navamsa chart** tables | No new text; the Lagna / Moon rows get `aria-describedby` pointing to the matching note in Key placements | - |
| **Method and transparency** (`ui.method.heading`) | The static row text | `method.row.*` |

Behaviour:
- Language switching shows the same notes in the other language with identical numbers and does not recompute anything (PRD: switching language must not change numerical values).
- A birth-detail edit already discards the shown result; notes go with it.
- Notes must not overflow at 280 px or with long Hindi strings (QA-023). The longest Hindi note is 307 code points and wraps normally; no truncation or ellipsis.

## 6. Visual treatment (Foundations)

| Element | Proposal | Contrast (computed) |
|---|---|---|
| Note block background | Light Cream `#FFF8E7` | - |
| Note text | Sacred Brown `#4E342E`, Inter (EN) / Poppins Devanagari (HI), body size; PDF at least 8 pt | 10.69:1 on Light Cream (AA) |
| Label ("Birth-time note:") | Saffron 700 `#C84700`, semibold | 4.55:1 on Light Cream (AA, just above 4.5:1). Plain Saffron `#D35400` is 3.94:1 and must not be used for label text |
| Left rule (non-text indicator) | 3 px Saffron `#D35400` | 3.94:1 (meets the 3:1 non-text minimum) |
| Temple Gold `#F4B400` | Not used for the rule or text | 1.74:1 on Light Cream, below 3:1 |
| Icon | Optional neutral "information" glyph, `aria-hidden`; never a warning triangle | - |
| Not used | Danger `#B42318`, red, warning icons, bold capitals | Tone: a note, not an alert (UX-03: no fear-oriented messaging) |

## 7. What the later implementation task must prove (RPT and ENG gates)

- Classifications, degrees and every existing string are byte-identical with and without the feature on all fixtures (the notes only add text).
- Each trigger fires at exactly 120 s and not at 121 s, in both directions, and the boundary note fires below the approved threshold (B6D-Q1).
- EN and HI show the same set of notes and the same numbers for every fixture.
- Every placeholder is filled from catalogs; no customer name, place or time is inserted.
- Devanagari shaping, copy and search work for every new Hindi string; no clipped glyphs (QA-016).
- Human Hindi language and Jyotish reviewers and the owner have signed [`SIGNOFF-SHEET.md`](SIGNOFF-SHEET.md) against the exact SHA-256 of the wording file used.
