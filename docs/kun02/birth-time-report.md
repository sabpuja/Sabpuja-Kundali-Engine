# Workstream B: birth-time accuracy

**Status:** technical report for SCI-01h and SCI-03. Recommendations only, PENDING.
**Base:** `d8193c692d52aa12595f81c227638a061605a3d9`. Python 3.13.16, tzdata 2026e (system and PyPI 2026.5), Swiss Ephemeris 2.10.03.
**Probe:** `tests/kun02/time_probe.py`; fixtures `time_cases.json`, `iana_zone_transcriptions.json`, `iers_leap_seconds.json`; invariants B1–B3.

## 1. The pipeline as implemented

```
"1930-06-15T12:00:00+05:30", "Asia/Kolkata"
  │ datetime.fromisoformat()            engine.py:64   explicit offset required (naive → refused)
  │ ZoneInfo(tz)                        engine.py:69   IANA key from the host's tzdata (system first)
  │ local.astimezone(zone) == local?    engine.py:73   offset must equal IANA's offset at that instant
  │ local.astimezone(UTC)               engine.py:76   civil UTC, leap seconds unrepresentable
  │ 1900 <= utc.year <= 2100            engine.py:78   UTC year, not local date
  │ swe.julday(utc …)                   engine.py:105  UTC passed as UT (= UT1 for Swiss)
  │ calc_ut(jd_ut, body)                engine.py:122  Swiss adds its ΔT model → TT for planets
  └ houses_ex(jd_ut, …)                 engine.py:130  UT1 → sidereal time → ARMC → Lagna
```

Three facts frame everything below:

1. The engine never guesses an offset: the caller supplies one and the engine checks it against IANA. That makes gaps and folds safe, but it moves the burden of choosing the right historical clock onto the caller.
2. Swiss Ephemeris treats the given UT as UT1 (`doc/swisseph.htm` §7: "Computations of sidereal time and houses … are calculated using Universal Time (UT)"; ΔT = TT − UT). The engine's UT is civil UTC.
3. Planet positions depend on TT = UT + ΔT(Swiss model). The Lagna depends on UT1 only (through sidereal time) plus the ayanamsha and obliquity, which change negligibly with ΔT.

## 2. Verified behaviour

### 2.1 Engine cases (B1)

All **63** synthetic cases behave exactly as derived by hand from the IANA 2026e Zone/Rule lines and Python's datetime rules. Every accepted case also runs end to end with the pinned data and reports the same UTC. The full table is in the appendix; the main results:

| Topic | Cases | Engine today |
|---|---|---|
| DST gaps (New York, London, Sydney), the Samoa skipped day, IST start 1906, war-time starts 1941/1942 | T05, T07–T09, T25, T26, T29, T32, T38, T39 | refused as `OFFSET_MISMATCH` (both offsets) |
| DST folds (New York, London, Sydney, 30-minute Lord Howe), war-time ends 1942/1945 | T13–T16, T27, T28, T30, T31, T33–T36 | both readings accepted, one hour (or 30 min) apart, disambiguated by the offset |
| 30- and 45-minute zones | T22, T36, T37 | correct |
| Leap second `23:59:60` | T40, T41 | refused by Python's parser (`PARSE`), not by a dedicated rule |
| 29 February in 1900 / 2000 / 2024 / 2100 | T42–T45 | refused / accepted / accepted / refused (Gregorian rule) |
| Window edges | T46–T51 | **UTC-year rule**: local 1900-01-01 00:00 Kolkata refused; local 2101-01-01 05:29:59 IST accepted; local 2100-12-31 20:00 New York refused; local 1899-12-31 23:59:59 New York accepted |
| Historical offsets IANA does model (Madras time, war time, LMT in Kathmandu and Karachi, HMT in Dhaka, Colombo, Yangon) | T02, T04, T06, T10, T12, T21, T23, T24, T61, T62 | accepted |
| Historical offsets IANA does not model in Asia/Kolkata after 1870 (LMT of 72.8777° E; +05:53:20 Calcutta government time) | T17, T19 | refused |
| The same 1930 clock reading given as +05:30 | T18 | **accepted** |
| `Z` with an Indian zone, naive time, `IST` as key | T53–T55 | refused |
| `Etc/GMT-5`, `UTC` with Indian coordinates, Asia/Kolkata with New York coordinates | T56, T57, T63 | **accepted**: no zone/location consistency check |
| Microseconds, space separator, ISO basic format `20000101T173000+0530` | T58–T60 | accepted (the last two only because Python ≥ 3.11 widened `fromisoformat`) |
| Lower-case key `asia/kolkata` | T-PD1 | refused on this Linux host; may load on case-insensitive file systems (not asserted) |

