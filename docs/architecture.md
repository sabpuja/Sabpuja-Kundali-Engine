# Architecture and boundaries

## Decision
Owned, self-hosted, AGPL-licensed Kundali numerical engine on Hostinger VPS. No external astrology API, cloud inference requirement or runtime calls to astrologer services.

```text
sabpuja.com Shopify UI (sabpuja/theme, NOT YET IMPLEMENTED)
  -> server-controlled authenticated app proxy (NOT YET IMPLEMENTED)
  -> rate-limited Kundali endpoint on Hostinger (NOT YET IMPLEMENTED)
  -> local Python + Swiss Ephemeris .se1
  -> deterministic Vedic rules
  -> localized charts / PDF, generated later
```

## Initial implementation
`src/sabpuja_kundali/engine.py` implements a **local-only** calculation function and CLI. It is not an HTTP server and does not read Shopify data. `rules.py` contains testable, pure mappings. Requests require a precise time offset and IANA timezone supplied by the caller; the engine does NOT guess birthplaces.

## Versioned conventions
- Sidereal zodiac: Lahiri ayanamsa.
- Nodes: mean Rahu, Ketu opposite 180 degrees.
- Houses: whole-sign houses based on sidereal ascendant (not quadrant houses).
- Planets: Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn; lunar nodes separately.
- Navamsa: D9 sign mapping; full D9 chart/ascendant presentation later.
- Start with a 1900-01-01 to 2100-12-31 envelope by local civil birth date (SCI-03); local dates before 1970-01-01 are refused until a historical clock is verified (RG-HIST Option B, P8). Expand only after historical timezone and reference test coverage.
- Sidereal ascendant calculated via Swiss `houses_ex` with `W` (whole-sign) geometry, `ascmc[0]` (SCI-01e; bit-identical to `P` at every sampled in-band point); this must pass reference validation before release.
- No Dasha, Dosha, Yoga, matching, prediction or product-remedy assertions until separately specified and validated.

## Service boundaries
A public app will require authentication, CSRF/abuse defenses, request limits, latency budgets, access control, privacy terms, observability excluding birth details, localization QA, and a source-offer link. Do not expose the local CLI directly as a public HTTP service.

## Repo routing
- Implementation and calculation methodology: this repo.
- Cross-repo decisions: sabpuja/core.
- Storefront/Component Lab: sabpuja/theme, with owner-approved unpublished staging only.
- Branding: sabpuja/design-system.
- Agent and runtime orchestration: sabpuja/Automation on VPS.
- Workflows/QA: sabpuja/Process-and-Workflows.
- Current state: sabpuja/Progress-Memory.
