# Workstream C: supported birth dates and locations

**Status:** evaluation of the proposed engineering envelope; recommendations for SCI-01g and SCI-03. PENDING. These are engineering boundaries, **not** customer-release approvals.
**Probe:** `tests/kun02/envelope_probe.py` plus Workstream A/B results; invariant C1.

Proposed envelope under evaluation: local civil birth dates **1900-01-01 through 2100-12-31**, latitude **±66°**.

## 1. Dates

### 1.1 What the data and Swiss can do

- The pinned `_18` files cover 1800–2399. With the engine's flags, all seven planets return `FLG_SWIEPH` on 1800-06-01 and 2399-06-01 and fall back to Moshier on 1799-06-01 and 2400-06-01 (the engine refuses a fallback). The mean node is analytic and reports `FLG_SWIEPH` everywhere.
- The UTC instants of the local-date window, over every IANA key in tzdata 2026e: local 1900-01-01 00:00 lies between **1899-12-31T10:00Z** (`Etc/GMT-14`; 1899-12-31T11:40:48Z for location keys, Pacific/Tongatapu) and 1900-01-01T12:00Z; local 2100-12-31 23:59:59 lies between 2100-12-31T09:59:59Z (Pacific/Kiritimati) and **2101-01-01T11:59:59Z** (`Etc/GMT+12`; 10:59:59Z for location keys, Pacific/Midway). All bodies use Swiss files at both extremes (C1). The ephemeris margin is about 100 years on each side.
- Calendar: Python and `swe.julday` both use the proleptic Gregorian calendar; 1900 and 2100 are not leap years and are refused for 29 February; 2000 and 2024 are leap years.

### 1.2 Where reliability changes inside the window

| Interval | Astronomy | Civil time | Classification |
|---|---|---|---|
| 1900 – 1955 | ΔT from Stephenson, Morrison & Hohenkerk (2016); UT1 reconstructed | Asia/Kolkata: railway time and war time as modelled by IANA; local clocks (Bombay, Calcutta and others) known to differ | **Refuse or verify clock** (RG-HIST) |
| 1956 – 1971 | ΔT tabulated | IST stable in Asia/Kolkata; "UTC" before 1972 is not leap-second UTC | Reliable for India; other pre-1970 zones owner scope |
| 1972 – IERS list expiry (2027-06-28) | \|UT1 − UTC\| < 0.9 s by IERS rule (consistent with Swiss ΔT, B3; not measured here), ΔT tabulated | IANA rules for current zones | **Reliable** (within birth-time precision) |
| 2027-06-28 – 2049 | ΔT extrapolated after 2028; UT1 − UTC is a forecast, and the 0.9 s limit is raised in or before 2035 (CGPM 2022 Res. 4) | future civil rules are projections | Reliable with **disclosure** (projected civil time) |
| 2050-01-01 0h UT | Swiss sidereal-time model step −1.908″ | — | known convention, record only |
| 2050 – 2100 | ΔT extrapolated; UT1 − UTC may reach tens of seconds if leap seconds stop | projections | Reliable with **disclosure** |

### 1.3 The current rule and the recommended one

The engine checks `1900 <= utc.year <= 2100` (`engine.py:78`). Synthetic cases prove both kinds of edge error: local 1900-01-01 00:00 in Asia/Kolkata (UTC 1899-12-31) and local 2100-12-31 20:00 in New York (UTC 2101) are refused although their local dates are inside the window, while local 2101-01-01 05:29:59 IST and local 1899-12-31 23:59:59 in New York are accepted although they are outside it (T46–T51).

Recommendation: validate on the **local civil date** of the supplied wall-clock time, inclusive of both ends, before any offset conversion. The UTC instant then automatically stays inside 1899-12-31T10:00Z … 2101-01-01T12:00Z, well inside the data.

## 2. Latitude

| Fact | Value | Source |
|---|---|---|
| Current accepted input | −89 < lat < 89 | `engine.py:96` |
| Current Lagna refusal | \|lat\| ≥ 90° − ε_true(date), via Placidus | lagna report §3.3 |
| Polar-circle latitude 1900–2100 | 66.546714° to 66.575237° | lagna report §3.3 |
| Margin from 66.0° to the earliest polar circle | 0.5467° (about 60 km) | derived |
| Lagna rate at 60° / 63° / 66° | up to 65.9 / 110.2 / 634.4 ″ per second of time | time probe |
| Lagna shift per minute of birth time at 66° | up to 10.6° | derived |
| India's extreme latitudes | about 6.7° N to 37.1° N | general geography, not probed |

Today the latitude at which a chart is refused depends on the date (66.55° refused for 1900-01-01, accepted for 2100-12-31). A user cannot predict that, and above the polar circle the Lagna is not stable against any realistic birth-time error.

