# KUN-01 scientific decision package: SCI-01, SCI-02, SCI-03

**Document ID:** SP-KUN-ACC-SCI | **Work package:** CLAUDE-003 / KUN-01 Phase A | **Status:** RECOMMENDATIONS ONLY, every decision PENDING
**Baseline:** `feat/initial-kundali-foundation-20261021` at `d8193c692d52aa12595f81c227638a061605a3d9`

This document recommends; it decides nothing. The only decision register is `docs/DECISIONS.md` on `main` (SP-KUN-DEC-001). An owner choice made from this package should be recorded there, with date and Git SHA, by whoever the owner authorizes. Until then every convention below, including the ones the foundation code already uses, is **provisional**.

Numbers quoted as "probe" come from [`evidence/convention_probes.py`](evidence/convention_probes.py) ([raw output](evidence/convention_probes.out)), run with pyswisseph 2.10.3.2 (Swiss Ephemeris 2.10.03) and the pinned `sepl_18.se1`/`semo_18.se1` files. **They compare Swiss Ephemeris with itself under different conventions.** They size how much each choice moves results. They are not accuracy evidence and are not reference values.

## Summary table

| ID | Item | Current foundation behaviour | Recommendation | Changes current output? |
|---|---|---|---|---|
| SCI-01a | Ayanamsa | `SIDM_LAHIRI` (Swiss mode 1) | Keep: Swiss mode 1, true ayanamsha, Swiss default precession | No |
| SCI-01b | Rahu | Mean node | Keep mean node | No |
| SCI-01c | Ketu | Rahu + 180° exactly, from unrounded Rahu | Keep | No |
| SCI-01d | Planet longitude | Geocentric, apparent, ecliptic of date, minus true Lahiri ayanamsha | Keep | No |
| SCI-01e | Sidereal Lagna | `houses_ex(..., b"P", FLG_SIDEREAL)` ascendant | Keep the definition; take it from `b"W"` instead of `b"P"` | No numeric change where it works today; removes date-dependent polar failure |
| SCI-01f | D1 houses | Whole sign from Lagna sign | Keep | No |
| SCI-01g | Latitude band | Accept -89 < lat < 89, then fail where Placidus fails (date dependent) | Validated band \|lat\| ≤ 66.0°, refuse outside with a fixed rule | Yes, for 66.0° < \|lat\| < ~66.6° and polar inputs (now refused by a stable rule) |
| SCI-01h | Time scale | Civil UTC passed to Swiss as UT1 | Keep for MVP, document ≤0.9 s limitation | No |
| SCI-02 | MVP scope | D1 + D9 sign per body and Lagna, Moon Nakshatra/Pada | D1, D9 incl. D9 Lagna and D9 whole-sign houses, Moon Rashi, Moon Nakshatra/Pada; Nakshatra/Pada for all bodies is an owner option | Adds fields only |
| SCI-03 | Date range | Rejects when **UTC** year outside 1900–2100 | Validated window 1900-01-01 to 2100-12-31 by **local civil date**; India pre-1956 local-time limitation disclosed | Yes, at the two edges only |

---

## SCI-01 Calculation conventions

### SCI-01a Lahiri ayanamsa variant

**What exists.** Swiss Ephemeris 2.10.03 ships several "Lahiri" modes. Their definitions, from `sweph.h` at the pinned upstream commit `c69c14a` and §2.8.5 of the upstream documentation:

