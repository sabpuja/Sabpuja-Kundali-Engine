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
| PAN-QA-08 | v1: the preserved PR #62 baseline equals the 6722b5c git objects. v2 (KUN-I18N-INT-001): the other 210 v1 files byte-identical, the 12 declared bilingual changes and 55 declared additions exactly as in PR #61 fee3967, nothing undeclared; charts byte-identical with and without Panchanga; Nakshatra identity | Hindi editorial approval |
| PAN-QA-09 | Same refusals, codes, text and order as the chart; typed Panchanga refusals; no birth data in errors, logs or CLI output | — |
| PAN-QA-10 | Identical output across runs, processes, locales, host time zones, threads and foreign Swiss state | — |

## Typed Panchanga refusals (draft M1 machine contract only)

All chart refusals come first, unchanged in code, text and order. Then:

| Code | When |
|---|---|
| `PANCHANGA_TRANSITION_NOT_CONVERGED` | Any search cap reached, no sector change within 2.5 days, a non-finite value, or a failed whole-second verification. Also, before any computation, a `limits` override looser than the frozen D09-A-M1 values (extent > 2.5 days, iterations > 64, bracket > 0.5 s), a bracketing step other than exactly 6 h (D10-A; a smaller step would multiply Swiss calls without bound, QA review 5751704671), or malformed (not a `SearchLimits`, non-int, bool, non-positive, or a negative iteration cap). No separate code is added for this (KUN-PAN-M1-ENG-001A). Stricter extent, iteration and bracket overrides are allowed for failure injection; the method block then reports the limits actually used, so it never claims a limit that did not govern the calculation |
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
rounded-down whole second, an ignored iteration cap, unenforced frozen limits and a step
check that accepts steps below 6 h;
each must be caught.

## Files

| Path | Role |
|---|---|
| `oracle.py` | Independent rational rules (standard library only; edge bisection, no floor division of scaled values) |
| `checkers.py` | Independent document and rule checkers used by the gates and the mutation controls |
| `phase_events.py` | PAN-QA-04 evaluator |
| `swiss_conformance.py` | PAN-QA-07 evaluator: receipt-verified swetest, independent bisection (1 h steps, 1 ms) |
| `baseline-hashes.json` | SHA-256 of 222 chart, renderer, prototype, preview and existing test files at PR #62 |
| `identity-manifest-v2.json` | PAN-QA-08 v2: the 12 intentionally changed v1 paths (v1 and v2 SHA-256, v2 git blob) and the 55 added paths of the bilingual integration, bound to the v1 file by its SHA-256 |
| `identity_v2.py` | v2 loader, validator, working-tree and exact-commit verifier, and deterministic generator (`python -m tests.panchanga.identity_v2 --check`) |
| `identity-manifest-v3.json` | PAN-QA-08 v3 (KUN-I18N-INT-001A): the one v2 path the HTTP report repeatability fix changes and the one regression test it adds, bound to v1/v2 by SHA-256 and to the audited v2 commit `be608d8` |
| `identity_v3.py` | v3 validator, overlay tree check and exact-commit check (`python -m tests.panchanga.identity_v3 --check`) |
| `identity-manifest-v4.json` | PAN-QA-08 v4 (KUN-I18N-COPY-005): the 25 paths the owner-approved copy Changes A and B change (previous and new SHA-256), the 2 new copy tests and the exact editorial-packet inventory, bound to v1/v2/v3 by SHA-256 and to main `7fc1702` |
| `identity_v4.py` | v4 validator, overlay tree check and exact-commit check (`python -m tests.panchanga.identity_v4 --check`) |
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

## PAN-QA-08 identity versions (KUN-I18N-INT-001)

`baseline-hashes.json` (v1, SHA-256 `2e913eda…007e`) is never edited or regenerated. It
remains the acceptance record for the PR #62 / PR #68 base and is checked against the
git objects of `6722b5c`. The bilingual integration of PR #61 `fee3967` (with #59 and #60)
changes 12 of its 222 files on purpose, so the working-tree assertion now runs through
`identity-manifest-v2.json` (SHA-256 `d2dea049…87da`). Both SHA-256 values are pinned in
`identity_v2.py`, so any change to either manifest is a code change that review sees.

v2 refuses: a substituted or edited v1 file, a manifest that fails its pin, is not JSON,
has duplicate or extra keys, wrong counts, unsorted or unsafe paths, a v1 hash that
differs from the baseline, a "modified" entry that does not change or is not a v1 file,
an "added" entry that already exists in v1; and in the tree, any missing file, any
unexpected hash, any undeclared change to one of the 210 files and any undeclared file
in the v1 scope (the PR #68 Panchanga package stays confined to
`src/sabpuja_kundali/panchanga/` as before). `test_pan_qa08_identity_v2.py` seeds each
defect. The exact-commit checks need a clone with history back to `6722b5c`
(`git fetch --depth=200 origin <branch>` is enough); without it they fail, not skip.

### v3 (KUN-I18N-INT-001A)

v2 is kept byte for byte and is now proved on the exact tree of the commit it was
independently audited with, `be608d8`. The HTTP report repeatability fix changes one v2 path
(`prototype/kundali_prototype/server.py`: the PDF render slot is released before the response
is written) and adds one regression test (`prototype/tests/test_report_slot_release.py`).
`identity-manifest-v3.json` (SHA-256 `9a2051d9…0e77`, pinned in `identity_v3.py`) declares
exactly those two paths; the paths themselves are fixed in code as the only ones the task
authorizes. The working-tree check is the v2 check with the v3 overlay, so every other v2
expectation (210 unchanged v1 files, 11 other modified files, 55 added files) still holds,
and `be608d8..HEAD` inside the v1 scope must equal the v3 declaration.
`test_pan_qa08_identity_v3.py` seeds the v3 defects.
Since KUN-I18N-COPY-005, v3 is proved, unchanged, on the exact trees of `85f6a89` and `7fc1702`.

### v4 (KUN-I18N-COPY-005)

v1, v2 and v3 are kept byte for byte (their SHA-256 values stay pinned in code). The owner-approved
copy Changes A (English PDF page 10, `report_i18n.json` `method.exc5`) and B (web D9 footnote,
`i18n.json` `ui.d9.footnote` and the `index.html` fallback) change a fixed set of 25 already-pinned
paths: both catalogs, the HTML fallback, the 26 English PDF pins in `test_premium_name.py`, and 21
files of the editorial review packet (register re-pinned to the new reviewed source, regenerated
English sample PDF, page-10 image and result screenshots, documents and manifest). They add two
copy tests in the v1 scope and one blank owner attestation form in the packet.
`identity-manifest-v4.json` (pinned in `identity_v4.py`) declares exactly those paths, each with the
SHA-256 it had before (which must equal its v1/v2/v3 expectation) and its new SHA-256 and git blob,
plus the exact inventory of `docs/i18n/review/kun-i18n-003/`. The authorized path list is fixed in
code. The working-tree check is v1/v2/v3 with the v4 overlay: the 209 v1 files no version touches stay
byte-identical, and no undeclared file may appear in the v1 scope or in the packet. A signed sheet
under `signed/`, an edited attestation form or any other packet change is refused, so a later
signed-decision intake needs its own versioned overlay; v4 pre-approves no signature.
`7fc1702..HEAD` restricted to the v1 scope, the v2/v3-declared paths and the packet must equal the v4
declaration, and `7fc1702` itself must satisfy v3. `test_pan_qa08_identity_v4.py` seeds the v4 defects.
