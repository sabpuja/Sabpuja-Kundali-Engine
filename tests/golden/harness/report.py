"""Deterministic JSON and Markdown golden reports.

The JSON is the record; the Markdown is derived from the same data. Same
input and same clock give byte-identical files. Fixture birth inputs are
never written.
"""
from __future__ import annotations

from pathlib import Path
import json

NOT_VALIDATION = ("This run is not astronomical validation. The engine may be called validated only "
                  "after an overall PASS on QA-approved, non-dummy golden fixtures.")


def to_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, indent=2, ensure_ascii=False, allow_nan=False) + "\n"


def _cell(value) -> str:
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\n", " ")


def to_markdown(data: dict) -> str:
    env = data["environment"]
    lines = []
    if data["banner"]:
        lines += [f"# {data['banner']}", ""]
    lines += [
        "## Golden-chart run report", "",
        f"- Verdict: **{data['verdict']}** (exit code {data['exit_code']})",
        f"- Commit: `{env['git']['commit']}` dirty={env['git']['dirty']}",
        f"- Started / finished (UTC): {data['started_utc']} / {data['finished_utc']}",
        f"- Python {env['python']} ({env['implementation']}, {env['platform']}); "
        f"pyswisseph {env['swiss']['pyswisseph']}; Swiss {env['swiss']['swiss_library']}",
        f"- tzdata {env['tzdata']['version']} ({env['tzdata']['source']})",
        f"- Ephemeris manifest {env['ephemeris']['manifest_version']} @ `{env['ephemeris']['source_commit']}`, "
        f"verified={env['ephemeris']['verified']} {env['ephemeris']['error_code'] or ''}".rstrip(),
    ]
    for name, sha in sorted(env["ephemeris"]["files"].items()):
        lines.append(f"  - `{name}` sha256 `{sha}`")
    manifest = data["method_manifest"]
    if manifest:
        lines.append(f"- Method manifest: inspected `{manifest['inspected_commit']}`, status {manifest['status']}, "
                     f"QA review {manifest['qa_review']}")
    else:
        lines.append("- Method manifest: not loaded")
    lines += ["", "### Run-level blocking reasons", ""]
    lines += [f"- {r}" for r in data["run_reasons"]] or ["- none"]
    lines += ["", "### Fixtures", "", "| File | Fixture | Rev | SHA-256 | Dummy | Outcome | Engine called | Reasons |",
              "|---|---|---|---|---|---|---|---|"]
    for fx in data["fixtures"]:
        lines.append("| " + " | ".join(_cell(v) for v in (
            fx["file"], fx["fixture_id"], fx["revision"], fx["sha256"], fx["dummy"], fx["outcome"],
            fx["engine_called"], "; ".join(fx["reasons"] + [f"METHOD: {k}" for k in fx["method_mismatches"]]))) + " |")
    lines += ["", "### Independent checks", ""]
    if data["checks"]:
        lines += ["| Fixture | Quantity | Body | Engine deg | Reference deg | Diff arcsec | Tol arcsec | Boundary arcsec | Outcome | Reason |",
                  "|---|---|---|---|---|---|---|---|---|---|"]
        for c in data["checks"]:
            lines.append("| " + " | ".join(_cell(c.get(k)) for k in (
                "fixture_id", "quantity", "body", "engine_deg", "reference_deg", "diff_arcsec",
                "tolerance_arcsec", "boundary_distance_arcsec", "outcome", "reason")) + " |")
    else:
        lines.append("None: no fixture passed its gates, so the engine was not compared.")
    lines += ["", "### Self-consistency (not counted toward validation)", ""]
    lines += [f"- {s['fixture_id']}: {s['check']} diff {s['diff_arcsec']}\" -> {s['result']}"
              for s in data["self_consistency"]] or ["- none run"]
    lines += ["", f"_{NOT_VALIDATION}_", ""]
    return "\n".join(lines)


def write_reports(data: dict, report_dir: Path) -> tuple[Path, Path]:
    commit = (data["environment"]["git"]["commit"] or "nogit")[:12]
    stamp = data["started_utc"].replace("-", "").replace(":", "")
    report_dir.mkdir(parents=True, exist_ok=True)
    base = report_dir / f"golden-report-{commit}-{stamp}"
    json_path, md_path = base.with_suffix(".json"), base.with_suffix(".md")
    json_path.write_text(to_json(data), encoding="utf-8")
    md_path.write_text(to_markdown(data), encoding="utf-8")
    return json_path, md_path
