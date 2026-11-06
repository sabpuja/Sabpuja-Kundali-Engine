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
pdf = generate(engine_response, synthetic=False, palette='baseline', locale='hi')  # Hindi edition
```

- **Ten A4 pages:** cover, overview and contents, reading guide, birth details, D1 chart, D9 chart, planetary positions, Navamsa placements, twelve-house directory, methodology and provenance.
- **Only engine values.** The one derived display value is the position within the engine's own Rashi (`premium_layout.sign_position`): taken from the printed decimal, truncated to whole arc-seconds (never rounded into the next Rashi), and refused if the longitude does not lie in the engine's Rashi. The only tolerance is half a display unit at a boundary, where the engine's unrounded classification can print as the boundary value. Navamsa is never recalculated; D9 placements are checked against `d9.houses`.
- **Requires** the complete engine response with `calculation_metadata` schema `/3`; the provenance page is built from it.
- **Palettes:** `premium_theme.json`. **OD-10 is decided: the owner approved the saffron Foundation design.** `baseline` maps the existing `theme.json` tokens, is the default and is the only palette the server renders; the request cannot choose a palette. `od10-candidate` (maroon / ivory / gold) was not selected and is kept only for historical comparison in development tools; it must never appear in customer-facing output.
- **Optional report name (KUN-UX-NAME-001):** `generate(..., display_name=None)`. The name must be the output of `display_name.normalize()` (otherwise `ValueError`). It is drawn as "Prepared for" under the cover title (the subtitle moves down and the cover emblem shrinks to keep the birth panel in place) and as the first "Name on report" row of the page-4 Birth record, and nowhere else; never in the PDF metadata. Without a name the bytes are identical to the renderer before this option (pinned SHA-256 for all 13 scenarios in `tests/test_premium_name.py`). Accepted: 80 visible Latin letters (with accents) or Devanagari characters, single spaces, apostrophes, hyphens and full stops; see `display_name.py`. Latin is drawn with the brand face's Latin or Latin Extended subset; Devanagari with Poppins Devanagari 600 (same `@fontsource/poppins@5.3.0` package, SIL OFL 1.1), shaped with HarfBuzz through `uharfbuzz==0.57.0` (Apache-2.0; HarfBuzz is MIT-licensed), drawn as glyph outlines with the same words as invisible text in logical order, so copy, search and text extraction return exactly the typed Unicode. Long names shrink to a minimum (11 pt cover, 8 pt page 4) and then wrap; a character no face can draw raises instead of being dropped or transliterated.
- **Report language (KUN-I18N-001):** `generate(..., locale='en')` takes `'en'` (default) or `'hi'`; anything else raises `report_locale.ReportLocaleError`. Every sentence, label and heading of the ten pages comes from `report_i18n.json` (English and Hindi side by side); Rashi, graha, Nakshatra, month, place and fixed engine sentences come from the terminology register in `prototype/kundali_prototype/static/i18n.json`, shared with the web page (see `docs/i18n/TERMINOLOGY.md`). The English catalog values are the exact PR #58 strings, so the English PDF, with the locale omitted or `'en'`, is byte-identical (pinned hashes, all 13 scenarios, with and without a name). The Hindi report has the same ten A4 pages and the same engine values; Devanagari is drawn with Poppins Devanagari 400/500/600/700 (the 400 face added from the same `@fontsource/poppins@5.3.0` package, SIL OFL 1.1), shaped with HarfBuzz, as cached glyph outlines with the logical-order text as an invisible layer, so copy, search and extraction return the catalog Unicode; the PDF `/Lang` is `hi`. Latin runs (codes, numbers, proper names) use the brand faces. A value the register does not know (a new place, a changed engine sentence) makes the Hindi report refuse instead of showing English or a guess. **The Hindi text is a developer draft pending independent human language review; it is not owner-approved.**
- **Fail closed:** unknown glyphs in engine-supplied text (for example a Devanagari place name), text that cannot fit, chart labels that cannot be placed legibly, an altered logo file, or a PDF over 1 MiB all raise instead of producing a degraded PDF.
- **Tests:** `tests/test_premium_report.py`, `tests/test_premium_name.py`, `tests/test_display_name.py` and `tests/test_report_i18n.py` (Hindi layout, extraction, shaping against libraqm, palette, fail-closed), with 13 synthetic scenarios in `tests/fixtures/premium/` built by `tools/make_premium_scenarios.py`. Set `SABPUJA_TEST_EPHE_PATH` to also require the engine to reproduce every scenario exactly.
- **Visual review:** `python report/phase1/tools/visual_review.py OUT_DIR` writes the sample PDFs, contact sheets, old/new and palette comparisons outside Git.

## Extended edition with Panchanga at birth (KUN-PAN-RPT-001, draft)

A separate, opt-in edition. The ten-page report above is the **standard edition** and stays the default and the rollback baseline: `generate(...)` and `render(...)` without a Panchanga document produce byte-identical PDFs to `main@07da75e` (pinned hashes, all 13 scenarios, EN/HI, with and without names). The preview server is not changed and cannot produce the extended edition.

```python
from report.phase1.premium_report import generate_extended
pdf = generate_extended(engine_response, panchanga_document, synthetic=False, palette='baseline',
                        display_name=None, locale='en')   # or locale='hi'
