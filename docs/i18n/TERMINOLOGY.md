# Terminology register (English / Hindi), KUN-I18N-001 and KUN-I18N-002

**Status: developer draft. Pending independent human Hindi editorial review. Not owner-approved.**
The KUN-I18N-002 corrections below are developer corrections of objective defects; they are not a
human linguistic review, and the human editorial gate at the end of this page is still open.
Engineering acceptance (rendering, extraction, shaping, layout, privacy) is separate from Hindi
editorial acceptance; nothing here claims a linguistic review has taken place.

Source of truth: `prototype/kundali_prototype/static/i18n.json` (terms, engine sentences and the
web interface) and `report/phase1/report_i18n.json` (the ten-page PDF). Both are loaded by
`report/phase1/report_locale.py`, which checks at import that every entry has both languages, the
same placeholders and NFC text. This page lists the core terms; the tables below are generated
from the catalog.

## Conventions

- **numerals:** International (Latin) digits in both languages for every number, degree, date, time and offset, so engine values are shown exactly as calculated.
- **spelling:** Hindi follows the Kendriya Hindi Nideshalaya standard: anusvara for nasal clusters (कुंडली, चंद्र, कुंभ), chandrabindu where no vowel sign sits above the headline (बनाएँ), nukta in loanwords (फ़ाइल, फ़रवरी).
- **latin_kept:** Proper names of software, data sets, licences and standards (Sabpuja, Swiss Ephemeris, pyswisseph, IANA, tzdata, GeoNames, Natural Earth, AGPL-3.0, SIL Open Font License, Poppins, Inter), file names, hashes, URLs, codes (UTC, D1, D9, SHA-256, error codes) and the engine status code stay in Latin script in both languages.
- **Locale is presentation only.** The engine response is never changed. Engine values
  (Rashi, Nakshatra, place id, fixed metadata sentences) are replaced by their Hindi display form
  by exact lookup; a value the register does not contain makes the Hindi report refuse
  (`ReportLocaleError`, HTTP 503 `REPORT_UNAVAILABLE`) rather than show English or a guess.

## Core vocabulary

| Concept | English | Hindi | Note |
|---|---|---|---|
| Birth chart | Janam Kundali | जन्म कुंडली | |
| Ascendant | Lagna (Asc) | लग्न | chart label is the full word, not an abbreviation |
| Sign | Rashi | राशि | |
| House | House | भाव | |
| Whole-sign house | whole-sign house | पूर्ण-राशि भाव | review item |
| Planet | Graha | ग्रह | |
| Navamsa (D9) | Navamsa | नवांश | |
| Lunar mansion | Nakshatra | नक्षत्र | |
| Quarter | Pada | चरण | review item: चरण rather than पद |
| Sidereal | sidereal | निरयन | |
| Longitude | longitude | भोगांश | |
| Ayanamsa | ayanamsa | अयनांश | |
| Mean node | mean node | मध्यम पात | review item |
| Mean Rahu | mean Rahu | मध्यम राहु | review item; same convention as मध्यम पात |
| Lunar nodes | lunar nodes | चंद्र पात | one form everywhere (KUN-I18N-002) |
| Date of birth | date of birth | जन्म दिनांक | तिथि avoided: it is the Panchanga lunar day |
| Time of birth | time of birth | जन्म समय | |
| Birthplace | birthplace | जन्म स्थान | |
| Prepared for (cover) | Prepared for | जातक | review item |

## Rashis

| Engine | English | Hindi |
|---|---|---|
| Mesha | Mesha (Aries) | मेष |
| Vrishabha | Vrishabha (Taurus) | वृषभ |
| Mithuna | Mithuna (Gemini) | मिथुन |
| Karka | Karka (Cancer) | कर्क |
| Simha | Simha (Leo) | सिंह |
| Kanya | Kanya (Virgo) | कन्या |
| Tula | Tula (Libra) | तुला |
| Vrischika | Vrischika (Scorpio) | वृश्चिक |
| Dhanu | Dhanu (Sagittarius) | धनु |
| Makara | Makara (Capricorn) | मकर |
| Kumbha | Kumbha (Aquarius) | कुंभ |
| Meena | Meena (Pisces) | मीन |

