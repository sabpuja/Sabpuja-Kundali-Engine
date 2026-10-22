# KUN-02 Phase 2: approval actions, implementation sequence, compatibility and release risks

**Status:** PLAN ONLY. Nothing here is authorized. No production package (P1–P9) is started in this phase.
**Decisions:** [KUN-02-P2-decision-package.md](KUN-02-P2-decision-package.md) · **Evidence:** [KUN-02-P2-evidence-map.md](KUN-02-P2-evidence-map.md)

## 1. Pending approval actions

All of the following are open. They are listed in the order that unblocks implementation.

| # | Action | Who | Unblocks |
|---|---|---|---|
| A-1 | ChatGPT scientific QA of this decision PR (PASS / CHANGES REQUESTED) | ChatGPT | A-2 |
| A-2 | Owner decision on each of SCI-01a, 01d, 01e, 01f, 01g, 01h, SCI-02, SCI-03: approve, modify or reject, one entry at a time | Sabpuja | A-3 |
| A-3 | Record each owner decision in two steps: a **pre-merge approval record** in `docs/DECISIONS.md` (choice, date, approval link, effective scope, exact reviewed head SHA; row text stays PENDING), then, after the owner-authorized merge, a **post-merge adoption receipt** (merge SHA and date) that makes the row OWNER APPROVED | Sabpuja authorizes; Claude edits on request | P-packages |
| A-4 | Owner choices inside decisions: SCI-01e and SCI-01g together (W plus ±66.0°, or another band); SCI-02 Nakshatra/Pada for all bodies or Moon only; SCI-03 RG-HIST scope: (A) Kolkata before 1956 (mandatory floor), (B) plus every other zone before 1970 (Kolkata 1956–1969 still accepted), (B-full) every zone before 1970 including Kolkata 1956–1969 (recommended for public release), or (C) plus South Asian zones before 1970; whether non-location zones (`Etc/*`, `UTC`) are refused for births | Sabpuja | P2, P3, P6, P8, P5 |
| A-5 | Merge order of the existing drafts (#1 foundation, then #18, #19 and the KUN-01 documentation stack #11, #14, #17), so that production packages have a reviewed base | Sabpuja, with ChatGPT QA | P-packages |
| A-6 | Authorize DATA-01 historical-clock research as its own package | Sabpuja | verified exceptions to RG-HIST |
| A-7 | Each P-package: separate authorization to start, ChatGPT QA of its draft PR, and separate merge authorization | Sabpuja / ChatGPT | each package |
| A-8 | **Reconcile the release-gate source of truth:** decide in a separate, small doc-only owner decision PR how `docs/PRD.md` (product truth, KUN-F16, the "Astronomy accuracy" release gate) and `docs/ACCEPTANCE-MATRIX.md` (QA-009, QA-010, QA-012, G-ENGINE) relate to the Swiss-first change ([issue #15](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/15), [PR #17](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/17)). Until approved, those P0 requirements stand unchanged (§4) | Sabpuja, with ChatGPT QA | public accurate-chart claims |

## 2. Implementation sequence and dependencies

Each package is one scoped draft PR targeting the reviewed engine base, with its own tests, exact Git SHA, before/after comparison evidence (KUN-02 runner and PR #18 conformance reports), ChatGPT QA and a separate merge authorization.

```
            ┌────────────── P9 Swiss-state isolation tests (no decision needed) ──────────────┐
            │                                                                                  │
SCI-03 ──► P1 tzdata pinning ──► P4 local-date window ──► P5 strict format + refusal codes ──► P8 RG-HIST gate
SCI-01g ─► P2 latitude band ──► P3 Lagna via b"W" (SCI-01e; P2 first or in the same PR)
SCI-01f + SCI-02 ──────────────► P6 D9 houses (+ optional all-body Nakshatra)
SCI-01a, d, h + P1 + P3 ───────► P7 calculation metadata and time-scale provenance
```

| Order | Package | Decision required | Depends on | Numeric change | Input change | Size |
|---|---|---|---|---|---|---|
| 1 | **P9** Permanent Swiss-state isolation regression tests | none beyond QA | reviewed engine base | none | none | XS |
| 2 | **P1** Deterministic tzdata loading and provenance | SCI-03 (P1 is an engineering reproducibility fix that depends on it) | — | none for Asia/Kolkata; possibly pre-1956 values in 8 Asian zones on hosts with `backzone` | none | S |
| 3 | **P2** Fixed ±66.0° latitude validation | SCI-01g | — | none | refuses \|lat\| > 66.0 | S |
| 4 | **P3** Lagna via `b"W"` | SCI-01e | **P2 merged first, or in the same PR** | none (bit-identical) | none once P2 is in | XS |
| 5 | **P4** Local civil birth-date validation | SCI-03 | P1 | none | edge dates only | S |
| 6 | **P5** Strict birth-time format, gap/fold handling, structured refusal codes | SCI-03 (and API contract) | P4 | none | refuses non-RFC 3339 forms | M |
| 7 | **P8** Historical-clock fail-closed gate | SCI-03 RG-HIST scope (A-4) | P5 (its code set), P1 | none | refuses gated births | M |
| 8 | **P6** D9 whole-sign houses and approved chart fields | SCI-01f, SCI-02 | reviewed base | additive fields | none | M |
| 9 | **P7** Scientific calculation metadata and time-scale provenance | SCI-01a, d, h; SCI-03 | P1 (tzdata version), P3 (ascendant vehicle) | additive fields | none | S |

P2 and P3 together are the only hard ordering constraint between calculation packages: P3 alone would start accepting births between the polar circle and ±89°. P6 and P7 change the output schema, so they should each bump the schema version.

**Refusal validation order** (proposed in KUN-02 `supported-envelope.md` §3; fixed so one input always gets the same code): `REQUEST_INVALID` → `TIME_FORMAT_INVALID` → `TIME_OFFSET_REQUIRED` → `TIME_LEAP_SECOND_UNSUPPORTED` → `DATE_INVALID` → `TIMEZONE_INVALID` → (`TIMEZONE_NOT_LOCATION_BASED`, owner option) → `DATE_OUTSIDE_SUPPORTED_RANGE` → `TIME_NONEXISTENT_LOCAL` → `TIME_OFFSET_MISMATCH` → `HISTORICAL_CLOCK_UNVERIFIED` → `COORDINATE_INVALID` → `LATITUDE_OUTSIDE_SUPPORTED_BAND` → (`LOCATION_TIMEZONE_INCONSISTENT`, after DATA-01) → `EPHEMERIS_*` → `ASCENDANT_UNCOMPUTABLE` (defensive).

## 3. Compatibility and breaking-change analysis

Today's engine (foundation @ `d8193c6`) is the baseline. "Breaking" means a request that succeeded before now fails, a failing request now succeeds, or an existing output value changes.

| Change | Package | Accepted charts: values | Requests newly refused | Requests newly accepted | Output schema | Breaking? |
|---|---|---|---|---|---|---|
| tzdata pinned, deterministic loader | P1 | unchanged for Asia/Kolkata and all 63 KUN-02 cases; may change pre-1956 values for 8 Asian zones on hosts whose system tzdata includes `backzone` | none | none | adds tzdata version (P7) | Possibly, for those historical zones on such hosts (intended: removes host dependence) |
| Latitude band | P2 | unchanged | 66.0° < \|lat\| < 89° (some accepted today on some dates) | none | new error code | Yes, for those latitudes |
| Lagna via `b"W"` | P3 | bit-identical | none | none (with P2) | method text | No (with P2) |
| Local-date window | P4 | unchanged | local 1899-12-31 in western zones (UTC 1900); local 2101-01-01 in eastern zones (UTC 2100) | local 1900-01-01 in eastern zones (UTC 1899); local 2100-12-31 in western zones (UTC 2101) | new error code | Yes, at the two edges only |
| Strict format and codes | P5 | unchanged | space separator, ISO basic format (accepted today only on Python ≥ 3.11) | none | structured codes replace free-text `ValueError` messages | Yes for clients that parse message text or send non-RFC 3339 strings |
| RG-HIST gate | P8 | unchanged outside the gate | Asia/Kolkata before 1956-01-01 at minimum (more under option B, B-full or C) | none | new error code | Yes, by design |
| D9 houses (+ Nakshatra for all bodies) | P6 | unchanged | none | none | additive fields, version bump | No for tolerant clients; strict-schema clients must update |
| Metadata | P7 | unchanged | none | none | additive fields, version bump | As above |
| Swiss-state tests | P9 | unchanged | none | none | none | No |

Other compatibility notes:
- The PR #18 conformance cases that assert the current UTC-year and polar refusals must be updated in P2/P3/P4, as a reviewed test change, not silently.
- No pinned Swiss file, Swiss version, ayanamsa, node or frame changes in any package.
- No existing chart's planetary longitude changes in any package.

## 4. Release gates and risks requiring separate verification

These are outside what KUN-01 and KUN-02 evidence shows, and none is closed by this PR. They are of three kinds:
- **Mandatory release gates** block any public release.
- **Mandatory periodic reviews** must be repeated on a schedule or a trigger.
- **Optional assurance** supports a separate, stronger claim and is not a release gate.

| # | Risk | Gate type | Why it is open | Verification needed |
|---|---|---|---|---|
| R-1a | Chart correctness within the Swiss-first MVP | **Mandatory release gate** | Covered so far only by draft-PR evidence. That evidence is pinned Swiss CLI conformance (PR #18, 882/882) and independent mathematical D1/D9, segment and house checks (PR #18 rule oracle; PR #19 A8–A10). Known boundary and refusal cases are part of it. None of these PRs is merged | Keep both suites passing on every package; boundary and refusal fixtures for P2–P5 and P8; product claims limited to what the evidence shows (Swiss-based calculation with stated conventions, not independently verified astronomy) |
| R-1b | Independent astronomy (JPL/INPOP) | **Optional assurance**, per the owner-approved Swiss-first change ([issue #15](https://github.com/sabpuja/Sabpuja-Kundali-Engine/issues/15), [PR #17](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/17)) | No independent planetary reference has been run; no golden-chart tolerance is frozen (KUN-01 PG-1 to PG-5 open) | Only for a separate independent-accuracy claim or a discrepancy escalation |
| R-1c | **Source-of-truth conflict** on R-1b | **Mandatory, pending owner reconciliation** | `docs/PRD.md` (product truth, KUN-F16, the "Astronomy accuracy" gate) and `docs/ACCEPTANCE-MATRIX.md` (P0 QA-009, QA-010, QA-012; G-ENGINE) still require independently sourced golden charts before accurate public claims. Issue #15 made JPL/INPOP assurance optional. Neither document has been aligned | Owner decision A-8 in a separate doc-only PR. **Until then those P0 requirements stand and the public-release gate is not relaxed.** This package neither waives nor satisfies them |
| R-2 | Historical birth clocks | **Mandatory release gate** | IANA is not historical-clock evidence before 1970. RG-HIST (A) is a temporary floor. Under (A), (B) and (C), Asia/Kolkata 1956–1969 is accepted without DATA-01 evidence; under (A) and (C) other pre-1970 zones are too. Only (B-full) removes the pre-1970 residual | Owner decision on RG-HIST scope (A-4; B-full recommended); DATA-01 package before any exception |
| R-3 | UT1 − UTC after 2027 and especially from 2035 | Mandatory metadata (P7) and **periodic review** | The IERS list expires 2027-06-28. CGPM 2022 Res. 4 raises the limit in or before 2035. ΔT is extrapolated after 2028 | Era-labelled metadata before release; re-review SCI-01h before 2035 and on every Swiss or tzdata update |
| R-4 | Swiss 2.10.03 version-specific behaviour | **Mandatory release gate** (P9) and periodic review | −1.908″ sidereal-time step at 2050; Swiss state leaks between `set_sid_mode` calls | P9 tests; re-run the KUN-02 runner on any Swiss upgrade |
| R-5 | tzdata drift between hosts | **Mandatory release gate** (P1) | Same IANA version, different builds, different pre-1956 offsets | P1 two-host reproducibility test; pinned TZif manifest |
| R-6 | Place-to-zone consistency | **Mandatory release gate** | The engine accepts any IANA zone with any coordinates (for example Asia/Kolkata with New York coordinates) and accepts `Etc/*` keys | DATA-01 gazetteer and `LOCATION_TIMEZONE_INCONSISTENT`; owner choice on non-location zones |
| R-7 | Birth-time sensitivity | **Mandatory release gate** (product claims) | A one-minute error changes the Lagna Navamsa in about 8% of sampled charts; above 60° the Lagna moves more than 1° per minute | Product disclosure copy and editorial review |
| R-8 | Unknown birth time | **Mandatory release gate** | Not handled by these decisions (UX-01 pending) | UX-01 decision and QA-002 |
| R-9 | Licensing | **Mandatory release gate** | Swiss Ephemeris AGPL and data-rights perimeter (LEG-01 pending) | QA-026 legal review |
| R-10 | Concurrency of Swiss global state in a multi-worker service | **Mandatory release gate** | The engine serializes Swiss calls under one lock; the service architecture is not yet built | QA-008 concurrency tests in the service package |

Security, privacy (QA-018, QA-024, QA-025), accessibility, Hindi review and the owner's release sign-off remain mandatory gates under `docs/ACCEPTANCE-MATRIX.md` and are unaffected by this package.

## 5. What this PR does not change

- Production calculation code: none. `main` contains no engine code, and no engine branch is modified by this PR.
- Existing draft PRs #1, #11, #14, #17, #18 and #19: not amended, rebased or merged.
- Swiss Ephemeris files and versions: unchanged.
- SCI-01b and SCI-01c: unchanged text and status.
- No GitHub Actions, no deployment, no customer birth data, no accuracy certification claim.
