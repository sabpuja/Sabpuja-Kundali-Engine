# SCI-PAN-01: Panchanga method decision proposal

**PROPOSED — NOT CANONICAL — OWNER SCIENTIFIC-METHOD APPROVAL PENDING**

| Field | Value |
|---|---|
| Document | SCI-PAN-01 proposal, revision 0.5 (revised for ChatGPT reviews 5679285841, 5679456114 and 5680023508, the reviewer-mediated IMD evidence in PR #51 comment 6464388772, and the owner-authorized final source-validation pass) |
| Work package | WP-B1 (roadmap Workstream B), proposed requirement KUN-A01 Birth Panchanga, proposed milestone KUN-P1-ADV |
| Owner decision it prepares | OD-06 (PRD section 14) |
| Prepared by | Claude (Lead Developer), 2026-10-28 |
| Baseline | `main` `5395d2bc33847d1363e6d838f6109bad552221e3` (merge of PR #50) |
| Review | ChatGPT independent scientific-method review, then owner selection |
| Authorizes | Nothing. No implementation, schema change, merge, deployment or adoption |

Companion files:
- [WP-B2 engineering handoff draft](WP-B2-PANCHANGA-ENGINEERING-HANDOFF-DRAFT.md)
- [Source and provenance register](../../research/panchanga/SOURCE-REGISTER.md)
- [Reference fixtures](../../research/panchanga/reference-fixtures/README.md)
- [Package index and QA receipt](../../research/panchanga/README.md)

## 1. Summary

The five Panchanga limbs at a birth instant (Tithi, Nakshatra, Yoga, Karana and, with one caveat, Vara) are functions of the **geocentric** Sun and Moon longitudes at that instant. They need no sunrise and no observer location. They can reuse the canonical SCI-01d Sun and Moon longitudes unchanged, so no new coordinate convention is required.

Sunrise enters in only two places: the traditional **sunrise-to-sunrise Vara**, and the separate **sunrise-based daily Panchanga** (the elements in force at local sunrise). Sunrise is therefore the main new scientific choice, and the one this package could least verify independently.

Main findings:

1. **Frame.** Tithi and Karana depend only on the Moon−Sun elongation, which is the same in the tropical and sidereal frames. Nakshatra, Pada and Yoga depend on the Lahiri ayanamsa; Yoga depends on it twice (Sun + Moon), so an ayanamsa error enters Yoga with double weight. Reusing SCI-01d exactly is proposed (decision PAN-D01).
2. **Sunrise.** Three candidate conventions are compared (section 5.6.1). The astronomical one (SUN-A, USNO: upper limb, centre 50′ below the horizontal) and Swiss `SE_BIT_HINDU_RISING` (SUN-B: disc centre, no refraction, geocentric) are documented in sources read for this package. The Rashtriya Panchang convention (SUN-D) is **reported** by the PM/QA review as upper limb with 31′ refraction and 16′ semidiameter, i.e. centre 47′ below the horizontal, at the Central Station 82°30′ E, 23°11′ N. **Claude has not been able to verify this from the primary source** (section 5.6.1); the reviewer has since reported reading it in official-domain text. The six reviewer-transcribed Central Station sunrise and sunset pairs agree with a 47′ (or 50′) computation to within about one minute, and are 3 to 4 minutes away from SUN-B (section 5.6.1). At printed-minute precision they cannot distinguish 47′ from 50′. In revision 0.5 the reviewer reports opening IMD's explanation page directly, which states the 47′ convention and the Central Station. Across India SUN-B comes about 3.2 to 4.3 minutes after SUN-D, and SUN-D about 12 to 17 seconds after SUN-A (illustrative estimates, section 5.6.4). Inside the canonical ±66.0° band, SUN-A and SUN-D have **no sunrise on some dates above about 65.7° to 65.8°**; USNO confirms this for 65.9° N on 2026-06-21. SUN-B stays defined throughout the band. **No sunrise convention is recommended in this revision** (PAN-D03).
3. **Official Indian reference.** The Positional Astronomy Centre (IMD) Rashtriya Panchang still cannot be retrieved from this environment (network policy refusal and robots disallow), and no other route was used. With the owner's authorization, the PM/QA reviewer transcribed **46 field-level candidate values** from official IMD daily pages for six dates in spring, monsoon and autumn 2026, plus the method facts. They are held in the capture template as **reviewer-mediated candidates**: 30 from pages the reviewer opened and 16 from official-domain index text only. **None is a verified fixture yet**; the promotion rule is in section 8.1. Claude's consistency checks on them:
   - The two candidate Tithi ends at New and Full Moon agree with USNO/NASA (same minute on 2026-10-26; one minute later on 2026-07-14).
   - All 14 candidate Karana names follow the candidate 60-position rule, including Naga (#60) and Kimstughna (#1).
   - IMD's three reported 2026 ayanamsa values agree with Swiss **true** Lahiri (SCI-01a) to within 0.8″, and are 6 to 8″ away from the mean value (section 3.1). This is a Claude scratch calculation and a consistency check, not an independent validation.
   - Revision 0.5: the same reviewer reopened all three daily pages, the explanation page and the names page directly (review 5680023508). That is **Stage B** (primary page rechecked) for all 46 candidates. **Stage C** (independent second-person verification) and **Stage D** (engineering acceptance) are 0 of 46 (SOURCE-REGISTER section 5).
4. **Independent references obtained.** 50 geocentric lunar-phase events for 2026 from USNO, cross-checked against NASA/Espenak: they agree on 42 events and differ by exactly one minute on 8. They are published **whole-minute** times, not exact-second instants. **25 of them (New and Full Moon, elongation 0° and 180°) are Tithi and Karana boundaries. The other 25 (First and Last Quarter, 90° and 270°) are Karana boundaries only**: they fall mid-Tithi. There are also 14 USNO sunrise/sunset cases, two of them negative (no sunrise), and 8 clearly labelled derived cases.
5. **Gaps.** There is no verified reference for Nakshatra or Yoga ending times, for SUN-B or SUN-D sunrise, or for Karana names. Section 8 lists every gap and the IMD coverage needed to close it.
6. **Swiss behaviours that matter for fail-closed design.** `swe_rise_trans` does not report which ephemeris it actually used. `swe_mooncross_ut` has an unbounded loop and does not check the returned ephemeris flag. The fast rise/set path is used for the Sun only up to |lat| ≤ 65°, and a different algorithm runs between 65° and 66°. The Swiss manual describes `SE_BIT_GEOCTR_NO_ECL_LAT` inconsistently. Details are in sections 5.6.3 and 5.7.

The recommendations are in the [decision matrix](#7-decision-matrix). Each is **proposed only**, and every owner status is PENDING. Section 5.9 separates three ideas that are easy to conflate: publication precision, numerical convergence and method accuracy.

**Revision 0.5 changes (owner-authorized final source validation; review 5680023508):** Stage A to D verification register for each candidate, with Stage B recorded separately and the original retrieval tiers unchanged; official 24-hour-plus rule documented; publisher name spellings reconciled (section 5.5.1); SUN-D horizon geometry made explicit in the WP-B2 draft; error sources separated (section 5.9); source rights recorded; per-element coverage matrix (section 8.2). Every decision stays PENDING.

**Revision 0.4 changes (owner-authorized IMD evidence handoff, PR #51 comment 6464388772):** 46 reviewer-mediated IMD candidates and the reported method facts added to the capture template, not as fixtures; ayanamsa comparison added (section 3.1); Karana and sunrise consistency checks added (sections 5.5 and 5.6.1); sections 8, 8.1 and 9 and the evidence for PAN-D03, D07, D15, D16 and D20 updated. Every decision stays PENDING; PAN-D03 still has no recommendation.

**Revision 0.3 change (review 5679456114):** the section 5.2 sunrise-failure statement is conditional on PAN-D11.

**Revision 0.2 changes (review 5679285841):**
- QA-01: added SUN-D; removed the provisional SUN-B preference; added the IMD ayanamsa compatibility analysis (section 3.1), the Central Station and 24-hour-plus notation rules, and an IMD coverage matrix (section 8.1); listed the reviewer-reported IMD facts as unverified candidates.
- QA-02: 25 Tithi+Karana versus 25 Karana-only events, minute precision.
- QA-03: re-analysed partial output versus whole-object refusal (PAN-D11).
- QA-04: added section 5.9; tolerances are now provisional until the IMD method review.

## 2. Canonical constraints this proposal does not change

These are fixed by [DECISIONS.md](../DECISIONS.md) and remain untouched:

| Canonical item | What it fixes | How Panchanga uses it |
|---|---|---|
| SCI-01a | Swiss `SE_SIDM_LAHIRI`, true ayanamsha, Swiss 2.10.03 default precession, `set_sid_mode` reset per request | Same ayanamsa for Nakshatra and Yoga. No new ayanamsa |
| SCI-01d | Geocentric apparent sidereal longitudes, `calc_ut(jd_ut, body, FLG_SWIEPH \| FLG_SIDEREAL)`, refuse without returned `FLG_SWIEPH`, no Moshier | Sole source of Sun and Moon longitudes for all five limbs |
| SCI-01f / SCI-02 / SCI-02 C2 | D1/D9 rules; chart schema `0.3.0` including `moon_nakshatra` | Chart outputs unchanged; Panchanga Nakshatra must equal the chart's Moon Nakshatra/Pada |
| SCI-01g | Supported latitude −66.0° to +66.0° inclusive | Panchanga never runs outside the band; band refusal precedes any sunrise computation |
| SCI-01h | Civil UTC passed as UT1; Swiss automatic ΔT reset per request; disclosed approximation | Transition instants are computed and reported in this same UT approximation |
| SCI-03 | Local civil dates 1900–2100 envelope; pre-1970 `HISTORICAL_CLOCK_UNVERIFIED`; pinned tzdata; D3 v2 zone policy | Birth instants validated exactly as for the chart; see PAN-D13 for transitions that fall outside the envelope |
| REL-01 | Mandatory Swiss conformance + independent rule/formula checks + boundary/refusal fixtures | Applies to WP-B2 unchanged; the fixtures here are the independent part |
| Metadata `/3` | `sabpuja-calculation-metadata/3` | Not modified. Panchanga gets its own versioned metadata (PAN-D12) |

Draft PR #48 (ChatGPT-authored, non-canonical) was not opened or used. Draft PR #47 (`77c4223`) was read for context only. Its proposals are not treated as approved, and its text is not reused.

## 3. Common definitions

Let λ☉ and λ☾ be the unrounded sidereal apparent geocentric longitudes of the Sun and the Moon from SCI-01d at the instant *t* (UT per SCI-01h). Define:

- **Elongation** E(t) = (λ☾ − λ☉) mod 360, in [0, 360).
- **Yoga sum** S(t) = (λ☉ + λ☾) mod 360, in [0, 360).
- **sector(x, n)** = the zero-based index *k* of the half-open interval [k·360/n, (k+1)·360/n) containing *x*. It is evaluated exactly on the binary value of the float, as the canonical `rules._sector` helper does on the draft engine stack. Nothing is pre-rounded and no tolerance is applied.

**Monotonicity.** The Moon's geocentric longitude always increases. The geocentric Sun never retrogrades. The Moon's daily motion (about 11.8° to 15.4°) always exceeds the Sun's (about 0.95° to 1.02°). E(t), S(t) and λ☾(t) are therefore strictly increasing modulo 360, so every boundary crossing is unique and can be bracketed. The ayanamsa grows by only about 50″ per year, which cannot reverse this.

**Frame independence of E.** In the sidereal frame, λ = λ_tropical − A(t), where A is the same ayanamsa for both bodies at the same instant. A therefore cancels in E but enters S twice. Consequences:
- Tithi and Karana can be validated against tropical, ayanamsa-free published phase times (USNO, NASA).
- Nakshatra and Pada can only be validated against a source that uses a compatible Lahiri ayanamsa. A 1″ ayanamsa difference shifts a Nakshatra end by about 2 s; a 1′ difference shifts it by about 2 minutes.
- For Yoga, a 1′ ayanamsa difference moves the sum by 2′, which shifts a Yoga end by about 3.4 minutes at the combined speed of about 14.2°/day. Using the **tropical** sum instead would shift every Yoga by about 2 × 24.2° ≈ 48°, which is 3.6 Yogas. That is the most consequential frame error possible here.

### 3.1 Compatibility of an IMD ayanamsa with SCI-01a (QA-01)

IMD Nakshatra and Yoga ending times can serve as exact oracles for the Sabpuja engine only if IMD's nirayana ayanamsa equals the canonical SCI-01a value (Swiss `SE_SIDM_LAHIRI`, **true** ayanamsha, IAE 1985 initial value 23°15′00.658″ at 1956-03-21 0h TT, Swiss 2.10.03 precession) to within an amount that is small against the printed minute. Claude could not read IMD's own statement of its ayanamsa. The reviewer reports (official-domain text in revision 0.4, then the explanation page opened directly in revision 0.5) that IMD uses a variable, increasing ayanamsa fixed at 23°15′00″ at 0h on 21 March 1956, and prints monthly initial values. Claude compared those values with Swiss 2.10.03 `SE_SIDM_LAHIRI` computed in a scratch session (not committed; the epoch time of day of the IMD values is not stated, so 0h UT on the Indian national calendar date was assumed; one day changes the ayanamsa by about 0.14″):

| Epoch (assumed 0h UT) | IMD value, as reported | Swiss true Lahiri | Swiss mean Lahiri (no nutation) | IMD − true |
|---|---|---|---|---|
| 1956-03-21 | 23°15′00″ | 23°15′00.80″ | 23°14′44.02″ | −0.8″ |
| 1 Chaitra 1948 Saka = 2026-03-22 | 24°13′30″ | 24°13′30.23″ | 24°13′24.11″ | −0.2″ |
| 1 Ashadha = 2026-06-22 | 24°13′45″ | 24°13′44.54″ | 24°13′36.78″ | +0.5″ |
| 1 Kartika = 2026-10-23 | 24°14′02″ | 24°14′01.72″ | 24°13′53.71″ | +0.3″ |

On these four points IMD's printed ayanamsa matches true Lahiri to within the 1″ rounding of the printed value, and is clearly not the mean value. It is **not proof** that the two conventions are numerically identical. What remains unverified:

| Aspect | SCI-01a (Swiss 2.10.03 `SE_SIDM_LAHIRI`, true) | IMD, as reported | Status |
|---|---|---|---|
| Reference value | 23°15′00.658″ at 1956-03-21 0h **TT** (Swiss's stored initial value; Swiss's true value at 0h UT that day prints 23°15′00.80″) | 23°15′00″ at 0h on 21 March 1956, time scale not stated | Agree within 1″. Whether IMD's 0h is UT, IST or ephemeris time, and whether 23°15′00″ is mean or true, is not stated in the handoff |
| Epoch of the 2026 monthly values | — | "Initial" value for each Saka month; time of day and time scale not stated | 0h UT assumed above. Any choice within the day changes the value by under 0.15″ |
| Precession model | Swiss 2.10.03 default: `SEMOD_PREC_DEFAULT` = Vondrák 2011 in `swephexp.h` | "Variable/increasing"; model not named in the handoff | Unknown. Four points over 70 years cannot exclude a model difference that grows outside 1956 to 2026 |
| Nutation | Included (true ayanamsa) | Not stated; the values match true, not mean | Indicated but not stated |
| Printed precision | Engine uses full precision | Whole arcseconds | ±0.5″ from rounding alone |
| Evidence | Engine's own model computed in a scratch session (not committed) | Reviewer transcription, not second-person checked | Neither side is an independent verification of the other |

The explanation page, as read by the reviewer, confirms the variable ayanamsa and the 1956 reference. It does not, by itself, establish numerical identity with the Swiss 2.10.03 precession implementation over the supported 1970 to 2100 range.

**No tolerance is set from this comparison.** If the conventions turn out to match to about 1″, the first row of the table below applies (Nakshatra about 2 s, Yoga about 4 s). That stays a hypothesis until IMD's method text is verified and checked by a second person. The things to establish, and their numerical effect, are:

| Possible difference | Size of ayanamsa difference | Effect on a Nakshatra end (Moon about 13.2°/day) | Effect on a Yoga end (sum about 14.2°/day; ayanamsa counts twice) | Tithi / Karana |
|---|---|---|---|---|
| Same definition, rounding of the published value | ≤ 1″ | ≤ about 2 s | ≤ about 4 s | None |
| Mean versus true ayanamsa (nutation in longitude, amplitude up to about 17″) | up to about 17″ | up to about 31 s | up to about 57 s | None |
| Different precession model or epoch value, about 1′ | about 60″ | about 1.8 min | about 3.4 min | None |
| A different ayanamsa family (for example Raman or Krishnamurti, about 1° to 1.5° away) | ≥ 3 600″ | hours | hours | None |

**Proposed rule:** IMD Nakshatra/Yoga rows become oracles only after IMD's ayanamsa definition is captured verbatim and shown to fall in the first two rows (the revision 0.4 four-point comparison is consistent with the first row but does not establish it). A mean/true difference must then be budgeted explicitly in the tolerance (section 5.9). Otherwise the rows are reported as method-difference comparisons, not pass/fail tests. Tithi and Karana rows are unaffected by any ayanamsa difference.

## 4. Inputs

| Input | Source | Needed for |
|---|---|---|
| Birth instant (UTC) | Existing SCI-03 validated conversion | All birth-time elements |
| Latitude, longitude | Existing validated coordinates (DATA-01 prototype places today) | Sunrise, sunset, sunrise Vara, daily Panchanga |
| Elevation | **Not available** in the current input contract | Only for SUN-A variants; SUN-B is elevation-independent (section 5.6.3) |
| IANA zone and offset | Existing D3 v2 / P5 rules | Local rendering of instants; civil weekday |
| Pressure, temperature | Not collected; would be fixed constants | Only for SUN-A |

## 5. Component methods

### 5.1 Tithi

| Aspect | Proposal |
|---|---|
| Definition | Tithi number *n* = sector(E, 30) + 1, so 1..30; each Tithi spans 12° of elongation |
| Paksha | *n* = 1..15: Shukla (waxing); *n* = 16..30: Krishna (waning) |
| Paksha day | ((n − 1) mod 15) + 1 |
| Names | Pratipada, Dvitiya, Tritiya, Chaturthi, Panchami, Shashthi, Saptami, Ashtami, Navami, Dashami, Ekadashi, Dvadashi, Trayodashi, Chaturdashi, then Purnima (n = 15) or Amavasya (n = 30). See [Appendix A](#appendix-a-names-and-identifiers-proposed) |
| Boundary | Half-open: E = 12k exactly belongs to Tithi k + 1; E = 0 exactly is Shukla Pratipada |
| 0/360 | E is reduced into [0, 360) from the exact difference; a raw negative difference adds 360 exactly |
| Birth-time Tithi | Tithi at the birth instant, with the instants at which it began and ends (PAN-D02) |
| Sunrise-day Tithi | Tithi in force at the selected local sunrise of the civil date, plus every Tithi end before the next sunrise. That can be zero ends (adhika) or two (kshaya) |
| Transition time | Instant *t* where E(t) = 12k; search per section 5.7 |
| Precision | Convergence to ≤ 0.5 s (PAN-D09). E changes by about 0.0001° per second, so 0.5 s ≈ 0.00007° |
| Independent reference | New Moon (E = 0, Tithi 30 → 1) and Full Moon (E = 180, Tithi 15 → 16) for all 25 such events of 2026 from USNO and NASA. Other Tithi boundaries need IMD data |
| Limitations | Only the 15/16 and 30/1 boundaries are independently referenced. Sunrise-day Tithi inherits every sunrise uncertainty |

### 5.2 Vara

Two different quantities are often both called "Vara":

| Option | Definition | Pros | Cons |
|---|---|---|---|
| VARA-CIVIL | Weekday of the local civil date of the birth instant (midnight to midnight, local IANA time) | Needs no sunrise; matches calendars and the USNO `day_of_week` | Not the traditional Panchanga Vara |
| VARA-SUNRISE | Weekday named after the day whose local sunrise most recently preceded (or equals) the birth instant. A birth after midnight but before sunrise takes the previous day's Vara | The traditional Panchanga meaning; consistent with sunrise-based Tithi | Needs a sunrise convention; undefined if sunrise is undefined; differs from the civil weekday for every pre-sunrise birth |

**Proposal (PAN-D05):** output both, clearly labelled. Use VARA-SUNRISE as the Panchanga `vara` field and VARA-CIVIL as a separate `civil_weekday`. Reports should say in plain words when they differ, for example "born before sunrise; the traditional weekday is Saturday although the calendar date is Sunday".

Further rules proposed:
- The sunrise-day interval is half-open: [sunrise_d, sunrise_d+1). A birth exactly at sunrise belongs to the new day.
- The sunrise used is the one at the birth coordinates, never at a reference station.
- If the governing sunrise cannot be computed, `vara` is never output. What happens to the rest of the Panchanga depends on the owner's PAN-D11 decision (section 5.6.6), which is PENDING: under D11-A the whole Panchanga object is refused; under the proposed D11-B, a physically undefined sunrise returns `vara` and the sunrise-dependent fields as typed `unavailable` while the sunrise-independent elements are kept, and an ephemeris or numerical failure still refuses the whole object. Under either option, do not fall back to the civil weekday under the `vara` name.
- The weekday sequence is anchored on the civil calendar weekday of the sunrise's local date. No separate weekday epoch arithmetic is introduced.

Derived cases PAN-DER-04, -05 and -06 show the difference. PAN-DER-06 shows that a birth two minutes after astronomical sunrise has a different Vara under SUN-A and SUN-B.

### 5.3 Nakshatra and Pada

| Aspect | Proposal |
|---|---|
| Definition | 27 Nakshatras of 13°20′ (= 360/27) of sidereal Moon longitude; four Padas of 3°20′ each |
| Formula | pada index p = sector(λ☾, 108); Nakshatra = p div 4 (0..26); Pada = (p mod 4) + 1. This is **identical** to the canonical chart rule for `moon_nakshatra` |
| Ayanamsa | Canonical SCI-01a Lahiri only. No new ayanamsa; no `SIDBIT_*` |
| Names | The English identifiers already used by the chart engine on the draft stack (Ashwini … Revati), so the chart and the Panchanga never disagree in spelling. Hindi in Appendix A, pending the Hindi reviewer (OD-08) |
| Boundary | Half-open, exact, as in the chart |
| Consistency requirement | For the same request, Panchanga Nakshatra and Pada must equal the chart's `moon_nakshatra` byte for byte; WP-B2 must test this |
| Transition time | Instant where λ☾(t) = 40k/3 (Nakshatra) or 10k/3 (Pada) |
| Independent reference | **None obtained.** Requires IMD Rashtriya Panchang Nakshatra ending times (Lahiri) |
| Limitations | Validation against a non-IMD publisher needs that publisher's exact ayanamsa (section 3) |

### 5.4 Yoga

| Aspect | Proposal |
|---|---|
| Definition | 27 Yogas of 13°20′ of the **sidereal** sum S = (λ☉ + λ☾) mod 360 |
| Formula | Yoga index = sector(S, 27) (0..26), number = index + 1 |
| Names and order | Vishkambha, Priti, Ayushman, Saubhagya, Shobhana, Atiganda, Sukarma, Dhriti, Shula, Ganda, Vriddhi, Dhruva, Vyaghata, Harshana, Vajra, Siddhi, Vyatipata, Variyan, Parigha, Shiva, Siddha, Sadhya, Shubha, Shukla, Brahma, Indra, Vaidhriti (source SRC-WP-YOGA; its cited primary works were not retrieved) |
| Boundary | Half-open on the exactly reduced sum; the sum is formed from unrounded addends, then reduced |
| Transition time | Instant where S(t) = 40k/3. S increases at about 13.2 + 1.0 ≈ 14.2°/day |
| Independent reference | **None obtained.** Requires IMD data |
| Limitations | Double ayanamsa sensitivity (section 3). The name list rests on a secondary source only, so it needs primary-source confirmation before adoption (PAN-D16) |

### 5.5 Karana

| Aspect | Proposal |
|---|---|
| Definition | 60 half-Tithis of 6° of elongation per lunar month; half-tithi index h = sector(E, 60), 0..59 |
| Sequence (to be verified) | One-based #1 (h = 0, first half of Shukla Pratipada) = Kimstughna; #2 to #57 = the seven movable Karanas Bava, Balava, Kaulava, Taitila, Gara, Vanija, Vishti in that order, repeated 8 times; #58 = Shakuni; #59 = Chatushpada; #60 = Naga (second half of Amavasya) |
| Equivalent formula | h = 0 → Kimstughna; 1 ≤ h ≤ 56 → movable[(h − 1) mod 7]; h = 57, 58, 59 → Shakuni, Chatushpada, Naga |
| Verification status | **Not verified against a primary source.** The only source read (SRC-WP-KARANA) states this rule, but its own table contradicts it. The classical sources it cites (Sewell & Dikshit 1896; S. B. Dikshit, IMD 1981) and the IMD Rashtriya Panchang were not retrievable. Per the WP-B1 brief, **no Karana naming convention is adopted** here Revision 0.2: the owner and the PM/QA review identify IMD's official names page (`/panchang/en/tithi-nakshatra`, SRC-IMD-NAMES) as listing the eleven Karana names. That page is the proposed primary name source. It could not be read from this environment (robots disallow, network refusal), so the eleven names, their spelling and their order remain unverified here. Adoption needs the page's list captured verbatim, plus the indexing confirmed against at least one named Kimstughna transition and one fixed-Karana transition from the IMD daily tables (section 8.1). Revision 0.4: the reviewer reports the printed list as Bava, Balava, Kaulava, Taitila, Gara, Vanij, Vishti, Sakuni, Chatuspada, Naga, Kimstughna. All 14 reviewer-mediated Karana candidates follow the rule above: #6 to #11, #30, #31, #35, #36, and Naga (#60) then Kimstughna (#1) around the New Moon of 2026-07-14. Every Karana end that should coincide with a Tithi end does so at the same printed minute. The Kimstughna and Naga rows are index-text-only candidates, and the daily row spells the name Kinstughna. So this is strong consistency evidence, not yet verification |
| What is verified | The **index boundaries** h = 59→0 (New Moon), 14→15 (First Quarter, E = 90), 29→30 (Full Moon) and 44→45 (Last Quarter, E = 270), by all 50 USNO/NASA events. These are geometric facts that do not depend on names |
| Proposal (PAN-D07) | WP-B2 outputs the half-tithi index (1..60) from the start. Karana **names** are emitted only after the owner adopts a verified naming source. Until then the name field is absent and a reason is recorded, never guessed |
| Transition time | Instant where E(t) = 6k |
| Limitations | Variant name spellings (Gara/Garaja, Vanija/Vanij, Vishti/Bhadra) need the Hindi/English editorial decision (OD-08) |

#### 5.5.1 Official names and spellings (revision 0.5)

The primary names reference is IMD's names page, `https://packolkata.imd.gov.in/panchang/ta/tithi-nakshatra`. The reviewer opened it directly (review 5680023508); Claude could not. The page reportedly lists 27 Yoga names and 11 Karana names. Publisher spellings are recorded as printed and are **not** normalised into Sabpuja identifiers. Canonical English and Hindi names stay with PAN-D16 and the OD-08 editorial review. No engine name table or customer-facing translation changes.

**Karana**, in the order the handoff lists them from the names page:

| # in list | IMD spelling (names page) | Sabpuja Appendix A candidate | Daily-row spelling seen | Kind in the candidate rule |
|---|---|---|---|---|
| 1 | Bava | Bava | Bava (IMD-11, -35) | Movable |
| 2 | Balava | Balava | Balava (IMD-12, -36) | Movable |
| 3 | Kaulava | Kaulava | Kaulava (IMD-13) | Movable |
| 4 | Taitila | Taitila | — | Movable |
| 5 | Gara | Gara | Gara (IMD-27) | Movable |
| 6 | Vanij | Vanija | Vanij (IMD-04, -28, -43) | Movable |
| 7 | Vishti | Vishti (Bhadra) | Vishti (IMD-05, -29, -44) | Movable |
| 8 | Sakuni | Shakuni | — | Fixed (#58) |
| 9 | Chatuspada | Chatushpada | — | Fixed (#59) |
| 10 | Naga | Naga | Naga (IMD-19) | Fixed (#60) |
| 11 | Kimstughna | Kimstughna | **Kinstughna** (IMD-20) | Fixed (#1) |

**Discrepancy:** the names page prints Kimstughna and the 2026-07-14 daily row prints Kinstughna. Both are kept as published; neither is corrected.

**Yoga and Nakshatra.** The full 27-name Yoga list has **not** been transcribed into the evidence available to Claude, so it is not reproduced here. Daily-row spellings seen, compared with Appendix A:
- Yoga: Vaidhriti (same), Viskumbha (Appendix A: Vishkambha), Vyaghata (same), Vyatipata (same), Vajra (same), Variyan (same).
- Nakshatra: Bharani, Krittika, Punarvasu and Magha are the same as the chart engine; Asvini (engine: Ashwini).
- The candidate sequences are in Appendix A order. Bharani then Krittika (March), Asvini then Krittika (October), Vaidhriti then Viskumbha (wrap), and Vajra then Vyatipata then Variyan all follow that order.

**Karana mapping.**
- **What the official explanation describes** (reviewer, Stage B): seven repeating Karanas and four fixed Karanas. As relayed, it does not give the full 60-position table.
- **Daily rows that corroborate the candidate rule:** IMD-27, -28 and -29 (#6 to #8); IMD-04 and -05 (#7, #8); IMD-11, -12 and -13 (#9 to #11); IMD-35 and -36 (#30, #31); IMD-43 and -44 (#35, #36); IMD-19 and -20 (#60 Naga, then #1 Kimstughna, at the 2026-07-14 New Moon). Each Karana end that should coincide with a Tithi end does so at the same printed minute.
- **Still needed before the 60-position mapping can be approved:**
  1. Stage C verification of these rows, including IMD-19 and -20, which were first obtained from index text.
  2. At least one verified Sakuni (#58) row and one Chatuspada (#59) row, so that the fixed-sequence order before Naga is evidenced.
  3. A verified Krishna Chaturdashi second half (#57 Vishti, then #58 Sakuni).
  4. Verbatim capture of the explanation's Karana paragraph.

PAN-D07 and PAN-D16 stay PENDING.

### 5.6 Sunrise and sunset

#### 5.6.1 Conventions compared

| ID | Convention | Geometric condition at the event | Source |
|---|---|---|---|
| SUN-A | Astronomical apparent sunrise | Upper limb on a level sea horizon with mean refraction: centre geometrically 50′ below the horizontal (16′ semidiameter + 34′ refraction) | USNO definitions (SRC-USNO-RST-DEF); Swiss default behaviour (SRC-SWISS-PRG) |
| SUN-A′ | Swiss default with its own refraction model | Upper limb; refraction from Swiss `swe_refrac_extended` with the given or estimated pressure and temperature (0 °C if not given in the Python binding); apparent radius from the actual Sun distance | SRC-SWISS-SRC |
| SUN-B | Swiss `SE_BIT_HINDU_RISING` | Centre of the disc on the geometric horizon, no refraction, geocentric (not topocentric) position, ecliptic latitude of the Sun set to 0 | SRC-SWISS-PRG ("Sunrise in Astronomy and in Hindu Astrology"); practice evidence SRC-DRIK-FAQ |
| SUN-C | Centre with refraction | Centre at apparent horizon (about −34′ geometric) | Used by some almanacs; not documented as a Panchanga convention in the sources read |
| SUN-D | Rashtriya Panchang convention, **as reported by the PM/QA review** | Upper limb with refraction taken as 31′ and semidiameter 16′, so the centre is geometrically 47′ below the horizontal; sunrise and sunset printed for the adopted **Central Station (82°30′ E, 23°11′ N)** only | SRC-IMD-RP: first reported in review 5679285841; the explanation page was then read directly by the reviewer (review 5680023508, Stage B). **Not read by Claude**: the page remains unreachable from this environment |

Notes on SUN-D, if it is confirmed:
- **Closeness to SUN-A.** SUN-D is close to SUN-A, not to SUN-B: it differs from USNO's 50′ by 3′ of altitude, about 12 to 17 s of time across India (section 5.6.4).
- **Consistency with the reviewer-mediated candidates (revision 0.4).** Claude computed Central Station sunrise and sunset in a scratch session (Swiss 2.10.03, Moshier positions, which are adequate at this minute level; not committed) for the six candidate dates. All 12 printed times are within 0.7 min of the 47′ computation; the 50′ computation is 0.2 min earlier at sunrise. SUN-B is 3.4 to 3.7 min later at sunrise and earlier at sunset, which is outside every printed minute. The printed minutes fit neither plain rounding nor plain truncation of the 47′ times, so IMD's rounding rule and exact refraction or ephemeris details remain open. This supports the reported 47′ upper-limb convention, but does not verify it. At printed-minute precision it also cannot separate SUN-D (47′) from SUN-A (50′), which differ by about 13 s here.
- **No city sunrise.** Its printed sunrise belongs to the Central Station. It is not a sunrise for Delhi, Kolkata or any birthplace, and it must never be compared with the city-specific USNO fixtures.
- **Swiss realisation (a hypothesis for WP-B2 to test, not a verified recipe).** `swe_rise_trans` flags alone cannot express SUN-D, because its horizon is non-default: the WP-B2 draft (section 2) therefore requires an explicit, configurable horizon geometry. One possible form is `swe_rise_trans_true_hor` with `SE_BIT_NO_REFRACTION | SE_BIT_FIXED_DISC_SIZE` (upper limb at the 1 AU radius, about 15.99′ in Swiss) and `horhgt` = −31′. In the 2.10.03 source, `horhgt` is subtracted from the body's altitude when refraction is off, so −31′ would put the upper limb 31′ below the geometric horizon. Whether IMD uses topocentric or geocentric solar positions is also unknown; for the Sun the difference is under a second.

#### 5.6.2 Geocentric versus topocentric, centre versus limb, refraction, altitude

- **Centre versus upper limb:** 16′ of altitude. **Refraction:** about 34′ at the horizon in USNO's convention (31′ in the reviewer-reported IMD convention), with real-world variation of several arcminutes. Together they give the roughly 50′ (SUN-A) or 47′ (SUN-D) difference from SUN-B.
- **Geocentric versus topocentric:** the Sun's horizontal parallax is about 8.8″, worth under a second of time at Indian latitudes. It is negligible for the Sun. (For the Moon it would be about 57′, which is why the Panchanga longitudes must stay geocentric; see PAN-D01.)
- **Ecliptic latitude:** the Sun's ecliptic latitude is under about 1″. SUN-B sets it to zero by definition; the effect is negligible.
- **Observer altitude and horizon dip:** a raised observer sees the horizon depressed by about 1.8′·√h(m) (for example about 6′ at 10 m). Swiss applies dip only when `swe_rise_trans_true_hor` is called with `horhgt = −100`. Under SUN-B, altitude and pressure do not enter the condition. Under SUN-A they do, and Sabpuja has no elevation data.
- **Local horizon:** mountains, buildings and sea horizons are out of scope for every option. The product computes an idealised horizon and should say so.

#### 5.6.3 What the pinned Swiss Ephemeris actually does

Read from the 2.10.03 source and manual shipped in `pyswisseph==2.10.3.2` (SRC-SWISS-SRC, SRC-SWISS-PRG). This is vendor behaviour, not independent evidence.

| Behaviour | Evidence | Consequence for Sabpuja |
|---|---|---|
| `SE_BIT_HINDU_RISING = SE_BIT_DISC_CENTER \| SE_BIT_NO_REFRACTION \| SE_BIT_GEOCTR_NO_ECL_LAT` (256 \| 512 \| 128) | `swephexp.h` | SUN-B is one documented flag combination |
| `SE_BIT_GEOCTR_NO_ECL_LAT` is described as "use geocentric rather than topocentric position … ignore its ecliptic latitude" in the header and source. The manual's flag list says "use **topocentric** position of object and ignore its ecliptic latitude" | `swephexp.h` vs `swephprg.md` §6.1 | Documentation inconsistency. The **code** (`rise_set_fast` and `swe_rise_trans_true_hor`) omits `SEFLG_TOPOCTR` and uses ecliptic-to-horizon conversion with latitude 0 when the flag is set, i.e. geocentric. WP-B2 must test this behaviour and not rely on the manual's wording |
| The manual's sunset example uses only `DISC_CENTER \| NO_REFRACTION` (no `GEOCTR_NO_ECL_LAT`), unlike its sunrise example; it also declares the longitude as `int` | `swephprg.md` §6.1 example | Do not copy the example. Use the same complete flag set for rise and set |
| Fast algorithm `rise_set_fast` is used for the Sun only when \|lat\| ≤ 65° (60° for other bodies); otherwise the slower `swe_rise_trans_true_hor` path runs | `swecl.c`, `swe_rise_trans` | Within the canonical band, 65° < \|lat\| ≤ 66° uses a different algorithm. WP-B2 needs fixtures on both sides of 65° |
| `rise_set_fast` runs a fixed 2 refinement iterations for the Sun (4 for the Moon), each step clamped to 0.1 day; no convergence test is applied | `swecl.c` | WP-B2 must measure the residual altitude at the returned instant (or compare with the slow path) and refuse if it exceeds a declared bound (PAN-D10) |
| Return codes: 0 = found, −1 = error, −2 = circumpolar (no rise or set). The Python binding raises on −1 and returns −2 | Manual; `pyswisseph.c` | −2 must map to a typed refusal, never a time |
| `swe_rise_trans` gives no ephemeris-used flag; it calls `swe_calc_ut` internally, which may silently fall back to Moshier if `.se1` files are missing | `swecl.c` | SCI-01d's "refuse without `FLG_SWIEPH`" cannot be checked from the rise result. WP-B2 must verify `FLG_SWIEPH` from `calc_ut` at the same instants, as well as the pinned-file checks |
| The Python binding calls `swe_set_topo` when `FLG_TOPOCTR` is passed; `rise_set_fast` calls `swe_set_topo` itself when not geocentric | `pyswisseph.c`, `swecl.c` | Global Swiss state changes; reset it per request under the existing Swiss lock (PAN-SPEC-15) |
| Pressure 0 means "estimate from altitude"; the binding's default temperature is 0 °C | Manual; `pyswisseph.c` | SUN-A results depend on these hidden defaults. Fix them explicitly if SUN-A is chosen |
| Observer altitude must be within −500 m to 25 000 m or the call errors | `sweph.h`, `swecl.c` | Input validation in WP-B2 |
| The rise/set routines mask the ephemeris flag down to `SWIEPH \| JPLEPH \| MOSEPH` (plus `NONUT`/`TRUEPOS` on the slow path) | `swecl.c` | `FLG_SIDEREAL` is irrelevant to rise/set, so the sidereal mode does not leak in |

#### 5.6.4 Size of the convention effect

Illustrative spherical-astronomy estimate (scratch arithmetic, not engine output, not a fixture): the time for the Sun's centre to rise from −50′ (SUN-A) to 0′ (SUN-B), with declination held fixed. The same arithmetic puts SUN-D (−47′) about 12 to 17 s after SUN-A at Indian latitudes (8° to 34°), and therefore about 3.2 to 4.3 minutes before SUN-B.

| Latitude | Dec −23.44° (Dec. solstice) | Dec 0° (equinox) | Dec +23.44° (June solstice) |
|---|---|---|---|
| 0° | 3.6 min | 3.3 min | 3.6 min |
| 13.1° (Chennai) | 3.8 | 3.4 | 3.8 |
| 22.6° (Kolkata) | 4.0 | 3.6 | 4.0 |
| 28.6° (Delhi) | 4.3 | 3.8 | 4.3 |
| 34.1° (Srinagar) | 4.6 | 4.0 | 4.6 |
| 45° | 5.7 | 4.7 | 5.7 |
| 60° | 10.7 | 6.7 | 11.3 |
| 65° | 21.0 | 7.9 | 27.6 |
| 65.9° | 29.0 | 8.2 | no SUN-A sunrise |

Impact:
- **Birth-time Tithi, Nakshatra, Yoga and Karana are unaffected**, because they do not use sunrise.
- **Sunrise-day elements** change whenever a transition falls inside this window. E advances about 0.034° in 4 minutes. For Tithi (mean length about 23.6 h) the chance is roughly 4/1417 ≈ 0.3% per day; Nakshatra and Yoga are similar, and Karana (about 11.8 h) about 0.6%. Across the four sunrise-day elements, roughly 1 to 1.5% of days at an Indian location have at least one changed sunrise element.
- **Sunrise Vara** changes for births inside the window, about 4 minutes per day in India.
- **Polar edge:** with SUN-A, sunrise and/or sunset is undefined near the solstices for |lat| > 90° − 23.44° − 0.83° ≈ 65.73°, which lies **inside** the canonical ±66.0° band. With SUN-D the limit is 90° − 23.44° − 0.78° ≈ 65.78°, also inside. With SUN-B it is 90° − 23.44° ≈ 66.56°, outside the band. USNO confirms SUN-A has no sunset at 65.9° N on 2026-06-21 (fixture PAN-REF-SUN-N01).

#### 5.6.5 Undefined sunrise and fail-closed response

| Condition | Required response (proposed) |
|---|---|
| \|lat\| > 66.0° | Existing `LATITUDE_OUTSIDE_SUPPORTED_BAND`, before any Panchanga step |
| Swiss returns −2 (circumpolar), or no sunrise is bracketed in the search window | `PANCHANGA_SUNRISE_UNDEFINED` (or `…SUNSET_UNDEFINED`). Whether this refuses the whole object or only the sunrise-dependent fields is decision PAN-D11 (section 5.6.6) |
| Swiss returns −1, or the ephemeris pre-check fails | Existing ephemeris refusal; no Moshier |
| Residual altitude check fails (section 5.6.3) | `PANCHANGA_TRANSITION_NOT_CONVERGED` |
| Governing sunrise falls on a local date outside the SCI-03 envelope (for example a birth at 1970-01-01 03:00 whose governing sunrise is on 1969-12-31) | Proposed: refuse the sunrise-dependent output with `HISTORICAL_CLOCK_UNVERIFIED` semantics, or withhold local rendering (PAN-D13) |

#### 5.6.6 Partial output versus whole-object refusal (QA-03)

Birth-time Tithi, Nakshatra, Yoga, Karana and the civil weekday do not depend on sunrise (section 5.8). A sunrise failure therefore does not by itself make them wrong. Three cases need different treatment:

| Cause | Example | Are the sunrise-independent elements still trustworthy? |
|---|---|---|
| Physically no sunrise or sunset under the adopted convention | SUN-A or SUN-D at 65.9° N in June (USNO N01); Swiss −2 agrees with the geometric expectation | Yes |
| Ephemeris or Swiss error (−1, missing `FLG_SWIEPH`, manifest failure) | Corrupt `.se1` file | **No**: the same data feed every element |
| Numerical failure (no convergence, residual check fails) | Bracket without a sector change | Unknown: it may indicate a defect |

| Option | Behaviour | Pros | Cons |
|---|---|---|---|
| D11-A Whole-object refusal for every cause | Any sunrise failure refuses the Panchanga | Simplest; nothing partial can be misread | Discards valid elements in the physical case, which is reachable in-band under SUN-A and SUN-D |
| D11-B Partial output for the physical case only | Birth-time Tithi, Nakshatra, Yoga, Karana and `civil_weekday` are returned. `vara`, sunrise, sunset and the entire sunrise-day object are replaced by a typed `unavailable` with reason `PANCHANGA_SUNRISE_UNDEFINED`. Ephemeris and numerical failures still refuse the whole object | Keeps correct results; fail-closed for everything that depends on the missing event; matches the polar reality | More contract surface; reports must explain the missing Vara |
| D11-C Partial output for every cause | As B, but also for ephemeris and numerical failures | — | Unsafe: it can publish elements computed from bad data. Not offered as a recommendation |

In every option, `vara` is **never** silently filled with the civil weekday.

Trade-offs between whole-object refusal (A) and the structured partial result (B):

| Aspect | D11-A whole refusal | D11-B structured partial |
|---|---|---|
| Safety | Nothing partial can be misread. But a correct result is also withheld | Fail-closed is kept for everything that depends on the missing event. Ephemeris and numerical faults still refuse everything, so no element computed from suspect data is released |
| Consistency | One rule for all failures | Sunrise-independent elements are identical to what they would be at any other location for the same instant (they are geocentric). The chart's `moon_nakshatra` and the Panchanga Nakshatra still agree. The output shape varies, so the contract must type `unavailable` explicitly |
| Customer experience | A customer born at, for example, 65.9° N in June gets no Panchanga at all, with only a refusal message | The customer gets Tithi, Nakshatra, Yoga, Karana and the calendar weekday, with a plain-language note that the traditional sunrise weekday and sunrise times cannot be determined for that place and date |
| Reporting (Gate RPT) | No Panchanga section | The report needs explanatory text for the unavailable fields, which is an editorial item |
| Engineering cost | Lowest | Moderate: typed `unavailable` fields, tests for each cause |

**Proposal (PAN-D11):** D11-B. The owner status stays **PENDING**. This replaces revision 0.1's whole-object recommendation, which assumed SUN-B, under which a physical no-sunrise case cannot occur in the band. It remains a proposed owner choice, not an authorization to build a code path.

### 5.7 Transition-time calculation

| Option | Description | Assessment |
|---|---|---|
| TS-1 Bracketed bisection on calc_ut | Bracket [t0, t1] where sector(f) changes; bisect until the bracket is ≤ 0.5 s; check `FLG_SWIEPH` on every call | Simple, guaranteed by monotonicity, bounded (about 18 iterations from 1.5 days to 0.5 s) |
| TS-2 Secant/Newton with bisection safeguard | Use the speed (`FLG_SPEED` is not part of SCI-01d's flags, so the speed would come from finite differences) | Fewer calls, but more code and needs care to stay inside the SCI-01d flag set |
| TS-3 Swiss `swe_mooncross_ut` / `swe_solcross_ut` | Built-in crossing of a longitude, 0.001″ precision | Only single-body longitudes, so it does not cover E or S. In 2.10.03 `swe_mooncross_ut` loops `for(;;)` with **no iteration cap** and does not check the returned ephemeris flag. It would also add `FLG_SPEED` to the flags. **Not proposed** |

**Proposal (PAN-D10):** TS-1, optionally accelerated by TS-2 inside the bracket. Hard caps: iteration ≤ 64, search window ≤ 2.5 days each way (the longest Tithi is about 26.8 h; Nakshatras up to about 27 h). On failure use the typed refusal; never extrapolate. Report instants to the second.

### 5.8 Birth-time Panchanga versus sunrise-based daily Panchanga

| Output | Elements | Depends on location? | Depends on sunrise convention? |
|---|---|---|---|
| Birth-time Panchanga | Tithi (+Paksha), Nakshatra + Pada, Yoga, Karana index (name after PAN-D07), each with start and end instants; sunrise Vara; civil weekday; that day's sunrise and sunset | Only the Vara, sunrise and sunset | Only the Vara |
| Sunrise-based daily Panchanga for the birth date | Elements in force at the sunrise of the civil birth date at the birth place, and all transitions until the next sunrise | Yes | Yes |

**Proposal (PAN-D02):** deliver the birth-time Panchanga as the primary Kundali output. Deliver the daily Panchanga as a separate, clearly named object so that the two are never confused. They can legitimately differ (PAN-DER-01).

### 5.9 Publication precision, numerical convergence and method accuracy (QA-04)

These are three different things, and agreement in one does not prove another:

| Quantity | What it is | Typical size here | What it does **not** show |
|---|---|---|---|
| Publication precision | The resolution of a printed value | USNO, NASA and (reported) IMD: whole minutes, with rounding versus truncation unstated | That the true event lies within ±30 s of the printed minute |
| Numerical convergence | How tightly the WP-B2 solver locates the crossing **of its own model** | Proposed ≤ 0.5 s (PAN-D09) | Anything about the model's accuracy. A 0.5 s bracket around a wrong model is still wrong |
| Astronomical-method difference | Different definitions of the same event: for sunrise, SUN-A, SUN-B and SUN-D differ by about 13 s (A/D) and 3.4 to 4.3 min (B/D) in India | Seconds to minutes | That either result is wrong; only which convention it follows |
| Ayanamsa and epoch difference | A difference in ayanamsa value, epoch time scale or precession model between a reference and SCI-01a | About 2 s per arcsecond (Nakshatra), 4 s (Yoga); Tithi and Karana unaffected | Section 3.1 has four points within 0.8″ (Claude scratch, not independent). Not established across 1970 to 2100 |
| Source rounding uncertainty | Unknown round-versus-truncate rule of a printed minute | Up to 1 min of ambiguity (window [printed − 60 s, printed + 60 s]) | The IMD rule is not stated in the evidence available; the sunrise check fits neither plain rule |
| Actual numerical reference residuals | Engine instant minus reference instant, measured | **None measured.** WP-B2 measures them only after tolerances are fixed | — |
| Method accuracy | How close the modelled instant is to the event as defined by the reference's method | Geocentric lunar events: ephemeris, ΔT model and SCI-01h UT1 ≈ UTC, expected to be well under a minute for 2026 (an expectation, not a measured bound). Sunrise: dominated by the refraction convention and real atmosphere, a minute or more (USNO's own statement) | — |

Consequences for this package:
- USNO/NASA agreement within one minute shows that two independent computations agree at **minute** resolution. It does not establish either one, or the Sabpuja engine, to the second.
- The tolerances in PAN-D15 are **provisional**. They are to be fixed by QA and the owner only after the IMD method facts (ayanamsa definition, sunrise convention, rounding rule, 24-hour-plus notation) are captured and the budget in section 3.1 is applied. They must be fixed before any evaluation run.
- Reports should never present an ending time to a precision greater than its method accuracy supports. That is why PAN-D09 proposes minute display and a near-boundary flag.

## 6. Consistency with the canonical engine

| Question | Finding |
|---|---|
| Does Panchanga need a different solar or lunar coordinate convention? | **No** for the five limbs: SCI-01d gives exactly the geocentric apparent sidereal longitudes needed. Sunrise under SUN-B uses Swiss's internal geocentric tropical Sun with latitude 0, which is a horizon computation, not a longitude classification, so no longitude convention changes |
| Discrepancy if a topocentric Moon were used | Up to about 1° in λ☾ (lunar parallax), so Tithi/Nakshatra ends would move by up to about 2 hours. Not proposed |
| Discrepancy between USNO "apparent" phases and SCI-01d | Both are apparent and geocentric; nutation cancels in E. Remaining differences (ephemeris, ΔT model, UT1 − UTC) are expected to be well under the one-minute publication step for 2026 |
| D1/D9, schema `0.3.0`, metadata `/3` | Unchanged. Panchanga is a separate document (PAN-D12) |
| Error and refusal policy | Existing codes and order reused; four new Panchanga-specific codes proposed (WP-B2 handoff section 6) |
| Historical clock | Unchanged; one new edge (transitions or sunrises before 1970 local) handled by PAN-D13 |

## 7. Decision matrix

Every row is **PROPOSED ONLY**, and every owner status is **PENDING**.

| ID | Decision | Option A | Option B | Other options | Recommendation (proposed) | Evidence | Owner status |
|---|---|---|---|---|---|---|---|
| PAN-D01 | Panchanga longitude frame | Reuse SCI-01d exactly (geocentric apparent sidereal, true Lahiri) | Topocentric Moon | Tropical for E only (identical in theory) | **A**. No new convention; E is frame-independent anyway; matches USNO/NASA phase definitions; location-independent transitions | Section 3, 6; SRC-USNO-PHASE-DEF; canonical SCI-01a/d | PENDING |
| PAN-D02 | Which Panchanga to output | Birth-time Panchanga + separate sunrise-based daily Panchanga | Birth-time only | Daily only | **A**, with birth-time as primary | Section 5.8; PAN-DER-01 | PENDING |
| PAN-D03 | Sunrise convention | SUN-A astronomical (USNO: upper limb, centre −50′) | SUN-B Swiss Hindu rising (centre, no refraction, geocentric) | SUN-C (centre with refraction); SUN-D (Rashtriya Panchang: upper limb, centre −47′, as reported, unverified) | **No recommendation in this revision.** Decide after IMD's explanation page is verified from the primary source. Revision 0.4: the reviewer-mediated Central Station times fit SUN-D (and SUN-A) within a minute and do not fit SUN-B. The differences are about 12 to 17 s between A and D, and about 3.2 to 4.3 min between D and B; A and D lose sunrise in-band above about 65.7° to 65.8° | Section 5.6; USNO N01; SRC-SWISS-PRG; SRC-IMD-RP (reported); SRC-DRIK-FAQ (practice only)  Revision 0.5: 47′ stated on the explanation page (reviewer, Stage B); the candidates cannot separate 47′ from 50′ | PENDING |
| PAN-D04 | Sunrise parameters | Fixed-geometry convention (SUN-B, or SUN-D as a fixed 47′ depression realised without Swiss's pressure/temperature refraction model): altitude 0 m, no local horizon | Swiss refraction model (SUN-A′): fixed 1013.25 hPa, fixed temperature, altitude 0 m, disclosed | Use real elevation (not available) | Follows D03. Whichever convention is chosen, prefer a **fixed, disclosed geometry** over an atmospheric model that needs data Sabpuja does not have | Section 5.6.1-5.6.3 | PENDING |
| PAN-D05 | Vara boundary | `vara` = sunrise-based; `civil_weekday` separate | Civil weekday only | Sunrise only | **A** | Section 5.2; PAN-DER-04/05/06 | PENDING |
| PAN-D06 | Sunrise-day element rule | Element in force at sunrise, plus all transitions to next sunrise | Element at local noon or midnight | — | **A** (traditional rule, SRC-WP-TITHI) | Section 5.1 | PENDING |
| PAN-D07 | Karana names | Emit names only after a verified primary source is adopted; index meanwhile | Adopt the cyclic rule now from the secondary source | — | **A**. The review names IMD's `tithi-nakshatra` page as the candidate primary source for Karana and Yoga names; adopt it once it is read and its indexing checked | Section 5.5; SRC-WP-KARANA inconsistency; SRC-IMD-NAMES (reviewer-mediated list; all 14 Karana candidates fit the 60-position rule) ; revision 0.5: official names page read directly by the reviewer; spellings in section 5.5.1; the 60-position mapping is not yet accepted | PENDING |
| PAN-D08 | Boundary rule | Half-open, exact rational on unrounded values (same as chart) | Tolerance band | — | **A** | Canonical chart rule; PAN-SPEC-01..05 | PENDING |
| PAN-D09 | Event-time precision and display | Converge to ≤ 0.5 s; machine output UTC to the second; display local HH:MM rounded to nearest minute; flag births within ±2 min of a transition | Display truncated minutes | Display seconds | **A**, with a "near boundary" flag in reports | Section 5.1, 5.7; USNO/NASA one-minute differences | PENDING |
| PAN-D10 | Transition and sunrise numerics | TS-1 bounded bisection (optional TS-2), FLG_SWIEPH checked every call; sunrise residual-altitude check | Swiss `mooncross` | — | **A** | Section 5.6.3, 5.7 | PENDING |
| PAN-D11 | Undefined sunrise | D11-A: refuse the whole Panchanga object | D11-B: for a physically undefined sunrise only, return the sunrise-independent elements and mark `vara`, sunrise, sunset and the sunrise-day object as typed `unavailable`; refuse the whole object for ephemeris or numerical failures | D11-C: partial for every cause (unsafe) | **D11-B** | Section 5.6.6; USNO N01 | PENDING |
| PAN-D12 | Output contract and version | Separate `sabpuja-panchanga/1` document with its own metadata | Extend chart to `0.4.0` | — | **A**: chart `0.3.0` and metadata `/3` stay byte-identical | WP-B2 handoff section 3, 8 | PENDING |
| PAN-D13 | Instants outside the SCI-03 envelope | Always report UTC; withhold local rendering (flagged) for instants before 1970-01-01 local or after 2100-12-31 local | Render with unverified offsets | Refuse the request | **A** | PAN-SPEC-12 | PENDING |
| PAN-D14 | Reference hierarchy | IMD Rashtriya Panchang for Panchanga conventions and ending times; USNO/NASA for ayanamsa-free astronomical events and SUN-A sunrise; Swiss documentation for behaviour only | Use commercial Panchang websites | — | **A**; no commercial website as ground truth | SOURCE-REGISTER | PENDING |
| PAN-D15 | Comparison tolerances | Provisional: phases within [min published − 60 s, max published + 60 s]; SUN-A ±120 s; IMD rows: the printed-minute window, widened by the section 3.1 ayanamsa budget once IMD's definition is known | Tighter, seconds-level | — | **Provisional A.** Fix only after the IMD method facts are captured (section 5.9), and always before any run | Fixture files; sections 3.1, 5.9; the four-point ayanamsa comparison is not used to set any tolerance ; revision 0.5: error sources separated in section 5.9; no final tolerance selected | PENDING |
| PAN-D16 | Names and localisation | Reuse the engine's English Nakshatra names; Yoga/Tithi/Karana English per Appendix A; Hindi pending the OD-08 reviewer | Adopt a published IMD spelling set once captured | — | **A now, B when IMD captured** | Appendix A; reviewer-mediated Karana spellings (Vanij, Sakuni, Chatuspada) ; revision 0.5: publisher spellings recorded separately from engine ids (section 5.5.1), editorial decision deferred | PENDING |
| PAN-D17 | Sunset | Compute with the same convention as sunrise; display only | Omit | — | **A** (KUN-A01 names sunrise/sunset) | PRD 12.1 | PENDING |
| PAN-D18 | Tithi numbering | Output both 1..30 and Paksha + day 1..15 | One only | — | **A** | Section 5.1 | PENDING |
| PAN-D19 | Lunar month (Masa), Amanta/Purnimanta, Samvat | Out of scope for KUN-A01 | Include | — | **Out of scope**; needs its own decision if reports name the month | — | PENDING |
| PAN-D20 | Proceed to WP-B2 without IMD fixtures | Not until the IMD convention and the section 8.1 IMD coverage are captured and verified from the primary source | Proceed with USNO/NASA-only independence and Swiss conformance | — | **A**. WP-B2 readiness stays **BLOCKED** until then | Section 8.1; 46 candidates held, 0 verified | PENDING |

For each recommendation, if the owner picks the alternative:
- **D01-B (topocentric):** results become location-dependent; no published phase reference applies; tithi ends shift by up to hours. This would require a new metadata convention and fixtures.
- **D03-A (astronomical sunrise):** USNO fixtures become direct references. Outputs differ from SUN-B practice by about 4 minutes. In-band polar unavailability becomes reachable above about 65.7°, and refraction parameters must be fixed and disclosed.
- **D03-B (Swiss Hindu rising):** defined throughout the band and independent of altitude. If IMD's 47′ convention is confirmed, Sabpuja would differ from the official Indian Panchang by about 3 to 4 minutes at sunrise, and no published reference for SUN-B exists in this package.
- **D03-D (IMD, once verified):** aligns with the official national Panchang. It is within seconds of the USNO fixtures, so they become near-direct references after a fixed 3′ correction. In-band polar unavailability is reachable above about 65.8°, so D11 matters.
- **D05-B (civil only):** simpler and sunrise-free; the field must then not be called the traditional Vara.
- **D07-B:** names may be wrong. The only source read is internally inconsistent.
- **D11-A (instead of the proposed B):** a place and date with no physical sunrise returns no Panchanga at all, even though Tithi, Nakshatra, Yoga and Karana are correct.
- **D12-B:** chart schema `0.4.0`, new compatibility evidence, and a change to the canonical chart contract.
- **D20-B:** WP-B2 starts sooner. Nakshatra/Yoga ending times would rest only on Swiss-on-Swiss conformance and the frame argument, which REL-01 does not treat as independent astronomical accuracy.

## 8. Reference fixture summary and shortfall

| Fixture set | Class | Count | Covers |
|---|---|---|---|
| [geocentric-lunar-phase-events-2026.json](../../research/panchanga/reference-fixtures/geocentric-lunar-phase-events-2026.json) | Direct, two independent publishers, whole minutes | 50 | **25 Tithi + Karana boundaries** (New Moon 30→1: 12; Full Moon 15→16: 13) and **25 Karana-only boundaries** (First and Last Quarter, mid-Tithi); 0/360 wrap; UT/IST date rollover |
| [usno-sunrise-sunset-2026.json](../../research/panchanga/reference-fixtures/usno-sunrise-sunset-2026.json) | Direct, single publisher | 12 positive + 2 negative | SUN-A sunrise/sunset, twilight, civil weekday at 9 Indian points and 1 southern control; polar day inside the band; polar night outside it |
| [derived-classification-cases.json](../../research/panchanga/reference-fixtures/derived-classification-cases.json) | Derived | 8 | Sunrise Tithi, sunrise Vara versus civil weekday, convention sensitivity, date rollover, near-midnight Karana |
| [boundary-test-specifications.json](../../research/panchanga/reference-fixtures/boundary-test-specifications.json) | Specifications | 16 | Every boundary and refusal named in the WP-B1 brief |
| [imd-rashtriya-panchang-capture-template.json](../../research/panchanga/reference-fixtures/imd-rashtriya-panchang-capture-template.json) | Template with 0 verified rows; 46 reviewer-mediated candidates held separately | 0 verified | Capture plan for IMD; candidate Tithi, Nakshatra, Yoga, Karana, sunrise and sunset values for six dates |

**Verified direct references: 64** whole-minute publisher values. That meets the 24-case target in count but **not in coverage**, which is why section 8.1 sets IMD targets per element:

| Element | Independent references | Shortfall |
|---|---|---|
| Tithi end | 25 (15/16 and 30/1 only; whole-minute) | Other 28 boundary types unreferenced |
| Karana index boundary | 50 (4 boundary types: 25 coinciding with Tithi ends, 25 Karana-only) | Names unverified; other 56 boundary types unreferenced |
| Nakshatra / Pada end | **0** (6 IMD candidates) | Candidates need verification and the section 3.1 assessment |
| Yoga end | **0** (7 IMD candidates, including the Vaidhriti→Viskumbha wrap) | Same |
| Sunrise / sunset, SUN-A | 12 + 2 negative | — |
| Sunrise / sunset, SUN-B (Hindu) | **0 direct** | Only differential checks via USNO + an independent oracle |
| Sunrise / sunset, SUN-D (IMD) | **0** (6 + 6 Central Station candidates) | Candidates need verification |
| Rashtriya Panchang central-station values | **0** verified | IMD unreachable from this environment |
| Sunrise-day classifications | 8 derived, 0 direct | Needs IMD daily Panchang |

### 8.1 Proposed IMD coverage (QA-04)

These are targets for verified, individually sourced IMD rows, captured with the template's provenance fields. **None is verified yet.** Revision 0.4 holds 46 reviewer-mediated candidates; the last column shows how far they would go once promoted.

**Promotion rule:** every candidate carries status `REVIEWER_SOURCED_PENDING_VERIFICATION`, and none may be promoted directly to `VERIFIED_INDEPENDENT_PRIMARY_GOLDEN`. A candidate becomes a verified row only after exact-source reconfirmation on the official page, an independent second-person comparison, confirmation of the 24-hour-plus interpretation from IMD's own text, a record of IMD's reuse terms, and, for Nakshatra and Yoga, the section 3.1 assessment. Index-text-only candidates also need a direct page read.

| Element | Minimum rows | Spread | Notes | Candidates held (revision 0.4) |
|---|---|---|---|---|
| Method facts (ayanamsa definition, sunrise convention and refraction value, Central Station coordinates, time standard, rounding rule, 24-hour-plus notation, Vara statement) | 1 record each, verbatim | — | Needed before any tolerance is fixed (section 5.9) | Sunrise convention, Central Station, IST endings, ayanamsa, Karana names, 24-hour-plus usage reported; rounding rule and Vara statement not reported |
| Tithi endings | 6 | At least 3 seasons; include at least one 15/16 or 30/1 end, to cross-check against USNO/NASA, and at least one 24-hour-plus value | Ayanamsa-free | 7, 3 seasons, both 15/16 and 30/1, two 24-hour-plus |
| Nakshatra endings | 6 | 3 seasons; include a Revati→Ashwini wrap if available | Oracle status depends on section 3.1 | 6, 3 seasons, no Revati→Ashwini wrap |
| Yoga endings | 6 | 3 seasons; include a Vaidhriti→Vishkambha wrap if available | Double ayanamsa sensitivity | 7, 3 seasons, wrap included |
| Karana transitions with names as printed | 4 | Must include Kimstughna and at least one of Shakuni, Chatushpada or Naga | Settles PAN-D07 indexing | 14, including Naga and Kimstughna (index text only) |
| Yoga and Karana name lists | 1 each, verbatim | — | Name source for PAN-D07/D16 | Karana list reported; Yoga list not reported |
| Central Station sunrise and sunset | 4 | Solstices and equinoxes | Central Station only; never compared with city fixtures | 6 + 6, near the March equinox, in July and late October; no solstice |
| **Total** | **≥ 34** | | Each row needs a second-person check against the source | 46 candidates, 0 verified |

**24-hour-plus notation:** IMD's explanation page states that times such as 25h and 26h mean 1 AM and 2 AM on the following Gregorian civil date (read directly by the reviewer, review 5680023508; not read by Claude). So `h. 24-10`, `h. 25-30` and `h. 28-43` mean 00:10, 01:30 and 04:43 IST on the next date. Fixtures keep the printed value and the printed date unchanged; the interpreted IST time and the UTC instant are stored separately as deterministic arithmetic on this publisher-defined rule. All 8 such candidates were rechecked.

**Rights:** record IMD's reuse statement verbatim for each document. Copy individual facts only, never pages or tables wholesale.

### 8.2 Reference coverage reconciliation (revision 0.5)

| # | Category | Count | Notes |
|---|---|---|---|
| 1 | Direct published USNO/NASA records | 64 | 50 geocentric phase events (25 Tithi + Karana boundaries, 25 Karana-only boundaries), 12 USNO sunrise/sunset cases and 2 USNO negative cases. Values unchanged in revision 0.4 |
| 2 | IMD candidates from official HTML opened by the reviewer | 30 | 2026-03-22, 03-23 (Chaitra page) and 2026-10-26, 10-28 (Kartika page) |
| 3 | IMD candidates from official-domain index text only | 16 | 2026-07-14, 07-17 (Ashadha page). Direct page open first timed out; the reviewer later opened it (Stage B). Tier unchanged |
| 4 | IMD records verified and second-person checked | **0** | Stage B (same reviewer reopened the page): 46. Stage C (independent second person): 0. Stage D (engineering accepted): 0 |
| 5 | Derived mathematical cases | 8 | PAN-DER-01..08. The 46 derived UTC minutes in the IMD template are conversions of candidates, not separate cases |
| 6 | Outstanding independent-reference gaps | 9 | (a) any verified IMD row; (b) verified Nakshatra ends; (c) verified Yoga ends; (d) verified Karana names and indexing; (e) any SUN-B reference; (f) verified SUN-D Central Station times, including a solstice; (g) IMD's rounding rule; (h) IMD's own 24-hour-plus wording; (i) IMD's Vara statement and the Yoga name list |

Proposed KUN-A01 tests (WP-B2 handoff section 11) and their references:

| Test | Verified independent reference | IMD candidates now available | Oracle status |
|---|---|---|---|
| PAN-QA-01 rule oracles | Rule definitions; 50 phase events for the elongation boundaries | 7 Tithi, 6 Nakshatra, 7 Yoga, 14 Karana ends | Candidates only. Nakshatra and Yoga also need the section 3.1 assessment |
| PAN-QA-02 name tables | None | Karana list (11 names), plus Tithi, Nakshatra, Yoga and Karana names in the daily rows | Candidates only; the Yoga list itself is not reported |
| PAN-QA-04 phase events | 50 USNO/NASA | 2 phase-coincident Tithi ends and 2 coincident Karana ends (07-14 and 10-26) | USNO/NASA remain the reference |
| PAN-QA-05 sunrise/sunset | 14 USNO (SUN-A, city coordinates) | 6 sunrise and 6 sunset at the Central Station (SUN-D) | Candidates only; never compared with city cases |
| PAN-QA-06 IMD rows | None | All 46 | Not an approved engineering oracle until method compatibility, source precision and independent verification are established |
| PAN-QA-03, -07 to -11 | Not reference-based | — | — |

Per-element coverage (counts are records, not test passes):

| Element | Direct publisher evidence | Source and convention | Rechecked (Stage B) | Independent verifier (Stage C) | Missing boundary or seasonal cases | Owner decision still open | Can it support WP-B2 ENG testing now? |
|---|---|---|---|---|---|---|---|
| Tithi | 25 USNO/NASA New/Full Moon events; 7 IMD candidates | USNO/NASA phase definition (ayanamsa-free); IMD geocentric IST | USNO/NASA: cross-publisher; IMD: 7 | IMD: 0 | Non-New/Full boundaries only from IMD candidates (5); no kshaya/adhika case | PAN-D06, D08, D09, D15, D18 | USNO/NASA: yes, at minute level. IMD: no (Stage D needed) |
| Karana | 50 USNO/NASA (25 also Tithi, 25 Karana-only); 14 IMD candidates | Elongation (ayanamsa-free); IMD names | IMD: 14 | 0 | Shakuni (#58) and Chatushpada (#59) rows; Chatushpada→Naga and Naga→Kimstughna rollovers verified at Stage C | PAN-D07, D16 | Index boundaries: yes (USNO/NASA). Names: no |
| Nakshatra / Pada | 6 IMD candidates | IMD variable ayanamsa | 6 | 0 | Revati→Ashwini wrap; Pada boundaries; more seasons | PAN-D01, D15, D16 | No (ayanamsa compatibility and Stage D needed) |
| Yoga | 7 IMD candidates, including Vaidhriti→Viskumbha | IMD variable ayanamsa (counted twice) | 7 | 0 | Full official 27-name list transcription; more seasons | PAN-D01, D15, D16 | No |
| Vara | 0 direct; 8 derived cases | Sunrise-based day (stated on the explanation page, reviewer) | — | — | Any published Vara-at-sunrise example near midnight | PAN-D05 | Derived classification tests only |
| Sunrise / sunset, SUN-A | 12 USNO + 2 negative | USNO 50′, city coordinates | Cross-checked internally | n/a (single publisher) | Southern-hemisphere and in-band polar negative pairs beyond N01 | PAN-D03, D04, D11, D17 | Yes, if SUN-A is adopted |
| Sunrise / sunset, SUN-B | 0 | Swiss Hindu rising | — | — | Any published SUN-B value | PAN-D03 | No (differential checks only) |
| Sunrise / sunset, SUN-D | 6 + 6 IMD Central Station candidates | IMD 47′ upper limb, Central Station only | 12 | 0 | A solstice pair (June and December); IMD rounding rule | PAN-D03, D04, D17 | No (Stage D and PAN-D03 needed) |

Missing cases that no fixture value may be invented to fill:
- a Revati→Ashwini Nakshatra wrap;
- a solstice sunrise/sunset pair at the IMD Central Station;
- verified SUN-B sunrise, if SUN-B remains a product candidate;
- more Tithi boundaries other than New and Full Moon, verified at Stage C;
- Karana fixed-sequence rollover cases, including Shakuni and Chatushpada;
- IMD's rounding rule, its full Yoga name list and its Kimstughna/Kinstughna spelling;
- historical-date edge cases (before 1970 local) and supported-latitude edge cases (±66.0°), which remain specifications (PAN-SPEC-10, -12) with no published values.

## 9. Unresolved scientific questions

1. Verification from the primary source of the reviewer-reported IMD sunrise definition (upper limb, 31′ refraction, 16′ semidiameter, Central Station 82°30′ E, 23°11′ N), and whether IMD's daily Vara/Tithi are tied to the Central Station sunrise. The candidate times fit 47′ within a minute (section 5.6.1).
2. IMD's ayanamsa model and the epoch time of day of its printed values. The reported values match true Lahiri to under 1″ at four points (section 3.1); verbatim wording is still needed.
3. IMD's rounding of printed ending times (truncated or rounded minute). The 24-hour-plus rule is now stated on the explanation page (read by the reviewer); the rounding rule is still not.
4. The authoritative Karana name list and order; spellings in English and Hindi (Kimstughna versus Kinstughna in the candidates).
5. Primary confirmation of the Yoga name list.
6. Whether USNO and NASA round or truncate. The one-directional one-minute differences (NASA later in all 8 cases) suggest different rounding rules, but neither page says.
7. Accuracy of the Swiss fast rise algorithm for SUN-B at Indian latitudes (two fixed iterations), and agreement of the fast and slow paths around 65°.
8. Treatment of births in the 4-minute SUN-A/SUN-B window in reports: one answer with a method note, or both answers.
9. Whether the daily Panchanga should show transitions in local time when they fall on the next civil date (for example 01:22 IST in PAN-DER-07). Proposed: yes, with the date.
10. Masa, Samvat and Amanta/Purnimanta naming are out of scope (PAN-D19), but they are often expected in a Panchanga report.

## 10. Owner decision checklist

The owner records a choice for each item (approve / modify / reject); none is decided here.

- [ ] PAN-D01 Longitude frame
- [ ] PAN-D02 Birth-time and daily Panchanga outputs
- [ ] PAN-D03 Sunrise convention (and whether IMD confirmation is a precondition)
- [ ] PAN-D04 Sunrise parameters
- [ ] PAN-D05 Vara boundary
- [ ] PAN-D06 Sunrise-day element rule
- [ ] PAN-D07 Karana naming gate
- [ ] PAN-D08 Boundary rule
- [ ] PAN-D09 Precision and display
- [ ] PAN-D10 Numerical method
- [ ] PAN-D11 Undefined-sunrise policy
- [ ] PAN-D12 Output contract and version
- [ ] PAN-D13 Instants outside the envelope
- [ ] PAN-D14 Reference hierarchy
- [ ] PAN-D15 Tolerances
- [ ] PAN-D16 Names and localisation (and the OD-08 Hindi reviewer)
- [ ] PAN-D17 Sunset
- [ ] PAN-D18 Tithi numbering
- [ ] PAN-D19 Masa out of scope
- [ ] PAN-D20 Whether WP-B2 waits for IMD capture
- [ ] How IMD data will be obtained: allow `packolkata.imd.gov.in` in the cloud environment's network policy, or the owner (or ChatGPT, through legitimate access) saves the official pages/PDFs into the project files. Note that the site's robots policy also blocks Claude's page-reading tool, so a network allowance alone may only enable direct download

Adoption then follows the two-step rule in [DECISIONS.md](../DECISIONS.md): pre-merge owner record, then post-merge adoption receipt. This document does not change that register.

## Appendix A. Names and identifiers (proposed)

Machine identifiers are lower-snake-case ASCII and stable across languages. Hindi forms are **proposed, pending the OD-08 Hindi reviewer**. They are not taken from a verified IMD Hindi edition.

**Paksha:** `shukla` शुक्ल पक्ष; `krishna` कृष्ण पक्ष.

**Tithi** (paksha day 1..15; day 15 is `purnima` in Shukla and `amavasya` in Krishna):

| Day | id | English | Hindi |
|---|---|---|---|
| 1 | pratipada | Pratipada | प्रतिपदा |
| 2 | dvitiya | Dvitiya | द्वितीया |
| 3 | tritiya | Tritiya | तृतीया |
| 4 | chaturthi | Chaturthi | चतुर्थी |
| 5 | panchami | Panchami | पंचमी |
| 6 | shashthi | Shashthi | षष्ठी |
| 7 | saptami | Saptami | सप्तमी |
| 8 | ashtami | Ashtami | अष्टमी |
| 9 | navami | Navami | नवमी |
| 10 | dashami | Dashami | दशमी |
| 11 | ekadashi | Ekadashi | एकादशी |
| 12 | dvadashi | Dvadashi | द्वादशी |
| 13 | trayodashi | Trayodashi | त्रयोदशी |
| 14 | chaturdashi | Chaturdashi | चतुर्दशी |
| 15 (Shukla) | purnima | Purnima | पूर्णिमा |
| 15 (Krishna) | amavasya | Amavasya | अमावस्या |

**Vara:** `sunday` Ravivara रविवार; `monday` Somavara सोमवार; `tuesday` Mangalavara मंगलवार; `wednesday` Budhavara बुधवार; `thursday` Guruvara गुरुवार; `friday` Shukravara शुक्रवार; `saturday` Shanivara शनिवार.

**Nakshatra** (English exactly as in the chart engine; id = lower-snake-case of it): Ashwini अश्विनी, Bharani भरणी, Krittika कृत्तिका, Rohini रोहिणी, Mrigashira मृगशिरा, Ardra आर्द्रा, Punarvasu पुनर्वसु, Pushya पुष्य, Ashlesha आश्लेषा, Magha मघा, Purva Phalguni पूर्वाफाल्गुनी, Uttara Phalguni उत्तराफाल्गुनी, Hasta हस्त, Chitra चित्रा, Swati स्वाति, Vishakha विशाखा, Anuradha अनुराधा, Jyeshtha ज्येष्ठा, Mula मूल, Purva Ashadha पूर्वाषाढ़ा, Uttara Ashadha उत्तराषाढ़ा, Shravana श्रवण, Dhanishta धनिष्ठा, Shatabhisha शतभिषा, Purva Bhadrapada पूर्वाभाद्रपद, Uttara Bhadrapada उत्तराभाद्रपद, Revati रेवती.

**Yoga:** Vishkambha विष्कम्भ, Priti प्रीति, Ayushman आयुष्मान, Saubhagya सौभाग्य, Shobhana शोभन, Atiganda अतिगण्ड, Sukarma सुकर्मा, Dhriti धृति, Shula शूल, Ganda गण्ड, Vriddhi वृद्धि, Dhruva ध्रुव, Vyaghata व्याघात, Harshana हर्षण, Vajra वज्र, Siddhi सिद्धि, Vyatipata व्यतीपात, Variyan वरीयान, Parigha परिघ, Shiva शिव, Siddha सिद्ध, Sadhya साध्य, Shubha शुभ, Shukla शुक्ल, Brahma ब्रह्म, Indra इन्द्र, Vaidhriti वैधृति.

**Karana (names not adopted, PAN-D07):** candidate list Bava बव, Balava बालव, Kaulava कौलव, Taitila तैतिल, Gara गर, Vanija वणिज, Vishti विष्टि (Bhadra भद्रा), Shakuni शकुनि, Chatushpada चतुष्पद, Naga नाग, Kimstughna किंस्तुघ्न.

These identifiers and English forms are unchanged. IMD's publisher spellings (for example Viskumbha, Asvini, Vanij, Sakuni, Chatuspada) are recorded separately in section 5.5.1, and the canonical English and Hindi names are deferred to an owner and editorial decision (PAN-D16).

## Revision history

| Version | Date | Author | Change | Approval |
|---|---|---|---|---|
| 0.1 | 2026-10-28 | Claude, WP-B1 | Initial proposal | ChatGPT review 5679285841: CHANGES REQUESTED |
| 0.2 | 2026-10-28 | Claude, WP-B1 | QA-01 to QA-04 corrections (see section 1) | ChatGPT re-review 5679456114: CHANGES REQUESTED (one stale statement) |
| 0.3 | 2026-10-28 | Claude, WP-B1 | Section 5.2 Vara refusal bullet made conditional on PAN-D11 (A or B); matching wording in PAN-SPEC-11, PAN-REF-SUN-N01 and WP-B2 sections 3, 9 and 11. No decision status changed | Superseded by 0.4 before re-review |
| 0.4 | 2026-10-28 | Claude, WP-B1 | Owner-authorized reviewer-mediated IMD evidence (PR #51 comment 6464388772): 46 candidates and method facts held unverified; ayanamsa, Karana and sunrise consistency checks. No decision status changed | ChatGPT review 5680023508: QA PASS (documentation and provenance), evidence gate HOLD |
| 0.5 | 2026-10-28 | Claude, WP-B1 | Owner-authorized final source validation and provenance reconciliation: stage A to D register, official notation and sunrise facts, name spellings, error sources, rights, per-element coverage. No decision status changed | PENDING ChatGPT exact-SHA QA and owner selection |
