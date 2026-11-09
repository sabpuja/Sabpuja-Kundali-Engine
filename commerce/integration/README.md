# Shopify QA-store integration readiness (KUN-RC-COM-001B)

**TEMPLATES AND RUNBOOK ONLY.** Nothing in this folder has been applied. No app was created or installed,
no webhook subscribed, no notification edited, no server or DNS changed, no payment enabled. Every step under
"Owner-authorized steps" needs the owner's explicit go-ahead in chat. The frozen commerce candidate is
`6dc35b244bbd76754fe528937d4119721cfc5348` (PR #85); this folder adds no runtime code.

| File | Purpose |
|---|---|
| `shopify.app.toml.example` | App configuration: `read_orders` only, webhook API version `2026-10`, the three subscriptions with trimmed payloads |
| `commerce.qa-store.example.json` | Commerce settings for the QA store (live re-check on, test orders allowed, wording switch OFF) |
| `smtp.example.json` | Transactional SMTP for claim codes |
| `Caddyfile.staging.example` | Isolated HTTPS staging host: webhook open to Shopify, everything else limited to the QA team |
| `order-confirmation-snippet.liquid` | Claim link for the order confirmation e-mail (no personal data in the URL) |
| `validate_graphql.py` | Offline validation of both GraphQL operations and the three topics against Shopify's published schema |
| `../tests/test_integration_templates.py` | Keeps these templates consistent with the frozen code |

## 1. Admin API: version, scopes and operations

* **Version `2026-10`.** Shopify's published supported-version list (`supported-versions-schema.json` in
  `@shopify/dev-mcp` 1.18.0) names `2026-10` as latest stable for the Admin API and no longer lists
  `2025-10`. The frozen code's *default* `admin_api_version` is still `"2025-10"`
  (`sabpuja_commerce/config.py`). The QA config sets `"admin_api_version": "2026-10"` explicitly, so no code change
  is needed for the trial. Changing the default is a one-line fix left for QA to decide.
* **Scopes: `read_orders` only.** The re-check, reconciliation and recovery all read one order by id.
  There is no write scope, no `read_customers`, and no `read_all_orders`, because every entitlement hard-expires
  inside the 60-day default order window. The schema text for `Order` confirms "Only the last 60 days' worth of
  orders ... are accessible ... by default".
* **Operations.** `ORDER_QUERY` (re-check: no customer fields) and `RECOVERY_QUERY` (adds `name`, `email`,
  `createdAt`, prices) validate against the `2026-10` schema and against the `2027-01` release candidate, with
  no deprecated field. `PARTIALLY_REFUNDED` and `PAID` are real `OrderDisplayFinancialStatus` values.
  Evidence: `graphql-validate-admin-2026-10.txt`. Reproduce:

  ```sh
  npm pack @shopify/dev-mcp@1.18.0            # tarball sha256 a4c813bf...c05f7
  tar xzf shopify-dev-mcp-1.18.0.tgz package/dist/data/admin_2026-10.json.gz
  python -m venv gq && gq/bin/pip install graphql-core==3.2.6
  gq/bin/python commerce/integration/validate_graphql.py package/dist/data/admin_2026-10.json.gz
  ```
  This is schema validation, not a live call. Field *values* (for example `email` being null without protected
  data access) are only proven on the dev store.

## 2. Protected customer data (checkout e-mail)

The app needs the order e-mail in two places: the `orders/paid` webhook payload (`email` / `contact_email`) and the
recovery query's `Order.email`. Shopify treats e-mail as protected customer data. In the app's Dev Dashboard
entry, under API access → Protected customer data:

1. Request **level 1 protected customer data** with the purpose "order fulfilment of a purchased digital
   product" (the app processes data only to deliver what the buyer bought).
2. Under level 2 fields select **Email only**. Do not select Name, Phone or Address.
3. Data-protection answers to give, all true for this code: data is used only for fulfilment, minimised
   (keyed HMAC of the e-mail stored, never the address), encrypted in transit, not shared, retained only for
   the entitlement lifetime (≤ 60 days, then purgeable), no birth data or PDF stored.

Without this access the webhook arrives with no e-mail and the code records a `paid_without_email` exception;
`--recover-order` then returns `unavailable` or `still_without_email`. This is the expected fail-closed result
and the first thing to check on the dev store. Whether Shopify requires a review for a single-store app is
decided in the Dev Dashboard at that time; I could not confirm it offline.

## 3. Webhooks

Subscriptions live in `shopify.app.toml.example` (app-managed, API version `2026-10`), all pointing to
`https://<commerce-staging-host>/webhooks/shopify`:

| Topic | `include_fields` | Receiver action |
|---|---|---|
| `orders/paid` | `id, order_number, email, contact_email, financial_status, cancelled_at, test, currency, line_items` | Create entitlements for sellable lines |
| `orders/cancelled` | `id` | Revoke the order, end sessions |
| `refunds/create` | `id, order_id, refund_line_items` | Revoke refunded lines (money-only refund revokes the order) |

