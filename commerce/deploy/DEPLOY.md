# Commerce deployment, restart and rollback (KUN-COM-PROD-HARDEN-001)

Applies to the isolated QA staging today. A production host follows the same steps only after the owner
authorizes that environment. Secrets are files outside Git, mode 0400, owned by uid 10002. Nothing below
reboots the host.

## Topology (F6)

| Network | Kind | Members | Purpose |
|---|---|---|---|
| edge (`SBK_NETWORK`, external) | bridge | HTTPS proxy, gateway (alias `commerce`) | the proxy keeps dialling `commerce:8081`, no proxy change |
| `<project>-backend` | internal, `10.231.47.0/29` | gateway `.3`, commerce `.2` | the only path to the app |
| `<project>-egress` | bridge | commerce | Shopify Admin API, SMTP relay |
| mail (QA overlay only, external, internal) | internal | commerce, Mailpit | one-time codes in QA |

Before this change the gateway shared commerce's network namespace (`network_mode: service:commerce`).
Recreating commerce alone left the gateway attached to a namespace that no longer existed, and the proxy got 502.
Now each container has its own network stack and fixed backend addresses, so either one can be recreated alone.
Commerce listens only on its backend address and is not on the edge network, so the proxy has no path that
bypasses the gateway. When commerce is down the gateway answers 502 within 3 seconds. Nothing else answers.

## Restart and recovery (F7)

* Both services use `restart: unless-stopped`. Docker is `enabled` in systemd, so after a host reboot the
  daemon starts them again. A container an operator stopped stays stopped.
* Health checks: commerce `GET /healthz` on its backend address. The gateway runs the same request through
  itself, so an unhealthy gateway means either nginx or the path to commerce failed.
* `depends_on: {condition: service_healthy, restart: true}`: on `up`, the gateway waits for a healthy commerce.
  When Compose recreates or restarts commerce, it restarts the gateway too.
* State lives in `SBK_STATE_DIR` (SQLite with WAL). Entitlements, quotas, revocations and sessions survive a
  recreate. The Admin API token is never stored: a new process requests a fresh one (F4).

## Environment file (`compose.env`, outside Git)

```
SBK_PROJECT=<project name, same as -p>
SBK_IMAGE=sabpuja-kundali-commerce:<tag>
SBK_EPHE_DIR=<verified ephemeris dir>
SBK_SECRETS_DIR=<dir>/secrets
SBK_STATE_DIR=<dir>/state
SBK_TRUSTED_PROXY_FILE=<dir>/edge-cfg/trusted-proxy.conf   # set_real_ip_from <proxy address on the edge network>;
SBK_NETWORK=<edge network name>
# optional: SBK_BACKEND_SUBNET, SBK_COMMERCE_IP, SBK_GATEWAY_IP, SBK_EDGE_ALIAS
```

`commerce.json` must list the gateway's backend address in `trusted_proxies` (default `10.231.47.3`), plus:

