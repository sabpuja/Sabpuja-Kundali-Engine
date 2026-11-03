# KUN-B6D-REVIEW-001: B-6 birth-time sensitivity wording (editorial review packet)

**Documentation only. Developer recommendation, not reviewed, not approved.** Production NO-GO; PR #1 HOLD; PRs #62 and #63 remain draft.

This folder prepares customer wording for the SCI-06 birth-time sensitivity disclosure for human Hindi, Jyotish and owner review. It does not implement the disclosure.

| File | Content |
|---|---|
| [`REVIEW-PACKET.md`](REVIEW-PACKET.md) | Existing PR #63 wording and its defects; recommended English and Hindi for each message with trigger, back-translation and synthetic example; glossary; placeholders; short and expanded examples; special cases; open owner questions |
| [`b6-wording-draft.json`](b6-wording-draft.json) | The recommended strings in catalog form (55 keys). Not loaded by any application |
| [`DESIGN-INTEGRATION.md`](DESIGN-INTEGRATION.md) | Where approved wording would appear in the ten-page PDF and the browser interface, using the Foundations design system |
| [`SIGNOFF-SHEET.md`](SIGNOFF-SHEET.md) | Blank decision fields for the Hindi language reviewer, the Jyotish reviewer and, separately, the owner |
| [`check_packet.py`](check_packet.py) | Mechanical developer checks (placeholder parity, verbatim presence, terminology, banned vocabulary, lengths, contrast). Run `python3 -I check_packet.py`; it is not a language review |
| [`EVIDENCE-MANIFEST.md`](EVIDENCE-MANIFEST.md) | Base verification, source hashes, file hashes and the check output |

Base: `main` at `de721d665ed80ed58291f59962677065a73f0b26` (PR #64 merge). Policy: SCI-06 as adopted in the [PR #64 receipt](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/64#issuecomment-6598563378).