### 2.2 IANA cross-check (B2)

The Zone entries for Asia/Kolkata, Asia/Karachi (to 1971), Asia/Dhaka (to 2008), Asia/Kathmandu, Asia/Colombo, Asia/Yangon and Asia/Thimphu were transcribed by hand from tz 2026e `asia` (SHA-256 `02b69728…0e92e`, line numbers recorded) and re-evaluated by an independent offset function. At 74,864 probe instants (every transition ±1 s, and twice every 15 days from 1850), Python `zoneinfo` on the installed tzdata gives **the same offset in every case**.

Asia/Kolkata local-clock anomalies from 1900, found by scanning `zoneinfo`:

| Change (UTC) | Offset | Local effect |
|---|---|---|
| 1905-12-31 18:38:50 | +05:21:10 → +05:30 | 1906-01-01 00:00:00–00:08:50 does not exist |
| 1941-09-30 18:30 | +05:30 → +06:30 | 1941-10-01 00:00–01:00 does not exist |
| 1942-05-14 17:30 | +06:30 → +05:30 | 1942-05-14 23:00–24:00 occurs twice |
| 1942-08-31 18:30 | +05:30 → +06:30 | 1942-09-01 00:00–01:00 does not exist |
| 1945-10-14 17:30 | +06:30 → +05:30 | 1945-10-14 23:00–24:00 occurs twice |

What IANA itself says about these records (tz 2026e `asia`, India section): railway time is used "for 1870-1941" because it "was better documented"; "Some municipalities retained their former time, and the time in Calcutta continued to depend on whether you were at the railway station or at government offices"; Calcutta government time "was at +055320 (according to Shanks) or at +0554 (according to the Indian Year Book)"; "Shanks is our only (and dubious) source for the 1941-1945 data"; the Bombay "Battle of the Clocks" after 1906 "lasted nearly half a century". `theory.html`: the database "is not designed for and does not suffice for applications requiring accurate handling of all past times everywhere".

### 2.3 Which tzdata is used (new finding)

`zoneinfo` reads the host's system tzdata first (`TZPATH = /usr/share/zoneinfo, …`) and only falls back to the PyPI `tzdata` package. On this host both are IANA **2026e**, yet for 8 of 106 compared zones they disagree before 1956: Asia/Aden and Asia/Kuwait until 1949, Asia/Bahrain to 1943, Asia/Brunei and Asia/Phnom_Penh to 1945, Asia/Vientiane to 1955, Asia/Muscat to 1919, Asia/Kuala_Lumpur in 1900. Example: Asia/Aden in 1920 is +02:59:54 in Ubuntu's build and +03:06:52 in PyPI's. The cause is the build option: Ubuntu compiles IANA's `backzone` file (which has `Zone Asia/Aden 2:59:54 - LMT 1950`, backzone line 968), PyPI links Aden to Riyadh. Asia/Kolkata is identical in both builds. **A host tzdata upgrade or a different OS image can therefore change historical charts without any code change.**

### 2.4 Time scales (B3)

| Era | What the engine's "UTC" is | Swiss `utc_to_jd` UT1 minus engine UT | Basis |
|---|---|---|---|
| 1900–1960 | a civil clock reading converted with IANA's offset; no UTC existed before 1961 | 0 s (Swiss also treats input before 1972 as UT1) | `swedate.c` lines 366–369 |
| 1961–1971 | UTC with frequency offsets and steps (not yet leap-second UTC) | 0 s in Swiss | not separately sourced here |
| 1972–2033 | leap-second UTC; the IERS rule keeps \|UT1 − UTC\| < 0.9 s only while that rule stands (CGPM 2022 Res. 4: the limit will be raised in or before 2035) | −0.95 s to +0.39 s (Swiss ΔT model; the larger values after 2030 assume no new leap second) | leap-seconds.list, Swiss ΔT table to 2028 |
| from 2034 | projected UTC | 0 s again (Swiss treats input as UT1 once ΔT − TAI−UTC − 32.184 > 1 s) | `swedate.c` lines 366–371 |

