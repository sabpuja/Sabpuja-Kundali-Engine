# KUN-FREEMIUM-PREVIEW-001: free Kundali preview and paid conversion funnel (DRAFT, QA ONLY)

Issue #91. Stacked on draft PR #90 (`kun-com-ux-claim-001`). **Not deployed. No merge, no production, no real
payment, no marketing send.** Every switch below defaults to off. The frozen QA staging container of PR #88 is not
touched by this change.

```
/kundali  birth place + date + exact time (+ optional name, kept in the browser)
   └─ POST /api/preview ──▶ same validation and engine call as the paid route ──▶ 2 whitelisted fields, nothing stored
        └─ comparison: free preview vs 14-page English PDF, price (placeholder), "Buy Full Kundali Report"
             └─ hand-off panel ("you will enter your birth details again after payment")
                  └─ Shopify cart permalink  https://<shop>/cart/<variant>:1  (no birth data, no identifier)
                       └─ existing orders/paid webhook ─▶ entitlement ─▶ claim page ─▶ OTP ─▶ re-entered details ─▶ PDF
        └─ optional, unchecked e-mail opt-in ─▶ separate QA store, double opt-in, withdraw/delete at /marketing
```

## 1. Preview fields (scientific status)

| Field | Shown | Basis | Independent check in this PR |
|---|---|---|---|
| Lagna Rashi | **Yes** | SCI-01e sidereal Lagna (`houses_ex(..., b"W", FLG_SIDEREAL)` `ascmc[0]`), SCI-02 baseline; owner approved / canonical 2026-10-24 (ledger rows 4, 9) | `test_preview.VerifiedFields`: 30 synthetic births over all 10 cities equal both the engine and a separate direct pyswisseph computation |
| Moon Rashi | **Yes** | SCI-02 baseline field (ledger row 9), canonical 2026-10-24 | same 30-case matrix |
| Vara | **No (withheld)** | PAN-D03/PAN-D05 sunrise Vara is recorded "for the development stage only, not for customer release" (`src/sabpuja_kundali/panchanga/vara.py`) | Registry marks it `withheld`; config and service refuse to enable it (tests) |

The response is exactly `{preview_version, fields: {lagna_rashi, moon_rashi: {rashi, number}}, method}`; the page
labels it "Sidereal Rashi N of 12" and shows no Western sign name (001A): no degree, house, Navamsa, Nakshatra, planet, Panchanga, coordinate or PDF
(tests scan for 24 leak words and any fractional number).

**Birth-time check (SCI-06 Option 1): WITHHELD by default (001A).** SCI-06 adoption and wording are pending and the
paid PDF has no such disclosure, so `preview_birth_time_check` defaults to false: nothing is computed, returned or
shown. For QA research only, setting it true recomputes the instant 120 s earlier and later and returns
`birth_time_check` = `sign_change_within_2_min` (a different sign was actually calculated), `not_assessable` (a
neighbour could not be computed, e.g. 1970-01-01 00:00:30) or `no_change`; the page has two separate draft notes for
the first two cases. The shown values are always those of the entered time.

Not claimed: independent golden-chart accuracy. Engine `validation_status` stays `UNVERIFIED_GOLDEN_CHARTS`; page
wording says "calculated with Swiss Ephemeris", per REL-01.

## 2. Input rules (unchanged engine policy, plus one preview rule)

Same `kundali_prototype.server.compute` path as `/api/generate`: 10 India reference places only (London and Tromsø
fixtures excluded), no nearby-city substitution, exact time required, no guessed offset, historical-clock refusal
before 1970-01-01 (`HISTORICAL_CLOCK_UNVERIFIED`), engine range checks. The preview adds `BIRTH_DATE_FUTURE` (after
today in IST). The server accepts only `place_id`, `birth_date`, `birth_time` (and the engine's `utc_offset` for a
repeated hour, which never occurs at these places since 1970). A name, e-mail, locale, edition or any other key is
refused with 400. Body ≤ 512 bytes, strings ≤ 64 chars, duplicate keys refused.

## 3. Abuse and resource limits

