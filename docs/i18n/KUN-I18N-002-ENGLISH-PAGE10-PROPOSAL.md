# KUN-I18N-002: English page 10 "Hindi edition" wording (proposal only)

**Status: PROPOSAL. Owner decision required. Not applied.** The English report and its pinned
hashes are unchanged in KUN-I18N-002. This is kept separate from the Hindi editorial corrections.

## Problem

Page 10 (Methodology and provenance) of the English report lists, under "Not included in this
edition", the item **"Hindi edition"** (`report/phase1/report_i18n.json`, key `method.exc5`).
Since KUN-I18N-001 the Hindi PDF exists, so the line reads as if no Hindi report is available.
The Hindi report's matching line already says "अंग्रेज़ी पाठ (अलग संस्करण में उपलब्ध)"
("English text (available in a separate edition)").

## Exact replacement wording

| Key | Current English | Proposed English |
|---|---|---|
| `method.exc5` | `Hindi edition` | `Hindi text (available as a separate edition)` |

The Hindi value is unchanged. The proposed line mirrors the Hindi report, stays in the
"Not included in this edition" list (this edition is English-only) and states that the Hindi
edition exists. It is a single drawn line: 170.1 pt in the 8.6 pt body face against 227.6 pt of
column width (the longest existing item, `method.exc2`, is 215.2 pt), so no wrapping or layout
change.

Alternative if the owner prefers to remove the item instead: delete it and render four items
in that column. That changes the layout code as well as the catalog and is not recommended.

## Compatibility impact (measured on a scratch copy, not committed)

Applying only the catalog change above to the KUN-I18N-002 head:

- **All 26 pinned English PDF hashes change**: 13 scenarios × (customer, synthetic sample),
  `BEFORE` in `report/phase1/tests/test_premium_name.py`. Named English PDFs are not pinned by
  hash, but their bytes change as well. Hindi PDFs do not change.
- **Failing tests until the pins are updated (28 subtests, 4 test methods, 2 files):**
  - `test_premium_name.AnonymousReportUnchanged.test_no_name_is_byte_identical_to_c57747a_for_every_scenario` (13 subtests)
  - `test_premium_name.AnonymousReportUnchanged.test_no_name_after_a_named_render_is_still_identical`
  - `test_report_i18n.EnglishUnchanged.test_explicit_en_equals_omitted_and_pr58_for_every_scenario` (13 subtests)
  - `test_report_i18n.EnglishUnchanged.test_english_after_hindi_is_still_identical`
- **Unaffected:** every layout, overlap, clipping, palette, font, extraction and D1/D9 value test
  in `report/phase1/tests` (the rest of the 122 pass); the prototype suite (182 OK, its HTTP
  tests compare against a live render, not a pin); `test_premium_report` still finds
  "Not included in this edition"; `/api/chart` bytes; the browser suites.
- **Byte-identity claim lost:** "English output is byte-identical to the PR #58 renderer" would
  no longer hold. The new pins would have to be recorded as a new, owner-approved English
  baseline and the tests renamed from `c57747a` / `pr58` to that baseline.

Proposed new pins (SHA-256, `generate(fixture, synthetic, palette='baseline')`, pyswisseph
2.10.03, reportlab 4.4.9), as `[synthetic=False, synthetic=True]`:

| Scenario | Customer | Synthetic sample |
|---|---|---|
| s01-first-supported-date | `faabd39e74f29ef5f1ae8486ea15d201cfd6e762656260c59e4e34921b2c6c4c` | `e421cb81bb0920757cd1f1e8ecc4d5ca22adb21dffaccd586ff69686a0ff1109` |
| s02-last-supported-date | `69c308f3b697167c31f5826e6d2fba0c1f7ecd6f3d47002fa148f124bdd99539` | `26ff12fba637f00e3cb9a79e5cd894cee967f180c0ba7b19f487abd70ae9bcce` |
| s03-crowded-d1-house | `4727f547d8d61afec0549f3c112bb08fd061c30f403fb74f9b7c3a8ef3b47040` | `8e8791b4b17fc42e8b62b02481582bcc76fc600d6a397ddbed1c471e12988b14` |
| s04-crowded-d9-house | `e0ebd8028dfe27aa86171dc7711a59387310ef6ec0afb5e246d41ef076f6caf4` | `c865af51320e12ce2926231bb8507207e7de57943a7a97b8c387d07c8e36f2f3` |
| s05-graha-near-boundary | `fbdd58ec8c52172a9209075a548706670ac1c710b6ea72049017f87bbad30af5` | `c09eaf9b15b6b4e69c069e2d8ba65df6eb5dd4faf42d36d102023b20b714d30b` |
| s06-lagna-near-boundary | `3e749daede35a3a95c8c1faecf0d4915b351e4b22d7e7ffb58dbab5031f3c977` | `be84c18f880d9ce08bfc99d6d79c4daeffdbab1e8e5b9c3c885d5632d0f729f3` |
| s07-noon | `24bb5af8c366654cee93792325ab41fab35dd7368cfeb48454dfe422b6c678c1` | `dde07887faa4275bc55a321f56d53c1d844a5dc5c4952279bafb067c7547908c` |
| s08-dawn | `de63595e8ce5921b15e241fb00dc9727c44b4b214e0ce4412757d6b529475917` | `ea789a52984979da63dec8619fe7daf444f9e2c2ccfdfef5b23fec24bee0fea4` |
| s09-evening | `8a30b45790d4bf7fc2e5ca1258744c74c0051d17b1c6be128bcb1eea4fb5e90a` | `d543252562971ac442087321651aaf18be7ce14994b621a0ff078bf6fcaf6cd0` |
| s10-late-night | `7890f3c08b9341b97bc8b57fdfa55ae933ca58a5ee185801b75dc35a9e34aacb` | `e20d9503bfeae5f2e80329f002646cc792757effe16b10072be09e7e7125c1c5` |
| s11-afternoon | `793f18b0900c7b4a02086c67106b3321e4de76fa61b34621ffa5848be7838ae3` | `c12c378b84839530e0267aad846253b9488fe89d3bfdb65a1ee256909f978278` |
| s12-morning | `c388d8db6b36079359f02348d557b023c41ddce4bf416b4844fa6a5ae68254ac` | `e6e212d5c34f36613ed8c06cbbca1623ccd3603d2d262317b245fc524d48b942` |
| s13-remaining-lagna | `45f4a4fa775a2a63bab1eec2b86d0959b963e0afe8e2b4055d036475ca496876` | `eb712dbd3b7c403b4d020683991dd1697d0fd707129c2425152c67fa4c8bfea8` |

## If approved

A separate, owner-authorised task changes `method.exc5` English only, replaces the 26 pins with
the values above (re-measured on that task's exact head), renames the baseline references, and
re-runs the full report, prototype, browser and gateway suites.
