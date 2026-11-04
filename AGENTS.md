# Kundali Engine Agent Instructions

Scope: entire repository. All humans and agents must read README.md, machine/capabilities.json, docs/architecture.md, docs/accuracy-plan.md and docs/licensing.md before substantive work.

## Project-specific owner / PM / builder contract (2026-10-21)
- The human Sabpuja owner sets priorities and has final merge/release authority.
- ChatGPT is project manager and independent QA reviewer for **all material developer code, functions, interfaces and PRs**.
- Claude / Claude Code is the implementation developer, not the approver. Its GitHub/desktop access must be granted separately; it is not connected by these instructions alone.
- Read `docs/project-governance.md`, `docs/qa-review-template.md` and `machine/project-roles.json` before beginning work.
- Claude's first assignment was `docs/claude-builder-brief-001.md` (CLAUDE-001, issue #2): audit draft PR #1 and supply reproducible evidence, not a rewrite.
- Every code PR follows: scoped task -> Claude implementation and local tests -> draft PR with proof -> ChatGPT QA verdict -> Claude repairs -> owner-approved merge. Staging and production each require separate authorization.
- No direct main pushes, self-merge, AI-generated numeric fixture claims, silent workflow changes, or unreviewed feature expansion. ChatGPT's review occurs when a PR is explicitly presented or checked, not as a continuous autonomous watcher.

## Ownership and routing
1. This repository alone owns Kundali computation source code, divisional rules, deterministic report calculation contracts, fixtures and engine releases.
2. Kundali requirements, roadmap and scientific decision register: this repository (`docs/PRD.md`, `docs/DEVELOPMENT-ROADMAP.md`, `docs/DECISIONS.md`; DEC-004). Organization-wide policy: sabpuja/core. Shopify theme/Component Lab: sabpuja/theme. Design authority: sabpuja/design-system. Agent orchestration (only if later authorized): sabpuja/Automation. Current state/routing: sabpuja/Progress-Memory. Do not duplicate those systems here.
3. No third-party runtime astrology API, outbound chart data, AI-invented planet positions or unverified interpretation claims.
4. Use offline/local Swiss Ephemeris, local ephemeris data and an offline geographic/timezone pipeline. Never silently downgrade missing Swiss files to Moshier.
5. Chart method must be explicit in every output: ayanamsa, node method, house method, timezone/offset, ephemeris version and birth coordinates.
6. Fail on ambiguous/missing birth time and incomplete timezone input. Do not invent a time, longitude, city match or reference result.
7. Reconcile all calculations with independently reviewed golden charts before claiming accuracy, deploying or producing paid reports.
8. Preserve AGPL-3.0 obligations and upstream notices. Provide full corresponding source for modified AGPL network services when activated. External code contributions require license/provenance review.
9. No secrets, personal birth profiles, credentials or customer data in GitHub or test fixtures. Logs must not record raw birth requests.
10. Never create GitHub Actions, workflow files, agents/daemons or scheduled jobs. Work happens locally or on an explicitly approved VPS. Stop on GitHub restriction 403/429.
11. Branch -> local checks -> documented evidence -> PR -> independent review. No self-approval; do not merge or deploy without appropriate approval.
12. Storefront integration exclusively against approved **unpublished** Shopify staging. Recheck theme topology just before any future theme writes.

## Source precedence
Upstream Swiss Ephemeris docs for astronomy API; this repo for implemented calculation rules and for Kundali requirements and decisions (`docs/DECISIONS.md`); core for organization-wide policy; Progress-Memory for verified current state. If sources conflict, stop and document the discrepancy.

## Current development checkpoint (2026-11-03, integration candidate)
This branch, `integration/kun-int-001` (KUN-INT-CAND-001), is an isolated integration candidate: `main` `25cfde4` merged with the PR #68 head `b1bca79` for independent integration QA only. It is not `main`, not a release and not deployed. Draft PR #1 remains on HOLD; its commits are present here by ancestry for QA only.
- Scientific decisions: SCI-01a to SCI-01h, SCI-02, SCI-03, REL-01, SCI-02 C2 (chart schema `0.3.0`, metadata `/3`), SCI-04 to SCI-06 and the Panchanga M1 method selections are canonical at their recorded scopes per `docs/DECISIONS.md` and the post-merge adoption receipts on PRs #64 and #65. Older "PENDING" wording in historical records, code comments and hash-pinned documents is frozen proposal text; do not edit it to update status.
- Implemented and QA'd at source heads: D1/D9 engine, owner-only prototype and gateway, ten-page saffron premium PDF with optional Full Name, the D1/D9 gold harness (exit 2: 49 PASS / 18 QUALIFIED / 1 BOUNDARY-INDETERMINATE, a qualified result, not certification) and Panchanga M1 (machine-only, not customer-facing).
- Owner-only preview runs PR #58 `fde3ec6`. No public endpoint, client access, app proxy or Shopify deployment exists. The bilingual interface and Hindi PDF (PRs #59 to #61) are outside this candidate. LEG-01 is pending. **Production: NO-GO.**
