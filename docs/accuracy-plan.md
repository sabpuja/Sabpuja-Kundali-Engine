# Accuracy and acceptance test plan

**Status: the engine is NOT astronomically validated.** No independent golden-chart comparison has been run. Do not claim accuracy until the golden suite below passes independent QA on an exact commit.

## Swiss-first MVP verification priority (owner approved 2026-10-22)

**Scope and truth labels.** Sabpuja will keep the established, **locally pinned Swiss Ephemeris** library and checksum-verified `.se1` files as its sole runtime astronomical calculator. For MVP engineering, **verify our integration with a separate official Swiss `swetest` CLI process, plus independent mathematical oracles for Kundali classifications**, rather than requiring JPL/INPOP/IAE procurement and multi-ephemeris comparisons upfront. This revises the *MVP sequencing*, not the numerical truth of Swiss Ephemeris or any calculation-method decision.

- **New high-priority assignment:** [KUN-01-SWISS-01 issue #16](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/16). Require exact Swiss executable/source version and hashes, identical sidereal flags and UT handling, identical pinned ephemeris dataset, synthetic chart grid, reportable per-body/circular differences, independently derived D1/D9/Nakshatra/Pada/house expectations, refusal-path tests, immutable run receipts and independent PM QA. No code/methodology change in the same ticket.
- **Honest evidence classification:** `SWISS-CONFORMANCE PASS` means *our Python adapter agrees with Swiss's separate CLI for the explicitly tested equivalent inputs and versions*. It is **NOT** an independent astronomical accuracy PASS: both use Swiss astronomical algorithms and may share systematic errors. Mathematical Jyotish rule tests are separately labelled `RULE-CONFORMANCE`; historical civil-time checks and IANA-rule agreement are not independent evidence that a city actually used that clock.
- **Separate runner:** the QA-approved dummy-only architecture in [PR #14](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/14) remains the independent-reference harness. **Never insert Swiss output into an independent reference class**, change the harness's `BLOCKED` demo or `UNREVIEWED` method manifest to PASS, or silently freeze any `tests/golden/config/tolerances.json` value. Implement Swiss CLI conformance in a separate, clearly named suite/report path.
- **Optional later scientific assurance:** [JPL/INPOP comparison issue #15](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/15) is **OPTIONAL / DEFERRED**, not a blocking prerequisite for a *Swiss-conformance* statement or for completing the MVP integration tests. Retain the full independent golden specification below for any later independent astronomical-certification claim or unresolved scientific discrepancy. No external reference result or numerical tolerance is invented or frozen by this change.
- **Unchanged product/release gates:** All method choices except owner-approved SCI-01b/c remain PENDING in canonical `main:docs/DECISIONS.md`; historical Indian clocks (RG-HIST), UT1/UTC/Delta T limitations, Swiss/AGPL licensing review, privacy, report/PDF correctness, performance, independent engineering QA and explicit owner release authorization remain required. This change does **not** authorize a PR merge, public release, or claims such as "independently certified astronomical accuracy".
- **No new external runtime services:** do not call NASA/JPL/INPOP, online `swetest` or any third-party astrology API to serve customer charts. Run the standalone Swiss reference tool only in controlled offline test environments.

### MVP evidence sequence

1. Keep the calculation source and pinned data unchanged while Claude implements issue #16 on a separate draft branch from the foundation development branch. Require exact-SHA reproduction, negative/failure receipts and independent QA.
2. Validate the current Swiss flags/mean-node behavior through the official standalone `swetest` binary where methods are comparable. If a CLI quantity is unavailable or cannot be matched, record `BLOCKED` rather than guess. Distinguish known near-boundary 8-decimal display effects from category defects.
3. Independently check mathematical Kundali rules, timezone conversion **as rule application** and refusal handling. Fix defects only through subsequent owner-approved scoped code PRs.
4. Complete still-pending scientific method decisions, historical-clock release gate and legal/security/product launch gates before any customer-facing validation/accuracy language or release.
5. Optionally run the deeper independent-source PG-1 to PG-5 and golden charts later, particularly if the product seeks external astronomical-accuracy certification.

The original independent-science plan remains a **separate higher-assurance track**. It is not deleted; its pre-gates still apply whenever we attempt to claim *independent* astronomical accuracy.

## Existing tests (self-consistency and contract only)
These run with `python -m unittest discover -s tests`. With `SABPUJA_TEST_EPHE_PATH` set to verified pinned data, 79 tests pass with 0 skipped at `d8193c6`. None of them compares the engine with an independent astronomical source.
- `tests/test_rules.py`, `tests/test_angular_boundaries.py` (with `tests/boundary_oracle.py`): Rashi, Nakshatra/Pada, Navamsa and whole-sign house rules at exact boundaries.
- `tests/test_engine_contract.py`, `tests/test_engine_boundaries.py`, `tests/test_input_and_polar.py`: input validation, timezone offset rejection, polar refusal, raw-value classification.
- `tests/test_ephemeris_manifest.py`, `tests/test_swiss_integration.py`: pinned ephemeris gate, no Moshier fallback, real-data integration.

## KUN-01 independent validation package (CLAUDE-003, proposed)
| Document | Purpose |
|---|---|
| [accuracy/scientific-decisions.md](accuracy/scientific-decisions.md) | Recommendations and owner questions for SCI-01 (conventions), SCI-02 (MVP scope), SCI-03 (date range). Decisions are recorded only in `docs/DECISIONS.md` on `main` |
| [accuracy/reference-sources.md](accuracy/reference-sources.md) | Independent reference-source register, provenance and the conversions that make sources comparable |
| [accuracy/golden-chart-spec.md](accuracy/golden-chart-spec.md) | Golden-chart specification, fixture record format, fixture inventory, comparison rules, proposed tolerances (all numeric rows BLOCKED for freeze until evidence pre-gates pass) and the separate time-scale track |
| [accuracy/qa-architecture.md](accuracy/qa-architecture.md) | Local QA harness design, PASS / FAIL / BLOCKED semantics, report contents and execution work packages |
| [accuracy/risk-register.md](accuracy/risk-register.md) | Risks blocking a verified-accuracy claim |
| [accuracy/evidence/](accuracy/evidence/) | Research scripts and raw outputs (convention-sensitivity probes; fixture input check). Not reference values |

## Optional independent astronomical golden-chart verification (NOT DONE)
1. Owner approves SCI-01, SCI-02 and SCI-03 (or modifies them) in `docs/DECISIONS.md`.
2. Evidence pre-gates PG-1 to PG-5 complete and ChatGPT QA freezes the tolerances **before** any engine comparison is run.
3. Generate reference fixtures from independent sources only (never the engine, never Swiss-based software), with full provenance.
4. Run the golden harness on the exact commit; report per-body circular differences, category checks and environment versions.
5. Verify time handling on its own track (UTC → UT1 by era, Delta T) and implement the historical-clock release gate before any public 1900–2100 promise.
6. Cover sign, Nakshatra/Pada and D9 boundaries, the 0°/360° transition, leap years, UTC-date crossover, DST gaps and folds, historical Indian offsets, both hemispheres and the date-range edges (see the fixture inventory).
7. Confirm no silent ephemeris fallback and no stale global state across concurrent requests (QA-008).
8. Validate Hindi/English report labels separately from numerical outputs.
9. Dasha, Dosha, Yoga and further divisional charts only after their own specification and independent fixtures.
10. Human review of methodology, astrology variants, privacy and AGPL deployment boundary.

No independent astronomical-accuracy claim is permitted until that separate reference-backed golden suite passes on an exact SHA. A Swiss-conformance claim requires reproducible separate-CLI and rule-verification evidence. Customer-facing reliability claims or a release additionally require the separately maintained method, birth-time, legal, security and product gates. No deployment is authorized by this document.
