# Panchanga milestone M1: birth-instant limbs (proposal)

**PROPOSAL. NOT AN IMPLEMENTATION AUTHORIZATION.** Every SCI-PAN-01 decision is still PENDING. M1 is the sunrise-independent first step recommended in PR #63 `NEXT-MODULE-ROADMAP.md` §3, and it narrows the [WP-B2 handoff draft](../WP-B2-PANCHANGA-ENGINEERING-HANDOFF-DRAFT.md) to what verified reference evidence can support today.

## 1. Scope

| In M1 | Definition (SCI-PAN-01 rev 0.5, on `main` `1d4bcb6`) |
|---|---|
| **Tithi** at the birth instant: 1 to 30, plus Paksha and day 1 to 15 (PAN-D18) | E = (λ☾ − λ☉) mod 360; index ⌊E / 12°⌋ + 1 |
| **Karana index** at the birth instant: 1 to 60, **without names** (PAN-D07 option A) | ⌊E / 6°⌋ + 1 |
| **Yoga index** at the birth instant: 1 to 27 | S = (λ☾ + λ☉) mod 360, on sidereal longitudes; ⌊S / 13°20′⌋ + 1 |
| **Nakshatra and Pada** | Must equal the chart's `moon_nakshatra` for every request (PAN-QA-08) |
| **Start and end instants** of the current Tithi, Karana, Yoga and Nakshatra | TS-1 bounded bracketing and bisection, converged to ≤ 0.5 s, `FLG_SWIEPH` checked on every call (PAN-D10). Machine output in UTC to the second; local display rounded to the minute (PAN-D09) |

All of these are functions of the Sun and Moon longitudes, which are already canonical (SCI-01d, SCI-01a). None needs a location, a sunrise or any new astronomical convention. Boundaries are half-open on unrounded values (PAN-D08).

**Not in M1:** Vara, sunrise and sunset, the sunrise-day Panchanga, Kshaya/Adhika handling, Masa and Samvat (PAN-D19), Karana and Yoga names, Hindi labels, any report text, any customer-facing output.

**Output.** A separate `sabpuja-panchanga/1` document (PAN-D12 option A). Chart schema 0.3.0 and calculation metadata `/3` stay byte-identical.

## 2. Reference evidence available now

| Set (on `main`) | sha256 | Class | What M1 can prove with it |
|---|---|---|---|
| PAN-REF-PHASE-2026, `research/panchanga/reference-fixtures/geocentric-lunar-phase-events-2026.json` | `dfd964cf…9850` | **Independent.** 50 events, all `VERIFIED_TWO_INDEPENDENT_PUBLISHERS` (USNO API 4.0.1 and NASA/Espenak). 42 identical; 8 differ by 1 minute, with NASA later. Whole minutes, rounding rule unstated | E = 0° (12 New Moons: Tithi 30→1, includes the 0/360 wrap) and E = 180° (13 Full Moons: Tithi 15→16). These 25 are also Karana boundaries. E = 90° and 270° (25 quarters) are Karana-only boundaries. **Ayanamsa-free**, because Sun and Moon share the same ayanamsa at the same instant. Minute-level agreement only, not seconds-level accuracy |
| PAN-DER-2026 cases 07 and 08 | see below | Derived from the phase set, labelled DERIVED | UT/IST civil-date rollover of a Tithi boundary; a Karana boundary 30 minutes after local midnight |
| PAN-SPEC-BOUNDARY 01–06, 08–10, 12–15 | see below | Specifications, no numbers | Exact boundaries, the 0/360 wrap, Karana rollover, search caps and non-convergence refusal, refusal order, ephemeris failure, Swiss state isolation |
| Swiss CLI conformance (REL-01 mandatory) | — | Swiss-on-Swiss | swetest Sun and Moon at the same instants. The gold matrix from PR #62 (50 charts) can be reused as instants, through an independently coded rule oracle for E, S and the indices |

Derived set sha256 and specification set sha256 are listed in [QA-HANDOFF.md](QA-HANDOFF.md).

**Not yet available (stated, not filled in).**
- No independent reference for any **Yoga** or **Nakshatra** end time. These depend on the ayanamsa, and none has been obtained. M1 can therefore check Yoga only through the rule oracle plus Swiss conformance, and Nakshatra only through identity with the chart, which is itself Swiss-on-Swiss.
- Only two of the 30 Tithi boundary angles (0° and 180°) and four of the 60 Karana angles have independent events. The rule is uniform in E, so the oracle covers the other angles. That is a rule check, not an independent reference.
- IMD Rashtriya Panchang: 46 reviewer-collected candidates, **Stage C 0 of 46, Stage D 0 of 46**. They are not used in M1. PR #48 is not used.

**No comparison has been run.** PAN-D15 requires that tolerances be fixed and committed before any evaluation run. So this proposal does not compute an engine or Swiss result against the 50 events, and it reports no agreement figure.

