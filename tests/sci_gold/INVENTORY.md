# KUN-SCI-GOLD-001 inventory of existing scientific QA and reuse decisions

Checked on 2026-11-02 against GitHub and the project evidence folder. "Canonical"
means recorded in `main:docs/DECISIONS.md` (main `1d4bcb6`).

## Baseline and lineage

| Item | Value | Check |
|---|---|---|
| Candidate application baseline | PR #58 `fde3ec670618a02f2b913e9bbbedd1521d3840c7`, tree `da8112a1788f16c3f2f5ab94d46278d279c09278` | fetched by exact SHA; this branch starts there |
| Engine and engine tests since Gate 3E | `git diff 185353a fde3ec6 -- src tests` is empty | the engine is byte-for-byte the C7-passed Gate 3E engine (PR #42 `185353a`, C7 review 5647737922) |
| PR #61 (editorial, not stacked on) | head `fee3967d62d0229e31de98682da9ada5d9190e93`, tree `ae4bbf144d0d0c1209c6274b465009757711dfe9` | `fde3ec6` is its ancestor; `git diff fde3ec6 fee3967 -- src tests` is empty, so Hindi work changes no calculation; used read-only for Hindi PDF fidelity |
| Stack below PR #58 | #58 → #56 → #55 → #54 → #53 → #46 → #45 → #44 → #42 → #41 → `integration/kun03-gate1` | all draft, unmerged |
| PR #1 | draft, head `d8193c6` | HOLD unchanged |
| Decision register on this branch | `docs/DECISIONS.md` is the 72-line 2026-10-21 copy | **stale**: main's 199-line register is canonical (see DR-01) |

## Canonical decisions used (main `1d4bcb6`)

SCI-01a (Lahiri, Swiss mode 1, true ayanamsha), SCI-01b (Swiss mean node), SCI-01c
(Ketu = Rahu + 180 exactly), SCI-01d (geocentric apparent, `FLG_SWIEPH|FLG_SIDEREAL`),
SCI-01e (Lagna = `houses_ex(..., b"W", FLG_SIDEREAL)` `ascmc[0]`), SCI-01f (D1
whole-sign; D9 108 half-open parts; D9 Lagna from the unrounded Lagna), SCI-01g
(±66.0° band, disclosure above 60°), SCI-01h (civil UTC as UT1, disclosed), SCI-02
C2 (schema 0.3.0 D9 whole-sign houses), SCI-03 (1900-2100 local window, Option B
pre-1970 refusal, D3 v2, pinned tzdata 2026.5), REL-01 (Swiss CLI conformance +
independent rule/formula checks mandatory; JPL/INPOP optional; **no tolerance
frozen**). DATA-01 and OD-05 remain PENDING.

## Existing components and decisions

| Component | Where | Status found | Decision |
|---|---|---|---|
| Swiss CLI conformance, D3 v2 profile (`tests/swiss_conformance/run_d3.py`, `d3.py`, profiles, `spec.json`, `cases.json`, `inputs.py`, `swetest_cli.py`) | in the #58 lineage (KUN-01-SWISS-01 PR #18 → KUN-03 reconciliation #33 → D3 #35) | frozen spec SHA-256 `642a770d…`; run here with an official swetest: **SWISS-CONFORMANCE PASS** | **Reused unchanged** as the Swiss CLI conformance report. Its frozen tolerances (1e-9° binding, 1e-8° engine) are reused by reference for the new matrix (blocker B-3: QA to confirm) and its receipt validator is reused by `run.py` |
| Archival runners `run.py` (PR #18 profile) and `run_current.py` (KUN-03 current v1) | same | exit FAIL on `fde3ec6`, by design: D3 v2 refuses `UTC`/`Etc` keys in their cases; `run_d3` records the divergence as `v1_divergence PASS`, `archival_divergence PASS` | **Not used for a verdict**; reported in DR-02 |
| Exact rule oracles (`tests/boundary_oracle.py`, `tests/d9_house_oracle.py`, `tests/swiss_conformance/oracle.py`) | in lineage | pass inside the suite | **Not reused** for expectations: they use the same 108-part algorithm as production. A new isolated reference with a different (classical) algorithm was written; the unit test proves the algorithms agree on every Pada |
| Engine unit/contract suites (`tests/*.py`, 474 tests) | in lineage | 474/0/0 with real data and swetest, 0 skipped | **Reused unchanged**; run in full |
| Golden-chart harness skeleton, issue #12 / PR #14 `18be466` | separate branch off docs PR #11 | QA-passed as a dummy skeleton; method manifest pinned to `d8193c6`, decision mirror still shows SCI-01a/d/e/f/g/h PENDING, every tolerance NOT_FROZEN, reference registry empty | **Not merged or stacked.** Its outcome vocabulary (PASS/FAIL/METHOD-MISMATCH/BOUNDARY-INDETERMINATE/BLOCKED/QUALIFIED) and the QUALIFIED-after-observed-ΔT idea are adopted; its gates would block on stale records, so rebaselining it is a separate task (DR-06). Swiss output is never written into its independent-only oracle classes |
| Accuracy plan PR #11, Swiss-first plan PR #17, JPL/INPOP issue #15 | docs branches | #15 OPTIONAL/DEFERRED | Followed: ASTRO layer is BLOCKED; nothing external obtained |
| Ephemeris pinning, fail-closed (CLAUDE-002a/b/c, PRs #6/#8/#10, merged into the foundation branch) | in lineage | manifest checks pass with the pinned files | **Reused**: `verify_ephemeris_dir` is a run gate |
| Prototype gazetteer `places.json` and `prototype/tools/check_places.py` | in lineage | re-run with the pinned GeoNames wheel (`24fdaaea…`) and Natural Earth v5.1.2 GeoJSON (`fd3fa867…`): exit 0, 12/12 places, cross-check ≤ 4.04 km | **Reused** for the 13 places.json fixtures |
| Premium report tests (`report/phase1/tests`, 84) incl. PDF-vs-engine table and chart checks on 13 scenarios | in lineage | 84/0/0 | **Reused unchanged**; `pdf_fidelity.py` adds checks on the gold matrix with an isolated geometry and against the reference |
| Hindi renderer (PR #59-#61) | above #58 | not in this branch | Used read-only from `fee3967` |
| claude-004-swiss01 evidence (official vs bundled swetest) | project folder | historical, older SHAs | Build method reused; this run rebuilt swetest from `c69c14a` |

## Sources pinned in this task

| Source | Identity |
|---|---|
| Swiss Ephemeris source, swetest and `.se1` files | `https://github.com/aloistr/swisseph` `c69c14adb7a0f94829586ffd92cd422aacb21e86`; `sepl_18.se1` `ca1393ce…9a66`, `semo_18.se1` `1ca07bd6…a4f7` |
| swetest build | `make swetest`, gcc 13.3.0, glibc 2.39; SHA-256 `400661cdd27d1b3d55766de9a657d5a22bf232308468c2db2bea435152ae5abd` (builder testimony, not a reproducible-build proof; differs from the claude-004 build `02c82cea…` of the same source, DR-08) |
| IANA tz 2026e source text | `https://github.com/eggert/tz` tag `2026e`, commit `039ef27cc5f062a2055cb67435d6d71adbefd27d`; `asia` `02b69728085f6b0c999da70de2f1f9a2d8952b533a450d53bb41e03eb7d0e92e`, `australasia` `846ba455578e3e0f9eb850f05be3cc06d02ff51bbe4b726f755be9dc765f16c9`, `europe` `fec11bf6c6bd0619a8777bbdaa2ecd184fde291cb4b97efa87d334c7145ba3c2`, `northamerica` `c0c5da0dc337444d80709cf9f8d8011719b789df160ce107a5c38c90e73dc54c`, `backward` `b8296b9ef1ece72d813878132c0f17e2c52b26af6004eeb9c37d049b64cd9401`, `southamerica` `13be56a242da3c1a4a6d12050e5fd48b1753c8c1dc237cbc2edb40eac636be7f`, `antarctica` `e410ad71c9450828c592d21419301d41ac79ce50159fd0ac2d6c5031cb6bdfe6` |
| Runtime TZif data | PyPI `tzdata==2026.5` (IANA 2026e), verified by the engine's TZif manifest |
