# KUN-04 Scientific Methods RFC 0.1: Birth Panchanga, Vimshottari and Expanded Charts

**Draft for independent scientific review and owner selection | 2026-10-27 | NOT CANONICAL | No engine changes, PR merges or public release**

## Existing boundaries to preserve

Candidate Phase 1 PDF source f808eacfd677beca85c2eb33b8107def9ef12c71; scientific engine baseline PR #42 SHA 185353a1de8e5da02d20ea156cd4fca225fc1a27. Preserve existing approved Lahiri ayanamsa, Swiss source/ephemeris, mean Rahu, exact opposite Ketu, D1/D9 whole sign, pinned tzdata==2026.5, historical-clock refusal semantics, chart schema 0.3.0 and calculation metadata /3. The legacy PR #1 HOLD and production NO-GO remain.

**Do not silently introduce new fields into chart 0.3.0.** A separately versioned optional extension/report payload is proposed, with standalone contracts and explicit adoption before use.

## Module SCI-PAN-01 — Birth Panchanga

### Proposed five limbs

| Limb | Provisional equation/convention for validation | Mandatory decisions |
| --- | --- | --- |
| Tithi | E = (geocentric apparent Moon longitude − Sun longitude) mod 360; segment width 12°; number 1..30 from half-open intervals | Exactly which Swiss apparent/nutation flags and timescale; tithi at birth versus local sunrise |
| Nakshatra/Pada | Existing canonically validated sidereal Moon longitude from unrounded source, 27 sectors of 13°20′ and four padas each | Use existing source, not an alternate Moon rounding path |
| Yoga | Y = (sidereal Sun + sidereal Moon) mod 360; 27 equal 13°20′ segments | Star-based ayanamsa and boundary end-time method |
| Karana | A = E mod 360, karana half-tithi index in 60 six-degree segments; standard fixed/repeating karana name sequence | Exact mapping of the 60 half-tithis to 11 named karanas; boundary tie resolution |
| Vara | Civil local weekday available separately; traditional sunrise-to-sunrise weekday requires real local sunrise and sunset | Choose sunrise-based or civil weekday display; display both if supported and clearly labelled |

Sunrise/sunset must use one explicitly approved Swiss rise/transit contract, geodetic observer location, upper-limb/refraction/pressure/altitude choices and timezone conversion. Fail closed if event absent (polar location), astronomical rise computation fails, or location/clock is unsupported. Birth Panchanga cannot be equated to date-level public festival Panchang without selecting the underlying locale convention.

**Time boundaries:** half-open [start,end) convention on unrounded positions; crossing 0°/360°, midnight and sunrise handled via numerically bracketed searches; no guessed end-time or extrapolation outside supported dates. Audit all loops against bounded iteration/tolerance requirements. Never use local machine TZ as a fallback.

### Proposed payload only (not an approved schema change)

Birth-Panchanga extension version /1 with explicit method IDs, Sun/Moon UTC instant and derived values, tithi number/name, nakshatra/pada, yoga number/name, karana index/name, civil weekday, optional sunrise-vara, sunrise/sunset time with timezone provenance, start/end instants and uncertain/unavailable markers. Each field needs source and precision/rounding descriptions.

### Independent benchmark cases

- Longitude separations epsilon below/at/above 0°, 6°, 12°, 180°, 360°, and yoga/nakshatra 13°20′ boundaries; cross-zero normalization.
- Sunrise just before/at/after actual local event; timezone DST fold/gap, half-hour and quarter-hour offsets; leap day, 23:59 boundary; explicit stable refusal when sun does not rise/set.
- At least 24 independently sourced historical cases (multiple Indian regions/latitudes and seasons) checking all five limbs and rise times, distinct from developer fixtures.
- Differential Swiss numeric oracle that is independently written; ensure existing D1/D9 outputs byte-identical under projection.

## Module SCI-DAS-01 — Vimshottari Dasha

### Initial rule contract proposed for owner approval

Nine Dasha lords and canonical sequence: Ketu, Venus, Sun, Moon, Mars, Rahu, Jupiter, Saturn, Mercury. Years: 7, 20, 6, 10, 7, 18, 16, 19, 17; full cycle 120 nominal years. Natal Moon Nakshatra lord determines birth Maha Dasha; initial balance is the unelapsed fraction of its 13°20′ segment times lord's nominal year duration.

For nested Antar and Pratyantar Dasha, period share is outer-period duration × (child lord nominal years / 120). Child order starts with the parent lord and follows the nine-lord sequence cyclically. All periods use a single explicit positive-duration time arithmetic contract and half-open start-inclusive/end-exclusive boundaries. Derived end points must join without gaps or overlaps at the chosen exact internal precision.

### High-impact unresolved method decisions — DO NOT CODE AS CANONICAL

