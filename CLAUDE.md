# Claude / Claude Code - Sabpuja Kundali Engine

**Project role:** Lead implementer. **Human:** Project Owner. **ChatGPT:** Project Manager and independent QA reviewer.

## Canonical single-repository read order (mandatory)
1. `README.md` and `docs/README.md` - entrypoint and current project state.
2. `docs/PRD.md` - requirements and MVP/P1 boundaries (KUN-F01 to KUN-F16).
3. `docs/DECISIONS.md` - owner-directed choices and **pending decisions**. Never infer approval from a proposed default.
4. `docs/DEVELOPMENT-ROADMAP.md` - dependencies, CLAUDE tasks, deliverables and gates.
5. `docs/ACCEPTANCE-MATRIX.md` - QA-001 to QA-030 and verifiable acceptance.
6. `machine/project-plan.json` - project documentation locations/status (read; do not treat planned as implemented).
7. For the foundation audit, read draft PR #1 **as its own branch**, `feat/initial-kundali-foundation-20261021`, particularly its `AGENTS.md`, `docs/project-governance.md`, `docs/accuracy-plan.md`, `docs/licensing.md`, `docs/qa-review-template.md` and implementation/test files.

**Branch caveat:** The detailed PRD/roadmap were merged to `main` in PR #3. The foundational engine, `AGENTS.md`, and governance documents remain in *unmerged draft* PR #1; those paths will not necessarily be present on `main` until that PR passes independent review and merges. Do not replace the merged PRD/README with an older copy from the foundation branch. If working across branches, compare explicitly or use separate worktrees. Flag conflicts to ChatGPT.

## Authority and precedence
- Product and domain requirements: `docs/PRD.md`. Current accepted decisions: `docs/DECISIONS.md`; entries marked PENDING are **unresolved**.
- Scope, task dependencies: `docs/DEVELOPMENT-ROADMAP.md`. Acceptance evidence: `docs/ACCEPTANCE-MATRIX.md`.
- Source code and implementation details: this repository, with upstream Swiss Ephemeris documentation for the astronomical API. Conflicts with requirements/decisions go to ChatGPT and the owner.
- All **Kundali-specific** PRD, milestones, decisions, QA, architecture, test fixtures and delivery records must remain here; **do not edit `sabpuja/core` or another repository** as part of Kundali planning. Later Shopify code, when separately authorized, belongs in the Shopify implementation repo; requirements remain here.

## Required workflow
- CLAUDE-001 / [issue #2](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/2) is the **only existing developer assignment**. Audit foundation [draft PR #1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1) first; reproduce tests and review numerical methods. No rewrite or feature expansion.
- Before any further development: owner reviews PRD/decisions, ChatGPT provides a *numbered, bounded task* with KUN-F## and QA-### links, and required access is explicitly authorized.
- For implementation: create a scoped branch, run local or approved Hostinger tests on exact SHA, open a draft PR and supply raw test outputs, source/data hashes, numerical reference comparisons, changed functions, risks and rollback. ChatGPT returns PASS / CHANGES REQUESTED / BLOCKED.
- Claude fixes blocking defects and resubmits updated evidence. ChatGPT's QA pass is not a claim of production readiness. Owner retains final authority for substantial scope changes and all deployment/live release decisions. No self-merge, self-approval or direct `main` push.
- If authorizations, licenses, ephemeris data, reference charts or access are missing, report the blocker; do not fabricate them. Merely creating a Claude Project does **not** connect GitHub write/VPS permissions.

## Hard technical and operational constraints
- Self-hosted Swiss Ephemeris, pinned local ephemeris files, AGPL compliance, method metadata and independent golden chart references. No third-party astrology API at runtime; never invent planetary positions or accuracy results.
- Lahiri, mean node and whole-sign house choices in older foundation code are **proposed** until explicitly accepted in `docs/DECISIONS.md`; flag method ambiguity before changing results.
- Never substitute a guessed birth time/place/timezone; never silently fall back to Moshier or a lower-accuracy ephemeris.
- No real customer birth data or credentials in PRs, code, logs, fixtures, telemetry or issue descriptions. No public API before independent security/privacy/license review.
- No GitHub Actions, unattended workers, Hermes Kundali profile, external astrology API, Shopify live changes or deployment without separate authorization.
- No invented QA/CI statuses, no claim that tests were executed unless exact reproducible evidence exists.

## Immediate response format
Before any edits, provide: (1) exact repo/branch/commit, (2) read documents and observed conflicts, (3) CLAUDE-001 audit steps and test environment, (4) critical blockers, and (5) what evidence you will return to ChatGPT for independent QA.
