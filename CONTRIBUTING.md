# Contributions

1. Create a small descriptive feature branch; never commit customer birth data, token material, private reports or ephemeris binary blobs.
2. Read AGENTS.md and core GitHub safety policy. GitHub Actions/workflows are prohibited without explicit human approval; tests are local/approved VPS only.
3. Include an issue/requirement reference; document algorithm, ayanamsa, nodes, house system, data revision and licensing provenance.
4. Run `python -m unittest discover -s tests -v`. For numeric changes attach independent golden-chart comparisons with tolerances and source details.
5. Open a PR with scope, validation evidence, privacy/security impact, AGPL impact, rollback considerations and cross-repo references.
6. Obtain independent review. Changes to numerical conventions and public interfaces must not self-approve.
7. Deployment requires a distinct approved change, privacy checks, source-offer compliance and staging verification.

## Developer and QA handoff
- Claude / Claude Code is implementer, ChatGPT is independent PM/QA reviewer, and the Sabpuja human owner is final approver.
- Before beginning work read [project governance](docs/project-governance.md), [first Claude brief](docs/claude-builder-brief-001.md), and [QA evidence template](docs/qa-review-template.md).
- All code, function and interface changes go through a scoped task and draft PR. Share the PR with ChatGPT for a documented PASS / CHANGES REQUESTED / BLOCKED review. Claude must not mark its own work ready for release.
- No merge or deploy merely because ChatGPT QA says PASS; the owner approves those separately.
