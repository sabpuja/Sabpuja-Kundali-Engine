# KUN-I18N-003 evidence manifest

| | |
|---|---|
| Base (PR #60 head, re-fetched: no drift) | `c9f147bad9b50c5eb85585b0e3e952e49fb5ac40`, tree `85e38f1dbafc0eef4dc24f87c5910b118261fb73` |
| Reviewed source (catalogs and samples) | `c9f147b` (the packet adds no catalog change) |
| Packet commits | see the PR; the first is `3459c63639502d93284c541bd8d673f87f2542a8` |

## Application unchanged (Task 4)

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
owner-copy patches are files under `patches/` and are **not applied**.

## Files in this package (SHA-256)

| SHA-256 | File |
|---|---|
| `a8fb9ad42586c5773d3ca46a2273574a0522f87c1eec867646ef1ab504c243b8` | `CHANGE-A-ENGLISH-PAGE10.md` |
| `1f0379ce389b96897876bf0bc8663ef54f8f730cf395d085fe5b9d40d064c433` | `CHANGE-B-SCHEMA-WORDING.md` |
| `412356996918908afa18af0aab5405d9d973a5310474cf797b02a57910ca1227` | `DECISION-SHEET.csv` |
| `ac0acd932a73427e412952cd94dd8d44736979bfb1748d1df036cf5f8b0f42ea` | `DECISION-SHEET.md` |
| `d6d66f432b65fc15f1f5dd3b1989f7fb1f61e135df6142538a4acf0e3f5ecb99` | `EDITORIAL-ACCEPTANCE-REGISTER.md` |
| `8db067ac9e4734625647a615735f6ae947100bec7ef87b8c17d26e9cba58ddba` | `LOCATIONS.md` |
| `a19ec7a367c5c0eacbd398e1c9d264df1a1aacf0086438fc09a2a5031d307839` | `README.md` |
| `c31b604616ec5008a170749204147f989d2d7045abb6fe749639dccc7901226d` | `REVIEW-PACKET.md` |
| `732231a491cd70c4f9719001fef0bde1d63e39602f4e112eeef248a9ad32a66d` | `assets/en-hi-page-01.png` |
| `912c7b85e9241a9061f53ffc0ec714b4c217630faceff44288f79e944e5166d4` | `assets/en-hi-page-02.png` |
| `b5d5574356f9b202aac3f4c099a9404527af08a8bc3312628e07e8ce9625ecae` | `assets/en-hi-page-03.png` |
| `2fb3f8a8828597f652f0b664d379306459072aef52ba0699e24275fb5b6ec8f3` | `assets/en-hi-page-04.png` |
| `e924b186b3a41b9bcedd5b3ba239b75396f214544f8a1a2d425981a75f8e839e` | `assets/en-hi-page-05.png` |
| `5975f5fda4cfd680c9c573ece30835dedd6d0edca1a9e2152f475f6c5afe99ab` | `assets/en-hi-page-06.png` |
| `59782a41224f515b8bb9e39c8a58c833ae89f51cd539d174815599d076114322` | `assets/en-hi-page-07.png` |
| `d3fb7e2986921dabfdb279e5e1bdd6f6a4e0ae466e858d99a7c5f7b4b727921f` | `assets/en-hi-page-08.png` |
| `ed142a86b6a4560138dcb63c21e6c82eb9019a57cbafd69d9a628ad0933627d0` | `assets/en-hi-page-09.png` |
| `6fd9b048a3d100989cd947c1f16a82feeeda4b3f1b6f5cb6f73acd1a756a1f4d` | `assets/en-hi-page-10.png` |
| `e3035590f3e2d69d9347528ed4e89880c0557b9e9d6c590b9792857486cbfdc7` | `assets/hi-before-after-page-03-zoom.png` |
| `c361ecda56d916ff84578d310a08b9ce6c202ba95dcaeac828760d6fae841205` | `assets/hi-before-after-page-06-zoom.png` |
| `369b09bee4e8029985b1c40cdf2d053be5ab60d3d3c61ac006cbedc131af6f64` | `assets/hi-before-after-page-07-zoom.png` |
| `37b77f9a4013d5fb6ccfa379ac71c2bcd186f28428f1b010ff52ee63426010ea` | `assets/sample-en-anonymous.pdf` |
| `7590ea3a5b094e1f92e27ea975af262219a3bef4cd49219e48882944282588c7` | `assets/sample-hi-anonymous.pdf` |
| `ba10a0e9592ba8bfcb314323a5e0eaca89b7669ebc1a831de7d049855e56e442` | `assets/sample-hi-named-devanagari.pdf` |
| `8a3cebd57fb6496781198ba17646c7688492e1154049402bef3f63eb1ce9c573` | `assets/screens/i18n-en-1440.png` |
| `32c734e949fc20251d58b60a4ac2eb4a759a0c93f4ecc6cb74c798738ad97873` | `assets/screens/i18n-en-280.png` |
| `a3d6fc837e4612369ac29fbbdaf05b790ee95355e259915d0250bbebf4e8ac40` | `assets/screens/i18n-en-375.png` |
| `53d59c494c7d3c30eb063705b29844159a284883341d6095aa75368080ceba4f` | `assets/screens/i18n-en-768.png` |
| `850aaef924f9c9fe16ab3331639a140ac6651d609858667df9dba52092841298` | `assets/screens/i18n-hi-1440.png` |
| `15d78a4e1f7ce1ba3b511f655833a992f34e24fb3e6ffb564f6548fc7c10b400` | `assets/screens/i18n-hi-280.png` |
| `23daacd291fedfdf838f595fa6a501ff062d8c95c2d81fc2fe3a1d190d074e04` | `assets/screens/i18n-hi-375.png` |
| `7f59690c85c53609823cbc5e658a664288767f43ecd97e99993748c23b0ee877` | `assets/screens/i18n-hi-768.png` |
| `aaa9db9c1f892ef90d014aec473647a11f92170320cc96a998adc851fbe15db8` | `assets/screens/i18n-hi-form-1440.png` |
| `35bc27b3d3082c9cb677e17746d53f3a0d17738641c3129e1acee5c19e7c15ee` | `assets/screens/i18n-hi-form-280.png` |
| `fdd2d47f6132998d75a5732fa78ea9356436d3e0baa58fc8b9ac06bfbcd4787f` | `assets/screens/i18n-hi-form-375.png` |
| `1cae86ece38b489b11085cc789fa455071f8c8cdc80cc106112f52d15cfe0792` | `assets/screens/i18n-hi-form-768.png` |
| `f292c93d9495499c8e922eee681f372cb9bc8e763e642362a8c9dfe8e5cbc2d1` | `editorial-acceptance-register.json` |
| `384b9a863e4b531418e38d858eaf735b94ce1e5da032342306e30d582f416e4d` | `locations.py` |
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
