# Accuracy and acceptance test plan

## Existing tests
`tests/test_rules.py`: boundary tests for zodiac normalization, Rashi, Nakshatra/Pada, Navamsa and whole-sign houses.
`tests/test_engine_contract.py`: input validation, timezone offset rejection and fail-closed missing ephemeris behavior. These tests do NOT establish astronomical accuracy.

## Required golden-chart verification (NOT DONE)
1. Pin exact Swiss Ephemeris source, binding, source data SHA-256 and calculation flags.
2. Obtain licensed/independent trusted reference charts with documented birth time, historical offset, lat/lon, Lahiri definition, mean-node convention, and house methodology.
3. Check Sun, Moon, all classical grahas, mean nodes, ascendant and D1 houses against independent references. Define numeric tolerances, including birthtime precision and polar/house edge cases, *before* checking pass/fail.
4. Cover sign and Nakshatra/Pada boundaries, D9 boundaries, leap years, unusual geographic longitude, DST transition folds/gaps, historic Indian timezones and inconsistent UTC offsets.
5. Confirm no silent ephemeris fallback and no stale global state across concurrent requests.
6. Validate Hindi/English report labels separately from numerical outputs.
7. Add Dasha/Dosha/Yoga only after a documented algorithm/specification and their own independent fixtures.
8. Human review of methodology, astrology variants, privacy and AGPL deployment boundary.

No factual accuracy or release claim without evidence in the PR and a versioned validation report.
