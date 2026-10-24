# KUN-03 Swiss conformance reconciliation (profile KUN-03-current v1)

The PR #18 framework (KUN-01-SWISS-01) is imported unchanged, except for one
test. `spec.json` and `cases.json` are byte-identical to PR #18 at 66692d7 and
keep their SHA-256 pins in `inputs.py`. The KUN-03 engine changed what some of
the frozen requests should do. Those expectations live in a separately versioned
overlay, `profiles/kun03-current-v1.json`, which `profile.py` pins by SHA-256 and
validates field by field. Any missing or changed case, code, count, house letter
or hash makes the run SWISS-CONFORMANCE BLOCKED before the engine or swetest runs.

## Claim boundary

This is Swiss-on-Swiss integration conformance against the official swetest
CLI (aloistr/swisseph@c69c14a, Swiss 2.10.03, pyswisseph 2.10.3.2, pinned
`.se1` files) for these 24 synthetic requests.

It is not:

- independent astronomical validation;
- mathematical verification of the algorithms;
- historical clock verification.

The historical-numerics supplement runs with a test-only override of the
historical clock gate (P8 G1). It checks Swiss numerics only and is never
production acceptance.

## Three parts, one verdict

| Part | What runs | Expected on the KUN-03 engine |
|---|---|---|
| Archival | The unchanged PR #18 runner, spec and cases: Placidus reference, generic `INPUT_REFUSED`. | FAIL at exactly SC-09, SC-17, SC-18 and SC-23, with the reasons pinned in `profile.ARCHIVAL_DIVERGENCE`. Every other case passes: 16 charts × 49 = 784 checks, 32 self-consistency checks. |
| Current | The same 24 requests with overlay expectations, against a whole-sign (W) swetest and binding reference. | 24 cases: 16 charts and 8 refusals. 784 comparison checks, 32 self-consistency checks, 64 house-method checks, 16 refusal checks and 4 Placidus reference observations. |
| Historical supplement (TEST-ONLY) | SC-09 and SC-23 with `engine.HISTORICAL_CLOCK_GATE = ()` in this process only. Restoration is checked by refusing again. | 98 comparison checks, 4 self-consistency checks and 8 house-method checks. |

The final verdict is the worst of current, supplement and reconciliation.

Reconciliation passes only when both of these hold:

- The archival run diverges exactly as recorded and nowhere else.
- Each of the 16 current charts has the same 49 named checks in both profiles, with identical engine and binding values, PASS in both.

A missing swetest, an invalid receipt, unverified data, a dirty tree or
`SE_EPHE_PATH` blocks every part. A skipped reference never yields PASS.

## Differences from PR #18

| Case | PR #18 (archival) | Current | Source | Why |
|---|---|---|---|---|
| SC-07 | refuse `INPUT_REFUSED` | refuse `TIME_NONEXISTENT_LOCAL` | P5, PR #27 | Same refusal, typed code. |
| SC-09 | chart | refuse `HISTORICAL_CLOCK_UNVERIFIED` | P8, PR #28 | Local date 1900-01-01 is before 1970. The numerics are kept in the supplement. |
| SC-10 | refuse `INPUT_REFUSED` | refuse `DATE_OUTSIDE_SUPPORTED_RANGE` | P4, PR #26 and P5, PR #27 | Same refusal, by local date, typed code. |
| SC-12 | refuse `INPUT_REFUSED` | refuse `DATE_OUTSIDE_SUPPORTED_RANGE` | P4, PR #26 and P5, PR #27 | Same refusal, by local date, typed code. |
| SC-13 | refuse `INPUT_REFUSED` (UTC year 1899) | refuse `HISTORICAL_CLOCK_UNVERIFIED` | P4, PR #26 and P8, PR #28 | The local date 1900-01-01 passes the window, and the pinned Etc/GMT-3 offset +03:00 matches. The historical gate is the first refusal in P5 order: a wrong offset gives `TIME_OFFSET_MISMATCH` first. |
| SC-17 | refuse `ASCENDANT_UNCOMPUTABLE` (Placidus) | refuse `LATITUDE_OUTSIDE_SUPPORTED_BAND` | P2, PR #24 and P3, PR #25 | +70° is outside the fixed ±66° band, refused before the ephemeris check and any Swiss call. The Placidus failure is kept as a reference observation. |
| SC-18 | refuse `ASCENDANT_UNCOMPUTABLE` (Placidus) | refuse `LATITUDE_OUTSIDE_SUPPORTED_BAND` | P2, PR #24 and P3, PR #25 | As SC-17, at −75°. |
| SC-23 | chart | refuse `HISTORICAL_CLOCK_UNVERIFIED` | P8, PR #28 | Local date 1950-06-15 is before 1970. The numerics are kept in the supplement. |
| Lagna reference | swetest `-house<LON>,<LAT>,P`, binding `b"P"` | swetest `-house<LON>,<LAT>,W`, binding `b"W"` | P3, PR #25 (SCI-01e) | The engine's Lagna vehicle is the whole-sign call. |
| Counts | 24 cases (18 charts, 6 refusals), 882 checks, 36 self-consistency | 24 cases (16 charts, 8 refusals), 784 checks, 32 self-consistency | | Two charts became refusals. No eligible chart lost a check. |

