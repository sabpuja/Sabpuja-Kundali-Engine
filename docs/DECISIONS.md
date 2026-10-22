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


## Proposed scientific decisions: KUN-02 Phase 2 (PROPOSED, NOT APPROVED)

**Status: every entry below is PENDING owner approval.** This section records proposals and evidence only. It does not approve any convention, authorize any code change, PR merge, customer-facing claim, deployment or release. SCI-01b and SCI-01c above are unchanged.

Full rationale, alternatives, limitations, effect on results, input changes and required regression tests: [KUN-02-P2-decision-package.md](decisions/KUN-02-P2-decision-package.md). Evidence locations and the consistency review: [KUN-02-P2-evidence-map.md](decisions/KUN-02-P2-evidence-map.md). Approval actions, implementation sequence, compatibility and release risks: [KUN-02-P2-implementation-and-risks.md](decisions/KUN-02-P2-implementation-and-risks.md).

Evidence base (all unmerged drafts, cited by exact SHA): Swiss conformance PR #18 @ `66692d7d7d5a0cbef5a6354bb6ecfbd3f2478b38` ([final QA](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/18#pullrequestreview-5609326875): Swiss-on-Swiss conformance only) and KUN-02 Phase 1 PR #19 @ `1986b0aa4702c42140d7cf1cc2c7249d03ae1bf0` ([final QA](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/19#pullrequestreview-5610433809): research and test harness only). Neither is independent astronomical accuracy evidence.

