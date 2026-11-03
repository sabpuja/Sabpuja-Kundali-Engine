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

## Revision 2: KUN-PAN-M1-QA-FIX-001 (checker hardening, after QA review 5749516454)

| Item | Value |
|---|---|
| Base | `main` `de721d665ed80ed58291f59962677065a73f0b26` (tree `80597a0db7a49f1ebbd6f6faa713b7ea1627af45`) |
| r1 reviewed head | `aea018ba33e3e8d84f09e5b161212286b77ab9af` (tree `793312e2c85a75ccea733846496f6200f4b765b8`) |
| Checker-fix commit | `a4ff29156302d93d8755d5bedefb34255612de49` (tree `543b544cedc992e11b095f241a3146cc40dbdf85`) |
| This manifest commit | The PR head that contains this section. A commit cannot record its own SHA, so the exact final head and tree are given in the PR comment that requests re-review |

**Paths changed since r1.** `evidence/compare_phase_sources.py` (fail-closed exit status), `evidence/test_compare_phase_sources.py` (new), `evidence/checker-tests.log` (new), `evidence/comparison-output.txt` (rerun), `evidence/SHA256SUMS` (new manifest), `QA-HANDOFF.md` (this file), and `PHASE-EVENT-VERIFICATION.md` (a paragraph on the checker's exit status in §3, and §7 appending QA's reported raw-byte recheck as reviewer evidence, as the review suggested; no status, recommendation or threshold changed). Nothing outside `docs/science/kun-pan-m1-dec-001/`.

**Exit contract.** 0 all checks pass; 1 any discrepancy (minute mismatch, absent event either side, duplicate event either side, count ≠ 50, NASA marker mismatch, marker in the USNO file, wrong recorded inter-source difference); 2 unreadable or malformed input. One `ERROR` line per failing record, then `RESULT PASS` or `RESULT FAIL (n errors)`.

**Controls** (`evidence/test_compare_phase_sources.py`, on temp copies; log `evidence/checker-tests.log`, Python 3.13.18): `Ran 15 tests … OK`.

| Kind | Tests | Expected exit |
|---|---|---|
| Positive | committed inputs → `values 100 mismatches 0`, 8 differences, `RESULT PASS` | 0 |
| Wrong published minute | fixture Jan 3 Full Moon USNO 10:03→10:04; USNO file 10:03→10:05 | 1 |
| Missing event | NASA line removed; fixture case removed | 1 |
| Duplicate event | USNO line repeated; fixture case repeated | 1 |
| Event count | extra USNO event; 49 NASA / 51 fixture counts (inside the above) | 1 |
| Marker mismatch | NASA `A`→`T`; fixture marker removed; marker added to USNO line | 1 |
| Recorded difference | fixture `inter_source_difference_minutes` 0→1 | 1 |
| Malformed input | bad phase token; missing file | 2 |
| Inputs untouched | committed fixture and snapshots byte-identical after the run | — |

**Canonical rerun** on the unchanged fixture `dfd964cf450cee57d76aff780fc2541814ca3ab79ac7e55028f4a88aa6459850`: exit 0, `RESULT PASS` (`evidence/comparison-output.txt`).

**Evidence manifest:** `evidence/SHA256SUMS`; check with `cd docs/science/kun-pan-m1-dec-001/evidence && sha256sum -c SHA256SUMS`.

**Remaining blockers (unchanged):** owner selections and adoption for the PAN decisions (all PENDING); owner/QA disposition of whether the §7 recheck makes the 50 records `INDEPENDENTLY_RECHECKED`; OD-09 or authorization to stack on PR #62 `6722b5c`; a numbered KUN-PAN-M1 task.

## Revision 3: malformed-input classification (after QA review 5749654235)

| Item | Value |
|---|---|
| Re-reviewed head | `b623f14d53668874a8b044ada92005cf2a44c4e5` (tree `a60baa7cfc99d82edc9d1ad2c888a41bbcf177fb`) |
| This revision | The PR head containing this section; exact SHA and tree in the PR comment requesting re-review |

**Fix.** Publisher `MM-DD` and `HH:MM` must form a real 2026 date and a time in 00:00 to 23:59 (`datetime.strptime`), and each fixture `value_utc_minute` must be `2026-MM-DDTHH:MMZ` with the same validity. Anything else is `INPUT ERROR`, exit 2. Valid-but-wrong values stay exit 1.

**Added controls (5; suite now 20, `Ran 20 tests … OK`):** `01-03 Full Moon 25:99` → 2; `AA-BB Full Moon 10:03` → 2; `02-30` date → 2; fixture `2026-13-03T10:03Z` → 2; valid but wrong `23:59` → still 1.

**Paths changed since `b623f14`:** `evidence/compare_phase_sources.py`, `evidence/test_compare_phase_sources.py`, `evidence/checker-tests.log`, `evidence/SHA256SUMS`, `QA-HANDOFF.md`, `PHASE-EVENT-VERIFICATION.md` (exit-contract wording and the reviewer's 50-record disposition, attributed). `evidence/comparison-output.txt` was rerun and is byte-identical. Fixture, thresholds and recommendations unchanged; all PAN decisions PENDING.
