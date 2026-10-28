# Stage C method facts reconciliation, Part B

**Do not give this file to the verifier until Part A ([METHOD-FACTS-CHECKLIST.md](METHOD-FACTS-CHECKLIST.md)) and the blind sheet are frozen and their checksums recorded.**

This part lists what the Stage A/B ChatGPT reviewer has already reported about IMD's methods, the conventions Sabpuja is considering, and the comparison to fill in. Everything in the "previously reported" columns is **reviewer-reported and unverified**. Claude has never read the IMD host. Nothing here selects a convention: PAN-D03, PAN-D07, PAN-D15 and PAN-D16 stay PENDING, and SCI-01a is unchanged.

Comparison outcome for each item: `MATCHED_PRIMARY_SOURCE`, `SOURCE_DISAGREEMENT`, `SOURCE_UNAVAILABLE`, `DATE_OR_TIME_AMBIGUOUS`, `SOURCE_METHOD_UNCLEAR` or `REVIEW_INCOMPLETE`. A Part A answer of NOT STATED against a reported fact is `SOURCE_METHOD_UNCLEAR`, and goes to the discrepancy register.

## 1. Sunrise and sunset

### Conventions under consideration (none selected)

| ID | Definition | Origin |
|---|---|---|
| SUN-A | Upper limb on the horizon with USNO nominal values: centre 50′ below the horizontal (34′ refraction plus 16′ semidiameter) | USNO definitions |
| SUN-B | Swiss Ephemeris "Hindu rising": centre of the disc on the geometric horizon, no refraction | Swiss Ephemeris documentation |
| SUN-D | IMD as reported: upper limb, 31′ refraction plus 16′ semidiameter, so the centre is 47′ below the horizontal | Reviewer report of the IMD explanation page |

### Comparison

| Part A item | Previously reported | Verifier's Part A record | Outcome | Discrepancy id |
|---|---|---|---|---|
| M-SUN-01 limb | Upper limb | | | |
| M-SUN-02 refraction | 31′ | | | |
| M-SUN-03 semidiameter | 16′ | | | |
| M-SUN-04 total depression | 47′ (centre below the horizontal) | | | |
| M-SUN-05 station | Central Station | | | |
| M-SUN-06 coordinates | 82°30′ E, 23°11′ N | | | |
| M-SUN-07 station only | Yes, the printed times apply to the Central Station | | | |
| M-SUN-08 altitude or horizon | Ideal horizon; altitude not reported | | | |
| M-SUN-09 rounding | Not reported | | | |
| Which of SUN-A, SUN-B, SUN-D, or none, the IMD wording describes | Reported as SUN-D | | | |

At printed-minute precision, the 12 sunrise and sunset candidates cannot distinguish SUN-D from SUN-A (about 12 to 17 s apart). Only the method text can.

## 2. General and time standard

| Part A item | Previously reported | Verifier's Part A record | Outcome | Discrepancy id |
|---|---|---|---|---|
| M-GEN-01 edition | Rashtriya Panchang, Saka 1948 (2026-27) web edition | | | |
| M-GEN-02 geocentric endings | Tithi, Nakshatra, Yoga and Karana endings are geocentric | | | |
| M-GEN-03 time standard | IST (UTC+05:30) | | | |
| M-GEN-04 rounding | Not reported | | | |
| M-GEN-05 day basis | Traditional sunrise-based day for displaying phenomena | | | |
| M-GEN-06 Vara | Not reported | | | |

## 3. Ayanamsa

| Part A item | Previously reported | Verifier's Part A record | Outcome | Discrepancy id |
|---|---|---|---|---|
| M-AYA-01 name, Lahiri, Chitrapaksha | Not reported verbatim | | | |
| M-AYA-02 epoch | 0h on 21 March 1956 | | | |
| M-AYA-03 time scale | Not stated in the report | | | |
| M-AYA-04 initial value | 23°15′00″ | | | |
| M-AYA-05 fixed or variable | Variable (increasing) | | | |
| M-AYA-06 mean or true | Not stated in the report | | | |
| M-AYA-07 precession model | Not named in the report | | | |
| M-AYA-08 Chaitra 2026 | 24°13′30″ (1 Chaitra 2026) | | | |
| M-AYA-09 Ashadha 2026 | 24°13′45″ (1 Ashadha 2026) | | | |
| M-AYA-10 Kartika 2026 | 24°14′02″ (1 Kartika 2026) | | | |

