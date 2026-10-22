# KUN-02: scientific method finalization and birth-time accuracy

**Work package:** CLAUDE / KUN-02, first phase (investigation, deterministic probes, recommendations)
**Base:** `feat/initial-kundali-foundation-20261021` at `d8193c692d52aa12595f81c227638a061605a3d9`
**Status:** RECOMMENDATIONS ONLY. Every SCI decision except the owner-approved SCI-01b and SCI-01c stays **PENDING** until ChatGPT QA and the owner record it in `main:docs/DECISIONS.md`.

No production calculation code is changed by this package. Everything here is test-only code under `tests/kun02/` and documentation under `docs/kun02/`. All inputs are synthetic.

## Documents

| Document | Workstream | Contents |
|---|---|---|
| [lagna-p-vs-w.md](lagna-p-vs-w.md) | A | `houses_ex(..., b"P")` versus `b"W"`: exact results, known differences, edge cases, recommended method |
| [birth-time-report.md](birth-time-report.md) | B | Local time → IANA → UTC → UT1/TT pipeline, historical Indian clocks, risks and safeguards |
| [supported-envelope.md](supported-envelope.md) | C | Date window and latitude band, refusal boundaries and proposed deterministic codes |
| [sci-decision-matrix.md](sci-decision-matrix.md) | D | Recommendation, alternatives, references, consequences, evidence and implications for SCI-01a, d–h, SCI-02, SCI-03 |
| [implementation-plan.md](implementation-plan.md) | all | Prioritized, independently reviewable code packages, each gated on a named decision |

## Claim boundary

The probes produce four kinds of evidence, and every result in the reports is labelled with one of them:

| Class | Meaning | What it can support |
|---|---|---|
| `SWISS_CONFORMANCE` | Swiss Ephemeris compared with itself through another call, flag or house system | Two Swiss paths are equivalent. **Not** astronomical accuracy. |
| `INDEPENDENT_MATHEMATICS` | Our own formula (spherical trigonometry, IERS 2010 sidereal time, exact rationals) applied to definitions or to Swiss inputs | The Swiss output is what the stated geometry or definition implies. Independent of Swiss code, not of Swiss inputs. |
| `TIMEKEEPING` | Civil-time and time-scale behaviour against transcribed IANA tz 2026e and IERS leap-second records | Our conversion matches those records. It does **not** prove what clock a historical birth was recorded on. |
| `ENGINE_BEHAVIOUR` | What the current production engine accepts or refuses | Current behaviour only. |

Nothing here is an independent astronomical-accuracy certification, a golden-chart validation or a historical-clock verification. RG-HIST remains open.

## Reproducing

Prerequisites are the same as the foundation: Python ≥ 3.11, `pyswisseph==2.10.3.2`, the pinned `sepl_18.se1` and `semo_18.se1` from `aloistr/swisseph@c69c14a` (see `data/ephemeris/README.md`), and `SE_EPHE_PATH` unset. Optionally install `tzdata==2026.5` so the system/package comparison runs.

```bash
pip install -e . && pip install tzdata==2026.5
export SABPUJA_TEST_EPHE_PATH=/srv/sabpuja/ephe     # verified pinned files

# Full suite: existing foundation tests + KUN-02 tests (0 skipped expected)
python -m unittest discover -s tests -v 2>&1 | tee kun02-tests.log

# Evidence run: JSON + Markdown report with provenance; exit 0 PASS, 1 FAIL, 2 BLOCKED
python -m tests.kun02.run --ephe "$SABPUJA_TEST_EPHE_PATH" --report-dir reports/

# Deliberately wrong configurations (each must exit 2, BLOCKED)
python -m tests.kun02.run --ephe ""                         # EPHEMERIS_PATH_MISSING
python -m tests.kun02.run --ephe /tmp/empty-dir             # EPHEMERIS_FILE_MISSING
SE_EPHE_PATH=/tmp python -m tests.kun02.run --ephe "$SABPUJA_TEST_EPHE_PATH"   # EPHEMERIS_PATH_OVERRIDE
```

The runner refuses to report PASS from a dirty Git tree. Its report records the Git SHA, Python, pyswisseph and Swiss versions, the Swiss tidal acceleration, each ephemeris file's SHA-256 against the manifest, the tzdata source and version actually used by `zoneinfo`, and the PyPI tzdata version.

## Code map (all test-only)

| Path | Role |
|---|---|
| `tests/kun02/common.py` | Evidence classes, engine-identical Swiss configuration and Julian day |
| `tests/kun02/provenance.py` | Git, Python, Swiss, ephemeris checksums, tzdata source/version |
| `tests/kun02/lagna_probe.py` | Workstream A probes |
| `tests/kun02/time_probe.py` | Workstream B probes |
| `tests/kun02/envelope_probe.py` | Workstream C probes |
| `tests/kun02/run.py` | Runner, 16 predeclared invariants, reports |
| `tests/kun02/test_kun02.py` | The same probes as unit tests |
| `tests/kun02/fixtures/lagna_grid.json` | Synthetic places, instants, random-sample seeds, engine cases |
| `tests/kun02/fixtures/time_cases.json` | 63 synthetic time cases with hand-derived expected behaviour and proposed outcome |
| `tests/kun02/fixtures/iana_zone_transcriptions.json` | Hand transcription of 7 IANA 2026e South Asian Zone entries (source SHA-256 recorded) |
| `tests/kun02/fixtures/iers_leap_seconds.json` | IERS leap seconds transcribed from tz 2026e `leap-seconds.list` (SHA-256 recorded, expires 2027-06-28) |