## Grahas

| Engine key | English | Abbr. | Hindi | Hindi abbr. |
|---|---|---|---|---|
| sun | Sun (Surya) | Su | सूर्य | सू |
| moon | Moon (Chandra) | Mo | चंद्र | चं |
| mars | Mars (Mangal) | Ma | मंगल | मं |
| mercury | Mercury (Budha) | Me | बुध | बु |
| jupiter | Jupiter (Guru) | Ju | गुरु (बृहस्पति) | गु |
| venus | Venus (Shukra) | Ve | शुक्र | शु |
| saturn | Saturn (Shani) | Sa | शनि | श |
| rahu_mean | Rahu (mean node) | Ra | राहु (मध्यम पात) | रा |
| ketu_mean | Ketu (opposite mean Rahu) | Ke | केतु (मध्यम राहु के ठीक सामने) | के |

## Nakshatras

| Engine | Hindi |
|---|---|
| Ashwini | अश्विनी |
| Bharani | भरणी |
| Krittika | कृत्तिका |
| Rohini | रोहिणी |
| Mrigashira | मृगशिरा |
| Ardra | आर्द्रा |
| Punarvasu | पुनर्वसु |
| Pushya | पुष्य |
| Ashlesha | आश्लेषा |
| Magha | मघा |
| Purva Phalguni | पूर्वा फाल्गुनी |
| Uttara Phalguni | उत्तरा फाल्गुनी |
| Hasta | हस्त |
| Chitra | चित्रा |
| Swati | स्वाति |
| Vishakha | विशाखा |
| Anuradha | अनुराधा |
| Jyeshtha | ज्येष्ठा |
| Mula | मूल |
| Purva Ashadha | पूर्वाषाढ़ा |
| Uttara Ashadha | उत्तराषाढ़ा |
| Shravana | श्रवण |
| Dhanishta | धनिष्ठा |
| Shatabhisha | शतभिषा |
| Purva Bhadrapada | पूर्वा भाद्रपद |
| Uttara Bhadrapada | उत्तरा भाद्रपद |
| Revati | रेवती |

## Months

| English | Hindi |
|---|---|
| January | जनवरी |
| February | फ़रवरी |
| March | मार्च |
| April | अप्रैल |
| May | मई |
| June | जून |
| July | जुलाई |
| August | अगस्त |
| September | सितंबर |
| October | अक्टूबर |
| November | नवंबर |
| December | दिसंबर |

## Places (prototype fixture)

| Id | English | Hindi |
|---|---|---|
| in-new-delhi | New Delhi, Delhi (National Capital Territory), India | नई दिल्ली, दिल्ली (राष्ट्रीय राजधानी क्षेत्र), भारत |
| in-mumbai | Mumbai, Maharashtra, India | मुंबई, महाराष्ट्र, भारत |
| in-kolkata | Kolkata, West Bengal, India | कोलकाता, पश्चिम बंगाल, भारत |
| in-chennai | Chennai, Tamil Nadu, India | चेन्नई, तमिलनाडु, भारत |
| in-bengaluru | Bengaluru, Karnataka, India | बेंगलुरु, कर्नाटक, भारत |
| in-hyderabad | Hyderabad, Telangana, India | हैदराबाद, तेलंगाना, भारत |
| in-jaipur | Jaipur, Rajasthan, India | जयपुर, राजस्थान, भारत |
| in-lucknow | Lucknow, Uttar Pradesh, India | लखनऊ, उत्तर प्रदेश, भारत |
| in-varanasi | Varanasi, Uttar Pradesh, India | वाराणसी, उत्तर प्रदेश, भारत |
| in-guwahati | Guwahati, Assam, India | गुवाहाटी, असम, भारत |
| gb-london | London, England, United Kingdom | लंदन, इंग्लैंड, यूनाइटेड किंगडम |
| no-tromso | Tromsø, Troms, Norway | ट्रॉम्सो, ट्रोम्स, नॉर्वे |

## Fixed engine sentences

Shown in Hindi only when the engine sends exactly this English text.

