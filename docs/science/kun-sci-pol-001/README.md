# KUN-SCI-POL-001: D1/D9 scientific decision package

**DOCUMENTATION ONLY. All recommendations are PENDING OWNER APPROVAL. Production: NO-GO.**

This package prepares three owner decisions left open by KUN-SCI-GOLD-001:
- B-1: the independent Lagna formula tolerance
- B-3: whether the frozen Swiss tolerances apply to the gold matrix
- B-6: near-boundary disclosure

It also proposes the order of the next calculation modules.

It changes nothing else: no engine, schema 0.3.0, report renderer, Hindi catalogue, scientific fixture, existing tolerance, test or infrastructure. It does not edit `docs/DECISIONS.md`, because adoption follows the register's two-step rule after approval.

## Refs

| Item | SHA |
|---|---|
| Base: `main` | `1d4bcb6752010e8d13643287000081b8f38ebd76` (tree `8632cde48b27cee6dd64c6981d8450227b2c2f98`) |
| Evidence: PR #62 head (draft, unmerged, independent QA PASS in review [5747720823](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/62#pullrequestreview-5747720823)) | `6722b5c46c3fb510495d8587b7b613f32691d97a` (tree `84816a56f388ac5e07bae3f63e24740b191da96c`) |
| Gold report used (`python -m tests.sci_gold.run` on `6722b5c`, live swetest) | `sci-gold-6722b5c46c3f.json` sha256 `edb8aab5459a326b57b4abcffc7e8f44a79be2a966baf549e97162d8d4e24bef` |
| PR #62 receipts `SHA256SUMS` / `matrix.json` / Swiss `spec.json` | `71a6a9695f12ade3fadf18c26a7098aba8b16fb1f5febcdd21381ccc63be8eee` / `bc27314f4d243cb673debccf970dd20f8916fdb8d7661262495398556bd0e9c1` / `642a770d713c11bc42fc92fe441da02e4848522fc4978ae3049dddbea33d12a8` |

Nothing from PR #62 is copied or merged here. The analysis reads a separate checkout of `6722b5c`, read-only, and checks the receipt and matrix hashes against PR #62's `PINS.json` before it uses them.

## Files

| File | Content |
|---|---|
| [DECISION-PACKET.md](DECISION-PACKET.md) | The concise owner packet: the three items, recommendations and **decision forms** |
| [B1-LAGNA-FORMULA-TOLERANCE.md](B1-LAGNA-FORMULA-TOLERANCE.md) | B-1 numerical analysis and options |
| [B3-SWISS-TOLERANCE-APPLICABILITY.md](B3-SWISS-TOLERANCE-APPLICABILITY.md) | B-3 distribution, coverage, approval scope and options |
| [B6-NEAR-BOUNDARY-DISCLOSURE.md](B6-NEAR-BOUNDARY-DISCLOSURE.md) | B-6 GOLD-E01 analysis, birth-time sensitivity, three customer-experience options and EN/HI **draft** wording |
| [NEXT-MODULE-ROADMAP.md](NEXT-MODULE-ROADMAP.md) | Inventory of Panchanga research and evidence classes; proposed module order |
| [QA-HANDOFF.md](QA-HANDOFF.md) | What to verify, and how to reproduce it |
| [analysis/analyze.py](analysis/analyze.py) | Standalone analysis script for the numbers above. It is not part of the engine or the tests and is imported by nothing |
| [analysis/results.json](analysis/results.json) | Its output (deterministic; seed 20261103) |

## Claim boundary

- The SWISS figures are Swiss-on-Swiss conformance.
- LAGNA-F tests the ascendant transformation on Swiss-printed inputs.
- The birth-time sensitivity figures come from pyswisseph with the SCI-01 flags, applied to synthetic instants.
- None of this is independent astronomical accuracy: the JPL/INPOP layer remains deferred and BLOCKED. None of it supports a public accuracy claim.
