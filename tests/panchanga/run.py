"""KUN-PAN-M1 numerical gate runner: PAN-QA-04 (50 phase events) and PAN-QA-07 (full swetest set).

    python -m tests.panchanga.run --report-dir reports/

Writes panchanga-gate-<sha12>-<UTC>.json and .md. Exit codes: 0 both gates PASS
on a clean tree with verified inputs; 1 any FAIL; 2 BLOCKED (missing or unverified
input, dirty tree) or BOUNDARY-INDETERMINATE. Errors are reported as codes only.
Swiss-on-Swiss rows are implementation conformance, not independent astronomy.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys

from .common import FIXTURE_PATH, FIXTURE_SHA256, PinnedInputError, TOLERANCES_PATH, TOLERANCES_SHA256

REPO = Path(__file__).resolve().parents[2]


def _git(*args) -> str:
    try:
        return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _sha(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ephe", default=os.environ.get("SABPUJA_TEST_EPHE_PATH"))
    ap.add_argument("--swetest", default=os.environ.get("SABPUJA_TEST_SWETEST"))
    ap.add_argument("--receipt", default=os.environ.get("SABPUJA_TEST_SWETEST_RECEIPT"))
    ap.add_argument("--report-dir", type=Path, default=REPO / "reports")
    args = ap.parse_args(argv)
    head, tree = _git("rev-parse", "HEAD"), _git("rev-parse", "HEAD^{tree}")
    dirty = bool(_git("status", "--porcelain", "--untracked-files=no"))
    blocked = []
    if os.environ.get("SE_EPHE_PATH"):
        blocked.append("SE_EPHE_PATH_SET")
    if dirty:
        blocked.append("DIRTY_TREE")
    if _sha(TOLERANCES_PATH) != TOLERANCES_SHA256:
        blocked.append("TOLERANCES_HASH_MISMATCH")
    if _sha(FIXTURE_PATH) != FIXTURE_SHA256:
        blocked.append("FIXTURE_HASH_MISMATCH")
    versions = {}
    try:
        from sabpuja_kundali import engine
        from sabpuja_kundali.ephemeris import EphemerisDataError, verify_ephemeris_dir
        swe = engine.swiss_runtime()
        versions = {"swiss_library": swe.version, "binding": engine.REQUIRED_BINDING_VERSION}
        verify_ephemeris_dir(args.ephe)
    except Exception as exc:  # reported as a code, never a traceback
        blocked.append(f"ENVIRONMENT:{getattr(exc, 'code', type(exc).__name__)}")
    gates = {}
    if not any(b.startswith(("ENVIRONMENT", "TOLERANCES", "FIXTURE")) for b in blocked):
        from . import phase_events, swiss_conformance
        try:
            gates["PAN-QA-04"] = phase_events.evaluate(args.ephe)
        except PinnedInputError:
            blocked.append("PAN-QA-04:PINNED_INPUT")
        try:
            gates["PAN-QA-07"] = swiss_conformance.evaluate(args.ephe, args.swetest, args.receipt)
        except swiss_conformance.ReferenceBlocked as exc:
            blocked.append(f"PAN-QA-07:{exc.code}")
    verdicts = {k: v["verdict"] for k, v in gates.items()}
    if any("FAIL" in v for v in verdicts.values()):
        overall, code = "FAIL", 1
    elif blocked or len(gates) != 2 or any("BOUNDARY" in v or "BLOCKED" in v for v in verdicts.values()):
        overall, code = "BLOCKED", 2
    else:
        overall, code = "PASS", 0
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report = {
        "runner": "KUN-PAN-M1 numerical gate", "overall": overall, "exit_code": code, "verdicts": verdicts,
        "blocked_reasons": blocked, "commit": head, "tree": tree, "dirty": dirty, "generated_utc": stamp,
        "python": platform.python_version(), "platform": platform.platform(terse=True), "versions": versions,
        "inputs": {"tolerances.json": {"sha256": _sha(TOLERANCES_PATH), "frozen": TOLERANCES_SHA256},
                   "phase_fixture": {"sha256": _sha(FIXTURE_PATH), "frozen": FIXTURE_SHA256}},
        "claim_boundary": "PAN-QA-04: agreement with publisher-printed whole minutes inside the frozen D15-a "
                          "window only. PAN-QA-07: Swiss-on-Swiss implementation conformance, not independent "
                          "astronomical accuracy. Yoga and Nakshatra end times have no external reference.",
        "gates": gates,
    }
    args.report_dir.mkdir(parents=True, exist_ok=True)
    base = args.report_dir / f"panchanga-gate-{head[:12] or 'nogit'}-{stamp}"
    base.with_suffix(".json").write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    lines = [f"# KUN-PAN-M1 numerical gate: {overall} (exit {code})", "",
             f"- Commit `{head}` tree `{tree}` dirty={dirty}",
             f"- Python {report['python']}; Swiss {versions.get('swiss_library')}; binding {versions.get('binding')}",
             f"- tolerances.json `{report['inputs']['tolerances.json']['sha256']}`",
             f"- phase fixture `{report['inputs']['phase_fixture']['sha256']}`",
             f"- Blocked reasons: {blocked or 'none'}", "", f"_{report['claim_boundary']}_", ""]
    q4 = gates.get("PAN-QA-04")
    if q4:
        lines += [f"## PAN-QA-04: {q4['verdict']} ({q4['counts']}, {q4['case_count']}/{q4['expected_case_count']})", "",
                  f"NEAR_WINDOW_EDGE (<= 10 s): {q4['near_window_edge_cases'] or 'none'}", "",
                  "| Case | Phase | Published (UT) | Window | Engine UTC | Resid. vs earliest s | Margin s | Status |",
                  "|---|---|---|---|---|---|---|---|"]
        for r in q4["rows"]:
            lines.append(f"| {r['case_id']} | {r['phase']} | {', '.join(r['published_minutes_utc'])} | "
                         f"{r['window_utc'][0]} .. {r['window_utc'][1]} | {r['engine_utc']} | "
                         f"{r['residual_vs_earliest_minute_s']:+.0f} | {r['margin_to_window_edge_s']:.0f} | "
                         f"{r['status']}{' ' + ','.join(r['problems']) if r['problems'] else ''} |")
        res = [r["residual_vs_earliest_minute_s"] for r in q4["rows"]]
        lines += ["", f"Residual vs earliest published minute: min {min(res):+.0f} s, max {max(res):+.0f} s; "
                  f"smallest margin to a window edge {min(r['margin_to_window_edge_s'] for r in q4['rows']):.0f} s.", ""]
    q7 = gates.get("PAN-QA-07")
    if q7:
        lines += [f"## PAN-QA-07: {q7['verdict']}", "",
                  f"- Instants {q7['instants']}; checks {q7['checks']}; failed {q7['checks_failed']}; "
                  f"transition checks {q7['transition_checks']}, whole second identical to the oracle "
                  f"{q7['transition_whole_second_identical']}",
                  f"- swetest `{q7['swetest_sha256']}` ({q7['swetest_source']}), {q7['swetest_calls']} calls",
                  f"- Worst differences: {json.dumps(q7['worst'])}", "",
                  "| Instant | Status | Failed checks |", "|---|---|---|"]
        for r in q7["rows"]:
            bad = [c["check"] for c in r["checks"] if c["status"] != "PASS"]
            lines.append(f"| {r['instant_id']} | {r['status']} | {', '.join(bad)} |")
    base.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:12]))
    print(f"\nReports: {base.name}.json, {base.name}.md")
    return code


if __name__ == "__main__":
    sys.exit(main())
