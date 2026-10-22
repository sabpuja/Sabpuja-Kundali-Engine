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
from .common import DATA_ENV, REPO_ROOT, ephe_dir, load_fixture

POLAR_BAND = "[polar circle, 89)"
ENGINE_FIELDS = {"lagna_display", "display_equals_w", "rashi_equals_w", "navamsa_equals_w", "all_houses_equal_w"}
COVERAGE_PREFIXES = ("earliest UTC of local window", "latest UTC of local window", "1800-06-01", "2399-06-01")
IERS_SAMPLES_1972_2026 = 2 * (2026 - 1972 + 1)  # 1 January and 1 July of each year


class MissingEvidence(Exception):
    """A probe section is empty, partial or does not match the predeclared fixture."""


def require(ok: bool, what: str) -> None:
    if not ok:
        raise MissingEvidence(what)


def expected_counts() -> dict:
    """Sample sizes and IDs fixed by the fixtures; a PASS must cover all of them."""
    grid = load_fixture("lagna_grid.json")
    s = grid["structured_instants"]
    return {
        "structured_points": len(grid["locations"]) * len(s["years"]) * len(s["months"])
        * len(s["days"]) * len(s["hours_utc"]),
        "random_within_66": grid["random_sample"]["count"],
        "random_66_to_89": grid["random_polar_sample"]["count"],
        "threshold_dates": [f"{y:04d}-{m:02d}-{d:02d}T12:00Z" for y, m, d in grid["threshold_dates"]],
        "sweep_locations": list(grid["boundary_sweep"]["locations"]),
        "sweep_segments": grid["boundary_sweep"]["segments"],
        "engine_case_ids": [c["id"] for c in grid["engine_cases"]],
        "time_case_ids": [c["id"] for c in load_fixture("time_cases.json")["cases"]],
        "iana_zones": [z["key"] for z in load_fixture("iana_zone_transcriptions.json")["zones"]],
        "iers_leap_dates": len(load_fixture("iers_leap_seconds.json")["entries"]) - 1,
    }


def _engine_row_ok(r: dict) -> bool:
    """A predeclared engine case: exact refusal when Placidus refuses, otherwise a full chart equal to W."""
    e = r["engine"]
    if r["p_asc"] is None:
        return e == {"refused": "ASCENDANT_UNCOMPUTABLE"}
    if set(e) != ENGINE_FIELDS or not isinstance(e["lagna_display"], float):
        return False
    return all(e[k] is True for k in ENGINE_FIELDS - {"lagna_display"})


