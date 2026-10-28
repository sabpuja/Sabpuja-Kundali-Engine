# Sabpuja Kundali - Detailed Development Roadmap and Claude Delivery Plan

**Document ID:** SP-KUN-DEV-001 | **Version:** 1.1-proposed (rebaseline draft; supersedes 1.0-rc1 only after an owner-authorized merge) | **Date:** 2026-10-28 | **Evidence cut-off:** 2026-10-27\
**Status:** DRAFT, awaiting owner review. Proposed by Claude under [CLAUDE-DOC-014 / issue #49](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/49) from `main` `2f67c648f7c7e02dade58bd72993722d06cb1cd3`. **Authoritative requirements:** [PRD.md](PRD.md); **QA matrix:** [ACCEPTANCE-MATRIX.md](ACCEPTANCE-MATRIX.md); **decisions:** [DECISIONS.md](DECISIONS.md). **Website:** [sabpuja.com](https://sabpuja.com)

This roadmap defines *work and acceptance*, not permission for Claude to execute, merge or deploy. All Kundali project planning stays in this repository. No GitHub Actions. No modification of `sabpuja/core`. Other repo changes (e.g. Shopify theme) require separate, explicitly approved implementation PRs in their owning repo, referenced back here.

**Production: NO-GO.** All implementation PRs are draft and unmerged. The restricted owner-only preview is not a public release.

## 1. Operating protocol
- **Owner:** choose priorities, settle open product/astronomy/privacy decisions, approve each merge and all release targets. Final decision-maker for scope, scientific conventions, budgets, merges and deployments.
- **ChatGPT PM/QA:** write scoped tickets with requirement + test IDs; review every material code/function/API change and actual test output; independently check numeric reference evidence; return PASS / CHANGES REQUESTED / BLOCKED; track regressions. ChatGPT does **not** act as lead implementer.
- **Claude (sole lead developer):** read project docs and baseline SHA, implement only assigned slice, run local/approved-host tests, submit a draft PR plus the [QA evidence template in foundation PR #1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/blob/feat/initial-kundali-foundation-20261021/docs/qa-review-template.md) when available on the foundation branch; provide real output and fix QA defects. No direct `main` writes, self-approval or self-merges.
- **Sources of truth:** existing draft [foundation PR #1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1), first [audit issue #2](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/2), project [governance](https://github.com/sabpuja/Sabpuja-Kundali-Engine/blob/feat/initial-kundali-foundation-20261021/docs/project-governance.md). Those foundation docs are proposed, **not merged**.
- **Strict gates:** approved spec -> scoped task -> Claude draft PR/tests -> independent QA -> owner merge -> explicit staging deploy approval -> independent staging QA -> separate owner launch approval. Equivalently: Owner authorization → Claude implementation → Claude test evidence → ChatGPT independent QA → Owner merge authorization → Controlled deployment → Release QA.
- **Independence rule (2026-10-27).** Draft PR [#48](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/48) holds ChatGPT-authored experimental arithmetic ([6442494969](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/48#issuecomment-6442494969)). It is non-canonical: never merge, cherry-pick or import it, and never treat it as independently developed scientific implementation. New calculation modules are implemented by Claude from owner-approved methodology and independently sourced reference cases, then reviewed by ChatGPT. Draft PRs #44, #45 and #46 share #48's Git author identity; their implementation independence is an open owner decision ([PRD OD-12](PRD.md#14-open-owner-decisions)).

## 2. Milestones, sequencing and objective exit gates
### 2.1 Original milestone definitions (1.0-rc1, unchanged)
*The identifiers, work packages and exit evidence below are the canonical milestone records from 2026-10-21. The last column is kept as historical; current status is in section 2.2.*

| Milestone | Work packages | Depends on | Evidence for PM/QA | Status at 1.0-rc1 (2026-10-21, historical) |
|---|---|---|---|---|
| KUN-DOC | PRD, detailed roadmap, acceptance matrix, decision register approved by owner | none | Owner's explicit approval and immutable Git SHA | DRAFT |
| KUN-00 | Existing foundation audit, dependency scan, baseline tests, correct blocking numerical/contract bugs | KUN-DOC for new fixes; audit itself can precede | Real local test output; PR #1 review; zero critical defects | Existing foundation PR #1 DRAFT; audit issue #2 OPEN |
| KUN-01 | Version-pinned Swiss data, reproducible golden-chart fixture suite, astronomy and D1 method fixes | KUN-00 + SCI-01 decisions | Dataset SHA, methods, Swiss CLI conformance and independent rule/formula checks within predeclared tolerances (REL-01; independent JPL/INPOP differences optional) | Not started |
| KUN-02 | Offline place index and historical local-time resolution | KUN-01 and DATA-01 | DST fold/gap, duplicate cities, historical offset, invalid-place validation tests | Not started |
| KUN-03 | Deterministic D1/D9 output schema, North Indian chart renderer domain model, rule explanations | KUN-01 + KUN-02 | Independent D9 fixtures, accessible chart data and schema backward-compat tests | Not started |
| KUN-04 | Secure, rate-limited self-hosted calculation and PDF service contract | KUN-01-03 + SEC-01 | Threat model, endpoint tests, load/profile evidence, no birth data in logs | Not started |
| KUN-05 | Branded SP-KUN Component Lab interface, language switching, accessibility | Stable KUN-03/04 interface + UX-01 | Desktop/mobile keyboard, Hindi content, zero chart/crop defects | Not started |
| KUN-06 | Branded EN/HI PDF renderer, explicit user download, privacy-safe outputs | KUN-03/04 + design | Tested PDF charts, font rendering, no unexpected retention | Not started |
| KUN-07 | Shopify **unpublished staging** integration, end-to-end and regression QA | KUN-04-06 + owner staging approval | Real staging interactions, secure app-proxy verification, site/performance QA | Not started |
| KUN-08 | License/privacy release review, runbook, source offer, rollback and explicit public launch authorization | All P0 gates + owner launch decision | Signed release checklist, exact deployed SHAs, live smoke QA after release | Not started |
| KUN-P1 | Save profiles, Dashas, additional Vargas, South Indian chart, matching | New owner-approved feature PRD(s) | Separate specs and numerical/privacy/source validation | Backlog only |

**Order of work may be optimized without bypassing gates.** Dates and sprint length are intentionally not promised until Claude supplies actual capacity, reference-data availability and baseline findings.

### 2.2 Milestone status as of 2026-10-27
Status labels: **Completed in isolated development** · **Independent QA passed** (only for QA of Claude-authored code) · **Functional QA passed (independence unresolved, OD-12)** (reviewer-executed QA of #44 to #46) · **Restricted preview deployed** · **Partially completed** · **Pending owner acceptance** · **Pending integration** · **Not started** · **Production blocked**. A milestone is never marked complete because one related draft PR passed tests. Every milestone is also **Production blocked** until KUN-08.

| Milestone | Status | Evidence (exact SHAs) | Still open |
|---|---|---|---|
| KUN-DOC | Partially completed; Pending owner acceptance | PRD/roadmap/matrix merged as owner-review drafts (PRs #3, #4); decision register canonical entries via #13, #20 (`5b71408`), #37, #38, #43 (`2f67c64`); this 1.1-proposed rebaseline | Owner approval of PRD, roadmap and matrix; matrix ENG/RPT IDs; `machine/project-plan.json` sync |
| KUN-00 | Partially completed; Pending integration | CLAUDE-001 audit ([issue #2](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/2)); [HOLD 6323581875](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1#issuecomment-6323581875); CLAUDE-002a/b/c merged into the PR #1 branch (#6, #8, #10); PR #1 head `d8193c692d52aa12595f81c227638a061605a3d9` | PR #1 HOLD conditions (a) P0/high remediation, (c) README/AGENTS/registry alignment, (d) exact-head QA; reconciliation with Gate 1 and schema `0.1.0` legacy lineage |
| KUN-01 | Completed in isolated development; Independent QA passed (REL-01 mandatory scope at `185353a`); Pending integration | Pinned Swiss data and manifest (002a, Gate 3C #40); Swiss CLI conformance (#18, D3 v2); [C7 PASS 5647737922](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/42#pullrequestreview-5647737922): 474/0/0 engine, Swiss D3 v2 24/24 | Integration into `main`; broader golden-chart / JPL-INPOP certification only if the owner requires it (PRD OD-05) |
| KUN-02 | Partially completed | Historical local-time resolution done on Gate 1 `cacd482776366faa9b7d99ceddb16b10ed900b67` (P1 tzdata, P4 window, P5 refusals, P8 Option B, D3 v2) and covered by C7; birthplace data is a ten-city prototype fixture only | DATA-01 licensed offline place index, duplicate-city UI, zone-to-coordinate validation, pre-1970 historical-clock research |
| KUN-03 | Partially completed; Independent QA passed (D1/D9 scope); Pending integration | Schema `0.3.0` D1/D9 with D9 houses and North Indian D1/D9 renderer at [#42](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/42) `185353a`; [Gate 3E QA 5646798499](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/42#pullrequestreview-5646798499); C7 prototype 106/0/0 | Rule explanations (not started); all-body and Lagna Nakshatra/Pada (deferred); integration |
| KUN-04 (secure service) | Partially completed; Functional QA passed (independence unresolved, OD-12); Restricted preview deployed | Owner-only gateway [#44](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/44) `b436134` and PDF API [#46](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/46) `f808eac`; reviewer-executed [isolated QA 5648673115](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/44#pullrequestreview-5648673115); [HTTPS update 6440936155](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/46#issuecomment-6440936155) and [follow-up 6442162352](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/46#issuecomment-6442162352) | SEC-01, threat model, app-proxy design, PERF-01 measurement, runtime patches into source, authorship disposition (OD-12). Not a public service |
| KUN-05 | Partially completed; Restricted preview deployed | Prototype UI (#39, #41, #42) and preview UI; Chromium QA at 280/375/768/1440 px over real HTTPS | Component Lab, Hindi, language switching, full accessibility audit (QA-022), owner visual acceptance |
| KUN-06 | Partially completed; Functional QA passed (independence unresolved, OD-12); Restricted preview deployed; Pending owner acceptance | Phase 1 English eight-page PDF [#45](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/45) `15b048b` ([QA 5650911232](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/45#pullrequestreview-5650911232)); download [#46](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/46) `f808eac` ([QA 5651387736](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/46#pullrequestreview-5651387736)) | Hindi PDF, owner editorial acceptance, comprehensive content (KUN-P1-ADV) |
| KUN-07 | Not started | - | Owner staging authorization; Shopify theme work in its own repo |
| KUN-08 | Not started; Production blocked | Preview rollback image only | LEG-01, SEC-01, privacy review, release runbook, owner launch decision |
| KUN-P1 | Backlog only | - | New owner-approved specs |
| **KUN-P1-ADV** *(proposed new identifier)* | Proposed; not approved | Reference only: draft [#47](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/47) `77c4223a80e8dad9b7ec7676cc766528dee1c11f` (PM RFCs); [#48](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/48) `7dcd82546e565ec4cd0f4603f566a4805f65fe57` (non-canonical) | Owner adoption of the identifier and KUN-A01 to KUN-A13 (PRD section 12) |

**Naming correction.** KUN-04 is, and remains, the secure self-hosted calculation and PDF service milestone. Draft PRs #47 and #48 reused "KUN-04" for the Panchanga/Vimshottari stage. That work is renamed here to the proposed, non-colliding **KUN-P1-ADV**. Historical milestone records, PR titles and comments are not rewritten. The proposed requirements under KUN-P1-ADV are in [PRD section 12](PRD.md#12-proposed-comprehensive-report-scope-kun-p1-adv), and adoption of the identifier is [PRD OD-02](PRD.md#14-open-owner-decisions).

## 3. Sprint-sized work package backlog
### 3.1 Original task definitions (1.0-rc1, unchanged)
| Task | Milestone | Inputs and implementation scope | Required tests/evidence | Stop/QA gate |
|---|---|---|---|---|
| CLAUDE-001 | KUN-00 | **Existing issue #2**: audit draft PR #1, no rewrite | Exact SHA, package versions, raw local tests, prioritized numeric concerns | ChatGPT triages; audit is not accuracy signoff |
| CLAUDE-002 | KUN-00 | Fix P0 contract/offset/ephemeris bugs identified by audit, one bug family per PR | Unit + negative tests, before/after error reproduction | No unapproved methodology change |
| CLAUDE-003 | KUN-01 | Pin Swiss source, binding and ephemeris data; exact method manifest; fail-closed fallback | SHA-256 verification and deterministic startup tests | Stop on unresolved licenses or mismatched files |
| CLAUDE-004 | KUN-01 | Golden chart fixtures: reference methodology and tolerance per REL-01, core planet/Lagna D1 correctness | Accuracy report with comparisons, boundary cases and no silent interpolation | PM QA review; independent astronomy review only for the optional REL-01 assurance |
| CLAUDE-005 | KUN-02 | Offline place database/import, ambiguity-aware place lookup, IANA timezone dataset | Same-name cities, no outbound network, licenses/hashes | No guessed place/offset |
| CLAUDE-006 | KUN-02 | Birth-time conversion and DST/historic time rules | Missing/fold/gap and leap-year tests; explicit error contract | PM location/time QA |
| CLAUDE-007 | KUN-03 | Complete canonical structured D1/D9 domain output, renderer data model, accessible tables | Cross-chart mathematical consistency, D9 ascendant, JSON schema fixture | No browser/UI until model passes |
| CLAUDE-008 | KUN-03 | Rule-based explanations editorial package and localization keys | Traceable rule IDs; reviewed EN/HI strings | No deterministic prediction/guarantee |
| CLAUDE-009 | KUN-04 | Secure calculation endpoint, input schema, authentication/app proxy verification, rate limits and response errors | Local integration tests, abusive input/rate tests, logs inspection | No public listener before security approval |
| CLAUDE-010 | KUN-05 | SP-KUN fluid UI in canonical component lab; birth form, chart tabs, textual legend, languages | Manual visual/device/zoom, screen-reader/keyboard/Hindi QA | Staging-only on separately approved theme |
| CLAUDE-011 | KUN-06 | Branded PDF with both charts and method metadata | EN/HI glyph tests, repeatability, temp file TTL and access tests | No public persistent URL |
| CLAUDE-012 | KUN-07 | Staging-only Shopify integration, navigation, request flow and E2E QA | Verified theme role, functional/video/screenshot QA, fail/retry behavior | No live theme or storewide data changes |
| CLAUDE-013 | KUN-08 | Release packaging, license/source-offer, privacy runbook, version pin, operational readiness | Full test matrix, rollback rehearsal, exact release receipt | Human owner authorizes launch separately |

Each task should be one bounded issue with acceptance IDs (from [ACCEPTANCE-MATRIX.md](ACCEPTANCE-MATRIX.md)), size estimate and explicit excluded scope. No new issue is considered assigned merely because it appears in this plan. *(Historical, 2026-10-21: "only issue #2 is already created". That is no longer true; current task status is in section 3.2.)* Grouping of tasks/PRs may be adjusted after audit, but not their safety gates.

### 3.2 Task status as of 2026-10-27
| Task | Status | Delivered through (draft unless noted) | Remaining |
|---|---|---|---|
| CLAUDE-001 | Completed (audit) | Issue #2; findings drove the PR #1 HOLD | - |
| CLAUDE-002 | Completed in isolated development; Pending integration | #6 (002a), #8 (002b), #10 (002c), merged into the PR #1 branch only | PR #1 HOLD and integration |
| CLAUDE-003 | Completed in isolated development; Independent QA passed (C7 scope); Pending integration | 002a manifest; Gate 3C #40 version pins and start-up preflight; KUN-01 plan drafts #11, #17 | `verify_all()` service start-up gate; integration |
| CLAUDE-004 | Partially completed; Independent QA passed (REL-01 mandatory scope) | Swiss CLI conformance #18 and D3 v2 run in C7; golden harness skeleton #14 (dummy fixtures) | Broader independent golden charts only if required (PRD OD-05) |
| CLAUDE-005 | Partially completed (ten-city prototype fixture) | Prototype places fixture in #39 lineage, deployed via #44/#46 | DATA-01 gazetteer, licensing, ambiguity UX |
| CLAUDE-006 | Completed in isolated development; Independent QA passed (C7 scope); Pending integration | #23, #26 to #29, #35 and Gate 1 `cacd482` | DATA-01 pre-1970 research; integration |
| CLAUDE-007 | Partially completed; Independent QA passed (D1/D9 scope) | Schema `0.2.0` (Gate 1) then `0.3.0` (#42) | All-body and Lagna Nakshatra/Pada; metadata `/4` if approved |
| CLAUDE-008 | Not started | - | Rule-ID explanation library and EN/HI strings; RPT gate |
| CLAUDE-009 | Partially completed; Functional QA passed (independence unresolved, OD-12); Restricted preview deployed | Owner-preview gateway and API (#44, #46); authorship open (OD-12) | App-proxy design, SEC-01, threat model, PERF-01 |
| CLAUDE-010 | Partially completed; Restricted preview deployed | Prototype UI (#39, #41, #42) and preview UI | Component Lab, Hindi, accessibility audit |
| CLAUDE-011 | Partially completed; Functional QA passed (independence unresolved, OD-12); Restricted preview deployed; Pending owner acceptance | Phase 1 English PDF (#45, #46); authorship open (OD-12) | Hindi, editorial acceptance |
| CLAUDE-012 | Not started | - | Owner staging authorization |
| CLAUDE-013 | Not started | Preview-only rollback runbook in #46 | Release packaging and launch gates |

## 4. Parallelism and dependency logic
1. **While CLAUDE-001 is auditing:** owner/PM complete PRD + method decisions; UX can be reviewed as non-deployed mockups only. Do not accept or merge unverified engine code.
2. **After KUN-01 accuracy gate:** birthplace/time validation and chart-renderer domain work can proceed in separate branches with pinned schema, while preventing conflicting data methods.
3. **After stable schema:** API/PDF/UI can run in coordinated branches, with versioned contracts and narrow reviews.
4. **Before staging:** signed privacy and API threat model; project owner permits theme access and isolated VPS test deployment.
5. **Before public production:** independent E2E, legal/compliance, rollback and owner signoff. No unattended release.
6. **P1 features:** only after separate prioritization and user-data consent requirements; never quietly add to MVP.
7. **Advanced modules (KUN-P1-ADV, proposed):** a module's code starts only after the owner approves its method record. Method research, reference-case collection and report design can run before that, as documentation and fixtures, without touching the engine or schema.

## 5. Definition of ready for a Claude task
- PRD requirement IDs + acceptance IDs, explicit owner scope approval.
- Known baseline branch and commit, interfaces and calculation conventions.
- Dependencies, external dataset rights, secret/access prerequisites.
- Negative cases, test/fixture provenance and measurable success.
- No critical unresolved upstream decision that would invalidate implementation.
- For a new calculation module: an owner-approved method record in [DECISIONS.md](DECISIONS.md) and independently sourced reference cases not derived from any implementation (including PR #48).

## 6. Definition of done for a coding task
- Code and docs in specialist owning repo, PR linked to work package; no unrelated modifications.
- Static review, automated unit/contract and relevant integration tests run with raw results on exact SHA, plus the REL-01 reference cases for astronomical work (Swiss CLI conformance and independent rule/formula checks; independently sourced astronomy optional).
- User-facing EN/HI and accessibility checks when applicable; no exposed birth information.
- ChatGPT QA PASS on the exact updated SHA, defects remediated, owner merge approval and verified merge read-back.
- Any deployment is a separate approved phase; passing tests alone never means released.
- For a KUN-P1-ADV module: Gate ENG PASS; and, if it produces customer-facing interpretation or report content, Gate RPT PASS (section 7).

## 7. QA gates and non-negotiable blockers
**Gate A - Astronomy:** Planet/Lagna and D1/D9 differences to the REL-01 references (Swiss CLI conformance, independent rule/formula checks; independent charts when the optional assurance is run) reported with methods and tolerances defined before evaluation. Stop on unverified Swiss .se1 data, silent Moshier fallback, time conversion errors, or wrong house/navamsa math.

**Gate B - Security:** Validate app-proxy authenticity, access control, rate limiting, input max, malformed dates, server-side errors, request replay, CORS/CSRF as applicable, and no birth data in logs/query strings. No unauthenticated open service.

**Gate C - Privacy/legal:** Document ephemeral report lifecycle, cookie/analytics consent, network source-offer operation, and AGPL-compatible boundary. A qualified license/privacy review is a public-release prerequisite, not a claim that review has happened.

**Gate D - Product/UX:** Fluid viewport, 200% zoom, Devanagari font embedding, keyboard navigation, accessible chart table, bilingual input/error messages and no hardcoded Shopify products.

**Gate E - Operations:** Test source/data pin, deterministic container config, no unapproved GitHub Actions, isolated Hostinger infrastructure, staging theme verification, clear rollback, exact owner approval.

**Gate ENG - Engineering accuracy (per module, proposed):** exact-SHA implementation; owner-approved conventions; independent references; Swiss calculations; mathematics; timezone handling; deterministic outputs; schema compatibility; boundary cases; error handling; security. Builds on Gates A, B and E; does not replace them.

**Gate RPT - Report quality (per module, proposed):** report coverage; rule-to-interpretation traceability; editorial accuracy; cultural and contextual sensitivity; readability; design-system fidelity; accessibility; localization; PDF presentation. Builds on Gates C and D.

An ENG PASS does not validate an astrological interpretation or prediction. A premium module needs **both** ENG and RPT PASS on the exact delivered variant, plus separate owner approval, before it is sellable. ENG/RPT QA IDs still have to be added to the acceptance matrix by a separately authorized change.

## 8. Milestone review format
Use a record attached to the PR/issue:
```text
Milestone / Work package:
PR + exact reviewed SHA:
PRD requirements / acceptance IDs:
Test environment and commands:
Raw test report / independent reference provenance:
Security, locale, privacy, licensing evidence:
Module gates (KUN-P1-ADV only): ENG PASS | RPT PASS | not applicable
PM / QA verdict: PASS | CHANGES REQUESTED | BLOCKED
Defects / unresolved questions:
Owner merge approval: pending | approved with reference
Stage/live deployment: not authorized | separately approved with reference
```

## 9. Risk register and contingency
| Risk | Severity | Mitigation / owner |
|---|---|---|
| Incorrect sidereal Lagna / Swiss sidereal house options | Critical | Owner selects methodology; Claude supplies the REL-01 reference checks (independent golden charts optional); ChatGPT verifies |
| Historical India offsets or DST folds | High | Offline timezone revision pin, comparison tests, explicit ambiguity UI |
| Swiss library and .se1 rights / AGPL combined work | Critical pre-launch | External license review and working source offer; owner signoff |
| Data leakage through PDF, URLs, logs, analytics or caching | Critical | Privacy threats, negative tests, ephemeral default; ChatGPT QA |
| Dubious traditional interpretation presented as fact | High | Rule provenance, uncertainty language, editorial review |
| Unstable Shopify theme or brand drift | High | Dynamic content, current staging verified, Component Lab and design-system assets |
| Developer self-merge or changing scope | High | PR-based approval matrix, no direct main, owner signoff |
| Build timeline uncertainty | Medium | No fixed dates until audit and estimates; small, measurable packages |
| Builder/reviewer role overlap (PR #48; open question on #44 to #46) | High | Claude implements, ChatGPT reviews; non-canonical code never imported; owner disposition OD-12 |
| Preview runtime drift (server-side gateway patches outside Git; trusted upstream IP `172.28.0.3` can change on edge-container recreation) | High | **Control:** after any recreation of the Caddy container, revalidate the trusted-IP line and re-run per-client throttling checks before further preview use. Longer term: commit settings to source and use deterministic addressing (WP-A3) |
| Long-lived draft stack diverges from `main` and PR #1 | High | Integration reconciliation plan before any further stacking (Workstream A) |
| Premium scope outruns validated calculations | High | ENG before RPT; only ENG-passed data in reports; no page-count targets driving content |
| Unapproved Panchanga/Dasha conventions coded as canonical | Critical | Owner method records first; independent references; no reuse of PR #48 |

## 10. Forward roadmap (proposed, 2026-10-28)
*Workstreams and work packages below are proposals for PM scoping and owner authorization. None is assigned by this document. Work-package IDs (WP-…) are planning labels, not CLAUDE task numbers; the PM assigns task numbers when scoping tickets.*

### Workstream A - MVP readiness
Close remaining owner-review items, strengthen operational reliability, maintain rollback and access restrictions, and preserve exact-SHA verification.

| WP | Work (owner role / Claude role) | Depends on | Gate |
|---|---|---|---|
| WP-A1 | Owner visual and editorial review of the restricted preview and Phase 1 PDF (owner) | - | Owner acceptance (OD-11) |
| WP-A2 | Disposition of #44 to #46 authorship (owner); then Claude independent re-verification or re-implementation as decided | OD-12 | ChatGPT exact-SHA QA |
| WP-A3 | Draft (research and proposal) first; then, only after OD-13 is decided, commit the preview gateway runtime patches to source, with deterministic upstream addressing and a recheck procedure for per-client throttling (Claude, no deployment) | Draft: none. Source change: OD-13 and owner authorization | Gates B and E |
| WP-A4 | Integration reconciliation plan for PR #1 (HOLD, schema `0.1.0` lineage), Gate 1 and the #39 to #46 stack: conflict map, merge order, regression plan; no merge (Claude) | OD-09 | ChatGPT review; owner merge plan |
| WP-A5 | Documentation sync: ENG/RPT and KUN-A## IDs in the acceptance matrix; `machine/project-plan.json`; `docs/README.md`; `CLAUDE.md`. An audit of what is stale can be drafted now; the edits wait for the decisions (Claude) | Audit: none. Edits: OD-01, OD-02 and owner authorization | ChatGPT review |

### Workstream B - Core advanced calculations
Panchanga → Vimshottari Dasha → additional verified divisional charts → advanced planetary and house strength calculations.

| WP | Work | Depends on | Gate |
|---|---|---|---|
| WP-B1 | Panchanga method decision package: options, Swiss flags, sunrise/sunset definition, Vara and boundary conventions, independently sourced reference cases (e.g. official national Panchang); documentation and fixtures only (Claude) | OD-04 | ChatGPT review; owner method decision OD-06 |
| WP-B2 | Panchanga implementation (KUN-A01) under its own versioned contract (Claude) | WP-B1 decision | ENG |
| WP-B3 | Vimshottari method decision package and reference timelines (Claude) | OD-04 | Owner method decision OD-07 |
| WP-B4 | Vimshottari MD/AD implementation; PD after separate validation (KUN-A02) | WP-B3 decision; uses canonical Moon longitude | ENG |
| WP-B5 | D10 method record and implementation; then proposed D7 and D12, and further vargas, one at a time, each with its own method gate (KUN-A03) | Owner method decision per chart | ENG |
| WP-B6 | Strength calculations: Shadbala and Ashtakavarga (KUN-A06) | Method decisions | ENG |
| WP-B7 | Yoga/Dosha rule registry and detection; transit and period analysis (KUN-A05, KUN-A07) | ENG-passed inputs; method decisions | ENG; RPT |

### Workstream C - Birthplace and time accuracy
Expand licensed offline place data, improve ambiguity resolution and independently verify timezone and historical-clock policies.

| WP | Work | Depends on | Gate |
|---|---|---|---|
| WP-C1 | DATA-01 options package: candidate datasets, licence and rights evidence, import approach, India-first coverage, alias and duplicate handling. Evidence for the owner's DATA-01 decision, no implementation | None (precedes the decision) | ChatGPT review; then owner DATA-01 decision |
| WP-C2 | Offline place index and ambiguity-aware lookup (KUN-F02, KUN-A04) | WP-C1 and the owner's DATA-01 selection | ENG; Gate D for UI |
| WP-C3 | Zone-to-coordinate consistency validation | WP-C2 | ENG |
| WP-C4 | Historical-clock research for India before 1970; any exception only through an owner-approved DATA-01 record | DATA-01 | ENG; owner decision |

### Workstream D - Comprehensive Kundali reports
Create progressively richer report structures, interpretations, readable tables, professional design, accessible PDF output, and bilingual support.

| WP | Work | Depends on | Gate |
|---|---|---|---|
| WP-D1 | Report information architecture and design system for Entry/Premium/Professional, starting from the Phase 1 PDF (KUN-A09, KUN-A12) | OD-03, OD-10 | RPT |
| WP-D2 | Interpretation provenance register: rule IDs, chart facts, sources, school differences (KUN-F07, KUN-A08) | OD-08 | RPT |
| WP-D3 | Hindi localization of UI and reports with human review (KUN-F09, KUN-A11) | OD-08 | RPT; Gate D |
| WP-D4 | Accessible, searchable PDF output for richer reports | WP-D1; ENG-passed modules only | RPT; Gate C |

### Workstream E - Commercial product integration
Later Shopify staging integration, digital report products, customer experience, privacy/legal approval and production release.

| WP | Work | Depends on | Gate |
|---|---|---|---|
| WP-E0 | Commercial-demand validation (proposed, KUN-A13): competitor offer evidence, buyer-demand validation, format and price tests, pilot acceptance, with no assumed prices or sales claims. Product-market work, separate from ENG/RPT (owner, with PM; Claude only for evidence gathering if asked) | OD-03 | Owner commercial signoff |
| WP-E1 | Shopify unpublished-staging integration (CLAUDE-012, KUN-07) | KUN-04 to KUN-06; owner staging approval | QA-020, QA-021, QA-028 |
| WP-E2 | Digital report product definitions and delivery (KUN-A09, KUN-A10) | OD-03; WP-E0 signoff; ENG and RPT per module | Owner sale approval |
| WP-E3 | Privacy, consent and legal approval (SEC-01, LEG-01; two-person consent for compatibility) | Qualified review | Gate C |
| WP-E4 | Release packaging and production launch (CLAUDE-013, KUN-08) | All P0 gates | Owner launch decision |

### 10.1 Dependencies and safe parallelism
- **Can proceed in parallel now, as research, audits or proposed drafts only:** WP-A1 (owner), WP-A3 (draft only), WP-A4, WP-A5 (audit only), WP-B1, WP-B3, WP-C1, WP-D1, WP-D2, WP-E0. Each still needs the PM's scoped ticket and the owner's authorization before Claude starts. Any actual source, runtime, configuration or documentation-of-record change (for example WP-A3's source change after OD-13, or WP-A5's edits after OD-01/OD-02) needs separate owner authorization. None changes the engine, schema `0.3.0`, metadata `/3`, the preview, Shopify or `main`.
- **Sequential by gate:** WP-E2 after WP-E0 signoff and the module gates; WP-B2 after the owner's Panchanga decision; WP-B4 after the Vimshottari decision; WP-B5 to WP-B7 after their method decisions and their ENG-passed inputs; WP-C2 after DATA-01; WP-D4 after ENG-passed modules exist; Workstream E after the P0 gates.
- **Never bypassed:** owner method approval before calculation code is merged; ENG before any data reaches a report; RPT before any interpretive content is sold; owner authorization for every merge and deployment; PR #1 HOLD until the owner closes it.

### 10.2 Recommended next Claude assignments (for PM scoping and owner authorization)
1. **WP-B1 Panchanga method decision package** (documentation and independent reference fixtures only). It is the first step of the approved direction and unblocks Panchanga implementation without coding unapproved conventions.
2. **WP-A4 integration reconciliation plan** for PR #1, Gate 1 and the draft stack, so that verified engine work can eventually reach `main` without silently redefining the preview as production.
3. **WP-A5 documentation sync**, once this rebaseline is accepted.

## 11. Requirement-to-milestone traceability
| Requirement | Milestone | Tasks / WPs | QA IDs | Gate(s) | Status (2026-10-27) |
|---|---|---|---|---|---|
| KUN-F01 Birth form | KUN-05 | CLAUDE-010 | QA-001, QA-002 | D | Partially completed; Restricted preview deployed |
| KUN-F02 Offline birthplace | KUN-02 | CLAUDE-005, WP-C1, WP-C2 | QA-003, QA-004 | A, D | Partially completed (ten-city fixture) |
| KUN-F03 Historical time | KUN-02 | CLAUDE-006, WP-C4 | QA-005, QA-006 | A | Completed in isolated development; Independent QA passed; Pending integration |
| KUN-F04 Methodology | KUN-01 | CLAUDE-003, CLAUDE-004 | QA-007, QA-008 | A | Canonical; Independent QA passed; Pending integration |
| KUN-F05 D1 | KUN-01, KUN-03 | CLAUDE-004, CLAUDE-007 | QA-009, QA-010, QA-011 | A | Independent QA passed; Restricted preview deployed; Pending integration |
| KUN-F06 D9 | KUN-03 | CLAUDE-007 | QA-012 | A | Partially completed (D9 houses done; all-body Nakshatra/Pada deferred) |
| KUN-F07 Core explanations | KUN-03 | CLAUDE-008, WP-D2 | QA-013, QA-029 | D, RPT | Not started |
| KUN-F08 Transparent results | KUN-05 | CLAUDE-010 | QA-014 | D | Partially completed |
| KUN-F09 Hindi/English | KUN-05, KUN-06 | CLAUDE-008, CLAUDE-010, CLAUDE-011, WP-D3 | QA-015, QA-016 | D, RPT | Not started |
| KUN-F10 Branded PDF | KUN-06 | CLAUDE-011 | QA-017, QA-030 | C, D | Partially completed; Functional QA passed (OD-12 open); Restricted preview deployed; Pending owner acceptance |
| KUN-F11 Self-hosted API | KUN-04 | CLAUDE-009, WP-A3 | QA-018, QA-019 | B, E | Partially completed; Functional QA passed (OD-12 open); Restricted preview deployed |
| KUN-F12 Shopify staging | KUN-07 | CLAUDE-012, WP-E1 | QA-020, QA-021 | B, D, E | Not started |
| KUN-F13 Accessibility | KUN-05 | CLAUDE-010 | QA-022, QA-023 | D | Partially completed |
| KUN-F14 Privacy/security | KUN-04, KUN-08 | CLAUDE-009, CLAUDE-013, WP-E3 | QA-024, QA-025 | B, C | Partially completed |
| KUN-F15 License compliance | KUN-08 | CLAUDE-013, WP-E3 | QA-026 | C | Partially completed |
| KUN-F16 Verification/release | KUN-00 to KUN-08 | CLAUDE-001 to CLAUDE-013, WP-A4, WP-E4 | QA-027, QA-028 | All | Partially completed; Production blocked |
| KUN-A01 Birth Panchanga *(proposed)* | KUN-P1-ADV | WP-B1, WP-B2 | To be added | ENG (+RPT for text) | Proposed |
| KUN-A02 Vimshottari *(proposed)* | KUN-P1-ADV | WP-B3, WP-B4 | To be added | ENG (+RPT) | Proposed |
| KUN-A03 Divisional charts *(proposed)* | KUN-P1-ADV | WP-B5 | To be added | ENG | Proposed |
| KUN-A04 Birthplace coverage *(proposed)* | KUN-02, KUN-P1-ADV | WP-C1 to WP-C3 | QA-003, QA-004 + new | ENG | Proposed |
| KUN-A05 Yogas and Doshas *(proposed)* | KUN-P1-ADV | WP-B7 | To be added | ENG, RPT | Proposed |
| KUN-A06 Strengths *(proposed)* | KUN-P1-ADV | WP-B6 | To be added | ENG | Proposed |
| KUN-A07 Transits and periods *(proposed)* | KUN-P1-ADV | WP-B7 | To be added | ENG, RPT | Proposed |
| KUN-A08 Interpretations *(proposed)* | KUN-P1-ADV | WP-D2 | To be added | RPT | Proposed |
| KUN-A09 Premium reports *(proposed)* | KUN-P1-ADV | WP-D1, WP-D4, WP-E2 | To be added | ENG, RPT | Proposed |
| KUN-A10 Specialized products *(proposed)* | KUN-P1-ADV | WP-E2, WP-E3 | To be added | ENG, RPT, C | Proposed |
| KUN-A11 Bilingual reports *(proposed)* | KUN-P1-ADV | WP-D3 | QA-015, QA-016 + new | RPT | Proposed |
| KUN-A12 Report design system *(proposed)* | KUN-P1-ADV | WP-D1 | To be added | RPT | Proposed |
| KUN-A13 Commercial-demand validation *(proposed)* | KUN-P1-ADV | WP-E0 | Not a QA test (owner commercial signoff) | Owner decision | Proposed |

## 12. Owner review checklist
- [ ] Approve [PRD.md](PRD.md) MVP / P1 boundary.
- [ ] Resolve [DECISIONS.md](DECISIONS.md) P0 items or explicitly authorize discovery tasks to answer them.
- [ ] Approve requirements and QA coverage, including numerical methodology.
- [ ] Accept the phase order and gates above.
- [ ] Only then authorize Claude to implement the next bounded issue. *(Historical, 2026-10-21: "Existing CLAUDE-001 is an audit-only assignment". CLAUDE-001 is now complete, see section 3.2; every further Claude task needs its own owner authorization.)*
- [ ] *(1.1-proposed)* Decide the open items in [PRD section 14](PRD.md#14-open-owner-decisions) (OD-01 to OD-14), including the `KUN-P1-ADV` identifier, the ENG/RPT gates and the disposition of PRs #44 to #46.

**Owner approval record:** PENDING - exact commit/date/approval note to be added only after explicit decision.

## 13. Revision history
| Version | Date | Author | Change | Approval |
|---|---|---|---|---|
| 1.0-rc1 | 2026-10-21 | ChatGPT PM (planning PR #3) | Initial roadmap | PENDING |
| 1.0-rc1 + REL-01 | 2026-10-24 | Claude (PR #20) | REL-01 wording in KUN-01, CLAUDE-004, section 6, Gate A, Lagna risk | REL-01 owner approved / canonical, adoption merge `5b71408` |
| 1.1-proposed | 2026-10-28 | Claude (CLAUDE-DOC-014, issue #49) | Milestone and task status as of 2026-10-27; KUN-04 naming correction and proposed KUN-P1-ADV; Workstreams A to E; ENG and RPT gates; traceability; next assignments. Revised 2026-10-28 for ChatGPT review 5678627440: #44 to #46 QA relabelled pending OD-12, historical sentences labelled, dependency wording, WP-E0 / KUN-A13 | PENDING owner review |
