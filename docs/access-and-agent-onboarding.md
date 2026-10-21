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

## Hermes / Hostinger VPS integration (NOT CONFIGURED)
1. Add this repo to the existing Hermes/Automation source registry **after the org registration PRs are merged**. Keep current social/blog profiles untouched.
2. Grant a repo-scoped, short-lived, read-only GitHub installation/token for source retrieval if needed; require distinct explicitly approved write permission for PR creation. Do not put tokens in Git.
3. Use a pinned reviewed commit with a separately verified source/data manifest. Deploy only through an approved operator on Hostinger, not GitHub Actions.
4. Run the tool inside an isolated container/VM; mount locally verified Swiss ephemeris data read-only. Block outbound astrology API calls. Protect birth inputs, disable request-body logging, and expose no public HTTP listener until security signoff.
5. Record read-back proof: installed source SHA, local test report, datasource SHA, access check, and deployment approval. Do not mark runtime active until verified.

## Access matrix
| Actor | Repo read | Repo write | VPS / Shopify |
|---|---|---|---|
| Public visitors | Public source only | None | None |
| Human maintainers | Via GitHub | Reviewed PRs with authorized role | Separate approval |
| ChatGPT GitHub connector | Accessible repository data within granted permission | Reviewed branches/PRs if connector authorized | Separate connector authorization |
| Hermes Kundali worker (planned) | Read-only install/checkout after onboarding | None by default | Restricted approved runtime only |
| Customer | No source authentication needed | None | Future published storefront, if approved |

## Verification gates
- Check the exact repo exists and manifest is readable.
- Confirm code and compliance have been reviewed/merged.
- Validate GitHub installation scope and operator secrets out of band.
- Recheck canonical Shopify staging theme role prior to integration.
- Confirm there are still **no GitHub Actions, scheduled jobs, active API endpoint or auto deployment** from this repo.

Never state `wired to Hermes`, `production deployed`, or `agent can access VPS` merely because this repo is registered.