* `admin_client_id`
* `admin_client_secret_file` (`shopify-client-secret`, the app's client secret)

The old `shopify-admin-token` file is no longer read; delete it after cutover.

## Deploy or update

1. Build the image from the exact commit: `docker build -f commerce/deploy/Dockerfile -t sabpuja-kundali-commerce:<tag> .`
2. Back up first:
   * `cp -a state state.bak-<UTC>`, taken while the stack is stopped, or with `sqlite3 .backup`
   * `compose.env` and the override
   * the `secrets/` listing (names only)
3. `docker compose -p <project> --env-file compose.env -f commerce/deploy/compose.yml [-f compose.qa-mailpit.yml] config -q`
4. `... up -d --wait` brings both services up and returns once both are healthy.
5. Check:
   * `GET https://<host>/healthz` answers 200 through the proxy
   * the webhook path still answers 401 to an unsigned request
   * other paths still ask for QA basic auth

## Rollback

1. `docker compose -p <project> ... down` (state, secrets and edge are untouched).
2. Restore the previous `compose.env`, override and commit checkout, plus `shopify-admin-token` if it was deleted,
   then `up -d` with the previous image tag.
3. If the state directory was changed by the failed version, stop the stack and restore `state.bak-<UTC>`.
4. The edge proxy configuration is not changed by this deployment, so it needs no rollback.

## Transactional e-mail

* QA: Mailpit through `integration/compose.qa-mailpit.example.yml` (`smtp.json` with `auth: "login"`).
* Production (owner choice 2026-11-09): our own send-only server, `deploy/compose.outbound-mail.yml` with image
  `commerce/mail/`.
  * Postfix and OpenDKIM. Commerce submits to `outbound-mail:2587` with STARTTLS, verified against a private CA,
    and no SMTP AUTH (`integration/smtp.outbound-mail.example.json`).
  * Postfix accepts only the internal mail network and only `MAIL_SENDER`.
  * It signs with DKIM and delivers straight to each recipient's MX, over IPv4 only.
  * Nothing is published, there is no inbox, and the queue lives in memory for at most 15 minutes. Addresses
    are redacted from the log.
  * For a QA signature check without DNS, add `integration/compose.qa-dkim-sink.example.yml` and set
    `SBK_MAIL_TEST_TRANSPORT=smtp:[dkim-sink]:1025`.
* The Google Workspace relay mode (`smtp.google-relay.example.json`) stays supported, but it is not used: there
  is no Workspace admin access.

### One-time setup for the send-only server

1. Create the internal network: `docker network create --internal <project>-mail`, and note its subnet for
   `SBK_MAIL_CLIENT_NETWORK`.
2. Secrets directory `SBK_OUTBOUND_MAIL_SECRETS_DIR`, every file 0400, never in Git or backups:
   * `dkim.private`, generated with `opendkim-genkey -b 2048 -d sabpuja.com -s kun2026`
   * `tls.crt` and `tls.key`, a server certificate for `outbound-mail` signed by the private CA that commerce
     trusts through `SSL_CERT_FILE`
3. `compose.env`:
   * `SBK_MAIL_HOSTNAME=mail.sabpuja.com`
   * `SBK_MAIL_DOMAIN=sabpuja.com`
   * `SBK_MAIL_SENDER=noreply@sabpuja.com`
   * `SBK_DKIM_SELECTOR=kun2026`
   * `SBK_MAIL_NETWORK`, `SBK_MAIL_CLIENT_NETWORK`, `SBK_MAIL_IMAGE`
4. In `commerce.json`, set `mail_from` to `Sabpuja <noreply@sabpuja.com>`.

### DNS needed before real customers (owner, at the authoritative DNS: Namecheap BasicDNS)

| Record | Host | Value |
|---|---|---|
| A | `mail` | `2.25.245.64` |
| TXT (SPF, edit the existing one) | `@` | `v=spf1 ip4:2.25.245.64 include:_spf.google.com ~all` |
| TXT (DKIM) | `kun2026._domainkey` | the `p=` value printed by `opendkim-genkey` (`v=DKIM1; k=rsa; p=...`) |
| TXT (DMARC, fix the case) | `_dmarc` | `v=DMARC1; p=none; pct=100` |
| PTR (Hostinger hPanel, VPS → IP → reverse DNS) | `2.25.245.64` | `mail.sabpuja.com` |

Keep exactly one SPF record. The edit adds only `ip4:2.25.245.64`; Google Workspace mail stays covered. After the
records propagate, send a code to a Gmail and an Outlook inbox the owner controls. Check that the headers show
`spf=pass`, `dkim=pass header.d=sabpuja.com` and `dmarc=pass`, and that the mail lands in the inbox, not spam.

Rollback: stop `outbound-mail`, put the previous `smtp.json` back, and restore the previous SPF value. The DKIM,
A and PTR records do no harm if they stay.
