# KUN-B6D-REVIEW-001: B-6 birth-time sensitivity wording, editorial review packet

**Status: DEVELOPER RECOMMENDATION. NOT REVIEWED. NOT APPROVED.**
Prepared by Claude (developer). Nothing in this packet is a human editorial review, a Jyotish review or an owner copy approval, and nothing here may be shown to customers. Every recommendation below is a proposal for qualified human reviewers to accept, revise or reject on [`SIGNOFF-SHEET.md`](SIGNOFF-SHEET.md).

| | |
|---|---|
| Canonical base | `main` at `de721d665ed80ed58291f59962677065a73f0b26` (tree `80597a0db7a49f1ebbd6f6faa713b7ea1627af45`), the PR #64 merge |
| Policy | **SCI-06**, OWNER APPROVED / CANONICAL per the [PR #64 post-merge adoption receipt](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/64#issuecomment-6598563378). The receipt says: "No customer-facing English/Hindi wording has been approved". This packet does not change that |
| Existing wording reviewed | Draft PR #63 head `1b70927bed1e040f55441b5b710600ae6fe11216`, `docs/science/kun-sci-pol-001/B6-NEAR-BOUNDARY-DISCLOSURE.md` §5 (git blob `1bfc31fcdc010272397daad244e7033e9fd1a89b`, SHA-256 `fa537ed1c8e8e17059a5632449150a1ad2602bd88c73a599d3f5baa0e80929f5`). PR #63 is unmerged, so the text is quoted below verbatim |
| Terminology source | The existing developer-draft catalogs on draft PR #61 head `fee3967d62d0229e31de98682da9ada5d9190e93`: web `prototype/kundali_prototype/static/i18n.json` SHA-256 `5cf9e5fcb4234dd971fa1c512c6c6da6567918d38a0c7e61c9e6d8cd496b17f1`, PDF `report/phase1/report_i18n.json` SHA-256 `324b19ec2269b578f026b4b1dbebbd73d9b3b2f3d4879e2cca9dedb325ac0145`. These are the same catalog bytes as the KUN-I18N-003 review packet. They are themselves unreviewed, so where this packet follows them it inherits their pending review |
| Recommended strings | [`b6-wording-draft.json`](b6-wording-draft.json) (machine-readable; this packet shows each string verbatim, checked by [`check_packet.py`](check_packet.py)) |
| Placement | [`DESIGN-INTEGRATION.md`](DESIGN-INTEGRATION.md) |

All chart data in this packet is synthetic. Example values marked **constructed** were chosen by hand to show the wording and are not engine output. The single **reference** example (GOLD-E01) is the synthetic boundary chart from the KUN-SCI-GOLD-001 matrix, with values as recorded in PR #63 §2.

---

## 1. What SCI-06 requires, and what the wording must do

SCI-06 (verbatim scope): "Keep calculated classifications. Show a brief birth-time sensitivity note when the Lagna Rashi, Lagna Navamsa, Moon Rashi, Moon Navamsa, Moon Nakshatra or Moon Pada would change within **±2 minutes** of the entered time, plus a near-exact-boundary note. Option 2's expanded explanation is an optional premium appendix. The window is a disclosure policy, not an assumption that the recorded time is wrong."

Note on coverage: the owner task lists Lagna Rashi, Lagna Navamsa, Moon Rashi, Moon Nakshatra and Pada, exact boundaries and the appendix. SCI-06 also covers the **Moon Navamsa**, so this packet adds a Moon Navamsa (D9 Rashi) message (§3.6). The reviewer or owner can remove it, but removing it would leave an SCI-06 item without a message.

Every message must:

1. state the result **for the time entered** first, and only then the alternative;
2. describe the alternative as depending on the **actual birth time**, which is different from the entered time, never as a calculation that might be wrong;
3. state the direction (earlier or later) and an approximate size, never a false-precision number of seconds;
4. make no prediction, interpretation, remedy or fear-based statement, and no claim of certified or independently validated accuracy;
5. use the same term for the same thing as the rest of the report (§4).

---

## 2. Existing wording (PR #63 §5, verbatim) and the defects found

| ID | Case | Existing English draft | Existing Hindi draft |
|---|---|---|---|
| X1 | Lagna Rashi | Birth-time note: your Lagna is about {m} minutes from changing from {A} to {B}. If your birth time could differ by that much, the Lagna and every house in the D1 chart could differ. | जन्म-समय सूचना: आपका लग्न {A} से {B} में बदलने से लगभग {m} मिनट दूर है। यदि आपके जन्म-समय में इतना अंतर संभव है, तो लग्न और D1 कुंडली के सभी भाव बदल सकते हैं। |
| X2 | Lagna Navamsa | Birth-time note: your D9 (Navamsa) Lagna would be {B} instead of {A} if you were born about {m} minutes {earlier/later}. | जन्म-समय सूचना: यदि जन्म लगभग {m} मिनट {पहले/बाद} होता, तो आपका नवांश (D9) लग्न {A} के स्थान पर {B} होता। |
| X3 | Moon Rashi | Birth-time note: the Moon was about {m} minutes from moving from {A} into {B}. | जन्म-समय सूचना: चंद्रमा {A} से {B} राशि में जाने से लगभग {m} मिनट दूर था। |
| X4 | Moon Nakshatra / Pada | Birth-time note: the Moon was about {m} minutes from moving from {N} Pada {p} to {N2} Pada {p2}. | जन्म-समय सूचना: चंद्रमा {N} नक्षत्र के {p} चरण से {N2} के {p2} चरण में जाने से लगभग {m} मिनट दूर था। |
| X5 | Exact boundary (numerical) | This position lies exactly on the boundary between {A} and {B}, within one second of birth time. By the standard rule, a boundary point belongs to the sign that begins there, so it is shown as {B}. | यह स्थिति {A} और {B} की ठीक सीमा पर है (जन्म-समय के एक सेकंड के भीतर)। मानक नियम के अनुसार सीमा-बिंदु उस राशि का माना जाता है जो वहाँ से आरंभ होती है, इसलिए इसे {B} दिखाया गया है। |
| X6 | Option 2 section intro | Some parts of a Kundali change quickly. The Lagna moves through a whole sign in about two hours, and through each Navamsa in about 13 minutes on average. This chart is calculated exactly for the time you entered. The items below would differ if the true birth time were a few minutes earlier or later. | कुंडली के कुछ भाग जल्दी बदलते हैं। लग्न लगभग दो घंटे में एक पूरी राशि और औसतन लगभग 13 मिनट में एक नवांश पार करता है। यह कुंडली आपके दर्ज किए गए समय के लिए ठीक-ठीक गणना की गई है। यदि वास्तविक जन्म-समय कुछ मिनट पहले या बाद का हो, तो नीचे दिए गए अंश अलग हो सकते हैं। |
| X7 | Option 3 (not recommended) | Your {item} cannot be stated reliably for this birth time, because it changes within {m} minutes. Please check the recorded birth time. | इस जन्म-समय के लिए आपका {item} विश्वसनीय रूप से नहीं बताया जा सकता, क्योंकि यह {m} मिनट के भीतर बदल जाता है। कृपया दर्ज जन्म-समय की जाँच करें। |

### Defects in the existing drafts

| # | Where | Defect | Fix in the recommendation |
|---|---|---|---|
| D-01 | X1, X3, X4 | No direction. "{m} minutes from changing" does not say whether an earlier or a later birth time causes the change. The Moon only moves forward, so for X3/X4 an earlier birth time gives the *previous* Rashi or Nakshatra, which the "from {A} into {B}" form cannot express | Separate *earlier* and *later* phrases (`offset.*`), and the current value is always stated first |
| D-02 | X2 | `{earlier/later}` and `{पहले/बाद}` are slash alternatives inside a placeholder. They cannot be implemented as a single field, and Hindi word order differs | Six catalogued offset phrases, each a complete grammatical unit in both languages |
| D-03 | X1 | "If your birth time could differ by that much" places doubt on the customer's record, and "could differ" twice reads as vague alarm. It also omits the D9 chart, whose Lagna and houses change too | "If the actual birth time were … than the time entered". The consequence is stated as a fact about house counting, for both D1 and D9 |
| D-04 | X3, X4 | Past tense ("the Moon was") in a report that describes the chart in the present tense ("the Moon is in …" on pages 2 and 7) | Present tense for the entered time, conditional for the alternative |
| D-05 | X3, X4, X6 | Hindi uses चंद्रमा. Both catalogs use चंद्र everywhere (13 occurrences, no चंद्रमा) | चंद्र (glossary G-05) |
| D-06 | all | Hindi spells जन्म-समय with a hyphen. The catalogs spell जन्म समय (7 occurrences, no hyphenated form) | जन्म समय (G-08) |
| D-07 | X4 | Hindi "{p} चरण" puts the number before the word. The catalogs use "चरण {pada}" | "{nakshatra} नक्षत्र के चरण {pada}" |
| D-08 | X4 | Only a Nakshatra change is covered. A Pada change inside the same Nakshatra (three of every four Pada edges) has no wording | Separate `note.moon_pada.change` |
| D-09 | all | Moon Navamsa, an SCI-06 item, has no wording | `note.moon_navamsa.one` |
| D-10 | X5 | "so it is shown as {B}" assumes that the position is just *after* the boundary. If the value is just *before* it, the item is shown in {A}, and the sentence would be false | The note names the side the position occupies at the time entered; the convention sentence is used only when it applies (§3.7) |
| D-11 | X5 | "By the standard rule" claims a universal standard. The half-open rule is this report's convention (SCI-01f) | "By the convention used in this report" |
| D-12 | X5 | "राशि" is used for every boundary, but Navamsa, Nakshatra and Pada boundaries also occur | Separate Rashi, Navamsa and Nakshatra/Pada boundary notes |
| D-13 | X5 | "within one second of birth time" is ambiguous (within one second of what?) | "A difference of less than one second in birth time decides which side it falls on" |
| D-14 | X5 | No handling of a printed longitude that rounds onto the boundary (for example 119.999999999996° prints as 120.00000000° but is classified Karka) | `boundary.rounding` (special case S-07) |
| D-15 | X6 | "calculated exactly" can be read as an accuracy claim. Hindi "ठीक-ठीक" has the same problem | "calculated for the birth time you entered" |
| D-16 | X6 | Hindi "अंश" for "items". In Jyotish, and in these catalogs (e.g. `chart.d1_note`), अंश means *degree* | "स्थितियाँ" (placements), as in the catalog's "मुख्य स्थितियाँ" (G-11) |
| D-17 | X6 | "a few minutes" does not match the approved 2-minute window, and the Moon's slower pace is not explained | States the 2-minute rule and the Moon's pace |
| D-18 | label | "सूचना" (notice) can read as an official warning | "टिप्पणी" (note), with alternatives for the reviewer (§4, G-09) |
| D-19 | X7 | Option 3 was not selected (SCI-06 chose Option 1) | Not carried forward. Kept above only as history |

---

## 3. Recommended wording

Each message below gives its trigger, the recommended English and Hindi, a literal back-translation of the Hindi (so the owner can check the meaning) and an example. The label (`label.note` or `label.boundary`) is printed before every short note, as **label:** text.

### 3.0 Shared building blocks

| Key | English | Hindi | Back-translation |
|---|---|---|---|
| `label.note` | Birth-time note | जन्म समय टिप्पणी | birth time note |
| `label.boundary` | Boundary note | सीमा टिप्पणी | boundary note |
| `label.more` (web link) | What does this mean? | इसका क्या अर्थ है? | what is the meaning of this? |
| `tag.note.pdf` | Birth-time note · p. {page} | जन्म समय टिप्पणी · पृ. {page} | birth time note · p. {page} |
| `tag.boundary.pdf` | Boundary note · p. {page} | सीमा टिप्पणी · पृ. {page} | boundary note · p. {page} |
| `offset.later.lt1` | less than a minute later | एक मिनट से भी कम समय बाद का | (of) less than one minute's time after |
| `offset.later.m1` | about 1 minute later | लगभग 1 मिनट बाद का | (of) about 1 minute after |
| `offset.later.m2` | about 2 minutes later | लगभग 2 मिनट बाद का | (of) about 2 minutes after |
| `offset.earlier.lt1` | less than a minute earlier | एक मिनट से भी कम समय पहले का | (of) less than one minute's time before |
| `offset.earlier.m1` | about 1 minute earlier | लगभग 1 मिनट पहले का | (of) about 1 minute before |
| `offset.earlier.m2` | about 2 minutes earlier | लगभग 2 मिनट पहले का | (of) about 2 minutes before |
| `body.lagna` / `body.moon` | Lagna / Moon | लग्न / चंद्र | Lagna / Moon |

**Offset rule (recommended; owner decision B6D-Q2).** Let *t* be the time in seconds, measured as elapsed time from the entered birth instant, to the nearest change of the item in one direction. Inside the SCI-06 window (*t* ≤ 120 s): *t* < 60 → `lt1`; 60 ≤ *t* < 90 → `m1`; 90 ≤ *t* ≤ 120 → `m2`. *t* below the exact-boundary threshold (§3.7) uses a boundary note instead. Seconds are never printed, because the entered time is itself usually recorded only to the minute.

Hindi grammar note for the reviewer: the offset phrases end in "का" so that they complete "यदि वास्तविक जन्म समय दर्ज समय के {offset} हो". The Hindi `lt1` form avoids a double "से" ("दर्ज समय से एक मिनट से कम") by using "दर्ज समय के … समय बाद का".

### 3.1 Lagna Rashi changes

**Trigger.** The D1 Lagna Rashi at the entered instant differs from the Lagna Rashi at some instant within 120 s before or after it, and the nearest change is not an exact-boundary case. Use `.one` when the change occurs in one direction only, and `.both` when it occurs in both directions (possible only where the Lagna moves fast, near the ±66° limit).

| | English | Hindi |
|---|---|---|
| `note.lagna_rashi.one` | For the time entered, your Lagna is {from_rashi}. If the actual birth time were {offset} than the time entered, the Lagna would be {to_rashi}. Houses are counted from the Lagna, so every house in the D1 and D9 charts would then have a different Rashi. | दर्ज समय के अनुसार आपका लग्न {from_rashi} है। यदि वास्तविक जन्म समय दर्ज समय के {offset} हो, तो लग्न {to_rashi} होगा। भाव लग्न से गिने जाते हैं, इसलिए तब D1 और D9 दोनों कुंडलियों के हर भाव की राशि बदल जाएगी। |
| `note.lagna_rashi.both` | For the time entered, your Lagna is {from_rashi}. It would be {to_rashi_earlier} if the actual birth time were {offset_earlier} than the time entered, or {to_rashi_later} if it were {offset_later}. Houses are counted from the Lagna, so either change would give every house in the D1 and D9 charts a different Rashi. | दर्ज समय के अनुसार आपका लग्न {from_rashi} है। यदि वास्तविक जन्म समय दर्ज समय के {offset_earlier} हो, तो लग्न {to_rashi_earlier} होगा, और यदि {offset_later} हो, तो {to_rashi_later}। भाव लग्न से गिने जाते हैं, इसलिए इनमें से किसी भी बदलाव पर D1 और D9 दोनों कुंडलियों के हर भाव की राशि बदल जाएगी। |

Back-translation (`.one`): "According to the entered time your Lagna is {from}. If the actual birth time is {offset} the entered time, then the Lagna will be {to}. Houses are counted from the Lagna, so then the Rashi of every house of both the D1 and D9 Kundalis will change."

Why the D9 is named: a Lagna Rashi boundary is also a Navamsa boundary (30° = 9 × 3°20′), so the D9 Lagna always changes as well.

Example (constructed; Lagna late in Karka, later direction, *t* = 100 s):
- EN: **Birth-time note:** For the time entered, your Lagna is Karka. If the actual birth time were about 2 minutes later than the time entered, the Lagna would be Simha. Houses are counted from the Lagna, so every house in the D1 and D9 charts would then have a different Rashi.
- HI: **जन्म समय टिप्पणी:** दर्ज समय के अनुसार आपका लग्न कर्क है। यदि वास्तविक जन्म समय दर्ज समय के लगभग 2 मिनट बाद का हो, तो लग्न सिंह होगा। भाव लग्न से गिने जाते हैं, इसलिए तब D1 और D9 दोनों कुंडलियों के हर भाव की राशि बदल जाएगी।

Example `.both` (constructed; high-latitude case):
- EN: **Birth-time note:** For the time entered, your Lagna is Mithuna. It would be Vrishabha if the actual birth time were about 2 minutes earlier than the time entered, or Karka if it were about 1 minute later. Houses are counted from the Lagna, so either change would give every house in the D1 and D9 charts a different Rashi.
- HI: **जन्म समय टिप्पणी:** दर्ज समय के अनुसार आपका लग्न मिथुन है। यदि वास्तविक जन्म समय दर्ज समय के लगभग 2 मिनट पहले का हो, तो लग्न वृषभ होगा, और यदि लगभग 1 मिनट बाद का हो, तो कर्क। भाव लग्न से गिने जाते हैं, इसलिए इनमें से किसी भी बदलाव पर D1 और D9 दोनों कुंडलियों के हर भाव की राशि बदल जाएगी।

### 3.2 Lagna Navamsa (D9 Lagna) changes

**Trigger.** The D9 Lagna at the entered instant differs from the D9 Lagna within 120 s before or after it, not an exact-boundary case. `.one`: one direction, one change. `.both`: one change in each direction. `.multiple`: two or more changes in at least one direction (only where the Lagna moves faster than 3°20′ in 2 minutes, i.e. at high latitudes).

| | English | Hindi |
|---|---|---|
| `note.lagna_navamsa.one` | For the time entered, your D9 Lagna is {from_rashi}. If the actual birth time were {offset} than the time entered, the D9 Lagna would be {to_rashi}. Houses in the D9 chart are counted from the D9 Lagna, so each of them would then have a different Rashi. | दर्ज समय के अनुसार आपका D9 लग्न {from_rashi} है। यदि वास्तविक जन्म समय दर्ज समय के {offset} हो, तो D9 लग्न {to_rashi} होगा। D9 कुंडली के भाव D9 लग्न से गिने जाते हैं, इसलिए तब उसके हर भाव की राशि बदल जाएगी। |
| `note.lagna_navamsa.both` | For the time entered, your D9 Lagna is {from_rashi}. It would be {to_rashi_earlier} if the actual birth time were {offset_earlier} than the time entered, or {to_rashi_later} if it were {offset_later}. Houses in the D9 chart are counted from the D9 Lagna, so either change would give each of them a different Rashi. | दर्ज समय के अनुसार आपका D9 लग्न {from_rashi} है। यदि वास्तविक जन्म समय दर्ज समय के {offset_earlier} हो, तो D9 लग्न {to_rashi_earlier} होगा, और यदि {offset_later} हो, तो {to_rashi_later}। D9 कुंडली के भाव D9 लग्न से गिने जाते हैं, इसलिए इनमें से किसी भी बदलाव पर उसके हर भाव की राशि बदल जाएगी। |
| `note.lagna_navamsa.multiple` | For the time entered, your D9 Lagna is {from_rashi}. At this birthplace the Lagna is moving quickly at this time, and the D9 Lagna changes more than once between 2 minutes before and 2 minutes after the time entered. | दर्ज समय के अनुसार आपका D9 लग्न {from_rashi} है। इस जन्म स्थान पर इस समय लग्न तेज़ी से आगे बढ़ रहा है, और दर्ज समय से 2 मिनट पहले से 2 मिनट बाद तक के बीच D9 लग्न एक से अधिक बार बदलता है। |

Back-translation (`.one`): "According to the entered time your D9 Lagna is {from}. If the actual birth time is {offset} the entered time, then the D9 Lagna will be {to}. The houses of the D9 Kundali are counted from the D9 Lagna, so then the Rashi of each of its houses will change."

Back-translation (`.multiple`): "According to the entered time your D9 Lagna is {from}. At this birthplace at this time the Lagna is moving forward quickly, and between 2 minutes before and 2 minutes after the entered time the D9 Lagna changes more than once."

Examples (constructed):
- `.one`, earlier, *t* = 70 s. EN: **Birth-time note:** For the time entered, your D9 Lagna is Tula. If the actual birth time were about 1 minute earlier than the time entered, the D9 Lagna would be Kanya. Houses in the D9 chart are counted from the D9 Lagna, so each of them would then have a different Rashi.
- HI: **जन्म समय टिप्पणी:** दर्ज समय के अनुसार आपका D9 लग्न तुला है। यदि वास्तविक जन्म समय दर्ज समय के लगभग 1 मिनट पहले का हो, तो D9 लग्न कन्या होगा। D9 कुंडली के भाव D9 लग्न से गिने जाते हैं, इसलिए तब उसके हर भाव की राशि बदल जाएगी।
- `.both`, earlier *t* = 40 s, later *t* = 110 s. EN: **Birth-time note:** For the time entered, your D9 Lagna is Vrishabha. It would be Mesha if the actual birth time were less than a minute earlier than the time entered, or Mithuna if it were about 2 minutes later. Houses in the D9 chart are counted from the D9 Lagna, so either change would give each of them a different Rashi.
- HI: **जन्म समय टिप्पणी:** दर्ज समय के अनुसार आपका D9 लग्न वृषभ है। यदि वास्तविक जन्म समय दर्ज समय के एक मिनट से भी कम समय पहले का हो, तो D9 लग्न मेष होगा, और यदि लगभग 2 मिनट बाद का हो, तो मिथुन। D9 कुंडली के भाव D9 लग्न से गिने जाते हैं, इसलिए इनमें से किसी भी बदलाव पर उसके हर भाव की राशि बदल जाएगी।
- `.multiple`. EN: **Birth-time note:** For the time entered, your D9 Lagna is Makara. At this birthplace the Lagna is moving quickly at this time, and the D9 Lagna changes more than once between 2 minutes before and 2 minutes after the time entered.
- HI: **जन्म समय टिप्पणी:** दर्ज समय के अनुसार आपका D9 लग्न मकर है। इस जन्म स्थान पर इस समय लग्न तेज़ी से आगे बढ़ रहा है, और दर्ज समय से 2 मिनट पहले से 2 मिनट बाद तक के बीच D9 लग्न एक से अधिक बार बदलता है।

### 3.3 Moon Rashi changes

**Trigger.** The Moon's D1 Rashi changes within 120 s before or after the entered instant, not an exact-boundary case. The Moon moves about 0.008° to 0.011° per minute, so at most one change can fall inside the window, in one direction only.

| | English | Hindi |
|---|---|---|
| `note.moon_rashi.one` | For the time entered, the Moon is in {from_rashi}. If the actual birth time were {offset} than the time entered, the Moon would be in {to_rashi}. | दर्ज समय के अनुसार चंद्र {from_rashi} राशि में है। यदि वास्तविक जन्म समय दर्ज समय के {offset} हो, तो चंद्र {to_rashi} राशि में होगा। |

Back-translation: "According to the entered time the Moon is in the {from} Rashi. If the actual birth time is {offset} the entered time, then the Moon will be in the {to} Rashi."

Example (constructed; Moon just before 30°, later, *t* = 75 s):
- EN: **Birth-time note:** For the time entered, the Moon is in Mesha. If the actual birth time were about 1 minute later than the time entered, the Moon would be in Vrishabha.
- HI: **जन्म समय टिप्पणी:** दर्ज समय के अनुसार चंद्र मेष राशि में है। यदि वास्तविक जन्म समय दर्ज समय के लगभग 1 मिनट बाद का हो, तो चंद्र वृषभ राशि में होगा।

A Moon Rashi boundary is always also a Pada and a Navamsa boundary, so §3.4 or §3.5 and §3.6 trigger at the same time (special case S-03).

### 3.4 Moon Nakshatra and Pada change (Nakshatra changes)

**Trigger.** The Moon's Nakshatra changes within 120 s (the Pada then changes too), not an exact-boundary case.

| | English | Hindi |
|---|---|---|
| `note.moon_nakshatra.change` | For the time entered, the Moon is in {from_nakshatra} Nakshatra, Pada {from_pada}. If the actual birth time were {offset} than the time entered, the Moon would be in {to_nakshatra} Nakshatra, Pada {to_pada}. | दर्ज समय के अनुसार चंद्र {from_nakshatra} नक्षत्र के चरण {from_pada} में है। यदि वास्तविक जन्म समय दर्ज समय के {offset} हो, तो चंद्र {to_nakshatra} नक्षत्र के चरण {to_pada} में होगा। |

Back-translation: "According to the entered time the Moon is in Pada {p} of {N} Nakshatra. If the actual birth time is {offset} the entered time, then the Moon will be in Pada {p2} of {N2} Nakshatra."

Example (constructed; Moon just after 40°, earlier, *t* = 95 s):
- EN: **Birth-time note:** For the time entered, the Moon is in Rohini Nakshatra, Pada 1. If the actual birth time were about 2 minutes earlier than the time entered, the Moon would be in Krittika Nakshatra, Pada 4.
- HI: **जन्म समय टिप्पणी:** दर्ज समय के अनुसार चंद्र रोहिणी नक्षत्र के चरण 1 में है। यदि वास्तविक जन्म समय दर्ज समय के लगभग 2 मिनट पहले का हो, तो चंद्र कृत्तिका नक्षत्र के चरण 4 में होगा।

### 3.5 Moon Pada changes within the same Nakshatra

**Trigger.** The Moon's Pada changes within 120 s and the Nakshatra does not, not an exact-boundary case.

| | English | Hindi |
|---|---|---|
| `note.moon_pada.change` | For the time entered, the Moon is in {nakshatra} Nakshatra, Pada {from_pada}. If the actual birth time were {offset} than the time entered, the Moon would be in Pada {to_pada} of the same Nakshatra. | दर्ज समय के अनुसार चंद्र {nakshatra} नक्षत्र के चरण {from_pada} में है। यदि वास्तविक जन्म समय दर्ज समय के {offset} हो, तो चंद्र इसी नक्षत्र के चरण {to_pada} में होगा। |

Back-translation: "According to the entered time the Moon is in Pada {p} of {N} Nakshatra. If the actual birth time is {offset} the entered time, then the Moon will be in Pada {p2} of this same Nakshatra."

Example (constructed; same chart as §3.3):
- EN: **Birth-time note:** For the time entered, the Moon is in Krittika Nakshatra, Pada 1. If the actual birth time were about 1 minute later than the time entered, the Moon would be in Pada 2 of the same Nakshatra.
- HI: **जन्म समय टिप्पणी:** दर्ज समय के अनुसार चंद्र कृत्तिका नक्षत्र के चरण 1 में है। यदि वास्तविक जन्म समय दर्ज समय के लगभग 1 मिनट बाद का हो, तो चंद्र इसी नक्षत्र के चरण 2 में होगा।

### 3.6 Moon Navamsa (Moon D9 Rashi) changes

**Trigger.** The Moon's D9 Rashi changes within 120 s, not an exact-boundary case. Every Pada boundary is also a Navamsa boundary (both are 3°20′ steps from 0° Mesha), so this always fires together with §3.4 or §3.5.

| | English | Hindi |
|---|---|---|
| `note.moon_navamsa.one` | For the time entered, the Moon's D9 Rashi is {from_rashi}. If the actual birth time were {offset} than the time entered, it would be {to_rashi}. | दर्ज समय के अनुसार चंद्र की D9 राशि {from_rashi} है। यदि वास्तविक जन्म समय दर्ज समय के {offset} हो, तो यह {to_rashi} होगी। |

Back-translation: "According to the entered time the Moon's D9 Rashi is {from}. If the actual birth time is {offset} the entered time, then it will be {to}."

Example (constructed; same chart as §3.3):
- EN: **Birth-time note:** For the time entered, the Moon's D9 Rashi is Dhanu. If the actual birth time were about 1 minute later than the time entered, it would be Makara.
- HI: **जन्म समय टिप्पणी:** दर्ज समय के अनुसार चंद्र की D9 राशि धनु है। यदि वास्तविक जन्म समय दर्ज समय के लगभग 1 मिनट बाद का हो, तो यह मकर होगी।

### 3.7 Exact numerical boundary

**Trigger (recommended; owner decision B6D-Q1).** For any SCI-06 item, the time to the nearest change in either direction is less than **1 second**, or the computation reports the case as resolution-limited (PR #63 §2: a float64 Julian date resolves only about 4e-5 s). The boundary note replaces the minute-based note for that item. `boundary.convention` is appended only when the position is classified into the division that *begins* at the boundary (the half-open rule actually decided the result). `boundary.rounding` is appended only when the printed longitude, at its printed precision, equals the boundary value.

| | English | Hindi |
|---|---|---|
| `boundary.rashi` | At the time entered, the {body} is at the boundary between {rashi_before} and {rashi_after}. A difference of less than one second in birth time decides which side it falls on. It is shown in {shown}, the Rashi it occupies at the time entered. | दर्ज समय पर {body} {rashi_before} और {rashi_after} राशियों की सीमा पर है। जन्म समय में एक सेकंड से भी कम का अंतर तय करता है कि यह सीमा के किस ओर होगा। इसे {shown} में दिखाया गया है, क्योंकि दर्ज समय पर यह उसी राशि में है। |
| `boundary.navamsa` | At the time entered, the {body} is at the boundary between two Navamsas, D9 {rashi_before} and D9 {rashi_after}. A difference of less than one second in birth time decides which side it falls on. It is shown in D9 {shown}, the Navamsa it occupies at the time entered. | दर्ज समय पर {body} दो नवांशों, D9 {rashi_before} और D9 {rashi_after}, की सीमा पर है। जन्म समय में एक सेकंड से भी कम का अंतर तय करता है कि यह सीमा के किस ओर होगा। इसे D9 {shown} में दिखाया गया है, क्योंकि दर्ज समय पर यह उसी नवांश में है। |
| `boundary.nakshatra_pada` | At the time entered, the Moon is at the boundary between {nakshatra_before} Nakshatra, Pada {pada_before} and {nakshatra_after} Nakshatra, Pada {pada_after}. A difference of less than one second in birth time decides which side it falls on. It is shown in {shown_nakshatra} Nakshatra, Pada {shown_pada}, where it is at the time entered. | दर्ज समय पर चंद्र {nakshatra_before} नक्षत्र के चरण {pada_before} और {nakshatra_after} नक्षत्र के चरण {pada_after} की सीमा पर है। जन्म समय में एक सेकंड से भी कम का अंतर तय करता है कि यह सीमा के किस ओर होगा। इसे {shown_nakshatra} नक्षत्र के चरण {shown_pada} में दिखाया गया है, क्योंकि दर्ज समय पर यह वहीं है। |
| `boundary.convention` | By the convention used in this report, a position exactly at a boundary is counted in the division that begins there. | इस रिपोर्ट की परिपाटी के अनुसार, ठीक सीमा पर स्थित स्थिति को उस भाग में गिना जाता है जो वहीं से आरंभ होता है। |
| `boundary.rounding` | The printed longitude is rounded, so it can appear to be exactly on the boundary. The classification uses the unrounded value. | छपा हुआ भोगांश पूर्णांकित है, इसलिए वह ठीक सीमा पर दिख सकता है। वर्गीकरण बिना पूर्णांकन वाले मान से किया जाता है। |

Back-translation (`boundary.rashi`): "At the entered time the {body} is on the boundary of the {A} and {B} Rashis. A difference of even less than one second in birth time decides on which side of the boundary it will be. It has been shown in {shown}, because at the entered time it is in that very Rashi."

Back-translation (`boundary.convention`): "According to this report's convention, a position situated exactly on a boundary is counted in the part that begins right there."

Example (**reference**, GOLD-E01: synthetic New Delhi chart at `2008-01-24T09:31:02.327269+05:30`; swetest Moon `120.00000000071`°, 7.1e-10° past the Karka/Simha, Ashlesha/Magha and Navamsa edge; engine and reference both give Simha, D9 Mesha, Magha Pada 1; printed longitude `120.0`):
- Moon Rashi, EN: **Boundary note:** At the time entered, the Moon is at the boundary between Karka and Simha. A difference of less than one second in birth time decides which side it falls on. It is shown in Simha, the Rashi it occupies at the time entered. By the convention used in this report, a position exactly at a boundary is counted in the division that begins there. The printed longitude is rounded, so it can appear to be exactly on the boundary. The classification uses the unrounded value.
- Moon Rashi, HI: **सीमा टिप्पणी:** दर्ज समय पर चंद्र कर्क और सिंह राशियों की सीमा पर है। जन्म समय में एक सेकंड से भी कम का अंतर तय करता है कि यह सीमा के किस ओर होगा। इसे सिंह में दिखाया गया है, क्योंकि दर्ज समय पर यह उसी राशि में है। इस रिपोर्ट की परिपाटी के अनुसार, ठीक सीमा पर स्थित स्थिति को उस भाग में गिना जाता है जो वहीं से आरंभ होता है। छपा हुआ भोगांश पूर्णांकित है, इसलिए वह ठीक सीमा पर दिख सकता है। वर्गीकरण बिना पूर्णांकन वाले मान से किया जाता है।
- Moon D9 Rashi, EN: **Boundary note:** At the time entered, the Moon is at the boundary between two Navamsas, D9 Meena and D9 Mesha. A difference of less than one second in birth time decides which side it falls on. It is shown in D9 Mesha, the Navamsa it occupies at the time entered. By the convention used in this report, a position exactly at a boundary is counted in the division that begins there.
- Moon D9 Rashi, HI: **सीमा टिप्पणी:** दर्ज समय पर चंद्र दो नवांशों, D9 मीन और D9 मेष, की सीमा पर है। जन्म समय में एक सेकंड से भी कम का अंतर तय करता है कि यह सीमा के किस ओर होगा। इसे D9 मेष में दिखाया गया है, क्योंकि दर्ज समय पर यह उसी नवांश में है। इस रिपोर्ट की परिपाटी के अनुसार, ठीक सीमा पर स्थित स्थिति को उस भाग में गिना जाता है जो वहीं से आरंभ होता है।
- Moon Nakshatra and Pada, EN: **Boundary note:** At the time entered, the Moon is at the boundary between Ashlesha Nakshatra, Pada 4 and Magha Nakshatra, Pada 1. A difference of less than one second in birth time decides which side it falls on. It is shown in Magha Nakshatra, Pada 1, where it is at the time entered. By the convention used in this report, a position exactly at a boundary is counted in the division that begins there.
- Moon Nakshatra and Pada, HI: **सीमा टिप्पणी:** दर्ज समय पर चंद्र आश्लेषा नक्षत्र के चरण 4 और मघा नक्षत्र के चरण 1 की सीमा पर है। जन्म समय में एक सेकंड से भी कम का अंतर तय करता है कि यह सीमा के किस ओर होगा। इसे मघा नक्षत्र के चरण 1 में दिखाया गया है, क्योंकि दर्ज समय पर यह वहीं है। इस रिपोर्ट की परिपाटी के अनुसार, ठीक सीमा पर स्थित स्थिति को उस भाग में गिना जाता है जो वहीं से आरंभ होता है।

### 3.8 Summary on the Birth details page

**Trigger.** At least one note from §3.1 to §3.7 applies. `{item_list}` is built from the `item.*` names below, joined with `list.join` and `list.join_last`, in the fixed order Lagna, D9 Lagna, Moon Rashi, Moon D9 Rashi, Moon Nakshatra and Pada (or Moon Pada).

| Key | English | Hindi |
|---|---|---|
| `summary.body` | Some placements in this chart would be different if the actual birth time were up to 2 minutes earlier or later than the time entered: {item_list}. Each one is marked where it appears. The chart itself is calculated for the time entered. | यदि वास्तविक जन्म समय दर्ज समय से 2 मिनट तक पहले या बाद का हो, तो इस कुंडली की कुछ स्थितियाँ अलग होंगी: {item_list}। हर ऐसी स्थिति के पास टिप्पणी दी गई है। कुंडली की गणना दर्ज समय के लिए ही की गई है। |
| `summary.record` | A recorded birth time is usually given to the minute, and is sometimes approximate. If you have an official birth record, you can compare its time with the time shown here. | दर्ज जन्म समय प्रायः मिनट तक ही लिखा होता है, और कभी-कभी अनुमानित होता है। यदि आपके पास जन्म का आधिकारिक रिकॉर्ड है, तो उसमें लिखे समय को यहाँ दिखाए गए समय से मिला सकते हैं। |
| `item.lagna_rashi` | Lagna | लग्न |
| `item.lagna_navamsa` | D9 Lagna | D9 लग्न |
| `item.moon_rashi` | Moon Rashi | चंद्र राशि |
| `item.moon_navamsa` | Moon D9 Rashi | चंद्र की D9 राशि |
| `item.moon_nakshatra` | Moon Nakshatra and Pada | चंद्र नक्षत्र और चरण |
| `item.moon_pada` | Moon Pada | चंद्र का चरण |

Back-translation (`summary.record`): "An entered birth time is usually written only to the minute, and sometimes it is estimated. If you have an official record of the birth, you can compare the time written in it with the time shown here."

`summary.record` makes a general statement about how birth times are recorded. It is not a statistic and is not about this customer. The reviewer may delete it.

Example (constructed; the §3.3 chart):
- EN: **Birth-time note:** Some placements in this chart would be different if the actual birth time were up to 2 minutes earlier or later than the time entered: Moon Rashi, Moon D9 Rashi and Moon Pada. Each one is marked where it appears. The chart itself is calculated for the time entered. A recorded birth time is usually given to the minute, and is sometimes approximate. If you have an official birth record, you can compare its time with the time shown here.
- HI: **जन्म समय टिप्पणी:** यदि वास्तविक जन्म समय दर्ज समय से 2 मिनट तक पहले या बाद का हो, तो इस कुंडली की कुछ स्थितियाँ अलग होंगी: चंद्र राशि, चंद्र की D9 राशि और चंद्र का चरण। हर ऐसी स्थिति के पास टिप्पणी दी गई है। कुंडली की गणना दर्ज समय के लिए ही की गई है। दर्ज जन्म समय प्रायः मिनट तक ही लिखा होता है, और कभी-कभी अनुमानित होता है। यदि आपके पास जन्म का आधिकारिक रिकॉर्ड है, तो उसमें लिखे समय को यहाँ दिखाए गए समय से मिला सकते हैं।

### 3.9 Optional premium appendix (SCI-06 Option 2)

**Trigger.** Premium edition only, and only when at least one note applies (owner decision B6D-Q3 on placement). Never shown as an empty or "nothing to report" page.

| Key | English | Hindi |
|---|---|---|
| `appendix.title` | Birth time and this chart | जन्म समय और यह कुंडली |
| `appendix.p1` | This chart is calculated for the birth time you entered. Some parts of a Kundali change faster than others. On average the Lagna moves into the next Rashi about every two hours and into the next Navamsa about every 13 minutes; the actual pace depends on the Rashi and the birthplace. The Moon moves more slowly: its Pada changes roughly every six hours and its Nakshatra roughly once a day. | यह कुंडली आपके द्वारा दर्ज जन्म समय के लिए गणना की गई है। कुंडली के कुछ भाग दूसरों की तुलना में जल्दी बदलते हैं। लग्न औसतन लगभग हर दो घंटे में अगली राशि में और लगभग हर 13 मिनट में अगले नवांश में जाता है; वास्तविक गति राशि और जन्म स्थान पर निर्भर करती है। चंद्र इससे धीरे चलता है: उसका चरण लगभग हर छह घंटे में और नक्षत्र लगभग दिन में एक बार बदलता है। |
| `appendix.p2` | The placements listed below would be different if the actual birth time were up to 2 minutes earlier or later than the time entered. This is not a correction, and it is not a measure of calculation accuracy. It shows how closely these placements depend on the birth time. | यदि वास्तविक जन्म समय दर्ज समय से 2 मिनट तक पहले या बाद का हो, तो नीचे दी गई स्थितियाँ अलग होंगी। यह कोई सुधार नहीं है, और न ही गणना की सटीकता का माप है। यह केवल दिखाता है कि ये स्थितियाँ जन्म समय पर कितनी बारीकी से निर्भर हैं। |
| `appendix.col.placement` | Placement | स्थिति |
| `appendix.col.entered` | For the time entered | दर्ज समय के अनुसार |
| `appendix.col.alternative` | Would become | बदलकर होगी |
| `appendix.col.when` | If the actual birth time were | यदि वास्तविक जन्म समय हो |
| `appendix.cell.boundary` | at the boundary (less than one second) | सीमा पर (एक सेकंड से भी कम) |
| `appendix.cell.multiple` | changes more than once within 2 minutes | 2 मिनट के भीतर एक से अधिक बार बदलता है |
| `appendix.p3` | The 2-minute range is a fixed reporting rule applied to every chart. It does not mean that your recorded birth time is wrong. A recorded birth time is usually given to the minute, and is sometimes approximate. If you have an official birth record, you can compare its time with the time on {birth_details_ref}. Nothing in this section changes the placements shown in the rest of this report. | 2 मिनट की यह सीमा हर कुंडली पर लागू होने वाला एक निश्चित नियम है। इसका अर्थ यह नहीं है कि आपका दर्ज जन्म समय गलत है। दर्ज जन्म समय प्रायः मिनट तक ही लिखा होता है, और कभी-कभी अनुमानित होता है। यदि आपके पास जन्म का आधिकारिक रिकॉर्ड है, तो उसमें लिखे समय को {birth_details_ref} पर दिए समय से मिला सकते हैं। इस खंड से इस रिपोर्ट के बाकी भागों में दिखाई गई कोई भी स्थिति नहीं बदलती। |
| `appendix.p4_boundary` (only if a boundary row exists) | A placement marked as a boundary case is less than one second of birth time away from a boundary. It is shown in the division it occupies at the time entered. By the convention used in this report, a position exactly at a boundary is counted in the division that begins there. | सीमा वाली स्थिति के रूप में चिह्नित स्थिति, जन्म समय के हिसाब से, किसी सीमा से एक सेकंड से भी कम दूर है। इसे उसी भाग में दिखाया गया है जिसमें यह दर्ज समय पर है। इस रिपोर्ट की परिपाटी के अनुसार, ठीक सीमा पर स्थित स्थिति को उस भाग में गिना जाता है जो वहीं से आरंभ होता है। |
| `appendix.p5_scope` | The positions themselves are calculated with Swiss Ephemeris and checked by the engine's own conformance tests. The validation status of those calculations is stated on {method_ref}. | ग्रह स्थितियाँ स्वयं Swiss Ephemeris से गणना की जाती हैं और इंजन के अपने अनुरूपता परीक्षणों द्वारा जाँची जाती हैं। इन गणनाओं की सत्यापन स्थिति {method_ref} पर बताई गई है। |
| `ref.birth_details.pdf` / `.web` | page {page} / Confirmed birth details | पृष्ठ {page} / पुष्टि किया गया जन्म विवरण |
| `ref.method.pdf` / `.web` | page {page} / Method and transparency | पृष्ठ {page} / गणना पद्धति और पारदर्शिता |

The `.web` references reuse the existing catalog headings `ui.confirm.heading` and `ui.method.heading` exactly.

Facts used in `appendix.p1`, for the Jyotish reviewer to confirm: 12 Rashis per sidereal day gives about two hours per Rashi on average, and nine Navamsas per Rashi gives about 13.3 minutes per Navamsa; the Moon's mean motion (about 13.2° per day) gives about one Nakshatra (13°20′) per day and one Pada (3°20′) about every six hours. These are averages, which the text says.

`appendix.p5_scope` repeats only what page 10 already says (Swiss-on-Swiss conformance, not independent validation). It makes no new accuracy claim.

### 3.10 Static Methodology row (always present once the feature ships)

| Key | English | Hindi |
|---|---|---|
| `method.row.label` | Birth-time notes | जन्म समय टिप्पणियाँ |
| `method.row.value` | Shown when the Lagna, the D9 Lagna, or the Moon's Rashi, D9 Rashi, Nakshatra or Pada would change within 2 minutes before or after the time entered. Every placement is calculated for the time entered. | तब दिखाई जाती हैं जब दर्ज समय से 2 मिनट पहले या बाद तक के भीतर लग्न, D9 लग्न, या चंद्र की राशि, D9 राशि, नक्षत्र या चरण बदलता हो। हर स्थिति की गणना दर्ज समय के लिए ही की जाती है। |

This row explains the rule on every report, including reports with no notes. It does not say "no notes apply", which could be read as a statement that the chart is certain.

---

## 4. Glossary and terminology decisions

These follow the existing catalogs unless stated. "Catalog" means the PR #61 head catalogs listed at the top, which are themselves pending human review (KUN-I18N-003). If the KUN-I18N-003 reviewers change a catalog term, the same change applies here.

| ID | English | Hindi | Decision and reason | Review layer |
|---|---|---|---|---|
| G-01 | Lagna | लग्न | Catalog term. "Ascendant" and "Asc" are not used in notes; "Asc" stays a chart label only | J |
| G-02 | Rashi | राशि | Catalog term. Rashi names come from the catalog (`terms.rashi`), Sanskrit form in English (Simha, not Leo) | J |
| G-03 | D9 Lagna; Navamsa | D9 लग्न; नवांश | Catalog uses "D9 Lagna" / "D9 लग्न" on every tile and chart label, so notes use it too. "Navamsa" / "नवांश" is used when talking about the division itself (boundary note, appendix). PR #63's "D9 (Navamsa) Lagna" / "नवांश (D9) लग्न" is not used, to keep one form | J |
| G-04 | Moon D9 Rashi | चंद्र की D9 राशि | Matches the catalog column "D9 Rashi" / "D9 राशि" on page 8 and the web table | J+L |
| G-05 | Moon | चंद्र | Catalog form (no चंद्रमा anywhere). Reviewer may prefer चंद्रमा in running prose, but then the catalog must change too | L |
| G-06 | Nakshatra; Pada | नक्षत्र; चरण | Catalog terms (KUN-I18N-003 item 2). Word order "{nakshatra} नक्षत्र के चरण {pada}", matching "चरण {pada}" | J |
| G-07 | time entered; actual birth time | दर्ज समय; वास्तविक जन्म समय | The central distinction. "Entered" is what the customer typed and the chart uses; "actual" is the true moment of birth, which may differ. Never "your time is wrong", never "true time" | L |
| G-08 | birth time | जन्म समय | Catalog spelling, no hyphen | L |
| G-09 | Birth-time note; Boundary note | जन्म समय टिप्पणी; सीमा टिप्पणी | टिप्पणी (note) is neutral. Alternatives: जन्म समय संबंधी टिप्पणी (longer), जन्म समय सूचना (PR #63; can read as a notice or warning) | L |
| G-10 | boundary | सीमा | Neutral word. **Not** sandhi or Gandanta (गंडांत): those carry interpretive and fear connotations, and the 0°/120°/240° Moon junctions in particular must not be named Gandanta | J |
| G-11 | placement | स्थिति / स्थितियाँ | Catalog term ("मुख्य स्थितियाँ"). अंश is never used for "item", because in Jyotish and in the catalog it means degree | J+L |
| G-12 | convention | परिपाटी | Catalog term ("परिपाटियाँ", page 10 heading). Not "standard rule" / "मानक नियम" | L |
| G-13 | house | भाव | Catalog term | J |
| G-14 | rounded; unrounded | पूर्णांकित; बिना पूर्णांकन वाला | New in this packet; reviewer to confirm | L |
| G-15 | conformance tests | अनुरूपता परीक्षण | Catalog term from page 10 `method.status` | L |

Numerals: ASCII digits in both languages, as in the catalogs (D1, D9, चरण 2, पृ. 4). Minute values are identical in both languages for the same chart (PRD locale QA: numerical identity across languages).

---

## 5. Placeholders and variables

| Placeholder | Used in | Source and format |
|---|---|---|
| `{from_rashi}`, `{to_rashi}`, `{to_rashi_earlier}`, `{to_rashi_later}` | Lagna, D9 Lagna, Moon Rashi, Moon D9 Rashi notes | Rashi name from catalog `terms.rashi.<Name>.en` / `.hi`. Never a Western sign name, never a number alone |
| `{rashi_before}`, `{rashi_after}`, `{shown}` | boundary notes | As above. `{shown}` must equal the engine's classification at the entered instant, byte for byte with the rest of the report |
| `{from_nakshatra}`, `{to_nakshatra}`, `{nakshatra}`, `{nakshatra_before}`, `{nakshatra_after}`, `{shown_nakshatra}` | Moon Nakshatra notes | Catalog `terms.nakshatra` |
| `{from_pada}`, `{to_pada}`, `{pada_before}`, `{pada_after}`, `{shown_pada}` | Moon Nakshatra/Pada notes | Integer 1 to 4, ASCII digit |
| `{offset}`, `{offset_earlier}`, `{offset_later}` | all minute-based notes | One of the six `offset.*` strings in the same language, chosen by the rule in §3.0 |
| `{body}` | `boundary.rashi`, `boundary.navamsa` | `body.lagna` or `body.moon`. For the D9 Lagna boundary, `body.lagna` with `boundary.navamsa` |
| `{item_list}` | `summary.body` | `item.*` names joined per §3.8 |
| `{page}` | `tag.*.pdf`, `ref.*.pdf` | Integer page number from the renderer's page plan |
| `{birth_details_ref}`, `{method_ref}` | appendix | `ref.birth_details.pdf` / `.web`, `ref.method.pdf` / `.web` |

Rules for implementation (for the later engineering task, not this one):
- EN and HI use exactly the same placeholder set for each key (checked by `check_packet.py`).
- Only catalogued values are inserted. No customer name, place, date or time is inserted into any note.
- "2 minutes" is written literally, because SCI-06 fixes W = 2 minutes. If the owner ever changes W, every string containing "2" minutes must be re-reviewed; a `{window}` placeholder is not proposed, because Hindi and English agreement for 1 versus several minutes differs.
- Missing or unknown values make the renderer refuse the note (and fail the report build), never print a raw `{field}`.

---

## 6. Short and expanded disclosures, side by side

**Short (PDF page 4 and the web Birth details panel), constructed §3.3 chart.**

| English | Hindi |
|---|---|
| **Birth-time note:** Some placements in this chart would be different if the actual birth time were up to 2 minutes earlier or later than the time entered: Moon Rashi, Moon D9 Rashi and Moon Pada. Each one is marked where it appears. The chart itself is calculated for the time entered. A recorded birth time is usually given to the minute, and is sometimes approximate. If you have an official birth record, you can compare its time with the time shown here. | **जन्म समय टिप्पणी:** यदि वास्तविक जन्म समय दर्ज समय से 2 मिनट तक पहले या बाद का हो, तो इस कुंडली की कुछ स्थितियाँ अलग होंगी: चंद्र राशि, चंद्र की D9 राशि और चंद्र का चरण। हर ऐसी स्थिति के पास टिप्पणी दी गई है। कुंडली की गणना दर्ज समय के लिए ही की गई है। दर्ज जन्म समय प्रायः मिनट तक ही लिखा होता है, और कभी-कभी अनुमानित होता है। यदि आपके पास जन्म का आधिकारिक रिकॉर्ड है, तो उसमें लिखे समय को यहाँ दिखाए गए समय से मिला सकते हैं। |
| **Birth-time note:** For the time entered, the Moon is in Mesha. If the actual birth time were about 1 minute later than the time entered, the Moon would be in Vrishabha. | **जन्म समय टिप्पणी:** दर्ज समय के अनुसार चंद्र मेष राशि में है। यदि वास्तविक जन्म समय दर्ज समय के लगभग 1 मिनट बाद का हो, तो चंद्र वृषभ राशि में होगा। |
| **Birth-time note:** For the time entered, the Moon's D9 Rashi is Dhanu. If the actual birth time were about 1 minute later than the time entered, it would be Makara. | **जन्म समय टिप्पणी:** दर्ज समय के अनुसार चंद्र की D9 राशि धनु है। यदि वास्तविक जन्म समय दर्ज समय के लगभग 1 मिनट बाद का हो, तो यह मकर होगी। |
| **Birth-time note:** For the time entered, the Moon is in Krittika Nakshatra, Pada 1. If the actual birth time were about 1 minute later than the time entered, the Moon would be in Pada 2 of the same Nakshatra. | **जन्म समय टिप्पणी:** दर्ज समय के अनुसार चंद्र कृत्तिका नक्षत्र के चरण 1 में है। यदि वास्तविक जन्म समय दर्ज समय के लगभग 1 मिनट बाद का हो, तो चंद्र इसी नक्षत्र के चरण 2 में होगा। |

Elsewhere in the PDF each affected value carries only the tag, for example "Birth-time note · p. 4" / "जन्म समय टिप्पणी · पृ. 4" (see `DESIGN-INTEGRATION.md`).

**Expanded (optional premium appendix), same chart, English.**

> **Birth time and this chart**
>
> This chart is calculated for the birth time you entered. Some parts of a Kundali change faster than others. On average the Lagna moves into the next Rashi about every two hours and into the next Navamsa about every 13 minutes; the actual pace depends on the Rashi and the birthplace. The Moon moves more slowly: its Pada changes roughly every six hours and its Nakshatra roughly once a day.
>
> The placements listed below would be different if the actual birth time were up to 2 minutes earlier or later than the time entered. This is not a correction, and it is not a measure of calculation accuracy. It shows how closely these placements depend on the birth time.
>
> | Placement | For the time entered | Would become | If the actual birth time were |
> |---|---|---|---|
> | Moon Rashi | Mesha | Vrishabha | about 1 minute later |
> | Moon D9 Rashi | Dhanu | Makara | about 1 minute later |
> | Moon Pada | Krittika Pada 1 | Krittika Pada 2 | about 1 minute later |
>
> The 2-minute range is a fixed reporting rule applied to every chart. It does not mean that your recorded birth time is wrong. A recorded birth time is usually given to the minute, and is sometimes approximate. If you have an official birth record, you can compare its time with the time on page 4. Nothing in this section changes the placements shown in the rest of this report.
>
> The positions themselves are calculated with Swiss Ephemeris and checked by the engine's own conformance tests. The validation status of those calculations is stated on page 10.

**Expanded, same chart, Hindi.**

> **जन्म समय और यह कुंडली**
>
> यह कुंडली आपके द्वारा दर्ज जन्म समय के लिए गणना की गई है। कुंडली के कुछ भाग दूसरों की तुलना में जल्दी बदलते हैं। लग्न औसतन लगभग हर दो घंटे में अगली राशि में और लगभग हर 13 मिनट में अगले नवांश में जाता है; वास्तविक गति राशि और जन्म स्थान पर निर्भर करती है। चंद्र इससे धीरे चलता है: उसका चरण लगभग हर छह घंटे में और नक्षत्र लगभग दिन में एक बार बदलता है।
>
> यदि वास्तविक जन्म समय दर्ज समय से 2 मिनट तक पहले या बाद का हो, तो नीचे दी गई स्थितियाँ अलग होंगी। यह कोई सुधार नहीं है, और न ही गणना की सटीकता का माप है। यह केवल दिखाता है कि ये स्थितियाँ जन्म समय पर कितनी बारीकी से निर्भर हैं।
>
> | स्थिति | दर्ज समय के अनुसार | बदलकर होगी | यदि वास्तविक जन्म समय हो |
> |---|---|---|---|
> | चंद्र राशि | मेष | वृषभ | लगभग 1 मिनट बाद का |
> | चंद्र की D9 राशि | धनु | मकर | लगभग 1 मिनट बाद का |
> | चंद्र का चरण | कृत्तिका चरण 1 | कृत्तिका चरण 2 | लगभग 1 मिनट बाद का |
>
> 2 मिनट की यह सीमा हर कुंडली पर लागू होने वाला एक निश्चित नियम है। इसका अर्थ यह नहीं है कि आपका दर्ज जन्म समय गलत है। दर्ज जन्म समय प्रायः मिनट तक ही लिखा होता है, और कभी-कभी अनुमानित होता है। यदि आपके पास जन्म का आधिकारिक रिकॉर्ड है, तो उसमें लिखे समय को पृष्ठ 4 पर दिए समय से मिला सकते हैं। इस खंड से इस रिपोर्ट के बाकी भागों में दिखाई गई कोई भी स्थिति नहीं बदलती।
>
> ग्रह स्थितियाँ स्वयं Swiss Ephemeris से गणना की जाती हैं और इंजन के अपने अनुरूपता परीक्षणों द्वारा जाँची जाती हैं। इन गणनाओं की सत्यापन स्थिति पृष्ठ 10 पर बताई गई है।

---

## 7. Cases requiring special handling

| ID | Case | Recommended handling |
|---|---|---|
| S-01 | Both directions trigger for one item (Lagna or D9 Lagna only) | Use the `.both` key, naming both alternatives. The Moon cannot trigger in both directions (its edges are at least 3°20′ apart, more than 100 times its 2-minute motion) |
| S-02 | Several D9 Lagna changes within the window (high latitude) | `note.lagna_navamsa.multiple`; do not list each alternative. Appendix row uses `appendix.cell.multiple` |
| S-03 | One boundary changes several items (a Moon Rashi edge is also a Pada and Navamsa edge; 0°, 120° and 240° are also Nakshatra edges; a Lagna Rashi edge is also a D9 Lagna edge) | Each affected item gets its own note at its own place, and the page-4 summary lists each once. Do not merge them into one long sentence, and do not describe the coincidence as special or significant |
| S-04 | Exact boundary (< 1 s) in one direction and a minute-based change in the other (fast Lagna) | Boundary note for the item; the appendix lists both rows |
| S-05 | Exact boundary where the position is just *before* the edge | `boundary.*` without `boundary.convention` (the half-open rule did not decide it). `{shown}` is the earlier division |
| S-06 | Resolution-limited case (GOLD-E01 style) | Treat as exact boundary. Never print a time in seconds or microseconds |
| S-07 | Printed longitude rounds onto the edge (e.g. 119.999999999996° prints as 120.00000000° but is Karka) | Append `boundary.rounding`. Never change the printed value or the classification |
| S-08 | Daylight-saving gap or fold near the entered time | "Earlier" and "later" mean elapsed time from the resolved UTC instant, not local clock arithmetic. Notes never print an alternative clock time, so no ambiguous local time is ever shown |
| S-09 | The ±2-minute window crosses midnight, a date change or the supported date range limit | The wording is unaffected (it never names a date). Whether the computation may evaluate instants just outside 1970-01-01 to 2100-12-31 is an engineering question for the later task (B6D-Q7) |
| S-10 | Latitude above 60° also triggers the existing engine disclosure `HIGH_LATITUDE_TIME_SENSITIVITY` | Show both: the existing general note keeps its current place and wording; B-6 notes are specific to the items. That engine text says "ascendant" in English; aligning it to "Lagna" belongs to the KUN-I18N review, not this one |
| S-11 | Entered time includes seconds | No wording change. The notes say "time entered", never "the minute entered" |
| S-12 | Name given on the report | No note contains the name. Notes say "your Lagna", never "{name}'s Lagna" |
| S-13 | No item triggers | No note, no tag, no summary and no appendix page. Only the static Methodology row (§3.10) |
| S-14 | Locale switch in the browser | Notes recompute nothing; the same trigger result is shown in the other language with identical numbers |
| S-15 | Existing label mismatch: the web calls D1 the "D1 Rashi chart", the PDF calls it the "D1 Lagna chart" | Notes never name the D1 chart title, so they are correct with either. The mismatch itself is outside this task and is reported for the KUN-I18N review |

---

## 8. Open decisions for the owner (not decided here)

| ID | Question | Recommendation |
|---|---|---|
| B6D-Q1 | Exact-boundary threshold | < 1 s of time, or resolution-limited |
| B6D-Q2 | Rounding of the time shown | Three buckets: less than a minute, about 1 minute, about 2 minutes (§3.0) |
| B6D-Q3 | Where the optional appendix appears | Premium edition only, as a conditional page after Methodology; the standard ten-page report gets only the short notes (see `DESIGN-INTEGRATION.md` §4) |
| B6D-Q4 | Hindi label | जन्म समय टिप्पणी (§4 G-09) |
| B6D-Q5 | Include the Moon D9 Rashi message (SCI-06 item not in the task list) | Yes |
| B6D-Q6 | Include `summary.record` (the general sentence about birth records) | Yes, subject to the language reviewer |
| B6D-Q7 | Evaluate instants outside the supported date range inside the window | Engineering task to propose; no wording impact |

---

## 9. What this packet does not do

It changes no calculation, schema (0.3.0), metadata (`/3`), reference data, tolerance, renderer, catalog, PDF, interface, private preview, Shopify, DNS or infrastructure. It adds no code that any application loads. It marks no wording as reviewed or approved. Implementation needs its own authorized task with separate ENG and RPT gates, after the human reviewers and the owner have signed [`SIGNOFF-SHEET.md`](SIGNOFF-SHEET.md).
