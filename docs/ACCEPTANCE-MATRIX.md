# SP-KUN Acceptance Matrix - Requirements to Test Evidence

**Version:** 1.0-rc1 | **Status:** proposed | **Date:** 2026-10-21

No requirement is considered implemented or passed based on this document. Every row is a future test case. Claude attaches raw evidence on the **exact SHA**; ChatGPT independently reviews; Sabpuja owner approves merge and release.

## MVP functional and technical acceptance cases
| Test ID | PRD requirement | Test / observable pass condition | Test approach | Launch gate |
|---|---|---|---|---|
| QA-001 | KUN-F01 | Birth date/time fields are labeled, validated; generation without login; optional name does not enter astronomy calculation | Form E2E, keyboard and API contract | P0 |
| QA-002 | KUN-F01/F03 | Absent/unknown time does not become 00:00 or 12:00; time-dependent chart is blocked with explanatory error | Negative unit/E2E | P0 |
| QA-003 | KUN-F02 | Offline place search finds known cities; duplicate city names show region/country; selecting choice locks precise lat/lon + IANA zone | Offline dataset unit/E2E | P0 |
| QA-004 | KUN-F02/F11 | Place lookup and astronomy work with outbound internet blocked after approved local datasets installed | Network-isolated integration | P0 |
| QA-005 | KUN-F03 | Nonexistent local DST time rejected; ambiguous fold requires choice; offset validated against IANA zone revision | Historical timezone independent cases | P0 |
| QA-006 | KUN-F03 | Leap day, local date/UTC day crossover, 1900/2100 boundary, unusual fractional offset and negative longitude processed or rejected explicitly | Table-driven boundary tests | P0 |
| QA-007 | KUN-F04 | Output identifies ayanamsa, node method, house method, ephemeris version/data manifest and exact timezone | Schema/output assertions | P0 |
| QA-008 | KUN-F04 | Engine fails closed on missing/incorrect .se1; no silent switch to Moshier; global sidereal configuration cannot leak between requests | Real ephemeris startup/concurrency tests | P0 |
| QA-009 | KUN-F05 | Sun, Moon, five classical grahas, Rahu/Ketu sidereal degrees agree with independently sourced method-compatible golden charts at **tolerances defined before running QA** | Independent numerical differential tests | P0 |
| QA-010 | KUN-F05 | Sidereal ascendant, D1 sign and whole-sign house assignment agree with reference chart convention, including 0/360 boundaries | Independent golden chart + property tests | P0 |
| QA-011 | KUN-F05 | North Indian chart houses/signs/planet labels exactly match structured API values; text table is equivalent | Renderer snapshot + manual review | P0 |
| QA-012 | KUN-F06 | D9 placements and D9 ascendant agree with independent reference fixtures including 3°20' sign divisions and boundaries | Numerical fixtures/property tests | P0 |
| QA-013 | KUN-F07 | Moon Rashi, Nakshatra and Pada match mathematical outputs and approved explanation rules, without guarantee language | Rule unit + editorial review | P0 |
| QA-014 | KUN-F08 | Visible birth-data confirmation, method/version, edit/recalculate and correct error state | E2E | P0 |
| QA-015 | KUN-F09 | Identical inputs produce identical numerical outputs EN vs HI, including number semantics and chart geometry | Locale invariance test | P0 |
| QA-016 | KUN-F09 | All UI labels, validation, chart legends, and PDF text human-reviewed in Hindi; no missing glyphs or clipped Devanagari | Native speaker QA + screenshots/PDF | P0 |
| QA-017 | KUN-F10 | User can download D1+D9 PDF with key positions/method; file belongs only to requesting user/session and has short retention | Download E2E, PDF inspect, authorization/TTL tests | P0 |
| QA-018 | KUN-F11 | Reject malformed/oversized requests, unknown schema, invalid latitude/longitude, abusive traffic and unauthenticated access | API negative/security tests | P0 |
| QA-019 | KUN-F11 | Stable response schema, errors and rate-limit contract; measured p95 core compute against pinned load profile | Contract + benchmark report | P0 |
| QA-020 | KUN-F12 | Shopify unpublished staging page loads and calculates via approved validated proxy; no public secrets or client-side direct trusted-key calls | Manual/automated E2E + network inspect | P0 |
| QA-021 | KUN-F12 | Product links/prices/images, if present, sourced from Shopify dynamically; no catalog facts hardcoded | Theme/API inspection | P0 |
| QA-022 | KUN-F13 | Form keyboard, visible focus, zoom >=200%, accessible chart table, screen reader announcements, reduced motion | Manual a11y checklist + audit | P0 |
| QA-023 | KUN-F13 | Fluid UI avoids horizontal overflow on narrow viewport, mobile, desktop and Hindi long strings | Visual responsive QA | P0 |
| QA-024 | KUN-F14 | No birth data in source control, logs, analytics payloads, errors, URLs, cache or metrics; stdout/PDF data controlled | Threat-model verification + redacted log scan | P0 |
| QA-025 | KUN-F14 | Default user flow writes no durable profile; any temp PDF/report is inaccessible publicly and expires per approved retention | Storage, TTL, cache and access tests | P0 |
| QA-026 | KUN-F15 | Full relevant AGPL Corresponding Source and notices are accessible, versions pinned, dataset licenses reviewed | Legal/license checklist + source link click-through | P0 |
| QA-027 | KUN-F16 | Release artifact tied to exact source SHA, ephemeris SHA, test run ID, launch approver and rollback tested | Operator release rehearsal | P0 |
| QA-028 | KUN-F16 | GitHub Actions absent; staging-only target verified immediately before Shopify write; no uncontrolled deploy or agent permission | Governance review | P0 |
| QA-029 | KUN-F07/F12 | Interpretation and commerce content have approved editorial provenance; no medical/financial guarantees or coercive remedies | Editorial/content QA | P0 |
| QA-030 | KUN-F10/F11 | p95 PDF request under proposed 10 sec on defined warm/cold representative test profile; safe timeout and failure behavior | Local/VPS performance run | Proposed release target; confirm at owner gate |

