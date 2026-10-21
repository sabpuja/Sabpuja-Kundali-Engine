# Golden-chart validation specification, fixture inventory and tolerances

**Document ID:** SP-KUN-ACC-GOLD | **Work package:** CLAUDE-003 / KUN-01 Phase C | **Status:** PROPOSED test design. **No expected values exist yet.**

Method-dependent fixtures (anything with a sidereal value, a node, a Lagna or a category) must not be generated until the matching SCI decision is APPROVED in `docs/DECISIONS.md` on `main` and ChatGPT QA has passed this specification. Tolerances below are declared **before** any reference comparison has been run and must not be widened to make a failing case pass. A tolerance can change only through a documented decision that cites a reason other than "the test failed".

Acceptance IDs served: QA-005, QA-006, QA-007, QA-008, QA-009, QA-010, QA-012, QA-013 (`docs/ACCEPTANCE-MATRIX.md` on `main`).

## 1. Principles

1. **Independent truth.** Expected values come only from sources in [reference-sources.md](reference-sources.md) classes I-data, I-code or I-pub. The reference generator must not import `sabpuja_kundali` or `swisseph`; the QA harness enforces this (see [qa-architecture.md](qa-architecture.md)).
2. **Synthetic inputs only.** Every input is an invented date and time at a public city-centre coordinate. No real person's birth data, ever.
3. **Same question to both sides.** Each fixture records the method signature (ayanamsa variant, node, house model, ascendant vehicle, frame, apparent/geometric, geocentric, time-scale assumption). The engine's side is **not** taken from its emitted `method` block, which today carries only `ayanamsa: Lahiri`, `nodes: mean`, `houses: whole_sign`, a source label and the binding version. It comes from an independently inspected, commit-pinned **method manifest** ([qa-architecture.md](qa-architecture.md) section 3a). A signature that differs from the manifest is METHOD-MISMATCH; a manifest that is missing, stale or cannot be verified makes the fixture BLOCKED, never a match.
4. **Categories are not compared near their edges by accident.** Ordinary golden charts are selected (using the reference only) so that every category is at least 10× its tolerance away from a segment boundary. Boundaries are tested on purpose by transition fixtures (section 5.3).
5. **Self-consistency is labelled.** Checks such as "Ketu is Rahu + 180°" or the exact-arithmetic boundary oracle prove internal consistency only, and are reported in a separate section titled as such.

## 2. Fixture record (one JSON file per fixture)

```json
{
  "fixture_id": "GC-01",
  "fixture_revision": 1,
  "purpose": "Baseline New Delhi chart, existing synthetic example",
  "synthetic": true,
  "input": {
    "birth_datetime": "2000-01-01T17:30:00+05:30",
    "timezone": "Asia/Kolkata",
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "derived_time": {
    "utc": "2000-01-01T12:00:00Z",
    "ut1_assumption": "civil UTC used as UT1 (SCI-01h)",
    "jd_ut": null,
    "delta_t_s_used_for_tt": null,
    "jd_tt": null,
    "tzdata_version": "2026e"
  },
  "method_signature": {
    "ayanamsa": "SE_SIDM_LAHIRI true, Swiss default precession (pending SCI-01a)",
    "node": "mean (pending SCI-01b)",
    "ketu": "node + 180 exact (pending SCI-01c)",
    "positions": "geocentric apparent, ecliptic of date (pending SCI-01d)",
    "ascendant": "tropical ascendant at UT minus true ayanamsha (pending SCI-01e)",
    "houses": "whole sign from Lagna; D9 whole sign from D9 Lagna (pending SCI-01f, SCI-02)"
  },
  "references": [
    {
      "source_id": "R-02",
      "software": "skyfield 1.55",
      "data": "de421.bsp sha256 a20a7139...",
      "command_or_query": "exact script path + git SHA, or Horizons query text",
      "retrieved_utc": "YYYY-MM-DDThh:mm:ssZ",
      "raw_output_sha256": "..."
    }
  ],
  "expected": {
    "tropical_longitude_deg": {"sun": null},
    "ayanamsa_deg": null,
    "sidereal_longitude_deg": {"sun": null, "rahu_mean": null, "ketu_mean": null, "lagna": null},
    "categories": {"sun": {"rashi": null, "house": null, "navamsa_rashi": null, "d9_house": null, "nakshatra": null, "pada": null}},
    "time_conversion": {"utc": "2000-01-01T12:00:00Z", "error_code": null}
  },
  "tolerances_ref": "golden-chart-spec.md section 4, revision 1",
  "limitations": ["..."],
  "approved_decisions_required": ["SCI-01a", "SCI-01b", "SCI-01c", "SCI-01d", "SCI-01e", "SCI-01f", "SCI-02"]
}
```

