# KUN-PAN-M1-DEC-001 B4: PAN-D15 acceptance tolerances for M1

**PROPOSAL. Owner decision PENDING. No engine or Swiss value was computed against any reference event to write this.** The evaluation below uses only the published precision, the publishers' own statements and textbook rates of motion. PAN-D15 requires the final tolerances to be owner-approved and committed before the first evaluation run.

## 1. Four different acceptance claims

These are easy to conflate. Each one has its own tolerance, its own evidence and its own meaning. A pass on one never implies a pass on another.

| # | Claim | Compared | Tolerance (proposed) | What a pass means | What it does not mean |
|---|---|---|---|---|---|
| C1 | **Numerical search convergence** | The solver's final bracket around a crossing **of its own model** | Bracket width ≤ 0.5 s, ≤ 64 iterations, ≤ 2.5 days each way (PAN-D09/D10) | The solver found the model's crossing to 0.5 s | Anything about whether the model is right |
| C2 | **Agreement with published whole-minute phase events** | Engine crossing instant of E = 0°, 90°, 180°, 270° vs USNO and NASA minutes | §2: the window [min published − 60 s, max published + 60 s] | Engine lies inside the span that both publishers' printed minutes allow, plus margin | Seconds-level accuracy; correctness of any Tithi or Karana boundary other than these four angles |
| C3 | **Swiss-on-Swiss conformance** | Engine Sun and Moon longitudes, and derived E and S, vs `swetest` at the same instants; engine transitions vs an independent oracle working on `swetest` output | §3 | The Panchanga code reads Swiss the same way the reference CLI does, and its rule and search code are right | Independent astronomy: both sides use the same Swiss model |
| C4 | **Independent astronomical validation** | Engine vs a separate ephemeris (JPL/INPOP) | None proposed | — | **Deferred.** No M1 claim |

## 2. C2: the phase-event window

### 2.1 What a published minute can mean

Neither USNO nor NASA states its rounding rule (PHASE-EVENT-VERIFICATION §2). For a printed minute M and a true instant t:

| Publisher rule | Interval for t |
|---|---|
| Round to nearest | [M − 30 s, M + 30 s) |
| Truncate | [M, M + 60 s) |
| Either (unknown) | [M − 30 s, M + 60 s) |

With two publishers whose values are M_min ≤ M_max (identical, or 1 min apart in 2026), the span consistent with either rule at either publisher is at most **[M_min − 30 s, M_max + 60 s)**.

### 2.2 Model differences between the publishers and the engine

| Source | Size for 2026 events | Basis |
|---|---|---|
| UT1 vs UTC (engine passes civil UTC as UT1, SCI-01h) | < 0.9 s by definition of UTC | IERS |
| ΔT model (Swiss automatic ΔT vs publisher ΔT) | Expected about 1 s or less for 2026; NASA prints ΔT only to the minute (`00h01m`) | Expectation, not a measured bound |
| Lunar and solar theory (Swiss DE-based files vs publisher ephemerides) | Sub-arcsecond in E, so under about 2 s (E moves about 0.45″ to 0.60″ per second) | Expectation |
| Observed USNO/NASA systematic offset | Plausibly about 10 s (4 to 17 s), NASA later (PHASE-EVENT-VERIFICATION §5) | Inference from 8 of 50 differing, all one way |

So the model terms are expected to be seconds to perhaps 10 to 20 s, well inside one minute but not negligible against a 30 s rounding half-width.

### 2.3 Evaluation of the proposed window

Proposed (SCI-PAN-01 PAN-D15, provisional A): **pass if M_min − 60 s ≤ t_engine ≤ M_max + 60 s**.

| Case | Early margin beyond the §2.1 span | Late margin beyond the §2.1 span |
|---|---|---|
| Both publishers round | 30 s | 30 s |
| Later publisher truncates | 30 s | **0 s** (window edge equals the truncation bound) |
| Total width | 2 min (identical values) or 3 min (1 min apart) | |

Assessment:
- **Sound for its purpose.** The window contains every true instant consistent with the printed minutes under any common rounding rule. A defect that matters for Panchanga (a wrong frame, a tropical sum, a sign error, a time-zone slip, a wrong bracket) moves crossings by minutes to hours, far outside it. A wrong ayanamsa cannot show up here at all, because E is ayanamsa-free.
- **Not a precision claim.** It cannot detect an engine error smaller than about 30 to 60 s. PAN-QA-04 must therefore be reported as "inside the declared window", never "accurate to 0.5 s" (PANCHANGA-M1-MILESTONE §4).
- **One weak edge.** If the later publisher truncates, a correct engine sitting a few seconds late could fall just outside. With the expected model terms (§2.2) this is unlikely but not impossible.

### 2.4 Options for the owner

