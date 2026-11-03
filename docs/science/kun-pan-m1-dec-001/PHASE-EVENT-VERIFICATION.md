# KUN-PAN-M1-DEC-001 B3: Phase-event source verification

**DOCUMENTATION ONLY. No engine, Swiss Ephemeris or Panchanga calculation was run.** This file rechecks transcribed publisher values against the live publisher pages. It does not compare any computed result with them.

## 1. Result in one paragraph

On 2026-11-03 Claude re-read the live USNO API response and the live NASA/Espenak table for 2026 and compared all 100 published values (50 events × 2 publishers) with the committed fixture `research/panchanga/reference-fixtures/geocentric-lunar-phase-events-2026.json` (sha256 `dfd964cf450cee57d76aff780fc2541814ca3ab79ac7e55028f4a88aa6459850`). **100 of 100 values match** in date, phase and minute. The 8 one-minute USNO/NASA differences and the 4 NASA eclipse markers also match. **This is not independent QA.** It was done by the same implementation actor (Claude) that made the original transcription, with the same class of tool (an automated page reader that returns a model-produced reading, not page bytes). Every one of the 50 records therefore **keeps its pending status** for the independent transcription recheck that the PANCHANGA-M1-MILESTONE §5 item 3 requires.

## 2. Sources and retrieval record

| Source id | Exact URL | Retrieved (UTC) | Tool | What the page says about time scale and precision |
|---|---|---|---|---|
| SRC-USNO-PHASES | <https://aa.usno.navy.mil/api/moon/phases/year?year=2026> | 2026-11-03, between 08:42 and 08:46 | WebFetch (page reader) | Response `apiversion` "4.0.1", `numphases` 50. API docs (<https://aa.usno.navy.mil/data/api>, same session): times are "time of the phase (in Universal Time)". UT1/UTC/TT not specified. Precision and rounding not stated |
| SRC-NASA-PHASES | <https://eclipse.gsfc.nasa.gov/phase/phases2001.html> | 2026-11-03, between 08:42 and 08:46 | WebFetch | Table heading as read: "Phases of the Moon: 2026 to 2030 Universal Time (UT)". ΔT column for 2026: `00h01m`, "the value used to convert Dynamical Time to Universal Time". No rounding statement |
| SRC-USNO-PHASE-DEF | <https://aa.usno.navy.mil/faq/moon_phases> | 2026-11-03, same session | WebFetch | Phases occur "when the excess of the apparent ecliptic (celestial) longitude of the Moon over that of the Sun is 0, 90, 180, and 270 degrees". Times are "independent of the location on the Earth". Neither "geocentric" nor a time scale is stated |

**Raw bytes could not be captured.** Direct download of all three URLs from this container was refused by the environment's network policy (`CONNECT tunnel failed, response 403`; [evidence/blocked-raw-capture.txt](evidence/blocked-raw-capture.txt)). So there is no source-file hash. The values below rest on the page reader's output, recorded verbatim in:
- [evidence/usno-moon-phases-2026-retrieved-20261103.txt](evidence/usno-moon-phases-2026-retrieved-20261103.txt)
- [evidence/nasa-espenak-phases-2026-retrieved-20261103.txt](evidence/nasa-espenak-phases-2026-retrieved-20261103.txt)

The NASA page lays out each row as New, First Quarter, Full, Last Quarter. The reader returned 13 rows for 2026 (the first starting with the Jan 3 Full Moon). Claude re-keyed them into one line per event by date and phase. That re-keying is a further manual step by the same actor.

## 3. Comparison

Script: [evidence/compare_phase_sources.py](evidence/compare_phase_sources.py), run with `python3 -I` on the fixture and the two retrieval files. It looks up each fixture value by (month-day, phase name) in the retrieved list for its source and compares the HH:MM. Output: [evidence/comparison-output.txt](evidence/comparison-output.txt).

