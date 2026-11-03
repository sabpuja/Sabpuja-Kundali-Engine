# KUN-PAN-M1 Panchanga birth-instant engine: tests and gate runner

Engineering acceptance for `src/sabpuja_kundali/panchanga/` (`sabpuja-panchanga/1`),
issue #67. Machine output only; not customer-facing. Decisions implemented:
D01-A, D02-M1, D07-A, D08-A, D09-A-M1, D10-A (TS-1 only), D12-A, D13-A, D14-A-M1,
D15-a-R, D15-b-R, D16-M1-INDEX, D18-A, D20-M1-SCOPED (adopted at `main` 25cfde4).

`tolerances.json` (commit b3883ba) and the phase fixture (commit d8d487a) were
frozen before any numerical run. Every test reads them through a byte-exact
SHA-256 check (`common.py`); nothing here may edit them.

## Claim boundary

| Gate | A PASS means | It does not mean |
|---|---|---|
| PAN-QA-01 | Sector rules equal an independent exact-rational oracle on every edge, its float neighbours, the 0/360 wrap and a 20,000-pair sweep | Anything about the longitudes |
| PAN-QA-03 | TS-1 search: 6 h steps, at most 2.5 days each way, at most 64 iterations, bracket at most 0.5 s, first whole second in the new sector, typed refusal otherwise | Accuracy of the instants |
| PAN-QA-04 | All 50 rechecked USNO/NASA phase events fall inside [earliest minute - 60 s, latest minute + 60 s] | Seconds-level astronomical accuracy; Yoga or Nakshatra end times |
| PAN-QA-07 | Engine equals the official swetest 2.10.03 within the D15-b thresholds, and every transition equals an independent swetest bisection within 1 s | Independent astronomy (Swiss-on-Swiss) |
| PAN-QA-08 | Chart engine, renderer and harness files byte-identical to PR #62; charts byte-identical with and without Panchanga; Nakshatra identity | — |
| PAN-QA-09 | Same refusals, codes, text and order as the chart; typed Panchanga refusals; no birth data in errors, logs or CLI output | — |
| PAN-QA-10 | Identical output across runs, processes, locales, host time zones, threads and foreign Swiss state | — |

## Typed Panchanga refusals (draft M1 machine contract only)

All chart refusals come first, unchanged in code, text and order. Then:

| Code | When |
|---|---|
| `PANCHANGA_TRANSITION_NOT_CONVERGED` | Any search cap reached, no sector change within 2.5 days, a non-finite value, or a failed whole-second verification. Also, before any computation, a `limits` override looser than the frozen D09-A-M1 values (step > 6 h, extent > 2.5 days, iterations > 64, bracket > 0.5 s) or malformed (not a `SearchLimits`, non-int, bool, non-positive, or a negative iteration cap). No separate code is added for this (KUN-PAN-M1-ENG-001A). Stricter overrides are allowed for failure injection; the method block then reports the limits actually used, so it never claims a limit that did not govern the calculation |
| `PANCHANGA_CHART_IDENTITY_FAILED` | The session's birth-instant longitudes do not reproduce the chart's Moon Nakshatra/Pada and 8-decimal Sun and Moon. An internal fail-closed safety check, accepted by QA review 5751031274 for the draft M1 machine contract only. It is not customer-facing error copy and changes no chart code; a public error schema needs its own integration review |

Both have fixed text, no birth data or instants, and no exception chain.

## Search note: more than one edge in a 6 h step

ENGINEERING-SPEC section 5 says each 6 h bracket contains exactly one crossing. That
holds for Tithi, Karana, Yoga and Nakshatra, but **not for Pada**: the Moon moves up to
about 3.85 deg in 6 h against a 3.33 deg Pada, so one step can cross two Pada edges.
The search does not rely on a single crossing. It bisects on membership of the birth
sector, which the monotonic Moon leaves exactly once within the extent, so it always
returns the first exit (the end) or the last entry (the start).
`test_two_edges_in_one_step_returns_the_first` covers this, and QA independently
reproduced it; no method change.

`test_mutations.py` seeds the defects listed in ENGINEERING-SPEC section 9 (tropical S,
sign error in E, closed edge, missing `FLG_SWIEPH` check, extrapolation) plus a
rounded-down whole second, an ignored iteration cap and unenforced frozen limits;
each must be caught.

## Files

| Path | Role |
|---|---|
| `oracle.py` | Independent rational rules (standard library only; edge bisection, no floor division of scaled values) |
| `checkers.py` | Independent document and rule checkers used by the gates and the mutation controls |
| `phase_events.py` | PAN-QA-04 evaluator |
| `swiss_conformance.py` | PAN-QA-07 evaluator: receipt-verified swetest, independent bisection (1 h steps, 1 ms) |
| `baseline-hashes.json` | SHA-256 of 222 chart, renderer, prototype, preview and existing test files at PR #62 |
| `run.py` | Full numerical gate run, JSON and Markdown report; exit 0 PASS, 1 FAIL, 2 BLOCKED |

## Reproduce

```bash
export PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=$PWD/src:$PWD/prototype
export SABPUJA_TEST_EPHE_PATH=/abs/ephe SABPUJA_TEST_SWETEST=/abs/swetest SABPUJA_TEST_SWETEST_RECEIPT=/abs/receipt.json
unset SE_EPHE_PATH
python -m unittest discover -s tests -v            # whole engine suite incl. tests/panchanga; 0 skipped expected
python -m tests.panchanga.run --report-dir reports/ # PAN-QA-04 and full PAN-QA-07; exit 0 expected
echo '{"birth_datetime":"2026-01-03T13:00:00+05:30","timezone":"Asia/Kolkata","latitude":28.6,"longitude":77.2}' \
  | SABPUJA_EPHE_PATH=$SABPUJA_TEST_EPHE_PATH python -m sabpuja_kundali.panchanga
```

Without `SABPUJA_TEST_EPHE_PATH` the real-data classes skip (existing convention);
once it is set, wrong or incomplete data fails instead of skipping. The swetest
classes also need `SABPUJA_TEST_SWETEST`.
