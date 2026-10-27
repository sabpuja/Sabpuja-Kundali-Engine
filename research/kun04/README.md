# KUN-04 provisional pure mathematics spike

Status: **EXPERIMENTAL / NON-CANONICAL / DO NOT IMPORT FROM ENGINE OR PDF**. Draft science choices in PR #47 are not owner-approved.

This isolated folder proves exact rational boundary behavior for prospective five-limb Panchanga indices and *nominal* Vimshottari proportions. It intentionally does **not** calculate Swiss Sun/Moon coordinates, rise/set, the named Karana sequence, calendar start/end dates, Dasha timestamps, predictions, new chart schema or PDF text.

- `provisional_math.py` classifies half-open segments into tithi 1..30, half-tithi slot 1..60, sidereal nakshatra 1..27 and pada 1..4, yoga 1..27. It has no traditional regional names or civil/sunrise weekday semantics.
- It also computes natal Moon nakshatra lord, remaining fractional **nominal years** and relative lengths for 9 subperiods using the provisional 120-year weights. Actual calendar dasha dates cannot be inferred without selecting and independently testing a year basis and timescale.
- Fraction-based arithmetic makes exact boundary tests (e.g., 40/3 degrees) possible without binary floating-point ambiguity. Real Swiss precision/runtime conversion/rounding have not yet been incorporated.
- Tests assert 30 tithi, 60 half-tithi, 108 pada, 27 yoga and 27 starting dasha boundary cases, wraparound, invalid inputs and contiguous abstract subdivisions. They are not golden-chart validation.

### Local test
From repository root: `python -m unittest discover -s research/kun04/tests -v`

### Scientific release blocking items
1. Independent historical/full reference vectors for all five Panchanga limbs and sunrise.
2. Karana name sequence, sunrise/vara, Sidereal lunar/solar flag choices, rise/set rule and exact event-boundary solvers.
3. Dasha calendar-year convention and nested period/date arithmetic, independent timeline verification.
4. Owner approval recorded separately without overwriting historical decisions.
5. Engineering and Report-Quality gate independent signoffs.

The prototype must never be shipped, imported into `src/`, used for a real client report or claimed as a Kundali-feature implementation before those items are resolved.
