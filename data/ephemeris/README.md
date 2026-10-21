# Local Swiss Ephemeris data

The calculation engine expects local Swiss Ephemeris `.se1` files in an **absolute** directory provided through `SABPUJA_EPHE_PATH`.

Authoritative source: https://github.com/aloistr/swisseph/tree/master/ephe

Before installing data on the Hostinger VPS:
1. Select the exact upstream source revision and record it in a reviewed deployment record.
2. Select files required for validated date ranges; confirm integrity (SHA-256) and licensing for each.
3. Store dataset files on the protected local runtime volume, not in GitHub.
4. Run verified golden-chart tests with the exact same data on development and staging.
5. Record Swiss code/binding/ephemeris data version in deployment logs **without logging birth data**.

Do not enable public requests if data is missing. The code rejects fallback to Moshier for planets.