| Swiss mode | Definition (upstream) | Difference from mode 1, 1900–2100 (probe [1]) |
|---|---|---|
| 1 `SIDM_LAHIRI` | 23°15'00.658" on 21 Mar 1956 0h TT, the value revised in Indian Astronomical Ephemeris (IAE) 1989 p. 556 "with effect from 1985". Swiss treats it as a **true** ayanamsha and carries it with its default precession (Vondrák 2011). | 0 |
| 1 with `SIDBIT_PREC_ORIG` | Same start value, carried with the original IAU 1976 precession. Upstream shows this reproduces IAE 2019 true ayanamsha tables to 0.1"; upstream calls it a test option that reduces ephemeris accuracy. | −0.30" to +0.31" |
| 46 `SIDM_LAHIRI_ICRC` | Calendar Reform Committee 1956 original, 23°15'00.0" before the 0.658" correction, Newcomb precession | −1.40" to −0.78" |
| 43 `SIDM_LAHIRI_1940` | Lahiri's *Panchanga Darpan* (1940) | −53.5" to −52.9" |
| 44 `SIDM_LAHIRI_VP285` | Mean Sun at 0° in 285 CE (preface to Lahiri's *Indian Ephemeris* 1980) | +22.7" to +23.3" |
| 5 Krishnamurti, 3 Raman | Different traditions, for scale only | about −5.8' and −1.45° |

**Recommendation.** Swiss mode 1 (`SIDM_LAHIRI`), true ayanamsha, Swiss default precession, exactly as the foundation code already calls it. Name it in output metadata as `Lahiri (Chitrapaksha), IAE 1985 definition, Swiss Ephemeris SE_SIDM_LAHIRI, true ayanamsha` rather than plain "Lahiri".

**Justification.**
- It is the Indian national standard lineage (ICRC 1956, IAE) and the default "Lahiri" in Swiss-based Jyotish software, so users comparing with other tools see the same convention.
- Its documented distance from the IAE IAU-1976 reproduction is at most 0.31" over the product window (probe [1]). The Moon moves that far in about 0.55 s (probe [7]), so it is negligible next to birth-time precision.
- Mode 1 with `SIDBIT_PREC_ORIG` would match IAE more closely, but upstream warns it degrades the ephemeris. Not worth it for ≤0.31".
- Modes 43, 44 and 46 are historically real but are not what Indian ephemerides publish today.

**Implications.** No change to current numbers. The independent ayanamsa reference (see [reference-sources.md](reference-sources.md), R-04 and R-05) must implement *this* definition, and the IAE published values are expected to differ by up to 0.31" plus their 0.05" rounding. That expectation is built into the tolerance (T-AYA) before any comparison is run.

**Owner question SCI-01a.** Do you approve "Lahiri = Swiss Ephemeris mode 1 (`SE_SIDM_LAHIRI`), 23°15'00.658" at 1956-03-21 0h TT, true ayanamsha, Swiss default precession" as Sabpuja's ayanamsa, with the IAE yearly tables as the published cross-check?

### SCI-01b Mean versus true Rahu

**Options.** Mean node (smooth, theory-defined) or true (osculating) node.

**Size of the choice (probe [3]).** Over 1900–2100 true minus mean ranges from −1.94° to +1.98°. Rahu's Rashi differs between the two in 3.15% of weekly samples and its Nakshatra in 7.15%.

**Recommendation.** Mean node, as the PRD proposes and the code does. It is smooth (always retrograde, no wobble) and exactly defined by a published polynomial, which makes it independently checkable. Practice is genuinely split: both mean and true nodes are in common use in Jyotish software and Panchangs, and this package does not claim one is "correct". True node remains a documented alternative; it should never be mixed in silently.

**Accuracy note.** JPL ephemerides contain no mean node. Upstream says Swiss computes it from Moshier's adjustment of ELP2000-85, deviating from ELP2000-85's mean node by 0 at J2000 and less than 20" across 3000 BCE–3000 CE, with estimated precision 1" relative to DE431. The independent reference for the mean node is therefore a published lunar-theory polynomial (R-06), and the tolerance (T-NODE) reflects that the mean node is a definition, not an observable.

**Owner question SCI-01b.** Do you approve **mean** Rahu for MVP? (If true node is wanted later, it is a separate, labelled option with its own fixtures.)

### SCI-01c Ketu

**Recommendation.** Ketu = chosen Rahu + 180° exactly, classified from the unrounded Rahu value with exact arithmetic (already merged in CLAUDE-002c). No credible alternative exists for a 180° opposition; the only real choice is mean versus true, which follows SCI-01b.

**Owner question SCI-01c.** Do you approve "Ketu is exactly opposite the approved Rahu, derived from the unrounded value"?

### SCI-01d Sidereal planetary longitude

**Current definition** (`calc_ut` with `FLG_SWIEPH | FLG_SIDEREAL`): geocentric, apparent (light-time, annual aberration, gravitational deflection), referred to the true ecliptic and equinox of date, minus the **true** ayanamsha. Probe [2] confirms the sidereal value equals tropical-of-date minus `get_ayanamsa_ex_ut` to 0.000000", and differs from tropical minus the mean ayanamsha by up to 18.7" (the nutation in longitude). So nutation cancels: sidereal longitude is effectively referred to the mean equinox of date minus the mean ayanamsha. Any reference must be converted the same way.

**Alternatives and size:**
- Topocentric instead of geocentric: Moon moves up to 1.02° (parallax), Moon Nakshatra changes in 3.87% of samples at New Delhi (probe [10]). Not standard for Parashari charts.
- Geometric instead of apparent: Sun 20.8", Mars 39.0", Saturn 27.3", Moon 0.8" (probe [11]).
- Other projection options (`SIDBIT_ECL_T0`, `SIDBIT_SSY_PLANE`): research modes, not used in Indian ephemerides.

**Recommendation.** Keep geocentric apparent, as now. Bodies: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn.

**Owner question SCI-01d.** Do you approve geocentric, apparent, ecliptic-of-date sidereal longitudes (Swiss default flags) for all grahas?

### SCI-01e Sidereal ascendant and the Placidus call

**What the code does.** `swe.houses_ex(jd_ut, lat, lon, b"P", FLG_SIDEREAL)` and reads only `ascmc[0]`. The ascendant does not depend on the house system: it is the ecliptic point rising in the east, from local apparent sidereal time, true obliquity and geographic latitude. Placidus is used only as the vehicle, and Placidus cusps cannot be computed beyond the polar circles, so the whole call raises `swisseph.Error` there (handled since CLAUDE-002b as `ASCENDANT_UNCOMPUTABLE`). Upstream §6.4 confirms Placidus and Koch fail beyond the polar circles while the ascendant itself is chosen as "the eastern rising point of the ecliptic".

**Evidence (probes [4]–[6]).**
- `ascmc[0]` from `W`, `E` and `O` equals `P` to 0.000000000" on 21,168 time/place samples with \|lat\| ≤ 66°.
- At latitudes 67°–88.9° north and −70° to −88.9° south, `P` raises and `W`/`E`/`O` return an ascendant.
- Sidereal ascendant equals tropical ascendant minus the true ayanamsha to 0.000000".

**Recommendation.** Keep the definition "tropical ascendant from UT, minus true Lahiri ayanamsha". Change only the vehicle from `b"P"` to `b"W"` (whole sign, matching the house model) in a later, separately authorized code package. Where Placidus works today the numbers are bit-identical, so this is a reliability change, not a method change. It still needs your approval because it changes which inputs are refused.

**Owner question SCI-01e.** Do you approve computing the ascendant through `houses_ex(..., b"W", FLG_SIDEREAL)` in place of `b"P"`, with no other change to the ascendant definition?

### SCI-01f Whole-sign houses

**Options.** Whole sign (house 1 = Lagna's Rashi), equal houses from the Lagna degree, Sripati/Bhava Chalit (quadrant-based), sidereal Placidus.

**Recommendation.** Whole sign for D1 placement, as proposed. It is the standard Rashi-chart convention for North Indian D1 rendering, it is a pure function of two Rashis (exactly testable), and it has no high-latitude singularity. Bhava Chalit is deferred to P1 as a separately labelled chart.

**Owner question SCI-01f.** Do you approve whole-sign houses for D1 (and, under SCI-02, for D9 from the D9 Lagna)?

### SCI-01g Validated latitude band

**Problem.** Today inputs are accepted for −89 < lat < 89, and then refused or not depending on date and time (wherever Placidus fails, roughly \|lat\| > 66.5°). That makes the supported area unpredictable. Above the polar circles the ascendant is also extremely time-sensitive: probe [7] shows up to 16"/s of birth time at the equator, 65"/s at 60° and 220"/s at 66°, so a one-minute birth-time uncertainty is 16' to several degrees of Lagna.

**Recommendation.** Validate and accept \|lat\| ≤ 66.0°, refuse outside with a fixed, documented `LATITUDE_OUTSIDE_VALIDATED_BAND` error, regardless of date. This covers all of India and almost all populated places, and keeps the date-dependent refusal out of the product. A wider band can be added later with its own fixtures.

**Alternatives.** (1) Keep today's behaviour. (2) After SCI-01e, accept up to ±89° and validate high-latitude fixtures too, accepting extreme time sensitivity. (3) A narrower band such as ±60°.

**Owner question SCI-01g.** Do you approve a validated latitude band of \|lat\| ≤ 66.0°, refused outside by a fixed rule?

### SCI-01h Time scale (UTC versus UT1)

**Current behaviour.** The engine converts civil time to UTC and passes it to `swe.julday`/`calc_ut`, which treat it as UT1. UT1 − UTC is kept within ±0.9 s since 1972 (probe [9] shows Swiss's own model puts it at +0.41 s on 2016-12-31). Before 1972, broadcast time and civil records are themselves only good to about a second or worse.

**Size.** Moon 0.565"/s, so ≤0.5". Ascendant up to about 15" at the equator and 1' at 60° (probe [7]). Both are tiny next to a birth time recorded to the minute.

**Recommendation.** Keep for MVP, and record "civil UTC used as UT1" in method metadata. Reference fixtures make the same assumption so this does not show up as a false failure (see T-ASC). Switching to `swe.utc_to_jd` is a possible later refinement and would need its own approval.

**Owner question SCI-01h.** Do you accept "civil UTC treated as UT1" as a documented MVP limitation?

---

## SCI-02 MVP calculation scope

**Recommendation for MVP (P0):**

| Output | Definition | In foundation code today |
|---|---|---|
| D1 longitudes | Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, mean Rahu, Ketu; sidereal degrees per SCI-01d | Yes |
| D1 Rashi and house | Rashi of each body and of Lagna; whole-sign house from Lagna | Yes |
| Lagna | Sidereal ascendant longitude, Rashi | Yes |
| Moon Rashi | Rashi of the Moon | Yes (as `planets.moon.rashi`) |
| Moon Nakshatra, Pada | 27 equal Nakshatras of 13°20', 4 Padas of 3°20', half-open segments, Ashwini starting at sidereal 0° | Yes |
| D9 sign of each body and of Lagna | 108 Navamsa segments of 3°20' mapped cyclically from Mesha; equivalent to the classical rule (fire signs start at Mesha, earth at Makara, air at Tula, water at Karka) | Yes |
| D9 Lagna and D9 houses | D9 Lagna = Navamsa sign of Lagna; D9 house of each body = whole-sign house from D9 Lagna | Lagna sign yes; **D9 houses not output** |
| Method metadata | Ayanamsa variant, node, house model, ascendant vehicle, time-scale note, Swiss and data versions | Partly |

**Owner options inside MVP.**
- Nakshatra and Pada for **every** body and for Lagna (cheap, same rule; many Kundali reports show it). Recommended: include, because it adds no new astronomy.
- Retrograde marker (from body speed). Recommended: defer to P1; needs speed sign rules near stations and its own fixtures.

**Explicitly deferred (P1 or later, each needing its own spec and fixtures):** Vimshottari Dasha and sub-periods; other divisional charts (D2, D3, D7, D10, D12, D60 and others); Bhava Chalit; Yogas, Doshas and Gun Milan; Panchang elements (Tithi, Yoga, Karana, Vara); Uranus, Neptune, Pluto; upagrahas (e.g. Gulika); retrograde, combustion and planetary-war status; Ashtakavarga, Shadbala; true node; topocentric options; South Indian layout (presentation, UX-02).

**Owner question SCI-02.** Do you approve the MVP table above (adding D9 whole-sign houses), and should Nakshatra/Pada be shown for all bodies and Lagna or for the Moon only?

---

## SCI-03 Supported birth-date range

**Facts.**
- Pinned data `sepl_18.se1`/`semo_18.se1` cover 1800–2399 CE (upstream table; manifest notes `FLG_SWIEPH` returned for 1800 and 2399, Moshier for 1799 and 2400). Any 1900–2100 window has a full century of margin.
- The engine currently checks the **UTC** year (`engine.py`, `_parse_birth`). So `1900-01-01T03:00+05:21:10` local (UTC 1899-12-31) is refused, while `2101-01-01T03:00+05:30` local (UTC 2100-12-31) is accepted. Users think in local dates, so the edge is surprising.
- Calendar: 1900–2100 is Gregorian everywhere relevant; Python and `swe.julday` both use the Gregorian calendar. 1900 and 2100 are not leap years; 2000 is.
- Delta T (TT − UT): Swiss uses Stephenson, Morrison & Hohenkerk (2016) before 1955, Astronomical Almanac values from 1955, IERS data from 1974, and an extrapolation formula after the last tabulated value. Its values (probe [8]) are −1.95 s (1900), 63.83 s (2000), 93.18 s (2100). Upstream states future Delta T "cannot be calculated with accuracy". The Moon moves 0.565"/s, so a Delta T error of tens of seconds near 2100 shifts the Moon by tens of arcseconds. The Lagna depends on UT, not Delta T.
- Time zones: the engine relies on IANA tzdata through Python `zoneinfo` (container system tzdata 2026e; PyPI `tzdata` is at 2026.5). For India, IANA `Asia/Kolkata` uses LMT before 1854, `+05:53:20` until 1870, Madras railway time `+05:21:10` until 1906-01-01, then `+05:30`, with war time `+06:30` from 1941 Oct to 1942 May 15 and 1942 Sep to 1945 Oct 15. The IANA source itself says Bombay and Calcutta kept their own civil times for decades after 1906 ("Battle of the Clocks"), that Calcutta government time was `+05:53:20` or `+05:54`, and that the 1941–1945 data rests on Shanks, "our only (and dubious) source". IANA does not model Bombay Time (about `+04:51`) or Calcutta Time in `Asia/Kolkata`.
- Consequence today: a correctly recorded 1930 Mumbai birth in Bombay Time is **refused** as an offset mismatch, and the same birth entered as `+05:30` is **accepted with about 39 minutes of error**, roughly 10° of Lagna. The engine cannot tell the difference.

**Recommendation.**
1. Supported and validated window: local civil birth date from **1900-01-01 through 2100-12-31 inclusive**, checked on the local date, with the UTC instant then necessarily inside the ephemeris range.
2. Astronomy is validated across the whole window (fixtures at both ends, see golden spec).
3. For India births before 1956-01-01 the product discloses that local time keeping varied by city and that the time zone rules used may not match the recorded clock. How the place/time UI handles this belongs to DATA-01 and KUN-02, not this package; this package only requires that the limitation be stated and tested.
4. Near 2100, Moon positions carry the Delta T extrapolation uncertainty; disclose in method notes rather than narrowing the window.

**Alternatives.** Keep the UTC-year rule; narrow to 1947 or 1956 onwards; widen to 1800–2399 (needs pre-1900 time-zone work).

**Required boundary tests** (detailed in [golden-chart-spec.md](golden-chart-spec.md)): first and last accepted local instants; the instants just outside; UTC-date crossover at both edges in east and west zones; 29 Feb in 1900 (reject), 2000 (accept), 2024 (accept), 2100 (reject); Asia/Kolkata 1905 (`+05:21:10`), 1943 (`+06:30`) and 1946 (`+05:30`); a DST gap (reject) and fold (both offsets accepted) in the northern and southern hemispheres; 30- and 45-minute zones; the date line.

**Owner question SCI-03.** Do you approve 1900-01-01 to 2100-12-31 by **local** birth date as the validated window, with a stated limitation for pre-1956 India local time?

---

## What approval unlocks

| Approved | Unlocks |
|---|---|
| SCI-01a, b, c, d, h | Generation of planet, node and ayanamsa reference fixtures |
| SCI-01e, f, g | Lagna and house fixtures; separate small code package for `b"W"` and the latitude band |
| SCI-02 | D9 house and optional all-body Nakshatra fixtures; output schema work package |
| SCI-03 | Date-edge fixtures; small code package for the local-date rule |

No calculation code changes until the matching item is APPROVED in `docs/DECISIONS.md`.
