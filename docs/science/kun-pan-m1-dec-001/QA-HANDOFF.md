# KUN-PAN-M1-DEC-001 independent QA handoff

## Check
1. **Documentation only, no existing file touched.** `git diff --stat origin/main HEAD` lists only new files under `docs/science/kun-pan-m1-dec-001/`. `git diff --diff-filter=MD --name-only origin/main HEAD` is empty.
2. **Status discipline.** Every PAN decision reads PENDING. Nothing says approved or canonical. No owner approval is claimed. KUN-PAN-M1 is described as prepared, not authorized.
3. **Coverage.** DECISION-PACKET §2 has all 13 required decisions (D01, D02, D07, D08, D09, D10, D12, D13, D14, D15, D16, D18, scoped D20), each with existing proposal, recommendation, rationale, alternatives and risks, exact M1 scope, consequences, required QA and owner option codes. §3 lists the deferred decisions.
4. **SCI-05 boundary.** PAN-D15-b is proposed as a separate scope approval; nothing says SCI-05 already covers Panchanga.
5. **Four claims kept apart.** PAN-D15-TOLERANCE-EVALUATION §1 separates convergence, phase-window agreement, Swiss-on-Swiss conformance and independent astronomy, and no text implies one from another.
6. **No numerical comparison.** No engine, `swetest` or Swiss output appears anywhere in the package. The tolerance evaluation uses published precision and rates only.
7. **Phase-event recheck honesty.** PHASE-EVENT-VERIFICATION states that the 100/100 match is a same-actor, page-reader recheck, that raw bytes could not be captured (proxy 403), and that all 50 records keep their pending status for an independent recheck. Rerun: `python3 -I docs/science/kun-pan-m1-dec-001/evidence/compare_phase_sources.py research/panchanga/reference-fixtures/geocentric-lunar-phase-events-2026.json docs/science/kun-pan-m1-dec-001/evidence/usno-moon-phases-2026-retrieved-20261103.txt docs/science/kun-pan-m1-dec-001/evidence/nasa-espenak-phases-2026-retrieved-20261103.txt` should end with `values 100 mismatches 0` and 8 inter-source differences.
8. **Independent recheck (QA's own task).** Follow PHASE-EVENT-VERIFICATION §6 from raw captured bytes, blind to the fixture.

## Evidence hashes (sha256)

| File | sha256 |
|---|---|
| Fixture `research/panchanga/reference-fixtures/geocentric-lunar-phase-events-2026.json` (unchanged) | `dfd964cf450cee57d76aff780fc2541814ca3ab79ac7e55028f4a88aa6459850` |
| `evidence/usno-moon-phases-2026-retrieved-20261103.txt` | `586e05647ff295ac457fed3e7c7b8982456fed1a962ff7a3c917473d57aaa9f2` |
| `evidence/nasa-espenak-phases-2026-retrieved-20261103.txt` | `083d76402cd19bd515c1b11c5adcafa3ba62eda951cb9bd12397dd037a36f55b` |
| `evidence/compare_phase_sources.py` | `355c8d60a17cb0f88bb41fbac60a85fba69cb684ebe9bfb9a474a5fb3f924e49` |
| `evidence/comparison-output.txt` | `3e494f2d6ee7627e7dfc40bfc59c2738645444d1ae3e10fa3823d2c8b73f0017` |
| `evidence/blocked-raw-capture.txt` | `615dc7a2bb6e54df0e6387fadf12c4d8b5cdc355ec1a3287d628160cc474abd0` |

## Requested verdict
PASS, CHANGES REQUESTED or BLOCKED on the exact head SHA. A PASS is not owner approval of any decision and not authorization to merge.
