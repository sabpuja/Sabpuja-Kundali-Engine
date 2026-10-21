# Independent reference-source register

**Document ID:** SP-KUN-ACC-REF | **Work package:** CLAUDE-003 / KUN-01 Phase B | **Status:** PROPOSED, for ChatGPT QA review

Rules that apply to every row:
- **The engine's own output is never a reference.** Neither is any program that calls Swiss Ephemeris internally; those can only show method agreement (class M below).
- A reference value is usable only with its source, version, retrieval date, exact query or command, and file hashes recorded in the fixture (see [golden-chart-spec.md](golden-chart-spec.md)).
- This register is for offline QA. Nothing here becomes a runtime dependency; the Sabpuja runtime stays self-hosted Swiss Ephemeris.
- **No fixture may be called independent, and no tolerance may be frozen on a source, until that source's reproducible input bytes (exact query text, script and lockfile, or file), raw output bytes, SHA-256 of both, retrieval date and confirmed reuse rights are recorded.** The "Obtained" column below shows where each source stands.
- "Verified here" means the item was downloaded or opened in the CLAUDE-003 container on 2026-10-21 and its hash or content was checked. It does not mean any comparison was run. **No reference comparison has been run in this package.**

## Independence classes

| Class | Meaning | Can support an accuracy claim? |
|---|---|---|
| I-data | Different ephemeris data and different code from the engine (in this register only INPOP) | Yes |
| I-code | Different code, same data family (JPL DE) | Partly: independent code paths, but **shares JPL dynamical models and observational fits** with Swiss (whose `.se1` files are compressed DE431) and with every other JPL-based path |
| I-pub | Published table from an authority, reproduced by citation | Yes, at the table's printed precision |
| D | Definition source (says what a convention means) | No, defines what is expected |
| M | Method cross-check (other astrology software, usually Swiss-based) | No, only shows convention agreement |

## Register

