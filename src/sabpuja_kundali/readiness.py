"""Fail-closed engine start-up preflight for a future service (Gate 3C, G3A-06).

A service calls `require_ready()` (or `preflight()`) once, before it opens a
listener or accepts any request, and refuses to start unless the result is
READY. Checks run in a fixed order and stop at the first failure; later checks
are reported NOT_RUN, so no READY can follow a failure. The result carries
fixed check names, stable codes and pinned version facts only: never a path,
an environment value, a request value or exception text. Nothing is
downloaded, installed or written, and no telemetry is sent.

Typed engine faults become a NOT_READY result. Any other exception is a
programming defect and propagates unchanged, which also stops start-up.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import engine, provenance, timezones
from .ephemeris import EphemerisDataError, load_manifest as load_ephemeris_manifest, verify_ephemeris_dir
from .timezones import PinnedZoneLoader, TimezoneDataError

READY = "READY"
NOT_READY = "NOT_READY"
PASS, FAIL, NOT_RUN = "PASS", "FAIL", "NOT_RUN"
CHECKS = ("ephemeris_data", "swiss_runtime", "timezone_data", "canary_calculation", "output_contract")

REQUIRED_TZDATA_VERSION = "2026.5"
# Approved synthetic canary (examples/birth-request.example.json, the docs/api-contract.md
# example, the PR #39 prototype canary). Its chart is checked, then discarded.
CANARY_REQUEST = {"birth_datetime": "2000-01-01T17:30:00+05:30", "timezone": "Asia/Kolkata",
                  "latitude": 28.6139, "longitude": 77.2090}
CANARY_BODIES = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu_mean", "ketu_mean")


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    code: str | None = None
    cause: str | None = None  # the engine code behind ENGINE_CANARY_FAILED

    def as_dict(self) -> dict[str, str | None]:
        return {"name": self.name, "status": self.status, "code": self.code, "cause": self.cause}


@dataclass(frozen=True)
class ReadinessResult:
    status: str
    code: str | None
    checks: tuple[CheckResult, ...]
    facts: tuple[tuple[str, object], ...]

    @property
    def ready(self) -> bool:
        return self.status == READY

    def as_dict(self) -> dict[str, object]:
        return {"status": self.status, "code": self.code,
                "checks": [c.as_dict() for c in self.checks], "facts": dict(self.facts)}


class EngineNotReadyError(RuntimeError):
    """Start-up preflight failed; the service must not accept requests."""

    def __init__(self, result: ReadinessResult):
        super().__init__(f"ENGINE_NOT_READY: {result.code}")
        self.code = "ENGINE_NOT_READY"
        self.result = result


class _Failed(Exception):
    def __init__(self, code: str, cause: str | None = None):
        self.code, self.cause = code, cause


def _fresh_zone_loader() -> PinnedZoneLoader:
    # A new loader re-reads and re-hashes every zone file from the installed package,
    # whatever the process-wide loader has already cached.
    return PinnedZoneLoader(timezones.load_manifest())


def _ephemeris_data(ephe_path: str, facts: dict) -> None:
    try:
        manifest = load_ephemeris_manifest()
        verify_ephemeris_dir(ephe_path, manifest)  # SE_EPHE_PATH, directory, every required file
    except EphemerisDataError as exc:
        raise _Failed(exc.code) from None
    facts["ephemeris_manifest_sha256"] = provenance.canonical_sha256(manifest)
    facts["ephemeris_required_files"] = sorted(e["name"] for e in manifest["files"] if e.get("required") is True)


def _swiss_runtime(facts: dict) -> None:
    try:
        swe = engine.swiss_runtime()
    except engine.ChartComputationError as exc:
        raise _Failed(exc.code) from None
    facts["swiss_library_version"] = swe.version
    facts["swiss_binding_version"] = provenance.binding_distribution_version()


def _timezone_data(facts: dict) -> None:
    try:
        fresh = _fresh_zone_loader()
        if fresh.provenance()["package_version"] != REQUIRED_TZDATA_VERSION:
            raise _Failed("TZDATA_VERSION_MISMATCH")
        count = fresh.verify_all()  # installed version, then every manifest zone's size and SHA-256
        serving = timezones.default_loader()  # the loader requests use
    except TimezoneDataError as exc:
        raise _Failed(exc.code) from None
    if serving.provenance() != fresh.provenance():
        raise _Failed("TZDATA_MANIFEST_INVALID")
    facts.update(tzdata_package_version=fresh.provenance()["package_version"],
                 tzdata_iana_version=fresh.provenance()["iana_version"],
                 tzdata_manifest_sha256=fresh.provenance()["manifest_sha256"], tzdata_zones_verified=count)


def _canary(ephe_path: str) -> dict:
    try:
        return engine.calculate(dict(CANARY_REQUEST), ephe_path=ephe_path)
    except engine.EXPECTED_ERRORS as exc:
        raise _Failed("ENGINE_CANARY_FAILED", exc.code) from None


def _output_contract(chart: dict, facts: dict) -> None:
    meta = chart.get(provenance.METADATA_KEY)
    ok = (chart.get("schema_version") == provenance.SCHEMA_VERSION
          and isinstance(meta, dict) and meta.get("metadata_schema") == provenance.METADATA_SCHEMA
          and isinstance(chart.get("planets"), dict) and tuple(chart["planets"]) == CANARY_BODIES
          and isinstance(chart.get("lagna"), dict))
    if not ok:
        raise _Failed("ENGINE_SCHEMA_MISMATCH")
    swiss = meta.get("swiss_ephemeris", {})
    if (swiss.get("library_version") != engine.REQUIRED_SWISS_LIBRARY_VERSION
            or swiss.get("python_binding_version") != engine.REQUIRED_BINDING_VERSION
            or meta.get("timezone_data", {}).get("package_version") != REQUIRED_TZDATA_VERSION
            or meta.get("ephemeris_data", {}).get("manifest_sha256") != facts.get("ephemeris_manifest_sha256")):
        raise _Failed("ENGINE_PROVENANCE_MISMATCH")
    facts.update(chart_schema_version=chart["schema_version"], metadata_schema=meta["metadata_schema"])


def preflight(ephe_path: str | None = None) -> ReadinessResult:
    """Verify every pinned resource and one synthetic chart; READY only if all pass.

    ephe_path defaults to SABPUJA_EPHE_PATH, exactly as `engine.calculate` resolves it.
    """
    path = engine.ephemeris_path(ephe_path)
    facts: dict[str, object] = {}
    state: dict[str, dict] = {}
    steps = {
        "ephemeris_data": lambda: _ephemeris_data(path, facts),
        "swiss_runtime": lambda: _swiss_runtime(facts),
        "timezone_data": lambda: _timezone_data(facts),
        "canary_calculation": lambda: state.__setitem__("chart", _canary(path)),
        "output_contract": lambda: _output_contract(state["chart"], facts),
    }
    results: list[CheckResult] = []
    failure: _Failed | None = None
    for name in CHECKS:
        if failure is not None:
            results.append(CheckResult(name, NOT_RUN))
            continue
        try:
            steps[name]()
        except _Failed as exc:
            failure = exc
            results.append(CheckResult(name, FAIL, exc.code, exc.cause))
        else:
            results.append(CheckResult(name, PASS))
    if failure is not None:
        return ReadinessResult(NOT_READY, failure.code, tuple(results), ())
    return ReadinessResult(READY, None, tuple(results), tuple(sorted(facts.items())))


def require_ready(ephe_path: str | None = None) -> ReadinessResult:
    """Return the READY result, or raise EngineNotReadyError: call before accepting requests."""
    result = preflight(ephe_path)
    if not result.ready:
        raise EngineNotReadyError(result)
    return result
