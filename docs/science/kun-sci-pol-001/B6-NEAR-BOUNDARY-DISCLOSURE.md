# B-6: Near-boundary handling in Kundali reports

**PROPOSAL. PENDING OWNER APPROVAL.** This document changes no calculation convention and no customer-facing report. All English and Hindi wording below is a **draft for later human editorial and Jyotish review**. It is not approved copy.

## 1. Two different kinds of near-boundary uncertainty

| Kind | Cause | Size | Example |
|---|---|---|---|
| **Numerical** | The reference and the engine cannot be told apart near an edge at the frozen band (B-3: 1e-9°) | Below 1e-9°, which is a few microseconds of Moon motion or less | GOLD-E01 |
| **Birth-time** | The customer's birth time is recorded to the minute at best and is often uncertain by several minutes. Classifications that change within that window are not determined by the data | Lagna moves about 0.14° to 1.0° per minute in the matrix (median 0.23°) and up to about 10.6° per minute at the edge of the ±66° band. The Moon moves about 0.008° to 0.011° per minute | Lagna Navamsa often changes within a few minutes |

The second kind is far larger and far more common. A disclosure policy based only on the 1e-9° numerical band would essentially never trigger, yet it would leave customers unaware of the uncertainty that matters. The recommendation below therefore treats them separately.

## 2. GOLD-E01 and the six indeterminate comparisons

GOLD-E01 is a synthetic New Delhi chart at `2008-01-24T09:31:02.327269+05:30`. It was designed with the Moon a few microseconds of time from the 120° edge. 120° is simultaneously the Karka/Simha Rashi edge, the Ashlesha/Magha Nakshatra edge, a Navamsa edge and a Pada edge.

- swetest Moon: `120.00000000071`. That is **7.1e-10°** past the edge: **extremely close to the boundary, well below one second.** The exact crossing time is unresolved at this numerical precision. A linear estimate (edge distance ÷ local Moon rate of 1.56e-4° per second) is about 4.5e-6 s. However, the birth instant is itself a float64 Julian date with a spacing of about 4.0e-5 s, so neither the instant nor a bisection on it resolves a separation that small. `analysis/results.json` therefore marks these GOLD-E01 values `RESOLUTION_LIMITED` instead of giving a measured time.
- The engine classifies on the unrounded value by the canonical half-open rule (SCI-01f): Simha, Navamsa Mesha, Magha Pada 1. The reference rules on the swetest value give the same results.
- The engine's displayed 8-decimal longitude is `120.0`.
- The six rows are `BOUNDARY-INDETERMINATE` only because the reference value lies within the 1e-9° band:
  1. `moon.rashi`
  2. `moon.navamsa_rashi`
  3. `moon.whole_sign_house`
  4. `moon.navamsa_whole_sign_house`
  5. `moon_nakshatra` (Nakshatra and Pada)
  6. the D9 North Indian cell list
- **No defect is involved.** The engine and the reference agree, and the band says only that agreement this close to an edge cannot be proven. Any band below 7.1e-10° would make the case decidable. Every band from 7.1e-10° to 2.4e-4° leaves it as the only indeterminate case (B-3 §2.2).

## 3. How often birth-time sensitivity occurs

The estimate below is **illustrative**. It is not a population prevalence, and it is not a rate of inaccurate birth records. It uses 20,000 synthetic instants, uniform over 1970 to 2100 UTC, at the matrix's 19 chart coordinates. The seed is 20261103 and the method is linear-rate time-to-edge from pyswisseph with the SCI-01 flags (see `analysis/results.json`, `B6.random_sample`). Each cell is the share of charts in which **a birth-time error up to N minutes in one direction** would change the item.