```

- **Input:** the `sabpuja-panchanga/1` document from the existing Panchanga M1 module (`sabpuja_kundali.panchanga.calculate`) for the *same* request as the chart. The renderer never calls the module and computes no astronomy.
- **13 A4 pages:** the ten pages, with three pages inserted before the methodology: *Panchanga at birth / जन्म के समय पंचांग* (Tithi, Paksha and Paksha day, Karana and Yoga numbers, Moon Nakshatra and Pada, elongation E and sum S, a Tithi ring and definitions), *Transition times / परिवर्तन समय* (start and end of each value in local time and UTC, with a timeline) and *Method and limits / पद्धति और सीमाएँ* (rules, transition search, data provenance, validation status in plain language, inclusions and exclusions). Contents, page numbers, cross-references, footers and the methodology inclusion/exclusion lists follow the new page plan.
- **No names for Tithi, Karana or Yoga** (D07-A, D16-M1-INDEX). Terms and sources: `docs/i18n/PANCHANGA-REPORT-TERMS.md`. Text: `report_panchanga_i18n.json` (developer draft, pending review); the approved ten-page catalog is unchanged.
- **Fail closed** (`panchanga_report.PanchangaReportError`) before any page is drawn when the document does not belong to the chart or is not the adopted one: other schema, validation status, claim boundary or method block (including any non-default search limits); different birth instant or zone; Moon Nakshatra/Pada not the chart's; E or S not consistent with the chart's Sun and Moon; a Tithi/Karana/Yoga number not consistent with its printed angle; Paksha, Karana-half or Pada nesting inconsistent; a transition that does not bracket birth or lies outside the frozen 2.5-day extent; a local time that is not the UTC instant in the birth zone (pinned tzdata), or that is withheld inside / rendered outside the 1970–2100 envelope; search records over the frozen limits; Swiss Ephemeris, ephemeris manifest or tzdata different from the chart's; chart ephemeris data not verified; unknown or missing fields.
- **Validation status** `ENGINEERING_UNVERIFIED_PENDING_INDEPENDENT_QA` is printed with a plain-language limitation. The edition is not for customers until independent QA and the owner approve it.
- **Tests:** `tests/test_panchanga_report.py` (fixtures `tests/fixtures/panchanga/`, captured from the 13 existing synthetic scenarios by `tools/make_panchanga_fixtures.py`). With `SABPUJA_TEST_EPHE_PATH` it also recomputes every fixture and runs live boundary cases (London summer-time start and end, repeated hour, birth exactly on a transition and one second before, last supported instant; minute rounding of displayed times at :29/:30, midnight, the summer-time gap and the repeated hour, failed and stricter-limit searches, refused inputs).
- **Review set:** `python report/phase1/tools/panchanga_review.py OUT_DIR` writes EN/HI extended and standard PDFs, page images and SHA-256 sums outside Git.
- **CLI:** `python report/phase1/premium_report.py CHART.json OUT.pdf --sample --panchanga-json PANCHANGA.json [--locale hi]`.

## Sunrise and Vara edition (KUN-PAN-RPT-002, draft, not for customers)

A further, separate opt-in edition, `extended-panchanga-m2-vara/1`: the 13-page Panchanga edition plus one page, *Sunrise and Vara / सूर्योदय और वार*, after the transition times (14 pages). Without a Vara document nothing changes: the ten-page and default 13-page PDFs stay byte-identical (pinned hashes, all scenarios, EN/HI, also after a Vara render).

```python
from sabpuja_kundali.panchanga import vara           # engine side: sabpuja-panchanga-vara/1
from report.phase1.premium_report import generate_extended
doc = vara.calculate(chart_request, ephe_path)
pdf = generate_extended(engine_response, panchanga_document, synthetic=False, palette='baseline',
                        locale='en', vara=doc)          # or locale='hi'
