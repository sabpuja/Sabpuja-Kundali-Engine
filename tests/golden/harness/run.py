"""Golden-chart harness entry point (WP1 skeleton).

    python -m tests.golden.harness.run --ephe /abs/ephe --report-dir reports/

Order: environment and run-level gates, then per-fixture gates, and only if
nothing blocks, the engine call and comparison. Exit 0 PASS, 1 FAIL,
2 BLOCKED or QUALIFIED. There is no skipped state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import os
import sys

from ..generator.isolation import scan_directory
from . import compare, gates
from .environment import capture_environment, environment_reasons
from .manifest import MANIFEST_NAME, check_manifest, emitted_block_contradictions, signature_mismatches
from .outcomes import Outcome, exit_code, fixture_outcome, overall_verdict
from .report import to_markdown, write_reports
from .schema import load_fixture_set, strict_loads

GOLDEN_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = GOLDEN_DIR.parents[1]
DEMO_BANNER = "DEMO ONLY / NOT ASTRONOMICAL VALIDATION"
REPORT_SCHEMA = "sabpuja-golden-report/1"
_CONFIGS = {"decisions": ("decision-status.json", "decisions"),
            "tolerances": ("tolerances.json", "tolerances"),
            "references": ("reference-registry.json", "references"),
            "time_track": ("time-track.json", None)}


def load_configs(config_dir: Path) -> tuple[dict, list[str]]:
    configs, reasons = {}, []
    for key, (name, field) in _CONFIGS.items():
        try:
            data = strict_loads((config_dir / name).read_text(encoding="utf-8"))
            configs[key] = data[field] if field else data
            if not isinstance(configs[key], dict):
                raise TypeError
        except (OSError, ValueError, KeyError, TypeError):
            configs[key] = {}
            reasons.append(f"CONFIG_INVALID: {name}")
    return configs, reasons


def default_engine(request: dict, ephe_path: str | None) -> dict:
    from sabpuja_kundali.engine import calculate
    return calculate(dict(request), ephe_path=ephe_path)


def _utc(clock) -> str:
    return clock().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frozen(fixture: dict, tolerances: dict) -> dict:
    return {q: tolerances[t]["frozen_arcsec"] for q, t in fixture["tolerance_ids"].items()}


def run_golden(fixtures_dir: Path, ephe_path: str | None, *, golden_dir: Path = GOLDEN_DIR,
               repo_root: Path = REPO_ROOT, engine_fn=default_engine, env: dict | None = None,
               clock=lambda: datetime.now(timezone.utc)) -> dict:
    started = _utc(clock)
    env = env if env is not None else capture_environment(repo_root, ephe_path)
    run_reasons = environment_reasons(env)
    manifest, manifest_reasons = check_manifest(golden_dir / MANIFEST_NAME, repo_root)
    run_reasons += manifest_reasons
    run_reasons += [f"GENERATOR_NOT_ISOLATED: {v}" for v in scan_directory(golden_dir / "generator")]
    configs, config_reasons = load_configs(golden_dir / "config")
    run_reasons += config_reasons
    run_reasons += gates.time_track_reasons(configs["time_track"])
    records, per_file, set_errors = load_fixture_set(fixtures_dir)
    run_reasons += [f"FIXTURE_NOT_INDEXED: {e}" for e in set_errors]
    if not records:
        run_reasons.append("NO_FIXTURES")

    fixtures, checks, self_checks = [], [], []
    for record in records:
        fixture = record["fixture"]
        valid = fixture is not None and not any(e.startswith("SCHEMA_INVALID") for e in per_file[record["file"]])
        entry = {"file": record["file"], "sha256": record["sha256"],
                 "fixture_id": fixture.get("fixture_id") if isinstance(fixture, dict) else None,
                 "revision": fixture.get("fixture_revision") if isinstance(fixture, dict) else None,
                 "dummy": fixture.get("dummy") if isinstance(fixture, dict) else None,
                 "reasons": list(per_file[record["file"]]), "method_mismatches": [],
                 "engine_called": False, "engine_method_block": None, "outcome": None}
        fixtures.append(entry)
        if valid:
            entry["reasons"] += gates.fixture_reasons(fixture, fixtures_dir, configs, env["tzdata"]["version"])
            if manifest is not None:
                entry["method_mismatches"] = signature_mismatches(fixture["method_signature"], manifest)
        if entry["reasons"] or run_reasons or manifest is None:
            entry["outcome"] = Outcome.BLOCKED.value
            continue
        if entry["method_mismatches"]:
            entry["outcome"] = Outcome.METHOD_MISMATCH.value
            continue
        entry["engine_called"] = True
        try:
            output = engine_fn(fixture["input"], ephe_path)
        except Exception as exc:  # recorded as a code; messages may not be logged
            entry["reasons"].append(f"ENGINE_ERROR: {getattr(exc, 'code', type(exc).__name__)}")
            entry["outcome"] = Outcome.BLOCKED.value
            continue
        entry["engine_method_block"] = output.get("method")
        contradictions = emitted_block_contradictions(output.get("method"), manifest)
        if contradictions:
            entry["method_mismatches"] = [f"emitted method block: {k}" for k in contradictions]
            entry["outcome"] = Outcome.METHOD_MISMATCH.value
            continue
        qualification = gates.time_qualification(
            fixture["derived_time"]["utc"], configs["time_track"]["observed_delta_t_through_utc"])
        try:
            fixture_checks = compare.compare_fixture(
                fixture, output, _frozen(fixture, configs["tolerances"]), qualification)
            self_check = compare.ketu_identity(fixture["fixture_id"], output)
        except (KeyError, TypeError, ValueError):
            entry["reasons"].append("ENGINE_OUTPUT_MALFORMED")
            entry["outcome"] = Outcome.BLOCKED.value
            continue
        checks += fixture_checks
        self_checks.append(self_check)
        entry["outcome"] = fixture_outcome([Outcome(c["outcome"]) for c in fixture_checks]).value

    verdict = overall_verdict([Outcome(f["outcome"]) for f in fixtures])
    if run_reasons:
        verdict = overall_verdict([*(Outcome(f["outcome"]) for f in fixtures), Outcome.BLOCKED])
    demo = any(f["dummy"] is not False for f in fixtures)
    return {
        "report_schema": REPORT_SCHEMA,
        "banner": DEMO_BANNER if demo else None,
        "started_utc": started,
        "finished_utc": _utc(clock),
        "environment": env,
        "method_manifest": None if manifest is None else {
            "inspected_commit": manifest["inspected_commit"], "status": manifest["status"],
            "qa_review": manifest["qa_review"]},
        "fixture_set": fixtures_dir.name,
        "run_reasons": run_reasons,
        "fixtures": fixtures,
        "checks": checks,
        "self_consistency": self_checks,
        "verdict": verdict.value,
        "exit_code": exit_code(verdict),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Golden-chart QA harness (WP1 skeleton)")
    parser.add_argument("--fixtures", type=Path, default=GOLDEN_DIR / "tests" / "fixtures_dummy")
    parser.add_argument("--ephe", default=os.environ.get("SABPUJA_EPHE_PATH"))
    parser.add_argument("--report-dir", type=Path, default=REPO_ROOT / "reports")
    args = parser.parse_args(argv)
    data = run_golden(args.fixtures, args.ephe)
    json_path, md_path = write_reports(data, args.report_dir)
    print(to_markdown(data))
    print(f"Reports: {json_path.name}, {md_path.name}")
    return data["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
