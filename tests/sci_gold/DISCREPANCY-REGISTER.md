# KUN-SCI-GOLD-001 discrepancy register

Every mismatch, refusal-to-judge and finding from this workstream, on PR #58
`fde3ec670618a02f2b913e9bbbedd1521d3840c7`. Exact numbers come from the
comparison report of the committed head (`sci-gold-<sha12>.json`).

**No calculation discrepancy was found.** No engine value, expected value or
tolerance was adjusted. Nothing here justifies a calculation-fix PR.

| ID | Type | Fixtures / scope | Observation | Classification | Disposition |
|---|---|---|---|---|---|
| DR-01 | Governance / lineage | `docs/DECISIONS.md` on the #58 branch | The branch carries the 72-line 2026-10-21 register (only SCI-01b/c approved, the rest PENDING). The canonical register on `main` `1d4bcb6` (199 lines) records SCI-01a/d/e/f/g/h, SCI-02 C1/C2, SCI-03 and REL-01 as OWNER APPROVED / CANONICAL. Code and metadata follow the canonical register | Finding, not a calculation mismatch | Read decisions from `main`. A documentation-only sync of the stack is a separate, owner-authorized task. Not changed here |
| DR-02 | Test lineage | `tests.swiss_conformance.run`, `run_current` | Both exit `SWISS-CONFORMANCE FAIL` on `fde3ec6`: their archived cases use `UTC`/`Etc/*` keys that D3 v2 refuses (`TIMEZONE_NOT_LOCATION_BASED`). The canonical `run_d3` reports `d3 PASS`, `numeric_continuation PASS`, `v1_divergence PASS`, `archival_divergence PASS`, `archived_d3_v1_policy PASS` | Expected, recorded divergence | Use `run_d3` for Swiss CLI conformance. No change |
| DR-03 | Boundary | GOLD-E01 (Moon at 120° within ~7.1e-10°) | The reference cannot decide Moon Rashi, D9, Nakshatra/Pada, both Moon houses and the D9 cell list at the frozen 1e-9° band. The engine's exact half-open classification is unchanged | `BOUNDARY-INDETERMINATE` (designed) | Owner/QA decision on near-edge customer disclosure is open (B-6). Not a defect |
| DR-04 | Coverage | 11 fixtures with synthetic non-registered places (GOLD-Z01-Z05, Z08, Z09, L01-L04) | The Hindi renderer (PR #61) refuses a birthplace outside its terminology register (`ReportLocaleError`), so these cannot be rendered in Hindi. English renders and passes for all 50 | Hindi fidelity `BLOCKED` for 11 | Correct fail-closed renderer behaviour. Hindi parity proven on the other 39 (cells and every printed number identical to English). Wider Hindi place coverage belongs to the place-data work |
| DR-05 | Schema | Retrograde-sensitive fixtures GOLD-B08-B10 | Schema 0.3.0 emits no speed or retrograde flag. Reference speeds (swetest run B, `SEFLG_SPEED`) confirm Mercury, Mars and mean Rahu are retrograde at the crossings; longitudes and categories pass | NOT-IN-SCHEMA (informational) | Any retrograde marker in the product needs its own owner decision and fixtures |
| DR-06 | Reuse | PR #14 golden harness `18be466` | Method manifest pinned to `d8193c6`; decision mirror and tolerance records stale | Not reused for verdicts | Rebaseline is a separate task; this workstream does not alter PR #14 |
| DR-07 | Schema | D1 North Indian chart | The engine has no D1 house list (only per-body `whole_sign_house`); the D1 North Indian cells exist only in the renderer | Verified via the PDF | Covered by `pdf_fidelity.py` (cell geometry, sign numbers) |
| DR-08 | Provenance | swetest build | This build's SHA-256 `400661cd…` differs from the claude-004 build `02c82cea…` of the same source and compiler (debug info carries build paths) | Finding | A build receipt is builder testimony plus binary hash, not a reproducible-build proof (as `tests/swiss_conformance/README.md` already says). Both builds report 2.10.03 and give byte-identical receipts across reruns here |
| DR-09 | Fixture text | GOLD-B02 description | An early draft of the fixture description named the D9 change as "Dhanu -> Makara"; the classical rule and the 108-part rule both give Karka -> Simha at 13°20′. Corrected before the first pinned run; no expected value is taken from description text | Fixed in this task (pre-pin) | None |