| Item (edge spacing) | ±1 min | ±2 min | ±5 min | ±15 min |
|---|---|---|---|---|
| Lagna Rashi (30°) | 1.7% | 3.5% | 8.4% | 24.5% |
| Lagna Navamsa / Pada (3°20′) | 14.7% | 29.4% | 69.9% | 100% |
| Lagna Nakshatra (13°20′) | 3.9% | 7.6% | 18.6% | 53.6% |
| Moon Rashi | 0.06% | 0.13% | 0.33% | 0.89% |
| Moon Navamsa / Pada | 0.59% | 1.1% | 2.8% | 8.1% |
| Moon Nakshatra | 0.19% | 0.32% | 0.76% | 2.1% |

In the designed matrix, which is biased toward edges, the median time to the nearest Lagna Navamsa change is 173 s, and 8 of 50 charts change within 60 s (`B6.per_chart`). The Moon statistics there use n = 49, because GOLD-E01's Moon times are `RESOLUTION_LIMITED` and are excluded rather than given a measured value. The slow planets change Rashi or Navamsa over days to months, so this mostly concerns the Lagna, which drives every house, and the Moon.

## 4. Customer-experience options

All three options keep the engine's classification as calculated (half-open rule, SCI-01f) unless the option says otherwise. A trigger would compare the time to the nearest change of each item with a window W (proposed: 2 minutes for every item; owner choice). Exact-edge numerical cases (§1, first row) always trigger.

| | Option 1: short disclosure | Option 2: expanded explanation | Option 3: withhold |
|---|---|---|---|
| What the customer sees | The result, plus one short line next to the affected item | The result, plus a dedicated "Birth-time sensitivity" section: what changes, by how many minutes, and what the alternative would be | For affected items, no classification; a statement that it cannot be determined, and a prompt to check the birth time |
| Usability | High. Charts stay complete | Medium. Longer, but answers the obvious follow-up questions | Low. A Lagna Navamsa would be withheld in about 29% of charts at W = 2 min. A withheld Lagna Rashi hides every D1 house |
| Customer trust | Honest and lightweight. Some customers will want more detail | Highest transparency. Risk of over-emphasis | Appears unreliable. It suggests the calculation failed when only the input is uncertain |
| Scientific fit | Matches the evidence: the result is correct for the entered time, and only the input is uncertain | Same as Option 1, plus it shows the alternative | Treats input uncertainty as a calculation refusal, which REL-01 and SCI-01f do not require |

**Recommended: Option 1** in the chart and PDF, with Option 2's longer explanation available as an optional appendix page in the premium report. Option 3 is not recommended, except as a possible future rule for a numerical exact-edge case where the owner prefers withholding. Even GOLD-E01 has a well-defined canonical answer.

The default windows are an owner choice:
- **W = 2 minutes** for the Lagna Rashi, the Lagna Navamsa, and the Moon Rashi, Navamsa, Nakshatra and Pada (the recommendation). It roughly matches minute-level birth records.
- Alternatives are W = 1 minute (fewer notes: about 15% of charts flag the Lagna Navamsa) or W = 5 minutes (about 70%). Figures are from the table in §3.

## 5. Draft disclosure wording (EN and HI)

**DRAFT. Requires human Hindi editorial review, Jyotish terminology review and owner copy approval before any use.** `{…}` marks a value inserted from the chart. The catalogues in PR #59 to #61 are not changed.

