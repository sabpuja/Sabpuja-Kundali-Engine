# WP-B1 Panchanga source and provenance register

**Status:** PROPOSED - NOT CANONICAL - OWNER SCIENTIFIC-METHOD APPROVAL PENDING
**Prepared by:** Claude (Lead Developer), WP-B1, 2026-10-28. All access dates are 2026-10-28 unless stated.
**Baseline:** `main` `5395d2bc33847d1363e6d838f6109bad552221e3`

Each source has a role. **Reference** means it supplies expected values in a fixture. **Method** means it defines or documents a convention. **Context** means it is cited for background and supplies no expected value. A source that only republishes another publisher's Panchanga is not used as ground truth.

## 1. Sources used for fixtures or methods

| ID | Publisher, title | Edition / version | What it gives | Method it states | Location | Precision | Independence | Rights / reuse | Role |
|---|---|---|---|---|---|---|---|---|---|
| SRC-USNO-PHASES | U.S. Naval Observatory, Astronomical Applications Dept., API `moon/phases/year?year=2026` <https://aa.usno.navy.mil/api/moon/phases/year?year=2026> | API version 4.0.1 | 50 primary lunar phase instants for 2026 | Phase defined by SRC-USNO-PHASE-DEF; times in Universal Time (API documentation) | Geocentric (location independent) | 1 minute; rounding rule not stated | Own computation by a national almanac office | U.S. Government work; no usage terms stated on the API documentation page | Reference |
| SRC-USNO-PHASE-DEF | USNO, "Phases of the Moon and Percent of the Moon Illuminated" <https://aa.usno.navy.mil/faq/moon_phases> | Accessed page | Definition: phases occur when the excess of the Moon's apparent ecliptic longitude over the Sun's is 0, 90, 180, 270 degrees | Apparent ecliptic longitudes; the page does not say "geocentric" explicitly and does not state the time scale | n/a | n/a | Primary | U.S. Government work | Method |
| SRC-NASA-PHASES | NASA Goddard Space Flight Center, F. Espenak, "Phases of the Moon: 2001 to 2100" <https://eclipse.gsfc.nasa.gov/phase/phases2001.html> | Accessed page | Same 50 events for 2026, plus eclipse markers | Universal Time; ΔT listed as 00h01m for 2026 | Geocentric | 1 minute | Independent computation (different publisher and software from USNO) | NASA web content, no copyright notice on the page; only individual times are recorded | Reference (cross-check) |
| SRC-USNO-RSTT | USNO API `rstt/oneday` <https://aa.usno.navy.mil/api/rstt/oneday> (each query URL is stored in the fixture) | API version 4.0.1 | Sunrise, sunset, transit, civil twilight and civil weekday for given coordinates, date and fixed UTC offset | SRC-USNO-RST-DEF | The exact coordinates queried only | 1 minute | Own computation | U.S. Government work | Reference |
| SRC-USNO-RST-DEF | USNO, "Rise, Set, and Twilight Definitions" <https://aa.usno.navy.mil/faq/RST_defs> | Accessed page | Sunrise/sunset = upper limb on horizon; centre geometrically 50' below horizontal (16' semidiameter + 34' refraction); sea level, level horizon, average atmosphere; times may be in error by a minute or more; accuracy decreases at high latitude | Astronomical (upper limb, refracted) | n/a | n/a | Primary | U.S. Government work | Method |
| SRC-USNO-API-DOC | USNO, "Data Services API" documentation <https://aa.usno.navy.mil/data/api> | Accessed page | Parameter meanings (east-positive tz, dst default false, year 1700 to 2100); continuous above/below horizon reported as notes with null time | n/a | n/a | n/a | Primary | U.S. Government work | Method |
| SRC-SWISS-PRG | Astrodienst, *Programming Interface to the Swiss Ephemeris*, section 6.1 "swe_rise_trans() and swe_rise_trans_true_hor()" and "Sunrise in Astronomy and in Hindu Astrology" | Version 2.10.03, dated 27-aug-2022, as shipped in `libswe/doc/swephprg.md` inside the pinned `pyswisseph==2.10.3.2` sdist (sha256 `c54c305e83dbd5d2b71e58d8a69d8ee41de24c4d3328ce09e2af860a3537624d`). Online edition: <https://www.astro.com/swisseph/swephprg.htm> | rsmi flags, return codes (0, -1, -2), the Hindu-rising definition, pressure/temperature behaviour | Astronomical default; `SE_BIT_HINDU_RISING` = centre, no refraction, geocentric, ecliptic latitude ignored | n/a | n/a | Vendor documentation of the engine itself (not independent of Swiss) | AGPL / Swiss Ephemeris licence, same as the engine | Method |
| SRC-SWISS-SRC | Swiss Ephemeris C source `libswe/swecl.c` and `libswe/swephexp.h` in the same pinned sdist | `SE_VERSION "2.10.03"` | Actual behaviour of the flags (see SCI-PAN-01 section 5.6.3) | n/a | n/a | n/a | Vendor source (not independent) | AGPL | Method |

