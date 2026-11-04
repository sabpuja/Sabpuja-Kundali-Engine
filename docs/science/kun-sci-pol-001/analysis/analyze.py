"""KUN-SCI-POL-001 numerical analysis (documentation evidence only).

Reads PR #62's QA-passed golden-reference evidence read-only and derives the
statistics used by the B-1, B-3 and B-6 decision documents. It is not imported
by the engine, the tests or the report, changes no value and decides nothing.

    python -I analyze.py --pr62 /path/to/checkout-of-6722b5c --gold-report sci-gold-6722b5c46c3f.json \
        --ephe /path/to/verified/ephe --out results.json

Requires: pyswisseph 2.10.3.2 and the pinned .se1 files (B-6 time sensitivity
only), mpmath 1.3.0 (B-1 high-precision re-evaluation). All inputs synthetic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
import sys
from decimal import Decimal, ROUND_HALF_EVEN
from fractions import Fraction
from pathlib import Path

import mpmath as mp

PADA = Fraction(10, 3)              # 3 deg 20 min: every Rashi, Nakshatra and Navamsa edge is a Pada edge
SIDEREAL_RATE = 360.98564736629     # deg of ARMC per UT day (IAU 1982 GMST rate; Meeus 12.4), used only for rates
PRINT_HALF_DEC11 = 5e-12            # swetest -fPl prints 11 decimals
PRINT_HALF_AYAN = 0.5e-8 / 3600     # ayanamsa printed in DMS with 8 decimals of arcsecond
ENGINE_HALF = 5e-9                  # engine longitude_deg rounded to 8 decimals


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def quantiles(values):
    v = sorted(values)
    pick = lambda q: v[min(len(v) - 1, int(round(q * (len(v) - 1))))]
    return {"n": len(v), "min": v[0], "p25": pick(.25), "median": pick(.5), "p75": pick(.75), "p95": pick(.95),
            "p99": pick(.99), "max": v[-1], "mean": statistics.fmean(v), "stdev": statistics.pstdev(v)}


def edge_distance(lon: Fraction) -> Fraction:
    r = lon % PADA
    return min(r, PADA - r)


# ---------- B-1 Lagna formula ----------
def asc_mp(armc, eps, phi):
    r, e, p = (mp.radians(x) for x in (armc, eps, phi))
    return mp.degrees(mp.atan2(mp.cos(r), -(mp.sin(r) * mp.cos(e) + mp.tan(p) * mp.sin(e)))) % 360


def asc_partials(armc_deg, eps_deg, phi_deg):
    """Analytic dAsc/dARMC and dAsc/deps (dimensionless, deg per deg) in float64."""
    r, e, p = (math.radians(x) for x in (armc_deg, eps_deg, phi_deg))
    y, x = math.cos(r), -(math.sin(r) * math.cos(e) + math.tan(p) * math.sin(e))
    den = x * x + y * y
    dy_dr, dx_dr = -math.sin(r), -math.cos(r) * math.cos(e)
    dx_de = -(-math.sin(r) * math.sin(e) + math.tan(p) * math.cos(e))
    return (x * dy_dr - y * dx_dr) / den, (-y * dx_de) / den


def b1(pr62: Path, gold: dict, sr, asc_formula) -> dict:
    mp.mp.dps = 40
    matrix = {f["id"]: f for f in json.loads((pr62 / "tests/sci_gold/matrix.json").read_text())["fixtures"]}
    rows = []
    for res in gold["results"]:
        lf = next((l for l in res["layers"] if l["layer"] == "LAGNA-F"), None)
        if lf is None:
            continue
        ref = sr.parse((sr.RECEIPTS / f"{res['id']}.txt").read_text(encoding="utf-8"))
        lat = matrix[res["id"]]["input"]["latitude"]
        armc, eps, ayan, asc = mp.mpf(ref["armc"]), mp.mpf(ref["eps_true"]), mp.mpf(ref["ayanamsa"].numerator) / ref["ayanamsa"].denominator, mp.mpf(ref["ascendant"])
        hp = (asc_mp(armc, eps, mp.mpf(repr(lat))) - ayan) % 360
        fl = asc_formula.sidereal_ascendant(float(ref["armc"]), float(ref["eps_true"]), lat, float(ref["ayanamsa"]))
        d_hp = float(((hp - asc + 180) % 360) - 180)
        d_float = lf["difference_deg"]
        dr, de = asc_partials(float(ref["armc"]), float(ref["eps_true"]), lat)
        q_bound = abs(dr) * PRINT_HALF_DEC11 + abs(de) * PRINT_HALF_DEC11 + PRINT_HALF_AYAN + PRINT_HALF_DEC11
        rows.append({"id": res["id"], "lat": lat, "diff_float64_deg": d_float, "diff_highprec_deg": d_hp,
                     "float64_eval_error_deg": float(mp.mpf(repr(fl)) - hp), "dAsc_dARMC": dr, "dAsc_deps": de,
                     "input_quantisation_bound_deg": q_bound, "ratio_highprec_to_bound": abs(d_hp) / q_bound,
                     "lagna_rate_deg_per_s": dr * SIDEREAL_RATE / 86400})
    # supported-envelope sweep: worst amplification for |lat| <= 66.0 deg
    worst = {"dAsc_dARMC": 0.0, "dAsc_deps": 0.0}
    for i in range(0, 1441):
        a = i * 0.25
        for j in range(-132, 133):
            lat = j * 0.5
            for eps in (23.40, 23.45):
                dr, de = asc_partials(a, eps, lat)
                if abs(dr) > worst["dAsc_dARMC"]:
                    worst.update(dAsc_dARMC=abs(dr), at_armc=a, at_lat=lat)
                worst["dAsc_deps"] = max(worst["dAsc_deps"], abs(de))
    worst["quantisation_bound_deg"] = (worst["dAsc_dARMC"] + worst["dAsc_deps"]) * PRINT_HALF_DEC11 + PRINT_HALF_AYAN + PRINT_HALF_DEC11
    lagna_edges = []
    for res in gold["results"]:
        if res.get("edge_distance_deg"):
            lagna_edges.append({"id": res["id"], "lagna_edge_distance_deg": res["edge_distance_deg"]["lagna"]})
    return {"rows": rows,
            "abs_diff_float64": quantiles([abs(r["diff_float64_deg"]) for r in rows]),
            "abs_diff_highprec": quantiles([abs(r["diff_highprec_deg"]) for r in rows]),
            "abs_float64_eval_error": quantiles([abs(r["float64_eval_error_deg"]) for r in rows]),
            "ratio_highprec_to_bound": quantiles([r["ratio_highprec_to_bound"] for r in rows]),
            "input_quantisation_bound": quantiles([r["input_quantisation_bound_deg"] for r in rows]),
            "abs_dAsc_dARMC": quantiles([abs(r["dAsc_dARMC"]) for r in rows]),
            "envelope_worst_case": worst,
            "min_lagna_pada_edge_distance_deg": min(x["lagna_edge_distance_deg"] for x in lagna_edges)}


# ---------- B-3 Swiss tolerance applicability ----------
def b3(pr62: Path, gold: dict) -> dict:
    rows, not_round = [], []
    for res in gold["results"]:
        for l in res["layers"]:
            if l["layer"] != "SWISS":
                continue
            exp = Decimal(repr(l["expected"]))
            rounded = float(exp.quantize(Decimal("1e-8"), rounding=ROUND_HALF_EVEN))
            rows.append({"id": res["id"], "field": l["field"], "diff": l["difference_deg"], "tol": l["tolerance_deg"]})
            if l["actual"] != rounded:
                not_round.append({"id": res["id"], "field": l["field"], "expected": l["expected"], "actual": l["actual"]})
    by_body = {}
    for r in rows:
        by_body.setdefault(r["field"].split(".")[0], []).append(abs(r["diff"]))
    # boundary proximity of all reference longitudes (planets, nodes, Lagna)
    thresholds = [1e-12, 1e-11, 1e-10, 1e-9, 1e-8, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3]
    dists = []
    for res in gold["results"]:
        for body, d in (res.get("edge_distance_deg") or {}).items():
            dists.append((d, res["id"], body))
    near = {f"{t:g}": sorted({f"{i}:{b}" for d, i, b in dists if d < t}) for t in thresholds}
    nearest = [{"id": i, "body": b, "edge_distance_deg": d} for d, i, b in sorted(dists)[:5]]
    # coverage, original SC cases vs gold matrix
    cases = json.loads((pr62 / "tests/swiss_conformance/cases.json").read_text())["cases"]
    sc = [c for c in cases if c["expect"] == "chart"]
    gm = [f for f in json.loads((pr62 / "tests/sci_gold/matrix.json").read_text())["fixtures"] if f["expect"]["kind"] == "chart"]

    def cov(items, get):
        lats = [get(x)["latitude"] for x in items]
        years = [int(get(x)["birth_datetime"][:4]) for x in items]
        return {"n": len(items), "year_min": min(years), "year_max": max(years), "lat_min": min(lats), "lat_max": max(lats),
                "abs_lat_gt_60": sum(abs(v) > 60 for v in lats), "southern": sum(v < 0 for v in lats),
                "zones": len({get(x)["timezone"] for x in items})}
    return {"n_rows": len(rows), "abs_diff": quantiles([abs(r["diff"]) for r in rows]),
            "max_abs_diff_by_body": {k: max(v) for k, v in sorted(by_body.items())},
            "rows_where_engine_value_is_not_round8_of_swetest": not_round,
            "theoretical_max_from_rounding_deg": ENGINE_HALF + PRINT_HALF_DEC11,
            "max_ratio_to_tolerance": max(abs(r["diff"]) / r["tol"] for r in rows),
            "reference_longitudes_within_threshold_of_a_pada_edge": near,
            "n_reference_longitudes": len(dists), "five_nearest_to_an_edge": nearest,
            "coverage_sc_cases": cov(sc, lambda c: c["request"]),
            "coverage_gold_matrix": cov(gm, lambda f: f["input"])}


# ---------- B-6 birth-time sensitivity ----------
def b6(pr62: Path, gold: dict, ephe: str, samples: int, seed: int) -> dict:
    import swisseph as swe
    swe.set_ephe_path(ephe)
    swe.set_sid_mode(swe.SIDM_LAHIRI)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL

    def moon(jd):
        xx, rf = swe.calc_ut(jd, swe.MOON, flags)
        assert rf & swe.FLG_SWIEPH
        return xx[0]

    def lagna(jd, lat, lon):
        return swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)[1][0]

    cats = {"rashi": 30.0, "navamsa": 30.0 / 9, "nakshatra": 360.0 / 27, "pada": 360.0 / 108}

    def seconds_to_change(f, jd0, width, step_s, limit_s):
        """Smallest |dt| (s) at which floor(f/width) changes, by stepping then bisection; None beyond limit."""
        k0 = math.floor(f(jd0) / width)
        best = None
        for sign in (1, -1):
            t = 0.0
            while t < limit_s:
                t2 = t + step_s
                if math.floor(f(jd0 + sign * t2 / 86400) / width) != k0:
                    lo, hi = t, t2
                    for _ in range(40):
                        mid = (lo + hi) / 2
                        if math.floor(f(jd0 + sign * mid / 86400) / width) != k0:
                            hi = mid
                        else:
                            lo = mid
                    best = hi if best is None else min(best, hi)
                    break
                t = t2
        return best

    def time_to_change(f, jd0, width, step_s, limit_s):
        """Time to the nearest change, with the float64 Julian-date resolution floor made explicit.

        A JD near 2.45e6 is a float64 with a spacing (ULP) of about 4.0e-5 s. A bisection on JD
        cannot resolve a crossing closer than that, so such results are reported as
        RESOLUTION_LIMITED, with a linear estimate (edge distance / local rate) instead of a value.
        """
        ulp_s = math.ulp(jd0) * 86400
        secs = seconds_to_change(f, jd0, width, step_s, limit_s)
        if secs is not None and secs > 2 * ulp_s:
            return {"status": "RESOLVED", "seconds": secs, "jd_ulp_s": ulp_s}
        v = f(jd0)
        r = v % width
        dist = min(r, width - r)
        h = 30 / 86400
        rate = abs((f(jd0 + h) - f(jd0 - h) + 540) % 360 - 180) / 60.0
        return {"status": "RESOLUTION_LIMITED", "seconds": None, "jd_ulp_s": ulp_s,
                "edge_distance_deg": dist, "local_rate_deg_per_s": rate,
                "linear_estimate_s": dist / rate,
                "note": "crossing closer than the float64 JD resolution; the input instant itself is only "
                        "representable to +/- half a JD ULP, so the time to the edge is unresolved at this precision"}

    matrix = {f["id"]: f for f in json.loads((pr62 / "tests/sci_gold/matrix.json").read_text())["fixtures"]}
    sys.path.insert(0, str(pr62))
    from tests.sci_gold import swiss_reference as sr
    per_chart = []
    for res in gold["results"]:
        if not res.get("edge_distance_deg"):
            continue
        fx = matrix[res["id"]]
        lat, lon = fx["input"]["latitude"], fx["input"]["longitude"]
        jd = float(sr.parse((sr.RECEIPTS / f"{res['id']}.txt").read_text(encoding="utf-8"))["header"]["jd_double"])
        row = {"id": res["id"], "group": res["group"], "classification": res["classification"]}
        for c in ("rashi", "navamsa"):
            row[f"lagna_{c}"] = time_to_change(lambda j: lagna(j, lat, lon), jd, cats[c], 10, 4 * 3600)
        for c, w in cats.items():
            row[f"moon_{c}"] = time_to_change(moon, jd, w, 300, 3 * 86400)
        per_chart.append(row)
    # unbiased estimate: random synthetic instants at the matrix coordinates, linear-rate time-to-edge
    rng = random.Random(seed)
    coords = sorted({(f["input"]["latitude"], f["input"]["longitude"]) for f in matrix.values() if f["expect"]["kind"] == "chart"})
    jd_lo, jd_hi = swe.julday(1970, 1, 1, 0), swe.julday(2100, 12, 31, 24)
    windows = (60, 120, 300, 900)
    hits = {f"{who}_{c}": {w: 0 for w in windows} for who in ("lagna", "moon") for c in cats}
    for _ in range(samples):
        lat, lon = rng.choice(coords)
        jd = rng.uniform(jd_lo, jd_hi)
        h = 30 / 86400
        vals = {"lagna": (lagna(jd, lat, lon), (lagna(jd + h, lat, lon) - lagna(jd - h, lat, lon) + 540) % 360 - 180),
                "moon": (moon(jd), (moon(jd + h) - moon(jd - h) + 540) % 360 - 180)}
        for who, (v, dv) in vals.items():
            rate = abs(dv) / 60.0      # deg per second
            for c, w in cats.items():
                r = v % w
                secs = min(r, w - r) / rate
                for win in windows:
                    if secs <= win:
                        hits[f"{who}_{c}"][win] += 1
    frac = {k: {f"within_{w // 60}_min": v[w] / samples for w in windows} for k, v in hits.items()}
    return {"per_chart": per_chart, "random_sample": {"n": samples, "seed": seed, "period": "1970-01-01..2100-12-31 UTC",
                                                     "interpretation": "illustrative synthetic sample at the matrix coordinates; "
                                                                       "not a population prevalence and not a rate of inaccurate birth records",
                                                     "coordinates": len(coords), "fraction_changing_within": frac}}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pr62", type=Path, required=True)
    ap.add_argument("--gold-report", type=Path, required=True)
    ap.add_argument("--ephe", required=True)
    ap.add_argument("--samples", type=int, default=20000)
    ap.add_argument("--seed", type=int, default=20261103)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    sys.path.insert(0, str(a.pr62))
    from tests.sci_gold import asc_formula, swiss_reference as sr
    pins = json.loads((a.pr62 / "tests/sci_gold/PINS.json").read_text())
    assert sha256(a.pr62 / "tests/sci_gold/receipts/SHA256SUMS") == pins["receipts_sha256sums_sha256"], "receipts not the pinned set"
    assert sha256(a.pr62 / "tests/sci_gold/matrix.json") == pins["matrix_sha256"], "matrix not the pinned matrix"
    gold = json.loads(a.gold_report.read_text())
    import swisseph
    out = {"schema": "kun-sci-pol-001-analysis/1",
           "inputs": {"pr62_head": gold["environment"]["git"]["head"], "pr62_tree": gold["environment"]["git"]["tree"],
                      "gold_report_sha256": sha256(a.gold_report), "receipts_sha256sums_sha256": pins["receipts_sha256sums_sha256"],
                      "matrix_sha256": pins["matrix_sha256"], "swiss_spec_sha256": pins["swiss_spec_sha256"],
                      "pyswisseph": __import__("importlib.metadata").metadata.version("pyswisseph"),
                      "swiss_library": swisseph.version, "mpmath": mp.__version__,
                      "python": sys.version.split()[0]},
           "B1": b1(a.pr62, gold, sr, asc_formula), "B3": b3(a.pr62, gold),
           "B6": b6(a.pr62, gold, a.ephe, a.samples, a.seed)}
    a.out.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