Recommendation: **support \|lat\| ≤ 66.0° inclusive and refuse outside with a fixed code, regardless of date.** This is a conservative product support envelope, not a computational limit: Swiss `b"W"` computes a rising point beyond 66°. Inside the band, `b"P"` and `b"W"` give bit-identical ascendants, so the band does not depend on the SCI-01e choice. Above 60° add a disclosure that the Lagna is very sensitive to birth time (more than 1° per minute).

Alternatives: keep today's behaviour (date-dependent, not recommended); after SCI-01e accept up to ±89° with high-latitude fixtures and a strong disclosure; a narrower band such as ±60° (refuses Reykjavik, Anchorage and parts of Scandinavia).

Longitude: −180 and +180 are both accepted and give the same Lagna (date-line locations in the Lagna grid, `DL-E180`/`DL-W180`, have zero P/W differences and identical behaviour).

## 3. Proposed deterministic refusal codes and validation order

Validation should run in this fixed order so that one input always produces the same code. Codes are proposals for a later, separately authorized code package; today the engine raises `ValueError` with free-text messages and `ChartComputationError`/`EphemerisDataError` with codes.

| Order | Code | Condition (exact boundary) | Today |
|---|---|---|---|
| 1 | `REQUEST_INVALID` | not a JSON object, wrong keys or types | `ValueError` text |
| 2 | `TIME_FORMAT_INVALID` | not `YYYY-MM-DDTHH:MM[:SS[.ffffff]]±HH:MM[:SS]` | accepted or `ValueError` |
| 3 | `TIME_OFFSET_REQUIRED` | no offset | `ValueError` text |
| 4 | `TIME_LEAP_SECOND_UNSUPPORTED` | seconds field `60` | generic parse error |
| 5 | `DATE_INVALID` | calendar date does not exist (for example 1900-02-29) | generic parse error |
| 6 | `TIMEZONE_INVALID` | not an IANA key in the pinned tzdata | `ValueError` text |
| 7 | `TIMEZONE_NOT_LOCATION_BASED` (owner option) | `Etc/*`, `UTC`, `GMT` and similar | accepted |
| 8 | `DATE_OUTSIDE_SUPPORTED_RANGE` | local civil date < 1900-01-01 or > 2100-12-31 | UTC-year rule |
| 9 | `TIME_NONEXISTENT_LOCAL` | wall time falls in a gap for this zone (no offset maps back to it) | `OFFSET_MISMATCH` text |
| 10 | `TIME_OFFSET_MISMATCH` | wall time exists, but the given offset is not one of IANA's offsets for it (one, or two in a fold) | same text |
| 11 | `HISTORICAL_CLOCK_UNVERIFIED` (RG-HIST) | zone and date inside the owner-approved gate, minimum Asia/Kolkata before 1956-01-01 | accepted |
| 12 | `COORDINATE_INVALID` | non-number, non-finite, lat outside (−90, 90), lon outside [−180, 180] | `ValueError` text |
| 13 | `LATITUDE_OUTSIDE_SUPPORTED_BAND` | \|lat\| > 66.0 | date-dependent `ASCENDANT_UNCOMPUTABLE` |
| 14 | `LOCATION_TIMEZONE_INCONSISTENT` (after DATA-01) | coordinates not inside the zone's region | accepted |
| 15 | `EPHEMERIS_*` (existing) | data gate | existing codes |
| 16 | `ASCENDANT_UNCOMPUTABLE` (existing, defensive) | Swiss refuses the ascendant | existing code |

A fold (repeated hour) is **not** a refusal when the offset is given: both readings are valid and the offset says which. A front end that collects wall time without an offset must ask the user to choose and must never pick one silently; `TIME_AMBIGUOUS_LOCAL` is reserved for such an interface.

Disclosures (charts still produced): `FUTURE_CIVIL_TIME_PROJECTED` for births after the pinned IERS list expiry, `HIGH_LATITUDE_TIME_SENSITIVITY` above 60°, and a standing note that a one-minute birth-time error changes the Lagna Navamsa in about 8% of charts.

## 4. Summary recommendation

| Boundary | Recommended rule | Evidence |
|---|---|---|
| Date | Local civil date 1900-01-01 to 2100-12-31 inclusive; refuse outside | §1, T46–T51, C1 |
| Historical clocks | RG-HIST fail-closed for Asia/Kolkata before 1956-01-01 as a temporary minimum until DATA-01 birthplace-clock evidence exists; not proof that later or other Indian clocks kept IST; owner decides wider scope | birth-time report §2.2, §2.5 |
| Future | Accept with projected-civil-time disclosure | birth-time report §2.4 |
| Latitude | \|lat\| ≤ 66.0° inclusive; refuse outside; disclose above 60° | §2, A3, A4 |
| Longitude | [−180, 180] inclusive (unchanged) | §2 |
