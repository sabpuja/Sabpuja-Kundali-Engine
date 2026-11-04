# Kundali Project Delivery & Review Contract

Status: proposed governance on draft foundation PR #1. Applies once reviewed and merged.
Decision date: 2026-10-21. Owner: Sabpuja product owner.

## Three roles
- **Product Owner (human):** Defines outcomes, approves scope and priority, accepts or rejects release candidates, authorizes cost/credential/data access, production deployment and launch. May request changes at any time.
- **Project Manager / Independent QA (ChatGPT):** Defines and prioritizes bounded work packages, maintains acceptance criteria and decisions, reviews **all developer PRs and material code/function changes**, examines real local/VPS test evidence, independently validates numerical/UX/security/compliance claims, raises defects, recommends acceptance or rejection, and gives an owner-ready release brief. ChatGPT does not continuously observe GitHub; a PR URL or explicit check-in triggers review. Availability of a connector does not imply an automatic approval bot.
- **Implementer (Claude / Claude Code):** Designs and implements only assigned scope, runs tests and static checks locally/approved VPS, provides reproducible artifacts and exact commit SHAs, documents changes, repairs QA findings, and submits reviewable draft PRs. Claude must **not self-approve, merge, launch, grant credentials, or silently change conventions**.

ChatGPT owns coordination and QA, not the production server. Execution by Claude requires separate authenticated repository and machine access configured by the owner/operator. Claude has not been connected or authorized by this document.

## Single source of truth
- Kundali product requirements and scientific decisions: this repository (`docs/DECISIONS.md`; DEC-004). Cross-repo and organization-wide decisions: `sabpuja/core`.
- Engine code, methodology, reference fixtures, validated releases: **this repository**.
- Shopify frontend: `sabpuja/theme`. Design rules: `sabpuja/design-system`.
- Current state/router: `sabpuja/Progress-Memory`.
- Operational process, if promoted: `sabpuja/Process-and-Workflows`.
- Do not create a second Kundali calculation repo or duplicate existing features.

## Mandatory delivery workflow
1. Owner requests/approves a defined outcome. PM writes a numbered, testable work package with acceptance criteria and explicit forbidden scope.
2. Claude reviews repo instructions, open PRs, upstream API/licensing documentation and the current exact baseline SHA. Claude asks the PM for scope disputes rather than inventing policy.
3. Claude works on a scoped branch and draft PR. All substantive code changes require a PR; never push directly to `main`. No GitHub Actions or agent-loop automation.
4. Claude supplies exact diff, changed functions/interfaces, test commands/results, failures, independent reference provenance, security/privacy/licensing impact and rollback guidance using `docs/qa-review-template.md`.
5. PM reads changed code and evidence, checks existing public contracts, independently reproduces feasible tests, compares independently sourced numeric reference charts, performs security/privacy/license scrutiny, and records **PASS / CHANGES REQUESTED / BLOCKED** with defects.
6. Claude repairs issues and reports new commit SHA. PM re-reviews changed scope and regressions. Repeat until PASS is justified.
7. Owner authorizes merge and, separately, any staging integration, VPS deployment or release. A QA PASS is a recommendation, **not** deployment authorization.
8. Record the verified checkpoint in Progress-Memory after canonical code merges. Never mark tentative work as released.

## Change-control triggers requiring owner decision before implementation
New scope or paid dependency, astronomy convention change (ayanamsa, nodes, houses, sidereal mode, epoch, supported year range), license model, customer data storage, new public API, design departure, broad repository permissions, third-party network API, production/staging mutation, VPS infrastructure/credentials, or automatic publishing.

## Nonnegotiables
- No third-party runtime astrology API, invented chart numbers, fake validation receipts, or fabricated sources.
- AGPL-3.0 project obligations and Swiss Ephemeris notices remain intact; legal signoff before network launch.
- No real birth profiles or secrets in GitHub, comments, screenshots, telemetry or fixture files.
- Deterministic computations are authoritative; AI may explain verified outputs but must not supply calculations.
- Fail closed on missing/mismatched ephemeris data or ambiguous birth time/place/timezone.
- No GitHub Actions, unattended merge/deploy, or live Shopify changes.
- Stop GitHub writes and do not retry automatically on policy-related 403/429, following `sabpuja/core/docs/policies/GITHUB-SAFETY-GUARDRAILS.md`.

## Definition of done
A task is **done** only with merged owner-approved code, reproducible QA evidence, updated user/developer documentation, security and license checks where relevant, and a verified checkpoint. A feature is **released** only after a separately authorized and verified deployment.
