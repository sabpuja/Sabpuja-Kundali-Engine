# Golden-chart validation specification, fixture inventory and tolerances

**Document ID:** SP-KUN-ACC-GOLD | **Work package:** CLAUDE-003 / KUN-01 Phase C | **Status:** PROPOSED test design. **No expected values exist yet.**

Method-dependent fixtures (anything with a sidereal value, a node, a Lagna or a category) must not be generated until the matching SCI decision is APPROVED in `docs/DECISIONS.md` on `main` and ChatGPT QA has passed this specification. Tolerances below are declared **before** any reference comparison has been run and must not be widened to make a failing case pass. A tolerance can change only through a documented decision that cites a reason other than "the test failed".

Acceptance IDs served: QA-005, QA-006, QA-007, QA-008, QA-009, QA-010, QA-012, QA-013 (`docs/ACCEPTANCE-MATRIX.md` on `main`).

## 1. Principles

1. **Independent truth.** Expected values come only from sources in [reference-sources.md](reference-sources.md) classes I-data, I-code or I-pub. The reference generator must not import `sabpuja_kundali` or `swisseph`; the QA harness enforces this (see [qa-architecture.md](qa-architecture.md)).
2. **Synthetic inputs only.** Every input is an invented date and time at a public city-centre coordinate. No real person's birth data, ever.
3. **Same question to both sides.** Each fixture records the method signature (ayanamsa variant, node, house model, ascendant vehicle, frame, apparent/geometric, geocentric, time-scale assumption). A fixture with a signature that differs from the engine's output metadata is reported as METHOD-MISMATCH, never as a pass or an implementation failure.
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
- **Planets and nodes** are compared at the same TT (section 4 note); the **ascendant** at the same UT1.

## 4. Tolerance proposal (declared before any comparison)

All values are maximum absolute circular differences. "S" is the ascendant's sensitivity to local sidereal time, `|∂λ_asc/∂θ|`, computed analytically by the reference for each fixture (≈1 near the equator, about 4 at 60°, much larger near the polar circle; probe [7]).

| ID | Quantity | Reference | Tolerance | Derivation |
|---|---|---|---|---|
| T-ICRF | Geocentric astrometric RA/Dec, ICRF (angular separation), Sun–Saturn and Moon | R-02 / R-02b / R-01 quantity 1 | **0.10"** | Swiss compression vs JPL ≤ 0.001" and documented Horizons reproduction ≈ 0.001" (R-10). Remaining budget is for DE431 vs DE421/DE440 data differences, **assumed** below 0.05" for 1900–2100; QA to confirm against the DE440 release paper. Frame-free: catches data and light-time defects |
| T-TROP-S | Tropical apparent ecliptic longitude of date | R-02 / R-02b (IAU 2006/2000A) | **0.10"** | Same physics family as Swiss (Vondrák 2011 vs IAU 2006 precession, IAU 2000B vs 2000A nutation: milliarcsecond level) plus T-ICRF budget |
| T-TROP-H | Same, against Horizons quantity 31 | R-01 | **0.50"** | Horizons of-date frame is IAU 1976/1980: documented constant 53 mas reference-ecliptic offset plus IAU 1976 precession-rate error ≈ 3 mas/yr, i.e. up to ≈ 0.3" at 1900 and 2100 (R-10, IAE 2019 note quoted there) |
| T-AYA | True Lahiri ayanamsha | Reimplementation of the approved definition with ERFA (R-04), and IAE printed tables (R-05) | **0.40"** | If SCI-01a approves Swiss mode 1: its documented spread against the IAE-reproducing IAU 1976 variant is −0.30" to +0.31" over 1900–2100 (probe [1]), plus 0.05" IAE print rounding. If the owner instead picks the IAU 1976 variant, this tightens to 0.10" |
| T-SID | Sidereal longitude, Sun–Saturn and Moon | T-TROP-S path − T-AYA path | **0.50"** | 0.10" + 0.40" |
| T-SID-H | Same via Horizons | T-TROP-H − T-AYA | **0.90"** | 0.50" + 0.40" |
| T-NODE | Tropical mean node, mean equinox of date | R-06 polynomial | **1.0"** | Upstream: Swiss mean node "estimated precision 1 arcsec" relative to DE431; R-06 is the published definition |
| T-NODE-SID | Sidereal mean Rahu and Ketu | T-NODE − mean ayanamsha path | **1.4"** | 1.0" + 0.40" |
| T-KETU | Ketu − Rahu − 180° (self-consistency, labelled) | none | **≤ 1e-8°** | Exact construction; only display rounding of two values remains |
| T-ASC | Tropical ascendant | ERFA sidereal time + true obliquity + spherical formula (R-04) at the same UT1 | **0.10" × max(1, S)** | Sidereal-time and obliquity model differences are milliarcsecond level; the formula amplifies any sidereal-time error by S, so the tolerance scales with S |
| T-ASC-SID | Sidereal ascendant | T-ASC − T-AYA | **0.10" × max(1, S) + 0.40"** | Sum |
| T-UTC | UTC instant from civil input | IANA rule (R-08) | **exact** | Discrete |
| T-CAT | Rashi, house, Nakshatra, Pada, D9 sign, D9 house | Harness oracle on reference longitude | **exact**, with BOUNDARY-INDETERMINATE band equal to the longitude tolerance used | Discrete |
| T-DT | Swiss Delta T vs IERS-derived Delta T | R-07 | **report only** | Delta T is not a pass/fail product quantity; recorded so that future-date Moon differences can be explained |