Every `null` above is filled by the reference generator only after approval. `fixture_revision` increases on any change; the QA report quotes the revision and the file's SHA-256.

## 3. Comparison rules

- **Angular difference** is always circular: `d = ((engine − reference + 180) mod 360) − 180`, reported in arcseconds with sign. Plain subtraction is a defect (359.9999° vs 0.0001° is 0.72", not 359.9998°).
- **Engine values** are the emitted 8-decimal `longitude_deg` (display rounding ≤ 5e-9° = 0.000018", negligible against every tolerance). Categories are read from the engine's category fields, never re-derived from the rounded number (see `docs/api-contract.md`).
- **Reference categories** are computed by the QA harness's own oracle from the reference longitude, written from the rule definitions (R-11), not by calling `sabpuja_kundali.rules`.
- **Category outcome:** exact equality required. If the reference longitude lies within the relevant tolerance of a segment boundary, the outcome is BOUNDARY-INDETERMINATE (neither pass nor fail) and the fixture must be redesigned or resolved with a tighter reference.
- **Time conversion:** the engine's `birth.utc` must equal the expected UTC string exactly; rejected inputs must produce the expected error class with no partial chart.
- **Planets and nodes** are compared at the engine's TT and the **ascendant** at the same UT1, which isolates the kernel and coordinate transforms. Time handling (UTC → UT1, Delta T) is verified on its own track (section 4.4); a kernel PASS alone is not an end-to-end PASS.

## 4. Tolerance proposal (declared before any comparison)

**Status of every numeric tolerance: PROPOSED BUDGETING HYPOTHESIS, BLOCKED FOR FREEZE.** None is yet backed by independent evidence for every body and epoch. A row may be frozen only after its pre-gate (section 4.2) has produced evidence that ChatGPT QA has reviewed. Pre-gate evidence must not include any comparison against the engine or Swiss Ephemeris output, so tolerances are still fixed before engine results are seen. If a pre-gate shows a budget is too small, the row is re-derived from that pre-gate evidence and re-reviewed; it is never widened because an engine comparison failed.

"S" is the ascendant's sensitivity to local sidereal time, `|∂λ_asc/∂θ|`, computed analytically by the reference for each fixture (≈1 near the equator, about 4 at 60°, much larger near the polar circle; probe [7]).

### 4.1 Rows

| ID | Quantity | Reference | Proposed budget | Basis and what is unverified | Freeze status |
|---|---|---|---|---|---|
| T-ICRF | Geocentric astrometric RA/Dec, ICRF (angular separation), Sun–Saturn and Moon | R-02 / R-02b / R-01 quantity 1 | 0.10" | Documented: Swiss compression vs JPL ≤ 0.001", Swiss reproduction of Horizons ≈ 0.001" (R-10). **Unverified:** the size of DE431 vs DE421/DE440 differences per body and epoch, assumed < 0.05" for 1900–2100 including the Moon | **BLOCKED** until PG-1 |
| T-TROP-S | Tropical apparent ecliptic longitude of date | R-02 / R-02b (IAU 2006/2000A) | 0.10" | T-ICRF budget plus model differences (Vondrák 2011 vs IAU 2006 precession, IAU 2000B vs 2000A nutation) **assumed** at milliarcsecond level | **BLOCKED** until PG-1, PG-4 |
| T-TROP-H | Same, against Horizons quantity 31 | R-01 | 0.50" | Documented constant 53 mas reference-ecliptic offset (R-10); IAU 1976 precession-rate error ≈ 3 mas/yr quoted from IAE 2019 via R-10, giving ≈ 0.3" at 1900 and 2100 | **BLOCKED** until PG-1, PG-4 |
| T-AYA | True Lahiri ayanamsha | Reimplementation of the approved definition with ERFA (R-04), and IAE printed tables (R-05) | 0.40" | **Hypothesis only.** Derived from Swiss-vs-Swiss variant sensitivity (probe [1]: mode 1 vs the IAU 1976 variant, −0.30" to +0.31") plus 0.05" IAE print rounding. Neither the IAE editions/epochs nor the ERFA derivation has been reviewed | **BLOCKED** until PG-3 |
| T-SID | Sidereal longitude, Sun–Saturn and Moon | T-TROP-S path − T-AYA path | 0.50" | Sum of two blocked rows | **BLOCKED** |
| T-SID-H | Same via Horizons | T-TROP-H − T-AYA | 0.90" | Sum of two blocked rows | **BLOCKED** |
| T-NODE | Mean Rahu | none yet | **no budget proposed** | See section 4.3. Swiss's mean node (Moshier's adjustment of ELP2000-85, corrected towards DE431-derived values) and a textbook ELP polynomial are **different conventions**: upstream says they differ by up to 20" over 3000 BCE–3000 CE, and its "1" relative to DE431" estimate is a precision claim against a different reference. A 1" or 20" pass band would both be unjustified | **BLOCKED** pending convention comparability (PG-2) |
| T-NODE-SID | Sidereal mean Rahu and Ketu | T-NODE − mean ayanamsha | none | Follows T-NODE | **BLOCKED** |
| T-KETU | Ketu − Rahu − 180° (self-consistency, labelled) | none | ≤ 1e-8° | Exact construction; only display rounding of two values remains. Not independent validation | Can freeze (arithmetic) |
| T-ASC | Tropical ascendant | ERFA sidereal time + true obliquity + spherical formula (R-04) at the same UT1 | 0.10" × max(1, S) | **Assumed** milliarcsecond-level sidereal-time and obliquity model differences; the formula amplifies sidereal-time error by S | **BLOCKED** until PG-4 |
| T-ASC-SID | Sidereal ascendant | T-ASC − T-AYA | 0.10" × max(1, S) + 0.40" | Sum of blocked rows | **BLOCKED** |
| T-UTC | UTC instant from civil input | IANA rule (R-08) | exact | Discrete. Tests IANA rule **application** only, not historical clock truth (section 5.2) | Can freeze per tzdata version |
| T-CAT | Rashi, house, Nakshatra, Pada, D9 sign, D9 house | Harness oracle on reference longitude | exact, with BOUNDARY-INDETERMINATE band equal to the longitude tolerance used | Discrete; band inherits the status of the longitude row | Follows its longitude row |
| T-TIME-* | Time-scale track | Section 4.4 | see 4.4 | | **BLOCKED** until PG-5 |

### 4.2 Evidence pre-gates (before any tolerance freezes)

| Pre-gate | Evidence required | Independent of the engine? | Unblocks |
|---|---|---|---|
| PG-1 | Per-body, per-epoch differences between JPL ephemeris versions (DE421 vs DE440s vs DE441 at least; DE431 if obtainable) for Sun–Saturn and Moon across 1900–2100, computed with Skyfield/jplephem on a machine with NAIF access, plus INPOP vs DE440 for the same grid; together with any published inter-version comparison (for example the DE440/DE441 release paper) cited by page. Output: a per-body, per-epoch table | Yes: reference sources only | T-ICRF, T-TROP-* |
| PG-2 | Owner and QA choose the mean-node **definition** (see 4.3); then a written derivation of what the reference computes (theory, polynomial order, frame, equinox) | Yes | T-NODE, T-NODE-SID |
| PG-3 | IAE true-ayanamsha pages (at least two editions, edition and page recorded, reuse terms confirmed) and a reviewed ERFA derivation of the approved Lahiri definition, compared **with each other**, not with Swiss | Yes | T-AYA |
| PG-4 | ERFA vs Skyfield vs Horizons comparison of sidereal time, obliquity and of-date frame on a date grid, to bound model differences | Yes | T-TROP-*, T-ASC |
| PG-5 | Time-scale evidence: IERS EOP series, Delta T sources and the pre-1972 historical framing in section 4.4 | Yes | T-TIME-* |

### 4.3 Mean node: comparability before precision

The engine's mean node is whatever Swiss Ephemeris defines it to be. Upstream §2.2.1: Swiss computes it from Moshier's lunar routine, an adjustment of ELP2000-85 to the JPL ephemeris, with added corrections derived from the DE431 true node; its deviation from ELP2000-85's mean node is 0 at J2000 and below 20" over 3000 BCE–3000 CE; estimated precision 1" relative to DE431. A published polynomial (Chapront-Touzé & Chapront 1988 ELP2000-82B; Simon et al. 1994; Chapront et al. 2002) gives the mean longitude of the ascending node on the ecliptic of date, referred to the mean equinox of date, without light-time or aberration.

These are two definitions of "mean node", not one quantity measured twice. The owner must choose one of:
- **(a) Swiss's mean node is the definition.** Then no independent source computes it; node checks become **definition-conformance** checks, reported as such, and never as independent accuracy validation.
- **(b) A named published polynomial is the definition.** Then the engine is compared with that polynomial; a difference larger than the agreed numerical budget is **METHOD-MISMATCH** (the engine uses a different definition), not an implementation defect, until the engine is changed to compute the approved definition (a separate authorized code PR).

Until that choice and PG-2 are complete, node fixtures are BLOCKED. No pass band, neither 1" nor 20", is proposed.

### 4.4 Time-scale and Delta T verification track (separate from the planetary track)

Planet and node comparisons at the engine's own TT isolate the **ephemeris kernel and coordinate transforms**. They cannot validate the engine's time handling, so time is verified on its own track and the end-to-end claim depends on both.

| Check | What is compared | Independent source | Regime and caveats | Proposed budget |
|---|---|---|---|---|
| T-TIME-1 UTC → UT1 | Engine assumption "civil UTC = UT1" vs measured UT1 − UTC | IERS EOP C04 (1962 onward) and `finals2000A` (R-07) | **1972 onward:** leap-second UTC, \|UT1 − UTC\| kept below 0.9 s (IERS, NIST). **1961–1971:** UTC used frequency offsets and step adjustments; size to be sourced from IERS/BIH records. **Before 1961:** no UTC; civil time was a national realisation of mean solar time (GMT-based standard times), and recorded birth times are civil clock readings of uncertain accuracy. These eras are a **historical civil-time approximation**, not covered by the 0.9 s bound | Report-and-bound by era; no single number |
| T-TIME-2 Delta T, observed era | Engine TT − UT (Swiss `deltat`) vs Delta T derived from IERS: (TAI − UTC) + 32.184 s − (UT1 − UTC) | IERS EOP, IERS TAI − UTC | 1962 to the last published EOP date | Hypothesis 0.1 s, **BLOCKED** until PG-5 |
| T-TIME-3 Delta T, historical | Engine Delta T vs published tables for 1900–1961 | Stephenson, Morrison & Hohenkerk (2016) tables; Astronomical Almanac K-section values | Swiss uses these same publications, so this checks **implementation** of the tables, not their truth | Hypothesis 0.5 s, **BLOCKED** until PG-5 |
| T-TIME-4 Delta T, future | Engine Delta T after the last observed value vs a spread of published extrapolations | e.g. Stephenson et al. (2016) long-term parabola; Espenak & Meeus (2006) polynomials | No truth exists. Output is an **uncertainty band** per year, converted to Moon longitude (0.565"/s, probe [7]) and disclosed | Report only, with disclosed band |

**End-to-end gate.** A golden chart can be called end-to-end PASS only when (i) its kernel checks pass at the engine's TT, (ii) T-TIME-2 or T-TIME-3 passes for its epoch, and (iii) its civil-time input is inside a verified era (section 5.2 and the historical-clock release gate in [scientific-decisions.md](scientific-decisions.md), SCI-03). For future dates the result is QUALIFIED by the T-TIME-4 band, never an unqualified PASS.

**Not hidden in the tolerances.** Birth-time precision (one minute is about 16' of Lagna at the equator and more than 1° at 60°), UTC-vs-UT1 by era, and future Delta T are product limitations. Fixtures share the engine's assumptions so these do not appear as false kernel failures, and the time track reports them separately.

## 5. Fixture inventory

### 5.1 Golden charts (GC)

Coordinates are public city-centre values. All dates are **proleptic Gregorian** as a mathematical input convention (Python and `swe.julday` both use it); this says nothing about which calendar or clock was legally in use at that place and time. Every input below was checked against IANA tzdata 2026e with [`evidence/fixture_input_check.py`](evidence/fixture_input_check.py) ([output](evidence/fixture_input_check.out)).

| ID | Civil input | Zone | Lat, Lon | UTC | Covers | Reference path | Blocked on |
|---|---|---|---|---|---|---|---|
| GC-01 | 2000-01-01 17:30 +05:30 | Asia/Kolkata | 28.6139, 77.2090 | 2000-01-01 12:00 | Baseline; J2000 epoch | R-02, R-01 | SCI-01, SCI-02 |
| GC-02 | 1956-03-21 05:30 +05:30 | Asia/Kolkata | 19.0760, 72.8777 | 1956-03-21 00:00 | Lahiri epoch day (ayanamsa definition anchor) | R-02, R-05 | SCI-01a |
| GC-03 | 1975-08-15 06:10 +05:30 | Asia/Kolkata | 22.5726, 88.3639 | 1975-08-15 00:40 | Mid-century India, sunrise-hour Lagna | R-02 | SCI-01 |
| GC-04 | 2026-10-21 14:45 +05:30 | Asia/Kolkata | 13.0827, 80.2707 | 2026-10-21 09:15 | Current era, IERS UT1 known | R-02, R-01 | SCI-01 |
| GC-05 | 2050-06-15 23:55 +05:30 | Asia/Kolkata | 25.3176, 82.9739 | 2050-06-15 18:25 | Near local midnight; future Delta T | R-02, R-01 | SCI-01 |
| GC-06 | 2099-12-31 20:00 +05:30 | Asia/Kolkata | 12.9716, 77.5946 | 2099-12-31 14:30 | Window end; **beyond DE421** | R-02b, R-01 | SCI-01, SCI-03 |
| GC-07 | 2024-02-29 08:15 +11:00 | Australia/Sydney | −33.8688, 151.2093 | 2024-02-28 21:15 | Southern hemisphere, DST, leap day, UTC previous day | R-02 | SCI-01 |
| GC-08 | 1985-07-10 21:45 −03:00 | America/Argentina/Buenos_Aires | −34.6037, −58.3816 | 1985-07-11 00:45 | South and West; UTC next day | R-02 | SCI-01 |
| GC-09 | 1966-01-20 03:05 +00:00 | Europe/London | 51.5074, −0.1278 | 1966-01-20 03:05 | Small negative longitude, 51°N | R-02 | SCI-01 |
| GC-10 | 1919-11-11 11:00 −05:00 | America/New_York | 40.7128, −74.0060 | 1919-11-11 16:00 | Early century, pre-1955 Delta T model | R-02, R-01 | SCI-01 |
| GC-11 | 1937-04-01 12:00 +02:00 | Africa/Johannesburg | −33.9249, 18.4241 | 1937-04-01 10:00 | Southern hemisphere, pre-war | R-02 | SCI-01 |
| GC-12 | 2010-09-23 00:00 −05:00 | America/Guayaquil | −0.1807, −78.4678 | 2010-09-23 05:00 | Equator (S ≈ 1) | R-02 | SCI-01 |
| GC-13 | 2015-06-21 12:00 +00:00 | Atlantic/Reykjavik | 64.1466, −21.9426 | 2015-06-21 12:00 | Inside proposed 66.0° band, high S | R-02 | SCI-01e, g |
| GC-14 | 1990-05-05 06:00 +05:45 | Asia/Kathmandu | 27.7172, 85.3240 | 1990-05-05 00:15 | 45-minute offset | R-02 | SCI-01 |
| GC-15 | 1981-12-31 23:00 +07:30 | Asia/Singapore | 1.3521, 103.8198 | 1981-12-31 15:30 | Historical offset just before a zone change | R-02 | SCI-01 |
| GC-16 | 1905-06-01 09:00 +05:21:10 | Asia/Kolkata | 13.0827, 80.2707 | 1905-06-01 03:38:50 | **IANA-rule test input** (Madras railway time era); not a historically verified local clock for this place | R-02 | SCI-01, SCI-03 |
| GC-17 | 1943-06-15 10:00 +06:30 | Asia/Kolkata | 13.0827, 80.2707 | 1943-06-15 03:30 | **IANA-rule test input** (war time, single source IANA calls dubious); not historically verified | R-02 | SCI-01, SCI-03 |
| GC-18 | 1900-01-01 00:00 +05:21:10 | Asia/Kolkata | 22.5726, 88.3639 | 1899-12-31 18:38:50 | First local instant; **rejected by today's UTC-year rule, accepted by proposed local-date rule**. **IANA-rule test input**: IANA does not model Calcutta civil time in 1900 | R-02 | SCI-03 |
| GC-19 | 2100-12-31 23:59 +14:00 | Pacific/Kiritimati | 1.8721, −157.4278 | 2100-12-31 09:59 | Last local instant, far east; DE421 out of range | R-02b | SCI-03 |
| GC-20 | 2100-12-31 23:59 −08:00 | America/Los_Angeles | 34.0522, −118.2437 | 2101-01-01 07:59 | Last local instant, west; UTC year 2101: **accepted only by the proposed local-date rule** | R-02b | SCI-03 |
| GC-21 | (input chosen after SCI-01g) | Europe/Oslo | 69.6492, 18.9553 | — | **Optional, retained pending SCI-01g.** If the owner keeps a band, expect a fixed refusal; if not, it becomes an ordinary high-latitude chart with its own reference. Moving the ascendant to `b"W"` removes the Placidus failure; a band is a separate product-support restriction. Neither is required by the rule arithmetic | depends on SCI-01g | SCI-01e, SCI-01g |

At least four GC fixtures (proposed: GC-01, GC-04, GC-10, GC-06) are also generated through R-01 Horizons, and at least two through R-03 INPOP, so that every tropical path has a second, differently built reference.

### 5.2 Time-conversion fixtures (TZ)

These test civil-to-UTC conversion and refusal. They are **not independent of IANA** (the engine uses the same database); they verify correct application of a pinned tzdata version. **An IANA-matched UTC string is not independent historical time truth.** IANA's own theory notes that pre-1970 data need not represent every locality, so any pre-1970 TZ row is an IANA-rule test, not proof of what a clock in that city read. Expected UTC values are in the evidence output.

| ID | Input | Zone | Expected |
|---|---|---|---|
| TZ-01 | 2021-03-14 02:30 −05:00 | America/New_York | Reject (DST gap) |
| TZ-02a/b | 2021-11-07 01:30 −04:00 / −05:00 | America/New_York | Both accepted, UTC 05:30 and 06:30 (fold) |
| TZ-03a/b | 2023-04-02 02:30 +10:30 / +09:30 | Australia/Adelaide | Both accepted (southern fold, half-hour zone) |
| TZ-03c | 2023-10-01 02:30 +09:30 | Australia/Adelaide | Reject (southern gap) |
| TZ-04 | 2023-10-01 02:15 +10:30 | Australia/Lord_Howe | Reject (30-minute DST gap) |
| TZ-05 | 2024-01-10 12:00 +13:45 | Pacific/Chatham | Accept (45-minute zone with DST) |
| TZ-06 | 1995-07-01 12:00 −02:30 | America/St_Johns | Accept (negative half-hour DST) |
| TZ-07 | 2000-01-01 17:30 +05:00 | Asia/Kolkata | Reject (offset mismatch) |
| TZ-08a/b | 2000-02-29, 2024-02-29 12:00 +05:30 | Asia/Kolkata | Accept (leap days) |
| TZ-08c/d | 1900-02-29, 2100-02-29 | any | Reject (not calendar dates) |
| TZ-09a | 2000-03-01 02:00 +05:30 | Asia/Kolkata | Accept, UTC 2000-02-29 20:30 (east crossover onto leap day) |
| TZ-09b | 2000-02-28 20:00 −08:00 | America/Los_Angeles | Accept, UTC 2000-02-29 04:00 (west crossover) |
| TZ-10a | 1930-01-15 10:00 +04:51 | Asia/Kolkata | **Reject under IANA**, although Bombay civil time was about +04:51. Documents the pre-1956 India limitation (SCI-03) |
| TZ-10b | 1930-01-15 10:00 +05:30 | Asia/Kolkata | Accept under IANA; would be ~39 min wrong for a Bombay-time record. Limitation fixture |
| TZ-11a/b | 1945-10-14 23:30 +06:30 / +05:30 | Asia/Kolkata | Both accepted under IANA (end of war time, fold). IANA-rule test only; the 1941–1945 data rests on a source IANA calls dubious |
| TZ-12a | 2011-12-30 12:00 +14:00 | Pacific/Apia | Reject (date skipped at the date line) |
| TZ-12b | 2011-12-31 00:00 +14:00 | Pacific/Apia | Accept |
| TZ-13 | 1981-12-31 23:45 +07:30 | Asia/Singapore | Reject (gap at the 1982 zone change) |
| TZ-14 | 1899-12-31 23:59 local, 2101-01-01 00:00 local | Asia/Kolkata | Reject at the window edges (SCI-03) |

### 5.3 Transition fixtures (TR)

The crossing instant is found **from the reference** (root-finding on the reference longitude). The engine is evaluated at `t_cross − Δ` and `t_cross + Δ`, with `Δ = 5 × tolerance / |reference rate|` rounded up to a whole second, so both sides are unambiguous. Expected categories before and after come from the reference.

| ID | Event | Location | Expected change | Tolerance used for Δ |
|---|---|---|---|---|
| TR-01 | Sun reaches sidereal 0° (Mesha Sankranti), first in 2026 | New Delhi | Sun: Meena → Mesha, Revati 4 → Ashwini 1, D9 Meena → Mesha; whole-sign house changes by one | T-SID |
| TR-02 | Moon reaches sidereal 0°, first in 2026 | New Delhi | Moon: Meena → Mesha; Revati 4 → Ashwini 1; Moon Rashi changes | T-SID |
| TR-03 | Moon reaches 3°20' | New Delhi | Ashwini Pada 1 → 2; D9 Mesha → Vrishabha; Rashi unchanged | T-SID |
| TR-04 | Moon reaches 13°20' | Sydney | Ashwini 4 → Bharani 1; D9 Karka → Simha | T-SID |
| TR-05 | Lagna reaches sidereal 0° on 2026-01-15 | New Delhi | Lagna Meena → Mesha; every body's whole-sign house shifts by one; D9 Lagna Meena → Mesha | T-ASC-SID |
| TR-06 | Lagna crosses a Navamsa boundary inside a sign | Buenos Aires | D9 Lagna and all D9 houses change; D1 unchanged | T-ASC-SID |
| TR-07 | Mean Rahu crosses a Rashi boundary (next after 2026-01-01) | any | Rahu and Ketu Rashi change together | T-NODE-SID |
| TR-08 | Mars crosses a Rashi boundary (next after 2026-01-01) | any | Mars Rashi and house change | T-SID |
| TR-09 | Moon crossing a Nakshatra boundary in 1901 and 2099 | Kolkata | Same as TR-04 at both window ends | T-SID (T-SID-H for 2099 if R-02b missing) |

### 5.4 Rule fixtures (RULE, self-consistency, labelled)

Exact synthetic longitudes (e.g. `30 − 2^-40`, `40/3`, `10/3`, `359.999999996`) through the pure rules. These already exist in `tests/test_angular_boundaries.py` and `tests/boundary_oracle.py` from CLAUDE-002c. They stay as they are and are reported under "self-consistency", never as astronomical validation.

## 6. Limitations and unresolved ambiguities

1. **Lahiri start value.** IAE has printed both 23°15'00" and 23°15'00.658" for 21 Mar 1956, and its "mean" tables have an epoch ambiguity (R-10 notes). The reference implements the approved definition literally; IAE tables are an external check at 0.1" precision.
2. **Mean node definition.** No observational truth exists, and Swiss's mean node and published polynomials are different conventions (section 4.3). Node validation is BLOCKED until the owner chooses the definition.
3. **DE421 ends 2053-10-09.** GC-06, GC-19, GC-20 and part of TR-09 need DE440s (R-02b) or Horizons, both unavailable from this container.
4. **Time zones are not independently validated.** IANA is both the engine's and the fixtures' source. Pre-1956 India is a known gap (TZ-10).
5. **UTC as UT1.** Fixtures use the same assumption. The ≤ 0.9 s bound holds only from 1972; earlier eras are historical civil-time approximations (section 4.4, T-TIME-1).
6. **Future Delta T.** For 2027–2100 the Swiss extrapolation and the reference's Delta T differ; planets are therefore compared at the engine's TT. Delta T is verified and bounded on the time track (T-TIME-2 to T-TIME-4), and future-date results are QUALIFIED.
7. **Expected values are absent on purpose.** They are generated in the implementation work package after approval.
8. **Historical clocks.** GC-16, GC-17, GC-18, TZ-10 and TZ-11 test IANA rules only. Correct handling of historical city clocks is a release gate (SCI-03), not something these fixtures prove.
9. **Tolerances are not frozen.** Every numeric row in section 4 is BLOCKED for freeze until its pre-gate evidence is reviewed.
