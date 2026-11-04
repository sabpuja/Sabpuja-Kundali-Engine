# Sabpuja Premium Kundali Report — Product Specification RFC 0.1

**27 October 2026 | Status: PROPOSED FOR OWNER REVIEW, NOT CANONICAL | Public release: NO-GO**

## North star and non-negotiables

Create an exceptionally comprehensive, readable, evidence-traceable Vedic Kundali product, not a thin PDF export or a padded 300-page report. Compete on scientific calculation integrity, transparent astrological traditions, usefulness, distinctive design, accessibility, secure delivery and substantive interpretive depth. The current eight-page Phase 1 PDF is a verified technical starting point only.

**Current verified foundation:** exact Phase 1 PDF/download candidate f808eacfd677beca85c2eb33b8107def9ef12c71, stacked on reviewed PRs #45/#44, with D1, D9, chart schema 0.3.0, Lahiri, mean lunar nodes, whole-sign houses, Swiss calculation and locked timezone policy. Independent C7 execution on PR #42 passed its scoped engineering suite. This does not mean comprehensive golden-chart or interpretation certification. Keep metadata schema /3. Public release HOLD remains.

### Nonnegotiable quality rules

1. Every numeric calculation has an exact scientific-method contract, pinned version, golden/reference cases, boundary cases, reproducible inputs and negative-input refusals. Display full precision internally; round only for presentation.
2. Astrological interpretation is explicitly framed as traditional/interpretive, never as guaranteed factual prediction. Each rendered insight carries rule ID, chart facts, method version and interpretation-source provenance; no invented yogas, dasas, doshas or life events.
3. Distinguish astronomical measurement, classical astrological rule and authored interpretation, in both data and UX. Predictions about health, wealth or marriage must not claim certainty or replace professional advice.
4. Download documents are generated from validated server-calculated data only. No accidental PII in server logs; minimize retention, provide export controls; test accessibility, PDF fonts, print and privacy.
5. Report quality means compact navigation, meaningful summaries and detailed drill-down, not repeated paragraphs, inflated page count or AI-generated filler.
6. Preserve existing approved brand marks/fonts and tokens; Poppins headlines, Inter body, accessible contrast, crisp North Indian charts, consistent gold/ivory/maroon tokens according to the current canonical brand pack.
7. English first, Hindi planned; never silently translate Sanskrit terminology incorrectly.

## Benchmark evidence (verified public competitor materials, not evidence of their accuracy)

