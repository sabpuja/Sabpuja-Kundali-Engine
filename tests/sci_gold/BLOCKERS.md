# KUN-SCI-GOLD-001 scientific decision and tolerance blockers

None of these is resolved by this workstream. Each needs an owner decision or
independent QA. Until then the affected layer is reported, never counted as PASS.

| ID | Blocker | Affected layer / fixtures | Effect now | Needed to unblock |
|---|---|---|---|---|
| B-1 | No frozen tolerance for an independent Lagna check (REL-01 ledger row 1: "no tolerance frozen"; SCI-01e: "no golden-chart Lagna tolerance") | `LAGNA-F`, all 50 charts | `BLOCKED`. Observed max |formula − swetest| is reported (about 4e-11°) | Owner/QA to freeze a Lagna formula tolerance with a written basis (a value much larger than the observed float noise, for example 1e-8°, is a proposal only) |
| B-2 | Independent JPL/INPOP astronomy is optional and deferred (issue #15; PRD OD-05) | `ASTRO`, all 50 charts | `BLOCKED`; no external value obtained | Separate owner authorization for KUN-01-PG1 |
| B-3 | The frozen KUN-01-SWISS-01 tolerances (spec.json `642a770d…`: binding 1e-9°, engine 1e-8°) were frozen for the 24 SC cases; this matrix reuses them by reference | `SWISS`, `RULES` boundary band | Applied; all 500 SWISS rows pass (max 4.99999e-9°, under the 5e-9° display half-unit) | Independent QA to confirm the reuse for the gold matrix |
| B-4 | DATA-01 historical civil-clock and birthplace verification is open | `TIME` | `TIME PASS` means IANA 2026e conformance only. Pre-1970 refused (GOLD-R11, R12); Kathmandu 1985/86 and Dhaka 2009 follow IANA, not an independently verified clock record | DATA-01 research and owner decisions |
| B-5 | Future instants (after the pinned 2027-06-28 leap-second list expiry) are projections (SCI-01h) | 18 charts | `QUALIFIED`, never PASS | None for this task; disclosure already emitted (`FUTURE_CIVIL_TIME_PROJECTED`) |
| B-6 | No decision on how a customer report treats a value within the reference band of an edge | GOLD-E01 | `BOUNDARY-INDETERMINATE` | Owner decision (for example a near-boundary disclosure); no method change implied |
| B-7 | Hindi place coverage is limited to the terminology register | 11 Hindi PDF checks | `BLOCKED` | Place-data / i18n work, not science |

Engineering-accuracy gate and premium-report-quality gate are kept separate:
this package is evidence for the engineering-accuracy gate (TIME, SWISS, RULES,
METHOD, DISCLOSURE, REFUSAL) and for report *fidelity to engine values* only. It
makes no statement on premium-report design, editorial or Hindi language quality,
which stay with KUN-RPT/KUN-I18N QA.