Claude's earlier comparison of these monthly values with Swiss Ephemeris true Lahiri (agreement within 0.8″, SCI-PAN-01 section 3.1) is an internal model-consistency observation. It is not independent ground truth and is not part of Stage C. Even a matched IMD Nakshatra or Yoga time does not become a Swiss calculation oracle until the ayanamsa definitions are shown to be compatible (Stage D).

## 4. Times after midnight

| Part A item | Previously reported | Verifier's Part A record | Outcome | Discrepancy id |
|---|---|---|---|---|
| M-CAL-01 rule | Times such as 25h and 26h mean 1 AM and 2 AM on the following Gregorian date | | | |
| M-CAL-02 date basis | Following Gregorian civil date | | | |
| M-CAL-03 notation | `h. hh-mm` 24-hour form for endings; sunrise and sunset seen in both `h. hh-mm` and `h:mm AM/PM` forms | | | |

**Interpretation used in the existing candidates.** A printed time `hh-mm` with `hh` of 24 or more, printed in the row for civil date D, is read as `(hh − 24):mm` IST on D + 1. The printed value and printed date are never changed; the interpreted IST time and the UTC minute are stored separately. Eight candidates depend on this rule:

| Assignment | Candidate |
|---|---|
| SC-13 | PAN-CAND-IMD-13 |
| SC-17 | PAN-CAND-IMD-17 |
| SC-20 | PAN-CAND-IMD-20 |
| SC-24 | PAN-CAND-IMD-24 |
| SC-29 | PAN-CAND-IMD-29 |
| SC-39 | PAN-CAND-IMD-39 |
| SC-42 | PAN-CAND-IMD-42 |
| SC-44 | PAN-CAND-IMD-44 |

Their candidate interpretations and UTC minutes are in the crosswalk (`extended_hour_value` = `YES`). Reconciliation checks the verifier's own `V09` against them in `R05`. If M-CAL-01 is NOT STATED, all eight rows are `DATE_OR_TIME_AMBIGUOUS`.

## 5. Karana indexing