Trimming the payloads means addresses, phone numbers and names never reach the host. The test
`test_include_fields_cover_what_the_receiver_reads` keeps the list in step with the code. **Verify on the dev
store** that `include_fields` keeps nested `line_items` objects whole. If any field is missing, the receiver
records `malformed_paid_webhook` and the order is recoverable with `--recover-order`; remove `include_fields`
for that topic if so. Shopify signs app webhooks with the app's **client secret**: that value goes into
`webhook-secret` (base64 HMAC-SHA256 is what `shopify.verify` checks).

## 4. Admin API token

The code reads a long-lived Admin API access token from `shopify-admin-token`. How it is obtained depends on
what the QA store offers when the app is created:

* An app created in the store admin ("Develop apps") shows a static `shpat_` token once: write it straight into
  the secret file.
* An app created in the Dev Dashboard and installed on the store yields an **offline** token through the
  install flow. The commerce service has no OAuth endpoint, so the operator performs the one-time exchange
  (Shopify CLI or a short manual token exchange) and writes the result to the file. If the store enables
  expiring offline tokens, a refresh step is needed that this code does not have. **This is the one genuinely
  open integration requirement**; confirm the token type on the dev store before relying on it.

## 5. Claim link

`order-confirmation-snippet.liquid` adds a short paragraph to the order confirmation e-mail, only when the
order contains the Essentials SKU. The link is the bare claim page: no order number, e-mail or birth data in
the URL. The buyer types the order number and the checkout e-mail. For the order status page, add the same
text through the store's order-status "additional content" setting if the plan still has one. Otherwise a
checkout UI extension (`customer-account.order-status.block.render`) is the supported route, but that is a
separate app extension and is not prepared here. The copy is an English draft for ChatGPT English-content QA.

## 6. Transactional e-mail (claim codes)

* A transactional SMTP provider on a subdomain the owner controls, for example `mail.<domain>`. One-time codes
  only: no marketing, no tracking pixels, no link tracking (provider setting), no attachments.
* DNS for the sender domain: SPF `include:` for the provider, DKIM keys from the provider, and DMARC at least
  `p=none` with a reporting address during QA, moving to `quarantine` later.
* `smtp.json` from `smtp.example.json`; password in `smtp-password` (0400). `SmtpMailer` requires STARTTLS
  with certificate verification.
* Dev-store checks: a code arrives at the checkout address; a wrong SMTP password gives the same 202 to the
  buyer and a bounded `MAIL_FAILED` log line, no address in the log.

## 7. Isolated HTTPS staging

* A **separate subdomain** (for example `kundali-qa.<domain>`) that is not linked from the storefront, with its
  own Caddy site block (`Caddyfile.staging.example`). It must be reachable by Shopify for webhooks. Every
  other path is restricted to QA team IPs during the trial.
* `commerce/deploy/compose.yml` unchanged: 512 MiB / 0.75 CPU / 64 pids for the app, read-only root, no
  published ports. Caddy joins the `sabpuja-commerce-qa` network.
* Secrets directory (`SBK_SECRETS_DIR`, mounted read-only at `/run/sabpuja`), every file mode 0400, owner uid
  10002, outside Git and outside backups of the web root:

  ```
  commerce.json  smtp.json  webhook-secret  pepper  shopify-admin-token  smtp-password
  ```
  `pepper`: `head -c 32 /dev/urandom > pepper` once. Losing it makes existing e-mail hashes unmatchable, and
  changing it ends every claim in progress.
* State directory (`SBK_STATE_DIR`): the entitlement SQLite only. It has no birth data, but it is still order
  data, so back it up with the same access rules as other order records.
* Ephemeris: the pinned files (`semo_18.se1` `1ca07bd6…`, `sepl_18.se1` `ca1393ce…`) at `SBK_EPHE_DIR`.

## Owner-authorized steps (none done)

1. Create the app on the QA store and grant `read_orders` plus protected e-mail access.
2. Choose the staging subdomain; DNS; Caddy site; start the compose stack.
3. Fill in the secret files; link and deploy the app configuration (webhooks).
4. SMTP provider account and DNS records.
5. Create the digital Essentials product (no shipping) on the QA store; put its ids in `commerce.json`.
6. Add the confirmation-e-mail snippet.
7. Test orders with Shopify's test payment gateway: purchase → code → PDF; refund before and during download;
   cancel; webhook without e-mail → `--recover-order`; `--reconcile-once`.
8. Keep `allow_unreleased_edition` false until the owner approves the paid wording in chat. Until then paid
   generation answers 503 by design, so step 7's PDF leg waits for that approval.

## Rollback

Uninstall the app from the QA store (removes its webhooks and token), stop the compose stack, remove the Caddy
site block and the DNS record, revert the notification template. The state directory holds no birth data;
delete it with the secrets directory to end the trial.
