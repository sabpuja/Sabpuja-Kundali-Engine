# KUN-I18N-003: Independent Hindi / Jyotish editorial review packet

**For:** a qualified, independent Hindi language editor and a qualified Jyotish terminology reviewer
(they can be the same person when the person holds both qualifications).
**Prepared by:** Claude (developer). **Nothing in this packet is a review.** The developer's notes
are proposals for the reviewer to accept, revise or reject. No human review has taken place yet.

| | |
|---|---|
| Source under review | commit `c9f147bad9b50c5eb85585b0e3e952e49fb5ac40`, tree `85e38f1dbafc0eef4dc24f87c5910b118261fb73` (PR #60, KUN-I18N-002) |
| Web catalog | `prototype/kundali_prototype/static/i18n.json` SHA-256 `5cf9e5fcb4234dd971fa1c512c6c6da6567918d38a0c7e61c9e6d8cd496b17f1` |
| PDF catalog | `report/phase1/report_i18n.json` SHA-256 `324b19ec2269b578f026b4b1dbebbd73d9b3b2f3d4879e2cca9dedb325ac0145` |
| Hindi sample PDF (10 pages, synthetic) | `assets/sample-hi-anonymous.pdf` SHA-256 `7590ea3a5b094e1f92e27ea975af262219a3bef4cd49219e48882944282588c7` |
| English sample PDF (10 pages, synthetic) | `assets/sample-en-anonymous.pdf` SHA-256 `37b77f9a4013d5fb6ccfa379ac71c2bcd186f28428f1b010ff52ee63426010ea` |

Every birth detail, name and chart in this packet is synthetic (fixture `s11-afternoon`: New Delhi,
5 September 2038, 15:20:10; name "क्षत्रिय प्रियंका सिद्धार्थ" where a named sample is shown). No
customer data is included.

## How to review

1. Read each item below. The exact places each term appears are in `LOCATIONS.md`
   (generated from the catalogs and from Hindi PDFs of all 13 synthetic scenarios).
2. Look at the term in context: `assets/en-hi-page-NN.png` (English | Hindi, each of the ten pages),
   `assets/sample-*.pdf`, and the interface screenshots `assets/screens/` (280, 375, 768 and
   1440 px; English, Hindi form, Hindi result).
3. Record a decision for every item in `DECISION-SHEET.md` (or the CSV copy): **ACCEPT**,
   **REVISE** (write the exact replacement Hindi) or **REJECT** (say why), and sign it.
4. Return the signed sheet to the owner. The developer then applies REVISE decisions in a
   separate exact-SHA commit, and `EDITORIAL-ACCEPTANCE-REGISTER.md` records who decided what,
   when, and against which catalog revision.

"Language" decisions are about Hindi grammar, spelling, readability and tone. "Jyotish" decisions
are about whether a term is the correct, recognised astrological term. Items marked **[L]**, **[J]**
or **[L+J]** say which review layer has to sign.

Priority items (owner and QA): **1, 3, 4, 5, 7, 10, 14, 15, 18**.

---

## Item 1 — "Prepared for" (cover / result heading) [L+J] — PRIORITY

| | |
|---|---|
| English source | PDF `cover.prepared_for`: "Prepared for". Web `ui.result.for_before` + name: "Prepared for {name}" |
| Current Hindi | PDF cover (p. 1, above the name): **जातक**. Web result heading: **"{name} के लिए तैयार"** |
| Alternatives | (a) जातक on both surfaces, web "जातक: {name}"; (b) "{name} के लिए तैयार की गई कुंडली" on both; (c) "{name} के लिए" on both; (d) keep both as they are |
| Meaning | जातक is the classical Jyotish word for the native, the person whose chart it is. "Prepared for" is a presentation label, not an astrological term. |
| Risks | The two surfaces translate the same English differently (the only such pair left; pinned by `test_item4_same_english_same_hindi_across_web_and_pdf`). The web fragment "… के लिए तैयार" can read as "ready for …". जातक may feel formal or technical to some customers. |
| Developer recommendation | **REVISE** web to option (a), keep जातक on the PDF. Reviewer chooses. |
| Where | PDF p. 1 (only when a name is given); web result heading. See `LOCATIONS.md` item 1. |

## Item 2 — Nakshatra Pada: चरण [J]

| | |
|---|---|
| English source | "Pada", "Moon Nakshatra and Pada", "Pada {pada} of 4" |
| Current Hindi | **चरण** ("चरण 2", "चरण 2 (4 में से)", "चंद्र नक्षत्र और चरण") |
| Alternatives | पद; पाद |
| Meaning | One quarter (3°20′) of a 13°20′ Nakshatra. |
| Risks | Low. चरण is the usual Panchanga word; पद is avoided and a test prevents "पद " reappearing. |
| Developer recommendation | **ACCEPT** |
| Where | PDF p. 2, 3, 7, 10; web key placements. |

## Item 3 — Whole-sign house: पूर्ण-राशि भाव [J+L] — PRIORITY

| | |
|---|---|
| English source | "whole-sign house(s)", e.g. "North Indian birth chart with whole-sign houses", "Whole-sign houses for D1 and D9: house = Rashi count from the Lagna Rashi." |
| Current Hindi | **पूर्ण-राशि भाव** (e.g. "पूर्ण-राशि भावों वाली उत्तर भारतीय जन्म कुंडली") |
| Alternatives | राशि भाव; संपूर्ण राशि भाव; "भाव = राशि" (descriptive); राशि-आधारित भाव पद्धति |
| Meaning | Each house is exactly one whole Rashi; house 1 is the Lagna's Rashi. This is the house system the engine currently uses; the house convention (SCI-01f) is recorded as PENDING in `docs/DECISIONS.md` on this branch. The review is of the Hindi term only, not the method. |
| Risks | पूर्ण is also used for "absolute" in **पूर्ण भोगांश** (absolute longitude, p. 3, 5, 10), so the same word means "whole" in one term and "absolute" in another. A reviewer may prefer निरपेक्ष भोगांश or "0° मेष से भोगांश" for absolute longitude. |
| Developer recommendation | **ACCEPT** पूर्ण-राशि भाव; **REVISE** absolute longitude to a term the reviewer chooses. |
| Where | PDF p. 2, 3, 4, 7, 8, 10 (whole-sign); p. 3, 5, 10 (absolute); web D1/D9 captions, legends, method section. |

## Item 4 — Mean node: मध्यम पात / मध्यम राहु; lunar nodes: चंद्र पात [J] — PRIORITY

| | |
|---|---|
| English source | "mean node", "Rahu (mean node)", "Mean Rahu; Ketu exactly opposite", "Lunar nodes", "Rahu is the mean lunar node" |
| Current Hindi | मध्यम पात (mean node); मध्यम राहु (mean Rahu); चंद्र पात (lunar nodes); "राहु मध्यम चंद्र पात है"; long names "राहु (मध्यम पात)", "केतु (मध्यम राहु के ठीक सामने)" |
| Alternatives | मध्य पात; माध्य राहु; औसत पात (plain-language); राहु-केतु अक्ष for "nodes" |
| Meaning | Rahu is the Moon's ascending node, calculated as the *mean* (averaged) position rather than the *true* (oscillating) one; Ketu is exactly 180° from it. This convention is owner-approved (SCI-01b, SCI-01c in `docs/DECISIONS.md`); the review is of the Hindi term only. |
| Risks | मध्यम pairs with स्पष्ट (true) as in Jyotish usage, but a lay reader may read मध्यम as "medium". KUN-I18N-002 removed a second form (चंद्रमा के पात) so the term is now uniform. |
| Developer recommendation | **ACCEPT** (Jyotish reviewer to confirm मध्यम as "mean") |
| Where | PDF p. 2, 3, 4, 7, 10; web D1 footnote, method section, chart house descriptions. |

## Item 5 — "true ayanamsha": स्पष्ट अयनांश [J] — PRIORITY

| | |
|---|---|
| English source | Engine sentence: "Lahiri (Chitrapaksha), Swiss Ephemeris SE_SIDM_LAHIRI (mode 1), IAE 1985 definition, true ayanamsha, Swiss default precession; no SIDBIT options" |
| Current Hindi | "… IAE 1985 की परिभाषा, **स्पष्ट अयनांश**, Swiss का डिफ़ॉल्ट अयन-चलन मॉडल; …" |
| Alternatives | सत्य अयनांश; नुटेशन-सहित अयनांश (descriptive); keep "true ayanamsha" in Latin as a technical identifier |
| Meaning | In Swiss Ephemeris "true" ayanamsha includes nutation (the short-period wobble), as opposed to "mean". It is a technical setting, not a different ayanamsa. |
| Risks | स्पष्ट can also mean "clear/explicit". The sentence mixes Hindi with Swiss identifiers, which is intended (it must match the engine text exactly). |
| Developer recommendation | **ACCEPT** (Jyotish reviewer to confirm) |
| Where | Web method section ("राशिचक्र और अयनांश"); PDF p. 10 (methodology, when the engine sends it). |

## Item 6 — Jupiter: गुरु, long form गुरु (बृहस्पति) [J]

| | |
|---|---|
| English source | "Jupiter", "Jupiter (Guru)" |
| Current Hindi | गुरु; long form गुरु (बृहस्पति); abbreviation गु |
| Alternatives | बृहस्पति as the main name |
| Meaning | The graha Jupiter. |
| Risks | Low. गुरु is the common Kundali name; बृहस्पति appears only in the long form. |
| Developer recommendation | **ACCEPT** |
| Where | PDF p. 3, 5, 6, 7, 8 and abbreviation lists; web tables, legends, chart descriptions. |

## Item 7 — Chart abbreviations and the Lagna label [J+L] — PRIORITY

| | |
|---|---|
| English source | Su Mo Ma Me Ju Ve Sa Ra Ke; Lagna label "Asc" |
| Current Hindi | **सू चं मं बु गु शु श रा के**; Lagna label **लग्न** (full word, not an abbreviation) |
| Alternatives | शनि as श़ / शनि in full; ल or लग for Lagna |
| Meaning | Labels drawn inside the North Indian chart houses. |
| Risks | श (Saturn) next to शु (Venus) differs by one vowel sign; at small sizes a reader could confuse them. Every chart page has a legend that lists all nine. |
| Developer recommendation | **ACCEPT** (traditional set); reviewer to check legibility on `assets/en-hi-page-05.png` and `-06.png` |
| Where | PDF p. 3, 5, 6, 7, 8, 9 (and legends); web D1/D9 charts and legends. |

## Item 8 — Date of birth: जन्म दिनांक [L]

| | |
|---|---|
| English source | "Date of birth", "Local date", "Supported: local dates from …" |
| Current Hindi | जन्म दिनांक; स्थानीय दिनांक; plural "स्थानीय दिनांक" (masculine, corrected in KUN-I18N-002 from दिनांकें) |
| Alternatives | जन्म तिथि (avoided: तिथि is the lunar day of the Panchanga); जन्म की तारीख |
| Meaning | The civil calendar date of birth. |
| Risks | दिनांक is masculine in standard Hindi; colloquial usage sometimes treats it as feminine. |
| Developer recommendation | **ACCEPT** (language reviewer to confirm gender) |
| Where | PDF p. 1, 4; web form, limits, refusal messages, confirmed details. |

## Item 9 — Nukta, chandrabindu and anusvara spelling policy [L]

| | |
|---|---|
| English source | (spelling convention) |
| Current Hindi | Anusvara for nasal clusters (कुंडली, चंद्र, कुंभ); chandrabindu where no vowel sign is above the headline (यहाँ, स्थितियाँ); nukta for ज़/फ़ in loanwords (नज़र, अंग्रेज़ी, फ़ाइल, तेज़ी, साफ़), none for क़/ख़/ग़ (तरीका) |
| Alternatives | No nukta anywhere; Sanskrit half-nasal spellings (कुण्डली, चन्द्र) |
| Meaning | Kendriya Hindi Nideshalaya standard spelling. |
| Risks | Low. A test prevents the half-nasal spellings mixing in. |
| Developer recommendation | **ACCEPT** |
| Where | Whole catalog. |

## Item 10 — Place transliterations [L] — PRIORITY

| | |
|---|---|
| English source | Tromsø, Troms, Norway; London, England, United Kingdom (and the 10 Indian cities) |
| Current Hindi | ट्रॉम्सो, ट्रोम्स, नॉर्वे; लंदन, इंग्लैंड, यूनाइटेड किंगडम |
| Alternatives | ट्रुम्से / ट्रॉम्से (closer to local pronunciation); ब्रिटेन for United Kingdom |
| Meaning | Place names. |
| Risks | **Customer exposure is limited:** London and Tromsø are test-coverage entries; the preview image removes all places outside India, and none of the 13 PDF fixtures uses them. The 10 Indian names (नई दिल्ली, मुंबई, …) are customer-facing and should be checked too. |
| Developer recommendation | **ACCEPT** the Indian names; **REVISE** Tromsø at the reviewer's discretion |
| Where | Web place list (prototype); PDF p. 1 and 4 when chosen. |

## Item 11 — Latin script kept [L]

| | |
|---|---|
| English source | Sabpuja, Swiss Ephemeris, IANA, tzdata, GeoNames, AGPL-3.0, UTC, D1, D9, SHA-256, `km`, the status code `UNVERIFIED_GOLDEN_CHARTS` |
| Current Hindi | Kept in Latin |
| Alternatives | Devanagari for UTC (यूटीसी), km (कि.मी.) |
| Meaning | Proper names, identifiers and codes. |
| Risks | Readers may find `km` and `UTC` foreign; transliterating identifiers would break exact matching. |
| Developer recommendation | **ACCEPT** (reviewer may revise `km` only) |
| Where | Whole catalog; tests allow only the listed Latin words. |

## Item 12 — International digits [L]

| | |
|---|---|
| Current Hindi | 0–9 for every number |
| Alternatives | Devanagari numerals ०–९ |
| Meaning | Engine values are shown exactly as calculated and compared between languages by tests. |
| Developer recommendation | **ACCEPT** (Devanagari numerals would be a separate owner decision) |

## Item 13 — English page 10 "Hindi edition" [Owner]

Not a Hindi editorial item. See `CHANGE-A-ENGLISH-PAGE10.md`. The Hindi line
"अंग्रेज़ी पाठ (अलग संस्करण में उपलब्ध)" (PDF p. 10) is in scope for the language reviewer: **ACCEPT / REVISE**.

## Item 14 — Hindi reading-guide sign note [L] — PRIORITY

| | |
|---|---|
| English source | `guide.sign_note`: "English sign names are conventional equivalents for the sidereal Rashis." |
| Current Hindi | "राशियों की ये क्रम संख्याएँ ही दोनों कुंडलियों में हर भाव पर लिखी गई हैं।" ("These Rashi numbers are the ones written in every house of both charts.") |
| Alternatives | A literal translation of the English note; or both sentences |
| Meaning | The English note explains why Western sign names appear. The Hindi page shows no Western names, so it explains the numbers instead. **This is an intended difference of content, not a translation.** |
| Risks | A reviewer comparing languages may expect a literal translation. |
| Developer recommendation | **ACCEPT** |
| Where | PDF p. 3 (under the Rashi list). |

## Item 15 — "owner-approved chart schema 0.3.0" [L + Owner] — PRIORITY

| | |
|---|---|
| English source | Web D9 footnote: "… The D9 house fields use the owner-approved chart schema 0.3.0." |
| Current Hindi | "… D9 भाव के फ़ील्ड **स्वीकृत** चार्ट स्कीमा 0.3.0 के अनुसार हैं।" |
| Alternatives | Change B (owner decision): English "… use chart schema 0.3.0.", Hindi "… चार्ट स्कीमा 0.3.0 के अनुसार हैं।"; or "परियोजना स्वामी द्वारा अनुमोदित" |
| Meaning | Internal engineering provenance in customer text. |
| Risks | स्वीकृत alone reads as generally "approved"; the English exposes internal process wording to customers. |
| Developer recommendation | **REVISE** per Change B, if the owner approves (`CHANGE-B-SCHEMA-WORDING.md`). Web only; no PDF effect. |

## Item 16 — Native date and time pickers [L]

Browser controls follow the browser's own language, not the page language. Typed values,
labels, help and validation are in the page language. **ACCEPT** (no wording to review).

## Item 17 — Fallback refusal message [L]

| | |
|---|---|
| English source | "No chart was produced." |
| Current Hindi | "कोई कुंडली नहीं बनाई गई।" (plus the code) |
| Developer recommendation | **ACCEPT** |
| Where | Web error panel. |

## Item 18 — Register and tone of all text [L] — PRIORITY

Formal आप forms throughout (करें, चुनें, देखें); no तुम forms. KUN-I18N-002 corrected the objective
defects it found. Style points left for the reviewer:

| Key | Current | Suggestion |
|---|---|---|
| `houses.key` (PDF p. 9) | "एक ही भाव संख्या में दोनों कुंडलियों में प्रायः …" | "एक ही भाव संख्या पर दोनों कुंडलियों में प्रायः …" (avoid the double में) |
| `ui.d9.legend` | "D9 भाव, D9 लग्न (भाव 1, सबसे ऊपर) से गिने गए …" | remove the comma between subject and predicate, or reorder |
| `ui.name.help`, `ui.msg.DISPLAY_NAME_TOO_LONG` | "अधिकतम 80 अक्षर: अक्षर, …" | the limit counts consonants and independent vowels, not vowel signs or virama, so "80 वर्ण" with a short note may be clearer; also the repeated अक्षर |
| `ui.name.help` | "ऐपॉस्ट्रॉफ़ी" | spelling of "apostrophe" (एपॉस्ट्रॉफ़ी?) |
| whole catalog | — | read for naturalness: nothing should read as machine translation |

Developer recommendation: **REVISE** at the reviewer's discretion; the reviewer signs the overall tone.

---

## KUN-I18N-002 developer corrections (also to be accepted)

A1 high-latitude note "60° उत्तर या दक्षिण से अधिक"; A2 धारणा for "assumption"; A3 page 6 word order;
A4 ellipsis; दिनांक plural; चंद्र पात. Before/after images: `assets/hi-before-after-page-03/06/07*.png`.
These are listed on the decision sheet as rows C1–C6.
