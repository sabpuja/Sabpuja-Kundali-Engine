# Developer PR evidence and independent QA template

Every change with executable code, calculation behavior, external interface, dependency, or user-facing report must be reviewed by ChatGPT PM/QA before owner approval.

## Claude PR submission
- Work package / issue:
- Baseline commit SHA / PR branch:
- Head commit SHA / diff URL:
- Purpose and **explicit out-of-scope**:
- Changed files, public functions, mathematical contracts:
- Before/after behavior and migration notes:
- Numerical conventions (ayanamsa, node, houses, epochs, data revision):
- Third-party dependency version, origin, license and changes:
- Test environment and dataset SHA-256 (no private paths/credentials):
- Exact local/approved-VPS commands, pass/fail counts and **raw failures**:
- Golden-chart independent provenance, inputs, output comparisons, numeric tolerance:
- Privacy, security, logs, network calls, abuse/rate limits:
- Compliance and source-offer impact (AGPL, upstream notices):
- Shopify/staging/UI impact (if applicable), screens, accessibility and Hindi/English:
- Rollback path, known limitations and risks:
- Open questions / explicitly unverified claims:

## ChatGPT PM/QA review checklist
### G0. Scope and governance
- [ ] Authorized numbered task; smallest reviewable diff; no duplicate implementations.
- [ ] No GitHub Actions, unintended write/deploy, secrets or customer PII.
- [ ] Baseline/head SHAs and provenance are clear; no self-approval.
### G1. Code quality
- [ ] Static review for numerical correctness, input validation, errors, defensive state, dependencies.
- [ ] Unit/contract tests executed on known exact commit; negative and boundary cases covered.
- [ ] Failure paths are non-leaky; no silent fallback or invented values.
### G2. Independent astronomical verification
- [ ] Pin code/library/data/flags; methodology matches output metadata.
- [ ] Independent reference inputs + author/source + tolerances + differences supplied; no circular tests.
- [ ] Test special timezones, DST folds/gaps, dates and geographic/polar boundaries.
- [ ] Sidereal Lagna, nodes, houses, D1, D9, Nakshatra/Pada validated at appropriate stages.
- [ ] If independent comparison missing, **BLOCK accuracy** regardless of unit-test success.
### G3. Compliance, privacy and security
- [ ] Verify AGPL combined-work boundary, Swiss and binding notices, dataset rights.
- [ ] No sensitive request-body logging, raw birth records in repos or telemetry.
- [ ] API abuse controls/auth/storage scope when server introduced.
### G4. Product/UI and launch (only relevant milestones)
- [ ] Brand tokens/approved logo only; fluid/mobile/accessibility; localization.
- [ ] Staging theme identity freshly verified before any writes; no live theme writes.
- [ ] Deployment separately approved, pinned source and data, rollback tested.
### G5. Decision
- [ ] PM records PASS / CHANGES REQUESTED / BLOCKED, evidence, defects and exact SHA.
- [ ] Owner decides merge, staging, public launch separately.
- [ ] Progress-Memory updated **only after** actual verified checkpoint.

## Review decision record
- PR / reviewed SHA:
- Verdict:
- Evidence independently reproduced:
- Defects (IDs, severity, expected fix):
- Unverified risks and stop conditions:
- PM recommendation:
- Owner approval reference (if given):
- Merged / deployed / released: only with verified evidence, otherwise **NO**.
