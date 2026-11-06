# KUN-PAN-M2-SUN-001: sunrise, sunset and Vara, IMD 47′ versus USNO 50′

**Status: validation evidence and a recommendation for the owner and independent QA. Nothing here is adopted.**
PAN-D03 (sunrise convention), D04 (Swiss realisation), D05 (Vara), D11 (undefined sunrise) and D17 (sunset) stay
**PENDING**. The new module `src/sabpuja_kundali/panchanga/sun.py` is not wired into `sabpuja-panchanga/1`, the
chart, the 10-page or the 13-page report. Every call must name its convention; there is no default.

Stacked on draft PR #81 (`kun-pan-m2-names-001` at `a8c31081dfc631f5a0a960c699aaabc24b05d7fe`), which is stacked
on draft PR #79. Neither is merged.

## 1. The two conventions

| Code | Publisher | Definition | Sun's centre at the event |
|---|---|---|---|
| `SUN-D-IMD-47` | IMD Positional Astronomy Centre, Rashtriya Panchang | Upper limb on the horizon, 31′ horizontal refraction, 16′ semidiameter | 47′ below the geometric horizon |
| `SUN-A-USNO-50` | US Naval Observatory | Upper limb on the horizon, 34′ refraction, 16′ semidiameter | 50′ below the geometric horizon |

**Primary source for 47′, now read by Claude** (IMD explanation page, https://packolkata.imd.gov.in/panchang/en/explanation,
accessed 2026-11-06, quoted in `research/panchanga/reference-fixtures/imd-sunrise-sunset-2026.json`):

> "The amount of horizontal refraction taken for the purpose is 31’ and that of the sun’s semi-diameter is 16’ so that
> at the moment when the upper limb of the sun is visible on the horizon, the centre of the sun is actually 47’ below
> the horizon"

The same page says IMD's sunrise and sunset are for "an adopted Central Station of India situated at 82° 30'
Longitude East and 23°11' Latitude North", that times are IST, and that the Panchang day runs from Central Station
sunrise to the next sunrise. It gives no rounding rule, no elevation, pressure or temperature, and does not say
whether solar positions are geocentric or topocentric. Earlier SCI-PAN-01 revisions held 47′ as "reported by QA";
it is now confirmed from IMD's own text.

Both conventions are fixed-depression rules (no weather model), so one code path realises both with a different
constant. They are never combined: the module refuses a missing, unknown or misspelled convention
(`SUNRISE_CONVENTION_REQUIRED`), and the tests check that the parameter has no default.

## 2. How the engine computes it (the proposed D04 realisation)

- Event condition: geometric altitude of the Sun's centre equals −47′ or −50′.
- Sun: Swiss `calc_ut(SUN, FLG_SWIEPH | FLG_EQUATORIAL)`, geocentric apparent RA/Dec of date; Swiss apparent sidereal
  time; UTC as UT1 (SCI-01h); automatic Delta T. `FLG_SWIEPH` is checked on every call.
- Observer: sea level, level horizon, no dip, no terrain. Geocentric: the Sun's 8.8″ parallax moves events by
  under 1 s (measured below: 0.4 to 0.8 s in India).
- Search: 5-minute samples over the local civil day plus the refined daily altitude maximum and minimum, then
  bisection on integer microseconds; the residual altitude must be ≤ 1″ (observed ≤ 0.001″).
- Swiss `rise_trans` / `rise_trans_true_hor` are **not** used for the result (they do not report the ephemeris used,
  and the fast path has no convergence test); they are a cross-check only.
- Day: the sunrise of local date D is the rising in [00:00 D, 00:00 D+1) of the IANA zone (23 or 25 h on DST days);
  the sunset is the first setting within 24 h after it.
- Vara: weekday of the local civil date of the latest sunrise at or before the birth instant, half-open
  [sunrise_D, sunrise_D+1). The civil weekday is always reported beside it, and Vara is never filled from it.
- Undefined events: typed `unavailable`, reason `PANCHANGA_SUNRISE_UNDEFINED` (D11-B as proposed). Latitude beyond
  ±66.0° is the chart's `LATITUDE_OUTSIDE_SUPPORTED_BAND`; dates outside 1970-01-01 to 2100-12-31 (D13-A) are refused,
  and a Vara whose governing sunrise would be 1969-12-31 is `unavailable` (`PANCHANGA_SUNRISE_OUTSIDE_ENVELOPE`).

## 3. Independent references and results

Run: `python -m tests.panchanga.sun_compare --report-dir DIR` (pinned ephemeris; swetest optional). Raw outputs are
in the PR evidence. Tolerances are in `tests/panchanga/sun-tolerances.json` (status: proposed, see §6).