Model consistency check (B3). This is **not** an observational verification of UT1: no IERS Earth-orientation (UT1 − UTC) series was used. UT1 − UTC is *implied under the Swiss ΔT model* as 32.184 s + (TAI − UTC) − ΔT_Swiss, with TAI − UTC from the leap-second list transcribed from tz 2026e `leap-seconds.list` (SHA-256 `db5a895f…3433`, updated 2026-07-06, **expires 2027-06-28**, TAI − UTC = 37 s since 2017-01-01). At all 110 half-year epochs from 1972 to 2026 that implied value stays within ±0.9 s (largest 0.81 s, 1973-01-01), which shows the Swiss ΔT table is consistent with the leap-second record; it does not measure the engine's real UT1 error. After the list expires the bound is a forecast, and after the CGPM change below it no longer holds by rule. Swiss's built-in table accepts `23:59:60` on all 27 IERS leap-second dates and refuses it on four non-leap dates (2018-12-31, 2020-12-31, 2024-06-30, 2025-12-31).

ΔT values used by Swiss (`deltat_ex`, `FLG_SWIEPH`): −1.95 s (1900-01-01), 29.12 s (1950-07-01), 63.97 s (2000-07-01), 68.84 s (2026-07-01), 74.58 s (2050-01-01), 82.81 s (2075-01-01), 93.18 s (2100-01-01). Swiss's tabulated values end in 2028 (`swephlib.c` `TABEND 2028`); after that they are an extrapolation, and upstream says ΔT "cannot be calculated with accuracy for the future" (§7). The Moshier tidal setting gives a different ΔT before 1955 (1900: −2.05 s), but Moshier is refused by the engine.

**Future UTC.** If no leap second is added after 2016, Swiss's extrapolated ΔT implies UT1 − UTC of −1.32 s in 2035, −5.40 s in 2050 and −24.0 s in 2100. The 27th CGPM (2022), Resolution 4 "On the use and future development of UTC" (BIPM, https://www.bipm.org/en/cgpm-2022/resolution-4), decides that the maximum permitted value of UT1 − UTC will be increased in, or before, 2035. The ChatGPT reviewer confirmed this at that primary BIPM page on 2026-10-22; this environment could not fetch it (proxy refused www.bipm.org), so the wording here follows the reviewer's reading, not a quotation. Consequently **the 0.9 s bound is not valid throughout 1900–2100**: for births from 2035 at the latest, \|UT1 − UTC\| is unbounded by rule and only forecastable, and the values above are Swiss-model projections, not limits. For a future birth the engine's "UTC as UT1" can then be wrong by tens of seconds, which is still a small Lagna effect (about 6′ at the equator for 24 s), while TT = UTC + 69.184 s would then be exact from the leap-second list and better than the ΔT model.

**Sidereal time (independent mathematics).** Against our own IERS Conventions 2010 eq. 5.32 expression (ERA + IAU 2006 polynomial + Δψ cos ε, Swiss nutation), Swiss's default sidereal time agrees to **0.0027″** for 1900–2049. From 2050-01-01 0h UT Swiss switches to its long-term model (`SEMOD_SIDT_DEFAULT = SEMOD_SIDT_LONGTERM`, `swephlib.c` lines 3460–3481; documented in §6.1), and the difference becomes −1.79″ to −1.91″, with a **−1.908″ step** at that instant. The Lagna steps by −1.66″ at New Delhi and −1.18″ at 60° N there. This is far below birth-time precision, but it is a deterministic discontinuity inside the proposed window and should be recorded as a Swiss convention. It is a measured behaviour of the pinned Swiss 2.10.03 implementation (version-specific), not an observation-based astronomical accuracy finding.

### 2.5 Sensitivity

Largest rates over 3,000 random instants 1900–2100: Moon 0.641″/s, Sun 0.042″/s; Lagna 16.4″/s (equator), 18.2″/s (13° N), 21.5″/s (28.6° N), 23.2″/s (34.2° N), 29.0″/s (45°), 43.1″/s (55°), 65.9″/s (60°), 110.2″/s (63°), 634.4″/s (66°).

Effect of a clock error, 2,000 random instants rotating over New Delhi, Mumbai and Kolkata (fraction of instants where the category changes):

