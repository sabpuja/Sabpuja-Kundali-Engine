# WP-B1 Panchanga research package

**PROPOSED — NOT CANONICAL — OWNER SCIENTIFIC-METHOD APPROVAL PENDING. Production: NO-GO.**

WP-B1 prepares the Panchanga (proposed KUN-A01) method decision. It contains documentation, provenance records and non-executable fixtures only. It contains no implementation code, test harness, schema change or change to any canonical file.

## Contents

| Path | Purpose |
|---|---|
| [../../docs/science/SCI-PAN-01-PANCHANGA-METHOD-DECISION-PROPOSAL.md](../../docs/science/SCI-PAN-01-PANCHANGA-METHOD-DECISION-PROPOSAL.md) | Method proposal, decision matrix (PAN-D01 to PAN-D20), uncertainties, owner checklist |
| [../../docs/science/WP-B2-PANCHANGA-ENGINEERING-HANDOFF-DRAFT.md](../../docs/science/WP-B2-PANCHANGA-ENGINEERING-HANDOFF-DRAFT.md) | Draft engineering handoff for a future, separately authorized WP-B2 |
| [SOURCE-REGISTER.md](SOURCE-REGISTER.md) | Every source with publisher, edition, method, precision, rights and role; sources that could not be retrieved |
| [reference-fixtures/](reference-fixtures/README.md) | 64 direct published references, 8 derived cases, 16 boundary specifications, IMD capture template |

## QA receipt (pre-PR)

Run on 2026-10-28 in the Claude cloud environment, on branch `docs/claude-wp-b1-panchanga-method-rfc`.

| # | Check | Result |
|---|---|---|
| 1 | Base SHA: `git ls-remote origin refs/heads/main` and local `HEAD` before branching | `5395d2bc33847d1363e6d838f6109bad552221e3`, matching the expected baseline. The head SHA is reported in the PR description, because a commit cannot contain its own SHA |
| 2 | Changed paths restricted to `docs/science/` and `research/panchanga/` (documents, provenance, JSON data) | PASS: 10 added files, 0 modified, 0 deleted (`git diff --name-status`) |
| 3 | Citations and links: every relative Markdown link and anchor resolves; every `SRC-…` id used in a fixture exists in the register | PASS (scratch checker, not committed) |
| 4 | Fixture structure: all 5 JSON files parse; 88 unique case/spec ids; every case has a status | PASS |
| 5 | Expected values supported by sources: phase list mutually consistent between USNO and NASA (42 identical, 8 differ by exactly +1 min); 10 `closestphase` values from separate USNO rise/set responses reproduce the phase list after their UTC offsets; counts 12 New, 12 First Quarter, 13 Full, 13 Last Quarter | PASS |
| 6 | Negative cases and alternatives: 2 published negative sunrise cases; 16 boundary/refusal specifications; 20 decisions with alternatives and consequences | Present |
| 7 | `git diff --check` | PASS (no output) |
| 8 | Markdown tables: column counts consistent in every table | PASS |
| 9 | Secrets, personal birth data, bulk source copying: no credentials; birth instants are synthetic; only individual published times are recorded | PASS (manual review and grep) |
| 10 | `docs/DECISIONS.md`, `docs/PRD.md`, `docs/DEVELOPMENT-ROADMAP.md`, `docs/ACCEPTANCE-MATRIX.md` and every engine file unchanged | PASS (`git diff --stat` against the base lists only the 10 new files) |

The scratch scripts used to transcribe and check the data are deliberately **not** committed, because WP-B1 must contain no executable code. Their checks are listed above so QA can repeat them independently.

## Known limits of this package

- The IMD Rashtriya Panchang could not be retrieved (network policy refusal and robots disallow). As a result there are no IMD rows, no Nakshatra or Yoga ending references, and no verified Hindu-convention sunrise reference.
- Values were read through an automated page-reading tool. Internal cross-checks pass, but QA should re-read rows from the live sources.
- Karana names are not adopted.