**Exit status (revision 2, after QA review 5749516454).** The script exits 0 only when every check passes, 1 on any discrepancy, and 2 on unreadable or malformed input (revision 3: including an impossible 2026 date or a time outside 00:00 to 23:59, in the fixture or a publisher file, after QA review 5749654235). Discrepancies are: a minute mismatch; a fixture value absent from a publisher file; a publisher event absent from the fixture; a duplicate key on either side; a fixture case count or publisher event count other than 50; a NASA eclipse-marker mismatch; a marker in the USNO file; a fixture `inter_source_difference_minutes` that disagrees with its own two values. Each is printed as an `ERROR` line, followed by `RESULT PASS` or `RESULT FAIL (n errors)`. Revision 1 printed mismatches but always exited 0, which QA showed by altering a fixture minute. 20 isolated positive and negative tests (15 in revision 2, 5 added in revision 3): [evidence/test_compare_phase_sources.py](evidence/test_compare_phase_sources.py), log [evidence/checker-tests.log](evidence/checker-tests.log).

| Check | Result |
|---|---|
| Fixture values compared | 100 (50 USNO, 50 NASA) |
| Date + phase found in the live list | 100 / 100 |
| Minute identical | **100 / 100**; 0 mismatches |
| Events in the live lists | USNO 50, NASA 50 (12 New, 12 First Quarter, 13 Full, 13 Last Quarter) |
| Live USNO/NASA one-minute differences | 8, NASA later in all 8: Feb 24 FQ, Mar 11 LQ, Apr 10 LQ, Jun 29 Full, Jul 21 FQ, Oct 18 FQ, Dec 1 LQ, Dec 17 FQ. Same 8 as the fixture (cases 08, 10, 14, 25, 28, 40, 46, 48) |
| NASA eclipse markers | Feb 17 `A`, Mar 3 `t`, Aug 12 `T`, Aug 28 `p`. Same as fixture `source_markers` on cases 07, 09, 31, 33 |

**Breakdown that matters for M1.** Of the 25 Tithi-boundary events (New and Full Moon), 24 are identical between publishers and 1 (Full Moon 2026-06-29, 23:56 vs 23:57) differs. Of the 25 Karana-only events (quarters), 18 are identical and 7 differ.

## 4. What this does and does not establish

| Claim | Supported? |
|---|---|
| The fixture's 100 values equal what both publishers show today, as read by Claude's page reader | Yes, 100/100 |
| The fixture was transcribed correctly, checked by someone other than the transcriber | **No.** Same actor, same tool class. A page-reader misreading that repeats itself would not be caught |
| Two publishers agreeing is an independent check of the transcription | **No.** Publisher independence speaks to the astronomy at minute resolution, not to whether Claude copied the numbers correctly |
| Either publisher, or the Sabpuja engine, is accurate to the second | No. Whole-minute publication only (SCI-PAN-01 §5.9) |
| Source rounding rule | Unknown. Neither publisher states it |

**Status of the 50 records:** fixture label `VERIFIED_TWO_INDEPENDENT_PUBLISHERS` unchanged (this PR does not edit the fixture). Transcription status: **SAME-ACTOR RECHECK MATCHED (2026-11-03); INDEPENDENT RECHECK PENDING** for all 50.

## 5. Observation on the 8 differences (inference, not a finding)

All 8 differences go the same way (NASA one minute later). If both publishers rounded to the nearest minute and NASA's instants were systematically δ seconds later, about δ/60 of events would differ. 8 of 50 suggests δ ≈ 10 s (rough 95% range about 4 to 17 s). A truncate-versus-round mix does not fit as well: USNO truncating and NASA rounding would make NASA later about half the time, and NASA truncating would make NASA earlier. 7 of the 8 are quarter phases. Neither page states a method, so this is a hypothesis. It matters for B4 because it says the two publishers may differ by about 10 s in their own models, which is larger than "well under a second".

## 6. Independent verification plan (for ChatGPT QA or a human verifier)

Compact, blind and reproducible. The verifier must not be Claude.

