# Sabpuja Kundali Engine

**Official project hub:** [docs/README.md](docs/README.md)

- [Product Requirements (owner review draft)](docs/PRD.md)
- [Detailed Development Roadmap](docs/DEVELOPMENT-ROADMAP.md)
- [Acceptance and QA Matrix](docs/ACCEPTANCE-MATRIX.md)
- [Owner Decision Register](docs/DECISIONS.md)
- [Machine-readable project plan](machine/project-plan.json)
- [Claude Code repo instructions](CLAUDE.md)
- [Claude Project Goal and Context - paste-ready](docs/CLAUDE-PROJECT-SETUP.md)

**Delivery model:** Sabpuja owner decides; ChatGPT manages scope and independently reviews all substantive code/functions; Claude builds on scoped branches and submits draft PRs.

**Current truth:** Product documents pending owner approval; [foundation PR #1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1) is unmerged and unaudited. [Claude audit issue #2](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/2) is ready for developer intake. No numerical accuracy signoff, staging connection or production deployment exists.

**Runtime direction:** Self-hosted Swiss Ephemeris + Sabpuja's Vedic algorithms under AGPL-3.0, with no third-party astrology API. Review licensing, local ephemeris rights, security and accuracy before network use.

All Kundali project documentation lives in this repository. Claude setup and Kundali documentation changes belong here. Claude instructions do not automatically connect Claude Projects or authorize a build.
**Status: Foundation implementation only. NOT production-ready, NOT deployed, and NOT connected to Shopify.**

Sabpuja-owned, self-hosted Vedic Kundali calculations based on the locally installed Swiss Ephemeris library. There are **no external astrology API calls**.

## Start here
- Humans: [architecture](docs/architecture.md), [roadmap](docs/roadmap.md), [accuracy gates](docs/accuracy-plan.md), [licensing](docs/licensing.md).
- Agents: [AGENTS.md](AGENTS.md), [machine/capabilities.json](machine/capabilities.json), [access/onboarding](docs/access-and-agent-onboarding.md), [API/data contract](docs/api-contract.md).
- Canonical org discovery: `sabpuja/core/docs/architecture/repo-map.md` and `sabpuja/Progress-Memory/ROUTER.md` + `machine/repos.json`.

## Project ownership and delivery
**Owner:** Sabpuja human project owner. **PM and independent QA:** ChatGPT. **Lead implementer:** Claude / Claude Code.

All material code, functions, interfaces and PRs are assigned and reviewed through ChatGPT. Claude implements and supplies reproducible test evidence; owner approval is required for merge, staging deployment and release. See [project governance](docs/project-governance.md), [Claude's first task](docs/claude-builder-brief-001.md), [QA template](docs/qa-review-template.md), and [machine role registry](machine/project-roles.json). Claude execution permissions are **not yet configured**.

Existing foundation is draft PR #1, which is awaiting independent test and numerical validation. Do not create a duplicate engine or merge until accepted.

## Implemented foundation
- Pure Vedic helpers for Rashi, Nakshatra/Pada and Navamsa (D9) sign mapping, with authored unit tests awaiting execution.
- Local Swiss Ephemeris adapter: explicit Lahiri sidereal mode, Sun/Moon/classical grahas, mean Rahu and opposite Ketu, sidereal ascendant and whole-sign houses.
- A private, stdin-driven JSON CLI, requiring an **explicit UTC-offset birth datetime, IANA timezone, latitude and longitude**.
- Fail-closed checks for missing ephemeris files and accidental Moshier fallback.

## Not implemented
Public HTTP service, offline city selector, PDF, dashas, Yogas/Doshas, personalized interpretations, customer profiles, Shopify integration and staging/live rollout. The numerics have **not yet passed independent golden-chart verification**.

## Developer quickstart
Python 3.11+ (3.13 supported by installed package), with local Python packaging tools:

```bash
python -m venv .venv
python -m pip install -e .
python -m unittest discover -s tests -v
# Download approved Swiss Ephemeris .se1 files locally (see data/ephemeris/README.md).
export SABPUJA_EPHE_PATH=/absolute/path/to/ephe
python -m sabpuja_kundali.cli < examples/birth-request.example.json
```

Windows PowerShell:
```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
$env:SABPUJA_EPHE_PATH = 'C:\absolute\path\to\ephe'
Get-Content .\examples\birth-request.example.json -Raw | .\.venv\Scripts\python.exe -m sabpuja_kundali.cli
```

The example has **synthetic birth details**. Do not commit real birth records.

## Boundaries
- Calculations, methodology, tests and future reports: **this repository**.
- Shopify UI and Component Lab: `sabpuja/theme` (staging only until approved).
- Brand assets: `sabpuja/design-system`.
- Agent orchestration: `sabpuja/Automation` / controlled Hostinger VPS.
- Product requirements and policy: `sabpuja/core`.
- Current checkpoints: `sabpuja/Progress-Memory`.

## License
**AGPL-3.0-only** for this project; see [LICENSE](LICENSE), [upstream notices](THIRD_PARTY_NOTICES.md) and [compliance checklist](docs/licensing.md). All combined-work, network source-offer and deployment obligations must be reviewed before public service activation.

**Safety:** No GitHub Actions, no auto-deploy, no customer PII in this public repository, and no claim of production accuracy until reference tests pass.
