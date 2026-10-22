# KUN-02 Phase 2: proposed canonical scientific decisions

**Document ID:** SP-KUN-DEC-KUN02-P2 | **Date:** 2026-10-22 | **Status:** PROPOSED, every new entry PENDING owner approval
**Register:** [`docs/DECISIONS.md`](../DECISIONS.md) (SP-KUN-DEC-001) is the only decision register. This package supports the proposed entries there; it approves nothing.
**Base for this PR:** `main` @ `0023fdc66f9061daffe60fe54bb92ea935e75b87`
**Companion documents:** [evidence and reference map](KUN-02-P2-evidence-map.md) · [implementation sequence, compatibility and release risks](KUN-02-P2-implementation-and-risks.md)

## How to read the status columns

Every pending decision keeps four things separate. One of them is never taken as another.

| Column | Meaning | Who |
|---|---|---|
| **Proposed convention** | The exact setting or formula Claude proposes | Claude (lead implementer) |
| **Evidence** | Reproducible test results, with the exact PR, SHA and QA review that accepted them | KUN-01 and KUN-02 runs, accepted by ChatGPT QA |
| **ChatGPT scientific QA** | ChatGPT's recorded recommendation, with a link | ChatGPT PM / independent QA |
| **Owner approval and canonical adoption** | Sabpuja's explicit choice, the date, and the merge SHA of the `DECISIONS.md` change that records it | Sabpuja (owner) |

A ChatGPT QA PASS of an evidence package is **not** an owner approval. An owner approval is **not** an implementation authorization: every code change still needs its own scoped draft PR, QA and merge authorization ([implementation sequence](KUN-02-P2-implementation-and-risks.md)).

## Evidence classes

The evidence is labelled with the classes used in KUN-02. None of them is independent observational astronomy.

- **SWISS_CONFORMANCE:** the Python integration agrees with Swiss Ephemeris itself (binding, `swetest` CLI, or Swiss internals). Swiss-on-Swiss.
- **INDEPENDENT_MATHEMATICS:** an independently coded formula (for example spherical trigonometry or the classical Navamsa rule) applied to Swiss inputs.
- **TIMEKEEPING:** checks against IANA tz and IERS leap-second records.
- **ENGINE_BEHAVIOUR:** what the current engine accepts, refuses and outputs.

No golden-chart tolerance has been frozen, and no claim of astronomical accuracy is made anywhere in this package.

## Already approved (unchanged by this PR)

| ID | Approved choice | Status |
|---|---|---|
| SCI-01b | Mean Rahu = the adjusted mean lunar node of the pinned Swiss Ephemeris `MEAN_NODE` | OWNER APPROVED 2026-10-22, unchanged |
| SCI-01c | Ketu = mean Rahu + exactly 180°, normalized cyclically, classified from the unrounded Rahu | OWNER APPROVED 2026-10-22, unchanged |

The text of these two entries in `DECISIONS.md` is not edited by this PR.

## Decision matrix