| Layer | Independent of Swiss? | Cases | Result |
|---|---|---|---|
| USNO published minutes, `SUN-A-USNO-50` | Yes (US publisher, own algorithm) | 12 located cases, 24 times, India + Sydney | all within the **pre-declared 120 s**; max 31.8 s; 22/24 consistent with round-to-nearest minute |
| USNO polar cases | Yes | N01 65.9° N 21 June; N02 Tromsø | N01: USNO "continuously above the horizon", engine `SUN_ABOVE_DEPRESSION_ALL_DAY` for both conventions; N02: latitude refusal |
| IMD published minutes, `SUN-D-IMD-47` | Yes (IMD) | 448 times: Central Station 60 days (Chaitra, Kartika 2026), Chennai, Delhi, Kolkata, Mumbai 41 days each (Chaitra, Ashadha) | all within 120 s; max 63.1 s (cities), 40.5 s (Central Station) |
| Pure-Python oracle (Meeus ch. 25 Sun, IAU GMST, own hour-angle iteration) | Yes (no Swiss code or data) | 992 Indian events (16 places × 31 dates, 1970 to 2100) + 84 high-latitude events, both conventions | max 2.43 s in India, 3.14 s up to 65.5° |
| Swiss `rise_trans_true_hor`, `DISC_CENTER | NO_REFRACTION | GEOCTR_NO_ECL_LAT`, horizon −47′/−50′ | No (Swiss-on-Swiss, different algorithm) | same grid | max 0.048 s in India; up to 0.97 s at 65.5° S (Swiss fast path, no convergence test) |
| Same, topocentric (flag 128 off) | No | same grid | 0.4 to 0.8 s in India: the Sun's parallax, as predicted |
| Official `swetest` (separate C build), altitude at the engine instant | No (same C library) | same grid | condition met to ≤ 0.027″ after the 8.79″/R parallax correction |

The 128 flag result also settles SCI-PAN-01 §5.6.3's documentation conflict: in 2.10.03, `GEOCTR_NO_ECL_LAT` makes the
rise routine **geocentric** (it matches the engine to 0.015 s), as the header says and the manual's flag list does not.

### 3.1 Size of the difference

Across the 16 Indian reference points and 31 dates, IMD 47′ sunrise is **12.1 to 16.6 s later**, and sunset 12.1 to
16.6 s earlier, than USNO 50′. Close to the polar limit the gap grows to minutes (8 min at 65.70° N on 21 June), and
between about 65.73° and 65.78° N near the June solstice only the 47′ rule has a sunrise at all, so the convention
decides whether a Vara exists.

### 3.2 Can the published minutes tell 47′ from 50′?

Only weakly. A 13 s shift is a quarter of the printed minute. Each publisher's own times fit its own convention
better, which is a useful consistency check, not a proof:

| Published set | consistent with round-to-nearest under 47′ | under 50′ | day-length fit of the depression |
|---|---|---|---|
| USNO, 24 times | 18 | **22** | (too few) |
| IMD Central Station, 120 times | **104** | 93 | **47.1′ ± 0.5′** (Chaitra 48.9′, Kartika 45.2′) |
| IMD four-city table, 328 times | 256 | 261 | 49.4′ ± 0.3′ (Kolkata 47.1 to 48.4′, Chennai 47.8 to 48.5′, Delhi 50.0′, Mumbai 51.4 to 52.3′) |

The day-length fit uses sunset minus sunrise, which cancels longitude and clock errors and is linear in the depression.
The Central Station, IMD's own reference point, fits 47′ and not 50′. The city table does not fit any single value.
The likely reasons are coordinates or rounding that IMD does not print (the city coordinates were taken from IMD's
Lagna correction page), but that is not verified, and the month-to-month spread at the Central Station is larger than
its standard error suggests. **The 47′ value therefore rests on IMD's text, not on its numbers.** The city-table
spread is recorded as an open item (§7).

### 3.3 Other conventions, for context only

Swiss `SE_BIT_HINDU_RISING` (disc centre, no refraction; much Jyotish software) is 3.2 to 4.3 minutes after the IMD
time in India (SCI-PAN-01 §5.6.4). A scratch check with the Sun's centre on the geometric horizon matched 0 of the 448 IMD values
under round-to-nearest (its times are 3 to 5 minutes off). It is not implemented and not recommended unless the owner wants that practice.

## 4. Coverage

- **Indian places**: Delhi, Mumbai, Kolkata, Chennai, Bengaluru, Hyderabad, Ahmedabad, Jaipur, Guwahati, Srinagar,
  Leh, Kanyakumari, Port Blair, Dwarka (west), Kibithu (east), and the IMD Central Station. Synthetic reference
  points, not a gazetteer.
