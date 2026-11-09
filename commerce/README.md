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
| Order/line-item verification | `shopify._paid_lines`: `financial_status == paid`, not cancelled, no `test` orders unless staging, exact product + variant + SKU + currency, price > 0; quantity × (1 + 3) generations |
| Live order re-check (required) | `GraphQLOrderVerifier` (GraphQL Admin API, scopes `read_orders` and `read_products` (the latter for `lineItem.variant`; owner decision F5, 2026-11-09), no customer fields) before every claim and generation: order paid or partially refunded, not cancelled, the entitlement's own line still present with the same variant, quantity ≥ 1 and not refunded. Lines Shopify no longer allows are revoked locally (reconciliation). Shopify unreachable, a partial answer, a truncated one (any `hasNextPage`, or a full page of 50 refunds) or an answer served under any API version other than the configured one (`X-Shopify-API-Version`; default `2026-10`, stable releases only): 503, nothing used, nothing revoked. Both queries are checked against Shopify's published schema by `tests/test_schema_contract.py` (set `SABPUJA_TEST_SHOPIFY_SCHEMA` to `admin_2026-10.json.gz` from npm `@shopify/dev-mcp`; needs graphql-core). `require_order_verification` defaults to on and needs the app's client id and secret (tokens from the client-credentials grant, renewed in memory before expiry, `admin_auth.py`) or a static custom-app token; offline tests turn it off explicitly. `--reconcile-once` runs one pass over all active entitlements (operator-run, not a daemon) |
| Order-read horizon | Apps read only the last 60 days of orders without `read_all_orders`, so `claim_validity_days` (30) + `generation_window_days` (30) must fit `order_read_horizon_days` (60), and every entitlement hard-expires there |
| Paid orders that cannot be fulfilled | `order_exceptions` table (ids and a bounded kind only: `paid_without_email`, `sellable_line_rejected`, `malformed_paid_webhook`) plus one `PAID_ORDER_EXCEPTION` log line; `--list-exceptions` prints them. The webhook is still acknowledged, because a retry cannot fix it |
| Recovery of those orders | `--recover-order ORDER_ID` (operator-run) re-reads the order with the separate GraphQL recovery query, the only query that reads a protected customer field (the order e-mail, hashed in memory, never stored or logged), applies the same line rules, creates any missing entitlement, attaches the keyed e-mail hash only where none exists, and resolves the order's exceptions. Claim and horizon deadlines run from the order's `createdAt`, so a late recovery cannot outlive the 60-day re-check; an order past its claim window, refunded, cancelled or tombstoned is not recreated; Shopify unreachable or a partial answer changes nothing. Idempotent |
| Duplicate webhooks | Webhook-id table plus `(shop, order, line item)` uniqueness |
| One-time e-mail code | 6 digits from `secrets`, stored as HMAC, 10 min, single use, 5 wrong tries lock it, 60 s resend cooldown, 5 codes per order per day, per-client rate limit, identical response for every claim |
| Secure session | 256-bit random token, stored as HMAC, `__Host-` cookie: `Secure; HttpOnly; SameSite=Strict`, exact Origin check, JSON only |
| Private birth form | `static/`: same refusal rules as the prototype (exact time required, no guessed place/offset, repeated-hour choice) |
| In-memory PDF | `renderer.EssentialsRenderer` → `report.phase1.essentials.render_for_form` (KUN-RC-ESS-001). Fails closed with 503 if that module is absent or its `release_problems()` is non-empty (wording not yet owner-approved); it never falls back to a development edition. `allow_unreleased_edition: true` lifts the release gate for staging QA only |
| Refund / revocation | Cancel and refund revoke and drop any reservation; sessions end when nothing on the order stays active; tombstones beat a late `orders/paid`. `Response.deliver` re-checks the reservation and session immediately before the PDF is written (403 and nothing sent if revoked), and `commit_delivery` counts only a still-active, still-reserved entitlement, atomically. A refund that lands while bytes are already on the wire cannot recall them; it only prevents that delivery being counted and every later one |
| Regeneration policy | `initial_generations=1`, `additional_generations=3`, `generation_window_days=30` from the first delivered PDF; configurable; stored per entitlement at purchase |
| English-only paid output | `renderer.screen`: any `report_locale` other than `en`, or any `locale`, `names`, `panchanga_names`, `edition`, `palette`, `synthetic` key, is refused with 422 before rendering |
| No persistence of birth data or PDFs | No such column exists; tests scan the database, WAL and logs after a full flow |
| Resource limits | `deploy/compose.yml` (CPU, memory, pids, nofile, read-only root) and `deploy/gateway.nginx.conf` (per-IP rate and connection limits) |

Code e-mails go through one bounded queue and one worker thread (`mail_queue_size`); a full queue drops the message
with a bounded log line, and the buyer can ask again.

A generation counts **only after the PDF bytes were written**. Refused input, a render fault, an unavailable renderer,
a busy renderer and a failed send all give the reservation back. One generation per order runs at a time (409 for a
double click); a reservation left by a crashed process is freed after 5 minutes.

## What is stored

`entitlements` (shop, order id/number, line item, edition, HMAC of the normalised checkout e-mail, capacity, used,
status, timestamps), `revocations`, `otp_challenges` (HMAC of the code), `sessions` (HMAC of the token),
`webhook_events` (id, topic, outcome). `secure_delete` is on; `Store.purge()` removes expired sessions and codes and
old webhook ids. The pepper is a separate secret file, so a copied database or backup cannot match an e-mail or a code.
The accurate claim is **"no stored birth data or PDFs"**: entitlements and the keyed e-mail hash are still
customer-linked order data and need the same access, backup and retention handling as other order records.

## Run the tests

```bash
PYTHONPATH=src:prototype:.:commerce:commerce/tests SABPUJA_TEST_EPHE_PATH=$HOME/sabpuja-ephe \
  python -m unittest discover -s commerce/tests -v
```

Without `SABPUJA_TEST_EPHE_PATH` the engine-backed tests in `test_end_to_end.py` are skipped; the handoff evidence is
run with the pinned data and has no skips. The end-to-end tests use the production `EssentialsRenderer` with the
release gate off (`tests/helpers.essentials_renderer`); `ReleaseGate` checks that the default refuses with 503.

## Remaining external actions (each needs separate owner authorization)

1. **Essentials wording release:** the owner approves the Essentials replacement wording so that
   `essentials.release_problems()` is empty; until then paid generation returns 503 by design.
2. **Shopify (owner-authorized development store first):** create the digital product (no shipping) and a custom
   app with `read_orders` and `read_products`; it also needs protected customer data access for the order e-mail in webhook payloads
   (without it, paid orders arrive as `paid_without_email` exceptions). A fulfillment-order scope only if the flow
   later marks fulfilment. Subscribe `orders/paid`, `orders/cancelled`, `refunds/create`; put the webhook secret and
   the app client secret in files (the client id goes in `commerce.json`). Confirm on the store that both GraphQL queries (schema-validated offline) (order re-check and recovery, incl. `number`, `email`, `createdAt`, `originalUnitPriceSet`) return real data there, and run one `--recover-order` on a dev-store order. Add a "Prepare your Janam Kundali" link to the order status
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
