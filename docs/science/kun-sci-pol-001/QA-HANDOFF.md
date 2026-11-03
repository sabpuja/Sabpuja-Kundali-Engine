# KUN-SCI-POL-001 independent QA handoff

## Scope to check
1. **Documentation only.** The PR adds files under `docs/science/kun-sci-pol-001/` and nothing else. `git diff --stat origin/main HEAD` should list only these paths.
2. **No approval language.** B-1, B-3 and B-6 appear everywhere as PENDING OWNER APPROVAL. No proposed tolerance or wording is described as approved or frozen. The existing frozen values in B-3 are described as frozen for KUN-01-SWISS-01 only.
3. **The numbers reproduce.** See below.
4. **Evidence classes are kept apart.** In the roadmap, reviewer-collected IMD candidates (Stage A/B, with Stage C and D at 0 of 46) are kept separate from the USNO/NASA references Claude sourced independently. PR #48 is not used.
5. **The Hindi text is marked as a draft** for human editorial and Jyotish review.

## Reproduce the analysis

```bash
# 1. PR #62 exact head, read-only, in its own directory
git worktree add --detach /tmp/pr62 6722b5c46c3fb510495d8587b7b613f32691d97a
# 2. Gold report on that head (live swetest as in PR #62's README), or use your independent 6722b5c report
(cd /tmp/pr62 && python -m tests.sci_gold.run --ephe "$EPHE" --swetest "$SWETEST" --receipt "$RECEIPT" --report-dir /tmp/gold)
# 3. Analysis (pyswisseph 2.10.3.2, pinned .se1 files, mpmath 1.3.0; wheel sha256 a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c)
unset SE_EPHE_PATH
python -I docs/science/kun-sci-pol-001/analysis/analyze.py --pr62 /tmp/pr62 \
    --gold-report /tmp/gold/sci-gold-6722b5c46c3f.json --ephe "$EPHE" --out /tmp/results.json
```

`python -I` ignores `PYTHONPATH`. If mpmath is not installed in the interpreter, put it on `sys.path` in another way, as done here:

```bash
python -I -c "import sys,runpy; sys.path[:0]=['/path/to/mpmath']; sys.argv=[...]; runpy.run_path('analyze.py', run_name='__main__')"
```

Compare the output with the committed `analysis/results.json`. Two runs here were byte-identical. Only these fields can differ:
- `inputs.gold_report_sha256`: an independently produced gold report records a different swetest binary hash in its environment block. Its `results[]` must equal ours.
- `inputs.python`.

## Key numbers to confirm

| Item | Value |
|---|---|
| B-1 \|LAGNA-F\| | max 4.33e-11°, median 2.47e-12°. Ratio to the per-chart quantisation bound at most 0.80. float64 evaluation error at most 8.9e-14°. Envelope worst-case bound 4.8e-10° (\|∂A/∂ARMC\| 42.4 at −66°, ARMC 90°) |
| B-3 SWISS | 500/500 engine values = `round(swetest, 8)`. Max 4.999992e-9° = 0.50 × 1e-8°. Within 1e-9° of an edge: only GOLD-E01 Moon (7.1e-10°). Next nearest 2.4e-4° (GOLD-B01b Moon) |
| B-6 sample (n = 20,000, seed 20261103) | Change within ±2 min: Lagna Navamsa 29.4%, Lagna Rashi 3.5%, Moon Pada 1.1%, Moon Nakshatra 0.32%, Moon Rashi 0.13% |
| GOLD-E01 | 6 BOUNDARY-INDETERMINATE rows. Engine and reference both give Simha, Mesha, Magha 1. Time to edge 2.0e-5 s |

## Remaining blockers (unchanged)
- DATA-01.
- JPL/INPOP: deferred; ASTRO stays BLOCKED.
- Hindi coverage of 11 places.
- UX-01, UX-02, UX-03, SEC-01, LEG-01 and PERF-01: PENDING.
- PR #62: draft. PR #1: HOLD. Production: NO-GO.

## Requested verdict
PASS, CHANGES REQUESTED or BLOCKED on the exact head SHA of this PR, before the three items go to the owner.