- **Dates**: the 1st and 15th of every month of 2026, the equinoxes and solstices, 1970-01-01, 2000-02-29 and
  2100-12-31. Refused: 1969-12-31 and 2101-01-01.
- **Time zones**: IST; America/New_York on both 2026 DST days; Europe/London DST start; Pacific/Kiritimati (UTC+14,
  local date ahead of UTC) and Pacific/Pago_Pago (UTC−11); Europe/Helsinki and Europe/Oslo; Australia/Sydney.
- **Vara**: birth exactly at sunrise (new day) and 1 µs before (previous day); midnight to sunrise gives the previous
  Vara with `vara_differs_from_civil_weekday: true`; a birth inside the 47′/50′ gap gets a different Vara under each
  convention; a DST-zone birth; polar day (Vara `unavailable`, civil weekday kept); governing sunrise before 1970.
- **Polar**: 65.9° N and 66.0° S at their solstices (`SUN_ABOVE_DEPRESSION_ALL_DAY`); the 65.73° to 65.78° split;
  64.9°, 65.1° and 65.5° on both sides of Swiss's 65° algorithm switch; beyond ±66.0° refused. A polar night cannot
  occur inside the band under either convention (the Sun's centre reaches at least +39′ at 66° on the December
  solstice).
- **Fail-closed**: missing or wrong ephemeris path, `SE_EPHE_PATH` set, a Moshier flag from Swiss, invalid date, zone
  or coordinates, non-location zones. Mutation runs (convention constant changed, a 9″ altitude bias, `>` for `>=`
  in the Vara rule, no extremum refinement, longitude sign flipped, a default convention added) each fail the suite.

## 5. Recommendation (for the owner; not adopted)

1. **PAN-D03: adopt `SUN-D-IMD-47`** for Sabpuja's Panchanga sunrise, sunset and Vara. It is the documented
   convention of India's national Panchang, now read from IMD's own page; IMD's Central Station times fit it; and its
   difference from the astronomical USNO rule (12 to 17 s in India) is smaller than any published minute, so the
   choice does not put Sabpuja at odds with standard almanacs.
2. **Keep `SUN-A-USNO-50` as a test-only reference**, because USNO is the only independent source that publishes
   city-specific times on demand. Do not offer it to customers and never mix the two in one report.
3. **Compute at the birthplace, not at the Central Station.** IMD prints sunrise for its Central Station only; using
   its definition at the birthplace is Sabpuja's extension of the convention, and the report should say so in
   plain words ("sunrise at the birthplace, IMD Rashtriya Panchang definition: upper limb, 31′ refraction").
4. **D04**: the realisation in §2 (own bracketing on Swiss positions, geocentric, sea level), with Swiss
   `rise_trans_true_hor` kept as a conformance test only.
5. **D05**: Vara as in §2, half-open from sunrise to sunrise, with the civil weekday always printed beside it.
6. **D11-B**: in the rare polar case, mark Vara and sunrise `unavailable` and keep the birth-instant Panchanga.
7. **D17**: sunset uses the same rule and code path.
8. **Display**: sunrise and sunset to the minute, labelled "about", as for the M1 transition times (D09 remainder).

Integration into the Janam Kundali report (KUN-PAN-RPT-002) should wait for these owner decisions and for QA of
this evidence.

## 6. Tolerances and their status

The 120 s USNO tolerance was declared on 2026-10-28 in the USNO fixture, before any sunrise computation. The IMD
layer reuses the same rule unchanged, but it was written down after a scoping comparison, and the oracle, Swiss and
swetest bounds are engineering bounds from the oracle's stated accuracy and the measured parallax. QA and the owner
should confirm or replace them before they are treated as acceptance thresholds (as PAN-D15 did for M1).

## 7. What is not verified or remains open

- IMD pages were read through an automated page reader, not downloaded (the container's network policy refuses the
  domain), so there is no archived page or SHA-256. QA should re-read them, as for the names work.
- The four-city table's column mapping is Claude's inference from the values (documented in the fixture). The
  city coordinates IMD used for it are not printed.
- The city table's spread (47′ to 52′ by place) is unexplained.
- Only 2026 IMD values were captured; IMD's December (Pausha) table was not reachable.
- No elevation, terrain or weather model; no historical refraction study.
- The swetest layer used a locally built `swetest` from the pinned source commit (SHA-256 in the evidence), not the
  QA-accepted `9ed78fdc…` binary; QA can re-run that layer with its binary through `SABPUJA_TEST_SWETEST`.
- Hindi labels for Vara are not part of this task (machine ids only: `ravivara` … `shanivara`).