| Option | Window | Pros | Cons |
|---|---|---|---|
| **R (recommended): adopt as proposed** | [M_min − 60 s, M_max + 60 s], closed | Already in the fixture (`proposed_tolerance.accept_window_utc` on every case), so the committed fixture needs no change; simple; symmetric; covers every rounding rule | Zero late margin in the truncation case |
| A1: asymmetric with model margin | [M_min − 40 s, M_max + 70 s] | Covers every rounding rule with 10 s model margin on both sides | New numbers not in the fixture; needs a fixture-side tolerance file; harder to explain |
| A2: tighter, rounding assumed | [M_min − 30 s, M_max + 30 s] | Detects errors of about 30 s | Assumes a rounding rule neither publisher states. **Not scientifically defensible** on current evidence |
| A3: wider | ±120 s | Never fails a correct engine | Loses diagnostic value for no evidenced reason |

**Recommendation R**, with one reporting rule that does not change pass/fail: the M1 run report must print, for every event, the signed residual t_engine − M for each publisher, and list any event within 10 s of a window edge as `NEAR_WINDOW_EDGE` for QA to look at. If that list is non-empty, QA decides whether it reflects the truncation case or a defect. The window is never widened after a run.

### 2.5 Applicability

- Applies to the 50 PAN-REF-PHASE-2026 events only, and only after each one passes the independent transcription recheck (PHASE-EVENT-VERIFICATION §6). Unverified cases are excluded, not passed.
- For each event, the Tithi (New and Full Moon) and the Karana index (all 50) must also be correct at t_engine − 1 s and t_engine + 1 s. That checks the side assignment of the half-open rule at the real crossing.
- Does not apply to any other Tithi or Karana angle, to Yoga, Nakshatra, sunrise or IMD rows.

## 3. C3: Panchanga Swiss conformance tolerance (new scope, separate from SCI-05)

SCI-05 extended the frozen KUN-01-SWISS-01 tolerances (`engine_vs_swetest` 1e-8°, `binding_vs_swetest` 1e-9°, `spec.json` sha256 `642a770d…12a8`) to the KUN-SCI-GOLD-001 50-chart matrix **only**. It does not cover Panchanga. Proposal **PAN-D15-b**:

| Quantity | Tolerance | Basis |
|---|---|---|
| λ☉, λ☾ (engine vs `swetest`), at Panchanga instants | 1e-8° (same value) | Same code path as the chart (SCI-01d). New scope, no new value |
| Same, Python binding vs `swetest` | 1e-9° (same value) | As above |
| E = (λ☾ − λ☉) mod 360 and S = (λ☉ + λ☾) mod 360 | **2e-8°** | Two terms, each within 1e-8° (triangle inequality). Derived bound, not a new physical tolerance |
| Tithi, Karana, Yoga, Nakshatra, Pada indices | Identical | Half-open rule (PAN-D08). If the `swetest`-derived value lies within the tolerance of an edge, the row is `BOUNDARY-INDETERMINATE`, as in the gold runner |
| Transition instant, engine vs an independently coded bisection on `swetest` output | **≤ 1.0 s** | Two independent solves, each converged to ≤ 0.5 s (C1). The angle tolerance contributes at most 2e-8° ÷ 1.2e-4 °/s ≈ 2e-4 s, which is negligible |
| Instants used | (a) the 50 PAN-REF-PHASE-2026 instants (published minutes, used only as instants); (b) the 50 KUN-SCI-GOLD-001 birth instants; (c) each transition found from those instants | Reuses existing, hashed instant sets. No new birth data |

Scope wording for the owner: "PAN-D15-b applies the frozen KUN-01-SWISS-01 values, unchanged, to Sun and Moon longitudes at the KUN-PAN-M1 instant sets, and adds the derived 2e-8° (E, S) and 1.0 s (transition) bounds. It is Swiss-on-Swiss conformance only."

## 4. Deferred tolerances (not decided now)

- IMD rows (Tithi, Nakshatra, Yoga, Karana): wait for IMD Stage C/D and the SCI-PAN-01 §3.1 ayanamsa budget.
- Sunrise and sunset (SUN-A ±120 s and others): wait for PAN-D03.
- Any Yoga or Nakshatra end-time comparison with an external publisher: no reference exists.
- Independent astronomical validation (C4).

## 5. Commit-before-run rule

1. The owner approves PAN-D15-a (C2 window) and PAN-D15-b (C3) under the two-step rule.
2. The approved values go into a test-side tolerance file on the KUN-PAN-M1 branch, hashed in its first commit, together with the list of independently rechecked case ids.
3. Only a later commit may contain the first evaluation run, and its report must cite the tolerance file hash.
4. QA checks the order of those commits. A tolerance changed after a run is a new decision, and the earlier run is reported as superseded, never re-scored.
