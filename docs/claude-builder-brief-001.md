# CLAUDE-001 | Verify and harden the existing Kundali foundation

**Status:** Ready for developer intake, NOT executed.
**Implementer:** Claude / Claude Code.
**PM and independent QA:** ChatGPT.
**Approver:** Sabpuja project owner.
**Target:** `sabpuja/Sabpuja-Kundali-Engine`, draft PR #1, branch `feat/initial-kundali-foundation-20261021`.
**Scope:** audit and evidence first; small remediation PR only when PM has triaged findings.

## Read before touching code
1. `README.md`, `AGENTS.md`, `docs/project-governance.md`, `docs/qa-review-template.md`.
2. `docs/architecture.md`, `docs/accuracy-plan.md`, `docs/licensing.md`, `docs/api-contract.md`.
3. `src/sabpuja_kundali/{engine,rules,cli}.py`, `tests/`, `pyproject.toml`, `data/ephemeris/README.md`.
4. Canonical GitHub safety policy in `sabpuja/core/docs/policies/GITHUB-SAFETY-GUARDRAILS.md`.

## Work required
A. **Baseline inventory**: identify exact upstream Swiss Ephemeris package/binding versions, flags, local dataset provenance and SHA-256, Python/runtime version, source branch/commit and all code paths; flag unresolved upstream-data licensing. Do not redistribute ephemeris data without verifying its rights.
B. **Reproduce tests**: clean Python environment, install pinned dependencies, run `python -m unittest discover -s tests -v`, capture output and failures, validate the CLI with the synthetic example only, and explicitly distinguish mock/contract tests from real astronomy tests.
C. **Inspect calculations**: independently review birth timestamp/UTC-offset/timezone handling, sidereal Lahiri mode, solar/lunar planets, mean Rahu/Ketu, house/ascendant calculation, D1/Rashi/Nakshatra/Pada/D9 mapping and signs/houses on boundaries. Check mutable Swiss global-state risks, negative longitude, DST folds/gaps, float normalization, ephemeris flags, missing data and fallback detection.
D. **Propose independent golden fixtures**: identify reference chart provenance, convention and precision, reproducible input, numeric tolerances **before** comparing. If independent references cannot be verified, mark this gate BLOCKED rather than declaring accuracy.
E. **Risk review**: AGPL source offer and dependency notices, privacy, sensitive logging, input validation, test reproducibility, and no network astrology calls.

## Required report
Submit a concise Markdown report (or comment on the existing draft PR) containing:
- exact baseline and tested commit SHAs, environment, installed dependency versions and dataset checksums;
- test commands + unedited PASS/FAIL results and diagnostics;
- numbered defect list: critical/high/medium/low with file/function/line and reproduction steps;
- numerical discrepancies against genuinely independent, cited reference values, OR explicit `NOT VALIDATED`;
- proposed smallest remediation sequence with regressions/tests per fix;
- statement of unchanged scope: no Shopify, VPS, app proxy, customer data or live operations.

## Gate / deliverable
**First response is an audit and reproducible evidence, not a full rewrite or production-ready claim.** PM reviews the report, defines narrow remediation issues/PRs, then Claude implements the highest-priority fix. Preserve draft PR #1; do not merge or rewrite its history.

## Out of scope
New REST API, Django/FastAPI server, customer storage, city search, PDF, dasha, yoga/dosha, paid features, Hermes agent profile, GitHub Actions, Shopify edits, and production deployment.

## Human handoff prompt
"Work as the Claude lead developer for sabpuja/Sabpuja-Kundali-Engine. First read AGENTS.md and docs/project-governance.md plus CLAUDE-001. Audit draft PR #1 using local tests and independently sourced reference methods. Report exact tested SHAs, failures and proposed fixes to ChatGPT (PM/QA). Do not merge, deploy, create GitHub Actions or change scope. Treat all astronomical accuracy as unverified until independently validated."
