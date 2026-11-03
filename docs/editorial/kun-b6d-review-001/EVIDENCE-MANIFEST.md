# KUN-B6D-REVIEW-001: evidence manifest

Developer evidence only (Claude). Not independent QA, not a language or Jyotish review.

## Base verification (2026-11-03)

| Check | Result |
|---|---|
| `git ls-remote origin refs/heads/main` | `de721d665ed80ed58291f59962677065a73f0b26` |
| Commit subject | "Merge PR #64: canonical SCI-04, SCI-05, SCI-06 decision records" (2026-11-03 13:36:58 +0530) |
| Base tree | `80597a0db7a49f1ebbd6f6faa713b7ea1627af45`, equal to the reviewed PR #64 tree stated in the receipt |
| Adoption receipt | [PR #64 comment 6598563378](https://github.com/sabpuja/Sabpuja-Kundali-Engine/pull/64#issuecomment-6598563378), author `ubermensch-site`, 2026-11-03T08:07:58Z; records SCI-06 as OWNER APPROVED / CANONICAL and "No customer-facing English/Hindi wording has been approved" |
| PR #63 | open, draft, unmerged, head `1b70927bed1e040f55441b5b710600ae6fe11216` |
| PR #62 | open, draft, unmerged, head `6722b5c46c3fb510495d8587b7b613f32691d97a` |

## Sources read (not modified)

| Source | Identifier |
|---|---|
| PR #63 `docs/science/kun-sci-pol-001/B6-NEAR-BOUNDARY-DISCLOSURE.md` | blob `1bfc31fcdc010272397daad244e7033e9fd1a89b`, SHA-256 `fa537ed1c8e8e17059a5632449150a1ad2602bd88c73a599d3f5baa0e80929f5` |
| PR #61 head | `fee3967d62d0229e31de98682da9ada5d9190e93`, tree `ae4bbf144d0d0c1209c6274b465009757711dfe9` |
| Web catalog at PR #61 head | `prototype/kundali_prototype/static/i18n.json` SHA-256 `5cf9e5fcb4234dd971fa1c512c6c6da6567918d38a0c7e61c9e6d8cd496b17f1` |
| PDF catalog at PR #61 head | `report/phase1/report_i18n.json` SHA-256 `324b19ec2269b578f026b4b1dbebbd73d9b3b2f3d4879e2cca9dedb325ac0145` |
| Synthetic English sample PDF (KUN-I18N-003 packet asset) | SHA-256 `37b77f9a4013d5fb6ccfa379ac71c2bcd186f28428f1b010ff52ee63426010ea` |
| Synthetic Hindi sample PDF (KUN-I18N-003 packet asset) | SHA-256 `7590ea3a5b094e1f92e27ea975af262219a3bef4cd49219e48882944282588c7` |

## Package files (SHA-256)

This manifest does not list its own hash.

```
651917da70e0b478edcccd678b3bc175086e2c8a0de3f6fc6c694931f10d3117  README.md
148d217890d48d3afeeb75073b794ca0d005aed70b353ad15fc357da412b349c  REVIEW-PACKET.md
5535ba213b0fbc9cc736becbcf46a81f3cf541eeceb8008139d14270772c1af7  b6-wording-draft.json
957dd180065b50c833dd0fb2010cef1bdab7908e7f485c7d4b63a652210aed06  DESIGN-INTEGRATION.md
1c40cb9ad1e317af681cd6e15b68b68244dc4f33c29341a17dae4727fc3b6b11  SIGNOFF-SHEET.md
cb76b5b22d5cc51df5c7e7ffca8f6ec1f608720c5ecd7613f65cd34a8f641a10  check_packet.py
```

## Unchanged application proof

The PR adds only the seven files in `docs/editorial/kun-b6d-review-001/` and changes or deletes nothing. Verify with `git diff --stat de721d665ed80ed58291f59962677065a73f0b26 <head>` (expected: 7 files changed, insertions only) and `git diff --name-only de721d6 <head> | grep -v '^docs/editorial/kun-b6d-review-001/'` (expected: empty). No engine, schema 0.3.0, metadata `/3`, reference data, tolerance, renderer, catalog, PDF, interface, preview or infrastructure file is touched.

`REVIEW-PACKET.md` was rendered from the JSON strings by a scratch tool so that every string is shown verbatim; `check_packet.py` independently confirms that.

## Developer check: `python3 -I check_packet.py` (Python 3.13.18)

```
== Length table (code points / visible characters)
key                                   EN    HI HI vis  HI/EN
label.note                            15    16     12   1.07
label.boundary                        13    12      7   0.92
label.more                            20    18     13   0.90
tag.note.pdf                          27    29     24   1.07
tag.boundary.pdf                      25    25     19   1.00
offset.later.lt1                      24    27     22   1.12
offset.later.m1                       20    18     15   0.90
offset.later.m2                       21    18     15   0.86
offset.earlier.lt1                    26    28     23   1.08
offset.earlier.m1                     22    19     16   0.86
offset.earlier.m2                     23    19     16   0.83
note.lagna_rashi.one                 251   207    163   0.82
note.lagna_rashi.both                315   293    239   0.93
note.lagna_navamsa.one               253   206    166   0.81
note.lagna_navamsa.both              314   292    242   0.93
note.lagna_navamsa.multiple          216   186    152   0.86
note.moon_rashi.one                  145   132    104   0.91
note.moon_navamsa.one                144   122    101   0.85
note.moon_nakshatra.change           207   182    152   0.88
note.moon_pada.change                198   166    135   0.84
boundary.rashi                       242   221    175   0.91
boundary.navamsa                     267   236    189   0.88
boundary.nakshatra_pada              336   307    257   0.91
boundary.convention                  117   109     74   0.93
boundary.rounding                    126   113     78   0.90
body.lagna                             5     4      3   0.80
body.moon                              4     5      3   1.25
item.lagna_rashi                       5     4      3   0.80
item.lagna_navamsa                     8     7      6   0.88
item.moon_rashi                       10    10      6   1.00
item.moon_navamsa                     13    16     11   1.23
item.moon_nakshatra                   23    20     16   0.87
item.moon_pada                         9    12      9   1.33
list.join                              2     2      2   1.00
list.join_last                         5     4      4   0.80
summary.body                         237   199    150   0.84
summary.record                       172   173    125   1.01
appendix.title                        25    21     17   0.84
appendix.p1                          390   349    261   0.89
appendix.p2                          271   227    165   0.84
appendix.col.placement                 9     6      3   0.67
appendix.col.entered                  20    18     14   0.90
appendix.col.alternative              12    10      8   0.83
appendix.col.when                     29    24     18   0.83
appendix.cell.boundary                38    27     21   0.71
appendix.cell.multiple                39    38     30   0.97
appendix.p3                          391   377    281   0.96
appendix.p4_boundary                 276   270    187   0.98
appendix.p5_scope                    182   170    125   0.93
ref.birth_details.pdf                 11    12     10   1.09
ref.birth_details.web                 23    26     18   1.13
ref.method.pdf                        11    12     10   1.09
ref.method.web                        23    25     18   1.09
method.row.label                      16    19     13   1.19
method.row.value                     200   178    136   0.89

== Contrast (WCAG 2.x)
Note text: Sacred Brown on Light Cream               #4E342E on #FFF8E7: 10.69:1 (meets 4.5:1)
Note text: Deep Brown on Light Cream                 #33241F on #FFF8E7: 14.04:1 (meets 4.5:1)
Note text: Sacred Brown on Ivory                     #4E342E on #FFFBEF: 10.94:1 (meets 4.5:1)
Label: Saffron 700 on Light Cream                    #C84700 on #FFF8E7:  4.55:1 (meets 4.5:1)
Label: Saffron on Light Cream (not used for text)    #D35400 on #FFF8E7:  3.94:1 (BELOW 4.5:1)
Rule: Temple Gold on Light Cream (non-text, 3:1)     #F4B400 on #FFF8E7:  1.74:1 (BELOW 3.0:1)
Rule: Saffron on Light Cream (non-text, 3:1)         #D35400 on #FFF8E7:  3.94:1 (meets 3.0:1)

== 55 keys checked
All mechanical checks pass. (This is not a language or Jyotish review.)
exit=0
```

## Negative control (the checker catches defects)

A scratch copy of the wording file was altered: चंद्र → चंद्रमा in `note.moon_rashi.one.hi`, `{to_rashi}` removed from `note.lagna_rashi.one.hi`, "dosha" appended to `summary.record.en`, and `label.note.hi` set to the PR #63 form "जन्म-समय सूचना". Result (problems section):

```
PROBLEMS:
  - note.lagna_rashi.one: placeholders EN ['from_rashi', 'offset', 'to_rashi'] != HI ['from_rashi', 'offset']
  - note.lagna_rashi.one.hi: not shown verbatim in REVIEW-PACKET.md
  - note.moon_rashi.one.hi: not shown verbatim in REVIEW-PACKET.md
  - summary.record.en: not shown verbatim in REVIEW-PACKET.md
  - label.note.hi: G-08 'जन्म समय' without hyphen (catalog form)
  - note.moon_rashi.one.hi: G-05 Moon is चंद्र (catalog form), not चंद्रमा
  - summary.record.en: banned term 'dosha'
exit=1
```

## Not done in this task

No human review was requested or recorded. No engine was run against any boundary case: every minute value in the examples is constructed, except GOLD-E01, whose values are quoted from PR #63. No wording is approved.
