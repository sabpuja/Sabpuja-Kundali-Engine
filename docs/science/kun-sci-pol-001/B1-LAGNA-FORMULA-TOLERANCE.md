# B-1: Tolerance for the independent Lagna formula check

**PROPOSAL. PENDING OWNER APPROVAL. Nothing here is frozen or approved.**

## 1. What is being decided

PR #62 adds the layer `LAGNA-F`. For each chart it recomputes the sidereal Lagna with a closed-form ascendant formula and compares the result with the swetest `Ascendant` value. The inputs are the ARMC, the true obliquity and the true Lahiri ayanamsha that swetest itself printed. The formula is Meeus ch. 14, in the eastern-root `atan2` form:

`Asc = atan2(cos ARMC, -(sin ARMC cos ε + tan φ sin ε)) − ayanamsha`

No tolerance has been frozen for this comparison. The REL-01 ledger row 1 says "no tolerance frozen", and SCI-01e says "no golden-chart Lagna tolerance". So all 50 rows are `BLOCKED` today, and the observed difference is only reported.

**Scope of the check.** It verifies the step from Swiss-printed sidereal time, obliquity and ayanamsha to the Lagna: the formula, the quadrant, the eastern root and the ayanamsha subtraction. It does **not** test Swiss sidereal time, nutation or precession, and it is not independent astronomy.

## 2. Evidence

The evidence comes from the 50 verified charts of the gold matrix. The source is PR #62 at `6722b5c`, using gold report `sci-gold-6722b5c46c3f.json` (sha256 `edb8aab5…4bef`) and pinned receipts with `SHA256SUMS` sha256 `71a6a969…8eee`. It was reproduced with [`analysis/analyze.py`](analysis/analyze.py). The full numbers are in [`analysis/results.json`](analysis/results.json), key `B1`.

