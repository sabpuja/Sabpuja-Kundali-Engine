# Golden-chart QA harness (KUN-01-WP1 skeleton)

**Status: skeleton only. It contains no reference values and validates nothing.** Every committed fixture is a labelled dummy, every owner decision except SCI-01b and SCI-01c (approved conventions, `main` 0023fdc) is PENDING, every tolerance is NOT_FROZEN, no reference output has been obtained, and the method manifest is UNREVIEWED. A run therefore always ends **BLOCKED (exit 2)** and its report starts with **DEMO ONLY / NOT ASTRONOMICAL VALIDATION**. Do not read any result from this directory as evidence that the engine is astronomically accurate.

Design: `docs/accuracy/qa-architecture.md` and `docs/accuracy/golden-chart-spec.md`. Runs locally only; no GitHub Actions or hosted CI.

## Run

```bash
# Unit tests for the harness itself (part of the normal suite)
SABPUJA_TEST_EPHE_PATH=/abs/path/to/verified/ephe python -m unittest discover -s tests -v

# Demo run on the dummy fixtures; writes reports/golden-report-<sha>-<utc>.json and .md (git-ignored)
python -m tests.golden.harness.run --ephe /abs/path/to/verified/ephe --report-dir reports/
echo $?   # 2 = BLOCKED
```

Options: `--fixtures DIR` (default `tests/golden/tests/fixtures_dummy`), `--ephe DIR` (default `$SABPUJA_EPHE_PATH`), `--report-dir DIR` (default `reports/`).

## Reading a report

Exit code: **0** PASS, **1** FAIL, **2** BLOCKED or QUALIFIED. There is no "skipped".

| Outcome | Meaning |
|---|---|
| PASS | Same method signature, within a frozen tolerance, categories equal |
| FAIL | Outside tolerance, or a category differs away from a boundary. Any FAIL makes the run FAIL |
| METHOD-MISMATCH | Fixture signature differs from `method-manifest.json`, or the engine's emitted `method` block contradicts it. Not a defect; the run is not PASS |
| BOUNDARY-INDETERMINATE | Reference within tolerance of a Pada/Nakshatra/Rashi/D9 edge (or the Lagna's Rashi edge for houses). The fixture must be redesigned |
| BLOCKED | Something needed to judge is missing. Every reason is listed |
| QUALIFIED | Would pass, but the epoch is after the last observed Delta T. Never an unqualified PASS |
| SELF-CONSISTENCY | Ketu = Rahu + 180°. Listed separately and never counted |

The engine is called only when **no** gate blocks. Gates, in order:

- **Run level:** clean git tree; verified ephemeris (the engine's own `verify_ephemeris_dir`, unchanged); known tzdata and Swiss versions; method manifest present, REVIEWED and with every pinned blob SHA equal to the working tree; generator passes the independence scan; configs readable; time-scale track VERIFIED; fixture index complete.
- **Fixture level:** index entry is a plain fixture file name (`DUMMY-NN.json`, `GC-NN.json`, `TR-NN.json`, `TZ-NN[a-z].json`), not a symlink, inside the fixture directory, and equal to `fixture_id` (otherwise BLOCKED without reading it); schema and index hash/revision; not dummy; `accuracy_claim` true; reference verified; each reference known, with the fixture's `source_class` equal to the registry's, of class I-code/I-data/I-pub, obtained, with raw bytes present inside the fixture directory and matching SHA-256; epoch inside each reference's coverage; every required SCI decision APPROVED with approver, date and DECISIONS.md commit; every tolerance FROZEN with a finite, non-negative number and a QA reference; fixture tzdata equal to the tzdata in use.

All JSON (fixtures, index, configs, manifest) is parsed strictly: `NaN`, `Infinity` and numbers that overflow to infinity are rejected, and oversized integers are schema errors, so they block instead of raising. The comparison itself also refuses a non-finite or negative tolerance.

Reports contain versions, hashes, reason codes and comparison numbers only: no fixture birth inputs, no paths, host or user names, and engine errors as codes only.

## Files

| Path | Role |
|---|---|
| `harness/circular.py` | `circular_diff_deg/arcsec` (signed, in [-180°, 180°), exact Fractions), `boundary_distance_arcsec` |
| `harness/oracle.py` | Category oracle written from the rule definitions; never imports `sabpuja_kundali.rules` |
| `harness/outcomes.py` | Outcome classes, `overall_verdict`, `fixture_outcome`, `exit_code` |
| `harness/schema.py` | `validate_fixture` (strict keys and types, dummy flags), `load_fixture_set` (INDEX.json SHA-256 and revision) |
| `harness/manifest.py` | `check_manifest` (read-only; recomputes git blob SHAs), `signature_mismatches`, `emitted_block_contradictions` |
| `harness/gates.py` | Decision, tolerance, source, coverage, tzdata and time-track gates; `time_qualification` |
| `harness/environment.py` | PII-safe capture: Python, platform, pyswisseph and Swiss versions, tzdata in use, git SHA and dirty flag, ephemeris hashes |
| `harness/compare.py` | Pure comparison (`compare_fixture`) and the Ketu self-consistency check |
| `harness/report.py` | Deterministic JSON (`sort_keys`) and Markdown from the same data |
| `harness/run.py` | Orchestration and CLI |
| `generator/isolation.py` | AST scan and runtime import guard against `sabpuja_kundali`, `swisseph` and engine report files; D/M reference classes rejected |
| `generator/generate.py` | Placeholder; always exits 2 (WP2 not authorized) |
| `method-manifest.json` | Engine method as read from source at `d8193c6`, with blob SHAs. UNREVIEWED until ChatGPT QA reviews it |
| `config/*.json` | Mirrors of decision status (SCI-01b/c approved, rest PENDING), tolerances (all NOT_FROZEN), reference registry (nothing obtained), time track (BLOCKED) |
| `tests/fixtures_dummy/` | Four DUMMY fixtures with invented values and fake source IDs, plus `INDEX.json` and one fake raw file |
| `tests/test_*.py` | Unit tests; "approved world" tests build temporary directories with TEST-ONLY records to exercise PASS/FAIL plumbing with a mock engine |

Layout differences from `qa-architecture.md` §1: the independence check lives in `generator/isolation.py` (not `harness/independence_check.py`), the category oracle in `harness/oracle.py` (the generator will reuse it in WP2), and real fixtures will go in `fixtures/` while the dummies stay in `tests/fixtures_dummy/`.

## Changing records

Nothing here updates itself. When code under `src/sabpuja_kundali/` changes, the manifest goes stale and runs block until someone re-reads the source, updates `method-manifest.json` by hand and QA reviews it. Decision, tolerance and reference records change only with the owner's decision in `main:docs/DECISIONS.md`, QA-reviewed pre-gate evidence, or recorded reference bytes, respectively.

## Rollback

The skeleton adds files under `tests/golden/` and one pointer line in `docs/accuracy/qa-architecture.md`; it changes no engine code, existing test, manifest or checksum. Rollback is closing the PR or reverting its commit.
