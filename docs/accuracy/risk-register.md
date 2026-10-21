# Astronomical-accuracy risk register

**Document ID:** SP-KUN-ACC-RISK | **Work package:** CLAUDE-003 / KUN-01 | **Status:** PROPOSED

Scope: risks that block or weaken a claim of verified astronomical accuracy. Product-wide risks stay in `docs/DEVELOPMENT-ROADMAP.md` §9 on `main`; these rows should be folded in there when the foundation and `main` documentation are reconciled.

**Current status: the Kundali engine is NOT astronomically validated.** All existing tests are contract, rule and self-consistency tests.

| ID | Risk | Severity | Blocks | Evidence | Mitigation / owner |
|---|---|---|---|---|---|
| AR-01 | SCI-01/02/03 not yet approved; method-dependent fixtures cannot be generated | Blocker | All golden fixtures | `docs/DECISIONS.md` on `main`: all PENDING | Owner decides using [scientific-decisions.md](scientific-decisions.md); record in DECISIONS.md |
| AR-02 | JPL Horizons, NAIF (DE440s) and IMCCE (INPOP) unreachable from the Claude container | High | Post-2053 fixtures, second tropical path, I-data path | Connection refused from container, 2026-10-21 | Generate on owner/PM machine; commit raw responses with hashes (WP3) |
| AR-03 | DE421 (only bundled JPL kernel) ends 2053-10-09 | High | GC-06, GC-19, GC-20, part of TR-09 | SPK segment table read locally | DE440s from NAIF via AR-02 route |
| AR-04 | Indian Astronomical Ephemeris volumes not in hand | High | External ayanamsha check (T-AYA) | Not obtainable here | Owner/PM to obtain IAE pages (at least two years, e.g. 2019 and a current volume); record edition/page |
| AR-05 | Lahiri definition ambiguity: IAE prints 23°15'00" and 23°15'00.658"; mean-table epoch unclear | Medium | Interpretation of T-AYA residuals | Upstream Swiss documentation, IAE comparison appendix | Compare against IAE **true** tables; owner approves one definition explicitly (SCI-01a) |
| AR-06 | Pre-1956 India civil time (Bombay ≈ +04:51, Calcutta ≈ +05:53:20/+05:54) not modelled by IANA `Asia/Kolkata`; correct records are refused, IST-entered records accepted with up to ~39 min error | High | Correctness for pre-1956 India births | IANA `asia` file comments; TZ-10a/b | Disclose (SCI-03); place/time policy in DATA-01/KUN-02 |
| AR-07 | 1941–1945 India war-time offsets rest on a single source IANA calls "dubious" | Medium | GC-17 confidence | IANA `asia` file | Seek a primary source (gazette); disclose |
| AR-08 | Time-zone validation cannot be independent: engine and fixtures both use IANA | Medium | QA-005 independence | By construction | Pin tzdata version per fixture; treat TZ fixtures as rule-application tests; add primary historical sources where available |
| AR-09 | tzdata version drift between environments (container system 2026e, PyPI `tzdata` 2026.5) | Medium | Reproducibility | Measured here | Report records zoneinfo's actual version; mismatch with fixture → BLOCKED |
| AR-10 | Civil UTC used as UT1 (≤ 0.9 s; up to ~15" Lagna at the equator, ~1' at 60°) | Low | None (disclosed limitation) | Probes [7], [9] | SCI-01h; quantify with IERS data in reports |
| AR-11 | Future Delta T is extrapolated (Swiss 93.18 s for 2100); Moon moves 0.565"/s | Low | Comparisons near 2100 if done in UT | Probe [8], upstream Delta T chapter | Compare planets at the engine's TT; report Delta T difference (T-DT) |
| AR-12 | Ascendant computed through Placidus `houses_ex(b"P")`: date-dependent refusal near and beyond the polar circles | Medium | Predictable latitude coverage | Probes [4], [5]; upstream §6.4 | SCI-01e (`b"W"`, bit-identical where P works) and SCI-01g (fixed band) |
| AR-13 | Ascendant extremely time-sensitive at high latitude (220"/s at 66°); birth time to the minute gives large Lagna uncertainty | Medium | User-facing reliability, not test correctness | Probe [7] | Fixed latitude band; disclose time sensitivity |
| AR-14 | Common-mode error: Skyfield, ERFA and Swiss use similar IAU models and JPL data | Medium | Strength of "independent" claim | Reference register | Second paths: Horizons (IAU 1976/1980) and INPOP (non-JPL data) on a subset |
| AR-15 | Mean node has no observational truth; Swiss's (Moshier/ELP2000-85 adjusted) differs in principle from textbook polynomials | Low | Interpretation of T-NODE residuals | Upstream §2.2.1 | Reference the published polynomial; classify residual > T-NODE as FAIL for investigation, not as tolerance change |
| AR-16 | Tolerance creep after results are seen | High (process) | Credibility of validation | Process | Tolerances frozen at QA-approved revision; changes only via DECISIONS.md with non-result reason |
| AR-17 | Self-consistency tests mistaken for validation | High (process) | Credibility | Existing `docs/accuracy-plan.md` listed only rule/contract tests | Harness reports self-consistency separately; this package relabels existing tests |
| AR-18 | Engine code and data provenance split: C library from the `pyswisseph` 2.10.3.2 wheel (`swe.version` 2.10.03), `.se1` data from `aloistr/swisseph` at `c69c14a` | Low | Provenance completeness | `pip show`; manifest | Record wheel hash in the golden report; consider pinning the wheel SHA-256 in a later packaging WP |
| AR-19 | Canonical documents split between `main` (PRD, DECISIONS, roadmap, acceptance matrix) and the foundation branch (accuracy plan, architecture, this package) | Medium (process) | Single source of truth | `git ls-tree` of both branches | Reconcile when foundation PR #1 is reviewed; record approvals only in `main` DECISIONS.md |
| AR-20 | Foundation `docs/architecture.md` lists Lahiri, mean node and whole-sign houses under "Versioned conventions" as if settled; `data/ephemeris/README.md` says 12 skipped real-data tests, measured 13 | Low (doc drift) | Clarity | Read at `d8193c6` | Correct in the PR that implements the approved decisions; not changed here to keep this PR to the KUN-01 package |
| AR-21 | Reference data rights: IAE reproduction terms, INPOP terms | Medium | Committing reference values | Register | Cite numeric facts only; confirm terms before committing tables |
| AR-22 | Birth-time precision dominates all astronomy errors (1 min ≈ 16' of Lagna at the equator, over 1° at 60°) | Product | None for QA; affects user trust | Probe [7] | UX and report wording (UX-01), outside KUN-01 |
