# KUN-02 Phase 2: evidence and reference map

**Status:** supporting document for the PROPOSED decisions in [KUN-02-P2-decision-package.md](KUN-02-P2-decision-package.md). It records where each piece of evidence lives, who reviewed it, and what it does **not** show. **Update 2026-10-24:** the owner has since selected every proposed entry pre-merge (canonical status PENDING; see the [owner pre-merge selection ledger](../DECISIONS.md#owner-pre-merge-selection-ledger)). Owner selections do not change what this evidence shows: none of it is independent astronomical validation.

All evidence below was produced on unmerged draft branches. The links are permalinks to exact commits, so they stay valid whatever happens to the branches.

## Evidence sources

| Key | Source | Exact commit | ChatGPT QA | Claim boundary |
|---|---|---|---|---|
| FOUND | Foundation engine, draft PR [#1](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1) | `d8193c692d52aa12595f81c227638a061605a3d9` | Audit history on PR #1 | Current behaviour only |
| K01-PLAN | KUN-01 validation plan, draft PR [#11](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/11) | `d4e9d9eb0c008a09744bb5a49f6bcf88f580319c` | [QA PASS, plan architecture only](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/11#pullrequestreview-5606241883) | Plan; no accuracy result |
| K01-PROBES | KUN-01 Swiss-first scientific-decision notes and convention probes, draft PR [#17](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/17) | `c56c2a5935b719d323400d4656fb423b0b05dae7` | No QA review recorded on PR #17 | Swiss compared with itself under different conventions; sizes of choices, not accuracy |
| SC18 | KUN-01-SWISS-01 `swetest` conformance, draft PR [#18](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/18) | `66692d7d7d5a0cbef5a6354bb6ecfbd3f2478b38` | [Final QA PASS, Swiss-on-Swiss conformance only](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/18#pullrequestreview-5609326875) | Python integration equals the official `swetest` CLI for 24 synthetic cases; not independent astronomy |
| K02 | KUN-02 Phase 1 probes, invariants and reports, draft PR [#19](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/19) | `1986b0aa4702c42140d7cf1cc2c7249d03ae1bf0` | [Final QA PASS, research and test harness only](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/19#pullrequestreview-5610433809) | Swiss conformance, independent formulae and timekeeping checks; not observational certification |

Common environment for SC18 and K02: Python 3.13.16, pyswisseph 2.10.3.2 (Swiss Ephemeris 2.10.03), `sepl_18.se1` SHA-256 `ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66`, `semo_18.se1` SHA-256 `1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7`, from `aloistr/swisseph@c69c14adb7a0f94829586ffd92cd422aacb21e86`. K02 also used system tzdata 2026e and PyPI tzdata 2026.5 (IANA 2026e). Both ChatGPT reviews reconciled Claude's execution receipts and inspected the source. Neither re-ran the pinned Swiss data independently.

## Evidence items

Abbreviations: K02 paths are relative to the PR #19 commit, `https://github.com/sabpuja/Sabpuja-Kundali-Engine/blob/1986b0aa4702c42140d7cf1cc2c7249d03ae1bf0/`.

| Item | Result | Class | Where | Used by |
|---|---|---|---|---|
| E-A1 | 204,416 synthetic points; at all 167,612 where `b"P"` returns, ascendant, MC and ARMC are bit-identical to `b"W"` | SWISS_CONFORMANCE | K02 invariant A1; `docs/kun02/lagna-p-vs-w.md` | SCI-01e |
| E-A2 | `b"W"` refuses 0 of 204,416 | SWISS_CONFORMANCE | K02 A2 | SCI-01e |
| E-A3/A4 | `b"P"` refuses exactly when \|lat\| ≥ 90° − true obliquity (to 1e-8″ on 8 dates); 36,804 refusals, all at or beyond the polar circle | SWISS_CONFORMANCE | K02 A3, A4 | SCI-01e, SCI-01g |
| E-POLAR | Polar-circle latitude 66.546714°–66.575237° over 1900–2100 | SWISS_CONFORMANCE | K02 `placidus_threshold` | SCI-01g |
| E-A5 | Lagna = tropical − true Lahiri to ≤ 1.4e-7″ | SWISS_CONFORMANCE | K02 A5 | SCI-01a, SCI-01e |
| E-FRAME | Planets: sidereal = tropical apparent − true ayanamsha to 4.1e-10″ (8 bodies, 2,000 instants); versus mean ayanamsha up to 18.776″ | SWISS_CONFORMANCE | K02 `planet_frame`; `docs/kun02/sci-decision-matrix.md` | SCI-01a, SCI-01d |
| E-A6 | Independent spherical-trigonometry ascendant agrees to ≤ 1.2e-5″ equatorward of the polar circle | INDEPENDENT_MATHEMATICS | K02 A6 | SCI-01e |
| E-A7 | `b"W"` ascendant always on the eastern horizon (\|altitude\| < 1e-6″) | INDEPENDENT_MATHEMATICS | K02 A7 | SCI-01e |
| E-A8 | `b"W"` cusps are exact Rashi starts | SWISS_CONFORMANCE | K02 A8 | SCI-01f |
| E-A9 | Lagna Navamsa sweep, 3 locations, 326 crossings, 0 failures | SWISS + INDEPENDENT_MATHEMATICS | K02 A9 | SCI-01f |
| E-A10 | 90,720 predeclared D1/D9 checks, 0 mismatches | SWISS + INDEPENDENT_MATHEMATICS | K02 A10 | SCI-01f, SCI-02 |
| E-A11 | Unset mode → Fagan/Bradley (−0.883°); `SIDBIT_PREC_ORIG` leaks until `set_ephe_path`; KP and NONUT differ; empty data dir gives no silent change | SWISS_CONFORMANCE | K02 A11 | SCI-01a, P9 |
| E-A12 | Engine Lagna, Rashi, D9 and houses equal the `b"W"` value on 6 fixture cases; polar case refused (`ASCENDANT_UNCOMPUTABLE`) | ENGINE_BEHAVIOUR | K02 A12 | SCI-01e |
| E-LAHIRI | Mode-1 epoch value +0.138″ (default), +0.008″ (`NO_PREC_OFFSET`), +0.0000016″ (`PREC_ORIG`); IAE mean values quoted in Swiss docs +0.073″/+0.044″/+0.002″ | SWISS_CONFORMANCE | K02 `lahiri_definition` | SCI-01a |
| E-B1 | 63 synthetic time cases behave as hand-derived from IANA 2026e and Python rules | ENGINE_BEHAVIOUR + TIMEKEEPING | K02 B1; `docs/kun02/birth-time-report.md` appendix | SCI-03 |
| E-B2 | Independent transcription of 7 South Asian Zone entries equals `zoneinfo` at 74,864 instants | TIMEKEEPING | K02 B2 | SCI-03 |
| E-B3 | Swiss leap seconds equal the IERS list (27/27, 4 non-leap controls refused); UT1 − UTC **implied under the Swiss ΔT model** within 0.9 s at 110 epochs 1972–2026 (largest 0.81 s) | TIMEKEEPING | K02 B3 | SCI-01h |
| E-C1 | All bodies use Swiss files at both UTC extremes of the 1900–2100 local window and at 1800/2399; fallback detected at 1799/2400 | SWISS_CONFORMANCE | K02 C1 | SCI-01d, SCI-03 |
| E-EDGE | UTC-year rule: local 1900-01-01 00:00 Kolkata refused, local 2101-01-01 05:29:59 IST accepted (T46–T51) | ENGINE_BEHAVIOUR | K02 time cases | SCI-03 |
| E-TZBUILD | Ubuntu tzdata 2026e and PyPI tzdata 2026.5 disagree for 8 Asian zones before 1956; Asia/Kolkata identical | TIMEKEEPING | K02 `tzdata_source_agreement`; birth-time report §2.3 | SCI-03, P1 |
| E-SIDT | Swiss sidereal time equals an independent IERS 2010 eq. 5.32 expression to 0.0027″ for 1900–2049; −1.908″ step at 2050-01-01 0h UT | INDEPENDENT_MATHEMATICS | K02 time probe; birth-time report §2.4 | SCI-01h |
| E-RATE | Largest Lagna rate in 3,000 random instants: 16.4″/s (equator), 21.5″/s (28.6° N), 65.9″/s (60°), 634.4″/s (66°) | SWISS_CONFORMANCE | K02 time probe | SCI-01g |
| E-CLOCK | Category change rate for clock errors (2,000 instants, Indian cities): 0.9 s → 0%; 1 min → Lagna Navamsa 7.7%; 38 min 29 s (hypothetical LMT vs IST) → Lagna Rashi 33.4% | SWISS_CONFORMANCE | K02 birth-time report §2.5 | SCI-01h, SCI-03 |
| E-ENV-LAT | Today 66.55° refused for 1900-01-01, accepted for 2100-12-31 | ENGINE_BEHAVIOUR | K02 `latitude_behaviour` | SCI-01g |
| E-SC18 | 24/24 cases, 882/882 engine-versus-`swetest` comparisons, 36/36 self-consistency checks; max deviation 4.93e-9° | SWISS_CONFORMANCE | SC18 `tests/swiss_conformance/` | SCI-01a, SCI-01d, SCI-02 |
| E-RULE18 | Rule oracle: 108 Pada edges and float neighbours, 20,000-point sweep, 0/360 wrap | INDEPENDENT_MATHEMATICS | SC18 `test_rule_oracle.py` | SCI-01f, SCI-02 |
| E-K01-n | KUN-01 convention probes [1]–[11] (mode differences, frame alternatives, 21,168-sample P/W equality, ΔT values) | SWISS_CONFORMANCE | K01-PROBES `docs/accuracy/evidence/convention_probes.out` | sizes of alternatives |

## Authoritative references

| Reference | Version / location | Fetched and hashed? | Used for |
|---|---|---|---|
| Swiss Ephemeris source and docs (`swehouse.c`, `swedate.c`, `swephlib.c`, `sweph.h`, `doc/swisseph.htm`) | `aloistr/swisseph@c69c14a` | Yes (hashes in PR #19 evidence `00-environment-and-hashes.txt`) | SCI-01a, d, e, g, h |
| IANA tz `asia`, `backzone`, `theory.html`, `leap-seconds.list` | tz 2026e (`eggert/tz` tag) | Yes (`asia` `02b69728…0e92e`, `leap-seconds.list` `db5a895f…3433`) | SCI-03, SCI-01h |
| IERS Conventions 2010, eq. 5.32 | Technical Note 36 | Formula implemented in the K02 probe | SCI-01h |
| 27th CGPM (2022) Resolution 4 | https://www.bipm.org/en/cgpm-2022/resolution-4 | Originally no (proxy blocked bipm.org; confirmed by [ChatGPT QA](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/19#pullrequestreview-5610345034)); read on 2026-10-24. **Superseded** by 2026 Resolution 5 | SCI-01h (history) |
| 28th CGPM (2026) Resolution 5 | https://www.bipm.org/en/cgpm-2026/resolution-5 | Read on 2026-10-24, not hashed: continuous UTC effective 20 May 2027; maximum \|UT1 − UTC\| 3 600 s. The page shows no adoption date and the text reviewed gives no effective hour | SCI-01h |
| Indian Astronomical Ephemeris (1989, 2019) | Values as quoted in Swiss `doc/swisseph.htm` | No (secondary source) | SCI-01a |
| Python `zoneinfo` (TZPATH search order, cache behaviour) | Python 3.13 standard library | Behaviour observed in K02 (system TZPATH read before the PyPI package) | SCI-03, P1 |
| Product requirements | `main:docs/PRD.md` KUN-F03 to KUN-F07; `main:docs/ACCEPTANCE-MATRIX.md` QA-005 to QA-013 | In this repository | all |

## Consistency review

Checked: SC18 and K02 against each other and against K01-PROBES, for contradictions and for conclusions the evidence does not support.

| # | Finding | Assessment | Resolution in this package |
|---|---|---|---|
| CR-1 | Lagna rate at 66°: K01 probe [7] reports 220.25″/s (24 hourly samples on 2000-03-20); K02 reports 634.4″/s (3,000 random instants) | Not a contradiction: both are sample maxima of different samples; the rate grows without bound towards the polar circle | Quote K02's value, labelled a sample maximum, not a bound |
| CR-2 | 38.5-minute clock error: K01 says "roughly 10° of Lagna"; K02 measures up to 13.76°, Rashi change in 33.4% of samples | Not a contradiction: 10° is the typical shift (about 15° per hour of sidereal rotation), 13.76° the sample maximum | Quote the K02 distribution; keep the scenario labelled hypothetical |
| CR-3 | Refusal code: K01 `LATITUDE_OUTSIDE_VALIDATED_BAND`, K02 `LATITUDE_OUTSIDE_SUPPORTED_BAND` | Naming conflict only | Propose `LATITUDE_OUTSIDE_SUPPORTED_BAND` ("supported", because the band is a product envelope, not validation) |
| CR-4 | K01 SCI-01h says UT1 − UTC "is kept within ±0.9 s (IERS, NIST)" and cites Swiss's model value +0.41 s | Supported only as the IERS rule while it stands and as a Swiss-model value; not a measurement; does not hold indefinitely (CGPM 2022 Res. 4) | SCI-01h wording uses "implied under the Swiss ΔT model" and the BIPM limit change |
| CR-5 | K01 SCI-03 mentions "Bombay Time (about +04:51)" | No source for this offset is in the reviewed evidence, and IANA does not model it | Not used. Any such offset comes only through DATA-01 with a citation |
| CR-6 | SC18 compares the Lagna with `swetest -house…,P`; SCI-01e moves to `W` | Documented blind spot (SC18 final QA) | P3 must extend the conformance suite to `W`. *Status 2026-10-24:* addressed by the versioned KUN-03 conformance profile in draft PR #33 (contained in Gate 1 `c3cb040`), which compares against a `W` reference; still Swiss-on-Swiss |
| CR-7 | SC18 enforces refusals for "years 1899/2101", "UTC-1899 via offset" (current UTC-year rule) and "polar Placidus" (`ASCENDANT_UNCOMPUTABLE`); SCI-03 and SCI-01g change those rules and codes | Expected change, not a contradiction | P4 (dates) and P2/P3 (polar) must update those SC18 refusal cases, with QA, in their own PRs. *Status 2026-10-24:* done through the versioned overlay in draft PR #33 (typed refusal codes; archival PR #18 run kept unchanged) |
| CR-8 | K02 P/W identity (167,612) and K01 (21,168): same conclusion on disjoint samples | Consistent | none |
| CR-9 | ΔT 2000: K01 63.83 s, K02 63.97 s | Different dates in 2000 (January vs 1 July) | none |

No reviewed document claims independent astronomical accuracy, golden-chart validation or historical-clock verification, and this package adds no such claim.