| ID | Source | Version / provenance | What it gives | Class | Availability from this container | Licence / rights |
|---|---|---|---|---|---|---|
| R-01 | **JPL Horizons** (Solar System Dynamics, JPL) | Horizons system version and DE440/DE441 as printed in each response header | Geocentric apparent RA/Dec (quantity 2), ICRF apparent (quantity 45), astrometric ICRF RA/Dec (quantity 1), observer ecliptic longitude/latitude of date (quantity 31), all with "extra precision" and **TT** time input | I-code (JPL DE440, JPL code) | **Not reachable** (`ssd.jpl.nasa.gov` connection refused). Must be generated on another machine; raw response text committed with its SHA-256 | US Government work; cite JPL SSD |
| R-02 | **Skyfield** (B. Rhodes) + **DE421** via `skyfield-data` | `skyfield` 1.55 wheel SHA-256 `9f98964855067460c94aa81a337194136f4a97a62ba8bbbfac1b8556f2b66ad4`; `skyfield-data` 7.0.0 wheel `4279f999f7f8c5ef5d8bf1b714f301a0844ae5df3a3f0d23610b20d8789073f5`; inside it `de421.bsp` `a20a7139da04cbc462454634918e9a9ca69127044e2cc9d4f9c16e238d2deedc` | Apparent geocentric positions, IAU 2006/2000A frame transformations, independent of Swiss code | I-code | **Verified here** (PyPI reachable). DE421 spans **1899-07-29 to 2053-10-09** only (read from the SPK segment table) | MIT (code, packaging); JPL ephemeris data freely distributed |
| R-02b | **DE440s** or **DE440** SPK from NAIF, used with Skyfield or `jplephem` | `de440s.bsp` covers 1849–2150; file SHA-256 to be recorded at download | Same as R-02 for 2053–2100 and as a newer DE cross-check | I-code | **Not reachable** (`naif.jpl.nasa.gov` refused). Download on another machine, record SHA-256, carry in as a QA input (never committed to Git) | US Government work |
| R-03 | **INPOP** (IMCCE, Paris Observatory) SPK, e.g. INPOP21a | Version and SHA-256 to record at download | A planetary and lunar ephemeris fitted by a different team from JPL: the only **I-data** source for planets in this register | I-data | Not tested here; expect off-machine download | IMCCE terms to be checked before use |
| R-04 | **ERFA** via `pyerfa` (BSD re-implementation of IAU SOFA) | `pyerfa` 2.0.1.5 wheel SHA-256 `0e43c7194e3242083f2350b46c09fd4bf8ba1bcc0ebd1460b98fc47fe2389906` | Greenwich apparent sidereal time (IAU 2006/2000A), true obliquity, nutation, precession angles. Basis of the independent **ascendant** and **ayanamsa** reimplementations | I-code | **Verified here** | BSD-3-Clause |
| R-05 | **Indian Astronomical Ephemeris** (Positional Astronomy Centre, India Meteorological Department, Kolkata), yearly volumes | Edition, page and table per value. Upstream Swiss documentation cites IAE 1989 p. 512/525/556 and IAE 2019 p. 385/427/429/445 | Published **true and mean Lahiri ayanamsha** (0.1" printed precision). To check: whether volumes also print Nirayana (sidereal) longitudes of planets and a mean node, which would make them a direct Vedic reference | I-pub | **Not available here.** Owner or QA must obtain scans/volumes | Government publication; reproduce numeric values with citation only; confirm reuse terms |
| R-06 | **Mean lunar node polynomial** from lunar theory: Chapront-Touzé & Chapront (1988) ELP2000-82B / Simon et al. (1994, A&A 282, 663) mean elements; as quoted in Meeus, *Astronomical Algorithms* (2nd ed. 1998) ch. 47 | Coefficients transcribed with citation and checked by a second reader | Mean longitude of the ascending node referred to the **mean equinox of date** | I-code **only if** the owner adopts this polynomial as the definition (SCI-01b b); otherwise D | Formula only; nothing to download | Published scientific formulae; cite, do not copy book text |
| R-07 | **IERS Earth orientation data** (`finals2000A`, leap seconds) | `finals2000A.all` inside `skyfield-data` 7.0.0, SHA-256 `d0d9c214fb11f4d1f9418f4075ec4310005f906674a0c4fa3a28232d4d9dd38d`; `astropy-iers-data` 0.2026.10.19.0.52.1 wheel `14665720aa481c7b97dfd104d7218b38ed7e2ba30a70ff53a5c26a0e14d4025c` | UT1−UTC and TAI−UTC to quantify the "UTC as UT1" limitation (SCI-01h); not used to define expected values | I-pub | **Verified here** (bundled copies; `iers.org` itself not reachable) | IERS data free with citation; packaging BSD-3 / MIT |
| R-08 | **IANA tz database** | Container system tzdata `2026e` (`/usr/share/zoneinfo/tzdata.zi`); PyPI `tzdata` 2026.5 wheel `b683bd1b6659ddcd810ff02ad09ba821d4bf1065072805063eb35c49617905ac`; source comments read at `github.com/eggert/tz` commit `48e835949dac7c3d1e13408392fd41492052e095` | UTC offsets for fixtures. **Not independent of the engine**, which uses the same database; only checks that the engine applies IANA correctly. **Not historical time truth:** IANA's theory states pre-1970 data need not represent every locality | D | Verified here (git clone of the tz source; `data.iana.org` refused) | Public domain |
| R-09 | **Historical Indian time-keeping sources** cited by IANA: Reed & Low, *The Indian Year Book 1936-37*; Shanks, *International Atlas*; Prasad (2016); Oldham (1899) | Citation as given in the IANA `asia` file | Evidence for what clocks Bombay, Calcutta and Madras actually used pre-1956 | I-pub (partial) | Citations only; IANA itself calls Shanks "dubious" for 1941–1945 | Cite only |
| R-10 | **Swiss Ephemeris source and documentation** at the pinned commit `c69c14adb7a0f94829586ffd92cd422aacb21e86` (`sweph.h`, `swephexp.h`, `doc/swisseph.htm`) | Read from a filtered git clone of `aloistr/swisseph`; `SE_VERSION "2.10.03"` | Definitions of ayanamsha modes, defaults (precession Vondrák 2011, nutation `SEMOD_NUT_IAU_2000B`, Delta T `SEMOD_DELTAT_STEPHENSON_ETC_2016`), documented Horizons agreement and polar-house behaviour | D | **Verified here** | AGPL-3.0 / Swiss Ephemeris licence |
| R-11 | **Classical rule texts** for Rashi, Nakshatra, Pada and Navamsa (e.g. *Brihat Parashara Hora Shastra*, Varga chapter) | Translation and chapter cited | Rule definitions for the QA harness's independent category oracle | D | Citation | Rules are facts; do not copy translated text |
| R-12 | **Other Jyotish software** (e.g. Jagannatha Hora, commercial Kundali tools, Swiss-based Python libraries) | Program version | Whether another tool using "Lahiri, mean node, whole sign" shows the same signs and houses | M | Not used | Do not copy outputs into Git without rights |

## Obtained status (input bytes, raw output, rights)

| ID | Input bytes recorded | Raw output recorded | Reuse rights confirmed | Status |
|---|---|---|---|---|
| R-01 Horizons | No | No | Likely (US Gov work); confirm citation terms | **NOT OBTAINED** |
| R-02 Skyfield + DE421 | Wheel hashes recorded | No outputs generated (by design) | Yes (MIT; JPL data freely distributed) | Software obtained; no fixtures |
| R-02b DE440s | No | No | Likely (US Gov work) | **NOT OBTAINED** |
| R-03 INPOP | No | No | **No**: IMCCE terms unchecked | **NOT OBTAINED** |
| R-04 ERFA | Wheel hash recorded | No | Yes (BSD-3) | Software obtained; no derivation reviewed |
| R-05 IAE | No | No | **No**: reuse terms unknown | **NOT OBTAINED** |
| R-06 node polynomial | No | No | Formula citation only | Pending owner node definition (SCI-01b) |
| R-07 IERS | File hashes recorded | n/a | Citation | Obtained (bundled copies) |
| R-08 IANA | Version and commit recorded | n/a | Public domain | Obtained; not historical truth |

## Why each item is needed

- **Tropical positions** need two code paths: R-02/R-02b (Skyfield, IAU 2006/2000A, close to Swiss's models) and R-01 (Horizons, IAU 1976/1980 for of-date frames, plus DE440). Agreement through both rules out a code or frame slip in either, but **not** an error shared by all JPL ephemerides, since Skyfield, Horizons and Swiss all rest on JPL dynamical models and fits. R-03 (INPOP) is the only non-JPL path and is required for at least a subset of fixtures before any claim of data-independent validation.
- **Ayanamsa** needs a reimplementation of the approved written definition with R-04 (precession and nutation from ERFA) plus the published IAE tables (R-05) as an external check. Neither may call Swiss.
- **Mean node** has no observational truth, and Swiss's mean node and R-06 polynomials are different conventions (golden spec section 4.3). R-06 is a reference only if the owner chooses a published polynomial as the definition (SCI-01b option b); otherwise node checks are definition-conformance only.
- **Ascendant** is computed in the reference from R-04 sidereal time and obliquity with the standard spherical-astronomy formula, from the same UT assumption as the engine (SCI-01h).
- **Categories** (Rashi, Nakshatra, Pada, D9, houses) come from an independent oracle written from R-11 rules, applied to the reference longitudes. The existing `tests/boundary_oracle.py` is a good model but it lives beside the engine tests and checks exact arithmetic on engine values, so it is **self-consistency**, not independent validation.

## Conversions needed to make sources comparable

| Issue | Engine (Swiss default flags) | Reference handling |
|---|---|---|
| Time scale | Input civil UTC used as UT1; Swiss adds its own Delta T to get TT | Planets and nodes: compare at the **same TT**. Generate references in TT (Horizons "TT" time input; Skyfield `ts.tt`) from the TT the engine used, `jd_ut + swe.deltat(jd_ut)`, recorded per fixture. Delta T is tested separately. Ascendant: compare at the same UT1 (civil UTC taken as UT1 in both) |
| Frame | ICRS → precession Vondrák 2011, nutation IAU 2000B → true ecliptic and equinox of date | Skyfield: IAU 2006 precession, IAU 2000A nutation (expected mas-level difference). Horizons quantity 31: IAU 1976/1980; Swiss documents a constant 53 mas reference-ecliptic offset versus Horizons, and IAU 1976's precession rate error of about 3 mas/yr adds up to about 0.3" at 1900 and 2100 |
| Apparent vs geometric | Apparent: light-time, aberration, light deflection | Use apparent quantities only (Horizons 2/31/45; Skyfield `.apparent()`). Astrometric quantities only for the frame-free ICRF check |
| Geocentric vs topocentric | Geocentric | Geocentric: Horizons site code `500` (geocentre), Skyfield `earth.at(t)` |
| Nutation in sidereal values | Sidereal = tropical of date − **true** ayanamsha, so nutation cancels | Reference sidereal = reference tropical of date − reference true ayanamsha, or equivalently tropical referred to mean equinox − mean ayanamsha |
| Mean node frame | Swiss mean node + nutation, then − true ayanamsha | R-06 polynomial (mean equinox of date) − reference mean ayanamsha. Light-time and aberration are not applied to the mean node |
| Ayanamsa epoch | 21 Mar 1956 0h **TT** | Reference uses the same epoch and time scale; IAE "mean" tables have an epoch ambiguity (upstream asks whether "1989.0" is 0h or 12h TT), so compare to IAE **true** ayanamsha tables first |
| Angles | Degrees in [0, 360) | Circular difference `((a − b + 180) mod 360) − 180`; never plain subtraction |
| Years | Gregorian, astronomical numbering | All fixtures are 1900–2100, so no year-0 or Julian issues |

## Gaps recorded as risks

Horizons, NAIF and IMCCE are unreachable from this container; IAE volumes are not in hand; DE421 stops in 2053; tz validation cannot be independent of IANA. See [risk-register.md](risk-register.md).