## 2. Sources cited for definitions only (no expected values)

| ID | Citation | Use | Limitation |
|---|---|---|---|
| SRC-WP-TITHI | Wikipedia, "Tithi" <https://en.wikipedia.org/wiki/Tithi> | Tithi names and order; sunrise rule; kshaya/adhika description. It cites Chatterjee and Chakravarty, "Indian Calendar from Post-Vedic Period to AD 1900", in Sen and Shukla (eds.), *History of Astronomy in India*, INSA, p. 296 | Secondary, editable. Not a ground-truth source |
| SRC-WP-YOGA | Wikipedia, "Nityayoga" <https://en.wikipedia.org/wiki/Nityayoga> | 27 Yoga names and order; 13°20' (800') segments of the sidereal sum. Cites Sewell and Dikshit, *The Indian Calendar* (1896) pp. 3 and 97; Burgess, "Translation of the Surya-Siddhanta", *JAOS* 6 (1858-60); S. B. Dikshit, *Bharatiya Jyotish Shastra* Part II (IMD English translation, 1981) pp. 277-279; S. D. Sharma, *BASI* 26 (1998) 75-90 | Secondary. The cited primary works were **not** retrieved in WP-B1 |
| SRC-WP-KARANA | Wikipedia, "Karana (pancanga)" <https://en.wikipedia.org/wiki/Karana_(pancanga)> | Karana sequence: #1 Kimstughna, #2 to #57 seven movable Karanas eight times, #58 Shakuni, #59 Chatushpada, #60 Naga | Secondary. **The page's own table contradicts its stated cyclic rule** (for example Ekadashi first half), which is direct evidence that Karana naming must be verified against a primary source before adoption |
| SRC-DRIK-FAQ | Drik Panchang, "Hindu Sunrise and Hindu Sunset" <https://www.drikpanchang.com/faq/faq-ans2.html> | Practice evidence only: a widely used commercial Panchang states it uses the centre of the disc without refraction for Panchang and festival work | Commercial astrology website; **not** a scientific reference and not ground truth |

## 3. Sources identified but not retrieved by Claude