| Clock error | max Lagna shift | Lagna Rashi | Lagna Navamsa | Moon Rashi | Moon Nakshatra Pada |
|---|---|---|---|---|---|
| 0.9 s (IERS rule on \|UT1−UTC\| while it stands) | 0.0054° | 0% | 0% | 0% | 0% |
| 1 min | 0.36° | 0.85% | 7.7% | 0.05% | 0.45% |
| 5 min | 1.79° | 4.3% | 36.6% | 0.2% | 1.45% |
| 23 min 20 s (+05:53:20 versus IST) | 8.35° | 19.7% | 100% | 1.05% | 7.0% |
| 38 min 29 s (LMT at 72.8777° E versus IST) | 13.76° | 33.4% | 100% | 1.35% | 11.3% |
| 60 min (war time versus IST) | 21.40° | 50.5% | 100% | 1.95% | 16.45% |

Local mean time minus IST for the synthetic Indian city centres (exact: 4 minutes of time per degree): Kavaratti −39.5 min, Mumbai −38.5, Srinagar −30.8, New Delhi −21.2, Kanyakumari −19.8, Leh −19.7, Bengaluru −19.6, Chennai −8.9, Kolkata +23.5, Guwahati +36.9, Port Blair +40.9. This is mean solar time only; a historical clock may have followed another meridian, and none of these is asserted to be a historical clock. The 38.5-minute Mumbai row in the table above is a **hypothetical sensitivity scenario** (what would change if a reading were on LMT and entered as IST), not evidence that any birth record used LMT.

## 3. Accuracy limitations

1. **Historical civil time is the dominant risk.** Before 1956 in Asia/Kolkata (and before 1970 in many zones) the offset of the clock that recorded a birth is not knowable from date and place. IANA states that its pre-1970 records are not comprehensive evidence of historical local clocks (`theory.html`), so a matching `zoneinfo` result (B2) shows only that Python reads IANA correctly, not that the clock was right. IANA's choice (railway time; war time from a single "dubious" source) can be wrong for a given household, and the engine cannot tell an IST reading from a Bombay or Calcutta reading entered as +05:30.
2. **UTC is not UT1.** From 1972 to 2027 the error is within the 0.9 s IERS rule (here only *implied under the Swiss ΔT model*, not measured), and 0.9 s changed no category in the samples. Before 1972 "UTC" is a reconstruction. After the IERS list expires (2027-06-28) and especially after 2035, UTC − UT1 may grow to tens of seconds by 2100.
3. **ΔT** is measured to 2028 and extrapolated after. For the Moon, 10 s of ΔT error is about 6″.
4. **Sidereal-time model step** of −1.9″ at 2050-01-01.
5. **Host tzdata build** changes historical offsets for some zones.
6. **Input parsing** accepts more ISO forms on Python ≥ 3.11 than earlier versions, so behaviour depends on the interpreter.
7. **No location/zone consistency check**; `Etc/*` and `UTC` keys are accepted for births.

## 4. Unsupported scenarios (today)

- Leap-second births (`23:59:60`): refused with a generic parse error.
- Local times without an offset: refused (correct; no guessing).
- Births recorded on clocks IANA does not model (for example Bombay or Calcutta local time after 1870, LMT of any Indian town after 1854): refused if entered with the true offset, silently mis-timed if entered as IST.
- Births before 1900 or after 2100 by **UTC** year.

## 5. Required safeguards (recommended)

| # | Safeguard | Why | Changes numbers? |
|---|---|---|---|
| S1 | Check the supported window on the **local civil date** (1900-01-01 to 2100-12-31) | T46–T51 | only at the edges |
| S2 | Distinguish `TIME_NONEXISTENT_LOCAL` (gap) from `TIME_OFFSET_MISMATCH`, and refuse `23:59:60` as `TIME_LEAP_SECOND_UNSUPPORTED` | clear user messages; no change in what is accepted | no |
| S3 | Accept one strict format (RFC 3339 profile: `YYYY-MM-DDTHH:MM[:SS[.ffffff]]±HH:MM[:SS]`) | removes Python-version dependence (T59, T60) | no |
| S4 | **RG-HIST**: refuse Asia/Kolkata births before 1956-01-01 with `HISTORICAL_CLOCK_UNVERIFIED` as a **temporary minimum, conservative policy to protect the first MVP**, until reviewed birthplace-clock evidence exists (see §7). It is not a claim that every clock from 1956 on, or every place in India before 1956, kept IST; the owner decides wider scope (other South Asian zones, any pre-1970 zone) | §2.2, §2.5 | refuses some inputs |
| S5 | Pin tzdata (an **engineering reproducibility fix with an SCI-03 dependency**, not an astrological convention): fix the package version **and** the TZif bytes (per-zone SHA-256 manifest), load zones deterministically at process start or through an isolated loader, never by changing the global `TZPATH` mid-process; emit the tzdata version in method metadata. See implementation plan P1 | §2.3 | possibly, for 8 Asian zones before 1956 |
| S6 | Refuse non-location keys (`Etc/*`, `UTC`, `GMT`) for births, and check zone against coordinates once the DATA-01 gazetteer exists | T56, T57, T63 | refuses some inputs |
| S7 | Record the time-scale assumption in output: "civil UTC used as UT1; TT from Swiss ΔT (Stephenson-Morrison-Hohenkerk 2016 / table to 2028 / extrapolated)" and flag dates after the IERS list expiry as projected | §2.4 | no |
| S8 | Keep `set_ephe_path` + `set_sid_mode` on every call under the lock, and forbid other code from calling swisseph outside it | Lagna report §3.4 state leak | no |