| Reference | Observed offering | Sabpuja design lesson |
| --- | --- | --- |
| Prokerala [one-page PDF](https://api.prokerala.com/reports/sample/single-page-horoscope-en.pdf) | Birth Panchang (tithi, yoga, karana, nakshatra, sunrise/sunset), planet positions, D1/D9, dasha balance and current period on one page | A strong quick summary ought to include Panchanga and dasha, not charts alone |
| [Prokerala PDF samples](https://api.prokerala.com/pdf-reports) | Separate multi-page compatibility, transit, Year Guide and natal modules; multilingual samples | Modular product architecture and specialized SKUs |
| [Clickastro In-depth](https://www.clickastro.com/in-depth-horoscope) | Advertises over 300 pages with Dasa-Apahara, yogas, doshas, life-area readings and remedies | Premium buyers expect holistic coverage; avoid copying claims or padding |
| [Clickastro report download](https://www.clickastro.com/horoscope-report-download) | Advertises Panchanga, Dasa, yoga, Ashtakavarga, transit, remedies and specialized life areas | Coverage matrix needed before premium marketing |
| [Jagannatha Hora updates](https://jagannathahora.com/whats-new) | Documents extensive classical calculation variants, sunrise/Panchanga, transit and strength conventions | Define exact methods; similar feature labels need not imply identical math |

These are feature/format benchmarks only. We have not certified vendors' calculations or obtained licenses to reproduce proprietary copy, images or page designs.

## Proposed digital products (not pricing or launch promises)

1. **Kundali Essentials**: clear birth details, location/clock disclosure, five-limb birth Panchanga, D1 and D9, planetary/nakshatra data, birth dasha balance, transparent methodology and compact PDF. Free/entry product only once new modules pass.
2. **Kundali Premium**: Essentials plus validated Vimshottari full Maha/Antar/Pratyantar timelines, supported extra vargas, house/planet narrative, rigorously detected yogas/doshas and focused life themes. Target around 45–80 meaningful pages, depending on actual features and content; never fabricate pages to hit a target.
3. **Kundali Comprehensive / Professional**: Premium plus validated Shadbala, Ashtakavarga, additional divisional charts, transits, context-specific annual timeline, uncertainty sensitivity, rich method appendices. Only market the sections we have independently tested. A 100+ page possibility is not a delivery commitment.
4. **Specialized modular reports**: compatibility (mutual consent), career, marriage, annual guide, Saturn/Jupiter transit, auspicious timing, and eventually localized editions. Independent calculations, editorial sources, consent and safety gates per SKU.

### Canonical report information architecture — proposed sequence

| Section | Content | Gate |
| --- | --- | --- |
| Cover, contents, quick reading guide | Approved Sabpuja logo; section navigation; timestamp and method profile | Design & provenance |
| Birth input and astronomical audit | Birth city/coordinates, source, IANA timezone version, UTC/offset disambiguation, Lahiri/Swiss/mean-node/whole-sign summary | Engineering |
| Birth Panchanga | Tithi, vara, nakshatra/pada, yoga, karana; sunrise/sunset and boundaries if method approved | New scientific gate |
| Natal chart atlas | D1/D9 North Indian SVGs, positions, house tables; only tested additional D-charts | Engineering |
| Graha/Bhava deep dive | Measurable chart facts, each house and planet, documented interpretive references | Both gates |
| Dasha timing | Birth balance, MD/AD/PD nested intervals, deterministic boundary logic, user-friendly timeline | New scientific gate |
| Combinations and strength | Versioned yogas/doshas, strengths, Ashtakavarga and uncertainty notes **only as approved** | Separate gates |
| Life-theme narratives | Career, studies, relationships, family, spirituality; specific supporting chart facts; no guaranteed outcomes | Report-quality |
| Ritual/observance and remedies | Tradition-specific, optional, not coercive, no high-risk medical/financial advice | Editorial/religious source & safety |
| Detailed tables and provenance | Exact calculation methodology, data-source rights, definitions, timestamp, unsupported features | Engineering |
| Privacy, license and support | Personal-data handling, AGPL/Swiss/GeoNames notices, correction flow | Legal/security |

### Interface and PDF acceptance

- Rich, visually balanced cards and navigation, legible 8–11 pt printed tables, 300-DPI-equivalent print assets or vector charts, searchable text, properly embedded licensed fonts, accessible HTML keyboard operation, print margins and headings.
- Display exact supported-region/date boundaries before collecting birth information. Prefer location choice plus disambiguation and explicit timezone/refusal to silently inferred coordinates.
- Browser QA at 280 / 375 / 768 / 1440 CSS px; A4 PDF review on every page, correct Devanagari when released, no clipped charts, no duplicate filler, no mismatched values between UI and report.
- Cross-reference every displayed numeric value to validated engine payload; schema compatibility must be explicit, no quiet modification to 0.3.0 or calculation metadata /3.
- AI assistance, if eventually used for prose, must consume structured verified facts; deterministic rules + curated editorial copy precede generative language. Include source-backed uncertainty, prohibit hallucinated yogas or claims.

## Two independent acceptance gates

**Gate ENG — Engineering accuracy** (separate exact-SHA signoff):
- Pinned environment, ephemeris integrity, timezone/coordinate coverage, formulas and day/sunrise boundaries, numerical reference charts from independent tools/data, refusal behavior, full regressions, schema backward compatibility and adversarial security tests.
- Test each new computation near wrap boundaries, DST folds/gaps, leap days, 0°/360°, sunrise, polar exclusions, date-limit edges and subperiod cutovers.
- If any required reference or method choice is not authoritative, keep the module EXPERIMENTAL and out of customer-visible PDFs.

**Gate RPT — Report quality** (independent of ENG):
- Expert editorial review of interpretation-to-rule mapping, traditional differences, non-deterministic language, cultural sensitivity, clarity, readability, no page padding, design system, EN/HI correctness when implemented, accessibility, synthetic PDF visual QA and privacy.
- No rule-grounding gaps, unsupported remedial claims or contradictory narratives. Sample set spans multiple ascendants, dasha sequences and high/low latitude.
- Only a module with ENG PASS **and** RPT PASS may be marked sellable.

## Commercial release criteria

No payment, general client invitation, public site, marketing 'most accurate' claim, automated real-birth-data storage or Shopify integration while release HOLD remains. Owner-only synthetic preview can continue with exact-SHA QA. Before any paying-customer use, separately approve privacy policy/data deletion, payment/refund/licensing, access/rate policy, support workflow and C7/HOLD reconciliation.

## First backlog, in order

P0: close owner HTTPS security/browser revocation/log/reverse-proxy checks and owner review.
P1: Panchanga calculation RFC, independent fixtures and scientific approval; then engine code and Gate ENG.
P1: Vimshottari Dasha convention RFC and independent fixtures; then engine code and Gate ENG.
P1: birthplace search/data-policy specification with robust coordinates, timezone source, unsupported/refusal behavior.
P2: D10 and selected extra charts **after individual transformation-method approval**.
P2: authored/peer-reviewed premium report copy and rule-to-claim provenance register, beginning only with ENG-passed modules.
P3: advanced strengths, charts and specialized digital product bundles.

**Owner decision still required:** accept or revise the product tiers, priority order, science conventions in the companion RFC, and desired marketable report depth. This RFC does not override docs/DECISIONS.md or authorize any code merge or client release.
