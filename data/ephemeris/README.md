# Local Swiss Ephemeris data

The calculation engine reads local Swiss Ephemeris `.se1` files from an **absolute** directory provided through `SABPUJA_EPHE_PATH`. Binary ephemeris files are **not** committed to this repository; their redistribution rights are reviewed separately before any public service.

## Required files (pinned manifest)
The authoritative list is `src/sabpuja_kundali/ephemeris-manifest.json`. Before every calculation the engine checks that each **required** file is present, readable, the pinned size and the pinned SHA-256. Any failure stops the calculation with a structured error (CLI exit code 2) before Swiss Ephemeris is called. Optional or unrelated `.se1` files never satisfy the check.

Source: https://github.com/aloistr/swisseph at commit `c69c14adb7a0f94829586ffd92cd422aacb21e86`.

| File | Required | Used for | Bytes | SHA-256 |
|---|---|---|---|---|
| `ephe/sepl_18.se1` | yes | Sun and planets | 484061 | `ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66` |
| `ephe/semo_18.se1` | yes | Moon | 1304771 | `1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7` |
| `ephe/seas_18.se1` | no | asteroids (not used) | 223004 | `a2cd8fc33807c78ca9a700c91c2e042258b12fc4796519e00781440b5ad8b2e2` |

The `_18` files cover years 1800 to 2399. The validated product range is a separate owner decision (SCI-03).

## Installing the files
```bash
git clone --filter=blob:none --no-checkout https://github.com/aloistr/swisseph swisseph-src
cd swisseph-src && git checkout c69c14adb7a0f94829586ffd92cd422aacb21e86 -- ephe/sepl_18.se1 ephe/semo_18.se1
git hash-object ephe/sepl_18.se1 ephe/semo_18.se1   # must equal git_blob_sha1 in the manifest
sha256sum ephe/sepl_18.se1 ephe/semo_18.se1         # must equal sha256 in the manifest
mkdir -p /srv/sabpuja/ephe && cp ephe/sepl_18.se1 ephe/semo_18.se1 /srv/sabpuja/ephe/
export SABPUJA_EPHE_PATH=/srv/sabpuja/ephe
```

Rules:
1. Store dataset files on the protected local runtime volume, not in GitHub.
2. Do not set `SE_EPHE_PATH`: Swiss Ephemeris would read it in preference to the verified directory, so the engine refuses to run while it is set.
3. Changing the source commit or file set requires a reviewed manifest update with new checksums.
4. Run the real-data tests with the same files. Without `SABPUJA_TEST_EPHE_PATH` the 8 real-data tests skip; once it is set, missing or mismatched required files make the run fail instead of skipping. Release verification must show 0 skipped tests:
   ```bash
   SABPUJA_TEST_EPHE_PATH=/srv/sabpuja/ephe python -m unittest discover -s tests -v 2>&1 | tee test-run.log
   tail -n 1 test-run.log | grep -qx 'OK' && ! grep -q 'skipped' test-run.log && echo "RELEASE TESTS: PASS (0 skipped)"
   ```
5. Record Swiss code/binding/ephemeris data version in deployment logs **without logging birth data**.

Do not enable public requests if data is missing. The code also still rejects any Moshier fallback reported by Swiss Ephemeris.
