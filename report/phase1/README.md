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
