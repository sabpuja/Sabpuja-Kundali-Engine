# Panchanga report terms (English / Hindi), KUN-PAN-RPT-001

**Status: developer draft. Pending independent QA and human Hindi editorial review. Not owner-approved.**

Source of truth for the wording: `report/phase1/report_panchanga_i18n.json` (the three extended-edition
pages and the extended methodology lists). The approved ten-page catalog `report/phase1/report_i18n.json`
and the shared terminology register `prototype/kundali_prototype/static/i18n.json` are **not changed**.
Nakshatra names and the Pada term come from that existing register unchanged.

## What is displayed, and what is not

| Element | Shown as | Name shown? | Decision |
|---|---|---|---|
| Tithi | number 1 to 30 ("11 of 30") | **No** Tithi name | D16-M1-INDEX |
| Paksha | Shukla Paksha / Krishna Paksha, with Paksha day 1 to 15 | Paksha name only (from the machine id `shukla` / `krishna`) | D16-M1-INDEX (ids), this table (display form) |
| Karana | number 1 to 60 ("21 of 60"), first or second half of its Tithi | **No** Karana name | D07-A |
| Yoga | number 1 to 27 ("25 of 27") | **No** Yoga name | D16-M1-INDEX |
| Nakshatra, Pada | engine Nakshatra id via the existing register; Pada number | Yes, as in the ten-page report | existing register |

The tests (`test_panchanga_report.py`) fail if any Tithi, Karana or Yoga name (English or Hindi,
spellings from SOURCE-REGISTER.md section 2 and the IMD candidates) appears in the catalog or on the
Panchanga pages. Adopting names needs a primary-source name table and a separate owner decision
(the open remainder of PAN-D07 / PAN-D16).

KUN-PAN-M2-NAMES-001 adds the source-checked names in a separate catalog,
`report/phase1/panchanga_names.json`, shown only in an internal QA preview
(`names='qa_preview'`). This catalog and the default 13-page output are unchanged. See
`PANCHANGA-NAMES-REVIEW.md` and `PANCHANGA-NAMES-CROSSWALK.md`.

## Terms and the documented sources checked (accessed 2026-11-05)

| Concept | English | Hindi | Checked against |
|---|---|---|---|
| Panchanga ("five limbs") | Panchanga | पंचांग | Wikipedia "Panchangam" (Sanskrit पञ्चाङ्गम्; five limbs Tithi, Nakshatra, Yoga, Karana, Vara). पंचांग is the anusvara spelling already used in the register's conventions and in `method.exc1` of the approved catalog |
| Lunar day | Tithi | तिथि | Wikipedia "Tithi": "the time taken for the longitudinal angle between the Sun and the Moon to increase by 12°"; 30 per lunar month. Register note: तिथि is reserved for the Panchanga lunar day |
| Bright fortnight | Shukla Paksha (bright, Moon waxing) | शुक्ल पक्ष (उजला, चंद्रमा बढ़ता हुआ) | Wikipedia "Paksha": "Shukla Paksha refers to the bright lunar fortnight ... corresponding to the waxing moon"; Hindi Wikipedia "पक्ष": "शुक्ल पक्ष तथा कृष्ण पक्ष" |
| Dark fortnight | Krishna Paksha (dark, Moon waning) | कृष्ण पक्ष (अँधेरा, चंद्रमा घटता हुआ) | same pages: "Krishna Paksha (dark side) ... corresponds to the period of the waning moon" |
| Half-Tithi | Karana | करण | Wikipedia "Karana (pancanga)": "a karaṇa is a half of a tithi ... increased by 6 degrees"; 60 in a lunar month |
| Sun + Moon period | Yoga | योग | Wikipedia "Nityayoga": "the sum of the nirayana longitudes of the Sun and the Moon increases by ... 13 degrees 20 minutes"; 27 Yogas. The report says it "is not a planetary Yoga" (ग्रह-योग नहीं) |
| Lunar mansion, quarter | Nakshatra, Pada | नक्षत्र, चरण | Wikipedia "Nakshatra": 27 sectors of 13°20′, each in four padas of 3°20′; Hindi चरण from the existing register (review item there) |
| Sunrise rule (limitation) | "the Tithi ... in force at local sunrise" | "स्थानीय सूर्योदय के समय" | Wikipedia "Tithi": "The tithi in place at sunrise is considered the 'tithi of the day'" |
| First / second half | 1st / 2nd half of Tithi n | तिथि n का पूर्वार्ध / उत्तरार्ध | standard Hindi words for first and second half |
| Clockwise | clockwise | दक्षिणावर्त | standard Hindi |