| Part A item | Previously reported | Verifier's Part A record | Outcome | Discrepancy id |
|---|---|---|---|---|
| M-KAR-01 movable | Seven repeating Karanas | | | |
| M-KAR-02 fixed | Four fixed Karanas | | | |
| M-KAR-03 fixed positions | Not reported from IMD (the candidate rule places Sakuni #58, Chatuspada #59, Naga #60, Kimstughna #1) | | | |
| M-KAR-04 start of movable cycle | Not reported from IMD (candidate rule: #2) | | | |
| M-KAR-05 New Moon rollover | Not reported verbatim | | | |
| M-KAR-06 spelling | Names page: Kimstughna. Daily row 2026-07-14: Kinstughna | | | |
| M-KAR-07 complete table | Principle described; complete 60-position table not reported | | | |

The candidate rule comes from a secondary source (SCI-PAN-01 section 5.5). It is not adopted (PAN-D07 PENDING). The 14 Karana candidates are consistent with it, which is consistency evidence, not verification. The rule still lacks verified Sakuni (#58) and Chatuspada (#59) rows.

## 6. Names

Publisher spellings are kept separately from Sabpuja's proposed identifiers. **No engine identifier or translation changes as a result of this comparison**; that is PAN-D16 and the OD-08 editorial review.

**Karana**, names page as reported, against SCI-PAN-01 Appendix A:

| # | Reported IMD spelling | Sabpuja proposed English | Verifier's M-NAM record | Outcome |
|---|---|---|---|---|
| 1 | Bava | Bava | | |
| 2 | Balava | Balava | | |
| 3 | Kaulava | Kaulava | | |
| 4 | Taitila | Taitila | | |
| 5 | Gara | Gara | | |
| 6 | Vanij | Vanija | | |
| 7 | Vishti | Vishti (Bhadra) | | |
| 8 | Sakuni | Shakuni | | |
| 9 | Chatuspada | Chatushpada | | |
| 10 | Naga | Naga | | |
| 11 | Kimstughna | Kimstughna | | |

**Yoga.** The full 27-name IMD list has not been reported. Sabpuja's proposed sequence (Appendix A) is shown so the verifier's list can be compared position by position. Publisher spellings seen in daily-row candidates are noted.

| # | Sabpuja proposed English | Publisher spelling seen in candidates | Verifier's M-NAM record | Outcome |
|---|---|---|---|---|
| 1 | Vishkambha | Viskumbha | | |
| 2 | Priti | | | |
| 3 | Ayushman | | | |
| 4 | Saubhagya | | | |
| 5 | Shobhana | | | |
| 6 | Atiganda | | | |
| 7 | Sukarma | | | |
| 8 | Dhriti | | | |
| 9 | Shula | | | |
| 10 | Ganda | | | |
| 11 | Vriddhi | | | |
| 12 | Dhruva | | | |
| 13 | Vyaghata | Vyaghata | | |
| 14 | Harshana | | | |
| 15 | Vajra | Vajra | | |
| 16 | Siddhi | | | |
| 17 | Vyatipata | Vyatipata | | |
| 18 | Variyan | Variyan | | |
| 19 | Parigha | | | |
| 20 | Shiva | | | |
| 21 | Siddha | | | |
| 22 | Sadhya | | | |
| 23 | Shubha | | | |
| 24 | Shukla | | | |
| 25 | Brahma | | | |
| 26 | Indra | | | |
| 27 | Vaidhriti | Vaidhriti | | |

**Nakshatra.** Sabpuja's proposed English is the chart engine's existing name set.

| # | Sabpuja / engine English | Publisher spelling seen in candidates | Verifier's M-NAM record | Outcome |
|---|---|---|---|---|
| 1 | Ashwini | Asvini | | |
| 2 | Bharani | Bharani | | |
| 3 | Krittika | Krittika | | |
| 4 | Rohini | | | |
| 5 | Mrigashira | | | |
| 6 | Ardra | | | |
| 7 | Punarvasu | Punarvasu | | |
| 8 | Pushya | | | |
| 9 | Ashlesha | | | |
| 10 | Magha | Magha | | |
| 11 | Purva Phalguni | | | |
| 12 | Uttara Phalguni | | | |
| 13 | Hasta | | | |
| 14 | Chitra | | | |
| 15 | Swati | | | |
| 16 | Vishakha | | | |
| 17 | Anuradha | | | |
| 18 | Jyeshtha | | | |
| 19 | Mula | | | |
| 20 | Purva Ashadha | | | |
| 21 | Uttara Ashadha | | | |
| 22 | Shravana | | | |
| 23 | Dhanishta | | | |
| 24 | Shatabhisha | | | |
| 25 | Purva Bhadrapada | | | |
| 26 | Uttara Bhadrapada | | | |
| 27 | Revati | | | |

Distinctions to keep exactly as found, never normalised: Viskumbha / Vishkambha, Asvini / Ashwini, Sakuni / Shakuni, Chatuspada / Chatushpada, Vanij / Vanija, Kimstughna / Kinstughna. A difference between the publisher spelling and the Sabpuja proposed form is **not** a discrepancy; it is the editorial question PAN-D16. A difference between the verifier's transcription and the reported IMD spelling **is** a discrepancy.

## 7. Reconciliation record

| Field | Entry |
|---|---|
| Reconciled by | |
| Date (UTC) | |
| SHA-256 of the frozen Part A file compared | |
| Items matched | |
| Items disputed | |
| Items NOT STATED or unclear | |
| Discrepancy ids raised | |
