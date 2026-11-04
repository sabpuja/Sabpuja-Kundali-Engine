# Engine start-up readiness (Gate 3C, PKG-2)

**Status: engine API implemented and tested; no service calls it yet.** There is no HTTP service in this branch. Production: NO-GO.

`sabpuja_kundali.readiness` is the fail-closed start-up gate that a future service runs **once, before it opens a listener or accepts any request**. It closes Gate 3A findings G3A-06 (no start-up gate; `verify_all()` had no caller) and, with `engine.swiss_runtime()`, G3A-07 (Swiss versions not enforced at run time). It changes no calculation.

## API

```python
from sabpuja_kundali import engine, readiness

result = readiness.require_ready(ephe_path)  # raises readiness.EngineNotReadyError unless READY
# ... only now bind the socket and start accepting requests ...
chart = engine.calculate(request, ephe_path=ephe_path)
```

- `preflight(ephe_path=None) -> ReadinessResult`: never READY after a failure. `ephe_path` defaults to `SABPUJA_EPHE_PATH`, resolved by `engine.ephemeris_path()`, exactly as `calculate` resolves it.
- `require_ready(ephe_path=None) -> ReadinessResult`: the same, but raises `EngineNotReadyError` (`.code == "ENGINE_NOT_READY"`, `.result` the NOT_READY result, text `ENGINE_NOT_READY: <first failing code>`).
- `ReadinessResult`: `status` (`READY` or `NOT_READY`), `ready`, `code` (the first failing code, `None` when READY), `checks` (one `CheckResult(name, status, code, cause)` per check), `facts` (READY only) and `as_dict()`.

## Checks

They run in this fixed order. The first failure stops the preflight, and every later check is reported `NOT_RUN`.

