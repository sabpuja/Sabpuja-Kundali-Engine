# Sabpuja Kundali | Phase 1 PDF Report Generator

**ISOLATED FEATURE ONLY:** This directory is stacked on draft PR #44 at pinned head `b436134fbcd82e0f3c510485c244f968dbb9deea`. No merge, GitHub Actions, public API, Shopify change, deployment, or preview UI change is authorized.

## Canonical sources

- Numerical calculations: *only* the Sabpuja Kundali engine's complete `{"input":..., "chart":...}` response, schema **0.3.0**.
- Layout and typography: `sabpuja/design-system` canonical `tokens/tokens.css`, Git blob `b371e009bb0d655c94695acb0ff8ec381fed9135`, current live [Foundations](https://lab.srv2005300.hstgr.cloud/theme/foundations/).
- Approved logo: existing `prototype/kundali_prototype/static/brand/sabpuja-logo-horizontal-color.svg`, used unchanged.
- Fonts: existing local Poppins and Inter WOFF2 from the prototype, converted **in memory** and embedded in the PDF. Missing approved fonts or logo makes rendering fail; no DejaVu/Helvetica substitution or Internet font fetch.
- Saffron `#D35400`, gold `#F4B400`, ivory `#FFFBEF`, white and current storefront neutrals. **No maroon UI palette and no hard-coded alternate theme.**

## Scope and safety

The 8-page, searchable A4 report contains a cover, birth details, D1 chart, D9 chart, D1 planetary degrees/houses, D9 placements, house directory and Nakshatra/Pada, methodology and limitations.

Only planet positions and houses returned by the engine are displayed. The renderer verifies internal D1/D9 house consistency and refuses unsupported responses. It does **not** compute new astronomical values, Dashas, Panchang, Vargas beyond D9, future predictions, Yoga/Dosha, Shadbala, or remedies. The engine's `UNVERIFIED_GOLDEN_CHARTS` status remains visible. This is an educational calculation display, not a certified prediction.

The `generate(response, synthetic=False) -> bytes` API produces an **in-memory** PDF. It does not create user profiles, files, analytics, storage, cookies, or network requests. The command-line helper writes only to an explicitly supplied output path. Do not persist real birth details during development or QA.

## QA

In a throwaway Python environment, from the repository root:

```bash
python -m pip install -r report/phase1/requirements-qa.txt
python -m unittest discover -s report/phase1/tests -v
python report/phase1/generate_report.py report/phase1/tests/fixtures/synthetic-new-delhi.json /tmp/sabpuja-synthetic-report.pdf --sample
```

QA must verify 8 pages, Poppins/Inter **embedded** (not generic fallbacks), no clipping or overlapping D1/D9 grahas, synthetic name/date only, and no out-of-page content. The test fixture is a synthetic New Delhi response captured from the independently reviewed Gate 3E engine. No client birth data should enter a code commit or QA artifact.

## Future preview integration

Do **not** add a public `/api/report` endpoint, download button, or per-user birth data storage in this PR. Prepare such integration as a separately QA-reviewed change with private auth checks, per-IP rate limits, request-boundary validation, no request-body logs, bounded PDF CPU/memory and on-demand ephemeral response headers (`no-store`, attachment disposition, correct content type). Apply source/license/privacy signoff before any client uses a PDF.

The owner-only HTTPS preview remains on the prior exact source and is unchanged. Original PR #1 HOLD remains active for production integration; C7 numerical scope is not altered by PDF generation. **Production NO-GO.**

## Phase 2A premium layout (KUN-RPT-002A, draft)

`premium_report.py` is a separate, versioned layout (`LAYOUT_ID = 'phase2a-premium'`). Since KUN-RPT-002B it is the renderer behind the private preview's `POST /api/report` (`prototype/kundali_prototype/server.py`, `handle_report`), always with the `baseline` palette. `generate_report.py` above is unchanged and remains the reproducible Phase 1 baseline for regression tests and rollback; it is no longer called by the server.

```python
from report.phase1.premium_report import generate
pdf = generate(engine_response, synthetic=False, palette='baseline')
pdf = generate(engine_response, synthetic=False, palette='baseline', display_name='Asha Verma')  # optional name
```

- **Ten A4 pages:** cover, overview and contents, reading guide, birth details, D1 chart, D9 chart, planetary positions, Navamsa placements, twelve-house directory, methodology and provenance.
- **Only engine values.** The one derived display value is the position within the engine's own Rashi (`premium_layout.sign_position`): taken from the printed decimal, truncated to whole arc-seconds (never rounded into the next Rashi), and refused if the longitude does not lie in the engine's Rashi. The only tolerance is half a display unit at a boundary, where the engine's unrounded classification can print as the boundary value. Navamsa is never recalculated; D9 placements are checked against `d9.houses`.
- **Requires** the complete engine response with `calculation_metadata` schema `/3`; the provenance page is built from it.
- **Palettes:** `premium_theme.json`. **OD-10 is decided: the owner approved the saffron Foundation design.** `baseline` maps the existing `theme.json` tokens, is the default and is the only palette the server renders; the request cannot choose a palette. `od10-candidate` (maroon / ivory / gold) was not selected and is kept only for historical comparison in development tools; it must never appear in customer-facing output.
- **Optional report name (KUN-UX-NAME-001):** `generate(..., display_name=None)`. The name must be the output of `display_name.normalize()` (otherwise `ValueError`). It is drawn as "Prepared for" under the cover title (the subtitle moves down and the cover emblem shrinks to keep the birth panel in place) and as the first "Name on report" row of the page-4 Birth record, and nowhere else; never in the PDF metadata. Without a name the bytes are identical to the renderer before this option (pinned SHA-256 for all 13 scenarios in `tests/test_premium_name.py`). Accepted: 80 visible Latin letters (with accents) or Devanagari characters, single spaces, apostrophes, hyphens and full stops; see `display_name.py`. Latin is drawn with the brand face's Latin or Latin Extended subset; Devanagari with Poppins Devanagari 600 (same `@fontsource/poppins@5.3.0` package, SIL OFL 1.1), shaped with HarfBuzz through `uharfbuzz==0.57.0` (Apache-2.0; HarfBuzz is MIT-licensed), drawn as glyph outlines with the same words as invisible text in logical order, so copy, search and text extraction return exactly the typed Unicode. Long names shrink to a minimum (11 pt cover, 8 pt page 4) and then wrap; a character no face can draw raises instead of being dropped or transliterated.
- **Fail closed:** unknown glyphs in engine-supplied text (for example a Devanagari place name), text that cannot fit, chart labels that cannot be placed legibly, an altered logo file, or a PDF over 1 MiB all raise instead of producing a degraded PDF.
- **Tests:** `tests/test_premium_report.py`, `tests/test_premium_name.py` and `tests/test_display_name.py`, with 13 synthetic scenarios in `tests/fixtures/premium/` built by `tools/make_premium_scenarios.py`. Set `SABPUJA_TEST_EPHE_PATH` to also require the engine to reproduce every scenario exactly.
- **Visual review:** `python report/phase1/tools/visual_review.py OUT_DIR` writes the sample PDFs, contact sheets, old/new and palette comparisons outside Git.
