# Sabpuja Kundali: internal localhost prototype (Gate 3B)

**Internal, non-public prototype. Production remains NO-GO.** This is a browser
front end and a `127.0.0.1`-only HTTP wrapper around the Gate 1 engine in
`src/sabpuja_kundali`. It adds no astronomy: every position comes from
`sabpuja_kundali.engine.calculate` with the pinned Swiss Ephemeris data. It is
English only and stores nothing.

It is not the DATA-01 gazetteer, not the KUN-F11 public API, not PDF, Hindi or
Shopify work, and it does not implement P6 (D9 houses).

## What it does

- Birth form: a birthplace from a curated list, the local date, and the exact
  local time (seconds optional). If the time is unknown, the page explains why
  an exact time is needed and calculates nothing. No time is ever assumed.
- The browser sends only `place_id`, `birth_date` and `birth_time`. The server
  takes the coordinates and IANA zone from the fixture, so a client can never
  pair a place with an arbitrary zone.
- The server finds the UTC offset for that wall time in the pinned zone:
  - one offset: it is used;
  - a repeated hour (clocks set back): the user is asked which occurrence
    (HTTP 409 `TIME_AMBIGUOUS_LOCAL`), then the chosen offset is sent;
  - a skipped hour: the engine refuses it (`TIME_NONEXISTENT_LOCAL`).
  The engine then re-validates the offset itself and applies all of its own
  checks (window, historical clock Option B, D3, latitude band, Swiss data).
- Result: a North Indian D1 chart, a D1 table, a D9 sign table with the D9
  Lagna, the confirmed input, and a method and provenance panel.
- Refusals are shown with their code and a plain explanation; no chart is shown.

## Setup

Python 3.11 or newer. Install only the engine's pinned dependencies in an
isolated environment, and fetch the two pinned ephemeris files
(see `data/ephemeris/README.md`).

```bash
python3 -m venv .venv
.venv/bin/pip install pyswisseph==2.10.3.2 tzdata==2026.5

mkdir -p "$HOME/sabpuja-ephe"
for f in sepl_18.se1 semo_18.se1; do
  curl -fL -o "$HOME/sabpuja-ephe/$f" \
    "https://raw.githubusercontent.com/aloistr/swisseph/c69c14adb7a0f94829586ffd92cd422aacb21e86/ephe/$f"
done
sha256sum "$HOME/sabpuja-ephe/"*.se1
# ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66  sepl_18.se1
# 1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7  semo_18.se1
```

## Run

From the repository root:

```bash
unset SE_EPHE_PATH
SABPUJA_EPHE_PATH="$HOME/sabpuja-ephe" PYTHONPATH=src:prototype \
  .venv/bin/python -m kundali_prototype --port 8765
# Sabpuja Kundali internal prototype: http://127.0.0.1:8765/ (localhost only; Ctrl+C to stop)
```

Open <http://127.0.0.1:8765/>. The host is fixed to `127.0.0.1` and is not
configurable. Requests whose `Host` is not `127.0.0.1:<port>` or
`localhost:<port>` are refused (DNS-rebinding guard), and so are cross-origin
POSTs.

The server refuses to start (exit 2, nothing listening) unless all of these hold:
- the required `.se1` files match the pinned manifest and `SE_EPHE_PATH` is unset;
- pyswisseph is 2.10.3.2, the Swiss library is 2.10.03 and tzdata is 2026.5;
- all 598 pinned zone files verify;
- the place fixture loads, and each zone is pinned and geographic;
- one synthetic canary chart computes with schema `0.2.0` and metadata `/3`.

## Tests

```bash
export SABPUJA_TEST_EPHE_PATH="$HOME/sabpuja-ephe"
# Engine (unchanged Gate 1 suite)
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests
# Prototype server, form, timezone, integration, privacy and loopback tests
PYTHONPATH=src:prototype:prototype/tests .venv/bin/python -m unittest discover -s prototype/tests -v
# Chart model unit tests (Node 18+)
node --test prototype/tests/browser/chart_model.test.cjs
# Browser QA, desktop and mobile plus 14 widths from 280 to 1920 px, with screenshots
# (Node 18+ and Playwright with Chromium)
PROTOTYPE_PYTHON=.venv/bin/python node prototype/tests/browser/e2e.cjs --out ./prototype-shots
```

Without `SABPUJA_TEST_EPHE_PATH`, the tests that compute charts are skipped and
reported as unavailable. Browser QA exits 3 (unavailable) instead of passing.

## Privacy

- No request is logged: the handler's log methods are no-ops, and the default
  HTTP error page is replaced by a fixed JSON body that never echoes the request.
- No database, files, cookies or browser storage. Birth data lives only in the
  request and the response.
