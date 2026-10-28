# Sabpuja Kundali Generator - Product Requirements Document

**Document ID:** SP-KUN-PRD-001  
**Version:** 1.1-proposed (rebaseline draft, owner review required). Supersedes 1.0-rc1 (2026-10-21) only after an owner-authorized merge.\
**Date:** 2026-10-28 · **Evidence cut-off:** 2026-10-27\
**Status:** DRAFT - NOT APPROVED FOR IMPLEMENTATION. Proposed by Claude under [CLAUDE-DOC-014 / issue #49](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/49) from `main` `2f67c648f7c7e02dade58bd72993722d06cb1cd3`.\
**Canonical home:** `sabpuja/Sabpuja-Kundali-Engine/docs/PRD.md` · **Website:** [sabpuja.com](https://sabpuja.com)\
**Owner:** Sabpuja human project owner | **PM / independent QA:** ChatGPT | **Sole lead developer:** Claude / Claude Code

> This repository is the single project hub for Kundali requirements, decisions, engineering delivery, test evidence, and release documentation. Other repositories own the implementation of their respective systems (e.g. Shopify theme), but do not maintain a competing Kundali PRD. No changes to `sabpuja/core` are needed for this project plan.

> **How to read this revision.** Three layers are kept deliberately separate:
> 1. **Original public MVP (P0) targets**, sections 1 to 10, unchanged in substance from 1.0-rc1. They remain the launch goals. None is shipped to the public.
> 2. **Current status snapshot as of 2026-10-27**, section 11. It records what exists, under six separate categories, with links to exact commits.
> 3. **Proposed comprehensive-report scope (KUN-P1-ADV)**, sections 12 and 13. These are proposed requirements, not approved scientific methods or completed features.
>
> Nothing in this revision records a new owner approval, changes a canonical scientific decision in [DECISIONS.md](DECISIONS.md), or relaxes a release safeguard.

## Status at a glance (as of 2026-10-27)

- **Public product:** not released. **Production: NO-GO.** No Shopify integration exists.
- **Engine:** the D1/D9 engine with chart schema `0.3.0` passed ChatGPT's independent C7 engineering execution at draft PR #42 `185353a1de8e5da02d20ea156cd4fca225fc1a27` (474 engine and 106 prototype tests, Swiss D3 v2 PASS). It is **not merged into `main`**, and the [PR #1 HOLD](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1#issuecomment-6323581875) remains active.
- **Restricted preview:** an owner-only, password-protected HTTPS preview on Hostinger runs draft PR #46 `f808eacfd677beca85c2eb33b8107def9ef12c71`. It is English-first, offers ten curated Indian birthplaces, accepts local birth dates from 1970-01-01 to 2100-12-31, and produces an eight-page Phase 1 PDF. It is **not** the public MVP, and synthetic data only has been used.
- **Comprehensive reports** (Panchanga, Vimshottari Dasha, more divisional charts, Yogas and Doshas, strengths, transits, interpretations, premium reports) are **proposed**, not approved or built.

## 0. Project roles and operating rules

These roles restore the governance in [DEC-003](DECISIONS.md#confirmed-owner-direction) and the [PR #1 governance contract](https://github.com/sabpuja/Sabpuja-Kundali-Engine/blob/feat/initial-kundali-foundation-20261021/docs/project-governance.md). They are restated here, not changed.

| Role | Holder | Responsibilities | Must not |
|---|---|---|---|
| Owner | Sabpuja human project owner | Final decisions on product scope, scientific conventions, budgets, merges and deployments; editorial and release acceptance | - |
| Sole lead developer | Claude / Claude Code | Engineering implementation, documentation updates, test execution, bug fixes and draft PR preparation with exact-SHA evidence | Approve its own implementation, merge, deploy, or silently change conventions |
| Project Manager and independent QA reviewer | ChatGPT | Planning, architecture oversight, requirements, acceptance criteria, technical audits, independent test verification, PASS / CHANGES REQUESTED recommendations | Act as the lead implementer of product code or tests that it then reviews |

**Required sequence for all significant work:** Owner authorization → Claude implementation → Claude test evidence → ChatGPT independent QA → Owner merge authorization → Controlled deployment → Release QA.

- A QA PASS is a recommendation, not a merge or deployment authorization. A merge is not a deployment. A restricted preview is not a release.
- Unresolved owner decisions are never assumed approved. Proposed defaults stay proposed until recorded in [DECISIONS.md](DECISIONS.md) through the two-step rule there.
- **Independence correction (2026-10-27).** Draft PR [#48](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/48) contains experimental Panchanga/Vimshottari arithmetic written by ChatGPT, not Claude ([governance clarification 6442494969](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/48#issuecomment-6442494969)). It is **non-canonical**. It must not be merged, cherry-picked, imported, or treated as independently developed or reviewed scientific implementation. When a new calculation module is authorized, Claude implements it from owner-approved methodology and independently sourced reference cases, and ChatGPT then reviews the exact Claude-authored SHA.
- **Open authorship question.** The commits on draft PRs #44, #45 and #46 (preview gateway, PDF renderer, PDF download) carry the same Git author identity as PR #48 and the PM documentation PRs #3 and #47, not the Claude identity and session trailers used on Claude-authored PRs such as #41, #42 and #43. Their implementation independence is therefore unconfirmed. This revision records their functional evidence factually and leaves the disposition to the owner ([OD-12](#14-open-owner-decisions)).

## 1. Product thesis and decisions already made
Build a trustworthy, premium, **self-hosted Vedic Janam Kundali generator** at `sabpuja.com`, free for a useful first chart, with English and Hindi support and exportable results. It will use **Swiss Ephemeris locally** under **AGPL-3.0-only** for the Kundali combined work, and Sabpuja-authored Vedic rules, chart renderer, reports and integration. There will be **no third-party runtime astrology API**, no per-chart API charges and no outsourced personal birth data.

The project owner is final authority for scope, expense, privacy/product policy and release. Claude implements only bounded tickets and supplies reproducible evidence. ChatGPT owns PM/architecture oversight, independent code review and QA recommendations. A QA PASS does not authorize merge or deployment.

**Important:** Astronomical positions can be computed deterministically. Astrological meaning and remedy claims are traditional interpretations, not scientifically established predictions or guaranteed outcomes. Report language must reflect that distinction naturally and respectfully.

### 1.1 Expanded product vision (proposed, 2026-10-27)
*Proposed by the owner for this revision. It extends, and does not replace, the thesis above.*

Build a **best-in-class, comprehensive Vedic astrology reporting platform**, not merely a basic Kundali generator. Sabpuja intends to compete with premium astrology-report offerings through:
- numerical accuracy and transparent, versioned calculation methods;
- calculation depth (Panchanga, Dasha, divisional charts, strengths, transits);
- genuinely useful, traceable interpretations framed as traditional guidance;
- premium report design, accessibility and bilingual (English/Hindi) delivery;
- personalization and a respectful customer experience.

The **free Kundali proposition is preserved**: a useful free chart and downloadable PDF without an account. Entry-level, premium and professional report offerings are kept separate from it (section 12.3). Commercial tiers, page counts and prices remain **subject to owner approval**. Competitor and product research in draft PR [#47](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/47) is reference material only, not an approved canonical specification.

## 2. Audience and primary jobs
| Persona | Job to be done | UX requirement |
|---|---|---|
| First-time visitor | Enter birth information and understand basic Kundali | No mandatory account or purchase; simple form and clear summary |
| Returning learner | Review Rashi, Nakshatra and chart placements | Accessible, educational explanations and reusable PDF |
| Hindi-first visitor | Complete the journey in Hindi | Human-reviewed Hindi UI and report, transliteration-aware city search |
| Advanced astrology reader | Inspect chart positions and calculation methodology | Method metadata, planet degrees, D1/D9 and downloadable calculation data |
| Mobile visitor | Generate and navigate results comfortably | Fluid layout, responsive charts and no clipped controls |
| Sabpuja operator | Verify, debug, and safely maintain the tool | Pinned ephemeris/runtime, QA logs with no customer PII, controlled releases |
| Premium report buyer *(proposed)* | Buy a deeper, well-designed report on specific life themes or periods | Clear statement of what each report contains and which methods it uses; no padded pages; no guaranteed predictions |

## 3. Success criteria and measurements
- **Product truth:** No numerical chart published unless it passes the mandatory engineering-accuracy gates for each supported convention: pinned Swiss Ephemeris integration conformance against the official Swiss CLI, independently coded rule and formula checks, and boundary and refusal fixtures. Public wording says positions are calculated with Swiss Ephemeris under the named conventions; it claims independent astronomical accuracy only if the optional JPL/INPOP assurance has been completed. No invented birth offset or time. (REL-01)
- **Ownership:** Calculation works without any runtime third-party astrology/geocoding API; source, ephemeris configuration and releases under Sabpuja control.
- **MVP value:** Visitor can enter precise birth information, render D1 and D9, read Rashi/Lagna/Nakshatra information, and export Hindi/English PDF without an account.
- **Trust:** Source/license notice accessible, calculation method presented, sensitive birth information excluded from logs and third-party analytics.
- **UX:** Responsive and accessible on common mobile, tablet, and desktop screen sizes; no critical information accessible only by color or images.
- **Performance targets (proposed):** authenticated/staging API p95 under 2 seconds for core chart calculation and PDF p95 under 10 seconds on an agreed Hostinger test configuration and representative warm/cold test set. Measure and revise after profiling, rather than asserting current performance.
- **Analytics:** Track aggregated form-start, validation-error count, chart-completed, language and PDF events without names, dates, times, coordinates or report content; only after privacy review.
- **Report value (proposed):** a paid module is classified as sellable only after both the ENG and RPT gates in section 13 pass on the exact delivered variant. An ENG PASS alone never validates an astrological interpretation or prediction.

## 4. Scope and priority
### P0 - Public MVP (launch blocking)
*Unchanged targets from 1.0-rc1. Current progress against each is in [section 11.3](#113-p0-requirement-status); none is released to the public.*

| Requirement | Required behavior / acceptance outcome |
|---|---|
| KUN-F01 Birth form | Date, exact local time, city/place selector, optional display name only if needed for PDF, English/Hindi locale. Clear precision and privacy messaging. No mandatory login. |
| KUN-F02 Offline birthplace | Resolve selected place to lat/long + canonical IANA timezone using locally stored, license-reviewed datasets. Ambiguous places require explicit selection; never guess. |
| KUN-F03 Historical time | Local birth date/time + IANA zone converted to UTC using versioned timezone rules. Reject nonexistent local times, disambiguate DST folds, verify explicit offsets when provided. |
| KUN-F04 Calculation methodology | Explicit Lahiri sidereal mode, mean Rahu, Ketu 180 degrees opposite, sidereal Lagna and whole-sign house model **as proposed baseline**, subject to documented owner acceptance and the REL-01 accuracy gates (mandatory engineering accuracy; independent astronomy optional). Output includes method and version metadata. *(Status 2026-10-27: these conventions are canonical in [DECISIONS.md](DECISIONS.md), SCI-01a to SCI-01h, each only to its recorded scope.)* |
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
- Vimshottari Mahadasha/Antardasha with source-defined conventions and separately validated golden fixtures. *(Expanded as proposed KUN-A02, section 12.)*
- Additional divisional charts (D10 etc.), Yogas/Doshas and explanation library with documented interpretative differences. *(Expanded as proposed KUN-A03, KUN-A05 and KUN-A08.)*
- South Indian chart presentation and polished advanced tables.
- Kundali matching / Gun Milan as a **separate** algorithmic, cultural and privacy review scope. *(Covered by proposed KUN-A10.)*
- Helpful, explicitly optional links to puja guides and relevant real Shopify products; no fear-based sales or miracle promises.
- **Proposed comprehensive-report scope (KUN-P1-ADV):** see [section 12](#12-proposed-comprehensive-report-scope-kun-p1-adv). Proposed, not approved.

### P2 / Explicitly excluded from MVP
- Paid astrology consultation, personalized predictions as certain facts, medical/financial/legal conclusions, remedy guarantees.
- Third-party astrology/geocoding/timezone APIs at runtime; mass retention or sale of birth profiles.
- Horoscope or astrological chart positions generated by LLMs; AI may only explain traceable structured deterministic results if separately approved.
- Hermes agent profile, autonomous agents, GitHub Actions, unattended deployment, production storefront edits prior to owner approval.
- Public promise of all historical years. **Initial supported validation window proposed: 1900–2100**; wider ephemeris availability is not a validated product guarantee. *(Status 2026-10-27: under canonical SCI-03 Option B, every birthplace before 1970-01-01 is refused with `HISTORICAL_CLOCK_UNVERIFIED` until DATA-01 verifies it, so the usable window today is 1970-01-01 to 2100-12-31.)*

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

### Flow D - Premium report purchase (proposed, not approved)
- After a free chart, a visitor may see clearly described optional reports. Each description states the modules included, the methods used and what the report does not claim. Purchase, payment, delivery and data retention need separate owner, privacy and legal approval (KUN-A09, KUN-A10, Workstream E) and are out of scope until then.

## 6. Calculation and data contract
- **Astronomical source:** pinned Swiss Ephemeris binding/library and versioned approved locally mounted ephemeris files with SHA-256 manifest; no silent Moshier fallback. Verify upstream dataset and binary distribution rights.
- **Input normalization:** local birth instant, validated timezone/offset, latitude/longitude, hemisphere, precision flags, canonical birthplace ID and language. Frontend name is optional and not an astronomy input.
- **Output contract:** versioned machine-readable JSON containing request/method metadata, sidereal degrees, D1 and D9 placements, Lagna and houses, Nakshatra/Pada; explicit units, enum identifiers, errors and status. Charts and language do not alter numerical outputs. *(Status 2026-10-27: canonical chart schema `0.3.0`, [SCI-02 C2](DECISIONS.md#sci-02-c2---gate-3e-chart-schema-030-canonical-adoption---2026-10-26), with calculation metadata `sabpuja-calculation-metadata/3`. New modules must use separately versioned, owner-approved contracts and must not silently add fields to `0.3.0`.)*
- **Method policy:** proposed Lahiri ayanamsa, mean lunar nodes, whole-sign houses; owner must accept named conventions, including D9 ascendant and sidereal house calculation details, **before** the scientific accuracy gate is signed. *(Status 2026-10-27: accepted as canonical SCI-01a to SCI-01h and SCI-01b/c; see [DECISIONS.md](DECISIONS.md).)*
- **Reference QA:** different source/process from implementation (for the mandatory gates: the separately built official Swiss CLI and independently coded rules/formulae; for optional assurance: JPL/INPOP) (REL-01); pin precise date/time/location/zone, ayanamsa, node, house model, dataset, precision and predeclared tolerances. Cover 1900/2100 edges, 29 Feb, 0/360-degree wrap, Rashi/Nakshatra/Pada/D9 transitions, UTC-midnight boundaries, high latitudes, historical offset changes and concurrency. Do not call unit tests proof of numerical accuracy.
- **Locale QA:** compare EN and HI numerical JSON for identity; proofread Devanagari, transliteration and typography, and keep numerical context on downloads.
- **New calculation modules (proposed):** each new module in section 12 needs, before code is merged, an owner-approved method record in [DECISIONS.md](DECISIONS.md), a versioned output contract, Claude-implemented code, independently sourced reference cases that the implementer did not derive from its own code, and the ENG gate in section 13.

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
| Module ENG and RPT *(proposed)* | Section 13: ENG for every new calculation module; RPT for every interpretive or report module; both before a module is sellable | YES, per module |

### Security/privacy essentials
Collect the minimum necessary. Never put date/time/location in query strings or logs. Default to stateless processing and no customer record storage; generated reports must not be world-readable or permanently cached. Consent, storage, deletion and eligibility for minors need a separately approved design before profiles are added. Check applicable Indian privacy obligations with qualified review; do not assume the public source license covers privacy compliance.

### Brand/content essentials
Use only approved Sabpuja design tokens and logo source from the design-system repository; deep maroon #681E30, antique gold #BE9148, champagne beige #E9D9BA, charcoal #2F2926, warm ivory. Premium, informative, respectful, fluid-first `clamp()` responsive layout and readable charts. Avoid old branding, green catalog imagery, long dashes, artificial scarcity, false expertise and promotional claims.

*Note (2026-10-27):* draft PR #45 pins the current storefront tokens from `sabpuja/design-system` (`tokens/tokens.css` blob `b371e009bb0d655c94695acb0ff8ec381fed9135`: saffron, gold, ivory and neutrals, "no maroon interface palette"). That differs from the palette named in the paragraph above. Which palette is canonical for Kundali reports is an owner decision ([OD-10](#14-open-owner-decisions)); this revision does not change the paragraph.

## 8. Dependencies and integration boundaries
- **Canonical project docs and computational engine:** `sabpuja/Sabpuja-Kundali-Engine` (this repo).
- **Storefront implementation only:** `sabpuja/theme` on a separately approved **unpublished** Shopify theme. Verify exact theme ID immediately before any future write. The Kundali product PRD remains here.
- **Brand authority only:** `sabpuja/design-system`. Do not duplicate approved logo masters.
- **VPS deployment:** approved Hostinger runtime, container isolation, pinned artifacts/data; no access or deployment authorization is granted by this PRD.
- **Team:** Owner approves, ChatGPT PM/QA reviews on explicit handoffs, Claude develops via scoped PRs; Claude credentials must be configured separately.

## 9. Risks and open decisions
See [DECISIONS.md](DECISIONS.md) for questions requiring owner selection, and [section 14](#14-open-owner-decisions) for the decisions raised by this revision. Top launch risks: AGPL combined-work boundary, sidereal Lagna precision, dataset licensing, time-zone historical correctness, Indian city collisions, data leakage, Hindi text rendering and unverified astrology interpretation claims. Block launch rather than asserting completion when evidence is missing.

Additional risks identified by 2026-10-27:
- **Preview runtime drift:** the restricted preview runs gateway settings patched on the server outside Git (permitted Origin, file mode, and a trusted upstream IP `172.28.0.3` for real-IP throttling). **Control:** that IP can change if the edge proxy (Caddy) container is recreated. Any recreation must be followed by revalidating the trusted-IP line and re-running the per-client throttling checks before the preview is used again.
- **Narrow privacy evidence:** the preview log scan searched only for three known synthetic input values. It is not a general privacy certification.
- **Comprehensive-report scope creep:** premium content can outrun validated calculations. Only ENG-passed data may feed RPT content.
- **Role separation:** see the PR #48 correction and the open authorship question in section 0.

## 10. Traceability, change control and approval
Every Claude issue/PR must cite at least one KUN-F## identifier (or, once adopted, a KUN-A## identifier) and roadmap work package. The [acceptance matrix](ACCEPTANCE-MATRIX.md) holds concrete QA IDs and owner gates. The requirement-to-milestone traceability is in [DEVELOPMENT-ROADMAP.md section 11](DEVELOPMENT-ROADMAP.md#11-requirement-to-milestone-traceability). Significant scope, science methods, licensing, personal data collection or storefront changes require owner decision recorded in [DECISIONS.md](DECISIONS.md). Do not treat this **draft** as final authorization.

**Owner approval record (blank until explicitly decided)**  
- Decision: PENDING  
- Approver: Sabpuja project owner  
- Approved version/commit: PENDING  
- Agreed open decision resolutions: PENDING  
- Date: PENDING

## 11. Current status snapshot (as of 2026-10-27)
*Evidence cut-off 2026-10-27. Every status below is tied to an exact commit and a GitHub record. "Completed" never means merged, deployed or released unless that is stated.*

### 11.1 Status by category
| Category | What is true today | Evidence |
|---|---|---|
| **Canonical policy** (on `main`) | Swiss Ephemeris integration conventions SCI-01a to SCI-01h and SCI-01b/c; REL-01 release-evidence policy; SCI-03 date window, historical-clock Option B, D3 v2, pinned `tzdata==2026.5`; chart schema `0.3.0` (SCI-02 C2); metadata `/3` retained | [DECISIONS.md](DECISIONS.md); adoption merge `5b71408fadc4634805b56dbcff0c19f941830eb0`; schema 0.3.0 merged by docs-only [PR #43](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/43) at `main` `2f67c648f7c7e02dade58bd72993722d06cb1cd3` |
| **Drafted feature code** (unmerged) | Engine hardening, prototype and D1/D9 charts (stack #39/#40 → #41 → #42); owner-preview gateway (#44); Phase 1 PDF renderer (#45); PDF download (#46). All are draft and unmerged; none is on `main` | [#41](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/41) `6c9e67069f86aa5c7e91771905d3cb5de2e66d69`, [#42](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/42) `185353a1de8e5da02d20ea156cd4fca225fc1a27`, [#44](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/44) `b436134fbcd82e0f3c510485c244f968dbb9deea`, [#45](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/45) `15b048b5587a0da819025177bc0db0d902447a5b`, [#46](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/46) `f808eacfd677beca85c2eb33b8107def9ef12c71` |
| **Independent QA** (ChatGPT, exact SHA, Claude-authored code) | C7 engineering execution PASS at `185353a` (474/0/0 engine, 106/0/0 prototype, Swiss D3 v2 PASS 24/24); Gate 3E scoped source/rule/UI PASS | [C7 5647737922](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/42#pullrequestreview-5647737922), [Gate 3E 5646798499](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/42#pullrequestreview-5646798499) |
| **Reviewer-executed functional and HTTPS QA** (ChatGPT, exact SHA; builder/reviewer independence unresolved, OD-12) | Preview gateway isolated PASS (#44); Phase 1 PDF isolated PASS (#45); PDF download isolated PASS (#46); real-HTTPS four-category synthetic QA PASS. These results stand as functional test evidence within their stated scope. They are not counted as independent QA acceptance until OD-12 is decided, and they are not a complete privacy, accessibility, legal or client-release signoff | [#44 5648673115](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/44#pullrequestreview-5648673115), [#45 5650911232](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/45#pullrequestreview-5650911232), [#46 5651387736](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/46#pullrequestreview-5651387736), [HTTPS 6442162352](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/46#issuecomment-6442162352) |
| **Restricted deployment** | Owner-only, Basic-Auth HTTPS preview on Hostinger, updated on 2026-10-27 to PR #46 `f808eac` (engine image `sha256:b788ae5d4397a69a3647e3a02a964e1b721d3d70ae95064cdabd1fd15b2ff2c0`, rollback image `sha256:255cd8cab9e574a942b325c25c450eea7a72671370e87d72eb6cda3fa75909fd` preserved). Synthetic data only; no client invited | [Update receipt 6440936155](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/46#issuecomment-6440936155), [follow-up 6442162352](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/46#issuecomment-6442162352) |
| **Owner acceptance** | Owner visual and editorial acceptance of the preview and PDF: **PENDING**. PRD and roadmap approval: **PENDING**. PR #1 HOLD: **ACTIVE** | [PR #1 HOLD 6323581875](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1#issuecomment-6323581875), [C7 Option A 6393656493](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1#issuecomment-6393656493) |
| **Public release** | None. **Production NO-GO.** No Shopify staging, no public endpoint, no paid offering | - |

### 11.2 Restricted owner preview: what it is and is not
**It is:** a password-protected, owner-only HTTPS deployment of draft PR #46 for synthetic QA and owner review. It calculates D1 and D9 with schema `0.3.0`, renders North Indian D1 and D9 charts, and downloads an eight-page English A4 PDF from memory with no file storage.

**Its limits:** English-first; ten curated Indian birthplaces (New Delhi, Mumbai, Kolkata, Chennai, Bengaluru, Hyderabad, Jaipur, Lucknow, Varanasi, Guwahati) from an internal prototype fixture that is explicitly not the DATA-01 gazetteer; local birth dates 1970-01-01 to 2100-12-31 (1900–1969 refused by canonical Option B); latitude band ±66.0°; no interpretations, Panchanga, Dasha or Hindi.

**It is not:** the public MVP, a Shopify integration, a client or paid release, golden-chart scientific certification, or a privacy/legal signoff. The [PR #1 HOLD](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1#issuecomment-6323581875) is not closed by it.

### 11.3 P0 requirement status
Status labels: **Completed in isolated development**, **Independent QA passed** (used only for QA of Claude-authored code), **Functional QA passed (independence unresolved, OD-12)** (used for #44 to #46), **Restricted preview deployed**, **Partially completed**, **Pending owner acceptance**, **Pending integration**, **Not started**, **Production blocked**. Every P0 requirement is also **Production blocked** until KUN-08.

| Req | Status (2026-10-27) | Evidence | Remaining before public P0 |
|---|---|---|---|
| KUN-F01 Birth form | Partially completed; Restricted preview deployed | #44/#46 preview form, browser QA at 280/375/768/1440 px | Hindi, full place search, privacy messaging review, Shopify page |
| KUN-F02 Offline birthplace | Partially completed (ten-city fixture only) | `prototype/kundali_prototype/places.json` at `f808eac` | DATA-01 licensed gazetteer, ambiguity UI, zone-to-coordinate validation |
| KUN-F03 Historical time | Completed in isolated development; Independent QA passed (C7 scope); Pending integration | Gate 1 `integration/kun03-gate1` `cacd482776366faa9b7d99ceddb16b10ed900b67`, C7 at `185353a` | DATA-01 historical-clock research for 1900–1969; integration into `main` |
| KUN-F04 Methodology | Canonical policy; Completed in isolated development; Independent QA passed (C7 scope); Pending integration | DECISIONS SCI-01a–h; C7 | Integration; optional JPL/INPOP only for an independent-accuracy claim |
| KUN-F05 D1 | Completed in isolated development; Independent QA passed (C7 scope); Restricted preview deployed; Pending integration | C7; Gate 3E; HTTPS QA | Broader golden-chart certification (owner choice, OD-05); integration |
| KUN-F06 D9 | Partially completed: D9 signs, D9 Lagna and D9 whole-sign houses done (schema `0.3.0`); Nakshatra/Pada for all bodies and the Lagna deferred | SCI-02 C2; Gate 3E 5646798499; C7 | Deferred fields under a future schema; integration |
| KUN-F07 Core explanations | Not started (Phase 1 PDF states "not an interpretation") | `report/phase1` at `15b048b` | Rule-ID explanation library, editorial review, RPT gate |
| KUN-F08 Transparent results | Partially completed; Restricted preview deployed (method, provenance and limitations shown) | #44/#46 | QA-014 formal run; correction-flow review |
| KUN-F09 Hindi/English | Not started (English only) | - | Full Hindi UI, report and human review |
| KUN-F10 Branded PDF | Partially completed: Phase 1 English eight-page PDF; Functional QA passed (independence unresolved, OD-12); Restricted preview deployed; Pending owner acceptance | #45, #46, HTTPS QA | Hindi PDF, owner editorial acceptance, QA-017 retention/authorization in final architecture |
| KUN-F11 Self-hosted API | Partially completed; Functional QA passed (independence unresolved, OD-12); Restricted preview deployed (Basic Auth, Origin check, 4 KiB limit, rate limits, no-store) | #44, #46, HTTPS QA | SEC-01, threat model, app-proxy design, PERF-01 measurement, runtime patches into source |
| KUN-F12 Shopify staging | Not started | - | Owner staging authorization; KUN-07 |
| KUN-F13 Accessibility | Partially completed (keyboard chart navigation, text tables, no overflow at four widths) | Gate 3E; #44/#46 browser QA | 200% zoom, screen-reader, contrast and reduced-motion audit (QA-022) |
| KUN-F14 Privacy/security | Partially completed (in-memory, no storage, no-store, access logs off, limited synthetic log scan) | #46 receipts | SEC-01 decision, qualified privacy review, comprehensive log/PII audit |
| KUN-F15 License compliance | Partially completed (AGPL source and GeoNames attribution links in preview) | #44 | LEG-01 qualified review, corresponding-source operation |
| KUN-F16 Verification/release | Partially completed: REL-01 mandatory engine execution passed at `185353a`; Production blocked | C7 | PR #1 HOLD conditions (a), (c), (d); staging; release checklist; owner launch decision |

### 11.4 Still pending
- Broader independent scientific golden-chart certification (optional JPL/INPOP under REL-01; required only for an independent-accuracy claim).
- Closure of the legacy PR #1 HOLD and a clean integration reconciliation of the draft stack (PR #1 lineage and schema `0.1.0` compatibility, Gate 1, #39 to #46) into `main`.
- Expanded birthplace coverage (DATA-01) and historical-clock verification before 1970.
- Complete English/Hindi localization.
- Comprehensive interpretive report content.
- Additional calculation modules (section 12).
- Shopify staging integration.
- Owner editorial acceptance and final public release authorization.

## 12. Proposed comprehensive-report scope (KUN-P1-ADV)
**Status: PROPOSED, not approved.** None of these requirements is a canonical scientific method, an approved product, or a completed feature. Each needs its own owner decision before implementation. The milestone identifier `KUN-P1-ADV` is new and proposed; it replaces the colliding use of "KUN-04" in draft PRs #47 and #48 ([OD-02](#14-open-owner-decisions)). The original KUN-04 still means the secure service milestone (see the naming correction in [DEVELOPMENT-ROADMAP.md section 2.2](DEVELOPMENT-ROADMAP.md#22-milestone-status-as-of-2026-10-27)).

### 12.1 Proposed requirements
| ID | Requirement (proposed) | Minimum acceptance outcome (proposed) | Gates |
|---|---|---|---|
| KUN-A01 Birth Panchanga | Tithi, Vara, Nakshatra, Yoga and Karana at birth, with sunrise/sunset under one validated, owner-approved convention | Owner-approved method record (e.g. Sun/Moon flags, tithi at birth vs sunrise, civil vs sunrise Vara, upper-limb and refraction choice); independently sourced reference cases such as an official national Panchang; fail closed when sunrise/sunset is undefined or the place/clock is unsupported | ENG; RPT for any explanation |
| KUN-A02 Vimshottari Dasha | Mahadasha and Antardasha first, Pratyantardasha after separate validation | Owner-approved year-length and time-arithmetic convention; exact half-open boundaries; independently sourced timelines; no change to chart `0.3.0` outputs | ENG; RPT for any explanation |
| KUN-A03 Additional divisional charts | Beginning with an independently validated D10; then, as proposals only, D7 and D12, and further individually approved vargas. Each chart has its own scientific-method gate | One owner-approved transformation rule per chart; independent rule oracle; versioned contract | ENG |
| KUN-A04 Birthplace coverage | Expanded licensed offline Indian birthplace database, later worldwide | DATA-01 licensing, import and alias QA; ambiguity resolution; zone-to-coordinate consistency; no runtime geocoding API | ENG |
| KUN-A05 Yogas and Doshas | Detection from versioned, source-cited rule definitions | Rule registry with IDs, sources and school differences; positive and negative fixtures; no invented yogas | ENG (detection) and RPT (wording) |
| KUN-A06 Strengths | Planetary and house strengths, Shadbala and Ashtakavarga | Owner-approved method per component; independent reference cases | ENG |
| KUN-A07 Transits and periods | Transit and period analysis over a stated horizon | Approved method and horizon; boundary-time tests; uncertainty disclosure | ENG; RPT |
| KUN-A08 Interpretations | Professionally authored, traceable chart interpretations | Every statement maps to a rule ID, chart facts, method version and authored source; traditional framing; no certainty, no medical/financial/legal advice; AI may not invent content | RPT |
| KUN-A09 Premium reports | Premium and comprehensive downloadable reports | Only ENG-passed modules included; no padded pages; accessible searchable PDF; bilingual when released | ENG for data; RPT for report |
| KUN-A10 Specialized products | Marriage, compatibility, career and annual reports. Concepts under consideration include a Career & Finance report (no financial predictions or advice) and a Professional Astrologer report; neither is approved | Separate scope, consent (two-person data for compatibility), privacy and editorial review per product | ENG; RPT; privacy/legal |
| KUN-A11 Bilingual reports | English and Hindi editions of every released report | Human-reviewed Hindi terminology and typography; numeric identity across languages | RPT |
| KUN-A12 Report design system | Premium report layouts and readable tables built on the approved Sabpuja brand | Design-system fidelity; print and screen QA; accessibility | RPT |
| KUN-A13 Commercial-demand validation | Evidence that a proposed paid report has real demand before it becomes a committed product | Evidence of existing paid competitor offerings, buyer-demand and format validation, pricing tests, pilot acceptance; owner commercial signoff before committing paid products; no assumed prices or sales claims | Owner commercial decision (separate from ENG/RPT) |

### 12.2 Proposed delivery order
Panchanga (KUN-A01) → Vimshottari (KUN-A02) → additional verified divisional charts, starting with D10 (KUN-A03) → strengths (KUN-A06). Birthplace expansion (KUN-A04) and report work (KUN-A08 to KUN-A12) run alongside, gated as set out in the roadmap. Yogas/Doshas and transits follow once their inputs are ENG-passed. Commercial-demand validation (KUN-A13) comes before any paid report product is committed.

### 12.3 Proposed offering structure
*Names, contents, page counts and prices are placeholders for owner decision ([OD-03](#14-open-owner-decisions)). Draft PR #47 is reference only.*

| Offering | Intent | Status |
|---|---|---|
| **Free Kundali** | The original P0 proposition: useful free D1/D9 chart, key placements and downloadable PDF, no account | Original goal, preserved |
| **Entry report** | Free Kundali plus validated Birth Panchanga and Dasha balance in a compact report | Proposed |
| **Premium report** | Entry plus validated Dasha timelines, supported divisional charts and traceable interpretations | Proposed |
| **Professional / comprehensive report** | Premium plus validated strengths, further charts, transits and method appendices | Proposed |
| **Specialized reports** | Marriage, compatibility, career, annual; concepts such as Career & Finance and Professional Astrologer | Proposed |

Only sections whose modules have passed the relevant gates may be included or marketed. A target page count is never a reason to add content.

**Commercial-demand validation (proposed gate, KUN-A13).** Before the owner commits to any paid report product (SKU), a separate product-market check (roadmap WP-E0, market and competitor validation) should be done and signed off by the owner: evidence of existing paid competitor offerings, buyer-demand and format validation, pricing tests, and pilot acceptance. This gate is about whether to sell a product. It does not replace ENG or RPT, which decide whether a module is correct and of report quality. No price, demand level or sales outcome is assumed in this document.

## 13. Module acceptance gates: ENG and RPT
Two independent gates apply to every module in section 12, in addition to the existing gates in section 7 and the [acceptance matrix](ACCEPTANCE-MATRIX.md). They do not weaken REL-01 or any existing gate.

**Gate ENG - Engineering accuracy.** Verifies, on the exact SHA: the implementation; the owner-approved scientific conventions; independently sourced reference cases; Swiss calculations; the mathematics; timezone handling; deterministic outputs; schema compatibility (no silent change to `0.3.0` or metadata `/3`); boundary cases; error handling and refusals; and security. Implemented by Claude, independently reviewed and re-executed by ChatGPT.

**Gate RPT - Report quality.** Verifies: meaningful report coverage; rule-to-interpretation traceability; editorial accuracy; cultural and contextual sensitivity; readability; design-system fidelity; accessibility; localization; and PDF presentation. Requires a named editorial reviewer for interpretive content ([OD-08](#14-open-owner-decisions)).

**Rules.**
- An ENG PASS does not mean an astrological interpretation or prediction has been validated.
- A premium module must pass **both** relevant gates on the exact delivered variant before it is classified as sellable, and the owner must separately approve its sale.
- A module that lacks an authoritative method or reference stays experimental and out of customer-visible reports.
- ENG and RPT QA identifiers are not yet in the acceptance matrix; adding them is a separate, authorized change.

## 14. Open owner decisions
These are raised or restated by this revision. None is decided here. Existing pending register items (UX-01, UX-02, UX-03, DATA-01, SEC-01, LEG-01, PERF-01) remain as recorded in [DECISIONS.md](DECISIONS.md).

| ID | Decision needed |
|---|---|
| OD-01 | Approve, revise or reject this PRD 1.1-proposed and roadmap 1.1-proposed |
| OD-02 | Adopt `KUN-P1-ADV` (or another non-colliding identifier) for the advanced-report milestone, and the KUN-A01 to KUN-A13 requirement IDs |
| OD-03 | Offering structure, tiers, page-count targets and prices (section 12.3), and the commercial-demand validation approach before any paid product is committed (KUN-A13) |
| OD-04 | Priority order of KUN-A modules and Workstreams A to E |
| OD-05 | Whether broader independent golden-chart or JPL/INPOP assurance is required before any public or paid release, beyond REL-01's mandatory gates |
| OD-06 | Panchanga conventions (SCI-PAN-01 style record): flags, sunrise definition, Vara convention, boundary rules, reference source |
| OD-07 | Vimshottari conventions: year length, time arithmetic, depth (MD/AD, then PD) |
| OD-08 | Editorial authority and sources for interpretations (RPT reviewer) and Hindi language reviewer |
| OD-09 | Path to close the PR #1 HOLD and the merge plan for the draft stack into `main` |
| OD-10 | Canonical palette for Kundali UI and reports (PRD section 7 maroon palette vs the storefront tokens pinned in PR #45) |
| OD-11 | Owner visual and editorial acceptance of the restricted preview and Phase 1 PDF |
| OD-12 | Disposition of draft PRs #44, #45 and #46 given the open authorship question in section 0 (for example, confirm authorship, Claude independent re-verification, or Claude re-implementation) |
| OD-13 | Whether the preview's server-side runtime patches must be committed to source before any further preview change |
| OD-14 | Calculation metadata `/4` for machine-readable D9 house method (deferred by SCI-02 C2) |

## 15. Known documentation inconsistencies (not changed by this revision)
This revision is limited to `docs/PRD.md` and `docs/DEVELOPMENT-ROADMAP.md`. These related inconsistencies are recorded for a separately authorized follow-up:
- `machine/project-plan.json` still lists version `1.0-rc1`, status PENDING for every milestone, and `updated: 2026-10-21`.
- `docs/ACCEPTANCE-MATRIX.md` (1.0-rc1) has no ENG/RPT or KUN-A## test IDs and still states every QA ID is NOT RUN.
- `docs/README.md` "Current stage" and `CLAUDE.md` still describe CLAUDE-001 as the only assignment.
- The SCI-02 C2 entry in `docs/DECISIONS.md` ends with a "Register merge" paragraph saying the register on `main` is unchanged, although PR #43 has since merged it. It is an append-only historical record and is not edited here.
- Draft PRs #47 and #48 use "KUN-04" for advanced-report work, which collides with the canonical KUN-04 secure service milestone.

## 16. Revision history
| Version | Date | Author | Change | Approval |
|---|---|---|---|---|
| 1.0-rc1 | 2026-10-21 | ChatGPT PM (planning PR #3) | Initial PRD | PENDING |
| 1.0-rc1 + REL-01 | 2026-10-24 | Claude (PR #20) | REL-01 evidence-policy wording | REL-01 owner approved / canonical, adoption merge `5b71408` |
| 1.1-proposed | 2026-10-28 | Claude (CLAUDE-DOC-014, issue #49) | Roles restated; status snapshot as of 2026-10-27; expanded vision; proposed KUN-P1-ADV scope (KUN-A01 to KUN-A13); ENG and RPT gates; open decisions. Revised 2026-10-28 for ChatGPT review 5678627440 | PENDING owner review |
