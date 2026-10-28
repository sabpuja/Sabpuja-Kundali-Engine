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

## 3. Sources identified but not retrieved

| ID | Resource | Why not retrieved | Consequence |
|---|---|---|---|
| SRC-IMD-RP | Positional Astronomy Centre, IMD: Rashtriya Panchang explanation, daily Panchang, English editions, per-city sunrise tables (URLs in [imd-rashtriya-panchang-capture-template.json](reference-fixtures/imd-rashtriya-panchang-capture-template.json)) | Host `packolkata.imd.gov.in` refused by this environment's network policy (proxy HTTP 403); the web-reading tool reported a robots disallow; a web-archive copy was also blocked; a third-party Scribd copy was neither readable nor acceptable as a primary source | **No IMD fixture exists.** IMD's ayanamsa wording, sunrise convention, station, rounding and Karana list are UNVERIFIED. All Nakshatra and Yoga ending-time fixtures are missing |
| SRC-SS-BURGESS | Burgess, *Translation of the Surya Siddhanta* (University of Calcutta reprint 1935, archive.org item `SuryaSiddhantaTranslation`) | Only front matter readable through the tool; Chapter II not reached; direct download blocked | Classical Karana/Yoga/Nakshatra verses not quoted |
| SRC-SEWELL-DIKSHIT | Sewell and Dikshit, *The Indian Calendar* (1896) | Not located in a readable form | Karana mapping remains unverified at primary-source level |
| SRC-SHARMA-BASI | S. D. Sharma, "Development of Pancanga from vedic times upto the present", *BASI* 26 (1998) 75-90 | ADS abstract page disallowed for the tool | Not used |

## 4. Independence statement

- No expected value in any fixture was computed by the Sabpuja engine, by Swiss Ephemeris, or by anything in PR #48. PR #48 was not opened, read, copied or imported.
- PR #47 (`77c4223a80e8dad9b7ec7676cc766528dee1c11f`) was read for context only. Its proposals are not treated as approved and none of its text is reused as a source.
- Swiss Ephemeris documentation and source are used to describe **how the engine would behave**, never as an independent reference for a numerical outcome.
- USNO and NASA are both computations, not observations. They are independent of each other and of Swiss Ephemeris. Their agreement within one minute on all 50 events is the cross-check.
- The fixture values were read through an automated page-reading tool. The two phase tables were read separately and agree with each other, and the USNO rise/set responses report closest-phase times that agree with the phase table after the +05:30 or other offsets. QA should still re-read each row from the live source.