- No analytics, CDN, third-party font service or external script. The
  Content-Security-Policy allows only `'self'`. Fonts and logos are served from
  this computer. The only external URL is a plain link to https://sabpuja.com
  (header and footer), opened only when clicked, in a new tab with
  `rel="noopener noreferrer"`.
- Unexpected exceptions return `INTERNAL_ERROR` with a fixed message. They
  never return a traceback, a server path or the input.

## Design system, logo and fonts

The page follows the Sabpuja Foundations: the published Component Lab page
(`sabpuja/theme` branch `gh-pages` at `1aa273d`, `foundations/index.html`) and
the tokens and component rules in `sabpuja/design-system` at `af3825f`
(`tokens/tokens.css`, `docs/components.md`). The live Foundations URL could not
be opened from the build environment, so the published source was read from
the repository instead.

- **Colours:** Foundations palette (Saffron `#D35400`, Temple Gold `#F4B400`,
  Sacred Brown `#4E342E`, Deep Brown `#33241F`, Light Cream `#FFF8E7`, Ivory
  `#FFFBEF`) with the token neutrals and Danger `#B42318`. Buttons use Saffron
  700 `#C84700` for text contrast, as in `docs/components.md`.
- **Type:** Poppins for headings, Inter for body, labels, fields, buttons and
  interface text. Sizes, gutters and gaps use `clamp()`; grids use `auto-fit`
  and `minmax()`. Container queries are used only for three structural
  changes: the compact emblem in a very narrow header, the chart-led result
  grid on wide containers, and tighter table cells in narrow table cards.
- **Logo:** the approved 2026-10-07 rebrand masters from
  `sabpuja/design-system` `assets/logo/current/`, copied byte for byte:

  | File | SHA-256 |
  |---|---|
  | `static/brand/sabpuja-logo-horizontal-color.svg` | `2f9acce59b19cac8e1abed203686cb791b82fa97678005189416ccf7e10f7b14` |
  | `static/brand/sabpuja-emblem-color.svg` | `c52269c8b475f60c0b1a5d5342bc18380b8dffaf88f960f43e7361db6656a2b8` |

  The horizontal lockup is the header logo; the emblem replaces it only when
  the header is narrower than 18rem, and marks the footer.
- **Fonts:** Latin and Latin Extended subsets of Inter 400/500/600 and Poppins
  500/600/700 from `@fontsource/inter@5.3.0` and `@fontsource/poppins@5.3.0`
  (npm integrity `sha512-RofMylZm…A3g==` and `sha512-cms1nM7U…CceQ==`), under
  the SIL Open Font License 1.1 (`static/fonts/OFL-*.txt`). `static/fonts.css`
  declares them with `font-display: swap` and the system sans-serif fallbacks
  from the design tokens.

## Birthplace fixture

`kundali_prototype/places.json` (SHA-256
`1211b323b2018a581bf66677e377ecd1d6ad115a1d461ac9c22a984f60d4a9f6`) lists ten
Indian cities and two non-India entries that exist only to test refusal paths:
London (daylight-saving gap and repeated hour) and Tromsø (latitude outside ±66°).

- **Coordinates, names and zones:** GeoNames `cities15000` as bundled in
  the `geonamescache==2.0.0` wheel (SHA-256 pinned in the fixture; GeoNames data
  CC BY 4.0).
- **Cross-check:** each point was checked against Natural Earth 1:10m populated
  places at v5.1.2 (`f1890d9`, public domain). All 12 agree within 4.1 km.

Re-check with `python -I prototype/tools/check_places.py <wheel> <geojson>`.

This fixture is for the prototype only. It is not an approval of DATA-01 or of
its licensing.

## Architecture

```
browser (static/index.html, app.js, chart.js, app.css, fonts.css; no computation)
   | POST /api/chart {place_id, birth_date, birth_time[, utc_offset]}
   v
kundali_prototype.server (127.0.0.1 only; stdlib http.server)
   - strict form validation and fixture lookup (places.py)
   - offset candidates from the engine's pinned zone loader; no guessing
   - engine.calculate({birth_datetime with offset, timezone, latitude, longitude})
   - maps engine refusals and errors to controlled JSON
   v
sabpuja_kundali.engine (Gate 1, unchanged): pinned tzdata, D3, P5 order,
   RG-HIST Option B, latitude band, manifest-verified Swiss .se1, Lahiri,
   mean Rahu, exact opposite Ketu, whole-sign D1, D9 signs, metadata /3
```

The response is `{"input": {...confirmed input...}, "chart": <engine result, unchanged>}`.
The North Indian view places each graha in its engine-reported
`whole_sign_house`, and gives house *h* the sign `(Lagna + h − 1) mod 12`. If
any graha's engine `rashi` disagrees with that sign, the view refuses to draw.
