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
- a `spec.json` or `cases.json` that fails validation (see below);
- a run that does not deliver the frozen coverage: all 24 cases in order, the
  49 named checks for each of the 18 chart cases (882 in all) and 2
  self-consistency checks per chart case;
- a dirty git tree;
- a pyswisseph or Swiss version mismatch;
- unverified ephemeris data;
- a set `SE_EPHE_PATH`;
- a missing swetest, or one whose receipt is missing, incomplete, names an
  unapproved source or version, or does not match the binary's SHA-256;
- a swetest warning (for example its silent Moshier fallback);
- malformed swetest output.

### Frozen inputs

`inputs.py` holds the frozen policy, and the runner checks both input files
against it before it calls the engine or swetest:

- **Byte-exact SHA-256.** Both files must match the SHA-256 pinned in
  `inputs.py`. Each report records the hash and size of both files.
- **Strict JSON.** These are rejected:
  - `NaN`, `Infinity` or `-Infinity`;
  - a number that overflows to infinity (for example `1e400`);
  - duplicate keys;
  - a file over 1 MiB.
- **Spec checks.** These must be exactly as frozen:
  - every key and its type;
  - the schema string and FROZEN status;
  - the claim-boundary marker;
  - the required versions;
  - the swetest switches (they must equal the arguments the runner uses);
  - the bodies, names and verdict codes.
- **Tolerance checks.** Every tolerance must be a finite float with
  0 < value ≤ 1e-6, and must equal its frozen value. A tolerance cannot be
  widened or narrowed silently.
- **Case checks.** The exact predeclared case IDs must appear, in order. The
  checks cover:
  - each case's type (chart, or the exact expected refusal);
  - the exact keys of each case;
  - finite latitude and longitude within range.

  Duplicate, missing, extra, renamed or retyped cases are rejected.

Any failure gives SWISS-CONFORMANCE BLOCKED (exit 2), with error codes only.
`numeric()` itself returns BLOCKED for a non-finite, non-positive, boolean or
oversized tolerance, and for a non-finite or non-numeric value. This includes
an integer too large to convert to a float, such as a 401-digit latitude. Such
a value is reported by its type only, never by the raw value.

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

Every field must be a non-empty string. The receipt's
`(source_repository, source_commit)` must be one of the approved sources in
`inputs.py`:

- the official `https://github.com/aloistr/swisseph` at
  `c69c14adb7a0f94829586ffd92cd422aacb21e86`, which is the reference build;
- the pyswisseph 2.10.3.2 sdist `libswe`, identified by the sdist's SHA-256.
  This is labelled in every report as a cross-check build, NOT the official
  source.

`swiss_version` must be `2.10.03`.

A receipt is the builder's testimony plus the binary's SHA-256. It is not
cryptographic proof that the binary was compiled from that source. The raw
build commands and the source diff are kept with the QA evidence for human
audit.

Binaries and receipts stay outside Git.

The verdict uses the official build. As a cross-check, a second swetest was
built from the `libswe` sources bundled in the pyswisseph 2.10.3.2 sdist. Those
library sources differ from c69c14a only in places this suite does not use:

- `sweph.c`: the fixed-star parallax fix and an error-buffer size;
- `swephlib.c`: `split_deg` display rounding;
- eclipse and heliacal code (`swecl.c`, `swehel.c`);
- the DE441 constant and default path in `swephexp.h`;
- K&R-style `()` prototypes, platform macros and comments (`swemmoon.c`,
  `swejpl.c`, `sweodef.h`, `swehouse.c`, `sweph.h`).

The `swetest.c` front ends differ more: help text, an asteroid-search option
and planet-list handling. Neither change touches the switches used here.
`swevents.c` is unsupported and not compiled into swetest. Both builds gave
identical case results. The PR evidence includes the full diff.

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