## 6. Recommendation for SCI-01h

Keep "civil UTC used as UT1, TT from Swiss's ΔT" for the MVP, disclose it by era, and do not switch to `swe.utc_to_jd` now: for 1972–2029 it would move inputs by at most 0.39 s (about 8″ of Lagna at New Delhi), up to 0.95 s in 2030–2033 under its no-new-leap-second assumption, and before 1972 and from 2034 it is identical. Revisit the policy before 2035, when leap-second practice is expected to change. Treat this as a time-scale convention, separate from the historical-clock policy (SCI-03, RG-HIST), which is where the real accuracy risk lies.

## 7. DATA-01 requirements for historical births (follow-up, not in this PR)

Before any pre-1956 Indian birth (or any gated zone and period) can be accepted, a reviewed, versioned DATA-01 package must record for each accepted case:

- **Historical birthplace**, as it was named and administered at the birth date, with coordinates and their source.
- **Clock source** of the recorded time: birth register or certificate, family recollection, railway time, civil or municipal time, local mean time, war time, or unknown.
- **Place-to-zone provenance**: why the place maps to a given IANA zone or to a sourced non-IANA offset, with the citation.
- **Jurisdiction-specific date coverage**: the dates for which that clock rule is documented for that place (for example a city that kept local time after 1906), with gaps refused.
- A refusal (`HISTORICAL_CLOCK_UNVERIFIED`) whenever any of these is unknown; verified city exceptions are added only through this reviewed list, never by extending the IANA model to every birthplace clock.

No offset is invented in this PR, and none may be added without a cited source.

## Appendix: synthetic time cases

The "Proposed outcome" column uses the codes from [supported-envelope.md](supported-envelope.md). "Engine today" uses the fixture's short names for the engine's current `ValueError` messages.

