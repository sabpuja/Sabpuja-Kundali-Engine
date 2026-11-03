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

**Current truth (2026-11-03, integration candidate KUN-INT-CAND-001):** This text describes the isolated branch `integration/kun-int-001`. That branch is **not** `main`, is **not** a release and is **not** deployed. It joins `main` `25cfde4` with the PR #68 head `b1bca79` for independent integration QA only. The engine began as [foundation PR #1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1), which **remains on its PM/QA HOLD** ([6323581875](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1#issuecomment-6323581875), [C7 Option A 6393656493](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1#issuecomment-6393656493)). Its historical commits appear here by ancestry for QA only. The HOLD can be released only by a later explicit owner decision (D-6) naming an independently QA'd candidate SHA. [Claude audit issue #2](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/2) remains open. **Production: NO-GO.**

**Scientific decision status.** The canonical register is [docs/DECISIONS.md](docs/DECISIONS.md). Status follows the register's two-step rule: a pre-merge owner selection becomes canonical only through an owner-authorized merge plus a post-merge adoption receipt. Earlier "PENDING" wording elsewhere in the repository is historical proposal text and does not override those receipts.
- **OWNER APPROVED / CANONICAL:** SCI-01a to SCI-01h, SCI-02 (engineering baseline), SCI-03 and REL-01 (adoption merge `5b71408`, 2026-10-24); SCI-02 C2, **chart schema `0.3.0`** with **calculation metadata `sabpuja-calculation-metadata/3`** retained (2026-10-26; PR #43).
- **SCI-04, SCI-05, SCI-06** (test-only LAGNA-F tolerance, scope extension of the unchanged Swiss tolerances to the gold matrix, B-6 near-boundary disclosure rule): canonical at their recorded scopes through the [PR #64 post-merge adoption receipt](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/64#issuecomment-6598563378) (merge `de721d6`). The register block that reads "CANONICAL ADOPTION PENDING" is the frozen pre-merge snapshot. No customer-facing English or Hindi B-6 wording is approved.
- **Panchanga M1 method selections** (KUN-PAN-M1-DEC-001: D01-A, D02-M1, D07-A, D08-A, D09-A-M1, D10-A, D12-A, D13-A, D14-A-M1, D15-a-R, D15-b-R, D16-M1-INDEX, D18-A, D20-M1-SCOPED): canonical for the M1 birth-instant scope only through the [PR #65 post-merge adoption receipt](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/65#issuecomment-6600051638) (merge `25cfde4`). PENDING fields in the merged decision packet are frozen pre-merge text.
- The PRD and Development Roadmap carry their own status headers (1.1-proposed rebaseline drafts). DATA-01, LEG-01 and the other public-MVP gates remain open.

**Runtime direction:** Self-hosted Swiss Ephemeris + Sabpuja's Vedic algorithms under AGPL-3.0, with no third-party astrology API. Review licensing, local ephemeris rights, security and accuracy before network use.

All Kundali project documentation lives in this repository. Claude setup and Kundali documentation changes belong here. Claude instructions do not automatically connect Claude Projects or authorize a build.

**Status: Unreleased engine on an isolated integration candidate awaiting independent QA. NOT production-ready, NOT merged into `main`, NOT a public or client release, and NOT connected to Shopify. Independent astronomical accuracy is not certified. This candidate is not a bilingual MVP.**

Sabpuja-owned, self-hosted Vedic Kundali calculations based on the locally installed Swiss Ephemeris library. There are **no external astrology API calls**.

## Start here
- Humans: [architecture](docs/architecture.md), [roadmap](docs/DEVELOPMENT-ROADMAP.md) (canonical; [docs/roadmap.md](docs/roadmap.md) is the superseded preliminary outline), [accuracy gates](docs/accuracy-plan.md), [licensing](docs/licensing.md).
- Agents: [AGENTS.md](AGENTS.md), [machine/capabilities.json](machine/capabilities.json), [access/onboarding](docs/access-and-agent-onboarding.md), [API/data contract](docs/api-contract.md).
- Canonical org discovery: `sabpuja/core/docs/architecture/repo-map.md` and `sabpuja/Progress-Memory/ROUTER.md` + `machine/repos.json`.

## Project ownership and delivery
**Owner:** Sabpuja human project owner. **PM and independent QA:** ChatGPT. **Lead implementer:** Claude / Claude Code.

All material code, functions, interfaces and PRs are assigned and reviewed through ChatGPT. Claude implements and supplies reproducible test evidence; owner approval is required for merge, staging deployment and release. See [project governance](docs/project-governance.md), [Claude's first task](docs/claude-builder-brief-001.md), [QA template](docs/qa-review-template.md), and [machine role registry](machine/project-roles.json). Claude works only within milestones the owner explicitly authorizes; each authorization is recorded on [PR #20](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/20).

The engine's history is draft PR #1 (foundation, HOLD), the KUN-03 stack (PRs #23 to #35, joined with `main` at Gate 1, then PR #36), Gate 3B to 3E (PRs #39 to #42), the private preview and premium report stack (PRs #44 to #46 and #53 to #58), the gold harness (PR #62) and Panchanga M1 (PR #68). Each was independently QA'd at its exact head; those receipts do not substitute for candidate-level QA. Do not create a duplicate engine, and do not merge into `main` without separate owner approval.

## Implemented on this candidate (independently QA'd at the source PR heads; unmerged, unreleased)
- Pure Vedic helpers for Rashi, Nakshatra/Pada and Navamsa (D9) sign mapping.
- Local Swiss Ephemeris adapter per SCI-01a to SCI-01h: Lahiri sidereal mode, Sun/Moon/classical grahas, mean Rahu and exactly opposite Ketu, sidereal Lagna via Swiss whole-sign (`b"W"`) houses.
- D1 and D9 charts with whole-sign houses, **chart schema `0.3.0`**, calculation metadata **`/3`** (PR #42; C7 reviewer-executed REL-01 engineering PASS, review 5647737922).
- A private, stdin-driven JSON CLI requiring an **explicit UTC-offset birth datetime, IANA timezone, latitude and longitude**. Fail-closed checks for missing or mismatched ephemeris files and Moshier fallback.
- KUN-03 input and time hardening: pinned `tzdata` 2026.5 with a TZif SHA-256 manifest, the -66.0 to +66.0 latitude band, the 1900-2100 local civil date window, ordered refusal codes, a fail-closed pre-1970 historical-clock gate, location-based timezone identifiers, per-request Swiss state and Delta T reset, private Swiss error codes and calculation provenance metadata. See [docs/api-contract.md](docs/api-contract.md).
- Gate 3C engine hardening: typed `SWISS_*` runtime faults, exact Swiss library and binding version pins, typed CLI errors and a fail-closed start-up preflight. See [docs/engine-readiness.md](docs/engine-readiness.md).
- Owner-only prototype and gateway ([prototype/](prototype/README.md), [preview/](preview/README.md)): authenticated form over a fixed 12-place list, North Indian D1/D9 charts, readiness checks and typed server errors, and failed-login user names kept out of gateway logs (PR #56).
- **Ten-page saffron premium Foundations PDF** served in memory from `/api/report` (PRs #54 and #55), with the **optional Full Name** field, including Devanagari names (PR #58). See [report/phase1/](report/phase1/README.md).
- **Independent D1/D9 gold-reference harness** (PR #62, `tests/sci_gold/`). The frozen run exits 2 with **49 PASS, 18 QUALIFIED and 1 BOUNDARY-INDETERMINATE**. This is a qualified engineering result, **not** a clean scientific certification. Independent astronomy (JPL/INPOP) remains BLOCKED (REL-01 optional), and Swiss-on-Swiss conformance is not independent astronomical validation.
- **Panchanga M1 birth-instant engine** (PR #68, `src/sabpuja_kundali/panchanga/`, `sabpuja-panchanga/1`): Tithi, Paksha, Karana index, Yoga index, chart-identical Nakshatra/Pada and bounded transition instants. **Independently engineering-QA-passed** (review 5752132632), **machine output only and not customer-facing**. No Panchanga names, Hindi copy, PDF insertion or public API is approved.

## Owner-only preview
The restricted owner-only HTTPS preview currently runs **PR #58 `fde3ec6`** ([deployment receipt](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/58#issuecomment-6544319453)). PRs #62 and #68 and this candidate are **not** deployed. Merging code never deploys it; every preview change needs a separate owner authorization and exact-SHA receipt.

## Not implemented or not approved
Public HTTP service or client access, a full offline city selector, verified historical clocks before 1970, dashas, Yogas/Doshas, personalized interpretations, customer profiles, Shopify integration and staging/live rollout. The **English/Hindi interface and the Hindi Kundali PDF** (draft PRs #59 to #61) are **outside this candidate** and planned for a subsequent bilingual integration milestone. Customer-facing Panchanga is not approved.

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
**AGPL-3.0-only** for this project; see [LICENSE](LICENSE), [upstream notices](THIRD_PARTY_NOTICES.md), the bundled OFL font licences under `prototype/kundali_prototype/static/fonts/`, and the [compliance checklist](docs/licensing.md). **LEG-01 remains pending**: this is not legal clearance for public network service or commercial launch. All combined-work, network source-offer and deployment obligations must be reviewed before public service activation.

**Safety:** No GitHub Actions, no auto-deploy, no customer PII in this public repository, and no claim of production accuracy until reference tests pass.
