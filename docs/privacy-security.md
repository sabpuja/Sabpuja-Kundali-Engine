# Privacy and security requirements

Birth date, exact time and location can be sensitive personal information.

Foundation currently has **no database, analytics collection, outbound API, HTTP server or logging of request bodies**. It only reads stdin and prints a sensitive chart result to stdout. Run locally with controlled input/output only.

Before public use:
- Minimize input and retention; default to no profile storage. Saving profiles requires separate consent and authenticated per-account ownership checks.
- No PII in logs, source, fixtures, query strings, error reporting, caches or GitHub Issues/PRs.
- Restrict backend network access, secrets and ephemeris volume permissions; use TLS through approved edge. Add secure authentication, request quotas, CSRF controls, anti-automation limits and abuse monitoring that excludes birth data.
- Treat missing/unknown birth time as an explicit state, never as midnight or noon.
- Allow deletion/export for any stored birth profiles; define retention and comply with applicable laws and consent requirements.
- Do not treat derived horoscope interpretation as evidence-based medical, financial or legal advice.
- Run security/privacy threat review before a Shopify staging API is exposed.
