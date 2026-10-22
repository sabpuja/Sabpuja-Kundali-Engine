# Sabpuja Kundali - Detailed Development Roadmap and Claude Delivery Plan

**Document ID:** SP-KUN-DEV-001 | **Version:** 1.0-rc1 | **Date:** 2026-10-21  
**Status:** DRAFT, awaiting owner review and baseline audit. **Authoritative requirements:** [PRD.md](PRD.md); **QA matrix:** [ACCEPTANCE-MATRIX.md](ACCEPTANCE-MATRIX.md); **decisions:** [DECISIONS.md](DECISIONS.md).

This roadmap defines *work and acceptance*, not permission for Claude to execute, merge or deploy. All Kundali project planning stays in this repository. No GitHub Actions. No modification of `sabpuja/core`. Other repo changes (e.g. Shopify theme) require separate, explicitly approved implementation PRs in their owning repo, referenced back here.

## 1. Operating protocol
- **Owner:** choose priorities, settle open product/astronomy/privacy decisions, approve each merge and all release targets.
- **ChatGPT PM/QA:** write scoped tickets with requirement + test IDs; review every material code/function/API change and actual test output; independently check numeric reference evidence; return PASS / CHANGES REQUESTED / BLOCKED; track regressions.
- **Claude:** read project docs and baseline SHA, implement only assigned slice, run local/approved-host tests, submit a draft PR plus the [QA evidence template in foundation PR #1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/blob/feat/initial-kundali-foundation-20261021/docs/qa-review-template.md) when available on the foundation branch; provide real output and fix QA defects. No direct `main` writes or self-merges.
- **Sources of truth:** existing draft [foundation PR #1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1), first [audit issue #2](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/2), project [governance](https://github.com/sabpuja/Sabpuja-Kundali-Engine/blob/feat/initial-kundali-foundation-20261021/docs/project-governance.md). Those foundation docs are proposed, **not merged**.
- **Strict gates:** approved spec -> scoped task -> Claude draft PR/tests -> independent QA -> owner merge -> explicit staging deploy approval -> independent staging QA -> separate owner launch approval.

## 2. Milestones, sequencing and objective exit gates
| Milestone | Work packages | Depends on | Evidence for PM/QA | Status |
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

## 3. Sprint-sized work package backlog
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

Each task should be one bounded issue with acceptance IDs (from [ACCEPTANCE-MATRIX.md](ACCEPTANCE-MATRIX.md)), size estimate and explicit excluded scope. No new issue is considered assigned merely because it appears in this plan; only issue #2 is already created. Grouping of tasks/PRs may be adjusted after audit, but not their safety gates.

## 4. Parallelism and dependency logic
1. **While CLAUDE-001 is auditing:** owner/PM complete PRD + method decisions; UX can be reviewed as non-deployed mockups only. Do not accept or merge unverified engine code.
2. **After KUN-01 accuracy gate:** birthplace/time validation and chart-renderer domain work can proceed in separate branches with pinned schema, while preventing conflicting data methods.
3. **After stable schema:** API/PDF/UI can run in coordinated branches, with versioned contracts and narrow reviews.
4. **Before staging:** signed privacy and API threat model; project owner permits theme access and isolated VPS test deployment.
5. **Before public production:** independent E2E, legal/compliance, rollback and owner signoff. No unattended release.
6. **P1 features:** only after separate prioritization and user-data consent requirements; never quietly add to MVP.

## 5. Definition of ready for a Claude task
- PRD requirement IDs + acceptance IDs, explicit owner scope approval.
- Known baseline branch and commit, interfaces and calculation conventions.
- Dependencies, external dataset rights, secret/access prerequisites.
- Negative cases, test/fixture provenance and measurable success.
- No critical unresolved upstream decision that would invalidate implementation.

## 6. Definition of done for a coding task
- Code and docs in specialist owning repo, PR linked to work package; no unrelated modifications.
- Static review, automated unit/contract and relevant integration tests run with raw results on exact SHA, plus the REL-01 reference cases for astronomical work (Swiss CLI conformance and independent rule/formula checks; independently sourced astronomy optional).
- User-facing EN/HI and accessibility checks when applicable; no exposed birth information.
- ChatGPT QA PASS on the exact updated SHA, defects remediated, owner merge approval and verified merge read-back.
- Any deployment is a separate approved phase; passing tests alone never means released.

## 7. QA gates and non-negotiable blockers
**Gate A - Astronomy:** Planet/Lagna and D1/D9 differences to the REL-01 references (Swiss CLI conformance, independent rule/formula checks; independent charts when the optional assurance is run) reported with methods and tolerances defined before evaluation. Stop on unverified Swiss .se1 data, silent Moshier fallback, time conversion errors, or wrong house/navamsa math.

**Gate B - Security:** Validate app-proxy authenticity, access control, rate limiting, input max, malformed dates, server-side errors, request replay, CORS/CSRF as applicable, and no birth data in logs/query strings. No unauthenticated open service.

**Gate C - Privacy/legal:** Document ephemeral report lifecycle, cookie/analytics consent, network source-offer operation, and AGPL-compatible boundary. A qualified license/privacy review is a public-release prerequisite, not a claim that review has happened.

**Gate D - Product/UX:** Fluid viewport, 200% zoom, Devanagari font embedding, keyboard navigation, accessible chart table, bilingual input/error messages and no hardcoded Shopify products.

**Gate E - Operations:** Test source/data pin, deterministic container config, no unapproved GitHub Actions, isolated Hostinger infrastructure, staging theme verification, clear rollback, exact owner approval.

## 8. Milestone review format
Use a record attached to the PR/issue:
```text
Milestone / Work package:
PR + exact reviewed SHA:
PRD requirements / acceptance IDs:
Test environment and commands:
Raw test report / independent reference provenance:
Security, locale, privacy, licensing evidence:
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

## 10. Owner review checklist
- [ ] Approve [PRD.md](PRD.md) MVP / P1 boundary.
- [ ] Resolve [DECISIONS.md](DECISIONS.md) P0 items or explicitly authorize discovery tasks to answer them.
- [ ] Approve requirements and QA coverage, including numerical methodology.
- [ ] Accept the phase order and gates above.
- [ ] Only then authorize Claude to implement the next bounded issue. Existing CLAUDE-001 is an **audit-only** assignment.

**Owner approval record:** PENDING - exact commit/date/approval note to be added only after explicit decision.
