# KUN-SCI-GOLD-001: D1/D9 golden-reference validation (test-only)

Scientific QA workstream on the owner-preview baseline PR #58
(`fde3ec670618a02f2b913e9bbbedd1521d3840c7`, tree `da8112a1788f16c3f2f5ab94d46278d279c09278`).
It adds tests and evidence only. **No calculation, method, schema, report or
dependency change.** All 68 fixtures are synthetic; none is a real birth.

## Claim boundary

| Layer | What a PASS means | What it does NOT mean |
|---|---|---|
| `SWISS` (`SWISS-CONFORMANCE PASS`) | Engine longitude equals the separately built official `swetest` 2.10.03 (same pinned `.se1` files and flags) within the frozen KUN-01-SWISS-01 tolerance | Independent astronomy: same Swiss C library on both sides |
| `RULES` | Engine D1 Rashi, D9 sign, Moon Nakshatra/Pada, D1 and D9 whole-sign houses and the D9 North Indian cells equal an **isolated** reference implementation applied to the swetest longitudes | That the longitudes themselves are astronomically right |
| `TIME` | Engine UTC equals the UTC derived by hand from the quoted IANA tz 2026e rule text, confirmed by an independent RFC 8536 TZif reader | Historical birthplace civil-clock truth (DATA-01 open) |
| `METHOD` | Engine-emitted conventions match the canonical decisions (SCI-01a/b/c/d/e/f, SCI-02 C2) | Otherwise `METHOD-MISMATCH` |
| `DISCLOSURE` | Projected-civil-time and >60° disclosures appear exactly when required | |
| `LAGNA-F` | Reported only: an independent ascendant formula on swetest ARMC/obliquity/ayanamsha | Always `BLOCKED`: no Lagna tolerance is frozen (REL-01, SCI-01e) |
| `ASTRO` | Nothing: always `BLOCKED` | Independent JPL/INPOP assurance is optional and deferred (issue #15, PRD OD-05) |
| `REFUSAL` | The engine refuses with exactly the expected code | |

Classifications: `PASS`, `FAIL`, `METHOD-MISMATCH`, `BOUNDARY-INDETERMINATE`,
`BLOCKED`, `QUALIFIED` (otherwise passing, but after the pinned 2027-06-28
leap-second list expiry, so civil time, UT1-UTC and Delta T are projections:
SCI-01h), and `SWISS-CONFORMANCE PASS/FAIL` for Swiss-on-Swiss rows. A
category is `BOUNDARY-INDETERMINATE` when its reference longitude lies within
the frozen `binding_vs_swetest` = 1e-9° of a relevant edge. No public accuracy
claim follows from any of this.

## Files

| Path | Role |
|---|---|
| `reference_rules.py` | Isolated D1/D9 rules (exact `Fraction`): classical movable/fixed/dual Navamsa start rule, cross-checked by the elemental rule; North Indian cell geometry. Standard library only (AST-checked) |
| `tzif_reference.py` | Isolated RFC 8536 TZif reader (no `zoneinfo`) |
| `asc_formula.py` | Isolated ascendant formula (Meeus ch. 14, quadrant-safe atan2) |
| `design/build_matrix.py` | Builds `matrix.json`. Boundary instants are *selected* with a pinned-pyswisseph search; no expected value comes from it. Deterministic (tested) |
| `matrix.json` | 68 predeclared fixtures with inputs, purpose, coordinate source and the quoted IANA rule text |
| `swiss_reference.py`, `capture.py` | Official swetest receipts: exact JD from the expected UTC, four runs (planets, speeds, W houses, true obliquity), redacted |
| `receipts/` | 50 committed receipts (original reference evidence) and `SHA256SUMS` |
| `PINS.json` | SHA-256 of `matrix.json`, `receipts/SHA256SUMS` and the frozen `tests/swiss_conformance/spec.json` |
| `run.py` | Comparison runner: per fixture the receipt and hash, exact input, expected, actual, difference, tolerance, classification and basis; JSON, CSV and Markdown |
| `pdf_fidelity.py` | Premium PDF vs engine and vs reference (D1/D9 chart cells by the isolated geometry, positions and Navamsa tables); English/Hindi parity |
| `test_sci_gold.py` | 22 unit/integration tests (in the normal `tests` discovery) |
| `INVENTORY.md` | Existing QA infrastructure and reuse decisions |
| `DISCREPANCY-REGISTER.md` | Every mismatch and finding, with disposition |
| `BLOCKERS.md` | Scientific decision and tolerance blockers |

## Reproduce

```bash
# Pinned environment (same as the engine suite)
pip install pyswisseph==2.10.3.2 tzdata==2026.5 -r report/phase1/requirements-qa.txt
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src:$PWD/prototype
# Verified .se1 files and the official swetest, built as in tests/swiss_conformance/README.md
export SABPUJA_TEST_EPHE_PATH=/abs/ephe SABPUJA_TEST_SWETEST=/abs/swetest SABPUJA_TEST_SWETEST_RECEIPT=/abs/receipt.json
unset SE_EPHE_PATH

python -m unittest discover -s tests -v                       # engine suite incl. sci_gold; 0 skipped expected
python -m tests.swiss_conformance.run_d3 --report-dir reports/ # canonical Swiss CLI conformance (D3 v2)
python -m tests.sci_gold.run --report-dir reports/             # golden-reference comparison, live receipt re-capture
python -m tests.sci_gold.pdf_fidelity --root . --ephe "$SABPUJA_TEST_EPHE_PATH" --out reports/pdf \
    --gold-report reports/sci-gold-<sha12>.json
# Hindi: the same tool against a read-only checkout of PR #61's exact head
python -m tests.sci_gold.pdf_fidelity --root /path/to/pr61-checkout --locales en,hi \
    --ephe "$SABPUJA_TEST_EPHE_PATH" --out reports/pdf61 --gold-report reports/sci-gold-<sha12>.json
# Regenerate (must be byte-identical): matrix and receipts
SABPUJA_EPHE_PATH=$SABPUJA_TEST_EPHE_PATH python tests/sci_gold/design/build_matrix.py | cmp - tests/sci_gold/matrix.json
python -m tests.sci_gold.capture --out /tmp/receipts && diff -r /tmp/receipts tests/sci_gold/receipts
```

The IANA source text quoted in the fixtures is tz release 2026e from
`https://github.com/eggert/tz` tag `2026e` (commit
`039ef27cc5f062a2055cb67435d6d71adbefd27d`, "Release 2026e"; file SHA-256 in
`INVENTORY.md`). data.iana.org was not reachable from the build host.

## Rollback

Delete `tests/sci_gold/`. Nothing else in the repository changes.