1. **Capture raw bytes.** From a network that allows the hosts, download the three URLs in §2 (for example `curl -sS -o usno-2026.json "<url>"`). Record UTC retrieval time, HTTP status and `sha256sum` of each saved file. For the NASA HTML page, also save a PDF or screenshot of the 2026 rows.
2. **Blind transcription.** Without opening the fixture, extract the 2026 events: from the USNO JSON by a direct JSON parse (no retyping); from the NASA HTML by reading the 2026 rows (by hand, or by a parser the verifier writes). Write one line per event as `MM-DD <Phase name> HH:MM [marker]`, the same format as the `evidence/*-retrieved-*.txt` files.
3. **Compare.** Run `python3 -I docs/science/kun-pan-m1-dec-001/evidence/compare_phase_sources.py research/panchanga/reference-fixtures/geocentric-lunar-phase-events-2026.json <usno.txt> <nasa.txt>`, or the verifier's own script. Expected on a correct fixture: `values 100 mismatches 0` and 8 inter-source differences.
4. **Record per record.** For each of the 50 cases: verifier identity, URL, retrieval time, file sha256, USNO value, NASA value, MATCH or MISMATCH. A mismatch is logged and never silently corrected. The fixture is changed only by a separately authorized task.
5. **Disposition.** A case that matches on both publishers from raw captured bytes becomes `INDEPENDENTLY_RECHECKED`. A case that cannot be captured, or mismatches, stays pending and is excluded from the PAN-QA-04 gate until resolved.

**Owner or environment action that would let Claude capture bytes too:** allow `aa.usno.navy.mil` and `eclipse.gsfc.nasa.gov` in the project's cloud environment network policy. That would give hashed captures, but it would still be a same-actor recheck and would not replace step 2 by someone else.

## 7. Reviewer evidence reported by independent QA (appended; not Claude's verification)

ChatGPT's QA review [5749516454](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/65#pullrequestreview-5749516454) on head `aea018b` reports, in the reviewer's words summarised here and **not re-verified by Claude**:

| Item | As reported by QA |
|---|---|
| Capture | Raw bytes of the USNO API URL and the NASA page in §2, captured on the private QA machine |
| USNO raw sha256 | `8e063694ffbf6cb49a650875f4bf1df6c361f955c63886c9fccfbe8aec084fa8` |
| NASA raw sha256 | `ceb16de952edaf9bf1f7c6d1daf13c7487632c3a5ad78808bd40120a76c9fbd8` |
| Independent script sha256 | `0f41cad8999da8b77140b13c1f8f353cf807b29989c227f51d930c4b01f4e8ab` |
| Result JSON sha256 | `54ff64c52279ef407b308015851db7ec8feb536ff2d5e574ff1075478a897a75` |
| Method | USNO JSON and the NASA 2026 preformatted table parsed independently, then compared with the fixture `dfd964cf…9850` |
| Result | 50 USNO + 50 NASA, **100/100 date + phase + minute matches, 0 mismatches**; the 8 one-minute differences (NASA later) and all 4 eclipse markers reproduced |
| Reviewer's caveats | Initial parser defects were corrected before the successful run. An engineering verification record, not a separate human attestation. No Swiss or engine calculation; no seconds-level or ephemeris certification |

Claude's own §4 status line ("same-actor recheck matched; independent recheck pending") is kept as written for the record. Whether QA's reported recheck satisfies the §6 disposition rule, so that the 50 records become `INDEPENDENTLY_RECHECKED` for PAN-QA-04, is for QA and the owner to record; this file does not change any record's status. The fixture is not edited.

**Reviewer disposition (QA review [5749654235](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/65#pullrequestreview-5749654235), as stated by the reviewer):** the 50 records meet the independently rechecked publisher-transcription-at-minute-precision criterion for a future PAN-QA-04, once the owner adopts the method and tolerance decisions. The fixture stays labelled PROPOSED until separately authorized adoption. This is recorded here as the reviewer's disposition; Claude does not change the fixture or any status.
