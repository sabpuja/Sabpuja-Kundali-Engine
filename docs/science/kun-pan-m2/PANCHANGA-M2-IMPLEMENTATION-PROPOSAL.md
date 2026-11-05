# Panchanga M2: implementation proposal

**Status: PROPOSAL for owner and independent QA. Nothing here is approved, and no M2 code exists.**
Every convention below is a proposed default or a set of options. A pending decision is not treated as accepted.
Prepared with KUN-PAN-RPT-001 (issue #78, draft PR #79). M2 starts only after PR #79 passes independent QA, the owner takes
the decisions listed in section 10, step 0, and ChatGPT issues a numbered, bounded task.

## 1. Where M1 stops and what M2 adds

M1 (`sabpuja-panchanga/1`, accepted decisions D01-A, D02-M1, D07-A, D08-A, D09-A-M1, D10-A, D12-A, D13-A,
D14-A-M1, D15-a/b-R, D16-M1-INDEX, D18-A, D20-M1-SCOPED) computes the following at the birth instant:
- Tithi (with Paksha), Karana index, Yoga index, and Nakshatra and Pada;
- the start and end instant of each span.

It has no sunrise and no names. The KUN-PAN-RPT-001 report shows exactly this on three pages.

M2 would add, in order of customer value:

| Output | Customer value | Needs sunrise? | Main pending decision |
|---|---|---|---|
| Verified names for Tithi, Karana, Yoga | Very high: the numbers alone are hard to use | No | PAN-D07 (rest), PAN-D16 |
| Sunrise and sunset at the birthplace on the birth date | High | Yes | PAN-D03, PAN-D04, PAN-D17 |
| Vara (traditional weekday) plus the civil weekday | High | Yes | PAN-D05, PAN-D11 |
| Sunrise-day (daily) Panchang for the birth date, incl. kshaya / vriddhi Tithi | High: matches printed Panchangs | Yes | PAN-D02 (daily part), PAN-D06 |
| Masa (lunar month), Adhika / Kshaya Masa, Amanta or Purnimanta label | High | Not for the birth instant; yes for the daily object | PAN-D19 (split into M-1 to M-4 below) |
| Samvat (Vikram, Shaka years), optionally the 60-year Samvatsara name | Medium | No for the birth instant | PAN-D19 (S-1 to S-3 below) |
| Local display precision and ±2 min near-boundary flag for Panchanga times | Medium (trust) | No | PAN-D09 (rest), SCI-06 extension |

## 2. Principles carried over from M1 (unchanged)

- **Same Sun and Moon.** Geocentric apparent sidereal Lahiri longitudes from the pinned Swiss Ephemeris (SCI-01d, D01-A). No topocentric Moon.
- **Time scale and data.** UTC is treated as UT1 (SCI-01h). Local times come from pinned tzdata, inside the D13-A envelope (1970–2100).
- **Search.** Bracketing and bisection with the frozen D09-A-M1 / D10-A limits: 6 h steps, 2.5 days each way, 64 iterations, ≤ 0.5 s.
- **Fail closed.** No guessed place, time or zone, and no silent Moshier fallback. A failure gives a typed refusal or a typed `unavailable`, never a substitute value.
- **M1 is frozen.** M2 is a new contract, `sabpuja-panchanga/2`. For the same request it returns the M1 fields byte-identical (a test compares them against `/1`). Chart schema 0.3.0 does not change.
- **Status.** Every new field starts as `ENGINEERING_UNVERIFIED_PENDING_INDEPENDENT_QA` until its independent references pass.

## 3. Sunrise and sunset (PAN-D03, D04, D17)

The conventions are compared in SCI-PAN-01 section 5.6.

| Code | Definition | Documented in | Approximate offset in India |
|---|---|---|---|
| SUN-A | Upper limb, standard refraction: centre 50′ below the geometric horizon (USNO) | USNO definitions; Swiss default | reference |
| SUN-B | Swiss `SE_BIT_HINDU_RISING`: disc centre, no refraction, geocentric | Swiss programmer's manual | 3.2 to 4.3 min after SUN-D |
| SUN-D | Rashtriya Panchang (IMD) as reported by QA: upper limb, 31′ refraction, 16′ semidiameter (centre 47′ below) | IMD explanation page, **not yet read by Claude** | 12 to 17 s after SUN-A |

**Proposal (still conditional):**
- **D03.** Adopt SUN-D, computed at the birthplace, if a primary-source copy of the IMD explanation confirms the 47′ convention. Otherwise adopt SUN-A, which has an independently checkable USNO reference. SUN-B is the convention of much Jyotish software; offer it only as a documented alternative if the owner wants that practice. The difference from the other two is several minutes, so the choice is the owner's.
- **D04 (Swiss realisation).**
  - For SUN-D, use `swe_rise_trans_true_hor` with `SE_BIT_NO_REFRACTION | SE_BIT_FIXED_DISC_SIZE` and horizon height −31′. This is a hypothesis from the 2.10.03 source and must be proved by test before adoption.
  - For SUN-A, use the Swiss default.
  - Either way, measure the residual altitude at the returned instant, because `rise_set_fast` does not test convergence. Refuse if it exceeds a declared bound.
  - Use sea-level altitude, with pressure and temperature stated, not estimated.
- **D17.** Sunset uses the same convention and the same flags as sunrise. The manual's sunset example must not be copied (SCI-PAN-01 §5.6.3).
- **D11 (undefined sunrise).** Option D11-B: if there is physically no sunrise or sunset under the adopted convention, `vara`, sunrise, sunset and the daily object become a typed `unavailable` with reason `PANCHANGA_SUNRISE_UNDEFINED`. The birth-instant elements and the civil weekday are kept. Ephemeris or numerical failures still refuse the whole object. Under SUN-A or SUN-D this case occurs inside the ±66° band, above about 65.7°.
- **Display.** Sunrise and sunset are shown to the **minute**: their accuracy is limited by refraction, about a minute (USNO's own statement). The rounding rule (nearest or truncated) is decided once in the D09 remainder (section 7).

## 4. Vara (PAN-D05)

- `vara`: the weekday of the local sunrise that most recently preceded the birth, or coincides with it.
  - The day is half-open: [sunrise_d, sunrise_d+1).
  - The weekday comes from the civil weekday of that sunrise's local date.
  - No weekday epoch arithmetic is used.
- `civil_weekday`: the weekday of the local civil birth date (midnight to midnight). It is always output.
- When the two differ (a birth after midnight and before sunrise), the report says so in plain words. `vara` is never filled from the civil weekday.

## 5. Sunrise-day (daily) Panchang for the birth date (PAN-D02 daily part, PAN-D06)

This is a separate object, `daily`, so it is never confused with the birth-instant values (D02).

- **Contents:**
  - the Tithi, Nakshatra, Yoga and Karana in force at the local sunrise of the civil birth date, at the birthplace;
  - every end that falls before the next sunrise.
- **Kshaya and vriddhi Tithi.** A kshaya Tithi has zero sunrises; a vriddhi Tithi has two.
  - These cases are flagged, not resolved by any regional rule.
  - Test cases are needed where Tithi n begins and ends between two sunrises (kshaya), and where one Tithi spans two sunrises (vriddhi).
- **Sunrise outside the envelope.** If the governing sunrise falls outside the D13-A envelope (for example a birth on 1970-01-01 before sunrise), the daily object is `unavailable`. It is not computed outside the envelope.

## 6. Names (PAN-D07 remainder, PAN-D16)

Names need no astronomy and could be the first M2 step. They need verified source tables and human Hindi and
Jyotish editorial review.

| Set | Count | Proposed mapping from M1 indices (to verify) | Primary sources to capture |
|---|---|---|---|
| Tithi | 15 per Paksha + Purnima (15) and Amavasya (30) | Index 1–14 and 16–29 → Pratipada … Chaturdashi; 15 → Purnima; 30 → Amavasya | IMD names page (`packolkata.imd.gov.in/panchang/ta/tithi-nakshatra`); Indian Calendar Reform Committee Report (1955) |
| Karana | 11 names over 60 half-Tithis | 1 → Kimstughna; 2–57 → Bava, Balava, Kaulava, Taitila, Gara, Vanija, Vishti, repeating ×8; 58 → Shakuni; 59 → Chatushpada; 60 → Naga | IMD names page, which lists 11 Karana names (reported); a classical text (Surya Siddhanta) cited by edition and page |
| Yoga | 27 | Index 1 → Vishkambha … 27 → Vaidhriti | IMD names page, which lists 27 (reported) |
| Vara | 7 | Ravivara … Shanivara, from the weekday | Standard. Hindi spellings to the editorial register |
| Masa | 12 (+ Adhika prefix) | Chaitra … Phalguna | Calendar Reform Committee Report; Rashtriya Panchang |
| Samvatsara | 60 (optional) | Two different cycles are in use (north, Jupiter-based; south, a fixed cycle from the Shaka year) | Decision S-3; not proposed for the first M2 step |

**Rules:**
- **Publisher spellings.** They are recorded as printed. The IMD Kimstughna / Kinstughna discrepancy is kept as published. Sabpuja's EN and HI display forms are a separate editorial decision (OD-08), entered in `TERMINOLOGY.md`.
- **Engine output.** The engine emits stable machine ids, for example `karana_id: "bava"`. Display text comes only from the reviewed catalog.
- **Secondary sources.** Wikipedia and Panchang websites may be used to cross-check, never as the name table.
- **Index tests.** One test per set ties every index to its name. A second test checks that the M1 indices are unchanged.

**Access blocker.** In earlier work Claude could not open the IMD pages from this environment. Primary-source
capture therefore needs one of two routes:
- the owner or QA saves the pages or PDFs as dated evidence files;
- network access to the IMD domain is authorised.

## 7. Display precision and near-boundary flag (PAN-D09 remainder)

D09-A-M1 approved the machine output to the second and deferred the local display rule. After independent
QA (PR #79, comment 6659583110) the KUN-PAN-RPT-001 report prints transition times to the nearest minute,
marked "about": the UTC instant is rounded once, half up, and the same instant is converted to local time.
The machine output keeps its seconds. Recording this as the D09 display rule in `docs/DECISIONS.md` is an
owner step.

For M2 the proposal is:
- **Times.** Lunar transition times follow the same minute rule. Sunrise and sunset are also shown to the minute.
- **Near-boundary flag.** Extend the SCI-06 ±2 min disclosure to the Panchanga elements. When the birth is within ±2 min of a Tithi, Nakshatra, Yoga or Karana change, or of sunrise for the Vara, the report shows the existing near-boundary note. The window needs an owner decision, because SCI-06 covers six chart items only.

## 8. Masa and Samvat (PAN-D19, split into owner choices)

**Masa at the birth instant** needs no sunrise. It needs new moons (E = 0°, already an M1 boundary) and solar
ingresses (sankranti: the sidereal Sun entering a Rashi), found with the same search.

| Choice | Options | Proposal |
|---|---|---|
| M-1 Month system | Amanta (new moon to new moon; common in the south and west) / Purnimanta (full moon to full moon; common in the north) | Compute the Amanta month as the base. Show the Purnimanta name as a labelled alternative, because the Krishna Paksha takes the next month's name in Purnimanta. Owner chooses which is primary |
| M-2 Naming rule | The month is named after the sidereal solar month in which its starting new moon falls, plus one. For example, a new moon with the Sun in Mina starts Chaitra | Adopt after verification against the Calendar Reform Committee Report and the Rashtriya Panchang. Lahiri, as D01 |
| M-3 Adhika and Kshaya | Adhika: two new moons in one solar month, so the month has no sankranti and is the first of the two. Kshaya: two sankrantis in one lunar month (rare) | Flag both explicitly. Test cases come from published Adhika years, verified against the Rashtriya Panchang, never assumed |
| M-4 Instant or sunrise | Birth-instant Masa / Masa at the daily sunrise | Birth-instant in the birth object; sunrise-based in `daily` (section 5) |

**Samvat at the birth instant:**

| Choice | Options | Proposal |
|---|---|---|
| S-1 Eras | Vikram Samvat; Shaka Samvat (lunisolar); the Indian national (civil) Saka calendar, which is a different solar calendar starting 22 March | Show Vikram and Shaka (lunisolar) numbers. Never present the national civil Saka date as the lunisolar Shaka year |
| S-2 Year start | Chaitradi: the year starts with the Amanta Chaitra Shukla Pratipada. Kartikadi (Gujarat) | Chaitradi by default, with the convention printed. Kartikadi only if the owner wants it |
| S-3 Samvatsara names | North (Jupiter mean-sign) and south (fixed 60-year cycle) counts differ | Defer. Both need verified tables and an owner choice |

The year number changes at the instant of the new moon that begins Chaitra, under M-2 and M-3. It is never
assumed from the Gregorian year: Vikram = Gregorian + 57 only after the year start, + 56 before it. This offset
is a check in the tests, not the algorithm.

## 9. Contract, tests and gates

- **Contract.** `sabpuja-panchanga/2` contains the `/1` fields, plus:
  - `sunrise`, `sunset`, `vara`, `civil_weekday`;
  - `daily` (section 5);
  - `masa`, `samvat`;
  - `names` (machine ids only).
  - Every dependent field can be a typed `unavailable` with a reason.
  - Method blocks record the convention codes chosen (SUN-x, M-x, S-x) and a new method SHA.
- **Independent references.** These are recorded in a source register, with access dates and hashes:
  - USNO sunrise and sunset for Indian cities (14 cases already captured, two of them with no sunrise);
  - IMD Rashtriya Panchang daily rows for Tithi ends, Masa and sunrise. Note that IMD sunrise is for the Central Station only, never a city;
  - published Adhika Masa years;
  - Government of India gazette holiday dates for the year-start festivals (Chaitra Shukla Pratipada, as a civil-date check);
  - Calendrical Calculations (Reingold and Dershowitz), as a secondary algorithm cross-check only.
- **Tolerances.** Fixed by QA and the owner **before** any evaluation run (as PAN-D15):
  - sunrise and sunset: to the published minute, with the rounding window;
  - Masa and Samvat: exact names and numbers.
- **Gates:**
  - M1 fields stay byte-identical;
  - chart byte identity;
  - a new PAN-QA-08 identity version;
  - reproducible fixtures from the pinned ephemeris;
  - no names without the verified table and editorial sign-off.
- **Report.** The extended edition gains up to two pages only when these outputs exist, for about 15 pages in total:
  - **Birth day Panchang:** sunrise and sunset, Vara versus civil weekday, the sunrise values compared with the birth-instant values, and kshaya / vriddhi flags;
  - **Lunar month and year:** Masa (Amanta / Purnimanta), Adhika flag, Vikram and Shaka year, with the conventions stated.
  - Names would appear on the existing pages 10–11.
  - The ten-page edition stays byte-identical.

## 10. Proposed sequence (each a separate, numbered, bounded task with its own branch, draft PR and QA)

| Step | Task (proposed id) | Code? | Depends on |
|---|---|---|---|
| 0 | **KUN-PAN-M2-DEC-001**: decision packet and primary-source capture for D03, D04, D05, D06, D07, D09, D11, D16, D17 and D19 (M-1 to M-4, S-1 to S-3), with reference fixtures. Documentation and fixtures only | No | PR #79 passes QA; IMD evidence route (section 6) |
| 1 | KUN-PAN-M2-NAMES: verified name tables, machine ids, EN/HI catalog, report cards show names | Yes | D07, D16, editorial review |
| 2 | KUN-PAN-M2-SUN: sunrise, sunset, Vara, civil weekday, D11 behaviour | Yes | D03, D04, D05, D11, D17 |
| 3 | KUN-PAN-M2-DAILY: sunrise-day Panchang, kshaya / vriddhi flags | Yes | Step 2, D06 |
| 4 | KUN-PAN-M2-MASA: Masa and Samvat at the birth instant and at sunrise | Yes | D19 split, step 2 for the daily form |
| 5 | KUN-PAN-RPT-002: report pages for steps 1 to 4 | Yes (report only) | Steps 1 to 4 |

Vimshottari Dasha (KUN-A02) follows. Its own method decisions (year length, time arithmetic, the
Moon-Nakshatra balance at birth) can be prepared in parallel with step 0. It reuses the chart's Moon
longitude, not the Panchanga object.

## 11. What I could not verify for this proposal

- The IMD explanation and names pages (SUN-D, the Karana and Yoga name lists) have not been read by Claude. Their content above is as reported by QA.
- The Masa naming and Adhika rules (M-2, M-3) and the Samvat offsets in section 8 are standard descriptions from memory and secondary sources. They must be checked against the Calendar Reform Committee Report and the Rashtriya Panchang before adoption.
- No sunrise convention has been tested in this repository. The Swiss SUN-D realisation in section 3 is a hypothesis.
