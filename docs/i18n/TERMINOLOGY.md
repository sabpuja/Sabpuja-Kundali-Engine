# KUN-I18N-001 terminology register (English / Hindi)

**Status: developer draft. Pending independent human Hindi editorial review. Not owner-approved.**
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
| ut1_assumption | civil UTC is treated as UT1 (an assumption, not a measured UT1 correction) | नागरिक UTC को UT1 माना गया है (यह एक मान्यता है, मापा गया UT1 संशोधन नहीं) |
| disclosure.FUTURE_CIVIL_TIME_PROJECTED | The birth instant is after the pinned IERS leap-second list expiry (2027-06-28): civil-time rules, leap seconds, UT1-UTC and Delta T are projections, not records. | जन्म का क्षण निर्धारित IERS लीप-सेकंड सूची की समाप्ति (2027-06-28) के बाद का है: नागरिक समय के नियम, लीप सेकंड, UT1-UTC और Delta T अनुमान हैं, दर्ज रिकॉर्ड नहीं। |
| disclosure.HIGH_LATITUDE_TIME_SENSITIVITY | Absolute latitude above 60 deg: ascendant sensitivity to birth-time uncertainty can be greater for some dates and sidereal times, but is not uniformly greater. An accurate recorded birth time is important. Descriptive only; calculation and acceptance are unchanged. | अक्षांश 60° से अधिक: जन्म समय की अनिश्चितता के प्रति लग्न की संवेदनशीलता कुछ दिनांकों और नाक्षत्र समयों पर अधिक हो सकती है, पर हर स्थिति में समान रूप से अधिक नहीं होती। जन्म का सही दर्ज समय महत्वपूर्ण है। यह केवल जानकारी है; गणना और स्वीकृति में कोई बदलाव नहीं। |

## Open items for the independent Hindi language review

These are developer choices, not reviewed decisions. Each needs a native Hindi editor's
acceptance or a replacement before customer use.

1. **जातक** for the cover's "Prepared for" (alternative: "… के लिए तैयार").
2. **चरण** for Nakshatra Pada (alternative: पद).
3. **पूर्ण-राशि भाव** for whole-sign house.
4. **मध्यम पात** / **मध्यम राहु** for the mean node.
5. **स्पष्ट अयनांश** wording in the ayanamsa definition sentence.
6. **गुरु** as the short name with **गुरु (बृहस्पति)** as the long form.
7. Chart abbreviations **सू चं मं बु गु शु श रा के**, especially **श** (Saturn) beside **शु** (Venus), and the full word **लग्न** as the Ascendant label.
8. **जन्म दिनांक** instead of **तिथि** for the calendar date of birth.
9. Nukta (फ़, ज़, ड़) and chandrabindu/anusvara use throughout, against the Kendriya Hindi Nideshalaya standard.
10. Place transliterations, in particular **ट्रॉम्सो** and **ट्रोम्स** (Tromsø, Troms) and **यूनाइटेड किंगडम**.
11. Latin script kept for proper names, data sets, licences, codes, hashes and the engine status code (`UNVERIFIED_GOLDEN_CHARTS`).
12. International digits rather than Devanagari numerals.
13. The methodology "not included" line: the Hindi report lists "अंग्रेज़ी पाठ (अलग संस्करण में उपलब्ध)" while the English report still says "Hindi edition", because changing the English text would break the PR #58 byte identity. **Owner decision needed** on whether the English wording should change in a later, separately approved task.
14. The Hindi reading guide replaces the English note on Western sign names with a note that the Rashi numbers match the chart.
15. Interface phrase **स्वीकृत चार्ट स्कीमा 0.3.0** (the English says "owner-approved chart schema").
16. Native date and time pickers follow the browser's own locale and are not controlled by the page language.
17. The server's English refusal messages for codes without a catalog entry are not shown in Hindi; the Hindi page shows the generic "कोई कुंडली नहीं बनाई गई।" with the code.
18. Register and tone of all interface and report sentences (formal आप forms, सीमित पूर्वावलोकन, प्रोटोटाइप), and that nothing reads as machine translation.
