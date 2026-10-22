# Workstream A: Lagna through `houses_ex(..., b"P")` versus `b"W"`

**Status:** evidence and recommendation for SCI-01e, SCI-01f and SCI-01g. PENDING.
**Base:** `d8193c692d52aa12595f81c227638a061605a3d9`. Swiss Ephemeris 2.10.03 (pyswisseph 2.10.3.2), pinned `sepl_18.se1`/`semo_18.se1`.
**Probe:** `tests/kun02/lagna_probe.py`; fixture `tests/kun02/fixtures/lagna_grid.json`; invariants A1–A12.

## 1. What the engine does today

`src/sabpuja_kundali/engine.py`:

- Line 96 accepts latitude in the open interval (−89, 89).
- Lines 105–108 build the Julian day from the UTC instant (`swe.julday`), used as UT.
- Lines 115–116, under `_SWISS_LOCK`, call `swe.set_ephe_path(folder)` and `swe.set_sid_mode(SIDM_LAHIRI, 0, 0)` on **every** request.
- Line 130 calls `swe.houses_ex(julian_day, lat, lon, b"P", swe.FLG_SIDEREAL)` and reads only `ascmc[0]`. A `swisseph.Error` becomes `ChartComputationError("ASCENDANT_UNCOMPUTABLE")`.
- Houses for D1 are whole-sign from the Lagna Rashi (`rules.whole_sign_house`); Placidus cusps are never used.

## 2. What Swiss Ephemeris does (source at `aloistr/swisseph@c69c14a`)

Read from `swehouse.c` (SHA-256 `bb17029e5fc2318885bcb8bfba72af3b7cd2d6437b4013195e953e35dd06c254`):

| Fact | Where |
|---|---|
| In sidereal mode without special bits, houses are computed tropically and then the ayanamsha of `swe_get_ayanamsa_ex(tjde, iflag)` (true, nutation included) is subtracted from every cusp and from `ascmc` | `sidereal_houses_trad`, lines 535–587 |
| For `W` the tropical computation is run as `E` (equal houses) and each cusp is then floored to its 30° sign start **after** the ayanamsha is subtracted, so W cusps are sidereal sign boundaries | lines 562–573 |
| The ascendant is computed **before** the house-system switch, as `Asc1(armc + 90, lat, ...)`; it is the same code for every house system | `CalcH`, line 973 |
| Placidus: `if (fabs(fi) >= 90 - ekl)` the routine sets `ERR`, writes "within polar circle, switched to Porphyry" and falls back; `ekl` is the true obliquity of date | lines 1830–1834 |
| Equal/whole sign: if the ascendant lies more than 180° from the MC (only possible beyond the polar circle), it is replaced by the opposite point, "we swap AC/DC if AC is on wrong side" | `case 'E'`, lines 994–1001 |
| If `FLG_SIDEREAL` is passed and no sidereal mode was ever set, Swiss silently uses **Fagan/Bradley** | `swe_houses_ex2`, line 229 |

pyswisseph turns the Placidus `ERR` into `swisseph.Error` and discards the Porphyry fallback, which is why the engine sees an exception.

Upstream documentation (`doc/swisseph.htm`, §6.4 "House cusps beyond the polar circle"): "We make sure that the ascendant is always in the eastern hemisphere"; Placidus and Koch "sometimes can, sometimes cannot be computed beyond the polar circles"; Swiss "switches to Porphyry houses … and returns a warning".

## 3. Controlled comparison

### 3.1 Inputs (all synthetic)

- **Structured grid:** 36 places (11 Indian city centres, equator, both sides of the date line, southern and northern mid and high latitudes, the ±66.0° band edges, ±66.5° just equatorward of the polar circle, three places beyond the polar circle, and ±88.99° at the current acceptance limit) × 12 years from 1900 to 2100 × 12 months × 2 days × 12 UTC hours = **124,416 points**.
- **Random within the band:** 60,000 points, seed 20261022, \|lat\| ≤ 66.0°, any longitude, UT uniformly over 1899-12-31 to 2101-01-01.
- **Random high latitude:** 20,000 points, seed 20261023, 66.0° ≤ \|lat\| ≤ 88.99°.