**Not hidden in the tolerances.** Birth-time precision (a one-minute uncertainty is up to about 16' of Lagna at the equator and ~1° at 60°), UTC-vs-UT1 (≤ 0.9 s) and future Delta T are product limitations. Fixtures share the same assumptions so these do not appear as false failures, and they are disclosed in method notes instead.

## 5. Fixture inventory

### 5.1 Golden charts (GC)

Coordinates are public city-centre values. Every input below was checked against IANA tzdata 2026e with [`evidence/fixture_input_check.py`](evidence/fixture_input_check.py) ([output](evidence/fixture_input_check.out)).

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
| GC-16 | 1905-06-01 09:00 +05:21:10 | Asia/Kolkata | 13.0827, 80.2707 | 1905-06-01 03:38:50 | IANA Madras railway time era | R-02 | SCI-01, SCI-03 |
| GC-17 | 1943-06-15 10:00 +06:30 | Asia/Kolkata | 13.0827, 80.2707 | 1943-06-15 03:30 | War time (single dubious source) | R-02 | SCI-01, SCI-03 |
| GC-18 | 1900-01-01 00:00 +05:21:10 | Asia/Kolkata | 22.5726, 88.3639 | 1899-12-31 18:38:50 | First local instant; **rejected by today's UTC-year rule, accepted by proposed local-date rule** | R-02 | SCI-03 |
| GC-19 | 2100-12-31 23:59 +14:00 | Pacific/Kiritimati | 1.8721, −157.4278 | 2100-12-31 09:59 | Last local instant, far east; DE421 out of range | R-02b | SCI-03 |
| GC-20 | 2100-12-31 23:59 −08:00 | America/Los_Angeles | 34.0522, −118.2437 | 2101-01-01 07:59 | Last local instant, west; UTC year 2101: **accepted only by the proposed local-date rule** | R-02b | SCI-03 |
| GC-21 | (input chosen after SCI-01g) | Europe/Oslo | 69.6492, 18.9553 | — | Outside proposed band: expect a fixed refusal, no chart | none (error expected) | SCI-01g |

At least four GC fixtures (proposed: GC-01, GC-04, GC-10, GC-06) are also generated through R-01 Horizons, and at least two through R-03 INPOP, so that every tropical path has a second, differently built reference.

### 5.2 Time-conversion fixtures (TZ)

These test civil-to-UTC conversion and refusal. They are **not independent of IANA** (the engine uses the same database); they verify correct application of a pinned tzdata version. Expected UTC values are in the evidence output.

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
| TZ-11a/b | 1945-10-14 23:30 +06:30 / +05:30 | Asia/Kolkata | Both accepted (end of war time, fold) |
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
2. **Mean node definition.** No observational truth exists; the reference is a published polynomial and T-NODE reflects definitional differences.
3. **DE421 ends 2053-10-09.** GC-06, GC-19, GC-20 and part of TR-09 need DE440s (R-02b) or Horizons, both unavailable from this container.
4. **Time zones are not independently validated.** IANA is both the engine's and the fixtures' source. Pre-1956 India is a known gap (TZ-10).
5. **UTC as UT1.** Fixtures use the same assumption; the true UT1 effect (≤ 0.9 s) is quantified with R-07 in the report, not tested against.
6. **Future Delta T.** For 2027–2100 the Swiss extrapolation and the reference's Delta T differ; planets are therefore compared at the engine's TT. The Delta T difference is reported (T-DT).
7. **Expected values are absent on purpose.** They are generated in the implementation work package after approval.