| Layer | Limit |
|---|---|
| Gateway (nginx) | `/api/preview` 6 r/min per IP (burst 3), `/api/funnel` 20 r/min, `/api/leads/*` 6 r/min, 1 KB bodies |
| App, per client | 6 previews/min and 40/hour (`preview_rate_per_minute`, `preview_rate_per_hour`); 20 beacons/min |
| App, global | 120 previews/min (`preview_global_per_minute`) |
| App, concurrency | 2 previews at once (`max_concurrent_previews`), separate from the paid render slot, non-blocking 429 |
| Cost | ~4 ms per engine call, 3 calls per preview (entered time ± 2 min) |

Server faults return a fixed 503 and log only the exception type (tested with an exception whose text contains the
birth data).

## 4. Paid hand-off

* The button opens a hand-off panel that says, before checkout, that birth details must be entered again after
  payment and are not sent to Shopify. "Continue to secure checkout" goes to `buy_url`.
* `buy_url` defaults to the cart permalink of the configured product variant on `shop_domain`
  (QA: `https://sabpuja-qa.myshopify.com/cart/44918795665467:1`). `preview_buy_url` may override it only with a cart
  permalink or `/products/<handle>` on the same shop; query strings, fragments and other hosts are refused at start-up,
  so no attribute, note or birth detail can be appended.
* Authentication, OTP, live order re-check, revocation, quota and the renderer are unchanged; the preview has no
  route to any of them (no cookie, no session, no store access; tests).
* **Price:** `preview_price_display` is empty, so the page shows "Price: to be confirmed". The QA product's ₹1.00 is
  a test price and is never shown as the selling price. Since 001A the service **refuses to start** with the preview on
  and no price unless `allow_test_orders` is true (QA store only), and the page shows a "QA test store" banner there.
  Before live publication the configured price must equal the Shopify product price (manual owner check).
* **Comparison (001A):** a short list of what the report adds and the Buy button come first; the full table is under
  "See everything in the 14-page report" (`<details>`). The Sunrise/Vara page is **not advertised** (see section 8).

## 5. Optional marketing opt-in (isolated QA store)

* Shown only after a preview, never required, checkbox unchecked, plus a separate "I am 18 or older" box.
* Separate SQLite file (`leads_db_path`, refused if equal to the entitlement database). Columns: e-mail, keyed hash,
  status (pending / subscribed / withdrawn), purpose, consent wording version, source, locale, adult flag, timestamps,
  hashed token and mail counters. No name, birth detail, chart value, order, IP or device identifier (schema test).
* Double opt-in: one confirmation e-mail; nothing is "mailable" until confirmed. **Opening the confirmation link only
  shows "waiting for confirmation"; the visitor must press "Confirm my sign-up"** (001A, so a link scanner that runs
  scripts cannot subscribe anyone; confirm is a same-origin POST with the Origin check). Unconfirmed sign-ups are deleted after
  7 days. Withdraw keeps a minimal "withdrawn" record; delete removes the row. A new manage link can be requested by
  address (neutral reply). 10-minute resend cooldown, 3 mails per address per day. Tokens travel in the URL fragment.
* In QA the confirmation mail goes to the private Mailpit sink. **No marketing message is sent by this code**, and
  nothing syncs to Shopify customers. Shopify's own marketing-consent fields must be aligned before any real send.

## 6. Measurement (aggregate only)

`funnel_daily(day, event, count)`. **Directional counts only, never a measured preview-to-sale conversion rate.**
Events: `preview_initiated`, `preview_generated`, `preview_refused` (server side); `full_report_selected` and
`checkout_link_clicked` (browser beacons carrying only the event name: client-asserted, rate-limited, not
authenticated; `checkout_link_clicked` is a click toward Shopify, not a verified checkout start);
`paid_orders_all_sources` (existing webhook: **all** paid orders, whatever brought the buyer, not attributable to the
preview). Renamed in 001A from `checkout_started` / `paid_order_completed` so the names cannot overstate them.
No cookie, pixel, fingerprint, IP, user agent or time finer than one UTC day. `--funnel-report` prints the rows.

