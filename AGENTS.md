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

## Current development checkpoint (2026-10-24)
The foundation (draft PR #1, still unmerged) and the KUN-03 draft stack (PRs #23 to #35, each engineering-QA-passed at its exact head) are joined with `main` on `integration/kun03-gate1` for integration QA only. Decision-register rows other than SCI-01b and SCI-01c are PENDING. No independent golden-chart validation, public endpoint, VPS installation, app proxy, or Shopify deployment has been performed.
