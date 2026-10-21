# Accuracy and acceptance test plan

**Status: the engine is NOT astronomically validated.** No independent golden-chart comparison has been run. Do not claim accuracy until the golden suite below passes independent QA on an exact commit.

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

## Required golden-chart verification (NOT DONE)
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

No factual accuracy or release claim without evidence in the PR and a versioned validation report.
