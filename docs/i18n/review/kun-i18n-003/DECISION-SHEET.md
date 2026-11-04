# KUN-I18N-003 Hindi / Jyotish reviewer decision sheet

**To be completed and signed by the independent human reviewer(s). Not filled in by the developer.**
The CSV copy (`DECISION-SHEET.csv`) has the same rows for spreadsheet use.

Reviewed revision (write it exactly as shown; a review of any other revision must say so):

| | |
|---|---|
| Commit | `84fe981c79573ab753b5d7baadf2ff4aa49e819c` |
| Tree | `273d99ee6c91a65117ff676c17ae6f0a2642ecb3` |
| Web catalog `prototype/kundali_prototype/static/i18n.json` SHA-256 | `06c0f071206ffc40a1f6c1eb254ce252bc8e91305568cf787a232f374f064627` |
| PDF catalog `report/phase1/report_i18n.json` SHA-256 | `1483e1fa666005a7182b791904dbb777f63a1a554b1407ff274d59c0b277f81e` |

Decisions: **ACCEPT** (wording is correct as is), **REVISE** (write the exact replacement Hindi and
the key it replaces), **REJECT** (wording is wrong and no replacement is offered; explain).
**NA** where the layer does not apply. Detail for each row: `REVIEW-PACKET.md`; locations: `LOCATIONS.md`.

| ID | Item | Layers | Developer recommendation | Language decision | Jyotish decision | Replacement Hindi (if REVISE) | Reason | Initials |
|---|---|---|---|---|---|---|---|---|
| 1 | "Prepared for": जातक / "… के लिए तैयार" | L+J | REVISE web to "जातक: {name}"; keep PDF जातक |   |   |  |  |  |
| 2 | Pada: चरण | J | ACCEPT | NA |   |  |  |  |
| 3 | Whole-sign house: पूर्ण-राशि भाव; absolute longitude: पूर्ण भोगांश | J+L | ACCEPT पूर्ण-राशि भाव; REVISE absolute longitude term |   |   |  |  |  |
| 4 | Mean node / mean Rahu / lunar nodes: मध्यम पात, मध्यम राहु, चंद्र पात | J | ACCEPT | NA |   |  |  |  |
| 5 | True ayanamsha: स्पष्ट अयनांश | J | ACCEPT | NA |   |  |  |  |
| 6 | Jupiter: गुरु, गुरु (बृहस्पति) | J | ACCEPT | NA |   |  |  |  |
| 7 | Chart abbreviations सू चं मं बु गु शु श रा के; Lagna label लग्न | J+L | ACCEPT |   |   |  |  |  |
| 8 | Date of birth: जन्म दिनांक | L | ACCEPT |   | NA |  |  |  |
| 9 | Nukta, chandrabindu, anusvara policy | L | ACCEPT |   | NA |  |  |  |
| 10 | Place transliterations | L | ACCEPT Indian names; Tromsø at reviewer discretion |   | NA |  |  |  |
| 11 | Latin script kept for names and codes | L | ACCEPT |   | NA |  |  |  |
| 12 | International digits | L | ACCEPT |   | NA |  |  |  |
| 13 | Page 10 not-included line (Hindi: अंग्रेज़ी पाठ (अलग संस्करण में उपलब्ध); English: Change A, applied) | L+Owner | ACCEPT Hindi line |   | NA |  |  |  |
| 14 | Hindi reading-guide sign note | L | ACCEPT |   | NA |  |  |  |
| 15 | D9 footnote: चार्ट स्कीमा 0.3.0 (Change B, applied; was स्वीकृत चार्ट स्कीमा) | L+Owner | ACCEPT applied Change B wording |   | NA |  |  |  |
| 16 | Native date and time pickers follow the browser locale | L | ACCEPT |   | NA |  |  |  |
| 17 | Fallback refusal message | L | ACCEPT |   | NA |  |  |  |
| 18 | Register and tone of all text | L | REVISE at reviewer discretion (see packet) |   | NA |  |  |  |
| C1 | KUN-I18N-002 A1: high-latitude note उत्तर या दक्षिण | L | ACCEPT |   | NA |  |  |  |
| C2 | KUN-I18N-002 A2: धारणा for "assumption" | L | ACCEPT |   | NA |  |  |  |
| C3 | KUN-I18N-002 A3: page 6 D9 note word order | L | ACCEPT |   | NA |  |  |  |
| C4 | KUN-I18N-002: दिनांक masculine plural | L | ACCEPT |   | NA |  |  |  |
| C5 | KUN-I18N-002: चंद्र पात on pages 3 and 7 | J | ACCEPT | NA |   |  |  |  |
| C6 | KUN-I18N-002: ellipsis character | L | ACCEPT |   | NA |  |  |  |

## Reviewer attestation

Complete one block per reviewer. A decision without a complete, signed block is not recorded.

**Hindi language reviewer**

| | |
|---|---|
| Full name | |
| Qualification (e.g. degree, professional editing experience) | |
| Organisation / contact (optional) | |
| Independence: "I did not write or translate the text under review and have no part in its development." | Yes / No |
| Rows reviewed | All / list |
| Commit and catalog SHA-256 reviewed (copy from the table above) | |
| Date (YYYY-MM-DD) | |
| Signature | |

**Jyotish terminology reviewer**

| | |
|---|---|
| Full name | |
| Qualification (e.g. Jyotish training, years of practice, institution) | |
| Organisation / contact (optional) | |
| Independence statement (as above) | Yes / No |
| Rows reviewed | All / list |
| Commit and catalog SHA-256 reviewed | |
| Date (YYYY-MM-DD) | |
| Signature | |

**Owner copy decisions (Sabpuja owner)**

| Decision | Approve / Reject | Date | Signature |
|---|---|---|---|
| Change A: English page 10 "Hindi text (available as a separate edition)" (`CHANGE-A-ENGLISH-PAGE10.md`) | | | |
| Change B: "Chart schema 0.3.0" / "चार्ट स्कीमा 0.3.0" (`CHANGE-B-SCHEMA-WORDING.md`) | | | |

The owner may sign either this block or `OWNER-COPY-ATTESTATION.md` (same two decisions, with the exact commit
and catalog hashes). Both changes are applied in the reviewed source above on the owner's chat approval for
implementation (issue #73); the signed owner record is still pending.

The signed sheet is the evidence the acceptance register cites. AI assistants (Claude, ChatGPT)
cannot sign any block on this sheet.
