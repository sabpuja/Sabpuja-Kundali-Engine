"""CLI: python -m tests.kun02.run --ephe DIR --report-dir DIR

Runs every KUN-02 probe, checks the predeclared invariants and writes a JSON
report plus a Markdown summary. Exit 0 KUN02-EVIDENCE PASS, 1 FAIL, 2 BLOCKED
(no verified pinned data, or a dirty Git tree).
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import sys

from sabpuja_kundali.ephemeris import EphemerisDataError

from . import envelope_probe, lagna_probe, provenance, time_probe
from .common import DATA_ENV, REPO_ROOT, ephe_dir

POLAR_BAND = "[polar circle, 89)"


def invariants(report: dict) -> list[dict]:
    """Predeclared pass conditions; each names the evidence it reads."""
    a, b, c = report["lagna"], report["time"], report["envelope"]
    checks = []

    def check(cid, text, ok):
        checks.append({"id": cid, "claim": text, "pass": bool(ok)})

    samples = [a["structured_grid"], a["random_within_66"], a["random_66_to_89"]]
    bands = [(name, v) for s in samples for name, v in s["by_band"].items()]
    check("A1", "Where b\"P\" returns, its ascendant equals b\"W\" bit for bit (and MC, ARMC)",
          all(v["p_w_bitwise_equal"] == v["samples"] - v["p_refused"] and v["p_w_max_abs_arcsec"] == 0.0
              and v["mc_armc_equal"] == v["samples"] - v["p_refused"] for _, v in bands))
    check("A2", "b\"W\" never refuses, including beyond the polar circle",
          all(v["w_refused"] == 0 for _, v in bands))
    check("A3", "b\"P\" refuses on every sample at or beyond the polar circle and on none equatorward of it",
          all((v["p_refused"] == v["samples"]) if n == POLAR_BAND else (v["p_refused"] == 0) for n, v in bands))
    check("A4", "b\"P\" failure latitude equals 90 deg minus true obliquity (within 1e-6 arcsec)",
          all(abs(r["north_minus_polar_arcsec"]) < 1e-6 and abs(r["south_minus_polar_arcsec"]) < 1e-6
              for r in a["placidus_threshold"]["per_date"]))
    check("A5", "Sidereal ascendant = tropical ascendant - true Lahiri ayanamsha (within 1e-6 arcsec)",
          all(v["lahiri_max_abs_arcsec"] < 1e-6 for _, v in bands))
    check("A6", "Independent spherical-trigonometry ascendant agrees within 1e-3 arcsec; same point equatorward of the polar circle",
          all(v["independent_max_abs_arcsec"] < 1e-3 for _, v in bands)
          and all(v["independent_opposite"] == 0 for n, v in bands if n != POLAR_BAND))
    check("A7", "b\"W\" ascendant is always on the eastern (rising) horizon, |altitude| < 1e-6 arcsec",
          all(v["not_rising"] == 0 and v["max_abs_altitude_arcsec"] < 1e-6 for _, v in bands))
    check("A8", "b\"W\" cusps are exact multiples of 30 deg from the Lagna Rashi",
          all(v["w_cusp_failures"] == 0 for _, v in bands))
    check("A9", "Navamsa-boundary sweep: every Lagna D9 crossing is consistent on both sides",
          all(not r["failures"] and r["navamsa_crossings"] >= 108 for r in a["boundary_sweep"]["per_location"]))
    check("A10", "D1/D9 houses from rules, W cusps and the classical Navamsa rule agree; P and W categories agree",
          a["chart_consistency"]["mismatches"] == 0 and a["chart_consistency"]["checks"] > 0)
    w = a["wrong_configurations"]["minus_reference_arcsec"]
    check("A11", "Wrong configurations are detectable: unset mode, missing flag, NONUT, KP and PREC_ORIG leak differ; empty ephe dir does not",
          abs(w["sid_mode_never_set"]) > 1000 and abs(w["lahiri_flag_missing"]) > 80000
          and 0 < abs(w["lahiri_nonut"]) < 20 and abs(w["krishnamurti"]) > 100
          and w["lahiri_empty_ephe_dir"] == 0.0 and w["lahiri_after_prec_orig_mode_reset_only"] != 0.0
          and w["lahiri_after_path_and_mode_reset"] == 0.0)
    eng = a["engine_cases"]["cases"]
    check("A12", "Engine Lagna equals the b\"W\" value (display, Rashi, D9, houses); polar case refused today",
          all((r["p_asc"] is None and r["engine"].get("refused") == "ASCENDANT_UNCOMPUTABLE")
              or (r["p_asc"] is not None and all(v for k, v in r["engine"].items() if k != "lagna_display"))
              for r in eng))
    check("B1", "Every synthetic time case behaves as derived by hand from IANA/Python rules",
          b["engine_time_cases"]["all_match"]
          and all(r.get("engine_utc_matches_parser", True) for r in b["engine_time_cases"]["cases"]))
    check("B2", "zoneinfo offsets equal the independent IANA 2026e transcription for 7 South Asian zones",
          all(z["mismatch_count"] == 0 for z in b["iana_crosscheck"]["zones"]))
    ts = b["timescale"]
    check("B3", "Swiss leap seconds equal the IERS list and Swiss Delta T keeps |UT1-UTC| < 0.9 s for 1972-2026",
          ts["iers_consistency_1972_2026"]["all_within_0_9_s"]
          and ts["swiss_leap_seconds"]["swiss_accepts_23_59_60"] == ts["swiss_leap_seconds"]["iers_leap_dates"]
          and all(r["swiss"] == "refused" for r in ts["swiss_leap_seconds"]["non_leap_dates"]))
    check("C1", "All bodies use Swiss files at both UTC extremes of the 1900-2100 local-date window",
          all(r["all_bodies_swiss_files"] for r in c["ephemeris_coverage"]["rows"][:4]))
    return checks


def run_all(ephe: str | None) -> dict:
    started = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    try:
        folder = ephe_dir(ephe)
    except EphemerisDataError as exc:
        prov = provenance.collect(None)
        return {"verdict": "BLOCKED", "exit_code": 2, "reason": str(exc), "provenance": prov, "started": started}
    prov = provenance.collect(folder)
    report = {"started": started, "provenance": prov,
              "lagna": lagna_probe.run(folder), "time": time_probe.run(folder),
              "envelope": envelope_probe.run(folder)}
    report["invariants"] = invariants(report)
    failed = [c["id"] for c in report["invariants"] if not c["pass"]]
    if failed:
        report.update(verdict="FAIL", exit_code=1, reason="failed: " + ", ".join(failed))
    elif not prov["git"]["clean"]:
        report.update(verdict="BLOCKED", exit_code=2, reason="git tree is dirty")
    else:
        report.update(verdict="PASS", exit_code=0, reason="all invariants hold")
    return report


def to_markdown(report: dict) -> str:
    p = report["provenance"]
    lines = [f"# KUN-02 evidence run: {report['verdict']}", "",
             f"- Reason: {report['reason']}",
             f"- Git HEAD: `{p['git']['head']}` ({p['git']['branch']}), clean: {p['git']['clean']}",
             f"- Python {p['python']['version']}, pyswisseph {p['swiss']['pyswisseph']}, Swiss {p['swiss']['swe_version']}",
             f"- tzdata in use: {p['tz'].get('source')} {p['tz'].get('version', '')} "
             f"(package: {(p['tz'].get('tzdata_package') or {}).get('iana_version')})",
             "- Ephemeris files: " + ", ".join(
                 f"{f['name']} {f.get('actual_sha256', 'absent')[:16]} match={f.get('match')}"
                 for f in p["ephemeris"]["files"]),
             ""]
    if "invariants" in report:
        lines += ["| Check | Claim | Result |", "|---|---|---|"]
        lines += [f"| {c['id']} | {c['claim'].replace('|', chr(92) + '|')} | {'PASS' if c['pass'] else 'FAIL'} |" for c in report["invariants"]]
    return "\n".join(lines) + "\n"


def write_reports(report: dict, out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"kun02-evidence-{report['provenance']['git']['head'][:12]}-{report['started']}"
    json_path, md_path = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=1, sort_keys=True, default=str) + "\n", encoding="utf-8")
    md_path.write_text(to_markdown(report), encoding="utf-8")
    return [json_path, md_path]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="KUN-02 Lagna, birth-time and envelope evidence")
    parser.add_argument("--ephe", default=os.environ.get(DATA_ENV) or os.environ.get("SABPUJA_EPHE_PATH"))
    parser.add_argument("--report-dir", type=Path, default=REPO_ROOT / "reports")
    args = parser.parse_args(argv)
    report = run_all(args.ephe)
    paths = write_reports(report, args.report_dir)
    print(to_markdown(report))
    print("Reports: " + ", ".join(p.name for p in paths))
    return report["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
