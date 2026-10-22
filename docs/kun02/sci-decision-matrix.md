# Workstream D: proposed final SCI decision matrix

**Status:** RECOMMENDATIONS ONLY. Every row below is **PENDING** except SCI-01b and SCI-01c, which the owner approved on 2026-10-22 and which this package preserves unchanged. ChatGPT performs independent QA and finalizes recommendations; only the owner approves, and approvals are recorded in `main:docs/DECISIONS.md` (SP-KUN-DEC-001), not here.
**Base:** `d8193c692d52aa12595f81c227638a061605a3d9`. Builds on the KUN-01 package (draft PR #11, `d4e9d9e`), which this matrix updates with KUN-02 evidence.

Evidence IDs (A1–C1) are the runner invariants in [README.md](README.md). Every "changes numbers?" answer refers to the current foundation output.

## Summary

| ID | Recommended convention | Changes numbers? | Changes accepted inputs? | Main evidence |
|---|---|---|---|---|
| SCI-01a | Swiss `SE_SIDM_LAHIRI` (mode 1), true ayanamsha, Swiss default precession, set on every call | No | No | A5, A11, Lahiri definition probe |
| SCI-01b | **Approved:** Swiss mean node | — | — | preserved |
| SCI-01c | **Approved:** Ketu = Rahu + 180° exactly | — | — | preserved |
| SCI-01d | Geocentric, apparent, true ecliptic and equinox of date, minus true ayanamsha | No | No | planet-frame probe |
| SCI-01e | Lagna = `ascmc[0]` of `houses_ex(jd_ut, lat, lon, b"W", FLG_SIDEREAL)` | No (bit-identical where defined) | Only with SCI-01g; alone it would accept polar inputs | A1–A8, A12 |
| SCI-01f | D1 whole-sign houses from the Lagna Rashi; D9 Lagna = Navamsa of the Lagna; D9 whole-sign houses from the D9 Lagna | No for D1; adds D9 houses | No | A8–A10 |
| SCI-01g | Support \|lat\| ≤ 66.0° inclusive, refuse outside with a fixed code; disclose above 60° | No inside the band | Yes: refuses 66.0° < \|lat\| < ~66.55° (accepted today on some dates) | A3, A4, envelope §2 |
| SCI-01h | Civil UTC used as UT1; TT from Swiss ΔT; disclose by era; revisit before 2035 | No | No | B3, time-scale probe |
| SCI-02 | D1 + D9 (incl. D9 Lagna and D9 houses), Moon Rashi, Moon Nakshatra/Pada, method metadata; Nakshatra for all bodies an owner option | Adds fields | No | A10 |
| SCI-03 | Local civil date window 1900-01-01–2100-12-31; RG-HIST fail-closed for Asia/Kolkata before 1956-01-01 (minimum); pinned tzdata; future-date disclosure | Only at the edges | Yes | B1, B2, T46–T51, C1, tzdata probe |

---

## SCI-01a: Lahiri ayanamsa definition

- **Recommended:** Swiss Ephemeris mode 1, `SE_SIDM_LAHIRI`, "23°15′00.658″ at 1956-03-21 0h TT (IAE 1985 revision), true ayanamsha, Swiss default precession (Vondrák 2011) with Swiss's built-in precession offset". Name it exactly that way in output metadata.
- **Alternatives:** mode 1 with `SIDBIT_PREC_ORIG` (IAU 1976 precession; upstream calls it a test option that reduces ephemeris accuracy); mode 1 with `SIDBIT_NO_PREC_OFFSET`; mode 46 Lahiri ICRC (−1.09″ at J2000); mode 43 Lahiri 1940 (−53.17″); mode 44 Lahiri VP285 (+23.00″); Krishnamurti (−348.67″); Raman (−5,206.68″).
- **References:** Swiss `doc/swisseph.htm` §2.8.5 and Appendix "How to compare the Swiss Ephemeris Lahiri Ayanamsha with IAE"; `sweph.h:387`; IAE 1989 p.556 footnote and IAE 2019 p.429 as quoted there (secondary source).
- **Evidence:**
  - At the defining epoch the default mode-1 true ayanamsha is the definition +0.138″ (Swiss's precession offset); with `SIDBIT_NO_PREC_OFFSET` +0.008″; with `SIDBIT_PREC_ORIG` +0.0000016″. So the literal epoch value is reproduced only by the test option.
  - Against mean ayanamsha values attributed to IAE (quoted in the Swiss documentation, not read from IAE here): +0.073″ (1989.0), +0.044″ (1990.0), +0.002″ (2000 Jan 1 12h TT). KUN-01 measured the default-versus-`PREC_ORIG` difference at ≤ 0.31″ over 1900–2100.
  - A5: the same true ayanamsha is subtracted from the Lagna (≤ 1.4e-7″) and from every planet (≤ 4.1e-10″).
  - A11: an unset sidereal mode silently gives Fagan/Bradley (−0.883°), and `SIDBIT_PREC_ORIG` leaks across `set_sid_mode` calls; the engine's per-call `set_ephe_path` + `set_sid_mode` under its lock prevents both.
- **Consequences:** no numeric change. The 0.31″ maximum difference from the IAE-reproducing variant equals about 0.5 s of Moon motion, far below birth-time precision.
- **Implementation implications:** none to the calculation; metadata text only (implementation plan P7). Keep the per-call reset and its regression test.

## SCI-01d: planetary coordinate frame

- **Recommended:** geocentric, apparent (light-time, aberration, deflection), referred to the true ecliptic and equinox of date, minus the true Lahiri ayanamsha: Swiss `calc_ut(jd_ut, body, FLG_SWIEPH | FLG_SIDEREAL)` with no other flags.
- **Alternatives (KUN-01 sizes):** topocentric (Moon up to 1.02°), geometric/astrometric (Sun 20.8″, Mars 39.0″), `SIDBIT_ECL_T0` or `SIDBIT_SSY_PLANE` projections (research modes), mean ayanamsha (up to 18.78″, measured here).
- **References:** Swiss `doc/swisseph.htm` §2.8.12 "On which ecliptic is the ayanamsha measured?"; KUN-01 `scientific-decisions.md` SCI-01d.
- **Evidence:** sidereal = tropical − true ayanamsha to 4.1e-10″ for all eight bodies on 2,000 random instants; minus the mean ayanamsha it differs by up to 18.776″ (nutation in longitude), proving the true ayanamsha is used.
- **Consequences:** none. Any independent reference must be converted the same way (nutation cancels; the result is effectively mean equinox minus mean ayanamsha).
- **Implementation implications:** none; record the frame in metadata.

## SCI-01e: Ascendant calculation

- **Recommended:** sidereal Lagna = `ascmc[0]` of `swe.houses_ex(jd_ut, lat, lon, b"W", swe.FLG_SIDEREAL)`, Lahiri set and path reset on every call under the lock. Definition unchanged: the tropical ecliptic point rising on the eastern horizon at the given UT1 (apparent sidereal time, true obliquity, geographic latitude), minus the true ayanamsha.
- **Alternatives:** keep `b"P"` (date-dependent refusal at 66.5467°–66.5752°); `b"E"` or `b"O"` (also identical, KUN-01); compute it ourselves from ARMC (would duplicate Swiss and lose the polar convention).
- **References:** `swehouse.c` at `c69c14a` (lines 229, 535–587, 973, 994–1001, 1830–1834); `doc/swisseph.htm` §6.4.
- **Evidence:** A1 (167,612 bit-identical comparisons of ascendant, MC and ARMC), A2, A3, A4 (P fails exactly at 90° − ε_true), A5, A6 (independent trigonometry ≤ 1.2e-5″), A7 (always the rising point, also beyond the polar circle), A8, A12 (engine output equals the W value in all accepted cases).
- **Consequences:** no numeric change anywhere P works. On its own it would start accepting births between the polar circle and ±89°, so it must not ship before SCI-01g.
- **Implementation implications:** one-line change plus regression tests (plan P3), after P2.

## SCI-01f: D1/D9 house conventions

- **Recommended:** D1 house = whole-sign count from the Lagna Rashi, from unrounded values (as today). D9 Lagna = Navamsa sign of the unrounded Lagna (as today). D9 house of a body = whole-sign count from the D9 Lagna (new output). Navamsa = 108 equal 3°20′ segments mapped cyclically from Mesha (as today), which equals the classical element rule.
- **Alternatives:** equal houses from the Lagna degree; Sripati/Bhava Chalit (deferred to P1 as a separate labelled chart); sidereal Placidus.
- **References:** KUN-01 SCI-01f; `rules.py`.
- **Evidence:** A8 (W cusps are the Rashi starts), A9 (Lagna Navamsa sweep, 326 crossings, 0 failures), A10 (90,720 checks: rules versus W cusps versus the classical rule, D9 houses, P versus W; 0 mismatches).
- **Consequences:** D1 unchanged; D9 houses are an additive field.
- **Implementation implications:** schema addition (plan P6), with fixtures at Navamsa edges.

## SCI-01g: Latitude policy

- **Recommended:** support \|lat\| ≤ 66.0° inclusive; refuse outside with `LATITUDE_OUTSIDE_SUPPORTED_BAND` regardless of date; add a high-latitude sensitivity disclosure above 60°.
- **Alternatives:** keep today's date-dependent behaviour; accept to ±89° after SCI-01e with polar fixtures; narrower ±60°.
- **References:** envelope report §2; lagna report §3.3, §3.5.
- **Evidence:** polar-circle latitude 66.546714°–66.575237° over 1900–2100 (margin ≥ 0.5467°); P refuses 66.55° in 1900 but not in 2100; Lagna rate 634″/s at 66° versus 21.5″/s at New Delhi.
- **Consequences:** all of India and nearly all populated places supported; births above 66° refused by a predictable rule; inputs between 66.0° and the polar circle that are accepted today become refused.
- **Implementation implications:** validation change plus refusal-code tests (plan P2).

## SCI-01h: UTC/UT1 time policy

- **Recommended:** keep "civil UTC passed to Swiss as UT1; TT = UT1 + Swiss ΔT" for MVP; disclose by era (pre-1972 reconstruction; 1972–2027 within the 0.9 s IERS rule, here only implied under the Swiss ΔT model and not measured; after the IERS list expiry projected; from 2035 at the latest no 0.9 s bound by rule); record the assumption in metadata; review before 2035.
- **Alternatives:** `swe.utc_to_jd` (moves inputs by −0.21 s to +0.39 s for 1972–2030, up to −0.95 s in 2030–2033, identical otherwise); a pinned IERS UT1−UTC table (more data to maintain, no product-visible gain).
- **References:** `doc/swisseph.htm` §7; `swedate.c` lines 366–371; IERS leap seconds via tz 2026e `leap-seconds.list`; IERS Conventions 2010 eq. 5.32; 27th CGPM (2022) Resolution 4, https://www.bipm.org/en/cgpm-2022/resolution-4: the maximum permitted UT1 − UTC will be increased in, or before, 2035 (confirmed by the ChatGPT reviewer at that page on 2026-10-22; not fetchable from this environment).
- **Evidence:** B3 (Swiss leap seconds equal the IERS list; UT1 − UTC *implied under the Swiss ΔT model* within 0.9 s for 1972–2026, a model-consistency check, not observed UT1); 0.9 s of clock error changed no category in 2,000 samples (max Lagna shift 0.0054°); Swiss sidereal time agrees with IERS 2010 to 0.0027″ before 2050 and steps −1.908″ at 2050-01-01.
- **Consequences:** none numerically; honest disclosure.
- **Implementation implications:** metadata only (plan P7).

## SCI-02: MVP calculation scope

- **Recommended:** D1 sidereal longitudes, Rashi and whole-sign house for Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, mean Rahu, Ketu; Lagna longitude and Rashi; D9 sign for every body and the Lagna; **D9 whole-sign houses**; Moon Rashi, Nakshatra and Pada; method metadata (ayanamsa, node, house model, ascendant vehicle, time-scale note, Swiss and data versions, tzdata version). Owner option: Nakshatra/Pada for all bodies and the Lagna (same rule, no new astronomy).
- **Deferred:** Dasha, other divisional charts, Bhava Chalit, Yogas/Doshas/Gun Milan, Panchang, outer planets, upagrahas, retrograde/combustion, true node, topocentric options.
- **Evidence:** A10 shows the D9 house rule is consistent for P and W, the classical rule and the rules module.
- **Consequences:** additive schema; fixtures needed for D9 houses.
- **Implementation implications:** schema package (plan P6) after SCI-01f.

## SCI-03: supported dates and historical-clock policy

- **Recommended:**
  1. Window 1900-01-01 to 2100-12-31 by **local civil date**, inclusive.
  2. **RG-HIST** before any customer launch: fail closed (`HISTORICAL_CLOCK_UNVERIFIED`) for Asia/Kolkata births before 1956-01-01 as a **temporary minimum, conservative policy to protect the first MVP**, until a sourced, reviewed historical-clock list (DATA-01: historical birthplace, clock source, place-to-zone provenance, jurisdiction-specific date coverage; birth-time report §7) allows explicit user clock selection with no default. This is not proof that clocks from 1956 on, or elsewhere in India before 1956, kept IST: IANA says its pre-1970 records are not comprehensive historical-clock evidence (`theory.html`). Verified city exceptions come only through DATA-01. The owner decides whether the gate also covers other South Asian zones (Karachi, Dhaka, Colombo, Yangon, Kathmandu, Thimphu) and other pre-1970 zones.
  3. **Pin tzdata** (package version, TZif byte hashes and a deterministic loading policy) and emit its version in metadata. This is an **engineering reproducibility fix that depends on the SCI-03 policy**, not an astrological convention (plan P1).
  4. Births after the pinned IERS list expiry: accept with a projected-civil-time disclosure.
- **Alternatives:** keep the UTC-year rule; start at 1947 or 1956; widen to 1800–2399 (needs pre-1900 civil-time work); accept historical IST entries with only a disclaimer (not recommended: in the hypothetical scenario of a Mumbai LMT reading entered as IST, the 38.5-minute error would change the Lagna Rashi in 33% of samples).
- **References:** IANA tz 2026e `asia` (India section comments and Zone lines), `backzone`, `theory.html`; Swiss `doc/swisseph.htm` §7.
- **Evidence:** B1 (63 cases), B2 (74,864 probes, 0 mismatches), T46–T51 edge cases, C1, tzdata build disagreement for 8 Asian zones before 1956, clock-error impact table.
- **Consequences:** edge dates change; some historical births are refused until clock verification exists; results stop depending on the host OS tzdata.
- **Implementation implications:** plan P4 (local-date window), P5 (time refusal codes, strict format), P8 (RG-HIST gate), P1 (tzdata pinning).

## Decisions that remain with the owner

Each SCI row needs the owner's explicit choice. The questions that change scope or refusals are: SCI-01e/g together (W plus a ±66.0° band, or another band); SCI-02 (Nakshatra for all bodies); SCI-03 RG-HIST behaviour and scope (minimum Asia/Kolkata before 1956-01-01; fail closed first, verified-clock selection later); whether non-location zones (`Etc/*`, `UTC`) are refused for births.