| Key | English | Hindi |
|---|---|---|
| ayanamsa_definition | Lahiri (Chitrapaksha), Swiss Ephemeris SE_SIDM_LAHIRI (mode 1), IAE 1985 definition, true ayanamsha, Swiss default precession; no SIDBIT options | लाहिड़ी (चित्रापक्ष), Swiss Ephemeris SE_SIDM_LAHIRI (मोड 1), IAE 1985 की परिभाषा, स्पष्ट अयनांश, Swiss का डिफ़ॉल्ट अयन-चलन मॉडल; कोई SIDBIT विकल्प नहीं |
| claim_boundary | Swiss-on-Swiss integration conformance only; not independent astronomical validation, mathematical verification or historical clock verification | केवल Swiss-पर-Swiss एकीकरण अनुरूपता जाँच; यह स्वतंत्र खगोलीय सत्यापन, गणितीय सत्यापन या ऐतिहासिक घड़ी सत्यापन नहीं है |
| ut1_assumption | civil UTC is treated as UT1 (an assumption, not a measured UT1 correction) | नागरिक UTC को UT1 माना गया है (यह एक धारणा है, मापा गया UT1 संशोधन नहीं) |
| disclosure.FUTURE_CIVIL_TIME_PROJECTED | The birth instant is after the pinned IERS leap-second list expiry (2027-06-28): civil-time rules, leap seconds, UT1-UTC and Delta T are projections, not records. | जन्म का क्षण निर्धारित IERS लीप-सेकंड सूची की समाप्ति (2027-06-28) के बाद का है: नागरिक समय के नियम, लीप सेकंड, UT1-UTC और Delta T अनुमान हैं, दर्ज रिकॉर्ड नहीं। |
| disclosure.HIGH_LATITUDE_TIME_SENSITIVITY | Absolute latitude above 60 deg: ascendant sensitivity to birth-time uncertainty can be greater for some dates and sidereal times, but is not uniformly greater. An accurate recorded birth time is important. Descriptive only; calculation and acceptance are unchanged. | अक्षांश 60° उत्तर या दक्षिण से अधिक: जन्म समय की अनिश्चितता के प्रति लग्न की संवेदनशीलता कुछ दिनांकों और नाक्षत्र समयों पर अधिक हो सकती है, पर हर स्थिति में समान रूप से अधिक नहीं होती। जन्म का सही दर्ज समय महत्वपूर्ण है। यह केवल जानकारी है; गणना और स्वीकृति में कोई बदलाव नहीं। |

## Item dispositions (KUN-I18N-002)

The 18 open items from KUN-I18N-001, each re-checked for terminology, grammar, readability and
consistency across the web interface and all ten PDF pages. Dispositions:

- **CORRECTED**: an objective defect (grammar, fidelity to the English, the same English term
  translated two ways, typography) fixed by the developer and covered by a test in
  `report/phase1/tests/test_hindi_editorial.py`. Still subject to the human gate below.
- **KEPT**: the developer found no objective defect; the choice stays as drafted. A qualified
  reviewer still has to accept it.
- **REVIEWER**: a terminology or style choice a qualified Hindi/Jyotish reviewer must make; the
  existing wording is unchanged until then.
- **OWNER**: an owner decision, outside the Hindi editorial work.