## 7. Copy review (DRAFT: needs English editorial QA, Hindi human review and owner sign-off)

| Item | Draft English | Hindi status |
|---|---|---|
| H1 / lede | "See your free Kundali preview" / "two facts calculated from your birth chart: your Lagna (rising sign) and your Moon sign (Chandra Rashi)…" | Not translated; page is English |
| Eligibility | 10 cities, "from 1 January 1970 up to today", "We never guess a time", English only | One Hindi line (`lang="hi"`): "यह निःशुल्क झलक और पूरी रिपोर्ट अभी केवल अंग्रेज़ी में उपलब्ध हैं।" needs human review |
| Result labels | "Lagna (rising sign)", "Moon sign (Chandra Rashi)", "Sidereal Rashi 6 of 12" (engine spelling, e.g. "Vrischika"; no Western names since 001A) | n/a |
| Birth-time notes (off by default) | "…is different when calculated for 2 minutes earlier or later…" / "We could not check whether these signs change within 2 minutes…" | SCI-06 wording is explicitly **not approved**; not shown |
| QA banner | "QA test store. Use synthetic birth details only. The full report's content is not yet approved for customers…" | QA only |
| Comparison table | Rows derived from the 14 Essentials page titles/descriptions | n/a |
| Hand-off | "After payment you will enter your birth details again…" | n/a |
| Opt-in | "Yes, send me occasional offers and news from Sabpuja by e-mail. I can unsubscribe at any time." Consent version `sabpuja-offers-email-en/0.1-draft` | Legal/privacy review needed (DPDP Act notice, purpose, retention) |

## 8. Flags for independent review before publication

1. Customer copy above (English editorial, Hindi, legal/privacy for the opt-in).
2. Owner selling price (placeholder now).
3. SCI-06: withheld in the preview (001A); adoption, wording and a matching paid-PDF disclosure remain open.
4. **Paid Sunrise/Vara page (owner decision).** `vara.py` marks the convention development-only, yet page 12 of the
   14-page Essentials PDF shows it. This PR does not change the PDF (no silent page changes). Paid public release is
   already blocked by the Essentials release gate (`release_problems()` non-empty) and the preview no longer advertises
   Sunrise/Vara. Smallest safe resolutions, for the owner: **(A)** ChatGPT/PM scientific review of PAN-D03/PAN-D05 for
   customer release, then keep 14 pages (recommended: no layout change, reviews an already QA-accepted module);
   **(B)** drop the Sunrise/Vara page from Essentials (13 pages: product text, manifest and tests change);
   **(C)** keep the page with an explicit "not verified" label (not recommended for a paid product).
5. Western sign names removed (001A).
6. Funnel counts are directional (001A renames and documentation).
7. Real Safari/WebKit, Android Chrome and the QA-store links are still untested (Chromium emulation only).

## 9. QA workflow on the QA store (after the PR #88 token proof; owner go-ahead needed)

1. Deploy this branch to the QA container with `preview_enabled: true`, `funnel_db_path` set, lead capture optional
   with Mailpit, `preview_price_display` empty. Use only synthetic births.
2. Open `/kundali` on a phone: check limits text, try London-type / pre-1970 / future / no-time refusals.
3. Get a preview, press Buy, read the hand-off, continue to the QA cart permalink, pay with the test gateway.
4. From the Thank you page or e-mail, claim with OTP, re-enter the same synthetic details, download the 14-page PDF.
5. `--funnel-report` should show one of each step (directional); `--leads-summary` counts only.
6. Opt-in: subscribe, open the Mailpit link (must stay pending), press Confirm, withdraw, delete; confirm `leads-qa.sqlite` has no birth data.

## 10. Rollout and rollback

Rollout is config-only after deploy: `preview_enabled` (page, API, beacons), then `lead_capture_enabled`.
Rollback: set both to `false` and restart (all preview, beacon and lead routes return 404; paid flow unaffected), or
revert this PR's commits. Delete `leads-qa.sqlite` and `funnel.sqlite` to remove all QA data. No migration of the
entitlement database.
