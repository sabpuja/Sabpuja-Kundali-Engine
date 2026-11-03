# KUN-SCI-POL-002 independent QA handoff

## Check
1. **Documentation only.** `git diff --stat origin/main HEAD` lists `docs/DECISIONS.md` (one appended section, no existing line changed) and `docs/science/kun-sci-pol-002/` only. `git diff origin/main HEAD -- docs/DECISIONS.md | grep '^-[^-]'` is empty.
2. **Status discipline.** SCI-04, SCI-05 and SCI-06 read **OWNER SELECTED PRE-MERGE - CANONICAL ADOPTION PENDING** everywhere. Nothing says APPROVED / CANONICAL, and no task is described as authorized.
3. **Provenance.** The records do not present PR #63 comment 6598001352 as an authenticated owner signature. They name its author account and its own disclaimer, and they keep it separate from the owner's own KUN-SCI-POL-002 message (transcribed in the PR description).
4. **Scope fidelity.** Each record's scope matches comment 6598001352 and the owner's task:
   - B-1: 1e-9°, \|lat\| ≤ 66.0°, test-only.
   - B-3: values unchanged, KUN-SCI-GOLD-001 matrix only.
   - B-6: Option 1; six items; ±2 min; near-exact-boundary note; optional premium Option 2 appendix; classifications unchanged; wording not approved.
5. **Hashes cited.** Compare against the sources:

| Item | sha256 |
|---|---|
| PR #63 `analysis/results.json` at `1b70927` | `cc402c73d0d820fed5271d7dedd2e534a1a407685574c44d62b306d6467e82d2` |
| PR #62 gold report `sci-gold-6722b5c46c3f.json` | `edb8aab5459a326b57b4abcffc7e8f44a79be2a966baf549e97162d8d4e24bef` |
| KUN-01-SWISS-01 `spec.json` (PR #62) | `642a770d713c11bc42fc92fe441da02e4848522fc4978ae3049dddbea33d12a8` |
| Gold `matrix.json` (PR #62) | `bc27314f4d243cb673debccf970dd20f8916fdb8d7661262495398556bd0e9c1` |
| `research/panchanga/reference-fixtures/geocentric-lunar-phase-events-2026.json` (`main`) | `dfd964cf450cee57d76aff780fc2541814ca3ab79ac7e55028f4a88aa6459850` |
| `…/derived-classification-cases.json` (`main`) | `c41b229efe99bf8f3b0015e5fa8fbfb618c77331fa23ace619886d533f920a12` |
| `…/boundary-test-specifications.json` (`main`) | `ba5930d5172d1271bd97ef749af51dad46a7532bef522764568d9af8a269245f` |

6. **Panchanga M1 facts.** The phase set has 50 cases, all `VERIFIED_TWO_INDEPENDENT_PUBLISHERS`: 12 New, 13 Full, 12 First Quarter and 13 Last Quarter. 42 are identical between publishers and 8 differ by 1 minute. No evaluation run was made (PAN-D15 requires tolerances first). Every PAN decision stays PENDING.

## Requested verdict
PASS, CHANGES REQUESTED or BLOCKED on the exact head SHA. A PASS is not owner authorization of the merge.
