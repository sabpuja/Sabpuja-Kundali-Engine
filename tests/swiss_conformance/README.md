# Swiss integration conformance (KUN-01-SWISS-01)

This suite checks that Sabpuja's Python integration of Swiss Ephemeris gives
the same answers as the official standalone `swetest` utility. It uses the same
Swiss version, the same ephemeris files and the same calculation settings.

## Claim boundary

A PASS supports exactly one statement: *the Sabpuja Python integration agrees
with the tested Swiss Ephemeris CLI for the specified cases, versions and
options.*

`swetest` and the engine share the same Swiss C library. This is a
Swiss-on-Swiss oracle, **not** independent astronomy. A PASS says nothing about
astronomical accuracy, and it does not replace independent golden-chart QA.
It also does not verify historical Indian civil time: RG-HIST remains open.
All 24 cases are synthetic. None is a real birth.

## What is compared

Frozen spec: `spec.json`. Predeclared cases: `cases.json`.

| Check | Reference | Tolerance |
|---|---|---|
| UTC instant used by the engine | expected UTC in the case | exact |
| Julian day | independent Fraction formula (`oracle.gregorian_jd`) and swetest `UT:` line | 1e-9 day |
| Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, mean node: pyswisseph binding | swetest | 1e-9° |
| The same bodies as emitted by the engine (8-decimal display) | swetest | 1e-8° |
| Lagna (`houses_ex(..., b"P", FLG_SIDEREAL)` Ascendant) | swetest `-house<lon>,<lat>,P` Ascendant | same as above |
| Rashi, D9 rashi, whole-sign house, Moon Nakshatra/Pada | `oracle.py` (exact Fractions) applied to swetest values | category equality |
| Ketu | `Fraction(rahu) + 180` (self-consistency, not swetest) | 1e-8° |
| Refusals: DST gap, years 1899/2101, UTC-1899 via offset, polar Placidus | expected engine error code; polar also requires swetest to report the Placidus failure | exact |

All positions are geocentric apparent sidereal with Lahiri (`-sid1`), using
Swiss files only (`-i65538` for planets, `-i65536` for houses). This
reproduces the engine's flags exactly. Categories are always computed from
unrounded values.

A category check whose swetest longitude lies within 1e-9° of a Pada edge is
BOUNDARY-INDETERMINATE unless the binding value and the swetest value fall in
the same segment. SC-14 to SC-16 sit about a second either side of a sidereal
Moon 0° crossing to test this.

The rule oracle (`test_rule_oracle.py`) independently checks D1, Nakshatra,
Pada, D9 and whole-sign houses across all 108 Pada edges and their float
neighbours, a 20,000-point random sweep, the 0/360 wrap and the no-360.0 rule.
This rule conformance is reported separately from the numeric conformance.

## Verdicts

The verdicts are `SWISS-CONFORMANCE PASS`, `FAIL` and `BLOCKED`, with exit
codes 0, 1 and 2. Any FAIL makes the run FAIL. Otherwise any of the following
makes it BLOCKED:

- a BLOCKED or BOUNDARY-INDETERMINATE check;
- a dirty git tree;
- a pyswisseph or Swiss version mismatch;
- unverified ephemeris data;
- a set `SE_EPHE_PATH`;
- a missing swetest, or one with a bad receipt or SHA-256;
- a swetest warning (for example its silent Moshier fallback);
- malformed swetest output.

Engine errors are recorded as codes only. Paths in captured CLI output are
replaced by `<SWETEST>` and `<EPHE>`.

## Building swetest (not committed)

Build swetest from the official source at the same commit that supplies the
pinned ephemeris files:

```sh
git clone https://github.com/aloistr/swisseph.git swisseph-src
cd swisseph-src && git checkout c69c14adb7a0f94829586ffd92cd422aacb21e86
mkdir ../swetest-official && git archive HEAD | tar -x -C ../swetest-official
cd ../swetest-official && make swetest
./swetest -h | grep -m1 -i version   # must report 2.10.03
sha256sum swetest
```

Next to the binary, write a `receipt.json` that contains these keys:

- `swetest_sha256`: must match the binary;
- `source_repository`;
- `source_commit`;
- `build_command`;
- `compiler`;
- `license`;
- `swiss_version`.

Binaries and receipts stay outside Git.

The `libswe` bundled in the pyswisseph 2.10.3.2 sdist differs from c69c14a
only in code this suite does not use:

- `sweph.c`: the fixed-star parallax fix and an error-buffer size;
- `swephlib.c`: `split_deg` display rounding;
- eclipse and heliacal code;
- the DE441 constant and the default path in `swephexp.h`;
- comments.

A swetest built from that sdist gives identical results. The PR evidence
includes this cross-check.

## Running

The pinned data comes from `scripts/fetch_ephemeris.py` and is verified
against `data/ephemeris/MANIFEST.json`.

```sh
# Unit tests (no swetest needed); the integration class skips
python -m unittest discover -s tests

# With swetest: the integration class runs and must not skip
SABPUJA_TEST_EPHE_PATH=/path/to/ephe \
SABPUJA_TEST_SWETEST=/path/to/swetest \
SABPUJA_TEST_SWETEST_RECEIPT=/path/to/receipt.json \
python -m unittest discover -s tests

# Conformance report (needs a clean, committed tree)
python -m tests.swiss_conformance.run --swetest /path/to/swetest \
  --receipt /path/to/receipt.json --ephe /path/to/ephe --report-dir reports
```

The run writes `swiss-conformance-<sha12>-<stamp>.{json,csv,md}` to the
report directory, which is git-ignored. The JSON report includes:

- signed differences;
- every swetest argv, with redacted stdout and stderr and the exit code;
- the swetest SHA-256 and receipt;
- the binding and library versions;
- the git state.

## Recorded findings from the deliberate-mismatch tests

- `SEFLG_NONUT` has no effect on Swiss sidereal positions, so the suite cannot
  detect it. `SEFLG_NOABERR` is used instead as the "wrong flag" probe.
- swetest's `Ascendant` line is the same for `P` and `W`, so the house-system
  letter cannot be observed through the lagna. The suite detects a wrong
  location or a tropical houses call.

## Rollback

The suite is test-only and self-contained. To roll it back, delete
`tests/swiss_conformance/`. No engine, data or manifest file is touched.
