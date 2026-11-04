# Kundali Project Documentation Hub

**Single canonical project home:** [Sabpuja-Kundali-Engine](https://github.com/sabpuja/Sabpuja-Kundali-Engine). These files are versioned together in this repository, not in `sabpuja/core`.

## Start here
| Reader | Document | Use |
|---|---|---|
| Owner / product | [PRD.md](PRD.md) | Product vision, MVP, future scope, functional and nonfunctional requirements |
| Owner / PM / Claude | [DEVELOPMENT-ROADMAP.md](DEVELOPMENT-ROADMAP.md) | Milestones, work packages, dependency sequence and release gates |
| ChatGPT PM / QA | [ACCEPTANCE-MATRIX.md](ACCEPTANCE-MATRIX.md) | Required test IDs, severity, proofs and signoff gates |
| Owner / PM | [DECISIONS.md](DECISIONS.md) | Owner-confirmed direction, pending decisions, approval records |
| Agents & tools | [../machine/project-plan.json](../machine/project-plan.json) | Machine-readable document routes and phase definitions |
| Claude Code | [../CLAUDE.md](../CLAUDE.md) | Code agent read order, scope and QA rules |
| Claude Project settings | [CLAUDE-PROJECT-SETUP.md](CLAUDE-PROJECT-SETUP.md) | Copy-paste Goal and Context fields for the external Claude Project |

## Existing foundation and governance (from draft PR #1, integrated through PR #69)
The foundation PR contains `README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/project-governance.md`, `docs/accuracy-plan.md`, `docs/api-contract.md`, `docs/privacy-security.md`, and `docs/qa-review-template.md`.

- [Draft foundation PR #1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1)
- [CLAUDE-001 audit issue #2](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/2)

These files reached `main` on 2026-11-04 through the PR #69 merge (`b7bf1cc`), under owner decision D-6 for the exact independently reviewed candidate. PR #1 was not merged separately; GitHub marked it merged automatically because its head is now part of `main`. The existing `docs/roadmap.md` is a **preliminary outline**, marked as superseded. `docs/DEVELOPMENT-ROADMAP.md` is the **canonical detailed plan**; its own header gives its current review status. Do not create a competing second roadmap.

## Ownership rules
- Human Sabpuja owner makes product/release decisions; ChatGPT is PM and independent QA; Claude develops in scoped PRs only.
- All Kundali project plans, accepted methods, validation reports and engineering handoffs are stored and linked **here**.
- Shopify/brand-related code remains in its respective owning repository and may link back to this project's requirements, but is not authorized or changed by writing these documents.
- **No GitHub Actions, no auto deploy, no real birth PII in GitHub, no third-party astrology API, no live-site changes without separate owner approval.**

## Current stage
See the "Current truth" and "Scientific decision status" sections of the [project README](../README.md). In short: scientific decisions are canonical where [DECISIONS.md](DECISIONS.md) and its post-merge adoption receipts say so (including [PR #64 receipt 6598563378](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/64#issuecomment-6598563378) for SCI-04 to SCI-06 and [PR #65 receipt 6600051638](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/65#issuecomment-6600051638) for the Panchanga M1 method). The D1/D9 engine, ten-page premium PDF, gold harness and Panchanga M1 (machine-only) are in `main` as source since PR #69; none is released. The owner-only preview runs PR #58. Bilingual PRs #59 to #61, LEG-01, bilingual editorial acceptance and the customer-release gates remain pending. **Production: NO-GO.**
