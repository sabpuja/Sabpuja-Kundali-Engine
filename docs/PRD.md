# Sabpuja Kundali Generator - Product Requirements Document

**Document ID:** SP-KUN-PRD-001  
**Version:** 1.0-rc1 (owner review required)  
**Date:** 2026-10-21  
**Status:** DRAFT - NOT APPROVED FOR IMPLEMENTATION  
**Canonical home:** `sabpuja/Sabpuja-Kundali-Engine/docs/PRD.md`  
**Owner:** Sabpuja human project owner | **PM / independent QA:** ChatGPT | **Lead implementer:** Claude / Claude Code

> This repository is the single project hub for Kundali requirements, decisions, engineering delivery, test evidence, and release documentation. Other repositories own the implementation of their respective systems (e.g. Shopify theme), but do not maintain a competing Kundali PRD. No changes to `sabpuja/core` are needed for this project plan.

## 1. Product thesis and decisions already made
Build a trustworthy, premium, **self-hosted Vedic Janam Kundali generator** at `sabpuja.com`, free for a useful first chart, with English and Hindi support and exportable results. It will use **Swiss Ephemeris locally** under **AGPL-3.0-only** for the Kundali combined work, and Sabpuja-authored Vedic rules, chart renderer, reports and integration. There will be **no third-party runtime astrology API**, no per-chart API charges and no outsourced personal birth data.

The project owner is final authority for scope, expense, privacy/product policy and release. Claude implements only bounded tickets and supplies reproducible evidence. ChatGPT owns PM/architecture oversight, independent code review and QA recommendations. A QA PASS does not authorize merge or deployment.

**Important:** Astronomical positions can be computed deterministically. Astrological meaning and remedy claims are traditional interpretations, not scientifically established predictions or guaranteed outcomes. Report language must reflect that distinction naturally and respectfully.

## 2. Audience and primary jobs
| Persona | Job to be done | UX requirement |
|---|---|---|
| First-time visitor | Enter birth information and understand basic Kundali | No mandatory account or purchase; simple form and clear summary |
| Returning learner | Review Rashi, Nakshatra and chart placements | Accessible, educational explanations and reusable PDF |
| Hindi-first visitor | Complete the journey in Hindi | Human-reviewed Hindi UI and report, transliteration-aware city search |
| Advanced astrology reader | Inspect chart positions and calculation methodology | Method metadata, planet degrees, D1/D9 and downloadable calculation data |
| Mobile visitor | Generate and navigate results comfortably | Fluid layout, responsive charts and no clipped controls |
| Sabpuja operator | Verify, debug, and safely maintain the tool | Pinned ephemeris/runtime, QA logs with no customer PII, controlled releases |

## 3. Success criteria and measurements
- **Product truth:** No numerical chart published unless it passes the mandatory engineering-accuracy gates for each supported convention: pinned Swiss Ephemeris integration conformance against the official Swiss CLI, independently coded rule and formula checks, and boundary and refusal fixtures. Public wording says positions are calculated with Swiss Ephemeris under the named conventions; it claims independent astronomical accuracy only if the optional JPL/INPOP assurance has been completed. No invented birth offset or time. (REL-01)
- **Ownership:** Calculation works without any runtime third-party astrology/geocoding API; source, ephemeris configuration and releases under Sabpuja control.
- **MVP value:** Visitor can enter precise birth information, render D1 and D9, read Rashi/Lagna/Nakshatra information, and export Hindi/English PDF without an account.
- **Trust:** Source/license notice accessible, calculation method presented, sensitive birth information excluded from logs and third-party analytics.
- **UX:** Responsive and accessible on common mobile, tablet, and desktop screen sizes; no critical information accessible only by color or images.
- **Performance targets (proposed):** authenticated/staging API p95 under 2 seconds for core chart calculation and PDF p95 under 10 seconds on an agreed Hostinger test configuration and representative warm/cold test set. Measure and revise after profiling, rather than asserting current performance.
- **Analytics:** Track aggregated form-start, validation-error count, chart-completed, language and PDF events without names, dates, times, coordinates or report content; only after privacy review.

