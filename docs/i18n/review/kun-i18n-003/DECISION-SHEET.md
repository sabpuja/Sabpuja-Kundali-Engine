# KUN-I18N-003 Hindi / Jyotish reviewer decision sheet

**For the independent human reviewer(s). Not filled in by the developer. No signature is needed**
(KUN-GOV-SIMPLE-001, issue #75): give your decisions as a GitHub issue or PR comment, or to the owner, who posts them there.
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

## Reviewer details

No attestation block or signature is needed (KUN-GOV-SIMPLE-001, issue #75). With your decisions, give your
name and the commit and catalog SHA-256 you reviewed (copy them from the table above). The developer records
each decision in `editorial-acceptance-register.json` with your name and the GitHub record of your feedback.
AI assistants (Claude, ChatGPT) cannot give a reviewer decision.

**Owner copy decisions (Changes A and B):** decided by the owner in chat (issue #73) and recorded as
owner-accepted under issue #75. Nothing to sign.