## Test evidence format
Evidence should include:
1. Work package, PR, exact head SHA, OS, Python version, Swiss library/binding versions, dataset revision + SHA-256 and timezone revision.
2. Exact commands, unedited output, test pass/fail/skip counts, execution dates and environmental constraints (never secrets or birth PII).
3. External independent reference source/method, source-rights confirmation, anonymized/synthetic inputs, **predeclared** angle/time tolerances and per-body differences.
4. UX screenshots without real people or birth details; locale/glyph checks and PDF checksums; source and staging URL read-back when approved.
5. Reviewer conclusion **PASS / CHANGES REQUESTED / BLOCKED** plus defects, reopen conditions and owner decision link.

## Severity and completion semantics
- **Blocker/Critical:** Numerically wrong chart, unknown/missing time silently substituted, ephemeris fallback, privacy leak, unlicensed distribution, unauthenticated data service, live unauthorized change, unreviewed launch. No release.
- **High:** Broken Hindi, D9 mislabel, faulty DST/city selection, PDF authorization error, inaccessible critical form. Must be resolved before launch.
- **Medium:** Noncritical polish, formatting/legibility defect without information loss. PM and owner disposition required.
- **Low:** Cosmetic inconsistency not altering information or accessibility. Can be deferred explicitly.

A **PASS** means verified evidence for the exact cited SHA, not source merged or released. Merged and deployed require separate owner permission.

## Progressive acceptance checkpoints
- **G-DOC:** Owner signs PRD, method choices and roadmap.
- **G-ENGINE:** QA-005-010, QA-012 and relevant reference-suite assertions PASS.
- **G-DATA:** QA-003-006, QA-008 PASS.
- **G-SERVICE:** QA-018-019, QA-024-026 PASS.
- **G-UX:** QA-001-002, QA-011, QA-013-016, QA-021-023, QA-029 PASS.
- **G-PDF:** QA-017, QA-030 PASS.
- **G-STAGING:** QA-020, QA-027-028 PASS plus explicit authorization.
- **G-LAUNCH:** All P0 cases PASS, documented exemptions (if any) approved by owner, legal/privacy review signed, owner production authorization.

## Baseline truth as of document drafting
The foundation draft PR #1 contains some authored rule and contract tests, **not independently verified accuracy**. No documented executed test evidence is available in this planning document. All QA IDs remain **NOT RUN** until actual evidence is reviewed.
