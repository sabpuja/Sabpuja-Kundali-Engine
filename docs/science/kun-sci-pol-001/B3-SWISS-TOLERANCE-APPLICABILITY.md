# B-3: Applying the frozen Swiss tolerances to the 50-chart gold matrix

**PROPOSAL. PENDING OWNER APPROVAL. The values below are already frozen for KUN-01-SWISS-01. Whether they apply to this matrix is not yet approved.**

## 1. Existing approved values and their scope

The source is `tests/swiss_conformance/spec.json`, sha256 `642a770d…12a8`. It is pinned by PR #62 `PINS.json` and was frozen for KUN-01-SWISS-01. The spec states: "predeclared before the first real run; changing any value needs a written reason and QA review".

| Name | Value | Recorded basis | Where the gold matrix uses it |
|---|---|---|---|
| `engine_vs_swetest` | 1e-8° | "engine displays 8 decimals (half unit 5e-9 deg) plus binding_vs_swetest" | SWISS layer, all 500 rows: engine `longitude_deg` against the swetest longitude |
| `binding_vs_swetest` | 1e-9° | "same C source; swetest prints 11 decimals (half unit 5e-12 deg); allowance for compiler/optimisation differences between the -O0 swetest build and the pyswisseph wheel" | RULES layer, as the band of the `BOUNDARY-INDETERMINATE` rule. The binding itself is not compared in this matrix, because schema 0.3.0 exposes only rounded values |

**Approval scope.** These values were frozen for the 24 SC cases (18 charts and 6 refusals). The D3 v2 profile reuses them. PR #62 applies them to a different, larger matrix by reference. **Applying them to that matrix is not a change of value, but it is an extension of scope, and no approval for it exists.** This item asks for that approval explicitly.

## 2. Evidence

The numbers come from PR #62 at `6722b5c`, `sci-gold-6722b5c46c3f.json`, reproduced with [`analysis/analyze.py`](analysis/analyze.py). The full figures are in [`analysis/results.json`](analysis/results.json), key `B3`.

### 2.1 `engine_vs_swetest`
- **500 of 500 engine values are exactly** `round(swetest value, 8 decimals)`, with zero exceptions. Every difference is the engine's 8-decimal display rounding. No calculation difference shows at the 11 decimals swetest prints.
- \|difference\| distribution: min 3.0e-11°, median 2.42e-9°, p95 4.70e-9°, p99 4.96e-9°, **max 4.999992e-9°** (Mercury). The theoretical maximum from rounding is 5e-9° + 5e-12° = 5.005e-9°. The largest observed difference is **0.50 × tolerance**.
- The maximum per body falls between 4.65e-9° and 5.00e-9° for every body. Lagna, Rahu and Ketu show no outlier.
- **Consequence.** The tolerance is justified by display quantisation alone, and that does not depend on date, place, latitude, retrograde motion or time zone. The basis recorded for KUN-01-SWISS-01 therefore holds for this matrix as well. One limit: a disagreement smaller than about 5e-9° cannot be detected through rounded output. That is about 3e-5 s of Moon motion (at about 1.6e-4° per second) and about 1e-6 s of Lagna motion.

### 2.2 `binding_vs_swetest` used as the boundary band
- Of 500 reference longitudes (planets, nodes and Lagna), exactly **one** lies within 1e-9° of a Pada edge: GOLD-E01's Moon, at 7.1e-10° from 120°. That is the designed exact-edge fixture.
- The next nearest is GOLD-B01b's Moon at **2.4e-4°**. Every band from 7.1e-10° to 2.4e-4° therefore gives the same result: only GOLD-E01 is indeterminate. A band below 7.1e-10° would make it decidable. **For this matrix, which value is chosen within that range does not change any classification.**
- The compiler allowance in the recorded basis is not observed in practice. Two independently built swetest binaries from the same `c69c14a` source agree byte for byte on all 50 receipts at 11 decimals. They are Claude's gcc 13 build (`400661cd…`) and the QA reviewer's gcc 14 build (`9ed78fdc…`). Both are `make swetest` defaults, whose `CFLAGS` carry no optimisation flag, so they match the `-O0` build named in the basis. The binding-against-build allowance itself is still exercised only by the SC and D3 suites, which compare the unrounded binding, and those suites pass.
- **Difference from the SC rule.** The SC rule resolves a near-edge case when the binding's unrounded value and the swetest value fall in the same segment. The gold harness cannot do that, because the schema has no unrounded field, so its treatment is more conservative. GOLD-E01 is indeterminate only for that reason: engine and reference both say Simha, Mesha, Magha 1.

### 2.3 Coverage, SC charts against the gold matrix

| | SC (18 charts) | Gold (50 charts) |
|---|---|---|
| Years | 1900 to 2100 | 1970 to 2100 (pre-1970 is now refused, SCI-03 Option B) |
| Latitude | −34.6° to +66.0° | **−66.0° to +66.0°** |
| \|lat\| > 60° | 1 | 3 |
| Southern hemisphere | 4 | 4 |
| Time zones | 6 | 10 |
| Designed boundary pairs (Moon, Sun, Lagna, nodes, retrograde) | 3 Moon cases | 20 pairs plus 1 exact edge |
| Future (after 2027-06-28) | 2 (SC-11, SC-22) | 18 (QUALIFIED) |

The gold matrix widens the coverage for every attribute except the pre-1970 years, which the product now refuses. Nothing in it falls outside the conditions under which the tolerance basis was argued.

## 3. Recommendation

**R (recommended): approve reusing both frozen values, unchanged, for the KUN-SCI-GOLD-001 matrix.** The approval should be recorded as an explicit scope extension: same values, same bases, and the evidence above as the written reason. No value changes, and the frozen `spec.json` is not edited.

| Option | Consequence |
|---|---|
| **R** Reuse 1e-8° and 1e-9° as frozen, with approval of the extended scope | Status quo results: 500 SWISS PASS and only GOLD-E01 BOUNDARY-INDETERMINATE. The decision record matches what the harness already does |
| A1 Reuse, and also amend the recorded basis of `binding_vs_swetest` to state that it serves here as a boundary band, with the observed gcc 13/gcc 14 agreement as evidence | Same results. It needs a new written reason and QA, because it edits the text of a frozen record |
| A2 Tighten `engine_vs_swetest` to about 5.1e-9° | Slightly more sensitive. The margin over rounding is only 2%, so the result could depend on float representation of the 8-decimal display. Not recommended |
| A3 Define separate gold-matrix tolerances | More records and the same numbers. It adds governance cost with no change in result |
| A4 Do not approve | The SWISS rows remain evidence under a tolerance borrowed without approval. Under REL-01 they cannot count toward the engineering gate |

## 4. Implementation implications if approved
Documentation only. Add a decision-register row ("B-3 scope extension of KUN-01-SWISS-01 tolerances to KUN-SCI-GOLD-001"). Optionally add a `tolerance_scope_approval` link in the gold report header in a later test-only PR. No engine, schema or report change.

## 5. Tests required after approval
- None beyond the existing suite.
- A rerun of the gold matrix on the approving SHA must confirm 500 PASS and the single BOUNDARY-INDETERMINATE.
- Any future change to these values or to their scope needs a new written reason, a new decision and QA.
