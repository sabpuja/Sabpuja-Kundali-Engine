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

## Existing foundation and governance (draft PR #1, pending merge)
The foundation PR contains `README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/project-governance.md`, `docs/accuracy-plan.md`, `docs/api-contract.md`, `docs/privacy-security.md`, and `docs/qa-review-template.md`.

- [Draft foundation PR #1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1)
- [CLAUDE-001 audit issue #2](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/2)

The existing `docs/roadmap.md` in that draft is a **preliminary outline**. Upon merge of these project planning docs, `docs/DEVELOPMENT-ROADMAP.md` becomes the **canonical detailed plan**, and the foundation branch should align its outline/readme links accordingly. Do not create a competing second roadmap.

## Ownership rules
- Human Sabpuja owner makes product/release decisions; ChatGPT is PM and independent QA; Claude develops in scoped PRs only.
- All Kundali project plans, accepted methods, validation reports and engineering handoffs are stored and linked **here**.
- Shopify/brand-related code remains in its respective owning repository and may link back to this project's requirements, but is not authorized or changed by writing these documents.
- **No GitHub Actions, no auto deploy, no real birth PII in GitHub, no third-party astrology API, no live-site changes without separate owner approval.**

## Current stage
Documentation is **draft for owner approval**, calculation foundation is a separate **unmerged draft PR**, and no numerical accuracy test, public service or Shopify integration is considered signed off. Before authorizing material new development: review PRD -> settle critical DECISIONS -> approve roadmap -> Claude audit and narrowly scoped fixes -> independent QA.