| ID | Proposed convention | Evidence (see evidence map) | ChatGPT scientific QA recommendation | Owner approval and canonical adoption |
|---|---|---|---|---|
| SCI-01a | Swiss `SE_SIDM_LAHIRI` (mode 1; 23°15'00.658" at 1956-03-21 0h TT, IAE 1985 revision), **true** ayanamsha, pinned Swiss 2.10.03 default precession; `set_ephe_path` + `set_sid_mode(SIDM_LAHIRI, 0, 0)` on every request under the Swiss lock; no `SIDBIT_*` options | E-A5, E-A11, E-LAHIRI, E-FRAME, E-SC18 | Supports the existing Lahiri direction; no formal approval (PR #19 final QA) | **PENDING** |
| SCI-01d | Geocentric apparent sidereal longitudes on the true ecliptic and equinox of date minus the true ayanamsha: `calc_ut(jd_ut, body, FLG_SWIEPH \| FLG_SIDEREAL)`, no other flags; refuse if `FLG_SWIEPH` is not returned (no Moshier fallback) | E-FRAME, E-SC18 (882/882), E-C1 | Supports the geocentric apparent direction; no formal approval (PR #19 final QA) | **PENDING** |
| SCI-01e | Sidereal Lagna = `ascmc[0]` of `houses_ex(jd_ut, lat, lon, b"W", FLG_SIDEREAL)`; definition unchanged (eastern rising point minus true Lahiri); **only together with or after SCI-01g** | E-A1 (167,612 bit-identical P/W), E-A2, E-A3/A4, E-A6, E-A7, E-A12 | Favour `b"W"` only paired with or following a fixed \|lat\| ≤ 66.0° limit (PR #19 final QA) | **PENDING** |
| SCI-01f | D1 whole-sign houses from the Lagna Rashi; Navamsa = 108 equal 3°20' segments from Mesha; D9 Lagna = Navamsa sign of the unrounded Lagna; D9 whole-sign houses from the D9 Lagna; all from unrounded values | E-A8, E-A9, E-A10 (90,720 checks), E-RULE18 | Supports the D1 + D9 direction; no formal approval (PR #19 final QA) | **PENDING** |
| SCI-01g | Supported latitude −66.0 ≤ lat ≤ +66.0 inclusive for every date; refuse outside with `LATITUDE_OUTSIDE_SUPPORTED_BAND`; disclose time sensitivity above 60°. A product envelope, not a computational limit | E-A3/A4, E-POLAR (66.5467°–66.5752°), E-RATE, E-ENV-LAT | Fixed ±66.0° product envelope favoured; P2 before or with P3 (PR #19 final QA) | **PENDING** |
| SCI-01h | Keep civil UTC (via IANA offset) passed to Swiss as UT1, TT = UT1 + Swiss ΔT; label by era in metadata; UT1 − UTC within 0.9 s only under the IERS rule while it stands (here *implied under the Swiss ΔT model*, not measured); 27th CGPM (2022) Resolution 4 raises that limit in or before 2035; record the Swiss 2.10.03 sidereal-time model step at 2050-01-01; review before 2035 | E-B3, E-SIDT, E-CLOCK | Honest epoch-specific metadata; do not assume < 0.9 s indefinitely; 2050 step is version-specific (PR #19 final QA) | **PENDING** |
| SCI-02 | MVP outputs: D1 longitude, Rashi and whole-sign house for the 7 grahas, mean Rahu and Ketu; Lagna longitude and Rashi; D9 sign of every body and Lagna; D9 whole-sign houses; Moon Rashi, Nakshatra and Pada; calculation metadata. Owner option: Nakshatra/Pada for all bodies and Lagna. Dasha and other charts deferred | E-A10, E-RULE18, E-SC18 | Supports the D1 + D9 direction; no formal approval (PR #19 final QA) | **PENDING** |
| SCI-03 | Local civil birth date 1900-01-01 to 2100-12-31 inclusive, checked before conversion; explicit offset validated against IANA, gaps refused, folds disambiguated by the offset; pinned `tzdata` plus a versioned TZif byte manifest, deterministic loading, no mid-process global time-zone changes; `HISTORICAL_CLOCK_UNVERIFIED` fail-closed for Asia/Kolkata before 1956-01-01 as a **temporary minimum**; owner chooses the pre-1970 scope: (A) that minimum only, (B) plus every other zone before 1970 (Kolkata 1956–1969 still accepted), (B-full) every zone before 1970 including Kolkata 1956–1969 (recommended for public release), or (C) plus South Asian zones before 1970; DATA-01 historical-clock research before any verified exception; future dates disclosed as projected; no invented offsets | E-B1, E-B2 (74,864 comparisons), E-EDGE, E-C1, E-TZBUILD, E-CLOCK | Local civil date, deterministic TZif and the temporary pre-1956 minimum endorsed (PR #19 final QA) | **PENDING** |

Recording an owner decision on any row takes two steps, so that no record needs a SHA that does not exist yet:

1. **Pre-merge approval record**, written in the PR that changes this register: owner choice (approve, modify or reject), date, approval link, effective scope, and the exact reviewed head SHA. The row's status stays PENDING in the register text until step 2.
2. **Post-merge adoption receipt**, written after the owner-authorized merge, in a follow-up commit or linked from the merged PR's metadata: the merge SHA and date. Only then is the row OWNER APPROVED and canonical.

A ChatGPT QA review alone never changes a row from PENDING. Until a row is adopted, the implementation packages (P1–P9) that depend on it remain unauthorized.

**Open source-of-truth conflict (pending owner reconciliation, not waived):** `docs/PRD.md` (product truth; KUN-F16; the "Astronomy accuracy" release gate) and `docs/ACCEPTANCE-MATRIX.md` (P0 QA-009, QA-010, QA-012; G-ENGINE) still require independently sourced golden-chart validation before accurate public claims. The owner-approved Swiss-first change of 2026-10-22 ([issue #15](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/15), [PR #17](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/17)) made independent JPL/INPOP astronomy assurance optional and deferred. These are not yet aligned. Until the owner approves an alignment in a separate doc-only change, **the public-release gate is not relaxed**. See [implementation and risks §4](decisions/KUN-02-P2-implementation-and-risks.md#4-release-gates-and-risks-requiring-separate-verification).
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
