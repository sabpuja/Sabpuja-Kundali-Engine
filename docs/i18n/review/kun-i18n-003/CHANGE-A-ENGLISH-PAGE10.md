# Change A: English page 10 "Hindi edition" (owner-controlled)

**Status: APPLIED (KUN-I18N-COPY-005, issue #73).** The owner approved this change for implementation and exact-SHA independent QA in chat on 2026-11-04 ("i will go with your recommendation", in reply to the question whether to approve Changes A and B exactly as documented). That chat decision is not a signed owner attestation: register item 13 `owner_copy` stays **PENDING** until the owner signs `OWNER-COPY-ATTESTATION.md`. Not merged, not released. The text below is the original specification, kept for traceability; the patch under `patches/` is the historical proposal and is not re-applied.
Apply only after the owner's explicit approval, recorded with attribution in
`editorial-acceptance-register.json` (item 13, `owner_copy`) in the same commit.

## Change

| Key | Current English | Approved English (if approved) | Hindi |
|---|---|---|---|
| `report/phase1/report_i18n.json` `method.exc5` | `Hindi edition` | `Hindi text (available as a separate edition)` | unchanged: `अंग्रेज़ी पाठ (अलग संस्करण में उपलब्ध)` |

Page 10, "Not included in this edition" list, fifth line. One drawn line: 170.1 pt in the 8.6 pt
body face against 227.6 pt of column width (the widest existing item is 215.2 pt). The web page is
unaffected.

## Patch

`patches/change-a-english-page10.patch` (apply with `git apply`, on this branch's head; it
applies cleanly with or without Change B, in either order). It changes:

1. `report/phase1/report_i18n.json`: the English value above.
2. `report/phase1/tests/test_premium_name.py`: the 26 pinned English hashes (`BEFORE`) replaced by
   the values below, and the comment naming the new owner-approved baseline.
3. `report/phase1/tests/test_owner_copy_change_a.py` (new): exact wording, Hindi unchanged, the
   new line drawn exactly once on page 10 of every scenario and "Hindi edition" gone.
4. `docs/i18n/review/kun-i18n-003/editorial-acceptance-register.json`: `reviewed_source`
   PDF catalog hash updated to the new catalog bytes.

After `git apply`, run `PYTHONPATH=src:prototype python docs/i18n/review/kun-i18n-003/refresh_manifest.py`: the patch changes `editorial-acceptance-register.json`, so the packet manifest must be refreshed in the same commit, or `test_review_packet_assets.py` fails (by design). The patch updates only the register's catalog SHA-256, so
`test_editorial_register.py` also fails on the patched tree until the source is re-pinned
(KUN-I18N-003B, by design): commit the approved change as `X`, then in a follow-up commit run
`refresh_manifest.py --pin-source X` (commit, tree, SHA-256 and blob IDs read from git) and rerun
the suites. Any decision recorded before the change is then stale and must be re-confirmed. This regenerates `assets/sample-en-anonymous.pdf` (page 10 changes) and updates its SHA-256 in `REVIEW-PACKET.md`; regenerate `assets/en-hi-page-10.png` too before asking for review.

The patch does **not** fill in the owner decision; that must be the owner's own recorded approval.

## Measured impact (scratch copy at the packet commit, `evidence/11-change-a-pdf-bytes.txt`)

| PDFs (13 scenarios each) | Identical to before |
|---|---|
| English customer, anonymous | 0/13 (all change; pinned) |
| English sample, anonymous | 0/13 (all change; pinned) |
| English sample, named (Devanagari, Latin) | 0/26 (all change; not pinned by hash) |
| Hindi (all 52) | 52/52 (no change) |

Pinned English hashes after Change A (SHA-256, `[synthetic=False, synthetic=True]`), identical to
the KUN-I18N-002 proposal measurement:

| Scenario | Customer | Sample |
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

Tests that depend on the pins (pass with the patch, fail without the pin update): 
`test_premium_name.AnonymousReportUnchanged` (both methods) and `test_report_i18n.EnglishUnchanged`
(two methods), 28 subtests. Their names still say `c57747a` / `pr58`; renaming them is optional
and, if wanted, belongs in the same approved commit.

## Acceptance criteria for an approved baseline change

1. Owner approval recorded (name, date, the exact commit approved, evidence) in the register; no
   approval inferred from QA or from this document.
2. One commit, exact SHA, containing only the four files above (plus optional test renames).
3. `method.exc5` English is exactly `Hindi text (available as a separate edition)`; Hindi byte-identical.
4. Fresh hashes recomputed on that commit equal the table above; if the toolchain differs
   (reportlab, fonts, Python), recompute and explain every difference before pinning.
5. All 52 Hindi PDFs byte-identical to the previous head; all other English pages carry the same
   extracted text and drawings (only page 10, one line, differs).
6. Full suites green on the commit: engine, prototype, report (including the layout, overlap,
   clipping, minimum-size, palette, font and extraction tests), browser e2e / name / i18n at
   280/375/768/1440, gateway name, locale and auth/log privacy stacks, `/api/chart` byte identity.
7. Independent QA verdict on that exact SHA before any preview update; still no release.
