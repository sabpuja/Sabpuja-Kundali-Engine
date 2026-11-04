# Human and agent access and onboarding

**Status: GitHub repository created; deployment and autonomous-agent authorization NOT configured.** Repo visibility is public. A public repo is readable without secrets, but pushes and pull requests must use approved GitHub identities/permissions.

## Human use
1. Read the [README](../README.md), [AGENTS.md](../AGENTS.md), and [capability manifest](../machine/capabilities.json).
2. Clone `https://github.com/sabpuja/Sabpuja-Kundali-Engine.git` to a managed workstation and checkout an approved release or reviewed branch.
3. Set up a local Python environment and install the declared dependencies (see README), then fetch/verify licensed Swiss ephemeris files into a protected local path.
4. Run unit tests and the planned golden-chart validation before touching the staging integration.
5. Submit scoped PRs rather than pushing to `main`; include evidence, upstream attribution and rollback notes.

## ChatGPT or other GitHub-connected agents
- Search organization owner `sabpuja` for `Sabpuja-Kundali-Engine`; use the exact repository path rather than relying on code-search indexing.
- Read this repo's `AGENTS.md` and `machine/capabilities.json` first.
- For current cross-org ownership, consult `sabpuja/Progress-Memory/ROUTER.md`, `REPOSITORIES.md`, `machine/repos.json`, then `sabpuja/core/docs/architecture/repo-map.md` once their registration PRs are merged.
- Authentication to GitHub **does not** imply Shopify, VPS or customer-profile access. Ask for separate authorized actions and least-privilege scopes.
- Agents may assist with calculation code and tests. Do not publish unverified chart outputs as accurate and do not expose personalized birth input in issues, commits, PRs or logs.

## Claude lead-developer handoff (CURRENT - permissions NOT CONFIGURED)
1. Read `AGENTS.md`, `docs/project-governance.md`, `docs/claude-builder-brief-001.md`, `docs/qa-review-template.md` and `machine/project-roles.json`.
2. Owner/operator may provide separate repo-scoped Claude Code GitHub credentials or a controlled local clone. Public readability of this repo is not write authorization. Never share credentials with ChatGPT or commit them.
3. Begin with an **audit of draft foundation PR #1** and send exact SHA/test evidence to ChatGPT for independent review. Do not create a duplicate foundation, change Shopify or launch a service.
4. For every later code/function change: approved work package -> Claude draft PR -> ChatGPT QA -> remediation loop -> owner merge approval. Separate authorization before VPS/staging/public deployment.
5. Claude is not an autonomous always-on agent in this project. Do not create a Hermes Kundali profile, scheduled jobs or GitHub Actions for the handoff.

## Optional future agents (NOT REQUESTED)
There is no Hermes Kundali profile or autonomous worker. Existing `sabpuja/Automation` remains the cross-repo owner for orchestration if the human owner requests it in a later phase. Do not provision new agent credentials or runners now.

## Access matrix
| Actor | Repo read | Repo write | VPS / Shopify |
|---|---|---|---|
| Public visitors | Public source only | None | None |
| Human maintainers | Via GitHub | Reviewed PRs with authorized role | Separate approval |
| ChatGPT GitHub connector | Accessible repository data within granted permission | Reviewed branches/PRs if connector authorized | Separate connector authorization |
| Claude / Claude Code (not yet authorized) | Public read or approved controlled clone | Draft PR only after separately granted access | No VPS / Shopify access without owner approval |
| Customer | No source authentication needed | None | Future published storefront, if approved |

## Verification gates
- Check the exact repo exists and manifest is readable.
- Confirm code and compliance have been reviewed/merged.
- Validate GitHub installation scope and operator secrets out of band.
- Recheck canonical Shopify staging theme role prior to integration.
- Confirm there are still **no GitHub Actions, scheduled jobs, active API endpoint or auto deployment** from this repo.

Never state `wired to Hermes`, `production deployed`, or `agent can access VPS` merely because this repo is registered.
