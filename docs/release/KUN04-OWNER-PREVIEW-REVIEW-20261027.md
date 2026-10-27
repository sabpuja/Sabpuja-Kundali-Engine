# KUN-04 Owner Preview Release-Gate and Review Handoff

**27 October 2026 | OWNER-ONLY / SYNTHETIC QA | Client invitation: NOT AUTHORIZED | Production: NO-GO**

## Reviewed running artifact

- HTTPS owner-only preview: https://kundali-preview.srv2005300.hstgr.cloud
- GitHub draft PR #46 at exact source SHA f808eacfd677beca85c2eb33b8107def9ef12c71; no PR merge. New engine image SHA256 b788ae5d4397a69a3647e3a02a964e1b721d3d70ae95064cdabd1fd15b2ff2c0.
- Prior image SHA256 255cd8cab9e574a942b325c25c450eea7a72671370e87d72eb6cda3fa75909fd retained under rollback tag.
- Gateway-only runtime patches outside Git source: permitted HTTPS Origin replaced with current host; file permissions corrected for UID 101; trusted Caddy upstream (observed 172.28.0.3) added to Nginx real-IP parsing. Caddy config and unrelated services not modified.
- No Shopify changes, public-domain deployment, new user invitations, real personal birth data, GitHub Actions or production code merge.

## Actual-HTTPS evidence

| Check | Outcome | Scope / limitation |
| --- | --- | --- |
| TLS/authentication | PASS | Live TLS validates; anonymous and wrong-password 401; owner 200 |
| D1/D9 authenticated chart | PASS | Synthetic New Delhi; 0.3.0; ten supported India cities |
| PDF HTTP download | PASS | Genuine eight-page 153,040-byte attachment; status 200; no-store; 401/403/413/415/422 and 429 tested |
| Chromium UI and Download | PASS | 280, 375, 768, 1440 widths, actual TLS; D1/D9 rendered; PDF downloaded; no overflow/JS exceptions; Clear disables download |
| PDF content check | PASS | Eight pages, embedded Poppins + Inter, D1/D9 & Delhi labels, zero out-of-page words |
| Preview access revocation | PASS | Temporary QA login 200 before removal, 401 after gateway recreation; owner baseline intact |
| Real-IP throttle isolation | PASS for tested paths | Trusted exact Caddy upstream IP; concurrent independent Windows/VPS 401/429 patterns; forged external X-Forwarded-For failed to bypass a depleted limit |
| Synthetic log scan | PASS, limited | Current engine/gateway Docker logs since 2026-10-27 11:20 UTC have no instances of three QA date/time/city tokens. Not a general personal-data audit |
| Restorable previous image | Available; first attempted switch auto-rolled back | Rollback snapshot exists. Do not delete prior tag or config |
| GitHub refs | Unchanged | Main 2f67c648f7c7e02dade58bd72993722d06cb1cd3; PR #46 draft; GitHub Actions 0 |

**Important remaining risk:** exact upstream trust uses the presently observed Caddy private-IP address. If the Caddy container is recreated and acquires a different IP, confirm/recompute the Nginx trust line and rerun per-client limits. Prefer a future deterministic private network addressing or controlled generated configuration as an independent infrastructure change. Do not broaden trust to all internet traffic or accept arbitrary forwarded headers.

**Release categorization:** the scoped four HTTPS QA categories now have passing synthetic test evidence; owner visual/editorial acceptance is **pending human owner review**; independent golden-chart scientific certification is not claimed; paid-client/general production gates remain NO-GO.

## Owner review pack, what to examine

Synthetic artifacts are on approved Hostinger under:
- /srv/sabpuja-kundali-owner-preview-20261027-pdf/evidence/screen-280.png, screen-375.png, screen-768.png and screen-1440.png
- /srv/sabpuja-kundali-owner-preview-20261027-pdf/evidence/report-375.pdf and report-1440.pdf
- /srv/sabpuja-kundali-owner-preview-20261027-pdf/evidence/browser-https-result.json
- /srv/sabpuja-kundali-owner-preview-20261027-pdf/evidence/https-report-result.json
- /srv/sabpuja-kundali-owner-preview-20261027-pdf/evidence/pdf-structure-result.json
- /srv/sabpuja-kundali-owner-preview-20261027-pdf/evidence/privacy-log-audit.json

### Human acceptance checklist

- [ ] Desktop and mobile hero/forms feel like the approved Sabpuja brand; no prototype/debug/staging language or missing logo
- [ ] Confirm D1 and D9 chart legibility at 375 and 1440 px, table density, empty/clear/error states
- [ ] Check PDF all eight pages visually: cover, hierarchy, technical content, actual chart/table legibility, printed A4 margins, no generic filler or incomplete labels
- [ ] Confirm preferred PDF content depth is only current Phase 1, not yet premium, and provide prioritized sections to enrich
- [ ] Explicitly accept/reject overall readability, typography, tone, design consistency, download UX and demonstrated refusal messaging
- [ ] Approve or request changes to the proposed comprehensive report RFC and separate science-method decisions
- [ ] No real customer birth data or invited users without privacy/legal and golden-reference signoff

## Two independent acceptance gates remain mandatory

**ENG**: independent exact-SHA calculation rules, pinned deps, golden references, schema compatibility, error/security handling, daylight/clock and place-data correctness. Existing C7 scoped engineering pass ≠ all-module golden-chart accuracy.

**RPT**: independent interpretation-to-chart provenance, reading quality, meaningful depth, visual QA, non-overconfident claims and accessibility. A correct PDF transport or eight-page page-count check ≠ RPT editorial signoff.

No feature is sellable before both gates pass on the exact variant delivered.

## Immediate follow-up

Owner can review the unchanged restricted HTTPS preview and synthetic screenshots/PDF. On feedback, produce a narrow design-only PR if needed. Separately submit method-choice RFCs for Panchanga, Vimshottari, birthplace expansion and new vargas for scientific-owner approvals before code integration. Keep PR #1 HOLD; never merge draft PRs in response to this owner-review preparation.
