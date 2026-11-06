# Janam Kundali paid fulfilment (KUN-RC-COM-001)

**OFFLINE ONLY. NOT DEPLOYED. NO SHOPIFY CHANGE.** This package implements the secure purchase-to-download flow for
Issue #77 and tests it with synthetic Shopify payloads and a mock mailer. It does not install a Shopify app, touch the
live store, enable payments or open a public endpoint. Production remains **NO-GO**.

## What it does

```
Shopify checkout ──orders/paid (HMAC)──▶ /webhooks/shopify ──▶ entitlement (order ids + keyed e-mail hash)
Customer: order number + checkout e-mail ──▶ /api/claim/start ──▶ 6-digit code by e-mail (same reply for any input)
Customer: code ──▶ /api/claim/verify ──▶ __Host- HttpOnly SameSite=Strict session (30 min)
Customer: birth details ──▶ /api/generate ──▶ English Essentials PDF rendered in memory, streamed once
orders/cancelled, refunds/create ──▶ entitlement revoked, sessions ended (also if they arrive before orders/paid)
```

| Requirement (owner, 2026-11-06) | Where |
|---|---|
| Entitlement store | `store.py`: SQLite, order ids, quantities, counters, keyed hashes only |
| Signed webhook receiver | `shopify.verify`: base64 HMAC-SHA256 of the raw body, constant time, shop domain, webhook id, optional freshness |
| Order/line-item verification | `shopify._paid_lines`: `financial_status == paid`, not cancelled, no `test` orders unless staging, exact product + variant + SKU + currency, price > 0; quantity × (1 + 3) generations. Optional `AdminOrderVerifier` re-check, fail closed |
| Duplicate webhooks | Webhook-id table plus `(shop, order, line item)` uniqueness |
| One-time e-mail code | 6 digits from `secrets`, stored as HMAC, 10 min, single use, 5 wrong tries lock it, 60 s resend cooldown, 5 codes per order per day, per-client rate limit, identical response for every claim |
| Secure session | 256-bit random token, stored as HMAC, `__Host-` cookie: `Secure; HttpOnly; SameSite=Strict`, exact Origin check, JSON only |
| Private birth form | `static/`: same refusal rules as the prototype (exact time required, no guessed place/offset, repeated-hour choice) |
| In-memory PDF | `renderer.EssentialsRenderer` → `report.phase1.essentials.render_for_form` (KUN-RC-ESS-001). Fails closed with 503 if that module is absent: it never falls back to a development edition |
| Refund / revocation | Cancel and refund revoke and end sessions; a refund during rendering blocks the delivery; tombstones beat a late `orders/paid` |
| Regeneration policy | `initial_generations=1`, `additional_generations=3`, `generation_window_days=30` from the first delivered PDF; configurable; stored per entitlement at purchase |
| English-only paid output | `renderer.screen`: any `report_locale` other than `en`, or any `locale`, `names`, `panchanga_names`, `edition`, `palette`, `synthetic` key, is refused with 422 before rendering |
| No persistence of birth data or PDFs | No such column exists; tests scan the database, WAL and logs after a full flow |
| Resource limits | `deploy/compose.yml` (CPU, memory, pids, nofile, read-only root) and `deploy/gateway.nginx.conf` (per-IP rate and connection limits) |

A generation counts **only after the PDF bytes were written**. Refused input, a render fault, an unavailable renderer,
a busy renderer and a failed send all give the reservation back. One generation per order runs at a time (409 for a
double click); a reservation left by a crashed process is freed after 5 minutes.

## What is stored

`entitlements` (shop, order id/number, line item, edition, HMAC of the normalised checkout e-mail, capacity, used,
status, timestamps), `revocations`, `otp_challenges` (HMAC of the code), `sessions` (HMAC of the token),
`webhook_events` (id, topic, outcome). `secure_delete` is on; `Store.purge()` removes expired sessions and codes and
old webhook ids. The pepper is a separate secret file, so a copied database or backup cannot match an e-mail or a code.

## Run the tests

```bash
PYTHONPATH=src:prototype:.:commerce:commerce/tests SABPUJA_TEST_EPHE_PATH=$HOME/sabpuja-ephe \
  python -m unittest discover -s commerce/tests -v
```

Without `SABPUJA_TEST_EPHE_PATH` the engine-backed tests in `test_end_to_end.py` are skipped; the handoff evidence is
run with the pinned data and has no skips. `tests/helpers.PipelineRenderer` is a **QA-only** stand-in for the
Essentials entry point that runs the real chart, Panchanga M1, Vara and 14-page English renderer; production code
never calls it.

## Remaining external actions (each needs separate owner authorization)

1. **Essentials entry point:** rebase onto KUN-RC-ESS-001 once it has a SHA, and switch the end-to-end tests from the
   QA stand-in to `EssentialsRenderer`.
2. **Shopify (dev or unpublished staging store):** create the digital product (no shipping) and a custom app with
   `read_orders` (plus `write_fulfillments` if fulfilment is marked); subscribe `orders/paid`, `orders/cancelled`,
   `refunds/create`; put the webhook secret in a file. Add a "Prepare your Janam Kundali" link to the order status
   page and the confirmation e-mail pointing at the claim page. No birth data goes to Shopify.
3. **Transactional e-mail:** choose an SMTP provider, configure SPF/DKIM for the sender, supply `smtp.json`.
   `SmtpMailer` (STARTTLS, verified certificate) is not exercised by these tests.
4. **Hosting:** subdomain, TLS, Caddy route to the gateway, state directory with backups (contains no birth data).
5. **Copy:** the claim page, e-mail and error texts are English drafts for ChatGPT English-content QA. Hindi stays off.
6. **Commercial:** price, refund policy and support copy (owner).

## Rollback

Unpublish the Shopify product (stops new sales), remove the webhook subscription, stop the `commerce` container.
While it is stopped nothing is consumed; paid-but-unfulfilled orders are refunded or fulfilled after restart. The
database contains no birth data to purge. The engine, report and preview are not modified by this package, so no
other service needs rolling back.