| ID | Input (zone) | Topic | Engine today | UTC used | Proposed outcome |
|---|---|---|---|---|---|
| T01 | `2000-01-01T17:30:00+05:30` Asia/Kolkata | modern IST | ACCEPT | 2000-01-01T12:00:00Z | ACCEPT |
| T02 | `1905-06-15T12:00:00+05:21:10` Asia/Kolkata | Madras time (IANA MMT +05:21:10) before 1906 | ACCEPT | 1905-06-15T06:38:50Z | HISTORICAL_CLOCK_UNVERIFIED (RG-HIST) unless clock confirmed |
| T03 | `1905-06-15T12:00:00+05:30` Asia/Kolkata | IST offset used before IST existed | OFFSET_MISMATCH |  | TIME_OFFSET_MISMATCH |
| T04 | `1905-12-31T23:59:59+05:21:10` Asia/Kolkata | last second of MMT | ACCEPT | 1905-12-31T18:38:49Z | HISTORICAL_CLOCK_UNVERIFIED (RG-HIST) |
| T05 | `1906-01-01T00:00:00+05:30` Asia/Kolkata | 1906-01-01 00:00 IST lies in the 8 min 50 s skipped by the MMT->IST change | OFFSET_MISMATCH |  | TIME_NONEXISTENT_LOCAL |
| T06 | `1906-01-01T00:08:50+05:30` Asia/Kolkata | first IST instant | ACCEPT | 1905-12-31T18:38:50Z | HISTORICAL_CLOCK_UNVERIFIED (RG-HIST) |
| T07 | `1906-01-01T00:05:00+05:21:10` Asia/Kolkata | MMT offset after the switch | OFFSET_MISMATCH |  | TIME_NONEXISTENT_LOCAL |
| T08 | `1941-10-01T00:30:00+05:30` Asia/Kolkata | war-time gap 1941-10-01 00:00-00:59, IST offset | OFFSET_MISMATCH |  | TIME_NONEXISTENT_LOCAL |
| T09 | `1941-10-01T00:30:00+06:30` Asia/Kolkata | war-time gap 1941-10-01 00:00-00:59, war offset | OFFSET_MISMATCH |  | TIME_NONEXISTENT_LOCAL |
| T10 | `1943-06-15T12:00:00+06:30` Asia/Kolkata | war time +06:30 (IANA, sourced from Shanks, 'dubious') | ACCEPT | 1943-06-15T05:30:00Z | HISTORICAL_CLOCK_UNVERIFIED (RG-HIST) |
| T11 | `1943-06-15T12:00:00+05:30` Asia/Kolkata | IST offset during war time | OFFSET_MISMATCH |  | TIME_OFFSET_MISMATCH |
| T12 | `1942-06-01T12:00:00+05:30` Asia/Kolkata | 1942 May 15 - Sep interlude at IST | ACCEPT | 1942-06-01T06:30:00Z | HISTORICAL_CLOCK_UNVERIFIED (RG-HIST) |
| T13 | `1942-05-14T23:30:00+06:30` Asia/Kolkata | 1942-05-14 23:30 repeated hour, first (war) reading | ACCEPT | 1942-05-14T17:00:00Z | ACCEPT only with explicit offset (fold) |
| T14 | `1942-05-14T23:30:00+05:30` Asia/Kolkata | 1942-05-14 23:30 repeated hour, second (IST) reading | ACCEPT | 1942-05-14T18:00:00Z | ACCEPT only with explicit offset (fold) |
| T15 | `1945-10-14T23:30:00+06:30` Asia/Kolkata | 1945-10-14 23:30 repeated hour, war reading | ACCEPT | 1945-10-14T17:00:00Z | ACCEPT only with explicit offset (fold) |
| T16 | `1945-10-14T23:30:00+05:30` Asia/Kolkata | 1945-10-14 23:30 repeated hour, IST reading | ACCEPT | 1945-10-14T18:00:00Z | ACCEPT only with explicit offset (fold) |
| T17 | `1930-06-15T12:00:00+04:51:31` Asia/Kolkata | offset = LMT computed from synthetic longitude 72.8777E (4h51m30.6s rounded to +04:51:31); NOT asserted to be historical Bombay Time | OFFSET_MISMATCH |  | HISTORICAL_CLOCK_UNVERIFIED (RG-HIST verified-clock list) |
| T18 | `1930-06-15T12:00:00+05:30` Asia/Kolkata | same clock reading entered as IST: accepted, possibly ~38.5 min wrong | ACCEPT | 1930-06-15T06:30:00Z | HISTORICAL_CLOCK_UNVERIFIED (RG-HIST) |
| T19 | `1930-06-15T12:00:00+05:53:20` Asia/Kolkata | Calcutta government time +05:53:20 (IANA comment, Shanks) is not modelled after 1870 | OFFSET_MISMATCH |  | HISTORICAL_CLOCK_UNVERIFIED (RG-HIST verified-clock list) |
| T20 | `2000-01-01T17:30:00+05:30` Asia/Calcutta | backward-compatible alias | ACCEPT | 2000-01-01T12:00:00Z | ACCEPT (normalise alias to Asia/Kolkata in output) |
| T21 | `1910-06-15T12:00:00+05:41:16` Asia/Kathmandu | Kathmandu LMT +05:41:16 until 1920 (IANA) | ACCEPT | 1910-06-15T06:18:44Z | HISTORICAL_CLOCK_UNVERIFIED (pre-1970 gate, owner scope) |
| T22 | `1990-06-15T12:00:00+05:45` Asia/Kathmandu | 45-minute zone | ACCEPT | 1990-06-15T06:15:00Z | ACCEPT |
| T23 | `1905-06-15T12:00:00+04:28:12` Asia/Karachi | Karachi LMT +04:28:12 until 1907 (IANA) | ACCEPT | 1905-06-15T07:31:48Z | HISTORICAL_CLOCK_UNVERIFIED (pre-1970 gate, owner scope) |
| T24 | `1930-06-15T12:00:00+05:53:20` Asia/Dhaka | Dhaka HMT +05:53:20 until 1941 (IANA) | ACCEPT | 1930-06-15T06:06:40Z | HISTORICAL_CLOCK_UNVERIFIED (pre-1970 gate, owner scope) |
| T25 | `2021-03-14T02:30:00-05:00` America/New_York | US DST gap, standard offset | OFFSET_MISMATCH |  | TIME_NONEXISTENT_LOCAL |
| T26 | `2021-03-14T02:30:00-04:00` America/New_York | US DST gap, daylight offset | OFFSET_MISMATCH |  | TIME_NONEXISTENT_LOCAL |
| T27 | `2021-11-07T01:30:00-04:00` America/New_York | US DST fold, first reading | ACCEPT | 2021-11-07T05:30:00Z | ACCEPT only with explicit offset (fold) |
| T28 | `2021-11-07T01:30:00-05:00` America/New_York | US DST fold, second reading | ACCEPT | 2021-11-07T06:30:00Z | ACCEPT only with explicit offset (fold) |
| T29 | `2021-03-28T01:30:00+00:00` Europe/London | UK DST gap | OFFSET_MISMATCH |  | TIME_NONEXISTENT_LOCAL |
| T30 | `2021-10-31T01:30:00+01:00` Europe/London | UK DST fold, first reading | ACCEPT | 2021-10-31T00:30:00Z | ACCEPT only with explicit offset (fold) |
| T31 | `2021-10-31T01:30:00+00:00` Europe/London | UK DST fold, second reading | ACCEPT | 2021-10-31T01:30:00Z | ACCEPT only with explicit offset (fold) |
| T32 | `2021-10-03T02:30:00+10:00` Australia/Sydney | southern-hemisphere DST gap | OFFSET_MISMATCH |  | TIME_NONEXISTENT_LOCAL |
| T33 | `2021-04-04T02:30:00+11:00` Australia/Sydney | southern-hemisphere DST fold, first reading | ACCEPT | 2021-04-03T15:30:00Z | ACCEPT only with explicit offset (fold) |
| T34 | `2021-04-04T02:30:00+10:00` Australia/Sydney | southern-hemisphere DST fold, second reading | ACCEPT | 2021-04-03T16:30:00Z | ACCEPT only with explicit offset (fold) |
| T35 | `2021-04-04T01:45:00+11:00` Australia/Lord_Howe | 30-minute DST fold (Lord Howe), first reading | ACCEPT | 2021-04-03T14:45:00Z | ACCEPT only with explicit offset (fold) |
| T36 | `2021-04-04T01:45:00+10:30` Australia/Lord_Howe | 30-minute DST fold (Lord Howe), second reading | ACCEPT | 2021-04-03T15:15:00Z | ACCEPT only with explicit offset (fold) |
| T37 | `2021-06-15T12:00:00+12:45` Pacific/Chatham | 45-minute zone (Chatham) | ACCEPT | 2021-06-14T23:15:00Z | ACCEPT |
| T38 | `2011-12-30T12:00:00+14:00` Pacific/Apia | Samoa skipped 2011-12-30 entirely, new offset | OFFSET_MISMATCH |  | TIME_NONEXISTENT_LOCAL |
| T39 | `2011-12-30T12:00:00-10:00` Pacific/Apia | Samoa skipped 2011-12-30 entirely, old offset | OFFSET_MISMATCH |  | TIME_NONEXISTENT_LOCAL |
| T40 | `2016-12-31T23:59:60+00:00` UTC | positive leap second (IERS 2016-12-31) in UTC | PARSE |  | TIME_LEAP_SECOND_UNSUPPORTED |
| T41 | `2017-01-01T05:29:60+05:30` Asia/Kolkata | the same leap second read on an IST clock | PARSE |  | TIME_LEAP_SECOND_UNSUPPORTED |
| T42 | `1900-02-29T12:00:00+05:21:10` Asia/Kolkata | 1900 is not a leap year | PARSE |  | DATE_INVALID |
| T43 | `2000-02-29T12:00:00+05:30` Asia/Kolkata | 2000 is a leap year | ACCEPT | 2000-02-29T06:30:00Z | ACCEPT |
| T44 | `2024-02-29T12:00:00+05:30` Asia/Kolkata | 2024 is a leap year | ACCEPT | 2024-02-29T06:30:00Z | ACCEPT |
| T45 | `2100-02-29T12:00:00+05:30` Asia/Kolkata | 2100 is not a leap year | PARSE |  | DATE_INVALID |
| T46 | `1900-01-01T00:00:00+05:21:10` Asia/Kolkata | local 1900-01-01 00:00 is UTC 1899: refused although the local date is in the window | RANGE |  | ACCEPT by local date (then RG-HIST for Asia/Kolkata pre-1956) |
| T47 | `1900-01-01T05:21:10+05:21:10` Asia/Kolkata | first instant the UTC-year rule accepts in Asia/Kolkata | ACCEPT | 1900-01-01T00:00:00Z | ACCEPT by local date (then RG-HIST) |
| T48 | `2100-12-31T23:59:59+05:30` Asia/Kolkata | last local second of 2100 in IST | ACCEPT | 2100-12-31T18:29:59Z | ACCEPT |
| T49 | `2101-01-01T05:29:59+05:30` Asia/Kolkata | local 2101-01-01 is UTC 2100: accepted although the local date is outside the window | ACCEPT | 2100-12-31T23:59:59Z | DATE_OUTSIDE_SUPPORTED_RANGE |
| T50 | `2100-12-31T20:00:00-05:00` America/New_York | west of Greenwich: local 2100-12-31 is UTC 2101, refused | RANGE |  | ACCEPT |
| T51 | `1899-12-31T23:59:59-05:00` America/New_York | west of Greenwich: local 1899-12-31 is UTC 1900, accepted | ACCEPT | 1900-01-01T04:59:59Z | DATE_OUTSIDE_SUPPORTED_RANGE |
| T52 | `2100-07-01T12:00:00-04:00` America/New_York | future DST from projected rule | ACCEPT | 2100-07-01T16:00:00Z | ACCEPT with FUTURE_CIVIL_TIME_PROJECTED disclosure |
| T53 | `2000-01-01T12:00:00Z` Asia/Kolkata | Z suffix with an Indian zone | OFFSET_MISMATCH |  | TIME_OFFSET_MISMATCH |
| T54 | `2000-01-01T17:30:00` Asia/Kolkata | naive local time | NAIVE |  | TIME_OFFSET_REQUIRED |
| T55 | `2000-01-01T17:30:00+05:30` IST | abbreviation is not an IANA key | TZ_INVALID |  | TIMEZONE_INVALID |
| T56 | `2000-01-01T17:00:00+05:00` Etc/GMT-5 | POSIX-sign zone Etc/GMT-5 means UTC+5 | ACCEPT | 2000-01-01T12:00:00Z | TIMEZONE_NOT_LOCATION_BASED (refuse Etc/* and UTC for births) |
| T57 | `2000-01-01T12:00:00+00:00` UTC | UTC zone with Indian coordinates | ACCEPT | 2000-01-01T12:00:00Z | TIMEZONE_NOT_LOCATION_BASED |
| T58 | `2000-01-01T17:30:00.123456+05:30` Asia/Kolkata | microseconds are kept | ACCEPT | 2000-01-01T12:00:00.123456Z | ACCEPT (or truncate to seconds by documented rule) |
| T59 | `2000-01-01 17:30:00+05:30` Asia/Kolkata | space separator accepted by Python 3.11+ | ACCEPT | 2000-01-01T12:00:00Z | Pin one strict format (RFC 3339 profile) |
| T60 | `20000101T173000+0530` Asia/Kolkata | ISO basic format accepted by Python 3.11+ only | ACCEPT | 2000-01-01T12:00:00Z | Pin one strict format (RFC 3339 profile) |
| T61 | `1942-06-15T12:00:00+06:00` Asia/Colombo | Colombo war time (+05:30 + 0:30 save) | ACCEPT | 1942-06-15T06:00:00Z | HISTORICAL_CLOCK_UNVERIFIED (pre-1970 gate, owner scope) |
| T62 | `1943-06-15T12:00:00+09:00` Asia/Yangon | Yangon occupation time +09:00 | ACCEPT | 1943-06-15T03:00:00Z | HISTORICAL_CLOCK_UNVERIFIED (pre-1970 gate, owner scope) |
| T63 | `2000-01-01T17:30:00+05:30` Asia/Kolkata | Asia/Kolkata with New York coordinates is not checked | ACCEPT | 2000-01-01T12:00:00Z | LOCATION_TIMEZONE_INCONSISTENT (DATA-01 gazetteer) |
