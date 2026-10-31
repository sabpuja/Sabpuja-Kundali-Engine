# Sabpuja Kundali - Owner-only Phase 1 PDF preview update

**Status: prepared, NOT DEPLOYED.** This integration branch is stacked on the reviewed Phase 1 PDF generator PR #45, which is stacked on owner-only preview PR #44. No code PR, GitHub Action, Shopify update, new public website, or production release is authorized here.


> **KUN-RPT-002B update (draft, NOT DEPLOYED):** `POST /api/report` now renders the ten-page Phase 2A premium report (`report/phase1/premium_report.py`) in the owner-approved saffron Foundation palette (`baseline`, OD-10). The palette is fixed in `server.REPORT_PALETTE` and is never read from the request; the maroon candidate is never served. The endpoint contract, headers, filename, `REPORT_BUSY`/`REPORT_UNAVAILABLE` behaviour, 1 MiB limit and in-memory rendering are unchanged. The eight-page Phase 1 generator stays in the source for regression tests; rollback is redeploying the reviewed PR #53 image. References below to an 8-page PDF describe the Phase 1 release.

## MVP scope

- Existing D1/D9 authenticated owner-only calculation stays on the canonical schema 0.3.0 and original pinned Swiss engine. No mathematical changes.
- After a successful calculation, the browser enables **Download Kundali PDF**. The button POSTs the same bounded form input to a separate private `/api/report` endpoint. The server recomputes from the trusted place fixture and returns the generated 8-page PDF, not an arbitrary client-supplied chart.
- The generated PDF contains birth location/date/time and planetary values. Treat it as **sensitive personal information** when genuine data is eventually permitted. No server-side files, user profiles, queues or caches are created; the recipient's device **does retain the downloaded PDF**.
- On error the browser keeps the chart visible and displays a generic message. Do not print request input, personally identifying filenames, or exception messages in logs.

## Security/privacy contract

1. Deploy only behind the existing restricted Hostinger HTTPS gateway, per-user Basic Auth and independent credentials. Keep the current hostname and noindex, no-store, strict Origin, 4 KB request and per-IP throttling.
2. Gateway uses a **separate rate-limited /api/report** location; request-rate burst = 1 beyond its 1 request/second token rate. Do not disable cross-origin enforcement. Behind-proxy per-IP behavior must be verified on real HTTPS before owner download approval.
3. The localhost-only engine requires JSON, validates Host and Origin and refuses oversized/malformed data before calculation. It permits **one concurrent PDF render** per process, with a 1 MiB in-memory PDF cap.
4. Successful response: `Content-Type: application/pdf`, `Content-Disposition: attachment`, `Cache-Control: no-store`. Any refusal uses the existing stable JSON errors. Rendering exceptions send fixed `REPORT_UNAVAILABLE` and log only the exception *type*.
5. Use **only synthetic** birth details for QA. Never allow an invited client access, publish credentials, enable request logging, use analytics, or claim production/golden-chart certification.
6. The browser revokes its temporary object URL after a download. It must abort a pending PDF request when the form changes, hide the result and disable the button on Clear.

## Isolated QA evidence and limits

- Source SHA must be frozen and recorded when promoting a draft deployment. Compare with the exact PR diff, build source and independent engine C7-approved underlying tree.
- Re-run `python -m unittest discover -s prototype/tests -v` with `PYTHONPATH` pointed to the **source checkout**, `SABPUJA_TEST_EPHE_PATH` to checksum-verified ephemeris files, and `SABPUJA_EPHE_PATH` unset. A CI/container with only loopback may legitimately skip the non-loopback interface test; disclose that skip.
- PDF/HTTP checks: unauthorized and wrong password 401, unexpected Origin 403, 5 KB body 413, malformed content 415, unsupported birthplace refusal 422, synthetic accepted report 200, PDF signature, attachment headers, no-store and max size.
- Chromium at 280/375/768/1440 widths: authenticated form, correct D1/D9, download event, valid PDF bytes and filename, embedded Poppins and Inter, no JS errors, no overflow, and Clear disables Download. A private-network HTTP test needs an **isolated browser test-only simulation** of the configured HTTPS Origin for PDF, chart and WOFF2 requests. This is **not actual TLS acceptance**.
- Use PyMuPDF to independently verify 8 pages, searchable values, embedded approved fonts, no text outside page bounds, no real client names and schema status `UNVERIFIED_GOLDEN_CHARTS`. Original PDF source code and approved brand artwork must not be changed in this integration without a new QA review.
- Run a Docker/request/log scan for synthetic birth dates and secret leaks. Keep raw request bodies out of all evidence and logs.

## Prepared owner-preview update procedure (requires separate owner deployment authorization)

**Current protected preview:** `https://kundali-preview.srv2005300.hstgr.cloud`, running the original PR #44 owner-only build. **Do not replace it under this instruction alone.**

After the owner approves the exact integration SHA and limited owner-only update:

1. Snapshot source SHA, current running image digest, Compose/Nginx/Caddy routing, anonymous-401 baseline and owner-credential file location. Keep the approved Swiss .se1 files read-only and their SHA-256 unchanged.
2. Build the new pinned image in a temporary workspace with no real birth records. Validate startup preflight and all isolated tests. Never rebase/merge the original PR branches to deploy this candidate.
3. Switch only the **owner-preview engine and gateway** to the reviewed image after ensuring the original containers and image digest are available for rollback. Do not add a published host port or change the public SSL certificate, hostname or other services.
4. On actual HTTPS, rerun 401/403/413/429 checks, successfully calculate synthetic D1 and D9, download and inspect the 8-page PDF in Chromium mobile and desktop, test missing credentials and revoke a synthetic user. **Recreate the gateway container to remount edited htpasswd files**; reload alone is not sufficient.
5. Review access/error logs and legal/AGPL source and Swiss/GeoNames attribution. Invite no client until independently signed off.

### Rollback

If any PDF/HTML error, TLS failure, invalid font, missing chart, Origin issue, unauthorized PDF response, excessive memory, logging leak or security regression occurs, immediately restore the prior image and gateway config at the recorded PR #44 snapshot. Verify previous `/api/chart` status 200 for synthetic input and `/api/report` 404, anonymous 401, HTTPS certificate and unrelated live sites. Leave preview restricted. **No production rollout**.

**Release state:** preparation only; no merge, no GitHub Actions, no Shopify changes, no real customer data. PR #1 HOLD continues to apply to public production. 