For every point the probe calls `b"P"` and `b"W"` with `FLG_SIDEREAL` and `b"W"` tropically, reads the true Lahiri ayanamsha with `get_ayanamsa_ex_ut(jd, FLG_SWIEPH)` and the true obliquity with `ECL_NUT`, and then checks:

- P against W bit for bit (`float.hex`), plus MC and ARMC;
- sidereal ascendant against tropical ascendant minus the true ayanamsha (Lahiri residual);
- the tropical ascendant against our own spherical-trigonometry formula `atan2(cos θ, −(sin θ cos ε + tan φ sin ε))` using Swiss's ARMC θ and true obliquity ε (independent residual; also whether the formula gives the same point or the opposite one);
- whether the W ascendant is the **rising** ecliptic point: its altitude from our own equatorial/horizontal transformation is zero and its hour angle is east of the meridian;
- whether W cusps are exactly `30·k`, `30·(k+1)`, … with `k` the Lagna Rashi index from `rules.sign_index`.

### 3.2 Results

Structured grid:

| \|lat\| band | samples | P refused | P = W bit-identical | max \|P−W\| (″) | max Lahiri residual (″) | max independent residual (″) | naive formula gives setting point | W not rising | W cusp failures |
|---|---|---|---|---|---|---|---|---|---|
| [0,10) | 24,192 | 0 | 24,192 | 0.0 | 1.4e-07 | 1.1e-08 | 0 | 0 | 0 |
| [10,20) | 20,736 | 0 | 20,736 | 0.0 | 1.4e-07 | 1.8e-08 | 0 | 0 | 0 |
| [20,30) | 10,368 | 0 | 10,368 | 0.0 | 1.3e-07 | 2.6e-08 | 0 | 0 | 0 |
| [30,40) | 20,736 | 0 | 20,736 | 0.0 | 1.4e-07 | 3.2e-08 | 0 | 0 | 0 |
| [40,50) | 3,456 | 0 | 3,456 | 0.0 | 1.3e-07 | 4.5e-08 | 0 | 0 | 0 |
| [50,60) | 6,912 | 0 | 6,912 | 0.0 | 1.3e-07 | 8.3e-08 | 0 | 0 | 0 |
| [60,66) | 6,912 | 0 | 6,912 | 0.0 | 1.3e-07 | 2.9e-07 | 0 | 0 | 0 |
| 66.0 exactly | 6,912 | 0 | 6,912 | 0.0 | 1.3e-07 | 1.3e-06 | 0 | 0 | 0 |
| (66, polar circle) | 6,912 | 0 | 6,912 | 0.0 | 1.3e-07 | 1.2e-05 | 0 | 0 | 0 |
| [polar circle, 89) | 17,280 | 17,280 | n/a | n/a | 1.3e-07 | 2.4e-07 | 6,191 | 0 | 0 |

Random samples:

| Sample | \|lat\| band | samples | P refused | P = W bit-identical | max Lahiri residual (″) | max independent residual (″) | naive formula gives setting point | W not rising |
|---|---|---|---|---|---|---|---|---|
| within 66° | [0,66) (7 bands) | 60,000 | 0 | 60,000 | 1.2e-07 | 6.8e-07 | 0 | 0 |
| 66°–88.99° | (66, polar circle) | 476 | 0 | 476 | 9.5e-08 | 2.2e-06 | 0 | 0 |
| 66°–88.99° | [polar circle, 89) | 19,524 | 19,524 | n/a | 1.3e-07 | 6.1e-07 | 6,197 | 0 |

By place group (structured grid): every Indian city (38,016 points), the equator (13,824), the date line (10,368), southern (13,824 + 3,456 high) and northern (6,912 + 6,912 high) groups and both band edges have **zero** P refusals and zero P≠W. All 17,280 points at or beyond the polar circle are refused by P.

**In total 167,612 P/W comparisons were possible, and all 167,612 are bit-identical in ascendant, MC and ARMC.**

### 3.3 Where exactly Placidus fails (A4)

Bisecting latitude on eight dates, `b"P"` starts to raise at exactly 90° − true obliquity, north and south:

| Date (12:00 UT) | 90° − ε_true | P fails from (N and S) | difference |
|---|---|---|---|
| 1900-01-01 | 66.548345° | 66.548345° | 1.0e-08″ |
| 1925-07-01 | 66.552663° | 66.552663° | −3.0e-09″ |
| 1956-03-21 | 66.555655° | 66.555655° | 1.0e-10″ |
| 2000-01-01 | 66.562323° | 66.562323° | 0 |
| 2024-06-01 | 66.561517° | 66.561517° | 1.0e-10″ |
| 2050-01-01 | 66.568711° | 66.568711° | 0 |
| 2075-09-01 | 66.570939° | 66.570939° | 5.1e-11″ |
| 2100-12-31 | 66.571801° | 66.571801° | 1.0e-10″ |

Sampled every 10 days across 1900–2100, the polar-circle latitude ranges from **66.546714° to 66.575237°** (the obliquity decreases about 47″ per century and nutation adds ±9.2″). The engine's refusal latitude therefore moves with the birth date. Envelope probe confirmation: at latitude 66.55°, a 1900-01-01 birth is refused (`ASCENDANT_UNCOMPUTABLE`) while a 2100-12-31 birth is accepted.

### 3.4 Lahiri in the sidereal Lagna (A5, A11)

- Sidereal ascendant = tropical ascendant − **true** Lahiri ayanamsha to ≤ 1.4e-7″ on all 204,416 points. The Lagna and the planets use the same ayanamsha: for all eight bodies, `calc_ut(..., FLG_SIDEREAL)` equals tropical apparent longitude minus the same true ayanamsha to 4.1e-10″ (2,000 random instants); against the **mean** ayanamsha the difference reaches 18.78″ (nutation in longitude).
- The mode is really Lahiri. At J2000 the same call under other modes differs by: Lahiri ICRC (46) −1.09″, Lahiri 1940 (43) −53.17″, Lahiri VP285 (44) +23.00″, Krishnamurti −348.67″, Raman −5,206.68″, Fagan/Bradley +3,179.55″.
- Wrong configurations, each in a fresh interpreter (New Delhi, J2000): sidereal mode never set → Fagan/Bradley, −3,179.55″; `FLG_SIDEREAL` omitted → tropical, +85,871.60″ (23.85°); `FLG_NONUT` added → +0.228″; Krishnamurti → +348.67″; `SIDBIT_PREC_ORIG` → +0.0175″. An **empty ephemeris directory changes the ascendant by 0.000″**, because houses do not read `.se1` files; only the planets fall back to Moshier (and the engine refuses them).
- **State leak (new finding).** After `set_sid_mode(SIDM_LAHIRI | SIDBIT_PREC_ORIG)`, calling `set_sid_mode(SIDM_LAHIRI)` alone still gives the +0.0175″ value. Only `set_ephe_path` restores the default. The engine is safe because it calls both on every request inside its lock; `test_engine_resets_leaked_swiss_state` pins that behaviour.

### 3.5 Beyond the polar circle (A2, A6, A7)

`b"W"` returns an ascendant everywhere up to ±88.99°. Our independent formula returns the **setting** point (180° away) in 6,191 of 17,280 structured and 6,197 of 19,524 random points beyond the polar circle; the Swiss W value is the rising (eastern-horizon) point in **every** case, with altitude below 3.1e-8″. Equatorward of the polar circle the formula and Swiss agree to ≤ 1.2e-5″ (worst at 66.5°, where the formula is ill-conditioned) and the opposite case never occurs.

The ascendant is extremely time-sensitive at high latitude. Maximum Lagna rate from 3,000 random instants (time probe): 16.4″/s at 0°, 21.5″/s at 28.6°, 29.0″/s at 45°, 65.9″/s at 60°, 110.2″/s at 63°, **634.4″/s at 66°** (10.6° per minute of birth time).

### 3.6 D1 and D9 internal consistency (A8–A10, A12)