## 3. Owner decisions M1 needs (all PENDING)

| Decision | Recommended option in SCI-PAN-01 | What M1 needs |
|---|---|---|
| PAN-D01 longitude frame | A: reuse SCI-01d | Required |
| PAN-D02 outputs | A, birth-time primary | Only the birth-time part. The daily Panchanga stays out |
| PAN-D07 Karana names | A: index only until a primary source is adopted | Required (index only) |
| PAN-D08 boundary rule | A: half-open, exact, unrounded | Required |
| PAN-D09 precision and display | A: ≤ 0.5 s convergence, UTC to the second, local display to the minute | Required. Its "±2 min near-boundary flag" overlaps SCI-06; see below |
| PAN-D10 numerics | A: TS-1 bisection | Required |
| PAN-D12 output contract | A: separate `sabpuja-panchanga/1` | Required |
| PAN-D13 instants outside the envelope | A: report UTC, withhold local rendering | Required (transition instants can fall outside the SCI-03 envelope) |
| PAN-D14 reference hierarchy | A | Required |
| PAN-D15 tolerances | Provisional A: phase events within [min published − 60 s, max published + 60 s] | **Only the phase-event part**, fixed before any run. The IMD and sunrise parts stay open |
| PAN-D16 names | A now | Either Tithi/Paksha names per Appendix A in English only, or indices only in M1. Recommended: indices and Paksha only, so that no name is shipped before OD-08 review |
| PAN-D18 Tithi numbering | A: both 1–30 and Paksha + 1–15 | Required |
| **PAN-D20, scoped** | A: WP-B2 blocked until IMD is verified | **New scoped question.** May M1, and only M1 (the sunrise-independent subset), proceed on the USNO/NASA events plus Swiss conformance, while everything sunrise-dependent stays BLOCKED until IMD Stage C/D? Recommended: yes, because these limbs are ayanamsa-free (Tithi, Karana) or already chart-verified (Nakshatra), and the claim is limited to minute-level agreement |

**SCI-06 interaction.** SCI-06 covers six chart items only. Applying a ±2 min sensitivity note to the Tithi, Karana, Yoga or Nakshatra end times would be an extension of SCI-06 and needs its own owner decision. It is not assumed here.

PAN-D03 to D06, D11, D17 and D19 are not needed for M1 and stay open.

## 4. Proposed acceptance (ENG gate only)

Every test must pass on the exact SHA, with raw logs, and then go to independent QA:

| ID (WP-B2 §11) | M1 check |
|---|---|
| PAN-QA-01 | Rule oracles for Tithi, Karana index, Yoga and Nakshatra/Pada; exact half-open boundaries; the 0/360 wrap (PAN-SPEC-01 to 05) |
| PAN-QA-03 | Transition search: convergence ≤ 0.5 s, caps, typed refusal on non-convergence (PAN-SPEC-06, 14) |
| PAN-QA-04 | All 50 phase events: the engine crossing instant lies inside the PAN-D15 window fixed beforehand, and the Tithi/Karana index is correct on both sides. A pass means "within the declared window", never "accurate to 0.5 s" |
| PAN-QA-07 | swetest conformance for Sun and Moon at the same instants, under a tolerance the owner has approved for this use (the SCI-05 scope covers only the gold matrix; reuse for Panchanga is a separate scope question) |
| PAN-QA-08 | Chart 0.3.0 byte identity with and without a Panchanga call in the same process; Nakshatra identity; metadata `/3` unchanged |
| PAN-QA-09 | Refusal order and codes match the chart (PAN-SPEC-09, 10, 12, 13); no birth data in errors or logs |
| PAN-QA-10 | Determinism across runs, processes and locales; Swiss state isolation (PAN-SPEC-15) |
| PAN-DER-07, -08 | Civil-date rollover and the post-midnight Karana boundary |

Not part of M1: PAN-QA-02 (names), PAN-QA-05 (sunrise), PAN-QA-06 (IMD), PAN-QA-11 (performance, waiting on PERF-01).

## 5. Preconditions and base

1. The owner records the §3 decisions under the two-step rule.
2. PAN-D15's phase-event tolerance is committed **before** the first evaluation run, and ChatGPT reviews it.
3. The engine base SHA is fixed, or the owner decides the OD-09 merge plan. M1 must not stack on an unresolved branch without that plan. PR #1 HOLD stays active.
4. ChatGPT issues a numbered, bounded task (for example KUN-PAN-M1) with KUN-A01 and QA links.

## 6. Claim boundary

M1 would give an independent check that Tithi and Karana transitions agree with USNO and NASA to the minute. It would give a Swiss-on-Swiss conformance check for the rest. It would not support any claim of independent astronomical accuracy (JPL/INPOP stays deferred), any IMD-equivalence claim, or any customer-facing Panchanga text.
