# Sabpuja Kundali client-preview fast track

**PREPARED ONLY. NOT DEPLOYED.** This draft introduces a restricted preview packaging layer for the independently tested Gate 3E engine. It does not authorize public deployment, Shopify integration, DNS changes, Github Actions or merging code. Production remains **NO-GO**.

## User-facing MVP scope

- English-only D1 Rashi chart and D9 Navamsa chart with tables, exact house assignments and Swiss calculation metadata.
- Birth date, exact time and one of the ten curated Indian city reference points. The preview image removes the two test-only non-India city fixtures.
- Supported local dates from 1970-01-01 through 2100-12-31; birth time must be known. No invented birthplace or time; explicit refusals.
- No PDF, paid interpretations, customer accounts, automated Hindi translation, catalog coupling or remote third-party astrology services.
- Only synthetic birth records may be used in development and testing. Actual client access is forbidden until separately authorized.

## Isolation and access design

- `preview/Dockerfile` packages the existing Gate 3E core, with `pyswisseph==2.10.3.2` and `tzdata==2026.5`. Astronomical source and pinned files are unchanged. A deterministic packaging step excludes the two foreign test-only place fixtures from the preview image.
- Core remains **127.0.0.1:8765-only**. A rootless Nginx gateway shares the engine network namespace and forwards on internal :8080, with 10 requests/sec plus a 40-request general burst and a stricter chart POST limit (1 request/sec, burst 3). There is **no published host port** in the production-oriented Compose file.
- Gateway Basic Auth from a protected htpasswd file, exact browser Origin restriction, no-store/noindex responses, 4 KiB body limit, and HTTP 429 abuse throttling. Body and URL request access logs are disabled. Engine stores no profiles, cookies or request bodies.
- No client secrets in the repository. Generate credentials and a secure `htpasswd` file outside Git and use a private `--env-file` pointing to the file. Passwords must be sent only over HTTPS. Copying test credentials from the QA suite is forbidden.
- External Docker network name is supplied through an environment variable. Use a dedicated disposable QA network for testing, **never attach dev containers to the existing `edge` network**.
- `preview/Edge.Caddyfile.example` is a **dormant snippet**, not an installed route. Owner must explicitly authorize the hostname, DNS, real HTTPS certificate and preview release before making it reachable.
- Basic Auth is only appropriate for a tiny invite-only client preview, not public authentication. Confirm request-rate protections and access revocation before opening to clients.

## Mandatory checks before offering any link

1. Validate PR #42 base SHA and full source diff; refuse to deploy any drift.
2. Verify both `.se1` SHA-256 files against `prototype/README.md`; never copy the datasets into the image.
3. Run pinned engine 474 tests, prototype 106 tests, current D3 v2 Swiss conformance and synthetic D1/D9 smoke scenarios with clean working tree.
4. Validate Caddy config and Compose in a temporary isolated Docker network. Test unauthorized/incorrect credentials 401; correct credentials 200; cross-origin JSON POST 403; no-store; 4 KiB limit; no accidental published ports. Inspect security-related error logging for personal data.
5. Automated desktop/mobile browser smoke checks on the private QA listener using only synthetic data; verify both charts, API, form, fonts, navigation and visual clipping.
6. Confirm all preview branding, disclaimer, approved schema 0.3.0 and birthplace choices. Confirm privacy/licensing notice and GeoNames attribution are visible.
7. Confirm no real client information has been used, no external service contacted by browser, and no source changes or deploy have touched `main`, active Caddy, Shopify or any live service.

## Deferred and approval boundary

Do not call the application **client ready** until the owner separately approves an exact preview deployment SHA and HTTPS route, and an independent QA reviewer signs off the end-to-end HTTPS/Basicauth test plus request throttling/access-revocation checks. Do not call it public production even after preview approval. The existing PR #1 HOLD remains binding for merging code into `main`; C7 source accuracy is only exact-SHA reviewed.

**Sabpuja | https://sabpuja.com | Preview preparation only | Production NO-GO**

## Access revocation and throttling gate