| ID | Resource | Why not retrieved | Consequence |
|---|---|---|---|
| SRC-IMD-RP | Positional Astronomy Centre, IMD: Rashtriya Panchang explanation (<https://packolkata.imd.gov.in/panchang/en/explanation>), daily Panchang, English editions, per-city sunrise tables (URLs in [imd-rashtriya-panchang-capture-template.json](reference-fixtures/imd-rashtriya-panchang-capture-template.json)). The reviewer later opened the explanation page directly (review 5680023508); see section 5 | Host `packolkata.imd.gov.in` refused by this environment's network policy (proxy HTTP 403); the web-reading tool reported a robots disallow; a web-archive copy was also blocked; a third-party Scribd copy was neither readable nor acceptable as a primary source | **No IMD fixture exists.** IMD's ayanamsa wording, sunrise convention, station, rounding and Karana list are UNVERIFIED by Claude (a reviewer has reported some of them; see SRC-REVIEW-5679285841). All Nakshatra and Yoga ending-time fixtures are missing |
| SRC-IMD-NAMES | IMD `panchang/en/tithi-nakshatra` (official Yoga and Karana names, as identified by PM/QA review 5679285841); the reviewer later read the English table under `panchang/te/tithi-nakshatra` | Robots disallow for the reading tool and network refusal for direct download, re-tried 2026-10-28 | Candidate primary name source for PAN-D07/D16. Not read by Claude; the Karana list reported in SRC-IMD-HANDOFF-6464388772 is held as a candidate |
| SRC-IMD-DAILY | IMD `panchang/bn/chaitra`, `panchang/bn/ashadha`, `panchang/bn/kartika` (2026-27 daily Panchanga, English body text per the review) | Same | Not read by Claude. 46 reviewer-transcribed values are held as candidates in the capture template, each with its URL and retrieval tier |
| SRC-REVIEW-5680023508 | ChatGPT PM/QA review on PR #51, 2026-10-28: QA PASS of the candidate transcription, plus a direct reopening of the explanation, names (`/panchang/ta/tithi-nakshatra`) and three daily pages | Read | **Stage B evidence only** (same reviewer as Stage A). Not an independent second-person verification |
| SRC-REVIEW-5679285841 | ChatGPT PM/QA review on PR #51, posted from the owner's GitHub account, 2026-10-28 | Read | **Not a primary source.** It reports IMD method facts (upper limb, 31′ refraction + 16′ semidiameter = 47′; Central Station 82°30′ E, 23°11′ N) and sample values. Recorded as reviewer-reported and unverified; used to frame SUN-D and the capture plan, never as an expected value |
| SRC-IMD-HANDOFF-6464388772 | Owner-authorized reviewer-mediated IMD evidence handoff, PR #51 comment 6464388772, 2026-10-28 (ChatGPT PM/QA reviewer) | Read | **Not a primary source.** Field-level transcriptions from official IMD pages: 30 from pages the reviewer opened (Chaitra, Kartika) and 16 from official-domain index text only (Ashadha), plus method facts (47′ sunrise, Central Station, IST endings, ayanamsa values, Karana names, 24-hour-plus usage). Held as candidates; promotion rule in SCI-PAN-01 section 8.1. No page was copied |
| SRC-SS-BURGESS | Burgess, *Translation of the Surya Siddhanta* (University of Calcutta reprint 1935, archive.org item `SuryaSiddhantaTranslation`) | Only front matter readable through the tool; Chapter II not reached; direct download blocked | Classical Karana/Yoga/Nakshatra verses not quoted |
| SRC-SEWELL-DIKSHIT | Sewell and Dikshit, *The Indian Calendar* (1896) | Not located in a readable form | Karana mapping remains unverified at primary-source level |
| SRC-SHARMA-BASI | S. D. Sharma, "Development of Pancanga from vedic times upto the present", *BASI* 26 (1998) 75-90 | ADS abstract page disallowed for the tool | Not used |

## 4. Independence statement

- No expected value in any fixture was computed by the Sabpuja engine, by Swiss Ephemeris, or by anything in PR #48. PR #48 was not opened, read, copied or imported.
- PR #47 (`77c4223a80e8dad9b7ec7676cc766528dee1c11f`) was read for context only. Its proposals are not treated as approved and none of its text is reused as a source.
- Swiss Ephemeris documentation and source are used to describe **how the engine would behave**, never as an independent reference for a numerical outcome.
- USNO and NASA are both computations, not observations. They are independent of each other and of Swiss Ephemeris. Their agreement within one minute on all 50 events is the cross-check.
- The fixture values were read through an automated page-reading tool. The two phase tables were read separately and agree with each other, and the USNO rise/set responses report closest-phase times that agree with the phase table after the +05:30 or other offsets. QA should still re-read each row from the live source.
- The 46 IMD candidates were transcribed and rechecked by the ChatGPT reviewer, not by Claude. Claude checked them only for internal consistency and against the handoff text. No IMD value is an expected value until Stage D (section 5).

## 5. IMD verification register

### 5.1 Stages

| Stage | Meaning | Who | Status for the 46 candidates |
|---|---|---|---|
| A. Reviewer-sourced candidate | Value transcribed from an official-domain source | ChatGPT PM/QA reviewer (comment 6464388772) | 46 done: 30 from opened HTML, 16 from index text only |
| B. Primary page rechecked | Official page reopened and compared with the candidate | Same reviewer (review 5680023508), per date block | 46 done; not independent |
| C. Independent second-person verification | A distinct authorized verifier reads the primary source and checks the exact record | Not yet assigned | **0 done** |
| D. Engineering reference acceptance | C done, plus notation conversion check, source rights and method compatibility | QA and owner | **0 done** |

Only Stage D records may enter an approved engineering golden-reference set. Claude's consistency calculations (SCI-PAN-01 sections 3.1, 5.5 and 5.6.1) do not replace Stage C, and Claude has not signed any stage. The `retrieval_tier` of each candidate records Stage A and is never rewritten.

### 5.2 Publisher, rights and access

| Item | Record |
|---|---|
| Publisher | Positional Astronomy Centre, India Meteorological Department, Government of India |
| Publication | Rashtriya Panchang, Saka 1948 (2026-27) web edition: daily pages `/panchang/bn/chaitra`, `/bn/ashadha`, `/bn/kartika`; explanation `/panchang/en/explanation`; names `/panchang/ta/tithi-nakshatra` (first seen as index text under `/te/`) |
| Access | Stage A and Stage B both 2026-10-28, by the ChatGPT reviewer. Claude: no access (network policy and robots); no other route used |
| Rights notice | The pages identify the Government of India as publisher and show an all-rights-reserved notice (reported by the owner and reviewer; not read by Claude) |
| Reuse permission | **Unresolved.** Only minimal individual factual fields are recorded. No page text, screenshot or PDF is committed, and republication rights are not assumed |
| Commercial sites | Not used as a substitute for any government record |

### 5.3 Row-level register

Columns A to D are the stages above. The printed value is exactly as transcribed. The interpreted IST time is deterministic arithmetic: the 8 values of 24 hours or more use IMD's stated rule (25h = 1 AM on the following Gregorian date). Every row has status `REVIEWER_SOURCED_PENDING_VERIFICATION` in the [capture template](reference-fixtures/imd-rashtriya-panchang-capture-template.json), which also holds each row's UTC minute, method dependencies and open ambiguities. A Stage C verifier should open the page in column 3 and compare columns 2, 4, 5 and 6.

| Candidate | Printed date | Page | Element | Printed name | Printed value | Interpreted IST | Stage A tier | A | B | C | D |
|---|---|---|---|---|---|---|---|---|---|---|---|
| PAN-CAND-IMD-01 | 2026-03-22 | chaitra | tithi | Chaitra Sukla Chaturthi | `h. 21-17` | 2026-03-22T21:17+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-02 | 2026-03-22 | chaitra | nakshatra | Bharani | `h. 22-43` | 2026-03-22T22:43+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-03 | 2026-03-22 | chaitra | yoga | Vaidhriti | `h. 15-42` | 2026-03-22T15:42+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-04 | 2026-03-22 | chaitra | karana | Vanij | `h. 10-37` | 2026-03-22T10:37+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-05 | 2026-03-22 | chaitra | karana | Vishti | `h. 21-17` | 2026-03-22T21:17+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-06 | 2026-03-22 | chaitra | sunrise | — | `6:02 AM` | 2026-03-22T06:02+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-07 | 2026-03-22 | chaitra | sunset | — | `6:12 PM` | 2026-03-22T18:12+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-08 | 2026-03-23 | chaitra | tithi | Chaitra Sukla Panchami | `h. 18-39` | 2026-03-23T18:39+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-09 | 2026-03-23 | chaitra | nakshatra | Krittika | `h. 20-50` | 2026-03-23T20:50+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-10 | 2026-03-23 | chaitra | yoga | Viskumbha | `h. 12-22` | 2026-03-23T12:22+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-11 | 2026-03-23 | chaitra | karana | Bava | `h. 7-57` | 2026-03-23T07:57+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-12 | 2026-03-23 | chaitra | karana | Balava | `h. 18-39` | 2026-03-23T18:39+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-13 | 2026-03-23 | chaitra | karana | Kaulava | `h. 29-22` | 2026-03-24T05:22+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-14 | 2026-03-23 | chaitra | sunrise | — | `h. 6-01` | 2026-03-23T06:01+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-15 | 2026-03-23 | chaitra | sunset | — | `h. 18-12` | 2026-03-23T18:12+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-16 | 2026-07-14 | ashadha | tithi | Shuddha Jyaishtha Krishna Amavasya | `h. 15-14` | 2026-07-14T15:14+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-17 | 2026-07-14 | ashadha | nakshatra | Punarvasu | `h. 24-10` | 2026-07-15T00:10+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-18 | 2026-07-14 | ashadha | yoga | Vyaghata | `h. 11-57` | 2026-07-14T11:57+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-19 | 2026-07-14 | ashadha | karana | Naga | `h. 15-14` | 2026-07-14T15:14+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-20 | 2026-07-14 | ashadha | karana | Kinstughna | `h. 25-30` | 2026-07-15T01:30+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-21 | 2026-07-14 | ashadha | sunrise | — | `5:23 AM` | 2026-07-14T05:23+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-22 | 2026-07-14 | ashadha | sunset | — | `6:49 PM` | 2026-07-14T18:49+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-23 | 2026-07-17 | ashadha | tithi | Ashadha Sukla Tritiya | `h. 6-28` | 2026-07-17T06:28+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-24 | 2026-07-17 | ashadha | tithi | Ashadha Sukla Chaturthi | `h. 28-43` | 2026-07-18T04:43+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-25 | 2026-07-17 | ashadha | nakshatra | Magha | `h. 18-35` | 2026-07-17T18:35+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-26 | 2026-07-17 | ashadha | yoga | Vyatipata | `h. 22-46` | 2026-07-17T22:46+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-27 | 2026-07-17 | ashadha | karana | Gara | `h. 6-28` | 2026-07-17T06:28+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-28 | 2026-07-17 | ashadha | karana | Vanij | `h. 17-31` | 2026-07-17T17:31+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-29 | 2026-07-17 | ashadha | karana | Vishti | `h. 28-43` | 2026-07-18T04:43+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-30 | 2026-07-17 | ashadha | sunrise | — | `5:24 AM` | 2026-07-17T05:24+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-31 | 2026-07-17 | ashadha | sunset | — | `6:48 PM` | 2026-07-17T18:48+05:30 | Index text only | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-32 | 2026-10-26 | kartika | tithi | Asvina Sukla Purnima | `h. 9-42` | 2026-10-26T09:42+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-33 | 2026-10-26 | kartika | nakshatra | Asvini | `h. 17-41` | 2026-10-26T17:41+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-34 | 2026-10-26 | kartika | yoga | Vajra | `h. 14-17` | 2026-10-26T14:17+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-35 | 2026-10-26 | kartika | karana | Bava | `h. 9-42` | 2026-10-26T09:42+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-36 | 2026-10-26 | kartika | karana | Balava | `h. 20-24` | 2026-10-26T20:24+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-37 | 2026-10-26 | kartika | sunrise | — | `6:02 AM` | 2026-10-26T06:02+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-38 | 2026-10-26 | kartika | sunset | — | `5:25 PM` | 2026-10-26T17:25+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-39 | 2026-10-28 | kartika | tithi | Asvina Krishna Tritiya | `h. 25-07` | 2026-10-29T01:07+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-40 | 2026-10-28 | kartika | nakshatra | Krittika | `h. 13-26` | 2026-10-28T13:26+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-41 | 2026-10-28 | kartika | yoga | Vyatipata | `h. 7-19` | 2026-10-28T07:19+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-42 | 2026-10-28 | kartika | yoga | Variyan | `h. 27-41` | 2026-10-29T03:41+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-43 | 2026-10-28 | kartika | karana | Vanij | `h. 14-37` | 2026-10-28T14:37+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-44 | 2026-10-28 | kartika | karana | Vishti | `h. 25-07` | 2026-10-29T01:07+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-45 | 2026-10-28 | kartika | sunrise | — | `6:03 AM` | 2026-10-28T06:03+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
| PAN-CAND-IMD-46 | 2026-10-28 | kartika | sunset | — | `5:24 PM` | 2026-10-28T17:24+05:30 | Opened HTML | Done | Done (same reviewer) | Pending | Pending |
