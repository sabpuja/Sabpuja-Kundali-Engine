# KUN-PAN-M1-DEC-001 independent QA handoff

## Check
1. **Documentation only, no existing file touched.** `git diff --stat origin/main HEAD` lists only new files under `docs/science/kun-pan-m1-dec-001/`. `git diff --diff-filter=MD --name-only origin/main HEAD` is empty.
2. **Status discipline.** Every PAN decision reads PENDING. Nothing says approved or canonical. No owner approval is claimed. KUN-PAN-M1 is described as prepared, not authorized.
3. **Coverage.** DECISION-PACKET §2 has all 13 required decisions (D01, D02, D07, D08, D09, D10, D12, D13, D14, D15, D16, D18, scoped D20), each with existing proposal, recommendation, rationale, alternatives and risks, exact M1 scope, consequences, required QA and owner option codes. §3 lists the deferred decisions.
4. **SCI-05 boundary.** PAN-D15-b is proposed as a separate scope approval; nothing says SCI-05 already covers Panchanga.
5. **Four claims kept apart.** PAN-D15-TOLERANCE-EVALUATION §1 separates convergence, phase-window agreement, Swiss-on-Swiss conformance and independent astronomy, and no text implies one from another.
6. **No numerical comparison.** No engine, `swetest` or Swiss output appears anywhere in the package. The tolerance evaluation uses published precision and rates only.
7. **Phase-event recheck honesty.** PHASE-EVENT-VERIFICATION states that the 100/100 match is a same-actor, page-reader recheck, that raw bytes could not be captured (proxy 403), and that all 50 records keep their pending status for an independent recheck. Rerun: `python3 -I docs/science/kun-pan-m1-dec-001/evidence/compare_phase_sources.py research/panchanga/reference-fixtures/geocentric-lunar-phase-events-2026.json docs/science/kun-pan-m1-dec-001/evidence/usno-moon-phases-2026-retrieved-20261103.txt docs/science/kun-pan-m1-dec-001/evidence/nasa-espenak-phases-2026-retrieved-20261103.txt` should print `values 100 mismatches 0`, 8 inter-source differences and `RESULT PASS`, and exit 0. Any discrepancy exits 1, malformed input exits 2.
9. **Checker tests (revision 2).** `python3 -I -m unittest discover -s docs/science/kun-pan-m1-dec-001/evidence -p 'test_*.py' -v` runs 15 isolated tests: 1 positive, 12 negative (altered minute on either side, absent, duplicate and extra keys, count errors, marker discrepancies, a wrong recorded difference), 2 malformed-input, plus a check that the committed inputs are not modified. Expected `OK`.
8. **Independent recheck (QA's own task).** Follow PHASE-EVENT-VERIFICATION §6 from raw captured bytes, blind to the fixture. QA's reported result on `aea018b` is appended in §7.

## Evidence hashes (sha256)

| File | sha256 |
|---|---|
| Fixture `research/panchanga/reference-fixtures/geocentric-lunar-phase-events-2026.json` (unchanged) | `dfd964cf450cee57d76aff780fc2541814ca3ab79ac7e55028f4a88aa6459850` |
| `evidence/usno-moon-phases-2026-retrieved-20261103.txt` | `586e05647ff295ac457fed3e7c7b8982456fed1a962ff7a3c917473d57aaa9f2` |
| `evidence/nasa-espenak-phases-2026-retrieved-20261103.txt` | `083d76402cd19bd515c1b11c5adcafa3ba62eda951cb9bd12397dd037a36f55b` |
| `evidence/compare_phase_sources.py` | `d2c4e54a914248b6b98f83f5154510bf7c1fe14be35b636d1c649ca7e0a6c74b` |
| `evidence/comparison-output.txt` | `ed26ade3a540667404bf9781afb98a1d2c41a40e512fdeee4fa15f29c589f5be` |
| `evidence/test_compare_phase_sources.py` | `d668d1b1de9f38486f0157df4372b324fbe6813b7233a592ca6a81390847ad0d` |
| `evidence/checker-tests.log` | `46063902df91735d480177c9889ba658fe605c6df9744cab84a27c825cec4ea6` |
| `evidence/blocked-raw-capture.txt` | `615dc7a2bb6e54df0e6387fadf12c4d8b5cdc355ec1a3287d628160cc474abd0` |

## Requested verdict
PASS, CHANGES REQUESTED or BLOCKED on the exact head SHA. A PASS is not owner approval of any decision and not authorization to merge.