## 4. Scope and priority
### P0 - Public MVP (launch blocking)
| Requirement | Required behavior / acceptance outcome |
|---|---|
| KUN-F01 Birth form | Date, exact local time, city/place selector, optional display name only if needed for PDF, English/Hindi locale. Clear precision and privacy messaging. No mandatory login. |
| KUN-F02 Offline birthplace | Resolve selected place to lat/long + canonical IANA timezone using locally stored, license-reviewed datasets. Ambiguous places require explicit selection; never guess. |
| KUN-F03 Historical time | Local birth date/time + IANA zone converted to UTC using versioned timezone rules. Reject nonexistent local times, disambiguate DST folds, verify explicit offsets when provided. |
| KUN-F04 Calculation methodology | Explicit Lahiri sidereal mode, mean Rahu, Ketu 180 degrees opposite, sidereal Lagna and whole-sign house model **as proposed baseline**, subject to documented owner acceptance and the REL-01 accuracy gates (mandatory engineering accuracy; independent astronomy optional). Output includes method and version metadata. |
| KUN-F05 D1 Janam Kundali | Planetary positions for Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, mean Rahu and Ketu; Rashi, house, longitude and Lagna; North Indian chart drawn from structured results. |
| KUN-F06 D9 Navamsa | Correctly computed D9 signs, D9 ascendant, sign/house placements as defined by validated D9 methodology; clear D9 label and chart. |
| KUN-F07 Core explanations | Lagna, Moon Rashi, Nakshatra/Pada, basic graha descriptions with documented rule identifiers and editorial review; traditional interpretation presented as guidance, not certainty. |
| KUN-F08 Transparent results | Visible birth place/time/timezone confirmation and calculation method/version; clear correction flow; safe explanation when an input cannot yield dependable time-dependent results. |
| KUN-F09 Hindi/English | Entire form, validation, result labels, chart legend, explanations and PDF in both languages; readable Devanagari fonts and human language review. |
| KUN-F10 Branded PDF | Download generated report containing entered profile details only when explicitly requested, calculation summary, North Indian D1 and D9, key placements, method/version, attribution and privacy-safe generation. |
| KUN-F11 Self-hosted API | Server-controlled backend on approved Hostinger deployment with strict input validation, rate limits, TLS, health endpoints, bounded work, request size limits, structured errors and no external astrology API. |
| KUN-F12 Shopify staging | Accessible, visually integrated `/pages/kundali` experience after sandbox/component validation. Shopify App Proxy or equivalent approved design; dynamic/editable commerce links; unpublished staging first. |
| KUN-F13 Accessibility | Keyboard accessible forms/tabs, labels/errors/assistive summaries for diagrams, text equivalence for planet tables, focus, contrast, reduced motion and 200% zoom check. |
| KUN-F14 Privacy/security | Transient processing by default, consent where necessary, no birth data in URLs, logs, analytics, repo, crash reports or CDN, sensible in-memory TTL and secure PDF download, no storage by default. |
| KUN-F15 License compliance | Review combined-work AGPL perimeter, notices, transitive dependency/data rights and network Corresponding Source offer before public activation. |
| KUN-F16 Verification/release | Real local tests, the REL-01 mandatory engineering-accuracy gates (independently sourced JPL/INPOP golden-chart validation optional), security/accessibility/Hindi QA, owner signoff and explicitly approved staging-to-production process. |

### P1 - After MVP (requires new owner-approved specs)
- Optional authenticated customer birth-profile saving in Sabpuja dashboard, consent, secure per-account authorization, export/deletion and retention policy.
- Vimshottari Mahadasha/Antardasha with source-defined conventions and separately validated golden fixtures.
- Additional divisional charts (D10 etc.), Yogas/Doshas and explanation library with documented interpretative differences.
- South Indian chart presentation and polished advanced tables.
- Kundali matching / Gun Milan as a **separate** algorithmic, cultural and privacy review scope.
- Helpful, explicitly optional links to puja guides and relevant real Shopify products; no fear-based sales or miracle promises.

### P2 / Explicitly excluded from MVP
- Paid astrology consultation, personalized predictions as certain facts, medical/financial/legal conclusions, remedy guarantees.
- Third-party astrology/geocoding/timezone APIs at runtime; mass retention or sale of birth profiles.
- Horoscope or astrological chart positions generated by LLMs; AI may only explain traceable structured deterministic results if separately approved.
- Hermes agent profile, autonomous agents, GitHub Actions, unattended deployment, production storefront edits prior to owner approval.
- Public promise of all historical years. **Initial supported validation window proposed: 1900–2100**; wider ephemeris availability is not a validated product guarantee.

## 5. User experience and flows
### Flow A - First-time visitor
1. Navigate through a Shopify menu link/landing page to Kundali. User sees value, privacy information and language selector.
2. Enter birth date, exact local time and select location from **offline** suggestions showing region/country to resolve duplicates. The service derives IANA timezone and confirms resolved birth information before calculating.
3. Resolve ambiguous/invalid time or place with human-actionable error. Never silently use noon/midnight or infer a city.
4. Generate chart. Show above-fold Lagna/Moon Rashi/Nakshatra overview; tab/scroll to D1, D9, positions, method/explanations, PDF.
5. Switch Hindi/English without losing user-entered data or changing numerical values. Generate PDF on explicit click. Correct birth information and recalculate safely.

### Flow B - Unknown or uncertain birth time
- V1 requires an exact birth time for time-dependent D1/D9/Lagna. If user does not know it, explain in ordinary language why reliable time-dependent results cannot be produced. Do **not** fabricate time or quietly downgrade to a full chart. An explicitly designed date-only educational feature may be specified in a later version.

### Flow C - Optional product discovery
- Educational content may link to approved Puja Guides or Shopify-derived product recommendations only when relevant and non-coercive. Never hardcode catalog price, inventory, products or religious guarantees. Commerce must not interrupt chart generation or PDF.

