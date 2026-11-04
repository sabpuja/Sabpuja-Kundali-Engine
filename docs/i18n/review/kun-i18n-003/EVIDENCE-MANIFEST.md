# KUN-I18N-003 evidence manifest

| | |
|---|---|
| Base (PR #60 head, re-fetched: no drift) | `c9f147bad9b50c5eb85585b0e3e952e49fb5ac40`, tree `85e38f1dbafc0eef4dc24f87c5910b118261fb73` |
| Packet commits | see PR #61; the first is `3459c63639502d93284c541bd8d673f87f2542a8` |
| Reviewed source since KUN-I18N-COPY-005 | `84fe981c79573ab753b5d7baadf2ff4aa49e819c` (Changes A and B applied; `editorial-acceptance-register.json` `reviewed_source` holds its tree, catalog SHA-256 and blob IDs). The English sample PDF, `assets/en-hi-page-10.png` and the eight result screenshots (English and Hindi at 280, 375, 768 and 1440 px, under `assets/screens/`) were regenerated at that commit; every other asset is unchanged. |

## Application unchanged at KUN-I18N-003 (Task 4, historical)

The packet commits add files under `docs/i18n/review/kun-i18n-003/` and two tests,
`report/phase1/tests/test_editorial_register.py` (register gate) and
`report/phase1/tests/test_review_packet_assets.py` (this manifest: every package file listed, committed and
matching its hash; every referenced asset present; the three sample PDFs equal to the current renderer's output
from the synthetic fixture `s11-afternoon`). The three sample PDFs are committed with `git add -f`, because the
root `.gitignore` ignores `*.pdf`; `.gitignore` itself is unchanged. Nothing else changes: `src`, `prototype/kundali_prototype`
(including both catalogs, `index.html`, `server.py`), `report/phase1` source, `preview` (Docker, gateway, security
configuration), `tests`, `machine`, `data`, `docs/DECISIONS.md`, `docs/api-contract.md` and `docs/i18n/TERMINOLOGY.md`
have identical git tree/blob objects at the base and the head (`evidence/01-unchanged-application.txt`, rerun on the
final head). All 104 premium PDFs are byte-identical and `/api/chart` is byte-identical (evidence 02, 03). The
owner-copy patches are files under `patches/` and were **not applied** in KUN-I18N-003. (Since
KUN-I18N-COPY-005 both changes are applied in the reviewed source above; this section describes KUN-I18N-003.)

## Files in this package (SHA-256)

| SHA-256 | File |
|---|---|
| `cca69914637b1705ee19af8f076094d981bb16a43e0ee7871a5f37bd78862525` | `CHANGE-A-ENGLISH-PAGE10.md` |
| `a52150d17ab5f8f5ba2d2ad7cdda37ed229035a462e0d370dc66182f63fab5bc` | `CHANGE-B-SCHEMA-WORDING.md` |
| `c99eae20648a787c64e0ea916c17ab276610c7d01c1e9f299f645af972b98c97` | `DECISION-SHEET.csv` |
| `c82b2566fcf960822e63a8c3dfd61cc09afdc6f8689d7d3950cdb89b81eeb2b3` | `DECISION-SHEET.md` |
| `d19d897407625b433b14d8ef5595e3c6a4b17c08ba112768a9f45b9186548465` | `EDITORIAL-ACCEPTANCE-REGISTER.md` |
| `9690c9afd5dc1f7ee9c10e6edc38033cd3017b5ad77422bb5b879f7f84803198` | `LOCATIONS.md` |
| `c00d5c12319076c02e07158d1f0f2991876322fd9d9516c64e560ff0d566527f` | `OWNER-COPY-ATTESTATION.md` |
| `8385911664de51054ee1a3b50563dba78c5f2e560977a639c06fce896fbf51ce` | `README.md` |
| `e9f9b9718bc873bea3ccbc73b3772fa5eb0ae579a3ed0b6b2573b508bc820058` | `REVIEW-PACKET.md` |
| `732231a491cd70c4f9719001fef0bde1d63e39602f4e112eeef248a9ad32a66d` | `assets/en-hi-page-01.png` |
| `912c7b85e9241a9061f53ffc0ec714b4c217630faceff44288f79e944e5166d4` | `assets/en-hi-page-02.png` |
| `b5d5574356f9b202aac3f4c099a9404527af08a8bc3312628e07e8ce9625ecae` | `assets/en-hi-page-03.png` |
| `2fb3f8a8828597f652f0b664d379306459072aef52ba0699e24275fb5b6ec8f3` | `assets/en-hi-page-04.png` |
| `e924b186b3a41b9bcedd5b3ba239b75396f214544f8a1a2d425981a75f8e839e` | `assets/en-hi-page-05.png` |
| `5975f5fda4cfd680c9c573ece30835dedd6d0edca1a9e2152f475f6c5afe99ab` | `assets/en-hi-page-06.png` |
| `59782a41224f515b8bb9e39c8a58c833ae89f51cd539d174815599d076114322` | `assets/en-hi-page-07.png` |
| `d3fb7e2986921dabfdb279e5e1bdd6f6a4e0ae466e858d99a7c5f7b4b727921f` | `assets/en-hi-page-08.png` |
| `ed142a86b6a4560138dcb63c21e6c82eb9019a57cbafd69d9a628ad0933627d0` | `assets/en-hi-page-09.png` |
| `a613e294fac2b41f91bd19b8d0470bd253a939e1895d9d87da40f367d2da2b86` | `assets/en-hi-page-10.png` |
| `e3035590f3e2d69d9347528ed4e89880c0557b9e9d6c590b9792857486cbfdc7` | `assets/hi-before-after-page-03-zoom.png` |
| `c361ecda56d916ff84578d310a08b9ce6c202ba95dcaeac828760d6fae841205` | `assets/hi-before-after-page-06-zoom.png` |
| `369b09bee4e8029985b1c40cdf2d053be5ab60d3d3c61ac006cbedc131af6f64` | `assets/hi-before-after-page-07-zoom.png` |
| `c12c378b84839530e0267aad846253b9488fe89d3bfdb65a1ee256909f978278` | `assets/sample-en-anonymous.pdf` |
| `7590ea3a5b094e1f92e27ea975af262219a3bef4cd49219e48882944282588c7` | `assets/sample-hi-anonymous.pdf` |
| `ba10a0e9592ba8bfcb314323a5e0eaca89b7669ebc1a831de7d049855e56e442` | `assets/sample-hi-named-devanagari.pdf` |
| `ccd988e5817d0b15708fdb617e4893211c245c91528c245ecc905aaa2e808d56` | `assets/screens/i18n-en-1440.png` |
| `d4e952e9c05e87c50aedcd90897b0d016f11eb6068022ebca6c7e7da3fa7f179` | `assets/screens/i18n-en-280.png` |
| `db20c8fd64891c1ede3e5e0f59942544c9bfeb7290a0094452f6a5eb786d5e9a` | `assets/screens/i18n-en-375.png` |
| `34ff8686caa1aa55d712c5eb6e2b87e1cfdaab215b28b137cebcfae2c640a6fb` | `assets/screens/i18n-en-768.png` |
| `041741536c5552412abef07eb901808523c56b33495a140b7f7b0f0466a8f3f8` | `assets/screens/i18n-hi-1440.png` |
| `bf12e4e4406adaba3fb500e038f4867e35cb5cedab879dc119b2b9d33bd97c97` | `assets/screens/i18n-hi-280.png` |
| `48f35a8eb590034f970e3c093bcf59a674b8724ef214bdcc78421a01aeddda57` | `assets/screens/i18n-hi-375.png` |
| `318ccf87352d86b8f5f6fc9410941485f9f9dc6b224e63df553f998a88e1d7ac` | `assets/screens/i18n-hi-768.png` |
| `aaa9db9c1f892ef90d014aec473647a11f92170320cc96a998adc851fbe15db8` | `assets/screens/i18n-hi-form-1440.png` |
| `35bc27b3d3082c9cb677e17746d53f3a0d17738641c3129e1acee5c19e7c15ee` | `assets/screens/i18n-hi-form-280.png` |
| `fdd2d47f6132998d75a5732fa78ea9356436d3e0baa58fc8b9ac06bfbcd4787f` | `assets/screens/i18n-hi-form-375.png` |
| `1cae86ece38b489b11085cc789fa455071f8c8cdc80cc106112f52d15cfe0792` | `assets/screens/i18n-hi-form-768.png` |
| `7fa3f3a981252f0f2275d0ca45fae61e110fc3183e93d46a70dac653f9fd2ed8` | `editorial-acceptance-register.json` |
| `a579014eba39fed9ba8478fd3e46ff3301694f72c0b855f1af6958d3f04a038a` | `locations.py` |
| `b2f55fc5c1f728a0566379a91581b77366533aa0c9749518b9eaff67a7f14326` | `patches/change-a-english-page10.patch` |
| `8998a9b0e06c8b4566b6cb7a64d28e7a07467e7b16d62b636c4f3afc2368af32` | `patches/change-b-schema-wording.patch` |
| `415e271594c98388ef1435d8b9b7e7f01b39f1f7127158d8f2b3e0ee54b82f0d` | `refresh_manifest.py` |

## Developer evidence outside the repository (shared project folder `kun-i18n-003/`)

| File | Content |
|---|---|
| `evidence/00-environment.txt` | toolchain, ephemeris hashes |
| `evidence/01-unchanged-application.txt` | path and tree-object comparison base vs head |
| `evidence/02-pdf-bytes-base-vs-head.txt` | 104/104 PDFs identical |
| `evidence/03-chart-byte-identity.txt` | `/api/chart` 24/24 identical |
| `evidence/04-suites-head.txt` | engine, prototype and report suites on the head archive |
| `evidence/05-register-negative-cases.txt` | 12 invalid registers caught, valid control passes |
| `evidence/10-change-b-pdf-bytes.txt`, `11-change-a-pdf-bytes.txt` | measured PDF impact of each patch |
| `evidence/12-patch-tests/` | full suites with Change A alone, Change B alone, both |
| `evidence/20-qa-round2/` | QA round 2 (review 5734501764): asset guard failing before the fix and passing after, the QA bypass register refused, suites, unchanged-application proof on the corrected head |
| `SHA256SUMS` | hash of every evidence file |

## Unresolved approvals

Every `human_hindi_language` and `human_jyotish_terminology` layer (items 1–18, C1–C6); owner Change A
(item 13) and Change B (item 15); final customer release. Production NO-GO; PR #1 HOLD.
