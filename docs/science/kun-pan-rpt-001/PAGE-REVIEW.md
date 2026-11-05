# KUN-PAN-RPT-001: page-by-page review of the extended edition

**Status: developer self-review for independent QA. Not owner-approved. Not a QA verdict.**

Reviewed on synthetic scenarios s07 (noon), s01 (first supported date), s12 (morning) and s02 (last supported
date, local times withheld), in English and Hindi, with and without a name. I also reviewed the live London
summer-time sample. The goal is a richer Janma Kundali, not a longer PDF. Each page is judged on what it adds
that the ten-page report does not already give.

## Edition structure (13 pages)

| Page | Content | Source |
|---|---|---|
| 1, 3–9 | Cover, reading guide, birth details, D1 and D9 charts, planetary positions, Navamsa placements, house directory: drawn by the unchanged functions | unchanged |
| 2 | Overview and contents: the same design, with three more rows, a tighter row step and the 13-page total | page plan |
| **10** | **Panchanga at the moment of birth** | M1 document |
| **11** | **When each value began and ended** | M1 document |
| **12** | **Panchanga method and limits** | M1 method block and provenance |
| 13 | Methodology and provenance (the former page 10). "Included" adds "Panchanga at birth, pages 10 to 12"; "Not included" adds "Sunrise-based daily Panchang" | page plan |

The ten-page edition remains the default and is byte-identical to main `07da75e`: 156 of 156 variants match.

## Page 10: Panchanga at the moment of birth

**What it gives:**
- Six cards: Tithi (n of 30, Paksha day), Paksha, Karana (n of 60), Yoga (n of 27), Moon Nakshatra and Pada, and elongation E with the sum S.
- A 30-segment Tithi ring with the birth marker.
- Plain EN/HI definitions of each limb.
- A boxed statement: "birth instant, not the calendar day".

**Completeness.** It shows every element M1 computes. Vara is the fifth limb, and it is missing because it
needs sunrise (PAN-D03/D05, pending). The intro and the box both say so.

**Readability.** Each card leads with one large value and one short qualifier. The definitions are one or two
sentences. Each card has a page cross-reference to its transition time.

**Duplication.** Moon Nakshatra and Pada also appear on page 7 (planetary positions). They are kept here because the
Nakshatra is one of the five limbs, and the page says "the same values as page 7".

**Usability.** The box explains why a printed Panchang for the birth date can differ from this page. This is
the most likely customer question.

**Issues found and fixed:**
- Hindi used चरण ("step") for the 12° divisions of the ring caption and the method page. On the same pages,
  चरण also means Pada. It is now भाग, so चरण keeps one meaning only.

**Open (for editorial or owner review, not fixed here):**
- E and S are printed to eight decimals, which matches the chart's own longitude precision. A customer-friendlier form, such as degrees and minutes, would be a copy decision.
- The ring shows positions, not names. Names wait for D16.

## Page 11: When each value began and ended

**What it gives:**
- A table of the five spans (Tithi, Karana, Yoga, Nakshatra, Pada). Each span shows its local start and end, with UTC and the offset under each.
- A timeline of the spans relative to the birth instant.
- A note on how the times are found.

**Completeness.** It shows every M1 instant. Times outside the D13-A envelope (1970–2100) are shown as "Local time not shown", with the UTC instant always given (s02). When a span crosses a clock change, a note says so (London sample).

**Readability.** Each cell has two lines: local time in front, UTC beneath.

**Duplication.** None.

**Usability.**
- The table answers "when did my Tithi or Nakshatra begin and end?".
- The timeline shows at a glance which values changed close to birth.

**Issues found and fixed:**
- The timeline gave no length for each span. Each bar now has its length next to the name, for example "Tithi 21 h 15 m".
  - The length is calculated from the UTC instants, so a span that crosses a summer-time change is not off by an hour.
  - New tests check the lengths for all 13 scenarios in EN and HI, and that a span crossing the London change is one hour shorter than its wall-clock difference.
  - Hours and minutes are truncated, and the seconds are in the table.
- The Hindi axis note left one word on a second line. The note is now shorter.

**Open (owner decision posted in the thread):**
- Times are printed to the second, as in the M1 document. The page says that a second is resolution, not accuracy.
- The local display rule and a ±2 min near-boundary flag were deferred under D09-A-M1.
- The proposal below carries both into M2.

## Page 12: Panchanga method and limits

**What it gives:**
- Eight method rows: positions, Tithi and Paksha, Karana, Yoga, Nakshatra and Pada, boundaries, time scale, and data.
- The validation status `ENGINEERING_UNVERIFIED_PENDING_INDEPENDENT_QA`, with its claim boundary.
- Included and excluded lists.

**Completeness.**
- The data row ties this page to the M1 document: schema, method, Swiss version, ephemeris manifest, tzdata and the call count.
- The page names the method choices that the M1 decisions fixed.

**Duplication.** Some overlap with page 13 is intentional:
- The positions and time-scale rows say "the same as the chart" instead of repeating the chart's settings.
- The two validation statuses are different claims, so both are kept: `UNVERIFIED_GOLDEN_CHARTS` covers the chart, and M1's status covers the Panchanga.

**Usability.** This page is mainly for QA and for informed buyers. The excluded list tells customers what is
not in the report, which helps prevent misreading.

**Issues found and fixed:**
- In Hindi, "step" is now भाग in the method rows and in the boundary rule (see page 10).

## Should the edition be four or five pages longer?

**No, not with M1.** M1 provides:
- the values at the birth instant;
- one span per element;
- the method and provenance blocks.

All of these are on pages 10–12. Candidate extra pages were considered and rejected:

| Candidate | Why not now |
|---|---|
| Neighbouring Tithis, Nakshatras or Yogas before and after birth | M1 does not compute them. Adding them would be a new calculation outside the accepted method |
| A full 30-Tithi, 27-Yoga or 60-Karana reference table | Without names (D07-A, D16-M1-INDEX) it would be a list of numbers: pages without value |
| Daily Panchang for the birth date (sunrise values, Vara) | Needs sunrise (PAN-D03/D04/D05/D06/D11/D17, all pending) |
| Masa and Samvat | Out of M1 scope (PAN-D19) |

The fourth and fifth pages belong to M2. Its outputs make them worthwhile, and the proposal sets out a plan for
each: verified names on pages 10–11, sunrise and sunset with Vara, the birth-date daily Panchang, and Masa and
Samvat.

## Hindi review

All new Hindi is a developer draft. `docs/i18n/PANCHANGA-REPORT-TERMS.md` lists nine items for the human
Hindi editor. Shaping, fonts, minimum size and overlap are checked automatically on every page. Language and
Jyotish terminology are not, and they still need human editorial review.
