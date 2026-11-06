# Panchanga names: verification and open review items (KUN-PAN-M2-NAMES-001)

**Status: developer draft for independent QA. Mappings source-checked; display forms pending human
review; not customer-facing; not owner-approved.** Issue #80, stacked on draft PR #79 (`f26dd10`).

## What changed

| Area | Change |
|---|---|
| `report/phase1/panchanga_names.json` | New catalog: 16 Tithi names, 11 Karanas, 27 Panchanga Yogas, each with a stable machine id, the IMD spelling as printed (plus alternates seen on daily pages), proposed English and Hindi display forms and three review layers. Index maps Tithi 1-30, Karana 1-60, Yoga 1-27. Customer release `PENDING`. |
| `report/phase1/panchanga_names.py` | Lookups that fail closed (index range, `bool`/float/str, unknown element, locale, missing or mistyped term, malformed catalog) and the release gate. |
| `panchanga_report.py`, `premium_report.py` | Optional `names=` argument of `generate_extended`. `None` (default) is the M1 display, byte for byte. `'qa_preview'` draws names on the existing cards, transition table and method page, with a "QA PREVIEW, NOT FOR CUSTOMERS" notice on all three Panchanga pages and in the PDF subject. `'customer'` is refused. CLI: `--names-qa-preview` (needs `--panchanga-json`). No page added. |
| Evidence | `research/panchanga/names/imd-names-evidence.json`; `SOURCE-REGISTER.md` section 6; generated `PANCHANGA-NAMES-CROSSWALK.md`. |
| Unchanged | `sabpuja-panchanga/1` contract and M1 module, chart schema 0.3.0, D1/D9, ten-page catalog and output, the M1 page catalog `report_panchanga_i18n.json`, nearest-minute display, preview server, sunrise conventions, validation status. |

## How each mapping was verified

1. **Tithi.** IMD names page: 1-14 the same in both Pakshas, 15 Purnima, 30 Amavasya. The IMD daily
   month prints 31 consecutive Tithis (Shukla Dvadashi to Shukla Dvadashi) with these names and
   Pakshas, all 30 slots included.
2. **Karana.** The IMD names page alone does not fix the slots. Two independent checks do:
   * the explanation page rule (7 repeating from the 2nd half of Shukla Pratipada to the 1st half of
     Krishna Chaturdashi, 4 fixed from the 2nd half of Krishna Chaturdashi to the 1st half of Shukla
     Pratipada) applied to the printed order gives 1 Kimstughna, 2-57 Bava to Vishti eight times,
     58 Shakuni, 59 Chatushpada, 60 Naga;
   * the IMD daily month prints 61 consecutive Karanas. Every printed Tithi ending time equals the
     ending of exactly one Karana, its 2nd half (31 of 31), which fixes the slot of every Karana. All
     60 slots are observed and every printed name matches the rule.
3. **Yoga.** IMD names page order, Yoga 1 ending at 13°20′ of the nirayana sum (explanation page).
   The daily month prints one consecutive cycle through all 27, wrapping Vaidhriti to Vishkambha.
4. **Live cross-check** (pinned ephemeris): at the middle of every IMD-printed span of the month,
   the engine's own M1 index names the element IMD printed (Tithi, Karana and Yoga). This checks
   that the engine's index and the IMD name agree; it is not used as the reference.
5. **Mutation check**: swapping Karanas 58/59 or Yogas 16/21 in the catalog fails all three checks.

## Held, not adopted

* **All display forms** (English and Hindi, Paksha prefixes, the Karana kind words) are developer
  proposals. Every entry is `PENDING_HUMAN_REVIEW` for English display, Hindi display and Jyotish
  terminology. Customer output therefore keeps the numeric M1 display.
* **Source reread.** The IMD facts were read by Claude's page-reading tool, not by a second person
  (Stage C). QA should reopen the three pages and compare the evidence file.
* **Rights.** IMD pages are "All Rights Reserved"; only minimal facts are recorded. Whether names
  may be cited as "IMD Rashtriya Panchang order" on the customer method page needs owner review.

## Items for the human Hindi and Jyotish reviewers

1. Hindi spellings with common variants: विष्कम्भ / विष्कुम्भ / विष्कंभ, अतिगण्ड / अतिगंड, गण्ड / गंड,
   इन्द्र / इंद्र, आयुष्मान / आयुष्मान्, वरीयान / वरीयान्, पंचमी / पञ्चमी, किंस्तुघ्न.
2. English transliterations: Vanija (IMD Vanij), Shakuni (Sakuni), Chatushpada (Chatuspada),
   Kimstughna (IMD names page) versus Kinstughna (IMD daily page), Vishkambha (Viskumbha),
   Dvitiya/Dwitiya, Dvadashi/Dwadashi, Variyan/Variyana.
3. Paksha prefix in a Tithi name: "Shukla Ekadashi" / "शुक्ल एकादशी"; Purnima and Amavasya alone.
4. Karana kind words "repeating"/"fixed" and चर/स्थिर; whether to show the kind at all.
5. Vishti is also known as Bhadra (भद्रा); the catalog shows only the IMD name.
6. "Panchanga Yoga" / "पंचांग योग" as the subtitle that keeps it apart from planetary Yogas.
7. The QA notice text itself is removed when names are released; customer copy needs owner review.

A reviewer decision is recorded by changing an entry's `review` layer to `ACCEPTED`, `REVISED` or
`REJECTED` with the GitHub record; customer display needs every layer `ACCEPTED` and
`customer_release` `APPROVED` with a GitHub issue or PR record of the owner's chat decision.
