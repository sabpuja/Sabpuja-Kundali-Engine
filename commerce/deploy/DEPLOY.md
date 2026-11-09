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

* QA: Mailpit through `integration/compose.qa-mailpit.example.yml`, with `smtp.json` `auth: "login"`.
* Production: Google Workspace SMTP relay, using `integration/smtp.google-relay.example.json` with `auth: "none"`
  (the relay checks this host's IPv4 address), `ipv4_only: true` and a real `ehlo_name`. Only after the Workspace
  admin has added the relay setting for this IPv4 address with TLS required. STARTTLS with certificate
  verification stays mandatory in both modes.