- **W cusps** are exact multiples of 30° starting at the Lagna Rashi on all 204,416 points.
- **Placement agreement:** 90,720 checks (Indian, equatorial, southern and northern places × 6 years × 4 months × 4 hours × 9 bodies including exact Ketu): the D1 whole-sign house from `rules.whole_sign_house` equals the house read from the W cusps; P and W give the same D1 houses and the same D9 Lagna; `rules.navamsa_sign` equals an independent implementation of the classical element rule (fire from Mesha, earth from Makara, air from Tula, water from Karka); the D9 whole-sign house from the D9 Lagna agrees with the classical rule. **0 mismatches.**
- **Boundary sweep:** for New Delhi, Sydney and 66.0° N on 2024-03-21, every Lagna Navamsa crossing in a UTC day (109, 109 and 108 crossings) was bracketed to 1e-10 day (8.6 µs). On both sides of each crossing P = W, cusp 1 = Rashi start, and the Navamsa rule matches the classical rule, and the segment advances by exactly one. **0 failures.**
- **Engine cases:** for five accepted synthetic requests (New Delhi 2000, Mumbai 1975, Sydney 2024-02-29, Quito 1956, 66.0° N 2050) the engine's Lagna display, Rashi, Navamsa and every whole-sign house equal the values derived from `b"W"`. The Tromsø 69.65° N request is refused today with `ASCENDANT_UNCOMPUTABLE`; W returns 150.547°.

## 4. Known differences and edge cases

| # | Situation | P | W | Consequence |
|---|---|---|---|---|
| 1 | \|lat\| < 90° − ε_true (always true for \|lat\| ≤ 66.0°) | ascendant | identical ascendant | none |
| 2 | 90° − ε_true ≤ \|lat\| < 89° | `swisseph.Error` → `ASCENDANT_UNCOMPUTABLE` | ascendant (rising point, swapped if needed) | W accepts inputs P refuses |
| 3 | 66.5467° ≤ \|lat\| ≤ 66.5752° | refused or accepted depending on date | always computed | date-dependent support disappears |
| 4 | Sidereal mode never set in process | Fagan/Bradley | Fagan/Bradley | both wrong by 0.88°; engine sets mode every call |
| 5 | `SIDBIT_PREC_ORIG` used earlier in process | +0.0175″ until `set_ephe_path` | same | engine resets every call |
| 6 | 2050-01-01 0h UT | −1.908″ step in Swiss sidereal time (model switch) | same | Lagna steps ≈ −1.7″ at New Delhi; see birth-time report |
| 7 | Exact Lagna on a Rashi or Navamsa edge | categories from the unrounded value, half-open | same | consistent on both sides (sweep) |

## 5. Recommendation

1. **SCI-01e:** compute the sidereal Lagna as `ascmc[0]` of `swe.houses_ex(jd_ut, lat, lon, b"W", swe.FLG_SIDEREAL)`, with `set_ephe_path` and `set_sid_mode(SIDM_LAHIRI, 0, 0)` called under the lock on every request (as today). This is a **reliability change, not a method change**: the ascendant definition (tropical rising point of date from apparent sidereal time and true obliquity, minus true Lahiri ayanamsha) and every number equatorward of the polar circle stay bit-identical.
2. **Do not ship W on its own.** Changing P to W by itself would start accepting births between the polar circle and ±89°, where the Lagna changes by more than 10° per minute of birth time. Ship it together with, or after, the SCI-01g latitude band.
3. **SCI-01g:** support \|lat\| ≤ 66.0° (inclusive), refuse outside with a fixed `LATITUDE_OUTSIDE_SUPPORTED_BAND` code regardless of date. The band edge stays at least 0.5467° (about 60 km) inside the earliest polar circle of the window. Keep `ASCENDANT_UNCOMPUTABLE` as a defensive error that should become unreachable.
4. **SCI-01f:** keep whole-sign D1 houses from the Lagna Rashi, and define D9 houses as whole-sign from the D9 Lagna (the Navamsa sign of the unrounded Lagna). Evidence: A8–A10.
5. Disclose high-latitude birth-time sensitivity above about 60°, where one minute moves the Lagna by more than 1°.

P and W are **not** interchangeable as calls: they differ in which inputs fail. They are interchangeable as ascendant values wherever both are defined, on every sample tested.
