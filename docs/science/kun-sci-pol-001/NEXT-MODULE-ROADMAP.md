# Next premium calculation modules: inventory and proposed sequence

**PROPOSAL. Nothing here authorizes implementation.** Each module needs, in order:
1. an owner method decision;
2. a numbered, bounded task;
3. an ENG gate (scientific accuracy) and, for any customer wording, a separate RPT gate (premium-report quality), as PRD §13 proposes.

An ENG PASS never validates an interpretation.

## 1. What already exists on `main` (`1d4bcb6`)

| Module (PRD) | Research on `main` | Evidence class | Status |
|---|---|---|---|
| **Panchanga** (KUN-A01) | `docs/science/SCI-PAN-01-…PROPOSAL.md` rev 0.5 (PAN-D01 to PAN-D20); `WP-B2-…HANDOFF-DRAFT.md`; `research/panchanga/` (source register, fixtures, Stage C package) | **Independently sourced by Claude:** 50 USNO lunar-phase events for 2026, cross-checked against NASA/Espenak (42 identical, 8 differ by one minute; whole-minute precision). Of these, 25 are Tithi plus Karana boundaries and 25 are Karana-only. Also 14 USNO sunrise/sunset cases (2 of them no-sunrise) and 16 boundary specifications. **Reviewer-collected:** 46 IMD Rashtriya Panchang candidates, Stage A/B by the ChatGPT reviewer. **Stage C (independent second person): 0 of 46. Stage D (engineering acceptance): 0 of 46.** **Derived:** 8 cases, labelled as such | Every PAN decision PENDING. PAN-D03 (sunrise) has no recommendation. WP-B2 BLOCKED. No verified Nakshatra- or Yoga-end reference |
| **Vimshottari Dasha** (KUN-A02) | None on `main`. Draft PR #48 holds ChatGPT-written arithmetic that is **non-canonical and must not be used** (PRD independence correction, 2026-10-27) | None | Not started. Needs a year-length and time-arithmetic decision plus independently sourced timelines |
| **D10 and further Vargas** (KUN-A03) | None | None | Not started. Needs one owner-approved rule per chart and an independent rule oracle |
| **Expanded interpretations** (KUN-A08 / KUN-F07) | None. The Phase 1 PDF says "not an interpretation" | None | Not started. Needs a rule-ID library, authored sources, human editorial review and the RPT gate |

**Dependency on this packet.** B-6, if approved, applies to every module that classifies a moving quantity: the Panchanga limbs, Dasha start (via the Moon Nakshatra) and Varga signs. B-1 and B-3 matter to every module that reuses the D1 Lagna and longitudes.

## 2. Comparison

| | Customer value | Reference availability | Implementation risk |
|---|---|---|---|
| **Panchanga, birth-instant limbs** (Tithi, Nakshatra, Yoga, Karana index) | High (core Indian premium report content) | **Best available.** Independent USNO/NASA boundary times exist for Tithi and Karana. The Nakshatra equals the chart Moon Nakshatra, which is already verified. Yoga and Karana names still need a source | **Low.** These are functions of the already-verified Sun and Moon longitudes, with no new convention and no location |
| Panchanga, sunrise-dependent parts (Vara, daily Panchanga) | High | Weak. IMD is at Stage C 0 of 46, and the SUN-D convention has not been verified from the primary source by Claude | **High.** A sunrise convention decision is still open, Swiss rise/set has caveats, and there are no-sunrise cases above about 65.7° |
| Vimshottari Dasha | Very high | **None yet.** Independent timelines must be sourced and verified | Medium. The arithmetic is simple but convention-sensitive (year length, the Moon Nakshatra balance), and boundary-sensitive through B-6 |
| D10 | Medium | None. School variants exist | Low arithmetic risk, but needs a method decision |
| Interpretations | High, but only once trustworthy | Needs authored sources | High editorial and RPT risk. AI may not invent content |

## 3. Recommended sequence

1. **First: Panchanga birth-instant limbs (KUN-A01, sunrise-independent subset).**
   - Ask the owner to decide only the PAN items this subset needs: PAN-D01 frame, PAN-D02 birth-time output, PAN-D07 Karana index without names, PAN-D09 convergence and display, PAN-D12 metadata, and PAN-D15 tolerances after the IMD method facts.
   - ENG gate on the USNO/NASA boundary events plus the derived cases. Refuse or omit names until PAN-D16.
   - The sunrise, Vara and daily Panchanga follow after PAN-D03 and Stage C/D.
2. **In parallel, documentation only: a Vimshottari method decision package** (year length, balance at birth, half-open boundaries, B-6 interaction), plus a plan to source independent reference timelines. Implementation comes second, once references exist.
3. **Third: D10**, after an owner rule decision and an independent rule oracle (the pattern used for D9 in KUN-SCI-GOLD-001).
4. **Last: expanded interpretations**, only over ENG-passed modules, with human-authored, rule-ID-traceable text and the RPT gate.

Throughout, keep the ENG (scientific-accuracy) and RPT (premium-report-quality) gates and their evidence separate. A module is sellable only when both pass on the exact delivered variant (PRD §13 proposal).