```

- **Convention:** `SUN-D-IMD-47` at the birthplace (PAN-D03, adopted for development only on PR #82 comment 6681108990): IMD's definition, upper limb with 31′ refraction and 16′ semidiameter, the Sun's centre 47′ below a level sea-level horizon, geocentric. Not a reproduction of IMD's Central Station or city tables. `SUN-A-USNO-50` stays test-only. Instants come from the QA-accepted `sun.py` (PR #82, c759c41), called only through `sun.vara()` and `sun.sun_day()`; `vara.py` adds no astronomy.
- **Shown:** the Vara (sunrise weekday, PAN-D05, half-open [sunrise, next sunrise)) with its governing sunrise date; the civil weekday of the birth date, separately and never substituted; sunrise, sunset (PAN-D17) and the next sunrise, rounded to the minute and marked *about / लगभग*, local and UTC; the time from the governing sunrise or to the next one; a day strip; and the method and limits (sea-level geocentric model, no weather, elevation or terrain; 120 s USNO/IMD screen is not an accuracy claim; IMD's four-city 47′–52′ discrepancy).
- **Near-sunrise caution:** when the birth is within 300 s (inclusive, on unrounded microsecond instants) of the governing or the next sunrise, a saffron caution asks the reader to check the birth time. The band is a presentation heuristic, not an accuracy claim.
- **Unavailable, never invented:** polar day or night, no sunrise on the date, a next sunrise that never comes (`VARA_DAY_END_UNDEFINED`), or a governing sunrise before 1 January 1970 show "Vara not given" with the typed reason and the civil weekday alone. A next sunrise after 31 December 2100 is not calculated and the caution says so.
- **Fail closed** (`vara_report.VaraReportError`) on any other schema, status, claim, method block (pinned SHA-256), birth instant, zone or coordinates; different Swiss Ephemeris, ephemeris or tzdata; a civil date or weekday that is not the birth instant's; a Vara that is not its sunrise date's weekday; event order or local times that do not match the UTC instants; a near-sunrise record that is not the instants; unknown reasons; or an unavailable Vara carrying events or a comparison.
- **Three M1 sentences** that would be untrue in this edition are replaced only here (`override.*` in `report_vara_i18n.json`): the birth-instant note now points to the sunrise page, the M1 exclusion "Sunrise, sunset and Vara" becomes "Panchanga at sunrise of the birth date", and the methodology lists the pages as "Panchanga, sunrise and Vara". Tithi, Karana and Yoga names stay QA-only (`names='qa_preview'` still combines with this edition).
- **Text:** `report_vara_i18n.json`, developer draft pending human Hindi, Jyotish and owner review.
- **Tests:** `tests/test_vara_report.py` (fixtures `tests/fixtures/vara/` for the 13 scenarios and `tests/fixtures/vara-cases/` for 12 synthetic boundary cases, from `tools/make_vara_fixtures.py`; 100 pinned 14-page hashes from `tools/make_vara_pins.py`) and `tests/panchanga/test_vara_doc.py` (engine document).
- **CLI:** `python report/phase1/premium_report.py CHART.json OUT.pdf --sample --panchanga-json PANCHANGA.json --vara-json VARA.json [--locale hi]`; `python -m sabpuja_kundali.panchanga.vara < request.json`.