Wikipedia is a secondary source (SOURCE-REGISTER.md section 2 lists it as "cited for definitions
only"). It is used here for definitions and common spellings, never for an expected value or a name
table. No proprietary Panchang text or layout was used.

## Review items for the human Hindi editor

1. उजला / अँधेरा पक्ष as the plain-language glosses of शुक्ल / कृष्ण.
2. पक्ष का दिन for Paksha day.
3. कोणीय अंतर E for the Moon–Sun elongation, and जोड़ S for the sum.
4. अर्ध-तिथि क्रमांक, नाम रहित for the Karana card subtitle.
5. पूर्वार्ध / उत्तरार्ध in the transition table.
6. "चंद्रमा की चार प्रमुख कलाएँ" for E = 0°, 90°, 180°, 270°, chosen to avoid Tithi names (अमावस्या, पूर्णिमा, अष्टमी).
7. घं as the axis abbreviation for hours.
8. भाग for an angular "step" (12° of E, 6°, 13°20′ of S). चरण is kept only for Pada, so the
   same page never uses one word for two meanings.
9. "{h} घं {m} मि" for the span lengths on the timeline, and अवधि for "length".
10. लगभग ("about") to mark transition times rounded to the nearest minute, and "निकटतम मिनट तक
    पूर्णांकित" in the page intro.

## Sunrise and Vara (KUN-PAN-RPT-002, developer draft)

The opt-in 14-page edition adds one page, "Sunrise and Vara" / "सूर्योदय और वार". Its 77 strings are in
`report/phase1/report_vara_i18n.json` (status DEVELOPER DRAFT). They have not had human Hindi review and are
not for customers.

| Concept | English | Hindi | Source checked |
|---|---|---|---|
| Panchanga weekday | Vara, e.g. "Somavara (Monday)" | वार, e.g. सोमवार | the ordinary Hindi weekday names; the sunrise-to-sunrise day is the accepted rule PAN-D05. No external source was newly checked for this row. |
| Calendar weekday | Calendar weekday | कैलेंडर का दिन | plain description, not a technical term |
| Sunrise, sunset | Sunrise, Sunset, Next sunrise | सूर्योदय, सूर्यास्त, अगला सूर्योदय | standard Hindi |
| Sunrise rule | Sunrise rule (SUN-D-IMD-47) | सूर्योदय नियम | the IMD upper-limb definition, as adopted for development in PAN-D17 |
| Refraction, semidiameter | refraction, semidiameter | अपवर्तन, अर्धव्यास | standard Hindi astronomy terms |
| Polar day / night | polar day, polar night | ध्रुवीय दिन, ध्रुवीय रात | standard Hindi |
| "about" a rounded time | about {time} | लगभग {time} | as in item 10 above |

A Hindi Vara name repeats the Hindi calendar weekday for most births. The page keeps both cards because they
can differ: a birth before sunrise keeps the previous Vara. The English name gives the Sanskrit form with the
weekday in brackets for the same reason.

Review items for the human Hindi editor (Sunrise and Vara page):

11. कैलेंडर का दिन for "calendar weekday", next to वार.
12. "सूर्योदय रेखा" for the sunrise line (the Sun's centre 47′ below the horizon) in the polar notes.
13. "सावधानी सीमा" for the ±5-minute caution band. It is a review prompt, not an accuracy.
14. "जन्म सूर्योदय के निकट: कृपया जन्म समय जाँचें" as the warning heading.
15. "{hours} घंटे {minutes} मिनट बाद / पहले" on the Birth and sunrise card.

