![Sabpuja official logo](../prototype/kundali_prototype/static/brand/sabpuja-logo-horizontal-color.svg)

# Sabpuja Kundali - Private Client Preview Release Gate QA

**Project website:** https://sabpuja.com  
**Date:** 2026-10-26  
**PR:** #44, stacked on Gate 3E PR #42 at source SHA `185353a1de8e5da02d20ea156cd4fca225fc1a27`  
**Status:** ISOLATED QA PASS. EXTERNAL HTTPS RELEASE NOT AUTHORIZED. PRODUCTION NO-GO.

## Scope verified

- The pinned Python Swiss engine and D1/D9 JSON schema 0.3.0 remained unchanged. Changes concern the restricted preview image, invitation-only frontend wording, source attribution, gateway and synthetic tests.
- Two-container private Compose stack uses an unprivileged Python engine at `127.0.0.1:8765` and an unprivileged Nginx gateway at internal `:8080`, sharing network namespace without published host ports.
- Build was validated with pinned pyswisseph 2.10.3.2, tzdata 2026.5 and SHA-verified `sepl_18.se1` and `semo_18.se1`, mounted read-only.
- Ten curated Indian city reference entries included in the preview image. Foreign test-only fixture entries omitted.
- Standard Nginx Basic Auth, strict proposed HTTPS Origin requirement, no access log, no-store/noindex, 4 KB request bound, general per-IP 10 requests/sec burst 40, chart-specific 1 request/sec burst 3 and 20 concurrent requests per connecting IP.
- Public AGPL Corresponding Source and GeoNames attribution links are visible in the footer. Formal license/privacy deployment review remains required.

## Independent QA evidence

Executed through the authorised Windows Desktop Commander and SSH on Hostinger in temporary `/tmp/sabpuja-kundali-preview-qa-20261026`. The test network `sabpuja-kundali-qa-20261026` is Docker-internal and isolated from the running `edge` network.

### Browser (Playwright Chromium)

Source: `preview/tests/browser-smoke.cjs`.

- Viewports **280, 375, 768 and 1440 px: 4/4 PASS**, all with synthetic birth details.
- Each successful submission populated ten D1 and ten D9 table rows and drew both North Indian charts.
- No whole-page horizontal overflow, no unexpected external browser requests, no browser JS errors and working Clear control.
- The internal HTTP test runner **simulated the intended HTTPS Origin** solely to exercise the gated form. These runs do NOT verify real-world TLS, certificate trust, Internet ingress or an HTTPS browser session.
- Synthetic screenshots and machine output are retained only in the private QA workspace under `browser-results/`; no genuine client data used.

### Gateway/API (synthetic security suite)

Source: `preview/tests/security-smoke.cjs`.

- **9/9 PASS:** anonymous 401, wrong password 401, correct login 200, privacy response headers, exactly ten Indian cities, unexpected Origin 403, 5 KB upload 413, concurrent chart POSTs resulting in 429, general request flood resulting in 429.
- Observed chart burst: **4 successful HTTP 200, 14 HTTP 429**. Observed 80-request general flood: **28 HTTP 200, 52 HTTP 429**.
- Nginx access logging disabled; no request-body storage or database. This source inspection and synthetic runtime exercise do not replace a live-edge log redaction assessment.

### Credential revocation

Initially, removing an account by an atomic host file replacement and sending only Nginx HUP **FAILED**: Docker's bind mount remained on the previous inode and the removed synthetic login still returned 200. The runbook now requires **a gateway-only container force-recreate**, which remounts the updated credentials file.

The corrected procedure passed: revoked synthetic account **401**, retained independent synthetic account **200**. It must be used for every access change until a dedicated identity layer is approved.

### Browser-safety issue corrected

Early rootless Nginx tests showed that a three-connection limit returned 429 for essential JavaScript assets. It was revised to twenty concurrent requests, keeping rate limiting, and the 4-width browser run subsequently passed. No source calculation changes were required.

## Outstanding client-access gate, strictly NOT approved

- Owner approval of the exact private-preview commit SHA, private Hostinger deployment target and HTTPS hostname.
- Real TLS certificate, external edge reverse-proxy and browser-origin test, with DNS/routing changes performed only after separate authorization.
- Verify identity isolation/individual credentials, revoked access on the **real HTTPS** route, request throttling behind edge proxy without trusting arbitrary X-Forwarded-For, and absence of birth data in any edge/proxy/error logs.
- Formal privacy/legal source-offer checklist and operator handling of any real client birth data. **No real client birth data was used in development or QA.**
- One short real-HTTPS browser/mobile and keyboard smoke pass after private deployment and before inviting clients.

**No GitHub Actions, Shopify edits, code PR merges, changes to live Caddy, public routes, or production deployments were authorized or performed.** PR #1 HOLD remains active for production engine integration. Passing this restricted QA does not waive C7 or authorize public launch.

**Recommendation:** Prepare a separately approved **access-restricted HTTPS owner-only validation**, then grant client access only after the remaining HTTPS/privacy checks pass. Do not merge PR #44 or expose it externally under this instruction.
