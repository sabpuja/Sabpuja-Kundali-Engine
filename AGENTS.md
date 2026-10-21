# Kundali Engine Agent Instructions

Scope: entire repository. All humans and agents must read README.md, machine/capabilities.json, docs/architecture.md, docs/accuracy-plan.md and docs/licensing.md before substantive work.

## Ownership and routing
1. This repository alone owns Kundali computation source code, divisional rules, deterministic report calculation contracts, fixtures and engine releases.
2. Requirements/policy: sabpuja/core. Shopify theme/Component Lab: sabpuja/theme. Design authority: sabpuja/design-system. Agents/Hermes orchestration: sabpuja/Automation. Current state/routing: sabpuja/Progress-Memory. Do not duplicate those systems here.
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
Upstream Swiss Ephemeris docs for astronomy API; this repo for implemented calculation rules; core for organizational policy; Progress-Memory for verified current state. If sources conflict, stop and document the discrepancy.

## Current development checkpoint
Scaffold/foundation is proposed. No production chart validation, public endpoint, VPS installation, app proxy, or Shopify deployment has been performed.