Tolerances, bodies, flags, swetest switches for planets, the oracle, the
parser, receipt validation and every negative gate are unchanged.

The one edited PR #18 file is `test_swetest_integration.py`. There,
`test_every_predeclared_case_conforms` still requires PASS for 20 cases and
now requires the recorded FAIL for the other four.

## Whole-sign proof

Placidus and whole sign print the same Ascendant line (a PR #18 finding), so
the Lagna value cannot show the house letter. Each current chart has four
house-method checks that can:

1. `engine_houses_ex_call`: the engine's recorded call is exactly `houses_ex(jd, lat, lon, b"W", FLG_SIDEREAL)`, once.
2. `swetest_house_system_letter`: swetest's header reads `Houses system W (equal/ whole sign)`.
3. `swetest_whole_sign_cusps`: house n is exactly `((floor(asc / 30) + n − 1) mod 12) × 30`.
4. `binding_vs_swetest_cusps`: the binding's W cusps match swetest within the binding tolerance.

The tests show:

- A Placidus swetest reference fails checks 2–4, while all 49 comparison checks still pass.
- An engine compiled with `b"P"` fails check 1 alone.

## Running

```
python -m tests.swiss_conformance.run_current --swetest <swetest> --receipt <receipt.json> --ephe <ephe> --report-dir reports/
```

This writes JSON, CSV and Markdown reports. The exit codes are:

| Exit | Meaning |
|---|---|
| 0 | PASS |
| 1 | FAIL |
| 2 | BLOCKED |

The archival runner (`python -m tests.swiss_conformance.run`) stays as it was.
On the KUN-03 engine it exits 1, with the recorded divergence.

## KUN-03 D3: location-based timezone profile

D3 refuses `UTC`, `GMT`, every `Etc/*` key and their aliases with
`TIMEZONE_NOT_LOCATION_BASED` (`docs/api-contract.md`, "Birthplace timezone
policy"); zone policy version 2 (owner Option B, PR #20 comment 6377855934) also
refuses `CST6CDT`, `EST5EDT`, `MST7MDT` and `PST8PDT`. The files above, profile v1
included, stay byte-identical; profile v1 now describes the PR #33 timezone
policy. The active D3 profile `profiles/kun03-d3-v2.json` (SHA-256
`a9aa1a4b85714bfb7167acba93a1ce70f107add44d51face655f07053961e5e7`, module
`d3.py`) records every case with its v1 and D3 outcome. The D3 profile v1
`profiles/kun03-d3-v1.json` (SHA-256
`942a0eac0a18b45f26de91b238d0b5b3868713076a4a50e457598b1fa999b980`, zone policy
version 1, QA PASS at `8b6507b`) is archived unchanged: no frozen request uses the
four US-rules names, so v2 must equal v1 in every case, count, continuation and
divergence field, and its `lineage` block records the policy delta (four names
added, seven abbreviation-style names kept, no case affected). Each run also
reproduces the archived version 1 policy in a test-only, versioned context
(engine outcomes of the 24 requests, no Swiss comparison) and checks that
version 2 is restored afterwards. The counts are the same under both versions:

- 7 charts (343 comparison checks) and 17 refusals. Nine former UTC charts
  (SC-01, 04, 11, 14, 15, 16, 19, 20, 24) and six former refusals (SC-09, 10, 12,
  13, 17, 18) now stop at D3.
- Numeric continuation keeps all 784 v1 comparison checks. SC-01, SC-04 and
  SC-24 run in production as geographic equivalents (same UTC instant and
  coordinates, verified offset), each proven equal to its original request. SC-11,
  SC-14, SC-15, SC-16, SC-19 and SC-20 run their original requests with a
  test-only D3 bypass, because no geographic zone gives the same instant inside
  the window or the point is open ocean.
- The historical supplement keeps SC-09 (gate and D3 bypassed) and SC-23 (gate
  bypassed), test-only.
- The unchanged v1 runner and the archival PR #18 runner must diverge from the
  D3 engine exactly as the profile records (15 cases plus the SC-09 supplement
  for v1; 13 cases for the archival run).

```
python -m tests.swiss_conformance.run_d3 --swetest <swetest> --receipt <receipt.json> --ephe <ephe> --report-dir reports/
```

Exit 0 PASS, 1 FAIL, 2 BLOCKED. `run_current` on the D3 engine exits 1 with
that v1 divergence; its unit tests reproduce the PR #33 policy with the
test-only D3 bypass.