def invariants(report: dict) -> list[dict]:
    """Predeclared pass conditions; each names the evidence it reads.

    Every condition first checks that its evidence is complete against the
    fixtures (expected IDs and sample counts), so an empty or partial probe
    section fails instead of passing vacuously.
    """
    exp = expected_counts()
    checks = []

    def check(cid, text, predicate):
        try:
            ok, basis = bool(predicate()), ""
        except (MissingEvidence, KeyError, TypeError, IndexError) as exc:
            ok, basis = False, f"incomplete evidence: {exc!r}"
        checks.append({"id": cid, "claim": text, "pass": ok, **({"basis": basis} if basis else {})})

    def sections():
        a = report["lagna"]
        samples = {"structured_grid": exp["structured_points"], "random_within_66": exp["random_within_66"],
                   "random_66_to_89": exp["random_66_to_89"]}
        for name, n in samples.items():
            s = a[name]
            require(s["points"] == n and sum(v["samples"] for v in s["by_band"].values()) == n,
                    f"{name}: expected {n} points")
        return [a[name] for name in samples]

    def bands():
        out = [(n, v) for s in sections() for n, v in s["by_band"].items()]
        require(any(n == POLAR_BAND for n, _ in out) and any(n != POLAR_BAND for n, _ in out),
                "both polar and equatorward bands must be sampled")
        compared = sum(v["samples"] - v["p_refused"] for _, v in out)
        require(compared > 0, "no point where b\"P\" returned")
        return out

    def a1():
        return all(v["p_w_bitwise_equal"] == v["samples"] - v["p_refused"] and v["p_w_max_abs_arcsec"] == 0.0
                   and v["mc_armc_equal"] == v["samples"] - v["p_refused"] for _, v in bands())

    def a4():
        rows = report["lagna"]["placidus_threshold"]["per_date"]
        require([r["date_utc"] for r in rows] == exp["threshold_dates"], "threshold dates differ from fixture")
        return all(abs(r["north_minus_polar_arcsec"]) < 1e-6 and abs(r["south_minus_polar_arcsec"]) < 1e-6
                   for r in rows)

    def a9():
        rows = report["lagna"]["boundary_sweep"]["per_location"]
        require([r["location"] for r in rows] == exp["sweep_locations"], "sweep locations differ from fixture")
        return all(not r["failures"] and r["navamsa_crossings"] >= exp["sweep_segments"] for r in rows)

    def a11():
        w = report["lagna"]["wrong_configurations"]["minus_reference_arcsec"]
        return (abs(w["sid_mode_never_set"]) > 1000 and abs(w["lahiri_flag_missing"]) > 80000
                and 0 < abs(w["lahiri_nonut"]) < 20 and abs(w["krishnamurti"]) > 100
                and w["lahiri_empty_ephe_dir"] == 0.0 and w["lahiri_after_prec_orig_mode_reset_only"] != 0.0
                and w["lahiri_after_path_and_mode_reset"] == 0.0)

    def a12():
        eng = report["lagna"]["engine_cases"]["cases"]
        require([r["id"] for r in eng] == exp["engine_case_ids"], "engine cases differ from fixture")
        require(any(r["p_asc"] is None for r in eng) and any(r["p_asc"] is not None for r in eng),
                "need both a refused and an accepted engine case")
        return all(_engine_row_ok(r) for r in eng)

    def b1():
        t = report["time"]["engine_time_cases"]
        require([r["id"] for r in t["cases"]] == exp["time_case_ids"], "time cases differ from fixture")
        accepted = [r for r in t["cases"] if r["actual"] == "ACCEPT"]
        require(accepted, "no accepted time case")
        return (t["all_match"] and all(r["matches_expectation"] for r in t["cases"])
                and all(r["engine_utc_matches_parser"] is True for r in accepted))

    def b2():
        zones = report["time"]["iana_crosscheck"]["zones"]
        require([z["zone"] for z in zones] == exp["iana_zones"], "zones differ from fixture")
        require(all(z["probes"] > 0 for z in zones), "a zone has no probe instants")
        return all(z["mismatch_count"] == 0 for z in zones)

    def b3():
        ts = report["time"]["timescale"]
        ic, ls = ts["iers_consistency_1972_2026"], ts["swiss_leap_seconds"]
        require(ic["samples"] == IERS_SAMPLES_1972_2026, f"expected {IERS_SAMPLES_1972_2026} samples")
        require(ls["iers_leap_dates"] == exp["iers_leap_dates"] > 0, "leap-second list incomplete")
        require(len(ls["non_leap_dates"]) == 4, "expected 4 non-leap control dates")
        return (ic["all_within_0_9_s"] and ls["swiss_accepts_23_59_60"] == ls["iers_leap_dates"]
                and not ls["swiss_refuses_iers_leap"]
                and all(r["swiss"] == "refused" for r in ls["non_leap_dates"]))

    def c1():
        rows = report["envelope"]["ephemeris_coverage"]["rows"]
        inside = [next((r for r in rows if r["instant"].startswith(p)), None) for p in COVERAGE_PREFIXES]
        outside = [r for r in rows if r["instant"].endswith("(outside data)")]
        require(all(inside) and len(outside) == 2, "coverage instants missing")
        return all(r["all_bodies_swiss_files"] for r in inside) and not any(r["all_bodies_swiss_files"] for r in outside)

    check("A1", "Where b\"P\" returns, its ascendant equals b\"W\" bit for bit (and MC, ARMC)", a1)
    check("A2", "b\"W\" never refuses, including beyond the polar circle",
          lambda: all(v["w_refused"] == 0 for _, v in bands()))
    check("A3", "b\"P\" refuses on every sample at or beyond the polar circle and on none equatorward of it",
          lambda: all((v["p_refused"] == v["samples"]) if n == POLAR_BAND else (v["p_refused"] == 0)
                      for n, v in bands()))
    check("A4", "b\"P\" failure latitude equals 90 deg minus true obliquity (within 1e-6 arcsec) on every fixture date", a4)
    check("A5", "Sidereal ascendant = tropical ascendant - true Lahiri ayanamsha (within 1e-6 arcsec)",
          lambda: all(v["lahiri_max_abs_arcsec"] < 1e-6 for _, v in bands()))
    check("A6", "Independent spherical-trigonometry ascendant agrees within 1e-3 arcsec; same point equatorward of the polar circle",
          lambda: all(v["independent_max_abs_arcsec"] < 1e-3 for _, v in bands())
          and all(v["independent_opposite"] == 0 for n, v in bands() if n != POLAR_BAND))
    check("A7", "b\"W\" ascendant is always on the eastern (rising) horizon, |altitude| < 1e-6 arcsec",
          lambda: all(v["not_rising"] == 0 and v["max_abs_altitude_arcsec"] < 1e-6 for _, v in bands()))
    check("A8", "b\"W\" cusps are exact multiples of 30 deg from the Lagna Rashi",
          lambda: all(v["w_cusp_failures"] == 0 for _, v in bands()))
    check("A9", "Navamsa-boundary sweep at every fixture location: every Lagna D9 crossing is consistent on both sides", a9)
    check("A10", "D1/D9 houses from rules, W cusps and the classical Navamsa rule agree; P and W categories agree",
          lambda: report["lagna"]["chart_consistency"]["checks"] > 0
          and report["lagna"]["chart_consistency"]["mismatches"] == 0)
    check("A11", "Wrong configurations are detectable: unset mode, missing flag, NONUT, KP and PREC_ORIG leak differ; empty ephe dir does not", a11)
    check("A12", "Every fixture engine case: a full chart with exactly the expected fields, Lagna display, Rashi, D9 and houses equal to b\"W\"; "
          "the polar case refused with ASCENDANT_UNCOMPUTABLE today", a12)
    check("B1", "Every fixture time case behaves as derived by hand from IANA/Python rules; accepted cases match the engine's UTC", b1)
    check("B2", "zoneinfo offsets equal the independent IANA 2026e transcription for every fixture zone", b2)
    check("B3", "Swiss leap seconds equal the IERS list; UT1-UTC implied under the Swiss Delta T model (with IERS TAI-UTC) "
          "stays within 0.9 s for 1972-2026 (model consistency, not measured UT1)", b3)
    check("C1", "All bodies use Swiss files at both UTC extremes of the 1900-2100 local-date window and at 1800/2399; "
          "fallback is detected outside the data", c1)
    return checks


