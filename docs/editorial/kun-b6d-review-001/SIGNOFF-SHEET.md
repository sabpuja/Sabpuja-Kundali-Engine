# KUN-B6D-REVIEW-001: reviewer and owner sign-off sheet

**Every field on this sheet is blank and PENDING.** No human has reviewed this wording. This sheet must be completed by people, not by Claude, ChatGPT or any other AI system; an AI entry in any reviewer or owner field is invalid. The developer (Claude) prepared the sheet only.

## Material under review

| | Value |
|---|---|
| Wording file | `docs/editorial/kun-b6d-review-001/b6-wording-draft.json` |
| SHA-256 of the wording file presented for review | `5535ba213b0fbc9cc736becbcf46a81f3cf541eeceb8008139d14270772c1af7` |
| Commit presented for review | the head of the KUN-B6D-REVIEW-001 draft PR (record the exact SHA when signing) |
| Policy | SCI-06, canonical per PR #64 adoption receipt 6598563378 |

If the wording file changes after a signature, that signature no longer applies; the changed file needs a new signature against its new SHA-256.

## How to record a decision

For each message group, each reviewer writes **ACCEPT**, **REVISE** (and gives the exact replacement text, quoting the key) or **REJECT** (and gives the reason). Layers:
- **L**: Hindi language (grammar, spelling, naturalness, tone).
- **J**: Jyotish terminology (correct, recognised terms; no interpretive or fear connotations).
- **O**: owner copy approval (English and Hindi customer copy, after L and J).

## Decisions by message group

| Group | Keys | L (Hindi language) | J (Jyotish) | O (owner copy, EN + HI) | Replacement text / reason |
|---|---|---|---|---|---|
| M-01 Labels and tags | `label.*`, `tag.*` | PENDING | PENDING | PENDING | |
| M-02 Offset phrases | `offset.*` | PENDING | PENDING | PENDING | |
| M-03 Lagna Rashi | `note.lagna_rashi.*` | PENDING | PENDING | PENDING | |
| M-04 D9 Lagna | `note.lagna_navamsa.*` | PENDING | PENDING | PENDING | |
| M-05 Moon Rashi | `note.moon_rashi.one` | PENDING | PENDING | PENDING | |
| M-06 Moon Nakshatra and Pada | `note.moon_nakshatra.change`, `note.moon_pada.change` | PENDING | PENDING | PENDING | |
| M-07 Moon D9 Rashi | `note.moon_navamsa.one` | PENDING | PENDING | PENDING | |
| M-08 Exact boundary | `boundary.*`, `body.*` | PENDING | PENDING | PENDING | |
| M-09 Summary | `summary.*`, `item.*`, `list.*` | PENDING | PENDING | PENDING | |
| M-10 Premium appendix | `appendix.*`, `ref.*` | PENDING | PENDING | PENDING | |
| M-11 Methodology row | `method.row.*` | PENDING | PENDING | PENDING | |
| M-12 Glossary G-01 to G-15 | `REVIEW-PACKET.md` §4 | PENDING | PENDING | PENDING | |

## Owner decisions on open questions (REVIEW-PACKET.md §8)

| ID | Question | Developer recommendation | Owner choice | Date |
|---|---|---|---|---|
| B6D-Q1 | Exact-boundary threshold | < 1 s, or resolution-limited | PENDING | |
| B6D-Q2 | Time rounding buckets | less than a minute / about 1 / about 2 minutes | PENDING | |
| B6D-Q3 | Appendix placement | Premium only, conditional page after Methodology | PENDING | |
| B6D-Q4 | Hindi label | जन्म समय टिप्पणी | PENDING | |
| B6D-Q5 | Include Moon D9 Rashi message | Yes | PENDING | |
| B6D-Q6 | Include `summary.record` | Yes, subject to L review | PENDING | |
| B6D-Q7 | Window instants outside the supported date range | Engineering task to propose | PENDING | |

## Attestations

### Hindi language reviewer (L)

| | |
|---|---|
| Name | |
| Qualification | |
| Independence (not the developer, not an AI, no conflict) | |
| Commit SHA reviewed | |
| Wording file SHA-256 reviewed | |
| Date | |
| Signature | |

### Jyotish terminology reviewer (J)

The same person may sign L and J only if they hold both qualifications.

| | |
|---|---|
| Name | |
| Qualification | |
| Independence (not the developer, not an AI, no conflict) | |
| Commit SHA reviewed | |
| Wording file SHA-256 reviewed | |
| Date | |
| Signature | |

### Owner copy approval (O), separate from L and J

Owner approval of customer copy is given only after L and J have signed, and is separate from approval of any implementation, merge, deployment or release.

| | |
|---|---|
| Name | |
| English copy: approved keys / exceptions | |
| Hindi copy: approved keys / exceptions | |
| Commit SHA approved | |
| Wording file SHA-256 approved | |
| Date | |
| Signature | |

## Status

| Layer | Status |
|---|---|
| Developer recommendation (Claude) | Prepared; this is not a review |
| Independent engineering QA of the packet (ChatGPT) | PENDING |
| Human Hindi language review | PENDING |
| Human Jyotish review | PENDING |
| Owner copy approval | PENDING |
| Implementation, customer release | Not authorized |