1. **Year-length convention:** 360-day Savana, 365.25-day mean solar, or another versioned school convention; results differ materially over decades.
2. **Time treatment:** fractional astronomical duration versus civil calendar additions (timezone/DST issues); UTC event instants versus wall-clock dates.
3. **Birth balance presentation:** convert remaining fraction to days/hours exactly, then display traditional years/months/days under a labelled conversion rule; avoid pretending equivalent to a Gregorian date.
4. **Subperiod depth and reporting horizon:** Maha + Antar are first-phase minimum; Pratyantar when independently validated; any smaller periods require new performance/reference gate.
5. **Astrological schools:** no hidden switch to different Dasha starting point, e.g. conditional alternative Nakshatra rule, without separate versioned approval.

### Independent cases and invariants

- Natal Moon exactly at every Nakshatra boundary and +/- epsilon; every one of 27 Nakshatras; wrapping 359.999...° -> 0°.
- Full birth balance and all 9 lord years; 120-year cumulative duration (according to selected year basis); 81 Maha/Antar combinations minimum; full nested coverage before exposing PD.
- Deterministic test for half-open boundary ownership and adjacent periods, leap days, time-zone DST folds, 1970+ age range, invalid and missing Moon values, precision over century-long accumulation.
- At least 20 independently supplied full or partial timeline cases across timezones/decades; compare exact UTC instants with documented rounding tolerance. A single vendor display matching to the day is not sufficient scientific verification.
- Cross validate inherited Moon Nakshatra/Pada and no change to existing chart 0.3.0 projection.

## Module DATA-CITY-01 — Place expansion and rights

Current private preview offers precisely ten curated Indian birthplace reference points; do NOT turn arbitrary text into coordinates or guessed timezones. Expand first to a versioned, licensed India city/administrative subdivision dataset with stable IDs, latitude/longitude, district/state disambiguation, precision/centroid warning, independent timezone mapping, source citation and data expiry policy. Avoid collecting exact GPS unless consented. Reject duplicate ambiguous locality names, unverified historical timezone corrections, out-of-band latitudes and locations without resolved coordinates.

**Coverage phases:** quality-controlled top India cities -> India broad coverage with ambiguity UX -> optional worldwide support by independent approval. Historic clock policies (D3 v2), pinned IANA and refusal contracts remain unchanged until separate reviewed decisions. Quota and geocoder licensing must be documented before production.

### Acceptance

- 100% unique IDs; no silent wrong-city selection; disambiguation for repeated names; synthetic QA across state borders, same-name towns, coast/altitude, timezone exceptions, 1970–present date rules.
- Coordinates/clock audit against an independently licensed source; no runtime geolocation internet dependency unless architecture/privacy approved.
- Search keyboard/mobile usability and explicit data-provenance line; no leakage of entered birth coordinates to third-party analytics.

## Module SCI-VARGA-02 — Additional divisional charts

D10 is suggested as the first extra varga because of career-oriented demand, followed by D7/D12 only if their complete sign-transform rules, Lagna convention, whole-sign chart placement, boundary policy and fixed fixtures are independently reviewed. D60 and other sensitivity-heavy vargas should not be promoted without explicit birth-time accuracy/uncertainty warnings.

No assumed uniform 'D-n' segmentation formula: varga schemes are tradition-specific; rule variants are a material scientific selection. Each new varga requires >=24 boundary/transformation vectors, multi-planet/Lagna tests, side-by-side reference chart checks, and explicit method IDs and chart schema adoption.

## Proposed implementation sequencing after scientific-owner selections

1. Build independent mathematical reference notebooks/fixtures and differential tests for PAN-01 and DAS-01; define unsupported/error codes and time arithmetic.
2. Implement isolated pure calculators in independent draft PR(s) based on reviewed source, with zero HTTP/PDF changes at first. Pin exact upstream SHA and keep results out of preview.
3. Integrate new optional, versioned output only after the scientific QA receipt, owner decision, compatibility projection checks and report-quality signoff.
4. Expand UI/PDF sections with brand, privacy and print QA in a separate PR.
5. Independently QA each extra varga and place dataset before surfacing them in client reports.

## Owner scientific decisions required (PENDING)

- PAN-01: Swiss solar/lunar longitude options, sunrise convention, named Karana mapping, sunrise-versus-civil vara, end-time tolerance and supported latitude/date scope.
- DAS-01: Dasha year model, fraction/date arithmetic, birth-balance representation, three-level coverage, rules for dates/boundaries.
- DATA-CITY-01: data rights/provider, initial city scope, source auditing and ambiguity/refusal policy.
- SCI-VARGA-02: canonical D10 and any follow-on varga rule selection and its historical source.

No selection above has been made by this RFC. Ask the owner to approve exact choices after independent science review. Neither this document nor an engineering prototype may supersede canonical docs/DECISIONS.md.