| # | Check | Verifies | Failure codes |
|---|---|---|---|
| 1 | `ephemeris_data` | The packaged ephemeris manifest is readable and well formed (entry and field shapes, see `docs/api-contract.md`); `SE_EPHE_PATH` is not set; the directory exists; every required `.se1` file matches its pinned size and SHA-256 (`ephemeris.verify_ephemeris_dir`, the per-request gate) | `EPHEMERIS_MANIFEST_INVALID`, `EPHEMERIS_PATH_OVERRIDE`, `EPHEMERIS_PATH_MISSING`, `EPHEMERIS_FILE_MISSING`, `EPHEMERIS_FILE_UNREADABLE`, `EPHEMERIS_FILE_MISMATCH` |
| 2 | `swiss_runtime` | `swisseph` imports; `swe.version == "2.10.03"`; `pyswisseph` distribution metadata exists and is exactly `2.10.3.2` (`engine.swiss_runtime`, the per-request gate). No Swiss call | `SWISS_BINDING_MISSING`, `SWISS_LIBRARY_VERSION_MISMATCH`, `SWISS_BINDING_METADATA_MISSING`, `SWISS_BINDING_VERSION_MISMATCH` |
| 3 | `timezone_data` | A **fresh** `PinnedZoneLoader`: manifest shape and digest; manifest package version is the approved `2026.5`; `verify_all()` (installed `tzdata` version and IANA version, then the size and SHA-256 of every manifest zone, re-read from the package whatever the process cache holds); the request loader (`default_loader()`) loads and names the same data | `TZDATA_MANIFEST_MISSING`, `TZDATA_MANIFEST_INVALID`, `TZDATA_PACKAGE_MISSING`, `TZDATA_VERSION_MISMATCH`, `TZDATA_FILE_MISSING`, `TZDATA_FILE_MISMATCH` |
| 4 | `canary_calculation` | `engine.calculate` on the approved synthetic request (`2000-01-01T17:30:00+05:30`, `Asia/Kolkata`, 28.6139, 77.2090: the `docs/api-contract.md` and `examples/` request, also the PR #39 canary). Its chart is checked in step 5, then discarded | `ENGINE_CANARY_FAILED`, with the engine code as `cause` (for example `SWISS_EPHEMERIS_FALLBACK_REFUSED`, `ASCENDANT_UNCOMPUTABLE`) |
| 5 | `output_contract` | Chart `schema_version` equal to the engine constant (`0.3.0`, proposed, on the Gate 3E branch; `0.2.0` baseline) and a whole-sign `d9` block; `calculation_metadata.metadata_schema` `sabpuja-calculation-metadata/3`; the nine bodies in order and a Lagna; the metadata names the pinned library, binding and tzdata versions and the ephemeris manifest verified in step 1 | `ENGINE_SCHEMA_MISMATCH`, `ENGINE_PROVENANCE_MISMATCH` |

`ENGINE_NOT_READY`, `ENGINE_CANARY_FAILED`, `ENGINE_SCHEMA_MISMATCH` and `ENGINE_PROVENANCE_MISMATCH` are start-up codes only; no request returns them. The first three names match the start-up codes of draft PR #39 where the meaning is the same.

On READY, `facts` holds only pinned, non-private values: the library, binding and tzdata versions, the IANA version, both manifest digests, the required ephemeris file names, the number of zones verified (598) and the two schema versions.

## Privacy and failure behaviour

- The result never contains a path, an environment value, a request value or exception text: only the fixed check names, codes, statuses and the facts above. No telemetry, logging, storage, download or installation.
- Typed engine faults become NOT_READY. Any other exception is a programming defect and **propagates** (it is not turned into a NOT_READY code), which also stops start-up.
- The preflight sets no Swiss state of its own. The canary is an ordinary request, so the per-request Swiss reset applies, and a later chart is unchanged (tested).
- It is a start-up gate, not a health check: run it once per process before serving. The ephemeris files and the Swiss library version are also checked on every request, the binding distribution version once per process, and each zone file when it is first loaded.

## Reuse by a future service

1. At process start, call `readiness.require_ready(ephe_path)`. If it raises, exit non-zero without binding a socket, and print only `result.code` (or `result.as_dict()`).
2. Only after READY, bind the listener.
3. Per request, call `engine.calculate(request, ephe_path=ephe_path)` and catch `engine.EXPECTED_ERRORS` only. `InputRefusalError` is a caller error. `ChartComputationError`, `EphemerisDataError` and `TimezoneDataError` are server faults; the `SWISS_BINDING_*`, `SWISS_LIBRARY_VERSION_MISMATCH` and `SWISS_EPHEMERIS_FALLBACK_REFUSED` codes in particular mean the deployment, not the request, is wrong.
4. Anything else is a defect. The service must return a fixed internal error with no traceback to the client and keep the defect visible to operators without request values (Gate 3A R-04 / G3A-05: still open for a service; the CLI keeps Python's exit 1).

## Compatibility with draft PR #39 (not modified by this package)

PR #39 (`dcd6a2f`, localhost prototype) has its own `startup_verify()` in `prototype/kundali_prototype/server.py`. It is not changed here. A three-way merge of PR #39 and this branch has no textual conflict. For a separately authorized integration task:

- **Start-up.** `startup_verify()` can call `readiness.require_ready(ephe_path)` first and keep only its prototype-specific steps (the birthplace fixture and the loopback bind). Its checks are a subset of the preflight. The preflight adds: a fresh-loader zone re-hash, the binding-metadata-missing case as its own code, the provenance comparison, and a typed-only canary (PR #39 maps *any* canary exception to `ENGINE_CANARY_FAILED`). Its `SWISS_VERSION_MISMATCH` becomes the engine's split `SWISS_LIBRARY_VERSION_MISMATCH` and `SWISS_BINDING_*` codes.
- **Per-request mapping (behaviour change to review).** With this package, a missing binding, a version mismatch or a Moshier fallback is a `ChartComputationError`, not a bare `RuntimeError`. PR #39's `handle_chart` maps `ChartComputationError` to HTTP 422 `computation`, so these deployment faults would show as 422 with the new codes instead of 503 `ENGINE_UNAVAILABLE`. The integration task should map those codes, and probably every `ChartComputationError`, to 503 `resources`. None is reachable for valid input in a correctly pinned environment.
- **Successful charts** are byte-identical (see the Gate 3C invariance evidence), so the PR #39 renderer and its chart-consistency tests are unaffected.