def summary(report: dict) -> dict:
    """Headline counts that the reports quote, read from this run (not from the docs)."""
    a, b, c = report["lagna"], report["time"], report["envelope"]
    bands = [v for k in ("structured_grid", "random_within_66", "random_66_to_89") for v in a[k]["by_band"].values()]
    thr = a["placidus_threshold"]
    return {
        "lagna_points": sum(a[k]["points"] for k in ("structured_grid", "random_within_66", "random_66_to_89")),
        "p_w_compared": sum(v["samples"] - v["p_refused"] for v in bands),
        "p_w_bitwise_equal": sum(v["p_w_bitwise_equal"] for v in bands),
        "p_refused": sum(v["p_refused"] for v in bands),
        "w_refused": sum(v["w_refused"] for v in bands),
        "polar_circle_latitude_1900_2100": thr["polar_circle_latitude_1900_2100"],
        "threshold_max_abs_arcsec": max(max(abs(r["north_minus_polar_arcsec"]), abs(r["south_minus_polar_arcsec"]))
                                        for r in thr["per_date"]),
        "lahiri_max_abs_arcsec": max(v["lahiri_max_abs_arcsec"] for v in bands),
        "independent_max_abs_arcsec_equatorward": max(v["independent_max_abs_arcsec"] for k in
                                                      ("structured_grid", "random_within_66")
                                                      for n, v in a[k]["by_band"].items() if n != POLAR_BAND),
        "d1_d9_checks": a["chart_consistency"]["checks"], "d1_d9_mismatches": a["chart_consistency"]["mismatches"],
        "navamsa_crossings": {r["location"]: r["navamsa_crossings"] for r in a["boundary_sweep"]["per_location"]},
        "engine_cases": len(a["engine_cases"]["cases"]),
        "time_cases": len(b["engine_time_cases"]["cases"]),
        "iana_probe_instants": sum(z["probes"] for z in b["iana_crosscheck"]["zones"]),
        "iana_zones": len(b["iana_crosscheck"]["zones"]),
        "iers_leap_dates": b["timescale"]["swiss_leap_seconds"]["iers_leap_dates"],
        "implied_ut1_minus_utc_worst_s_swiss_model": b["timescale"]["iers_consistency_1972_2026"]["worst"],
        "coverage_rows": {r["instant"]: r["all_bodies_swiss_files"] for r in c["ephemeris_coverage"]["rows"]},
    }


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
    try:
        report["summary"] = summary(report)
    except (KeyError, TypeError, ValueError) as exc:
        report["summary"] = {"error": repr(exc)}
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
        esc = lambda text: text.replace("|", chr(92) + "|")
        lines += ["| Check | Claim | Result | Note |", "|---|---|---|---|"]
        lines += [f"| {c['id']} | {esc(c['claim'])} | {'PASS' if c['pass'] else 'FAIL'} | {esc(c.get('basis', ''))} |"
                  for c in report["invariants"]]
    if isinstance(report.get("summary"), dict):
        lines += ["", "## Measured counts (this run)", ""]
        lines += [f"- {k}: {json.dumps(v, sort_keys=True)}" for k, v in report["summary"].items()]
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
