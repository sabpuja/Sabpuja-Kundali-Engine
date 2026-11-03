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

**Current truth (2026-10-24):** Product documents remain owner-review drafts. The engine began as [foundation PR #1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1), which is still unmerged and under its PM/QA hold. It was hardened through PRs #6, #8 and #10 (merged into the foundation branch) and the KUN-03 draft stack, PRs #23 to #35, each engineering-QA-passed by ChatGPT at its exact head. The branch `integration/kun03-gate1` joins `main` with the PR #35 head `5a0ac2f` for integration QA only: it is not `main`, not a release and not deployed. [Claude audit issue #2](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/2) remains open. Every decision-register row except SCI-01b and SCI-01c is still PENDING. No independent golden-chart verification, numerical accuracy signoff, staging connection or production deployment exists.

**Runtime direction:** Self-hosted Swiss Ephemeris + Sabpuja's Vedic algorithms under AGPL-3.0, with no third-party astrology API. Review licensing, local ephemeris rights, security and accuracy before network use.

All Kundali project documentation lives in this repository. Claude setup and Kundali documentation changes belong here. Claude instructions do not automatically connect Claude Projects or authorize a build.

**Status: Unreleased engine under integration QA. NOT production-ready, NOT deployed, and NOT connected to Shopify. Independent astronomical accuracy is not certified.**

Sabpuja-owned, self-hosted Vedic Kundali calculations based on the locally installed Swiss Ephemeris library. There are **no external astrology API calls**.

## Start here
- Humans: [architecture](docs/architecture.md), [roadmap](docs/DEVELOPMENT-ROADMAP.md) (canonical; [docs/roadmap.md](docs/roadmap.md) is the superseded preliminary outline), [accuracy gates](docs/accuracy-plan.md), [licensing](docs/licensing.md).
- Agents: [AGENTS.md](AGENTS.md), [machine/capabilities.json](machine/capabilities.json), [access/onboarding](docs/access-and-agent-onboarding.md), [API/data contract](docs/api-contract.md).
- Canonical org discovery: `sabpuja/core/docs/architecture/repo-map.md` and `sabpuja/Progress-Memory/ROUTER.md` + `machine/repos.json`.

## Project ownership and delivery
**Owner:** Sabpuja human project owner. **PM and independent QA:** ChatGPT. **Lead implementer:** Claude / Claude Code.

All material code, functions, interfaces and PRs are assigned and reviewed through ChatGPT. Claude implements and supplies reproducible test evidence; owner approval is required for merge, staging deployment and release. See [project governance](docs/project-governance.md), [Claude's first task](docs/claude-builder-brief-001.md), [QA template](docs/qa-review-template.md), and [machine role registry](machine/project-roles.json). Claude works only within milestones the owner explicitly authorizes; each authorization is recorded on [PR #20](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/20).

The engine's history is draft PR #1 (foundation) followed by the KUN-03 draft stack, PRs #23 to #35. Swiss-on-Swiss integration conformance against the official `swetest` passes; that is not independent astronomical validation, and independent golden-chart verification is still outstanding. Do not create a duplicate engine, and do not merge into `main` without separate owner approval.

## Implemented (engineering-QA-passed drafts; unmerged, unreleased, methods pending owner adoption)
- Pure Vedic helpers for Rashi, Nakshatra/Pada and Navamsa (D9) sign mapping, with unit tests run in every recorded QA pass.
- Local Swiss Ephemeris adapter: explicit Lahiri sidereal mode, Sun/Moon/classical grahas, mean Rahu and opposite Ketu, sidereal ascendant and whole-sign houses.
- A private, stdin-driven JSON CLI, requiring an **explicit UTC-offset birth datetime, IANA timezone, latitude and longitude**.
- Fail-closed checks for missing ephemeris files and accidental Moshier fallback.
- KUN-03 input and time hardening: pinned `tzdata` 2026.5 with a TZif SHA-256 manifest, the -66.0 to +66.0 latitude band, Lagna via Swiss whole-sign houses, the 1900-2100 local civil date window, ordered refusal codes, a fail-closed pre-1970 historical-clock gate, location-based timezone identifiers, per-request Swiss state and Delta T reset, private Swiss error codes and calculation provenance metadata. See [docs/api-contract.md](docs/api-contract.md).
- Gate 3C engine hardening (PKG-2, draft): typed `SWISS_*` runtime faults (missing binding, Moshier fallback), exact run-time Swiss library and binding version pins, a CLI boundary that reports only typed engine errors, and a fail-closed start-up preflight for a future service. See [docs/engine-readiness.md](docs/engine-readiness.md).

## Not implemented
Public HTTP service, offline city selector, verified historical clocks before 1970, PDF, dashas, Yogas/Doshas, personalized interpretations, customer profiles, Shopify integration and staging/live rollout. The numerics have **not yet passed independent golden-chart verification**.

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
- Kundali product requirements, roadmap, scientific decisions and QA documents: **this repository** (`docs/`; DEC-004).
- Organization-wide policy and repository map: `sabpuja/core`.
- Current checkpoints: `sabpuja/Progress-Memory`.

## License
**AGPL-3.0-only** for this project; see [LICENSE](LICENSE), [upstream notices](THIRD_PARTY_NOTICES.md) and [compliance checklist](docs/licensing.md). All combined-work, network source-offer and deployment obligations must be reviewed before public service activation.

**Safety:** No GitHub Actions, no auto-deploy, no customer PII in this public repository, and no claim of production accuracy until reference tests pass.