| # | Item | Existing wording | Proposed / applied | Disposition | Rationale and where it appears |
|---|---|---|---|---|---|
| 1 | "Prepared for" | PDF cover label: जातक. Web result heading: "{name} के लिए तैयार" | Recommend जातक on both surfaces (web: "जातक: {name}"); alternative "{name} के लिए तैयार की गई कुंडली" | REVIEWER | The same English label is the only phrase translated two different ways across the two surfaces (pinned as a known exception in the tests). जातक is the classical term for the native; the web fragment "… के लिए तैयार" can read as "ready for …". Web result heading; PDF page 1 (shown only with a name). |
| 2 | Nakshatra Pada | चरण | चरण (unchanged) | KEPT | चरण is the usual Panchanga term for a quarter of a Nakshatra; पद is avoided and test-enforced. Used identically in the web key placements and on PDF pages 2, 3, 7 and 10. |
| 3 | Whole-sign house | पूर्ण-राशि भाव | Unchanged. Reviewer to consider "राशि भाव" / "संपूर्ण राशि भाव" | REVIEWER | Consistent on the web and on pages 2, 3, 4, 5, 7, 8 and 10. Note the collision with पूर्ण भोगांश (absolute longitude, page 3 and 10): पूर्ण means "whole" in one and "absolute" in the other. A reviewer may prefer निरपेक्ष भोगांश or "0° मेष से भोगांश" for absolute longitude. |
| 4 | Mean node | मध्यम पात (mean node), मध्यम राहु (mean Rahu); lunar nodes as both चंद्र पात and चंद्रमा के पात; web nodes value with an extra "(180°)" | Lunar nodes: चंद्र पात everywhere (page 3 graha definition, page 7 notes). Web nodes value: "मध्यम राहु; केतु ठीक सामने", identical to the PDF | CORRECTED (consistency); terms themselves REVIEWER | The mapping mean node → मध्यम पात and mean Rahu → मध्यम राहु is consistent and follows the English. The English "lunar nodes" had two Hindi forms, and the same English "Mean Rahu; Ketu exactly opposite" had two Hindi forms (web vs page 4). मध्यम (mean) pairs with स्पष्ट (true) as in Jyotish usage. |
| 5 | True ayanamsha | "स्पष्ट अयनांश" in the ayanamsa definition sentence | Unchanged | REVIEWER | स्पष्ट (true, corrected) is the counterpart of मध्यम (mean); in Swiss Ephemeris "true ayanamsha" means including nutation. A reviewer should confirm that a Jyotish reader will not read स्पष्ट as "clear/explicit". Web method section; PDF page 4 and 10. |
| 6 | Jupiter | गुरु; long form गुरु (बृहस्पति) | Unchanged | KEPT | गुरु is the common name in Kundali practice, बृहस्पति given once in the long form (page 5 abbreviation list). Same on web and PDF. |
| 7 | Chart abbreviations and Lagna label | सू चं मं बु गु शु श रा के; Lagna label लग्न | Unchanged | REVIEWER | These are the conventional Hindi Kundali abbreviations. श (Saturn) beside शु (Venus) is the traditional pair and is drawn at the report minimum text size on the page 5 and 6 charts, but a reviewer should confirm customers will not confuse them. Abbreviation legends on the web, page 3, page 5 and page 6 list every one. |
| 8 | Date of birth | जन्म दिनांक; plural "स्थानीय दिनांकें" in two web strings | "स्थानीय दिनांक" (masculine plural) in the date help text and the limits list | CORRECTED (grammar); term itself KEPT | दिनांक is masculine in standard Hindi, so its plural is दिनांक (oblique दिनांकों), not the feminine दिनांकें. तिथि stays avoided (a Panchanga lunar day). |
| 9 | Nukta, chandrabindu, anusvara | Mixed "..." and "…" in Hindi status messages | "…" in both Hindi status messages | CORRECTED (typography); spelling KEPT | Whole-catalog audit: no word-final anusvara where chandrabindu is required (हैं, नहीं, यहाँ, स्थितियाँ are correct), nukta used consistently for ज़/फ़ in loanwords (नज़र, अंग्रेज़ी, फ़ाइल, तेज़ी, साफ़) and not for क़/ख़/ग़ (तरीका), as the Kendriya Hindi Nideshalaya standard allows. Reviewer to confirm the policy. |
| 10 | Place transliterations | ट्रॉम्सो, ट्रोम्स, यूनाइटेड किंगडम, बेंगलुरु | Unchanged | REVIEWER | Usual Hindi press spellings; Tromsø is pronounced closer to "ट्रुम्से" locally. Test-coverage places only. Web place list; PDF pages 1 and 4. |
| 11 | Latin script kept | Proper names, codes, `km`, `UTC`, status code | Unchanged | KEPT | Engineering convention; the stray-Latin tests allow only the listed names and codes. A reviewer should confirm `km` and `UTC` are acceptable to customers. |
| 12 | International digits | 0-9 | Unchanged | KEPT | Engine values must be shown exactly as calculated; the tests compare every number between the English and Hindi PDFs. Devanagari numerals would need a separate owner decision. |
| 13 | English "Hindi edition" | English page 10 lists "Hindi edition" as not included | Separate proposal: `docs/i18n/KUN-I18N-002-ENGLISH-PAGE10-PROPOSAL.md` | OWNER | Changing the English text changes every pinned English PDF hash. Not changed here. |
| 14 | Hindi reading-guide sign note | "राशियों की ये क्रम संख्याएँ ही दोनों कुंडलियों में हर भाव पर लिखी गई हैं।" | Unchanged | REVIEWER | The English note about Western sign names does not apply to a Hindi reader, so the Hindi note explains the Rashi numbers instead. This is an intentional difference of content; a reviewer should accept it. Page 3. |
| 15 | "owner-approved chart schema 0.3.0" | स्वीकृत चार्ट स्कीमा 0.3.0 | Unchanged. Suggest either "परियोजना स्वामी द्वारा अनुमोदित चार्ट स्कीमा 0.3.0" or dropping "approved" in both languages | REVIEWER and OWNER | The Hindi drops "owner", so स्वीकृत alone reads as generally approved. The English sentence itself is customer-facing internal process wording, so the owner may prefer to drop it in both languages. Web D9 footnote only. |
| 16 | Native date and time pickers | Follow the browser locale | Unchanged | KEPT | Browser behaviour, not page text. Typed values and validation messages are in the page language. |
| 17 | Server messages without a catalog entry | "कोई कुंडली नहीं बनाई गई।" plus the code | Unchanged | KEPT | Every code the server sends today has a catalog entry; the fallback only covers future codes and never shows English. |
| 18 | Register and tone | Formal आप forms throughout (करें, चुनें, देखें); no तुम forms | Corrections listed under "Additional corrections" | CORRECTED (listed defects); overall tone REVIEWER | Whole-catalog read-through. Remaining style suggestions for the reviewer: houses key (page 9) "एक ही भाव संख्या में दोनों कुंडलियों में" could read "एक ही भाव संख्या पर …"; the web D9 legend has a comma between subject and predicate; "80 अक्षर" in the name help counts consonants and independent vowels, not syllables, so a reviewer may prefer "80 वर्ण" with a note. |