| ID | Proposed convention (exact) | Changes current numbers? | Changes accepted inputs? | Evidence | ChatGPT scientific QA | Owner approval |
|---|---|---|---|---|---|---|
| SCI-01a | Swiss `SE_SIDM_LAHIRI` (mode 1): 23°15′00.658″ at 1956-03-21 0h TT, true ayanamsha, Swiss default precession; `set_sid_mode(SIDM_LAHIRI, 0, 0)` and `set_ephe_path` on every request under the Swiss lock | No | No | KUN-02 A5, A11, Lahiri-definition probe; KUN-01 probe [1]; PR #18 conformance | Supports direction (PR #19 final QA) | **PENDING** |
| SCI-01d | Geocentric, apparent, true ecliptic and equinox of date, minus the true ayanamsha: `calc_ut(jd_ut, body, FLG_SWIEPH \| FLG_SIDEREAL)`, no other flags; fail closed if `FLG_SWIEPH` is not returned | No | No | KUN-02 planet-frame probe; KUN-01 probes [2], [10], [11]; PR #18 882/882 | Supports direction (PR #19 final QA) | **PENDING** |
| SCI-01e | Sidereal Lagna = `ascmc[0]` of `houses_ex(jd_ut, lat, lon, b"W", FLG_SIDEREAL)`. **Only together with or after SCI-01g** | No (bit-identical wherever `b"P"` works) | Not with SCI-01g; alone it would accept polar births | KUN-02 A1–A8, A12; KUN-01 probes [4]–[6] | Favoured, only paired with or after SCI-01g (PR #19 final QA) | **PENDING** |
| SCI-01f | D1 house = whole sign from the Lagna Rashi; Navamsa = 108 equal 3°20′ segments mapped cyclically from Mesha; D9 Lagna = Navamsa sign of the unrounded Lagna; D9 house = whole sign from the D9 Lagna. All from unrounded values | No for D1; adds D9 houses | No | KUN-02 A8–A10; PR #18 rule oracle | Supports direction (PR #19 final QA) | **PENDING** |
| SCI-01g | Supported latitude −66.0 ≤ lat ≤ +66.0 inclusive, refused outside with `LATITUDE_OUTSIDE_SUPPORTED_BAND`, independent of date | No inside the band | Yes: refuses 66.0° < \|lat\| < 89° (some of which is accepted today, depending on date) | KUN-02 A3, A4, envelope §2 | Favoured as a fixed product envelope (PR #19 final QA) | **PENDING** |
| SCI-01h | Keep: civil UTC (from the IANA offset) passed to Swiss as UT1; TT = UT1 + Swiss ΔT. Label the assumption by era in metadata; review before 2035 | No | No | KUN-02 B3, time-scale and sidereal-time probes; KUN-01 probes [8], [9] | Honest epoch-specific metadata required (PR #19 final QA) | **PENDING** |
| SCI-02 | MVP outputs: D1 sidereal longitude, Rashi and whole-sign house for Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, mean Rahu, Ketu; Lagna longitude and Rashi; D9 sign of every body and the Lagna; D9 whole-sign houses; Moon Rashi, Nakshatra and Pada; calculation metadata. Owner option: Nakshatra/Pada for all bodies and the Lagna | Adds fields only | No | KUN-02 A10; PR #18 rule oracle | Supports direction; no new approval (PR #19 final QA) | **PENDING** |
| SCI-03 | Local civil birth date 1900-01-01 to 2100-12-31 inclusive; explicit offset validated against IANA; gaps refused, folds disambiguated by the given offset; pinned tzdata with a TZif byte manifest and deterministic loading; `HISTORICAL_CLOCK_UNVERIFIED` fail-closed for Asia/Kolkata before 1956-01-01 at minimum; future dates disclosed as projected | Only at the date edges | Yes: edge dates and gated historical births | KUN-02 B1, B2, C1, T01–T63, tzdata probe | Local-date window, pinned TZif and temporary pre-1956 minimum endorsed (PR #19 final QA) | **PENDING** |

Each row is expanded below with the exact setting, alternatives, evidence, references, limitations, effect on existing results, input-acceptance changes and required regression tests. "Evidence" items are defined in the [evidence map](KUN-02-P2-evidence-map.md).

---

## SCI-01a: Lahiri ayanamsa

- **Exact setting.** `swe.set_ephe_path(<verified pinned dir>)` followed by `swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)` on every request, inside the engine's Swiss lock. Mode 1 is defined upstream as 23°15′00.658″ at 1956-03-21 0h TT (IAE 1985 revision). Swiss carries it as a **true** ayanamsha with its default precession (Vondrák 2011) and its built-in precession offset. No `SIDBIT_*` option. Metadata text: `Lahiri (Chitrapaksha), Swiss Ephemeris SE_SIDM_LAHIRI (mode 1), IAE 1985 definition, true ayanamsha, Swiss 2.10.03 default precession`.
- **Alternatives evaluated.** Mode 1 with `SIDBIT_PREC_ORIG` (reproduces the IAE IAU-1976 tables more closely; upstream calls it a test option that reduces ephemeris accuracy; −0.30″ to +0.31″ from mode 1 over 1900–2100). Mode 1 with `SIDBIT_NO_PREC_OFFSET`. Mode 46 Lahiri ICRC (−1.40″ to −0.78″). Mode 43 Lahiri 1940 (about −53″). Mode 44 Lahiri VP285 (about +23″). Krishnamurti (about −5.8′) and Raman (about −1.45°) for scale.
- **Supporting evidence.** E-A5 (the same true ayanamsha is subtracted from the Lagna, to ≤ 1.4e-7″, and from all eight bodies, to ≤ 4.1e-10″). E-A11 (an unset mode silently gives Fagan/Bradley, −0.883°; `SIDBIT_PREC_ORIG` leaks across `set_sid_mode` until `set_ephe_path`; the per-call reset prevents both). E-LAHIRI (epoch value reproduced to +0.138″ by default, +0.008″ without the precession offset, +0.0000016″ with `PREC_ORIG`; against IAE mean values quoted in the Swiss documentation, +0.073″, +0.044″, +0.002″). E-K01-1 (mode differences). E-SC18 (engine equals `swetest -sid1`).
- **Upstream references.** Swiss Ephemeris `doc/swisseph.htm` §2.8.5 and the appendix on comparing Swiss Lahiri with IAE; `sweph.h` mode table at `aloistr/swisseph@c69c14a`. IAE values are quoted from the Swiss documentation and were not read from the IAE editions here.
- **Known limitations.** Mode 1 is a Swiss definition of Lahiri. The literal 1956 epoch value is reproduced only to 0.138″ in default mode, by design. The IAE comparison is secondary. No independent ayanamsa reference is frozen (KUN-01 PG-3 is still open). The Moon moves 0.31″ in about 0.55 s, so the variant spread is far below birth-time precision.
- **Effect on existing results.** None. The foundation already calls exactly this.
- **Input acceptance changes.** None.
- **Required regression tests.** Engine longitude equals `calc_ut` with mode 1 for a fixed synthetic set (PR #18 cases). The engine resets leaked Swiss state (`SIDBIT_PREC_ORIG`, an unset mode) on the next request (KUN-02 `test_engine_resets_leaked_swiss_state`, made permanent in P9). The metadata string is pinned by a contract test (P7).

## SCI-01d: planetary coordinate frame

- **Exact setting.** `swe.calc_ut(jd_ut, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)` for SUN, MOON, MARS, MERCURY, JUPITER, VENUS, SATURN and MEAN_NODE. No `FLG_TOPOCTR`, `FLG_TRUEPOS`, `FLG_NOABERR`, `FLG_NOGDEFL`, `FLG_NONUT` or `FLG_EQUATORIAL`. Refuse the request (existing `EphemerisDataError` path) if the returned flags lack `FLG_SWIEPH` (no silent Moshier fallback). This is geocentric, apparent (light-time, annual aberration, gravitational deflection), on the true ecliptic and equinox of date, minus the true ayanamsha.
- **Alternatives evaluated.** Topocentric (Moon up to 1.02°; Moon Nakshatra differs in 3.87% of samples at New Delhi). Geometric or astrometric positions (Sun 20.8″, Mars 39.0″, Saturn 27.3″, Moon 0.8″). Mean ayanamsha (up to 18.78″, the nutation in longitude). `SIDBIT_ECL_T0` and `SIDBIT_SSY_PLANE` (research projections, not used in Indian ephemerides).
- **Supporting evidence.** E-FRAME (sidereal equals tropical apparent minus the true ayanamsha to 4.1e-10″ for all eight bodies on 2,000 random instants; against the mean ayanamsha up to 18.776″). E-K01-2/10/11 (sizes of the alternatives). E-SC18 (882/882 engine-versus-`swetest` comparisons, max deviation 4.93e-9°, with `-i65538`, Swiss files only). E-C1 (all bodies use Swiss files at the UTC extremes of the 1900–2100 local window and at 1800/2399; fallback detected at 1799/2400).
- **Upstream references.** `doc/swisseph.htm` §2.8.12 ("On which ecliptic is the ayanamsha measured?"), §2.3 (apparent positions).
- **Known limitations.** Swiss-on-Swiss conformance only. `SEFLG_NONUT` is a documented blind spot of the `swetest` comparison (PR #18 final QA). Any independent reference must be converted to the same frame (nutation cancels against the true ayanamsha).
- **Effect on existing results.** None.
- **Input acceptance changes.** None.
- **Required regression tests.** The PR #18 conformance suite keeps passing (24/24 cases, 882/882). A test that the requested flags are exactly `FLG_SWIEPH | FLG_SIDEREAL`. A data-gate test that a missing or wrong `.se1` refuses rather than falls back (existing foundation tests).

## SCI-01e: sidereal Lagna through `b"W"`

- **Exact setting.** `cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, b"W", swe.FLG_SIDEREAL)`; Lagna = `ascmc[0]`, after the SCI-01a reset in the same locked section. The ascendant definition is unchanged: the eastern rising point of the ecliptic, from apparent sidereal time of `jd_ut` and true obliquity, minus the true Lahiri ayanamsha. Keep the existing `ASCENDANT_UNCOMPUTABLE` handler as defensive code. **Must ship atomically with, or after, SCI-01g** (P2 before or with P3).
- **Alternatives evaluated.** Keep `b"P"` (Placidus as the vehicle; fails at and beyond the polar circle, a date-dependent rule). `b"E"` or `b"O"` (also bit-identical; `W` is chosen because it matches the whole-sign house model and its cusps are exact Rashi starts). An independent ascendant formula (used only as a check: a naive formula returns the setting point in about 32% of polar samples).
- **Supporting evidence.** E-A1 (167,612 of 204,416 synthetic points where `b"P"` returns: ascendant, MC and ARMC bit-identical to `b"W"`). E-A2 (`b"W"` never refuses). E-A3/A4 (`b"P"` refuses exactly when \|lat\| ≥ 90° − true obliquity, to 1e-8″, 66.5467°–66.5752° over 1900–2100). E-A6 (independent spherical trigonometry agrees to ≤ 1.2e-5″ equatorward of the polar circle). E-A7 (`b"W"` is always on the eastern horizon). E-A12 (the engine's Lagna, Rashi, D9 and houses equal the `b"W"` value on all six fixture cases; the polar case is refused today). E-K01-4..6 (21,168 earlier samples, consistent).
- **Upstream references.** `swehouse.c` at `c69c14a` (`CalcH` ascendant; Placidus failure when \|φ\| ≥ 90° − ε; W computed as E floored to 30°; E/W ascendant swap); `doc/swisseph.htm` §6.4.
- **Known limitations.** Evidence is Swiss-on-Swiss plus independent formula; no golden-chart Lagna tolerance is frozen. The PR #18 suite compares `swetest` with `-house…,P`; after P3 it must also compare with `W` (documented blind spot). Swiss 2.10.03 sidereal time steps by −1.908″ at 2050-01-01 0h UT (Lagna about −1.7″ at New Delhi), a version-specific model switch.
- **Effect on existing results.** None wherever the engine produces a chart today.
- **Input acceptance changes.** None when shipped with SCI-01g. Alone, it would newly accept 66.5467°…89° births, which is why it must not ship alone.
- **Required regression tests.** The engine Lagna equals `b"P"` bit for bit on the KUN-02 in-band grid and on the PR #18 cases. The PR #18 conformance suite updated to compare against `swetest` with `W` (and still with `P` in the band). A polar case is refused by SCI-01g, not by `ASCENDANT_UNCOMPUTABLE`.

## SCI-01f: D1 and D9 house conventions

- **Exact formulas** (all on unrounded longitudes, half-open segments):
  - Rashi index = ⌊λ / 30°⌋ mod 12.
  - D1 house of a body = ((Rashi(body) − Rashi(Lagna)) mod 12) + 1.
  - Navamsa index = ⌊λ / (10/3)°⌋ mod 108; Navamsa sign = index mod 12 (equals the classical rule: fire signs start at Mesha, earth at Makara, air at Tula, water at Karka).
  - D9 Lagna = Navamsa sign of the unrounded Lagna.
  - D9 house of a body = ((Navamsa sign(body) − D9 Lagna) mod 12) + 1.
- **Alternatives evaluated.** Equal houses from the Lagna degree; Sripati/Bhava Chalit (deferred to P1 as a separate labelled chart); sidereal Placidus.
- **Supporting evidence.** E-A8 (W cusps are exact multiples of 30° from the Lagna Rashi). E-A9 (Lagna Navamsa sweep at three locations, 326 crossings, 0 failures). E-A10 (90,720 predeclared checks: rules versus W cusps versus the classical rule, D9 houses, P versus W; 0 mismatches). E-RULE18 (PR #18 rule oracle: all 108 Pada edges and float neighbours, a 20,000-point sweep, the 0/360 wrap).
- **Upstream references.** Not an astronomical convention; the rules module `src/sabpuja_kundali/rules.py` on the foundation branch @ `d8193c6`.
- **Known limitations.** Category boundaries are decided on float values exactly at edges; this is consistent and tested on both sides, but a reference that rounds before classifying can differ at an edge.
- **Effect on existing results.** D1 unchanged. D9 houses are a new output field.
- **Input acceptance changes.** None.
- **Required regression tests.** D9 house oracle at all 108 Navamsa edges and their float neighbours (as KUN-02 A10). Output schema version bump and contract test (P6). Existing D1 house tests unchanged.

## SCI-01g: supported latitude band

- **Exact setting.** Validate `latitude` as a finite number with −66.0 ≤ lat ≤ +66.0 (inclusive at both ends, compared on the parsed float) before any Swiss call; refuse otherwise with `LATITUDE_OUTSIDE_SUPPORTED_BAND`, for every date. Existing `COORDINATE_INVALID` handling for non-numbers and non-finite values stays first. Longitude unchanged: −180 ≤ lon ≤ +180. Disclosure `HIGH_LATITUDE_TIME_SENSITIVITY` above 60° (no refusal).
- **Alternatives evaluated.** Keep today's rule (accept −89 < lat < 89, then refuse wherever Placidus fails; date-dependent). After SCI-01e accept up to ±89° with high-latitude fixtures and a strong disclosure. A narrower band such as ±60° (refuses Reykjavik, Anchorage and parts of Scandinavia).
- **Supporting evidence.** E-A3/A4 and E-POLAR (polar circle 66.546714°–66.575237° over 1900–2100; margin from 66.0° at least 0.5467°, about 60 km). E-RATE (largest Lagna rate in KUN-02 samples: 21.5″/s at New Delhi, 65.9″/s at 60°, 634.4″/s at 66°; sample maxima, not bounds). E-ENV-LAT (today 66.55° is refused for 1900-01-01 and accepted for 2100-12-31).
- **Upstream references.** `swehouse.c` Placidus failure condition; `doc/swisseph.htm` §6.4.
- **Known limitations.** This is a conservative product support envelope, not a computational limit: Swiss `b"W"` returns a rising point beyond 66°. India lies between about 6.7° N and 37.1° N (general geography, not probed).
- **Effect on existing results.** None for any accepted chart.
- **Input acceptance changes.** Refuses 66.0° < \|lat\| < 89°. Today part of that range is accepted on some dates and refused on others.
- **Required regression tests.** ±66.0 accepted; `nextafter(66.0, +inf)` and ±66.55 refused on every date; 1900 and 2100 behave the same; existing polar tests updated to expect the new code; no change to any in-band chart.

## SCI-01h: astronomical time scales

- **Exact setting.** Keep the pipeline: local wall time and explicit offset → validated against IANA → civil UTC → `swe.julday(UTC, Gregorian)` → passed to Swiss as UT (= UT1 for Swiss). Planet positions use TT = UT1 + Swiss ΔT (`deltat_ex`, Swiss files). Do **not** switch to `swe.utc_to_jd` now. Record in metadata, by era:
  - **1900–1960:** a civil clock reading converted with IANA's offset; no UTC existed before 1961; UT1 is a reconstruction.
  - **1961–1971:** UTC with frequency offsets and steps; UT1 − UTC for this era is not sourced here (KUN-01 PG-5 open).
  - **1972 to the IERS leap-second list expiry (2027-06-28):** leap-second UTC; the IERS rule keeps \|UT1 − UTC\| < 0.9 s. In KUN-02 this is only *implied under the Swiss ΔT model* together with the IERS TAI − UTC list (largest 0.81 s), **not measured** Earth orientation.
  - **After the list expiry:** UT1 − UTC is a forecast. The 27th CGPM (2022), Resolution 4 (BIPM, https://www.bipm.org/en/cgpm-2022/resolution-4) decided that the maximum value of UT1 − UTC will be increased in, or before, 2035. The 0.9 s limit therefore must not be assumed for later births. Swiss's extrapolated ΔT implies −1.32 s (2035), −5.40 s (2050), −24.0 s (2100) if no further leap second occurs: model projections, not limits.
  - **2050-01-01 0h UT:** Swiss 2.10.03 switches its default sidereal-time model (−1.908″ step; Lagna about −1.7″ at New Delhi). Version-specific behaviour, recorded as a convention.
  - ΔT: tabulated to 2028 in Swiss (`TABEND 2028`), extrapolated after; upstream says future ΔT "cannot be calculated with accuracy".
- **Alternatives evaluated.** `swe.utc_to_jd` (moves 1972–2029 inputs by at most 0.39 s, up to 0.95 s in 2030–2033 under its no-new-leap-second assumption; identical before 1972 and from 2034). A pinned IERS UT1 − UTC table (more data to maintain; no category change in samples). TT from the leap-second list (exact after 1972 for TT; does not help UT1).
- **Supporting evidence.** E-B3 (Swiss accepts `23:59:60` on all 27 IERS leap dates and refuses 4 non-leap controls; implied UT1 − UTC within 0.9 s at 110 half-year epochs 1972–2026, Swiss-model consistency). E-SIDT (Swiss sidereal time agrees with an independent IERS 2010 eq. 5.32 expression to 0.0027″ before 2050). E-CLOCK (0.9 s of clock error changed no Lagna or Moon category in 2,000 samples, max Lagna shift 0.0054°). E-K01-8/9.
- **Upstream references.** `doc/swisseph.htm` §7 (time scales, ΔT) and §6.1 (sidereal time); `swedate.c` lines 366–371; `swephlib.c` lines 3460–3481; IERS `leap-seconds.list` via tz 2026e (SHA-256 `db5a895f…3433`, expires 2027-06-28); IERS Conventions 2010 eq. 5.32; BIPM CGPM 2022 Resolution 4.
- **Known limitations.** No measured UT1 − UTC series is used. The CGPM resolution text was confirmed by ChatGPT QA at the BIPM page; this environment's proxy blocked www.bipm.org, so it is cited, not quoted. The real accuracy risk before 1956 is the historical clock (SCI-03), not the time scale.
- **Effect on existing results.** None.
- **Input acceptance changes.** None.
- **Required regression tests.** Metadata contract test for the era label (P7). Pin the 2050 step value as a recorded Swiss behaviour (KUN-02 `test_swiss_sidereal_time_step_at_2050_is_recorded`). Re-run the B3 consistency check whenever tzdata's `leap-seconds.list` or Swiss is updated.

## SCI-02: MVP calculation scope

- **Exact scope.** Outputs, all from unrounded values:
  - D1: sidereal longitude, Rashi and whole-sign house for Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, mean Rahu (SCI-01b), Ketu (SCI-01c).
  - Lagna: sidereal longitude and Rashi (SCI-01e).
  - D9: Navamsa sign of every body and the Lagna; D9 whole-sign house of every body (SCI-01f).
  - Moon: Rashi, Nakshatra (27 × 13°20′ from sidereal 0°) and Pada (4 × 3°20′).
  - Metadata (P7): ayanamsa definition, node, frame, house model, ascendant vehicle, time-scale era label, Swiss version, ephemeris manifest SHA-256, tzdata version and TZif manifest SHA-256.
  - **Owner option:** Nakshatra and Pada for every body and the Lagna (same rule, no new astronomy).
- **Deferred (each needs its own spec, fixtures and decision):** Vimshottari Dasha; other divisional charts; Bhava Chalit; Yogas, Doshas, Gun Milan; Panchang; Uranus, Neptune, Pluto; upagrahas; retrograde, combustion, planetary war; true node; topocentric options; South Indian layout.
- **Alternatives evaluated.** Moon-only Nakshatra (today) versus all bodies; including Dasha in MVP (delays accuracy QA, per `DECISIONS.md` SCI-02 row).
- **Supporting evidence.** E-A10; E-RULE18; E-SC18 (categories from `swetest` values match).
- **Upstream references.** `docs/PRD.md` KUN-F04 to KUN-F07; acceptance QA-007, QA-010, QA-012, QA-013.
- **Known limitations.** Category correctness near edges depends on unrounded values (tested). No independent golden-chart D9 fixtures yet (QA-012 open).
- **Effect on existing results.** Additive fields only; no existing value changes.
- **Input acceptance changes.** None.
- **Required regression tests.** Output schema contract test with a version bump; D9 house and (if chosen) all-body Nakshatra oracles at every edge; existing outputs unchanged.

## SCI-03: supported dates, time zones and historical clocks

- **Exact setting.**
  1. **Date window:** the local civil date of the supplied wall-clock time must be within 1900-01-01 … 2100-12-31 inclusive, checked **before** conversion. Code `DATE_OUTSIDE_SUPPORTED_RANGE`. The UTC instant then lies within 1899-12-31T10:00Z … 2101-01-01T12:00Z, inside the pinned 1800–2399 data.
  2. **Offset and zone rules (kept):** an explicit UTC offset is required; it must equal one of IANA's offsets for that wall time in that zone. Wall time in a gap → `TIME_NONEXISTENT_LOCAL`; existing wall time with an offset IANA does not give → `TIME_OFFSET_MISMATCH`; a fold with a valid offset is accepted (the offset disambiguates). An interface without offsets must ask the user and never pick one silently (`TIME_AMBIGUOUS_LOCAL` reserved; QA-005).
  3. **tzdata reproducibility:** pin the PyPI `tzdata` package version and a committed SHA-256 manifest of the TZif bytes used (at least every zone accepted for births). Load deterministically: either set an empty `PYTHONTZPATH` in the service environment before the interpreter starts, or use an isolated loader (`ZoneInfo.from_file` on package resources, cached by the engine). **Never** call `zoneinfo.reset_tzpath()` or change global time-zone configuration in a live, multi-request process. Emit the tzdata version and the manifest hash in metadata.
  4. **Historical clocks (RG-HIST):** refuse Asia/Kolkata births whose local date is before 1956-01-01 with `HISTORICAL_CLOCK_UNVERIFIED`, as a **temporary minimum safety policy** until DATA-01 evidence exists. This is not proof of the clocks actually used across India, nor of correctness after 1956. No historical offset is invented.
  5. **Future dates:** accepted, with the disclosure `FUTURE_CIVIL_TIME_PROJECTED` for births after the pinned IERS list expiry.
- **Additional pre-1970 regions (assessment).** Evidence that the risk is not limited to Asia/Kolkata:
  - IANA states that its pre-1970 data is not comprehensive historical-clock evidence (`theory.html`).
  - KUN-02 accepts IANA-modelled LMT, HMT and war-time offsets for Karachi, Dhaka, Kathmandu, Colombo and Yangon (T21, T23, T24, T61, T62); these rest on the same kind of source.
  - Two builds of the same tzdata 2026e (Ubuntu with `backzone`, PyPI without) disagree for 8 Asian zones before 1956 (Aden, Kuwait, Bahrain, Brunei, Phnom Penh, Vientiane, Muscat, Kuala Lumpur).

  Options for the owner:
  - **(A) Floor (mandatory):** Asia/Kolkata before 1956-01-01.
  - **(B) Recommended before public release:** (A) plus every other IANA zone before 1970-01-01, fail closed, until DATA-01 reviews a zone and era. For an India-first MVP this refuses few real users and removes every unreviewed pre-1970 clock.
  - **(C)** (A) plus the other South Asian zones (Asia/Karachi, Asia/Dhaka, Asia/Kathmandu, Asia/Colombo, Asia/Yangon, Asia/Thimphu) before 1970-01-01 only.

  The gate is a versioned table (zone, local-date start, end, policy), reviewed like any decision. Asia/Kolkata from 1956 to 1969 stays accepted under (A); IANA's pre-1970 caveat still applies to it, and this is recorded as a residual risk.
- **DATA-01 historical-clock research package (separate, not started).** For each verified exception it must record:
  - birthplace as named and administered at the birth date, with coordinates and source;
  - historical jurisdiction;
  - source documentation (birth register, gazette, railway or municipal record, scholarly source), cited;
  - clock convention (local mean time, railway, municipal or civil, war time, or unknown);
  - date coverage for that place and clock, with gaps refused;
  - place-to-zone provenance.

  **Conditions for a verified exception:** all of the above are documented and cited; reviewed by ChatGPT QA; approved by the owner; added to the versioned gate table by its own PR; and the user explicitly selects the documented clock, with no default. No offset without a source.
- **Alternatives evaluated.** Keep the UTC-year rule; start at 1947 or 1956; widen to 1800–2399 (needs pre-1900 civil-time work); accept historical IST entries with only a disclaimer (not recommended: in the hypothetical case of a Mumbai local-mean-time reading entered as IST, the 38.5-minute error would change the Lagna Rashi in 33% of samples); conditional refusal (user confirms IANA's clock).
- **Supporting evidence.** E-B1 (63 synthetic cases behave as hand-derived from IANA and Python rules). E-B2 (7 South Asian Zone entries transcribed from tz 2026e `asia` match `zoneinfo` at 74,864 instants). E-EDGE (T46–T51: the UTC-year rule refuses local 1900-01-01 00:00 Kolkata and accepts local 2101-01-01 05:29:59 IST). E-C1 (data coverage at the window's UTC extremes). E-TZBUILD (8-zone build disagreement). E-CLOCK (clock-error sensitivity: 1 minute changes the Lagna Navamsa in 7.7% of samples).
- **Upstream references.** IANA tz 2026e `asia` (India section comments and Zone lines), `backzone`, `theory.html` (pre-1970 scope); Python 3.13 `zoneinfo` (system TZPATH read before the PyPI package, observed in KUN-02; cache semantics per the standard-library documentation, not re-verified here); Swiss `doc/swisseph.htm` §7.
- **Known limitations.** IANA is a model of civil time, not a record of every household clock. The gate is coarse by design. Future civil-time rules are projections.
- **Effect on existing results.** None for accepted charts inside the window, except that results stop depending on the host image's tzdata build.
- **Input acceptance changes.** Edge dates flip to the local-date rule; gated historical births are refused; non-RFC 3339 time strings refused by the strict format (P5).
- **Required regression tests.** KUN-02 T01–T63 with the proposed codes; first and last accepted local seconds in UTC+14 and UTC−12 zones; 29 February in 1900 and 2100 (refuse), 2000 and 2024 (accept); a DST gap and fold in both hemispheres; both sides of every gate edge; zones outside the gate unaffected; loaded TZif bytes match the manifest; identical output on two hosts (system tzdata with and without `backzone`); no stale cached zone after a reload.

---

## Consistency review of earlier evidence

The KUN-01 and KUN-02 evidence was checked for contradictions and unsupported conclusions. The findings are in the [evidence map](KUN-02-P2-evidence-map.md#consistency-review). In short:
- No contradiction changes any recommendation.
- Two numbers differ between KUN-01 and KUN-02 because they come from different samples (Lagna rate at 66°; Lagna shift of a 38.5-minute clock error). Both are sample statistics, not bounds; this package quotes KUN-02's larger sample.
- Three items are aligned here:
  - **Refusal code name:** `LATITUDE_OUTSIDE_SUPPORTED_BAND` (KUN-02), not `LATITUDE_OUTSIDE_VALIDATED_BAND` (KUN-01).
  - **Time-scale wording:** KUN-01's "UT1 − UTC within ±0.9 s" is read as the IERS rule while it stands, not a measurement.
  - **Historical offset:** KUN-01's "Bombay Time about +04:51" is not used. No sourced offset exists in this evidence.