| Quantity (50 charts) | min | median | p95 | max |
|---|---|---|---|---|
| \|formula − swetest\| in float64 (as run in PR #62) | 1.93e-13° | 2.47e-12° | 1.21e-11° | **4.33e-11°** |
| Same, formula evaluated at 40 digits (mpmath 1.3.0) | 1.82e-13° | 2.44e-12° | 1.21e-11° | 4.33e-11° |
| float64 evaluation error of the formula itself | 4.0e-16° | 2.2e-14° | 6.3e-14° | 8.9e-14° |
| Per-chart input-quantisation bound (see §3) | 9.46e-12° | 1.18e-11° | 2.89e-11° | 1.21e-10° |
| Observed difference ÷ that chart's bound | 0.013 | 0.22 | 0.51 | **0.80** |
| \|∂Asc/∂ARMC\| (amplification) | 0.55 | 0.93 | 1.70 | 3.99 (GOLD-L02, 60.17° N) |
| Lagna rate (degrees per minute of birth time) | 0.138 | 0.234 | | 1.00 |

## 3. Numerical-method analysis

**1. float64 is not the limiting factor.** Re-evaluating the formula at 40 significant digits changes the differences by at most 9e-14°. Arithmetic on a 360° circle in double precision has a spacing of about 5.7e-14°, so the remainder comes from the inputs.

**2. The inputs are printed and rounded.** swetest prints ARMC, obliquity and Ascendant to 11 decimals, a half unit of 5e-12°. It prints the ayanamsha in DMS with 8 decimals of an arcsecond, a half unit of 1.4e-12°. These errors pass through the formula with weights |∂Asc/∂ARMC| and |∂Asc/∂ε|. The resulting bound is:

   `B = |∂A/∂ARMC|·5e-12 + |∂A/∂ε|·5e-12 + 1.4e-12 + 5e-12`

   Every chart's observed difference is below its own bound, and the largest ratio is 0.80. The differences are therefore fully explained by print quantisation. No residual algorithmic difference between the formula and Swiss `houses_ex` is visible at this resolution.

**3. Worst case inside the canonical envelope.** A grid sweep covered ARMC in 0.25° steps, latitude from −66° to +66° in 0.5° steps (SCI-01g) and ε of 23.40° and 23.45°. The largest amplification is |∂A/∂ARMC| ≈ 42.4, at latitude −66° and ARMC 90°, where the ecliptic lies close to the horizon. |∂A/∂ε| reaches 52.4. Adding the two maxima, although they occur at different points, gives a conservative worst-case quantisation bound of **4.8e-10°** for any chart the product accepts. The joint maximum at a single point is 3.9e-10°, at latitude 66°. By latitude the joint bound is 2.1e-11° at 45°, 4.5e-11° at 60° and 7.2e-11° at 63°.

**4. Size of real defects the check must catch.** All values are on the 50 charts.

   | Defect | Typical size |
   |---|---|
   | Wrong quadrant or western root | 180° |
   | Ayanamsha sign error | about 47° |
   | Mean obliquity used instead of true | 1.06e-7° to 5.4e-2° (median 3.9e-4°) |
   | Mean ayanamsha used instead of true | about 2e-3° (6″ to 8″, the PR #51 comparison) |

   The smallest defect of this kind seen is about 1.1e-7°. Any tolerance above roughly 1e-7° would let the mean-versus-true obliquity mistake through on at least one chart.

**5. Time equivalent.** At the median Lagna rate, 1e-9° of Lagna equals 2.6e-7 s of birth time. At the envelope maximum of about 10.6° per minute it is about 6e-9 s. Every candidate tolerance below is far below one second of birth time.

## 4. Sensitivity at sign and house boundaries

- The closest any matrix Lagna comes to a Pada edge (every Rashi, Nakshatra and Navamsa edge is a Pada edge) is **0.0037°**. That is 3.7 million times the proposed tolerance. No Lagna category in the matrix is near-indeterminate.
- If a tolerance is frozen, a Lagna category compared through the formula would be `BOUNDARY-INDETERMINATE` when the swetest Lagna lies within that tolerance of an edge. This is the same rule as RULES and the same treatment as GOLD-E01. Because all 12 whole-sign houses follow the Lagna Rashi, one undecidable Lagna Rashi makes the whole D1 house list undecidable.
- The tolerance concerns only numerical agreement. Whether a customer's Lagna is stable against an uncertain birth time is a much larger effect: a quarter of a degree per minute. That belongs to B-6, not to this tolerance.

## 5. Options

| Option | Value | Consequence |
|---|---|---|
| **R (recommended)** | **1e-9°**, fixed, for \|lat\| ≤ 66.0° | About 2× the worst-case envelope bound (4.8e-10°) and 23× the observed maximum. It is also the existing `binding_vs_swetest` band, so one number serves both. It detects every defect class in §3 item 4 with at least 100× margin. All 50 rows would become PASS |
| A1 | 5e-10° | Equal to the envelope bound with no margin. A valid chart near latitude ±66° and ARMC 90° or 270° could FAIL on print rounding alone |
| A2 | 1e-10° | Below the bound in the highest-latitude part of the envelope. The joint bound passes 1e-10° only above about 64° (7.2e-11° at 63°, 3.9e-10° at 66°), so false FAILs are possible there. It would need a latitude-dependent rule |
| A3 | Adaptive: 2 × per-chart bound B (§3 item 2) | The tightest defensible value per chart (2e-11° to 1e-9°). It is more complex, and the tolerance becomes a computed quantity that QA must re-verify each time |
| A4 | 1e-8° | Matches the engine display tolerance. It still catches the defects in §3 item 4 (smallest 1.1e-7°), but with only about 10× margin |
| A5 | No tolerance (status quo) | LAGNA-F stays BLOCKED and never counts toward a verdict. The REL-01 "independent formula check" for the Lagna then remains reported but unscored |

## 6. Implementation implications if approved

These are test-only and go in a separate, authorized PR:
- `tests/sci_gold/run.py` `lagna_formula_layer` classifies with the frozen value instead of `BLOCKED`.
- Add the boundary-band rule for formula-based Lagna categories.
- Record the value, its basis and the approval link next to the KUN-01-SWISS-01 tolerances, without editing the frozen `spec.json`.

No engine, schema or report change. Customer output is unaffected.

## 7. Tests required after approval

- All 50 LAGNA-F rows PASS at the approved value.
- Mutation tests must FAIL: western root, ayanamsha sign error, mean instead of true obliquity, and a +2× tolerance offset.
- A synthetic envelope-edge case at latitude ±66.0° with ARMC near 90° or 270°, with the observed difference recorded.
- GOLD-E01 and all other classifications must be unchanged.
- A rerun of the 515-test suite, the Swiss D3 conformance and the live gold run, followed by independent QA on the exact SHA.