## 6. Calculation and data contract
- **Astronomical source:** pinned Swiss Ephemeris binding/library and versioned approved locally mounted ephemeris files with SHA-256 manifest; no silent Moshier fallback. Verify upstream dataset and binary distribution rights.
- **Input normalization:** local birth instant, validated timezone/offset, latitude/longitude, hemisphere, precision flags, canonical birthplace ID and language. Frontend name is optional and not an astronomy input.
- **Output contract:** versioned machine-readable JSON containing request/method metadata, sidereal degrees, D1 and D9 placements, Lagna and houses, Nakshatra/Pada; explicit units, enum identifiers, errors and status. Charts and language do not alter numerical outputs.
- **Method policy:** proposed Lahiri ayanamsa, mean lunar nodes, whole-sign houses; owner must accept named conventions, including D9 ascendant and sidereal house calculation details, **before** the scientific accuracy gate is signed.
- **Reference QA:** different source/process from implementation (for the mandatory gates: the separately built official Swiss CLI and independently coded rules/formulae; for optional assurance: JPL/INPOP) (REL-01); pin precise date/time/location/zone, ayanamsa, node, house model, dataset, precision and predeclared tolerances. Cover 1900/2100 edges, 29 Feb, 0/360-degree wrap, Rashi/Nakshatra/Pada/D9 transitions, UTC-midnight boundaries, high latitudes, historical offset changes and concurrency. Do not call unit tests proof of numerical accuracy.
- **Locale QA:** compare EN and HI numerical JSON for identity; proofread Devanagari, transliteration and typography, and keep numerical context on downloads.

## 7. Functional and nonfunctional acceptance
| Gate | Required demonstrable evidence | Owner approval needed? |
|---|---|---|
| Product approval | This PRD, assumptions and open decisions accepted | YES, before material new functionality |
| Astronomy accuracy | Reproducible unit/contract tests, Swiss CLI conformance and independent rule/formula fixtures with no blocking deviations (REL-01); independent JPL/INPOP fixtures only for an independent-accuracy claim | YES, before accurate-public claims |
| Location/time correctness | Offline dataset manifest, DST/historical cases, rejects ambiguity | QA plus owner for methodology change |
| Secure service | Threat model, auth/app proxy validation, quota tests, log scans, failure and abuse cases | YES, before publicly reachable endpoint |
| UI and i18n | Component Lab previews, fluid/accessibility mobile tests, bilingual human review | YES, before store install |
| PDF/privacy | Real export QA, PII minimization, secure links, deletion/nonretention behavior | YES, before public release |
| AGPL/license | Upstream license review, combined work assessment, working source link, data rights | YES, before network activation |
| Release | Staging tests, explicit release checklist, rollback and operator approval | YES, production separately |

### Security/privacy essentials
Collect the minimum necessary. Never put date/time/location in query strings or logs. Default to stateless processing and no customer record storage; generated reports must not be world-readable or permanently cached. Consent, storage, deletion and eligibility for minors need a separately approved design before profiles are added. Check applicable Indian privacy obligations with qualified review; do not assume the public source license covers privacy compliance.

### Brand/content essentials
Use only approved Sabpuja design tokens and logo source from the design-system repository; deep maroon #681E30, antique gold #BE9148, champagne beige #E9D9BA, charcoal #2F2926, warm ivory. Premium, informative, respectful, fluid-first `clamp()` responsive layout and readable charts. Avoid old branding, green catalog imagery, long dashes, artificial scarcity, false expertise and promotional claims.

## 8. Dependencies and integration boundaries
- **Canonical project docs and computational engine:** `sabpuja/Sabpuja-Kundali-Engine` (this repo).
- **Storefront implementation only:** `sabpuja/theme` on a separately approved **unpublished** Shopify theme. Verify exact theme ID immediately before any future write. The Kundali product PRD remains here.
- **Brand authority only:** `sabpuja/design-system`. Do not duplicate approved logo masters.
- **VPS deployment:** approved Hostinger runtime, container isolation, pinned artifacts/data; no access or deployment authorization is granted by this PRD.
- **Team:** Owner approves, ChatGPT PM/QA reviews on explicit handoffs, Claude develops via scoped PRs; Claude credentials must be configured separately.

## 9. Risks and open decisions
See [DECISIONS.md](DECISIONS.md) for questions requiring owner selection. Top launch risks: AGPL combined-work boundary, sidereal Lagna precision, dataset licensing, time-zone historical correctness, Indian city collisions, data leakage, Hindi text rendering and unverified astrology interpretation claims. Block launch rather than asserting completion when evidence is missing.

## 10. Traceability, change control and approval
Every Claude issue/PR must cite at least one KUN-F## identifier and roadmap work package. The [acceptance matrix](ACCEPTANCE-MATRIX.md) holds concrete QA IDs and owner gates. Significant scope, science methods, licensing, personal data collection or storefront changes require owner decision recorded in [DECISIONS.md](DECISIONS.md). Do not treat this **draft** as final authorization.

**Owner approval record (blank until explicitly decided)**  
- Decision: PENDING  
- Approver: Sabpuja project owner  
- Approved version/commit: PENDING  
- Agreed open decision resolutions: PENDING  
- Date: PENDING
