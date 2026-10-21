# Project Decisions, Assumptions and Approval Register

**Document ID:** SP-KUN-DEC-001 | **Date:** 2026-10-21 | **Status:** OWNER REVIEW REQUIRED

This file is the **only** editable Kundali product decision register. Proposed choices are *not* approvals. ChatGPT PM/QA documents the recommendation; Sabpuja human owner approves the selected option. Claude never decides unresolved product/security/astronomy conventions unilaterally. Every approved decision needs Git SHA/owner confirmation/date.

## Confirmed owner direction
| ID | Decision | Status | Source |
|---|---|---|---|
| DEC-001 | First-party, fully self-hosted Kundali computation with Swiss Ephemeris. No third-party astrology API. | Owner-directed | Project conversation, 2026-10-21 |
| DEC-002 | Choose Swiss Ephemeris AGPL approach for independent Kundali project; source and data licensing reviewed before network release. | Owner-directed, compliance pending | Project conversation, 2026-10-21 |
| DEC-003 | Human is project owner; ChatGPT project manager/independent QA; Claude lead implementer with owner merge/deploy authority. | Owner-directed | Project conversation, 2026-10-21 |
| DEC-004 | All Kundali project requirements, roadmap, decisions, execution/QA docs reside in `sabpuja/Sabpuja-Kundali-Engine`. Do not change `sabpuja/core` for these documents. | Owner-directed | Project conversation, 2026-10-21 |
| DEC-005 | No GitHub Actions, no staging/live Shopify changes without explicit authorization; development evidence through controlled workstation/VPS. | Owner-directed | Existing governance and project conversation |

## P0 choices to confirm before authorizing feature implementation
| ID | Decision needed | Proposed default | Alternatives / why it matters | Owner choice |
|---|---|---|---|---|
| SCI-01 | Sidereal method | Lahiri ayanamsa, **mean** Rahu/Ketu, sidereal ascendant, whole-sign houses | True node / other ayanamsa / house geometry materially change results; keep documented, versioned | PENDING |
| SCI-02 | Numerical product scope | D1 + full D9 incl. ascendant, planets, degrees, Rashi/Nakshatra/Pada; Dasha later | Including Dasha/Yoga/Dosha in MVP delays accuracy QA and grows interpretation scope | PENDING |
| SCI-03 | Supported initial birth years | 1900–2100 for **validated** MVP; reject outside explicitly | Swiss Ephemeris may support larger date range, but historical timezone/data accuracy must be qualified separately | PENDING |
| UX-01 | Anonymous use and unknown birth time | Free, no account to calculate; exact time mandatory for D1/D9; helpful unknown-time explanation | Date-only mode could be a later independently defined feature | PENDING |
| UX-02 | Presentation | North Indian D1 + D9, Hindi/English, browser result and PDF; South Indian chart P1 | Chart conventions and bilingual approval scope impact schedule | PENDING |
| DATA-01 | Offline location coverage | GeoNames or equivalently reviewed locally stored geographic data with IANA zones, India-first quality; refuse ambiguous location | All-world gazetteer is larger, with import and alias QA; licensing and historical support require review | PENDING |
| SEC-01 | Profile retention | MVP entirely stateless; no saved birth profiles; short-lived protected PDF generation | Optional saved accounts require consent, deletion/auth and additional product scope | PENDING |
| LEG-01 | AGPL deployment boundary | Release Kundali combined work under AGPL, preserve notices and provide network Corresponding Source; qualified review before activation | Separation from Shopify must be assessed rather than assumed | PENDING |
| PERF-01 | SLO | Proposed core calculation p95 < 2 sec; PDF p95 < 10 sec on profiled VPS reference configuration | Final budget depends on first benchmark, network route and user traffic | PENDING |
| UX-03 | Brand & religious copy | Premium Sabpuja visual system, helpful traditional explanatory tone, optional contextual commerce | No guarantee, fear-oriented predictions or fixed hardcoded commerce | PENDING |

## Post-MVP choices (do not block audit/foundation)
| ID | Topic | Status |
|---|---|---|
| P1-01 | Save Kundalis to authenticated Sabpuja customer dashboard | Deferred - new consent/access design |
| P1-02 | Vimshottari Dasha and Antardasha | Deferred - separate method + fixtures |
| P1-03 | Gun Milan, further divisional charts, Yoga/Dosha rules | Deferred - separate cultural/method QA |
| P1-04 | South Indian chart or other visual chart models | Deferred - additional UI contract |
| P1-05 | Shraddha conversational interpretation of rule-grounded outputs | Deferred - privacy/editorial gating |

## Decision record template
```
ID:
Options reviewed and evidence:
Recommended choice:
Owner decision / requested modification:
Effective scope/version:
Date:
Authoritative approval link / Git commit:
Change request needed: YES | NO
```

## Approval to begin Claude implementation
- [ ] Owner approves PRD scope and initial year/method/locale choices.
- [ ] Owner accepts the phase plan and independent QA gates.
- [ ] Open critical legal/data-rights risks are assigned for investigation.
- [ ] First new implementation ticket names source SHA, acceptance cases and exact bounds.

**As of 2026-10-21 no owner approval has been recorded in this file.** Claude issue #2 may audit existing code without implying acceptance of the provisional methods.
