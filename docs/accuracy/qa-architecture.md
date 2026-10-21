# Golden-chart QA architecture and execution plan

**Document ID:** SP-KUN-ACC-QA | **Work package:** CLAUDE-003 / KUN-01 Phase D | **Status:** PROPOSED design. Nothing here is implemented.

Runs locally or on an owner-approved VPS only. **No GitHub Actions, workflows, schedulers or hosted CI**, now or later, without separate owner authorization.

## 1. Components

```text
tests/golden/
  fixtures/                 GC-*.json, TZ-*.json, TR-*.json   (input + provenance + expected; committed)
  references/raw/           raw Horizons responses, generator logs (text, committed with SHA-256)
  generator/                reference generator: own venv, own lockfile
    requirements.lock       skyfield, pyerfa, jplephem, numpy pinned with hashes
    generate.py             writes fixtures; MUST NOT import sabpuja_kundali or swisseph
    oracle.py               category oracle written from rule definitions (R-11)
  harness/
    run.py                  loads fixtures, runs engine, compares, writes report
    circular.py             circular difference and boundary-distance helpers
    environment.py          collects versions and hashes
    independence_check.py   static import scan of generator/ (fails on forbidden imports)
reports/                    git-ignored local output: golden-report-<sha>-<utc>.json / .md
```

Two separate virtual environments keep the reference independent: `generator/` never sees the engine, the harness never computes references.

## 2. Flow

1. **Generate (after approvals only).** On a machine with the reference data (DE421 here; DE440s, Horizons and INPOP elsewhere), `generator/generate.py` writes each fixture's `expected` block and provenance. Horizons queries are done by hand or script on a machine that can reach JPL; the raw text response is committed and hashed. Fixture JSON is committed in a reviewed PR; ChatGPT QA checks provenance before any engine comparison is run.
2. **Freeze.** Fixtures get a `fixture_revision`. The report records each fixture file's SHA-256.
3. **Run.** `python -m tests.golden.harness.run --ephe /abs/path --report-dir reports/` on the exact commit under test.
4. **Review.** The JSON and Markdown reports go into the PR evidence with the exact SHA.

## 3. Outcome classes (per check, per fixture, and overall)

| Outcome | Meaning | Counted as implementation defect? |
|---|---|---|
| PASS | Same method signature, within tolerance, categories equal | No |
| FAIL | Same method signature, outside tolerance or category differs outside the indeterminate band | **Yes** |
| METHOD-MISMATCH | Fixture's method signature differs from the engine's emitted `method` metadata (e.g. fixture says mean node, engine says true) | No; reported separately as a convention disagreement for owner/PM |
| BOUNDARY-INDETERMINATE | Reference value within tolerance of a segment boundary | No; fixture must be redesigned |
| BLOCKED | Something needed to judge is missing: a required SCI decision not APPROVED, ephemeris verification failure, reference file missing or hash mismatch, tzdata version different from the fixture's, fixture outside reference coverage (e.g. DE421 after 2053) | Not a pass. Overall run is not PASS |
| SELF-CONSISTENCY PASS/FAIL | Internal identities (Ketu = Rahu + 180°, rule oracle) | Reported in a separate section, never counted toward independent validation |

Overall verdict: **PASS** only if every independent check is PASS. Any FAIL makes it FAIL. Otherwise any BLOCKED, METHOD-MISMATCH or BOUNDARY-INDETERMINATE makes it BLOCKED. Process exit code: 0 PASS, 1 FAIL, 2 BLOCKED. There is no "skipped": a check that cannot run is BLOCKED and the run is not green.

## 4. Report contents

Per check: fixture ID and revision, quantity, engine value, reference value and source ID, signed circular difference in arcseconds, tolerance ID and value, distance to nearest category boundary, outcome.

Run header (all mandatory; a missing item makes the run BLOCKED):
- Git commit (`git rev-parse HEAD`) and a dirty-tree flag; a dirty tree is BLOCKED.
- Fixture set: directory hash, per-file SHA-256 and revision.
- Python version and platform.
- `pyswisseph` distribution version and `swe.version` (Swiss library version).
- Ephemeris manifest version, source commit, and the verified SHA-256 of each required `.se1` file (from the existing `verify_ephemeris_dir` path, unchanged).
- tzdata version actually used by `zoneinfo` (system `tzdata.zi` header or `tzdata` package version) and whether it equals each fixture's `tzdata_version`.
- Reference generator lockfile hash, and reference data hashes (DE421/DE440s/INPOP, IERS file).
- Engine `method` block as emitted.
- UTC start and end time of the run. No birth data beyond the synthetic fixtures is ever logged.

## 5. Preserving existing safeguards

- The ephemeris manifest gate (`ephemeris.verify_ephemeris_dir`, CLAUDE-002a) runs unchanged before every engine call. A manifest failure is BLOCKED, never bypassed.
- The existing real-data unittest behaviour stays: without `SABPUJA_TEST_EPHE_PATH` the real-data tests skip (13 at `d8193c6`, measured; `data/ephemeris/README.md` still says 12); with it set, missing or mismatched files fail instead of skipping. Release evidence still requires 0 skipped. The golden harness is a separate entrypoint and does not change `python -m unittest discover -s tests`.
- `SE_EPHE_PATH` stays refused. No Moshier fallback.
- The golden suite needs the real ephemeris always; it has no "data absent" mode.

## 6. Independence guard

`independence_check.py` parses every file in `generator/` with `ast` and fails if it imports `sabpuja_kundali`, `swisseph`, or reads engine output files. The harness refuses to run (BLOCKED) if the check fails or if any fixture lists a reference whose class is D or M as its expected-value source.

## 7. Execution plan (work packages after approval)

| WP | Scope | Prerequisites | Output |
|---|---|---|---|
| KUN-01-WP1 | Harness skeleton: circular math, outcome classes, environment capture, independence guard, report writer; tested with **hand-made dummy fixtures** that are labelled as such | QA PASS on this plan | Draft PR, unit tests for the harness itself |
| KUN-01-WP2 | Reference generator with Skyfield/DE421 + ERFA + mean-node polynomial + oracle; generate GC/TR fixtures up to 2053 | SCI-01a–d, h, SCI-02 APPROVED | Fixtures + provenance PR, no engine comparison yet |
| KUN-01-WP3 | Off-container references: Horizons (4 fixtures), DE440s (post-2053 fixtures), INPOP (2 fixtures), IAE ayanamsha values | Owner/PM obtains data on another machine; IAE volumes | Raw files + hashes committed |
| KUN-01-WP4 | First full golden run on the exact foundation SHA; triage FAIL vs METHOD-MISMATCH | WP1–WP3 | Report; no code changes in the same PR |
| KUN-01-WP5 | Approved small code changes, each its own PR: ascendant via `b"W"` (SCI-01e), latitude band (SCI-01g), local-date window (SCI-03), D9 houses and optional all-body Nakshatra (SCI-02), method metadata strings | Matching approvals | Before/after golden reports |
| KUN-02 | Time-zone policy for pre-1956 India and place data (DATA-01) | DATA-01 | Separate spec |

Tolerances, fixture inputs and reference choices are frozen at the revision QA approves. Changing any of them after results are seen requires a written reason in `docs/DECISIONS.md`.