Each invited reviewer must have a distinct credential in the operator-managed htpasswd file. To revoke access, remove that user's htpasswd entry on the host, **recreate only the isolated gateway container** so Docker remounts the updated file inode, then verify the old credentials return 401 and unaffected credentials still return 200. Use synthetic identities only in QA. The Nginx limit is per connecting source IP, not per reviewer, and the separate live HTTPS edge may cause source-address aggregation; this needs explicit acceptance or a trusted-proxy design before access. Never trust arbitrary X-Forwarded-For from the public Internet. Keep the site inaccessible from the public Internet until separate owner deployment approval.

**QA revocation finding:** An atomic htpasswd-file rewrite plus Nginx SIGHUP left the old bind-mounted inode in place; old credentials still worked. A gateway-only Compose force-recreate remounted the updated file and independently returned **401** for the removed synthetic account and **200** for the retained synthetic account. Do not use reload-only as a revocation step. This is mandatory operator guidance for any preview deployment.

**Failed-login log privacy (KUN-SEC-AUTHLOG-001):** Nginx `auth_basic` logs the attempted user name at `error` level on every failed login (`user "..." was not found`, `password mismatch`). A user who pastes a password into the user-name field would put it in the log. The gateway therefore checks Basic Auth in a second server that listens only on `127.0.0.1:8081` inside the gateway's network namespace, through `auth_request`. That server logs only `crit` messages. The public server keeps its normal error log, so throttling (`limiting requests`), oversized bodies and upstream errors are still recorded. Behaviour is unchanged: same realm, same htpasswd file, same 401/403/413/429 responses, and revocation still needs a gateway recreate. Regression test: `preview/tests/auth-log-privacy.sh` (isolated QA stacks only; `--upstream-check` pauses the engine).

## Gateway deployment files (owner-preview drift, recorded 2026-10-27)

The 2026-10-27 owner-preview update needed three hand edits on the host that were not in Git: the allowed HTTPS Origin, the gateway file mode for non-root Nginx, and a trusted Caddy address for per-client throttling. They are now configuration files beside `htpasswd`, outside Git, and Compose refuses to start without them:

- `SABPUJA_PREVIEW_ALLOWED_ORIGINS_FILE`: the exact browser Origin(s). Start from `preview/gateway/allowed-origins.map.example`.
- `SABPUJA_PREVIEW_TRUSTED_PROXY_FILE`: one `set_real_ip_from` line naming the HTTPS edge (Caddy) address. Start from `preview/gateway/trusted-proxy.conf.example`. Nginx then takes the client address from the last `X-Forwarded-For` entry, the one Caddy appends, and only from that address. A client that forges the header directly, or sends earlier entries, cannot change its throttling bucket. With no `set_real_ip_from` line the header is ignored and every caller behind the edge shares one bucket.

Before starting or recreating the gateway, as the operator:

1. Make all mounted gateway files readable by the Nginx user: `chmod 0644 Gateway.nginx.conf allowed-origins.map trusted-proxy.conf` and keep `htpasswd` readable by UID 101. The first 2026-10-27 switch failed on an unreadable file.
2. Confirm the edge address still matches the file, because recreating the Caddy container can change it: `docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}' <caddy-container>` and compare with `trusted-proxy.conf`.
3. Validate the exact files as the Nginx user before switching: `docker run --rm --user 101:101 --read-only --tmpfs /tmp -v "$PWD/preview/Gateway.nginx.conf:/etc/nginx/nginx.conf:ro" -v "$HTPASSWD:/etc/nginx/private-htpasswd:ro" -v "$ORIGINS:/etc/nginx/preview-allowed-origins.map:ro" -v "$PROXY:/etc/nginx/preview-trusted-proxy.conf:ro" nginx:1.28.0-alpine nginx -t`.

Isolated QA lists its own private origin in a throwaway allowed-origins file, for example `"http://<gateway-qa-ip>:8080" 0;`, and passes the same address as `QA_ORIGIN`. The browser smoke tests no longer try to rewrite the `Origin` header: Chromium ignores such rewrites, so the old tests could only pass against a gateway that already allowed the QA origin.
