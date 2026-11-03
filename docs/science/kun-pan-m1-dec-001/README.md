# KUN-PAN-M1-DEC-001: Panchanga M1 birth-instant method decisions

**DOCUMENTATION ONLY. Every decision is PENDING. Production: NO-GO.** No engine, Swiss Ephemeris or Panchanga numerical comparison was run for this package.

| File | Task item | Content |
|---|---|---|
| [DECISION-PACKET.md](DECISION-PACKET.md) | B1, B2, B5 | Preserved M1 scope; the 13 decisions needed now (PAN-D01, D02, D07, D08, D09, D10, D12, D13, D14, D15, D16, D18, scoped D20) with recommendation, rationale, alternatives, scope, consequences, QA and owner option codes; deferred decisions; owner approval fields |
| [PHASE-EVENT-VERIFICATION.md](PHASE-EVENT-VERIFICATION.md) | B3 | Same-actor recheck of the 100 USNO/NASA values against the live sources (100/100 match), its limits, and a blind independent-verification plan |
| [PAN-D15-TOLERANCE-EVALUATION.md](PAN-D15-TOLERANCE-EVALUATION.md) | B4 | The four acceptance claims kept apart; evaluation of the ±60 s phase window; a separate Panchanga Swiss-conformance tolerance proposal (SCI-05 does not cover it); commit-before-run rule |
| [ENGINEERING-SPEC-KUN-PAN-M1.md](ENGINEERING-SPEC-KUN-PAN-M1.md) | B6 | Bounded, unexecuted KUN-PAN-M1 specification: base SHA strategy, change boundary, oracles, search, errors, privacy, fixtures, ENG and RPT gates, blockers, sequence |
| [QA-HANDOFF.md](QA-HANDOFF.md) | — | What ChatGPT should check, and the evidence hashes |
| [evidence/](evidence/) | B3 | Retrieval records, comparison script and output |

## Refs

| Item | Value |
|---|---|
| Base: `main` | `de721d665ed80ed58291f59962677065a73f0b26` (tree `80597a0db7a49f1ebbd6f6faa713b7ea1627af45`), the PR #64 merge |
| Adoption receipt checked | [PR #64 comment 6598563378](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/64#issuecomment-6598563378): SCI-04, SCI-05, SCI-06 canonical at their recorded scopes; Panchanga decisions and PAN-D15 still PENDING |
| Method source | SCI-PAN-01 rev 0.5; `docs/science/kun-sci-pol-002/PANCHANGA-M1-MILESTONE.md` |

Nothing here changes calculation code, schema 0.3.0, metadata `/3`, Swiss methods or approved tolerances, D1/D9 reference data, the PDF renderer, fixtures, the private preview or infrastructure. No existing file is modified. PR #62 and #63 are untouched; PR #1 stays on HOLD. The B-6 wording review (KUN-B6D-REVIEW-001) is a separate PR.