### Additional corrections found during the review

| # | Key | Existing wording | Corrected wording | Defect |
|---|---|---|---|---|
| A1 | `engine_text.disclosure.HIGH_LATITUDE_TIME_SENSITIVITY` | अक्षांश 60° से अधिक: | अक्षांश 60° उत्तर या दक्षिण से अधिक: | Fidelity: the English says *absolute* latitude, so the sentence applies in both hemispheres; matches the web limit "66° उत्तर या दक्षिण". |
| A2 | `engine_text.ut1_assumption` | (यह एक मान्यता है, …) | (यह एक धारणा है, …) | Wrong sense: मान्यता means recognition, belief or accreditation and can read as "approved"; धारणा is "assumption". |
| A3 | `chart.d9_note` (page 6) | … और इस कुंडली का हर ग्रह बनाने से पहले इंजन की D9 भाव सूची से जाँचा गया। | … और कुंडली बनाने से पहले इसके हर ग्रह को इंजन की D9 भाव सूची से जाँचा गया। | Ambiguity: "हर ग्रह बनाने से पहले" reads as "before making each graha". |
| A4 | `ui.download.preparing`, `ui.status.pdf_creating` | ... | … | Typography: the other Hindi status messages use the ellipsis character. |
| A5 | `report_locale.Translator.engine_text` (internal exception, never shown) | "Engine text has no reviewed Hindi form" | "Engine text has no catalogued Hindi form" | The Hindi text is not reviewed; internal wording must not imply that it is. |

## Human editorial gate (open)

**PENDING: independent human Hindi / Jyotish editorial review. Not performed. Not owner-approved.**
Before any customer release, a qualified reviewer must accept or replace every item above,
including the CORRECTED ones, and in particular decide items 1, 3, 4, 5, 7, 10, 14, 15 and 18.
Nothing in this register, in the catalogs or in the tests claims that a human linguistic review
has taken place.