| Case | English draft | Hindi draft |
|---|---|---|
| Lagna Rashi | Birth-time note: your Lagna is about {m} minutes from changing from {A} to {B}. If your birth time could differ by that much, the Lagna and every house in the D1 chart could differ. | जन्म-समय सूचना: आपका लग्न {A} से {B} में बदलने से लगभग {m} मिनट दूर है। यदि आपके जन्म-समय में इतना अंतर संभव है, तो लग्न और D1 कुंडली के सभी भाव बदल सकते हैं। |
| Lagna Navamsa | Birth-time note: your D9 (Navamsa) Lagna would be {B} instead of {A} if you were born about {m} minutes {earlier/later}. | जन्म-समय सूचना: यदि जन्म लगभग {m} मिनट {पहले/बाद} होता, तो आपका नवांश (D9) लग्न {A} के स्थान पर {B} होता। |
| Moon Rashi | Birth-time note: the Moon was about {m} minutes from moving from {A} into {B}. | जन्म-समय सूचना: चंद्रमा {A} से {B} राशि में जाने से लगभग {m} मिनट दूर था। |
| Moon Nakshatra / Pada | Birth-time note: the Moon was about {m} minutes from moving from {N} Pada {p} to {N2} Pada {p2}. | जन्म-समय सूचना: चंद्रमा {N} नक्षत्र के {p} चरण से {N2} के {p2} चरण में जाने से लगभग {m} मिनट दूर था। |
| Exact boundary (numerical) | This position lies exactly on the boundary between {A} and {B}, within one second of birth time. By the standard rule, a boundary point belongs to the sign that begins there, so it is shown as {B}. | यह स्थिति {A} और {B} की ठीक सीमा पर है (जन्म-समय के एक सेकंड के भीतर)। मानक नियम के अनुसार सीमा-बिंदु उस राशि का माना जाता है जो वहाँ से आरंभ होती है, इसलिए इसे {B} दिखाया गया है। |
| Option 2 section intro | Some parts of a Kundali change quickly. The Lagna moves through a whole sign in about two hours, and through each Navamsa in about 13 minutes on average. This chart is calculated exactly for the time you entered. The items below would differ if the true birth time were a few minutes earlier or later. | कुंडली के कुछ भाग जल्दी बदलते हैं। लग्न लगभग दो घंटे में एक पूरी राशि और औसतन लगभग 13 मिनट में एक नवांश पार करता है। यह कुंडली आपके दर्ज किए गए समय के लिए ठीक-ठीक गणना की गई है। यदि वास्तविक जन्म-समय कुछ मिनट पहले या बाद का हो, तो नीचे दिए गए अंश अलग हो सकते हैं। |
| Option 3 (not recommended) | Your {item} cannot be stated reliably for this birth time, because it changes within {m} minutes. Please check the recorded birth time. | इस जन्म-समय के लिए आपका {item} विश्वसनीय रूप से नहीं बताया जा सकता, क्योंकि यह {m} मिनट के भीतर बदल जाता है। कृपया दर्ज जन्म-समय की जाँच करें। |

The wording avoids fear-based or predictive claims (UX-03) and describes only the effect on the calculation.

## 6. Implementation implications if approved

Each of these needs its own authorized task, ENG gate and RPT gate:
1. **Calculation.** A new, versioned "boundary sensitivity" computation: time to the nearest change for each covered item, by bracketing and bisection on the canonical functions, using the SCI-01d/SCI-01e calls. The Moon is monotonic. The Lagna is monotonic per sidereal day within the band, but it needs care above about 60°.
2. **Schema.** An additive field in a new chart schema version (proposed 0.4.0) or in report-only metadata. Schema 0.3.0 is unchanged.
3. **Report.** Renderer lines (Option 1) and an optional appendix (Option 2) in EN and HI, plus catalogue entries.
4. **Not affected.** The classification rules, the half-open convention and all existing values.

## 7. Tests required after approval
- **Bracketing and bisection.** Times to edge checked against independent bisection on swetest values at designed boundary pairs (GOLD-B01 to B10 style), with a stated time tolerance in stated units. The time arithmetic must declare its resolution: a single float64 JD resolves only about 4e-5 s. Results finer than that must be reported as resolution-limited, never as a measured time.
- **Windows.** The trigger fires at exactly W and not at W plus 1 s, in both directions, for the Lagna at low and high latitude (including ±66°) and for the Moon.
- **GOLD-E01.** It must trigger the exact-boundary text and keep Simha, Mesha, Magha 1.
- **No side effects.** Classifications and degrees stay byte-identical to schema 0.3.0 outputs on all 50 charts. EN/HI key parity, PDF fidelity and no PII in logs.
- **RPT gate.** Hindi editorial sign-off, owner copy sign-off and an accessibility check of the note placement.
