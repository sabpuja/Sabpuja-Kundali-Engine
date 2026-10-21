# Contributions

1. Create a small descriptive feature branch; never commit customer birth data, token material, private reports or ephemeris binary blobs.
2. Read AGENTS.md and core GitHub safety policy. GitHub Actions/workflows are prohibited without explicit human approval; tests are local/approved VPS only.
3. Include an issue/requirement reference; document algorithm, ayanamsa, nodes, house system, data revision and licensing provenance.
4. Run `python -m unittest discover -s tests -v`. For numeric changes attach independent golden-chart comparisons with tolerances and source details.
5. Open a PR with scope, validation evidence, privacy/security impact, AGPL impact, rollback considerations and cross-repo references.
6. Obtain independent review. Changes to numerical conventions and public interfaces must not self-approve.
7. Deployment requires a distinct approved change, privacy checks, source-offer compliance and staging verification.