## Predeclared invariants

| ID | Claim | Class |
|---|---|---|
| A1 | Where `b"P"` returns, its ascendant, MC and ARMC equal `b"W"` bit for bit | Swiss conformance |
| A2 | `b"W"` never refuses, including beyond the polar circle | Swiss conformance |
| A3 | `b"P"` refuses on every sample at or beyond the polar circle and on none equatorward of it | Swiss conformance |
| A4 | `b"P"` failure latitude equals 90° − true obliquity (within 1e-6″) | Swiss conformance + source reading |
| A5 | Sidereal ascendant = tropical ascendant − true Lahiri ayanamsha (within 1e-6″) | Swiss conformance |
| A6 | Independent spherical-trigonometry ascendant agrees within 1e-3″; same point equatorward of the polar circle | Independent mathematics |
| A7 | `b"W"` ascendant is always the eastern rising point, \|altitude\| < 1e-6″ | Independent mathematics |
| A8 | `b"W"` cusps are exact multiples of 30° from the Lagna Rashi | Swiss conformance |
| A9 | Every Lagna Navamsa crossing in a full-day sweep is consistent on both sides | Swiss + independent mathematics |
| A10 | D1/D9 houses from rules, W cusps and the classical Navamsa rule agree; P and W categories agree | Swiss + independent mathematics |
| A11 | Wrong Swiss configurations are detectable | Swiss conformance |
| A12 | Every fixture engine case returns a full chart with exactly the expected fields, all equal to `b"W"`; the polar case is refused with `ASCENDANT_UNCOMPUTABLE` today | Engine behaviour |
| B1 | Every synthetic time case behaves as derived by hand | Engine behaviour + timekeeping |
| B2 | `zoneinfo` equals the independent IANA 2026e transcription for 7 zones | Timekeeping |
| B3 | Swiss leap seconds equal the IERS list; UT1−UTC *implied under the Swiss ΔT model* stays within 0.9 s for 1972–2026 (model consistency, not measured UT1) | Timekeeping |
| C1 | All bodies use Swiss files at both UTC extremes of the local-date window | Swiss conformance |

## Most important findings

1. **P and W give the same ascendant.** On 167,612 synthetic comparisons, wherever Placidus is defined, the ascendant, MC and ARMC from `b"P"` and `b"W"` are bit-identical. The ascendant does not depend on the house system in Swiss Ephemeris; the house letter only decides whether the call fails.
2. **Placidus refusal is a date-dependent latitude rule.** `b"P"` raises exactly when \|lat\| ≥ 90° − true obliquity of date, which moves between 66.5467° and 66.5752° over 1900–2100. So 66.55° is refused in 1900 and accepted in 2100 today.
3. **W beyond the polar circle returns the rising point.** A naive ascendant formula gives the setting point in about 32% of samples beyond the polar circle; Swiss `b"W"` always returns the eastern rising point (independently verified).
4. **Swiss global state can leak.** After `SIDBIT_PREC_ORIG` is used, `set_sid_mode(SIDM_LAHIRI)` alone does not restore the default; `set_ephe_path` does. The engine already calls both on every request under its lock, and a new test pins that.
5. **Swiss sidereal time has a −1.908″ step at 2050-01-01 0h UT** (model switch); the Lagna steps by about −1.7″ at New Delhi at that instant. Negligible against birth-time precision, but inside the proposed window. This is version-specific behaviour of the pinned Swiss 2.10.03, not an observation-based accuracy finding.
6. **The engine's date rule uses the UTC year, not the local date**, so local 1900-01-01 00:00 in Asia/Kolkata (UTC 1899-12-31) is refused and local 2101-01-01 05:29:59 IST (UTC 2100-12-31) is accepted.
7. **Historical Indian clocks cannot be inferred.** IANA models railway time for Asia/Kolkata. A 1930 Mumbai reading entered as IST is accepted. In the hypothetical scenario that the clock was really on Mumbai local mean time (a sensitivity case, not a documented record), that is a 38.5-minute error, which moves the Lagna by up to 13.8° and changes its Rashi in 33% of sampled instants.
8. **Host tzdata decides historical results.** Ubuntu's tzdata 2026e and PyPI tzdata 2026.5 (same IANA release) disagree for 8 Asian zones before 1956, because one build includes IANA `backzone` data. Asia/Kolkata agrees in both.
9. **Birth-time precision dominates every astronomical convention.** One minute of clock error changes the Lagna Navamsa in 7.7% of sampled Indian charts; 0.9 s (the UT1−UTC limit while the current IERS rule stands; CGPM 2022 Res. 4 raises it in or before 2035) changed no category in 2,000 samples.
