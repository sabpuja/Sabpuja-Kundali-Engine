# KUN-02 Phase 2: proposed canonical scientific decisions

**Document ID:** SP-KUN-DEC-KUN02-P2 | **Date:** 2026-10-22 | **Status:** originated on 2026-10-22 as a PROPOSED decision package. *Historical:* the canonical status of every new entry was then PENDING, and on 2026-10-24 the owner selected every entry pre-merge (step 1 only). **Current (Gate 2G reconciliation, 2026-10-24):** fourteen specific owner selections became **OWNER APPROVED / CANONICAL - 2026-10-24** through the PR #20 adoption process (merge `5b71408fadc4634805b56dbcff0c19f941830eb0` into `main`, [adoption receipt 6383419093](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/20#issuecomment-6383419093)). Their authoritative scopes, owner records and receipts are in the [owner pre-merge selection ledger](../DECISIONS.md#owner-pre-merge-selection-ledger) of `docs/DECISIONS.md`, which governs wherever this package differs. Historical recommendations, alternatives that were not selected and pre-merge evidence are kept below as dated material. Not every project decision is approved: UX-01, UX-02, UX-03, DATA-01, SEC-01, LEG-01 and PERF-01 remain PENDING
**Register:** [`docs/DECISIONS.md`](../DECISIONS.md) (SP-KUN-DEC-001) is the only decision register. This package supports the entries there; it approves nothing itself, and adoption is recorded only in the register.
**Base of the original decision PR (PR #20, historical):** `main` @ `0023fdc66f9061daffe60fe54bb92ea935e75b87`
**Companion documents:** [evidence and reference map](KUN-02-P2-evidence-map.md) · [implementation sequence, compatibility and release risks](KUN-02-P2-implementation-and-risks.md)

## How to read the status columns

Every decision in this package, whether pending or since adopted, keeps four things separate. One of them is never taken as another.

| Column | Meaning | Who |
|---|---|---|
| **Proposed convention** | The exact setting or formula Claude proposes | Claude (lead implementer) |
| **Evidence** | Reproducible test results, with the exact PR, SHA and QA review that accepted them | KUN-01 and KUN-02 runs, accepted by ChatGPT QA |
| **ChatGPT scientific QA** | ChatGPT's recorded recommendation, with a link | ChatGPT PM / independent QA |
| **Owner approval and canonical adoption** | Two records: a **pre-merge approval record** (owner choice, date, approval link, effective scope, exact reviewed head SHA) and, after the owner-authorized merge, a **post-merge adoption receipt** (merge SHA and date). The entry becomes canonical only at that merge | Sabpuja (owner) |

A ChatGPT QA PASS of an evidence package is **not** an owner approval. An owner approval is **not** an implementation authorization: every code change still needs its own scoped draft PR, QA and merge authorization ([implementation sequence](KUN-02-P2-implementation-and-risks.md)).

## Evidence classes

The evidence is labelled with the classes used in KUN-02. None of them is independent observational astronomy.

- **SWISS_CONFORMANCE:** the Python integration agrees with Swiss Ephemeris itself (binding, `swetest` CLI, or Swiss internals). Swiss-on-Swiss.
- **INDEPENDENT_MATHEMATICS:** an independently coded formula (for example spherical trigonometry or the classical Navamsa rule) applied to Swiss inputs.
- **TIMEKEEPING:** checks against IANA tz and IERS leap-second records.
- **ENGINE_BEHAVIOUR:** what the current engine accepts, refuses and outputs.

No golden-chart tolerance has been frozen, and no claim of astronomical accuracy is made anywhere in this package.

## Already approved (unchanged by PR #20 and by later status reconciliation)

| ID | Approved choice | Status |
|---|---|---|
| SCI-01b | Mean Rahu = the adjusted mean lunar node of the pinned Swiss Ephemeris `MEAN_NODE` | OWNER APPROVED 2026-10-22, unchanged |
| SCI-01c | Ketu = mean Rahu + exactly 180°, normalized cyclically, classified from the unrounded Rahu | OWNER APPROVED 2026-10-22, unchanged |

The text of these two entries in `DECISIONS.md` was not edited by PR #20 or by the later status syncs.

## Decision matrix

| ID | Proposed convention (exact) | Changes current numbers? | Changes accepted inputs? | Evidence | ChatGPT scientific QA | Owner approval |
|---|---|---|---|---|---|---|
| SCI-01a | Swiss `SE_SIDM_LAHIRI` (mode 1): 23°15′00.658″ at 1956-03-21 0h TT, true ayanamsha, Swiss default precession; `set_sid_mode(SIDM_LAHIRI, 0, 0)` and `set_ephe_path` on every request under the Swiss lock | No | No | KUN-02 A5, A11, Lahiri-definition probe; KUN-01 probe [1]; PR #18 conformance | Supports direction (PR #19 final QA) | **OWNER APPROVED / CANONICAL - 2026-10-24**, ledger row 10 |
| SCI-01d | Geocentric, apparent, true ecliptic and equinox of date, minus the true ayanamsha: `calc_ut(jd_ut, body, FLG_SWIEPH \| FLG_SIDEREAL)`, no other flags; fail closed if `FLG_SWIEPH` is not returned | No | No | KUN-02 planet-frame probe; KUN-01 probes [2], [10], [11]; PR #18 882/882 | Supports direction (PR #19 final QA) | **OWNER APPROVED / CANONICAL - 2026-10-24**, ledger row 11 |
| SCI-01e | Sidereal Lagna = `ascmc[0]` of `houses_ex(jd_ut, lat, lon, b"W", FLG_SIDEREAL)`. **Only together with or after SCI-01g** | No (bit-identical wherever `b"P"` works) | Not with SCI-01g; alone it would accept polar births | KUN-02 A1–A8, A12; KUN-01 probes [4]–[6] | Favoured, only paired with or after SCI-01g (PR #19 final QA) | **OWNER APPROVED / CANONICAL - 2026-10-24**, ledger row 4 (with SCI-01g) |
| SCI-01f | D1 house = whole sign from the Lagna Rashi; Navamsa = 108 equal 3°20′ segments mapped cyclically from Mesha; D9 Lagna = Navamsa sign of the unrounded Lagna; D9 house = whole sign from the D9 Lagna. All from unrounded values | No. D9 house fields are not implemented in schema 0.2.0 and are deferred (SCI-02) | No | KUN-02 A8–A10; PR #18 rule oracle | Supports direction (PR #19 final QA) | **OWNER APPROVED / CANONICAL - 2026-10-24**, ledger row 12; D9 house fields not implemented (deferred) |
| SCI-01g | Supported latitude −66.0 ≤ lat ≤ +66.0 inclusive, refused outside with `LATITUDE_OUTSIDE_SUPPORTED_BAND`, independent of date | No inside the band | Yes: refuses 66.0° < \|lat\| < 89° (some of which is accepted today, depending on date) | KUN-02 A3, A4, envelope §2 | Favoured as a fixed product envelope (PR #19 final QA) | **OWNER APPROVED / CANONICAL - 2026-10-24**, ledger row 3 |
| SCI-01h | Keep: civil UTC (from the IANA offset) passed to Swiss as UT1; TT = UT1 + Swiss ΔT. Kept only as an explicitly disclosed approximation; label the assumption by era in metadata; review on any CGPM/CIPM/IERS change (CGPM 2026 Resolution 5 applies from 2027-05-20) | No | No | KUN-02 B3, time-scale and sidereal-time probes; KUN-01 probes [8], [9] | Honest epoch-specific metadata required (PR #19 final QA) | **OWNER APPROVED / CANONICAL - 2026-10-24**, ledger row 13 (P7 status under SCI-01h below) |
| SCI-02 | First engineering integration baseline = schema 0.2.0: D1 sidereal longitude, Rashi and whole-sign house for Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, mean Rahu, Ketu; Lagna longitude, Rashi and D9 sign; D9 sign of every body; Moon Rashi, Nakshatra and Pada; calculation metadata. Deferred: D9 whole-sign house fields; Nakshatra/Pada for all bodies and the Lagna | No (baseline as implemented) | No | KUN-02 A10; PR #18 rule oracle | Supports direction; no new approval (PR #19 final QA) | **OWNER APPROVED / CANONICAL - 2026-10-24**, ledger row 9: chart schema 0.2.0 engineering integration baseline only, not the complete KUN-F06 D9 requirement |
| SCI-03 | Local civil birth date 1900-01-01 to 2100-12-31 inclusive; explicit offset validated against IANA; gaps refused, folds disambiguated by the given offset; pinned tzdata with a TZif byte manifest and deterministic loading; `HISTORICAL_CLOCK_UNVERIFIED` fail-closed for every zone before 1970-01-01 including Kolkata 1956–1969 (owner-selected Option B; A and C not selected); location-based zones only (D3 v2); future dates disclosed as projected | Only at the date edges | Yes: edge dates and gated historical births | KUN-02 B1, B2, C1, T01–T63, tzdata probe | Local-date window, pinned TZif and temporary pre-1956 minimum endorsed (PR #19 final QA; the minimum is superseded by the owner's Option B) | **OWNER APPROVED / CANONICAL - 2026-10-24**, as separate selections: ledger rows 2 (Option B), 5 (date window), 6 (P5 D1–D4), 7 (P8 G1–G5), 8 (D3 v2) and 14 (tzdata C6). DATA-01 remains open |

The "Owner approval" column above shows canonical status. *Historical:* it read PENDING until the separately authorized merge and adoption receipt. **Current:** each row is canonical from 2026-10-24 (merge `5b71408`, [receipt 6383419093](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/20#issuecomment-6383419093)), only to the scope of the ledger row(s) cited. The owner selections themselves, with their records and dates, are in the [owner pre-merge selection ledger](../DECISIONS.md#owner-pre-merge-selection-ledger).

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

- **Exact setting.** `swe.calc_ut(jd_ut, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)` for SUN, MOON, MARS, MERCURY, JUPITER, VENUS, SATURN and MEAN_NODE. No `FLG_TOPOCTR`, `FLG_TRUEPOS`, `FLG_NOABERR`, `FLG_NOGDEFL`, `FLG_NONUT` or `FLG_EQUATORIAL`. Refuse the request if the returned flags lack `FLG_SWIEPH` (no silent Moshier fallback). As implemented at Gate 1 `c3cb040` this refusal is an uncoded `RuntimeError`, not the typed `EphemerisDataError` path first proposed here; typing it is a separate owner-authorized hardening task. This is geocentric, apparent (light-time, annual aberration, gravitational deflection), on the true ecliptic and equinox of date, minus the true ayanamsha.
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
- **Known limitations.** Evidence is Swiss-on-Swiss plus independent formula; no golden-chart Lagna tolerance is frozen. The PR #18 suite compares `swetest` with `-house…,P`; after P3 it must also compare with `W` (documented blind spot; addressed in the versioned KUN-03 conformance profile of draft PR #33, contained in Gate 1 `c3cb040`, which uses a `W` reference). Swiss 2.10.03 sidereal time steps by −1.908″ at 2050-01-01 0h UT (Lagna about −1.7″ at New Delhi), a version-specific model switch.
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
- **Effect on existing results.** D1 and D9 signs unchanged. D9 house fields are **not implemented** in schema 0.2.0 and are deferred by the owner's SCI-02 selection; the D9 house formula above applies only if a separately authorized milestone builds them.
- **Input acceptance changes.** None.
- **Required regression tests.** Existing D1 house and D9 sign tests unchanged. When D9 house fields are separately authorized: D9 house oracle at all 108 Navamsa edges and their float neighbours (as KUN-02 A10), output schema version bump and contract test (P6).

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

- **Exact setting.** Keep the pipeline, **only as an explicitly disclosed approximation**: local wall time and explicit offset → validated against IANA → civil UTC → `swe.julday(UTC, Gregorian)` → passed to Swiss as UT (= UT1 for Swiss). Planet positions use TT = UT1 + Swiss automatic ΔT (`deltat_ex`, Swiss files; reset to automatic on every request). Do **not** switch to `swe.utc_to_jd` now. Record in metadata, by era:
  - **1900–1960:** a civil clock reading converted with IANA's offset; no UTC existed before 1961; UT1 is a reconstruction.
  - **1961–1971:** UTC with frequency offsets and steps; UT1 − UTC for this era is not sourced here (KUN-01 PG-5 open).
  - **1972 to the start of continuous UTC:** leap-second UTC; the IERS rule kept \|UT1 − UTC\| < 0.9 s. In KUN-02 this is only *implied under the Swiss ΔT model* together with the IERS TAI − UTC list (largest 0.81 s), **not measured** Earth orientation, and not a guaranteed error bound of this engine.
  - **From 2027-05-20 (continuous UTC):** the 28th CGPM (2026), Resolution 5 (BIPM, https://www.bipm.org/en/cgpm-2026/resolution-5) decides that continuous UTC becomes effective on 20 May 2027 and that the maximum value of \|UT1 − UTC\| will be 3 600 seconds. This is a permitted **policy ceiling**, not a measured offset and not an engine error. The resolution text reviewed gives the date only; the effective hour is **not** assumed here and must be substantiated before any boundary is frozen. *Status 2026-10-24:* for the P7 metadata implementation only, the owner's Option 2 ([6381685709](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/20#issuecomment-6381685709)) replaced that prerequisite. Eras are reported by UTC date, an owner-approved reporting convention; this is not a statement that the official transition occurs at 00:00 UTC. The official effective hour remains unresolved. The 0.9 s rule must not be stated for instants from that date. Resolution 5 supersedes the earlier 27th CGPM (2022) Resolution 4 (https://www.bipm.org/en/cgpm-2022/resolution-4), which had said only that the limit would be increased in, or before, 2035.
  - **Pinned leap-second-list expiry (2027-06-28):** a separate event: the IERS `leap-seconds.list` shipped with tz 2026e expires then. After it, leap-second and UT1 − UTC values are not records. Swiss's extrapolated ΔT implies −1.32 s (2035), −5.40 s (2050), −24.0 s (2100) if no further leap second occurs: model projections, not limits.
  - **2050-01-01 0h UT:** Swiss 2.10.03 switches its default sidereal-time model (−1.908″ step; Lagna about −1.7″ at New Delhi). Version-specific behaviour, recorded as a convention.
  - ΔT: tabulated to 2028 in Swiss (`TABEND 2028`), extrapolated after; upstream says future ΔT "cannot be calculated with accuracy".
- **Alternatives evaluated.** `swe.utc_to_jd` (moves 1972–2029 inputs by at most 0.39 s, up to 0.95 s in 2030–2033 under its no-new-leap-second assumption; identical before 1972 and from 2034). A pinned IERS UT1 − UTC table (more data to maintain; no category change in samples). TT from the leap-second list (exact after 1972 for TT; does not help UT1).
- **Supporting evidence.** E-B3 (Swiss accepts `23:59:60` on all 27 IERS leap dates and refuses 4 non-leap controls; implied UT1 − UTC within 0.9 s at 110 half-year epochs 1972–2026, Swiss-model consistency). E-SIDT (Swiss sidereal time agrees with an independent IERS 2010 eq. 5.32 expression to 0.0027″ before 2050). E-CLOCK (0.9 s of clock error changed no Lagna or Moon category in 2,000 samples, max Lagna shift 0.0054°). E-K01-8/9.
- **Upstream references.** `doc/swisseph.htm` §7 (time scales, ΔT) and §6.1 (sidereal time); `swedate.c` lines 366–371; `swephlib.c` lines 3460–3481; IERS `leap-seconds.list` via tz 2026e (SHA-256 `db5a895f…3433`, expires 2027-06-28); IERS Conventions 2010 eq. 5.32; BIPM CGPM 2022 Resolution 4.
- **Known limitations.** No measured UT1 − UTC series is used. The real accuracy risk before 1970 is the historical clock (SCI-03), not the time scale. Resolution 5 was read at the BIPM page on 2026-10-24; that page does not show the adoption date or the exact effective hour. *Historical (Gate 1 `c3cb040`):* the runtime metadata was outdated. `src/sabpuja_kundali/provenance.py` labelled 1972 to 2027-06-28 with the 0.9 s IERS rule, cited the 2022 "in or before 2035" wording, and had no boundary at 2027-05-20. It was not edited by the documentation PR, and a separately owner-authorized P7 metadata disclosure and era-boundary correction, with boundary tests and independent QA, was required before integration into `main`. **P7 status (2026-10-24):** completed on the isolated `integration/kun03-gate1` at `cacd482776366faa9b7d99ceddb16b10ed900b67` (PR #36). Calculation `metadata_schema` is `sabpuja-calculation-metadata/3`, and chart `schema_version` stays 0.2.0. It passed scoped independent QA ([6382789595](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/36#issuecomment-6382789595)) and is **not merged into `main`**. P7 discloses metadata only; it changes no astronomical numerical rule and provides no independent astronomical accuracy. The pinned leap-second-list expiry on 2027-06-28 remains a separate event.
- **Effect on existing results.** None.
- **Input acceptance changes.** None.
- **Required regression tests.** Metadata contract test for the era label (P7). For the separately authorized P7 correction: both sides of the substantiated 2027-05-20 effective instant (19/20 May 2027, by UTC instant, including a local IST case either side) and of the 2027-06-28 list expiry, with chart values byte-identical before and after. *(As implemented under Option 2 on Gate 1: both sides of the 2027-05-20 and 2027-05-21 UTC-date boundaries and of 2027-06-28, in UTC and IST, with chart values unchanged; evidence on PR #36.)* Pin the 2050 step value as a recorded Swiss behaviour (KUN-02 `test_swiss_sidereal_time_step_at_2050_is_recorded`). Re-run the B3 consistency check whenever tzdata's `leap-seconds.list` or Swiss is updated.

## SCI-02: MVP calculation scope

- **Owner selection (2026-10-24, C1 Option A; selected pre-merge, canonical since the 2026-10-24 adoption, ledger row 9):** chart schema 0.2.0 as implemented at Gate 1 `c3cb040` is the first **engineering integration baseline**. The deferred fields below remain deferred. It does not satisfy or certify the complete KUN-F06 D9 product requirement and is not independent astronomical validation.
- **Baseline scope.** Outputs, all from unrounded values:
  - D1: sidereal longitude, Rashi and whole-sign house for Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, mean Rahu (SCI-01b), Ketu (SCI-01c).
  - Lagna: sidereal longitude and Rashi (SCI-01e).
  - D9: Navamsa sign of every body and the Lagna (SCI-01f).
  - Moon: Rashi, Nakshatra (27 × 13°20′ from sidereal 0°) and Pada (4 × 3°20′).
  - Metadata (P7): ayanamsa definition, node, frame, house model, ascendant vehicle, time-scale era label, Swiss version, ephemeris manifest SHA-256, tzdata version and TZif manifest SHA-256.
- **Deferred to separately authorized milestones (P6 or successors):** D9 whole-sign house fields (SCI-01f formula); Nakshatra and Pada for every body and the Lagna (same rule, no new astronomy). Each needs a schema version, rule fixtures, numerical QA and backward-compatibility evidence.
- **Deferred (each needs its own spec, fixtures and decision):** Vimshottari Dasha; other divisional charts; Bhava Chalit; Yogas, Doshas, Gun Milan; Panchang; Uranus, Neptune, Pluto; upagrahas; retrograde, combustion, planetary war; true node; topocentric options; South Indian layout.
- **Alternatives evaluated.** Moon-only Nakshatra (today) versus all bodies; including Dasha in MVP (delays accuracy QA, per `DECISIONS.md` SCI-02 row).
- **Supporting evidence.** E-A10; E-RULE18; E-SC18 (categories from `swetest` values match).
- **Upstream references.** `docs/PRD.md` KUN-F04 to KUN-F07; acceptance QA-007, QA-010, QA-012, QA-013.
- **Known limitations.** Category correctness near edges depends on unrounded values (tested). No independent golden-chart D9 fixtures yet (QA-012 open).
- **Effect on existing results.** None for the baseline. The deferred fields, if built, are additive.
- **Input acceptance changes.** None.
- **Required regression tests.** The baseline keeps its existing tests. For the deferred fields: output schema contract test with a version bump; D9 house and all-body Nakshatra oracles at every edge; existing outputs unchanged.

## SCI-03: supported dates, time zones and historical clocks

- **Exact setting.**
  1. **Date window** (ledger row 5): the local civil date of the supplied wall-clock time must be within 1900-01-01 … 2100-12-31 inclusive, checked **before** conversion. Code `DATE_OUTSIDE_SUPPORTED_RANGE`. The UTC instant then lies within 1899-12-31T10:00Z … 2101-01-01T12:00Z, inside the pinned 1800–2399 data.
  2. **Offset and zone rules (kept; owner-selected P5 D1–D4 and D3 version 2, ledger rows 6 and 8):** birthplace zones must be location-based: D3 version 2 refuses 49 identifiers (`Etc/*`, the UTC and GMT aliases, `Factory`, and `CST6CDT`, `EST5EDT`, `MST7MDT`, `PST8PDT`) and accepts 549, retaining the owner-reviewed aliases CET, MET, EET, WET, EST, MST and HST; any further identifier needs new owner authorization. An explicit UTC offset is required; it must equal one of IANA's offsets for that wall time in that zone. Wall time in a gap → `TIME_NONEXISTENT_LOCAL`; existing wall time with an offset IANA does not give → `TIME_OFFSET_MISMATCH`; a fold with a valid offset is accepted (the offset disambiguates). An interface without offsets must ask the user and never pick one silently (`TIME_AMBIGUOUS_LOCAL` reserved; QA-005).
  3. **tzdata reproducibility:** pin the PyPI `tzdata` package version and a committed SHA-256 manifest of the TZif bytes used (at least every zone accepted for births). Load deterministically: either set an empty `PYTHONTZPATH` in the service environment before the interpreter starts, or use an isolated loader (`ZoneInfo.from_file` on package resources, cached by the engine). **Never** call `zoneinfo.reset_tzpath()` or change global time-zone configuration in a live, multi-request process. Emit the tzdata version and the manifest hash in metadata. **Owner selection (2026-10-24, C6 Option A; canonical 2026-10-24, ledger row 14):** `tzdata==2026.5` (IANA 2026e); 598 TZif keys with a versioned manifest, manifest digest, per-zone size and SHA-256 checks and installed package/IANA-version checks; no host fallback; upgrades only through a separate owner-authorized PR with a new manifest, the 63 KUN-02 time cases, full regression and a changed-key report. The wheel SHA-256 is recorded and tested but not verified by the runtime loader. A fail-closed `verify_all()` startup gate is required in any future service.
  4. **Historical clocks (RG-HIST), owner-selected Option B (ledger rows 2 and 7, canonical 2026-10-24):** refuse **every** birthplace and zone whose local birth date is before 1970-01-01, including Asia/Kolkata 1956–1969, with `HISTORICAL_CLOCK_UNVERIFIED`, until DATA-01 verifies a place and date (exception table empty; P8 G1–G5). This is not proof of the clocks actually used anywhere, nor of correctness after 1970. No historical offset is invented. *(History: this item first proposed only Asia/Kolkata before 1956-01-01 as a temporary minimum, option (A) below; the owner's Option B supersedes it.)*
  5. **Future dates:** accepted, with the disclosure `FUTURE_CIVIL_TIME_PROJECTED` for births after the pinned IERS list expiry.
- **Additional pre-1970 regions (assessment).** Evidence that the risk is not limited to Asia/Kolkata:
  - IANA states that its pre-1970 data is not comprehensive historical-clock evidence (`theory.html`).
  - KUN-02 accepts IANA-modelled LMT, HMT and war-time offsets for Karachi, Dhaka, Kathmandu, Colombo and Yangon (T21, T23, T24, T61, T62); these rest on the same kind of source.
  - Two builds of the same tzdata 2026e (Ubuntu with `backzone`, PyPI without) disagree for 8 Asian zones before 1956 (Aden, Kuwait, Bahrain, Brunei, Phnom Penh, Vientiane, Muscat, Kuala Lumpur).

  Options presented to the owner (all fail closed with `HISTORICAL_CLOCK_UNVERIFIED`, all by local civil birth date, none invents an offset). **The owner selected (B) pre-merge on 2026-10-22** ([record](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/20#issuecomment-6336254894)); (A) and (C) are kept as history and are not selected. *Historical:* canonical adoption was PENDING until 2026-10-24; (B) is now canonical (ledger row 2):

  | Option | Refused until DATA-01 verifies the place and date | Known residual risk (accepted without DATA-01 evidence) |
  |---|---|---|
  | **(A) Temporary minimum** | Asia/Kolkata before 1956-01-01 | Asia/Kolkata 1956-01-01 to 1969-12-31; every other zone before 1970 |
  | **(B) All unverified pre-1970 clocks** | **Every** birthplace and IANA zone before 1970-01-01, **including Asia/Kolkata 1956-01-01 to 1969-12-31** | none of the pre-1970 kind (IANA's post-1970 rules remain a model) |
  | **(C) Regional** | (A), plus Asia/Karachi, Asia/Dhaka, Asia/Kathmandu, Asia/Colombo, Asia/Yangon and Asia/Thimphu before 1970-01-01 | Asia/Kolkata 1956–1969; every zone outside South Asia before 1970 |

  **Reduction in historical birth-date coverage.** The proposed window, 1900-01-01 to 2100-12-31, spans 201 years. Until DATA-01 adds verified exceptions:

  | Option | Asia/Kolkata births accepted from | Other South Asian zones accepted from | All other zones accepted from |
  |---|---|---|---|
  | (A) | 1956-01-01: 1900–1955 lost, 56 years (28% of the window) | 1900-01-01: nothing lost | 1900-01-01: nothing lost |
  | (B) | 1970-01-01: 1900–1969 lost, 70 years (35%), 14 years more than (A) | 1970-01-01: 70 years lost | 1970-01-01: 70 years lost |
  | (C) | 1956-01-01: 56 years lost | 1970-01-01: 70 years lost | 1900-01-01: nothing lost |

  These figures are calendar coverage only. No evidence here estimates how many users or births fall in the refused years, so no user-impact figure is claimed. Under (B), for example, nobody born in India before 1970 gets a chart until DATA-01 verifies their place and date.

  **Recommendation for public release: (B)**, matching ChatGPT's scientific-policy recommendation on [PR #20](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/20#pullrequestreview-5610686390). It is the only option that follows IANA's statement that pre-1970 records are not sufficient for actual local history (https://www.iana.org/time-zones/theory). It deliberately gives up the coverage shown above, and that should be presented to users and the owner as a product trade-off. (B) contains (A). The owner selected (B) pre-merge on 2026-10-22, and it became canonical on 2026-10-24 with the register merge `5b71408` and [receipt 6383419093](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/20#issuecomment-6383419093). No DATA-01 exception is approved, so the 1900–2100 supported date envelope does not imply accepted pre-1970 historical-clock coverage.

  The gate is a versioned table (zone, local-date start, local-date end, policy), reviewed and approved like any decision.
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
- **Known limitations.** IANA is a model of civil time, not a record of every household clock. The gate is coarse by design. Future civil-time rules are projections. Zone-to-coordinate consistency is not validated (any accepted zone is taken with any in-range coordinates) until a separate DATA-01 gazetteer package. The 1900–2100 window is a product computation envelope, not an accuracy certificate.
- **Effect on existing results.** None for accepted charts inside the window, except that results stop depending on the host image's tzdata build.
- **Input acceptance changes.** Edge dates flip to the local-date rule; gated historical births are refused; non-RFC 3339 time strings refused by the strict format (P5).
- **Required regression tests.** KUN-02 T01–T63 with the proposed codes; first and last accepted local seconds in UTC+14 and UTC−12 zones; 29 February in 1900 and 2100 (refuse), 2000 and 2024 (accept); a DST gap and fold in both hemispheres; both sides of every gate edge; zones outside the gate unaffected; loaded TZif bytes match the manifest; identical output on two hosts (system tzdata with and without `backzone`); no stale cached zone after a reload.

---

## REL-01: release evidence policy (reconciling Swiss-first with the PRD and Acceptance Matrix)

**Status: OWNER APPROVED / CANONICAL - 2026-10-24** (owner selection 2026-10-22, [record](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/20#issuecomment-6336254894); ledger row 1; adopted by merge `5b71408` and [receipt 6383419093](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/20#issuecomment-6383419093)). It is not an SCI decision; it governs which evidence counts for the accuracy gates. Its edits to `PRD.md`, `ACCEPTANCE-MATRIX.md` and `DEVELOPMENT-ROADMAP.md` have been on `main` since that merge. **REL-01 adoption does not remove or satisfy the separate [PR #1 hold](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/1#issuecomment-6323581875) (independent reference-golden charts), and C7 remains unresolved.** *Historical:* until canonical adoption, `main`'s golden-chart requirements stood unchanged.

- **Why it is needed.** The owner approved the Swiss-first roadmap change on 2026-10-22 ([issue #15](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/15), [PR #17](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/17)). It made independent JPL/INPOP astronomy assurance optional and deferred, not a prerequisite for a limited launch subject to all other gates. *Historical (2026-10-22):* `main` then required independently sourced golden charts in `docs/PRD.md`, `docs/ACCEPTANCE-MATRIX.md` and `docs/DEVELOPMENT-ROADMAP.md`, so two sources of truth disagreed. PR #20 aligned them on 2026-10-24.
- **Proposed policy.**
  1. **Mandatory engineering-accuracy gates (release-blocking):**
     - pinned Swiss Ephemeris integration conformance against the separately built official Swiss CLI (`swetest`), same version and data, predeclared cases and tolerances (as PR #18);
     - independently coded mathematics for every chart rule: Rashi, Nakshatra, Pada, Navamsa, D1/D9 houses and the ascendant formula (as PR #18 rule oracle and PR #19 A6–A10);
     - boundary and refusal fixtures for each supported convention: 0/360, segment edges, date-window edges, DST gaps and folds, the latitude band and the historical-clock gate;
     - data and state safeguards: verified ephemeris files, no Moshier fallback, Swiss-state isolation, pinned tzdata;
     - truthful public claims: "calculated with Swiss Ephemeris 2.10.03 under the named conventions"; never "independently verified astronomy" unless item 2 is completed.
  2. **Optional independent astronomy assurance (not release-blocking):** JPL/INPOP comparison (KUN-01 PG-1), only for a separate independent-accuracy claim or a specific discrepancy escalation.
  3. **Unchanged mandatory gates:** location and time correctness, historical clocks (RG-HIST), security, privacy, accessibility, Hindi review, AGPL and data licensing, PDF, staging and the owner's release sign-off.
- **Gates changed by REL-01 (merged into `main` by PR #20 on 2026-10-24).** The middle column is the pre-adoption wording on `main` (historical); the right column summarizes the wording now on `main`:

  | Document | Requirement | Pre-adoption text on `main` (historical, short) | Proposed, now on `main` (summary) |
  |---|---|---|---|
  | `PRD.md` §3 | Product truth | "No numerical chart published as accurate without independently reviewed reference fixtures" | Mandatory engineering-accuracy gates; public wording limited to Swiss-based calculation unless optional assurance completed |
  | `PRD.md` §3 | Reference QA | "different source/process from implementation" | Same, naming the Swiss CLI and independent rules/formulae (mandatory) and JPL/INPOP (optional) |
  | `PRD.md` §4 | KUN-F04 | "independent accuracy QA" | "the REL-01 accuracy gates" |
  | `PRD.md` §4 | KUN-F16 | "independently sourced golden-chart validation" | REL-01 mandatory gates; JPL/INPOP golden charts optional |
  | `PRD.md` §7 | Astronomy accuracy gate | "independent golden fixtures with no blocking deviations" | Swiss CLI conformance and independent rule/formula fixtures; JPL/INPOP only for an independent-accuracy claim. Owner approval before accurate-public claims is kept |
  | `ACCEPTANCE-MATRIX.md` | QA-009 | "independently sourced method-compatible golden charts" | Official Swiss CLI conformance at predeclared tolerances; JPL/INPOP differential optional |
  | `ACCEPTANCE-MATRIX.md` | QA-010 | "Independent golden chart + property tests" | Swiss CLI conformance + independent ascendant formula and rule oracle + property tests |
  | `ACCEPTANCE-MATRIX.md` | QA-012 | "independent reference fixtures" | Independently coded rule-oracle fixtures |
  | `ACCEPTANCE-MATRIX.md` | Evidence item 3, G-ENGINE | "External independent reference source/method"; "reference-suite assertions" | References as defined by REL-01 |
  | `DEVELOPMENT-ROADMAP.md` | KUN-01 row, CLAUDE-004, §6 definition of done, Gate A, risk register (Lagna) | independent charts / golden charts | REL-01 references; independent charts optional |

- **Release gates after canonical adoption (2026-10-24).** *Historical:* until 2026-10-24 every row above awaited canonical adoption of REL-01. Until then the `main` wording stood: independent golden-chart validation was required before accurate public claims, and the public-release gate was not relaxed. The edits were to be removed if the owner approved the SCI rows but not REL-01; that condition no longer applies. **Current:** REL-01 is canonical and the edits above are on `main`. This does not lift the PR #1 independent-reference hold, does not decide C7, satisfies no QA row and authorizes no release. Every other release gate stays as written.
- **What REL-01 does not do.** It does not claim that Swiss-on-Swiss conformance is independent astronomy. It does not freeze a tolerance. It does not satisfy any QA row: every QA-### stays NOT RUN until evidence for an exact SHA is reviewed. It does not change the PR #1 hold or decide C7. It does not touch any other gate.

---

## Consistency review of earlier evidence

The KUN-01 and KUN-02 evidence was checked for contradictions and unsupported conclusions. The findings are in the [evidence map](KUN-02-P2-evidence-map.md#consistency-review). In short:
- No contradiction changes any recommendation.
- Two numbers differ between KUN-01 and KUN-02 because they come from different samples (Lagna rate at 66°; Lagna shift of a 38.5-minute clock error). Both are sample statistics, not bounds; this package quotes KUN-02's larger sample.
- Three items are aligned here:
  - **Refusal code name:** `LATITUDE_OUTSIDE_SUPPORTED_BAND` (KUN-02), not `LATITUDE_OUTSIDE_VALIDATED_BAND` (KUN-01).
  - **Time-scale wording:** KUN-01's "UT1 − UTC within ±0.9 s" is read as the leap-second-era IERS rule, not a measurement; it does not apply from 2027-05-20 under CGPM 2026 Resolution 5 (see SCI-01h).
  - **Historical offset:** KUN-01's "Bombay Time about +04:51" is not used. No sourced offset exists in this evidence.
