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
| SCI-01 | Sidereal method | Lahiri ayanamsa, **mean** Rahu/Ketu, sidereal ascendant, whole-sign houses | True node / other ayanamsa / house geometry materially change results; keep documented, versioned | PARTIAL: SCI-01b and SCI-01c approved 2026-10-22; all other SCI-01 choices PENDING |
| SCI-02 | Numerical product scope | D1 + full D9 incl. ascendant, planets, degrees, Rashi/Nakshatra/Pada; Dasha later | Including Dasha/Yoga/Dosha in MVP delays accuracy QA and grows interpretation scope | PENDING |
| SCI-03 | Supported initial birth years | 1900–2100 for **validated** MVP; reject outside explicitly | Swiss Ephemeris may support larger date range, but historical timezone/data accuracy must be qualified separately | PENDING |
| UX-01 | Anonymous use and unknown birth time | Free, no account to calculate; exact time mandatory for D1/D9; helpful unknown-time explanation | Date-only mode could be a later independently defined feature | PENDING |
| UX-02 | Presentation | North Indian D1 + D9, Hindi/English, browser result and PDF; South Indian chart P1 | Chart conventions and bilingual approval scope impact schedule | PENDING |
| DATA-01 | Offline location coverage | GeoNames or equivalently reviewed locally stored geographic data with IANA zones, India-first quality; refuse ambiguous location | All-world gazetteer is larger, with import and alias QA; licensing and historical support require review | PENDING |
| SEC-01 | Profile retention | MVP entirely stateless; no saved birth profiles; short-lived protected PDF generation | Optional saved accounts require consent, deletion/auth and additional product scope | PENDING |
| LEG-01 | AGPL deployment boundary | Release Kundali combined work under AGPL, preserve notices and provide network Corresponding Source; qualified review before activation | Separation from Shopify must be assessed rather than assumed | PENDING |
| PERF-01 | SLO | Proposed core calculation p95 < 2 sec; PDF p95 < 10 sec on profiled VPS reference configuration | Final budget depends on first benchmark, network route and user traffic | PENDING |
| UX-03 | Brand & religious copy | Premium Sabpuja visual system, helpful traditional explanatory tone, optional contextual commerce | No guarantee, fear-oriented predictions or fixed hardcoded commerce | PENDING |

## Approved scientific sub-decisions (owner, 2026-10-22)

The Sabpuja owner explicitly accepted ChatGPT PM's recommendation in the project conversation on **2026-10-22**: **retain the existing Swiss Ephemeris mean Rahu and derive Ketu exactly opposite the unrounded Rahu** for the Kundali MVP. This approval is deliberately **limited to SCI-01b and SCI-01c**; the SCI-01 parent decision is not wholly approved.

| ID | Owner-approved choice | Status | Effective scope / provenance |
|---|---|---|---|
| SCI-01b | **Mean Rahu = the adjusted mean lunar node returned by the pinned Swiss Ephemeris `MEAN_NODE` implementation**, not the Swiss true/osculating node and not an independently chosen textbook lunar-node polynomial. Preserve the current mode and numerical outputs. | **OWNER APPROVED - 2026-10-22** | Kundali MVP only. Owner explicitly accepted ChatGPT PM's Swiss mean Rahu recommendation in project conversation, 2026-10-22. Current foundation baseline `d8193c692d52aa12595f81c227638a061605a3d9`; scientific analysis at draft PR #11 (`d4e9d9eb0c008a09744bb5a49f6bcf88f580319c`). |
| SCI-01c | **Ketu = mean Rahu + exactly 180 degrees**, normalized cyclically and classified from the unrounded Rahu value. | **OWNER APPROVED - 2026-10-22** | Kundali MVP only. Owner accepted the paired Rahu/Ketu recommendation; existing exact arithmetic incorporated by CLAUDE-002c (PR #10). |

**Scientific validation boundary:** The Swiss-specific adjusted mean-node definition is an **approved convention**, not observational proof that this is the uniquely correct lunar node. Tests against the same Swiss implementation are definition/implementation conformance, **not independent astronomical accuracy**. Independently coded published node formulae are useful to report method differences, but their disagreement must not be treated as a failed numerical tolerance for this different approved definition. No `T-NODE` or golden-chart tolerance has been frozen; KUN-01 PG-2 and its reference-provenance checks remain outstanding.

**Still PENDING:** SCI-01a (Lahiri variant), SCI-01d (planetary frame/coordinates), SCI-01e (ascendant `b"P"` vs `b"W"`), SCI-01f (D1/D9 house conventions), SCI-01g (latitude policy), SCI-01h (UTC/UT1 policy), SCI-02 (MVP additions), SCI-03 (year and historical-clock policies) and all other pending product decisions. This entry **does not authorize a code change, a PR merge, new customer-facing calculation claims, a production deployment, or a release**. Any future true-node / polynomial alternative requires a separate owner decision and independent fixtures.

---

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

**As of 2026-10-22, the owner has approved SCI-01b and SCI-01c only.** All remaining scientific and product decisions are pending; foundation PR #1 remains draft and unmerged. Claude's audit/QA work is not acceptance of any other provisional method.
