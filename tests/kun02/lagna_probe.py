"""KUN-02 Workstream A: Lagna through houses_ex b"P" versus b"W".

Test-only probe. It calls Swiss Ephemeris directly with the engine's exact
configuration and never changes production code. Results are grouped by
evidence class (see common.py).
"""
from __future__ import annotations

from fractions import Fraction
import json
import math
import random
import subprocess
import sys
import tempfile

from sabpuja_kundali import rules
from sabpuja_kundali.engine import ChartComputationError, _display_deg, calculate

from .common import (ARCSEC, ENGINE_BEHAVIOUR, INDEPENDENT_MATHEMATICS, SWISS_CONFORMANCE,
                     finite_max, houses, load_fixture, rad, signed_delta, swiss, true_obliquity)

BANDS = [(0, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 66)]
BODIES = ("SUN", "MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN", "MEAN_NODE")


def band_name(abs_lat: float, polar_limit: float) -> str:
    for low, high in BANDS:
        if low <= abs_lat < high:
            return f"[{low},{high})"
    if abs_lat == 66.0:
        return "66.0 exactly"
    if abs_lat < polar_limit:
        return "(66, polar circle)"
    return "[polar circle, 89)"


def independent_ascendant(armc: float, eps: float, lat: float) -> float:
    """Tropical ascendant by spherical trigonometry (Meeus-type formula), degrees in [0, 360)."""
    th, e, f = rad(armc), rad(eps), rad(lat)
    return math.degrees(math.atan2(math.cos(th), -(math.sin(th) * math.cos(e) + math.tan(f) * math.sin(e)))) % 360


def horizon_state(lam: float, armc: float, eps: float, lat: float) -> tuple[float, bool]:
    """(altitude in arcsec, rising?) of the ecliptic point lam (tropical, beta=0).

    Rising means east of the meridian: sin(hour angle) < 0. Independent of Swiss.
    """
    l, e, f = rad(lam), rad(eps), rad(lat)
    ra = math.atan2(math.sin(l) * math.cos(e), math.cos(l))
    dec = math.asin(math.sin(l) * math.sin(e))
    ha = rad(armc) - ra
    alt = math.asin(math.sin(f) * math.sin(dec) + math.cos(f) * math.cos(dec) * math.cos(ha))
    return math.degrees(alt) * ARCSEC, math.sin(ha) < 0


def classical_navamsa(longitude: Fraction) -> int:
    """D9 sign index by the classical element rule, exact. Independent of rules.navamsa_sign."""
    lon = longitude % 360
    sign = int(lon // 30)
    part = int((lon - 30 * sign) // Fraction(10, 3))
    start = {0: 0, 1: 9, 2: 6, 3: 3}[sign % 4]
    return (start + part) % 12


def reset(swe, folder) -> None:
    """The engine's per-call configuration. set_ephe_path also clears leaked sidereal bits."""
    swe.set_ephe_path(str(folder))
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)


def compare_point(swe, jd: float, lat: float, lon: float) -> dict:
    sid = swe.FLG_SIDEREAL
    p = houses(swe, jd, lat, lon, b"P", sid)
    w = houses(swe, jd, lat, lon, b"W", sid)
    wt = houses(swe, jd, lat, lon, b"W", 0)
    ayan = swe.get_ayanamsa_ex_ut(jd, swe.FLG_SWIEPH)[1]
    eps = true_obliquity(swe, jd)
    w_cusps, w_ascmc = w
    asc_w = w_ascmc[0]
    trop = wt[1][0]
    armc = wt[1][2]
    indep = independent_ascendant(armc, eps, lat)
    d_indep = signed_delta(trop, indep)
    alt, rising = horizon_state(trop, armc, eps, lat)
    k = rules.sign_index(asc_w)
    cusps_ok = (w_cusps[0] == 30.0 * k
                and all(w_cusps[i] == (30.0 * (k + i)) % 360 for i in range(12)))
    out = {
        "p_ok": p is not None,
        "asc_w": asc_w,
        "lahiri_residual_arcsec": signed_delta(asc_w, trop - ayan) * ARCSEC,
        "independent_residual_arcsec": d_indep * ARCSEC if abs(d_indep) < 90 else (abs(d_indep) - 180) * ARCSEC,
        "independent_relation": "same" if abs(d_indep) < 90 else "opposite",
        "altitude_arcsec": alt,
        "rising": rising,
        "w_cusps_whole_sign": cusps_ok,
    }
    if p is not None:
        asc_p = p[1][0]
        out["asc_p"] = asc_p
        out["p_equals_w_bitwise"] = asc_p.hex() == asc_w.hex()
        out["p_minus_w_arcsec"] = signed_delta(asc_p, asc_w) * ARCSEC
        out["mc_equal"] = p[1][1].hex() == w_ascmc[1].hex()
        out["armc_equal"] = p[1][2].hex() == w_ascmc[2].hex()
    return out


def _structured_points(grid):
    import swisseph as swe
    s = grid["structured_instants"]
    for loc in grid["locations"]:
        for y in s["years"]:
            for m in s["months"]:
                for d in s["days"]:
                    for h in s["hours_utc"]:
                        yield loc, swe.julday(y, m, d, h)


def _random_points(spec, lat_low, lat_high):
    rnd = random.Random(spec["seed"])
    for _ in range(spec["count"]):
        jd = rnd.uniform(spec["jd_ut_start"], spec["jd_ut_end"]) if "jd_ut_start" in spec \
            else rnd.uniform(2415020.5, 2488434.5)
        lat = rnd.uniform(lat_low, lat_high) * rnd.choice((-1, 1))
        lon = rnd.uniform(-180.0, 180.0)
        yield {"id": "random", "group": "random", "lat": lat, "lon": lon}, jd


def aggregate(rows) -> dict:
    stats: dict[str, dict] = {}
    for loc, r in rows:
        key = r["band"]
        b = stats.setdefault(key, {"samples": 0, "p_refused": 0, "w_refused": 0, "p_w_bitwise_equal": 0,
                                   "p_w_max_abs_arcsec": 0.0, "mc_armc_equal": 0,
                                   "lahiri_max_abs_arcsec": 0.0, "independent_max_abs_arcsec": 0.0,
                                   "independent_opposite": 0, "max_abs_altitude_arcsec": 0.0,
                                   "not_rising": 0, "w_cusp_failures": 0})
        b["samples"] += 1
        b["p_refused"] += not r["p_ok"]
        b["lahiri_max_abs_arcsec"] = max(b["lahiri_max_abs_arcsec"], abs(r["lahiri_residual_arcsec"]))
        b["independent_max_abs_arcsec"] = max(b["independent_max_abs_arcsec"], abs(r["independent_residual_arcsec"]))
        b["independent_opposite"] += r["independent_relation"] == "opposite"
        b["max_abs_altitude_arcsec"] = max(b["max_abs_altitude_arcsec"], abs(r["altitude_arcsec"]))
        b["not_rising"] += not r["rising"]
        b["w_cusp_failures"] += not r["w_cusps_whole_sign"]
        if r["p_ok"]:
            b["p_w_bitwise_equal"] += r["p_equals_w_bitwise"]
            b["p_w_max_abs_arcsec"] = max(b["p_w_max_abs_arcsec"], abs(r["p_minus_w_arcsec"]))
            b["mc_armc_equal"] += r["mc_equal"] and r["armc_equal"]
    return dict(sorted(stats.items()))


def placidus_threshold(swe, jd: float, hemisphere: int) -> float:
    """Smallest |lat| where b"P" raises, by bisection between 66 and 67 degrees."""
    lo, hi = 66.0, 67.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if houses(swe, jd, hemisphere * mid, 0.0, b"P", swe.FLG_SIDEREAL) is None:
            hi = mid
        else:
            lo = mid
        if hi - lo <= 1e-13:
            break
    return hi


def threshold_report(swe, grid) -> dict:
    rows = []
    for y, m, d in grid["threshold_dates"]:
        jd = swe.julday(y, m, d, 12.0)
        polar = 90.0 - true_obliquity(swe, jd)
        north, south = placidus_threshold(swe, jd, 1), placidus_threshold(swe, jd, -1)
        rows.append({"date_utc": f"{y:04d}-{m:02d}-{d:02d}T12:00Z", "ninety_minus_true_obliquity": polar,
                     "p_fails_from_north": north, "p_fails_from_south": south,
                     "north_minus_polar_arcsec": (north - polar) * ARCSEC,
                     "south_minus_polar_arcsec": (south - polar) * ARCSEC})
    # Range of the polar-circle latitude over the window (10-day steps, nutation included).
    values = [90.0 - true_obliquity(swe, jd) for jd in [2415020.5 + 10 * i for i in range(7342)]]
    return {"evidence_class": SWISS_CONFORMANCE, "per_date": rows,
            "polar_circle_latitude_1900_2100": {"min": min(values), "max": max(values)}}


def boundary_sweep(swe, grid) -> dict:
    spec = grid["boundary_sweep"]
    locs = {l["id"]: l for l in grid["locations"]}
    y, m, d = spec["date_utc"]
    start = swe.julday(y, m, d, 0.0)
    sid = swe.FLG_SIDEREAL
    out = []

    def seg(jd, loc):
        a = swe.houses_ex(jd, loc["lat"], loc["lon"], b"W", sid)[1][0]
        return rules._sector(a, 108), a

    for lid in spec["locations"]:
        loc = locs[lid]
        crossings, failures = 0, []
        prev_jd = start
        prev_seg, _ = seg(prev_jd, loc)
        for step in range(1, 1441):
            jd = start + step / 1440
            # Near the polar circle one minute can cross several segments: find each in turn.
            while seg(jd, loc)[0] != prev_seg:
                lo, hi = prev_jd, jd
                for _ in range(80):
                    mid = (lo + hi) / 2
                    if seg(mid, loc)[0] == prev_seg:
                        lo = mid
                    else:
                        hi = mid
                    if hi - lo < 1e-10:
                        break
                for side in (lo, hi):
                    p = swe.houses_ex(side, loc["lat"], loc["lon"], b"P", sid)
                    w = swe.houses_ex(side, loc["lat"], loc["lon"], b"W", sid)
                    asc = w[1][0]
                    checks = {
                        "p_equals_w": p[1][0].hex() == asc.hex(),
                        "cusp1_is_rashi_start": w[0][0] == 30.0 * rules.sign_index(asc),
                        "navamsa_rule_matches_classical":
                            rules.SIGNS.index(rules.navamsa_sign(asc)) == classical_navamsa(Fraction(asc)),
                    }
                    if not all(checks.values()):
                        failures.append({"jd": side, "asc": asc, **checks})
                if (seg(hi, loc)[0] - prev_seg) % 108 != 1:
                    failures.append({"jd_lo": lo, "jd_hi": hi, "error": "segment did not advance by one"})
                crossings += 1
                prev_jd, prev_seg = hi, seg(hi, loc)[0]
            prev_jd = jd
        out.append({"location": lid, "navamsa_crossings": crossings,
                    "bracket_days_max": 1e-10, "failures": failures})
    return {"evidence_class": SWISS_CONFORMANCE + "+" + INDEPENDENT_MATHEMATICS, "per_location": out}


CONSISTENCY_GROUPS = ("india", "southern", "equator", "northern")
CONSISTENCY_MONTHS = (1, 4, 7, 10)
CONSISTENCY_HOURS = (0.0, 6.0, 12.0, 18.0)
CONSISTENCY_ROW_CHECKS = 5  # keys of `row` below
CONSISTENCY_BODIES = len(BODIES) + 1  # plus Ketu


def chart_consistency_plan(grid) -> list[tuple[dict, int, int, float]]:
    """The predeclared (location, year, month, hour UT) instants of the D1/D9 consistency check."""
    s = grid["structured_instants"]
    return [(loc, y, mth, h) for loc in grid["locations"] if loc["group"] in CONSISTENCY_GROUPS
            for y in s["years"][::2] for mth in CONSISTENCY_MONTHS for h in CONSISTENCY_HOURS]


def chart_consistency(swe, grid) -> dict:
    """D1/D9 placement from W cusps and from rules agree; P and W give identical categories."""
    sid, flags = swe.FLG_SIDEREAL, swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    checks = mismatches = 0
    examples = []
    for loc, y, mth, h in chart_consistency_plan(grid):
        jd = swe.julday(y, mth, 1, h)
        p = swe.houses_ex(jd, loc["lat"], loc["lon"], b"P", sid)[1][0]
        cusps, ascmc = swe.houses_ex(jd, loc["lat"], loc["lon"], b"W", sid)
        w = ascmc[0]
        longitudes = {}
        for name in BODIES:
            pos, ret = swe.calc_ut(jd, getattr(swe, name), flags)
            assert ret & swe.FLG_SWIEPH, "Moshier fallback"
            longitudes[name] = pos[0]
        longitudes["KETU"] = Fraction(longitudes["MEAN_NODE"]) + 180
        d9_lagna = rules.SIGNS.index(rules.navamsa_sign(w))
        for name, lam in longitudes.items():
            exact = Fraction(lam)
            house_rules = rules.whole_sign_house(lam, w)
            # W cusps are exact multiples of 30 (checked elsewhere), so no range wraps.
            house_cusps = next(i + 1 for i, c in enumerate(cusps)
                               if Fraction(c) <= exact % 360 < Fraction(c) + 30)
            d9 = rules.SIGNS.index(rules.navamsa_sign(lam))
            d9_house = (d9 - d9_lagna) % 12 + 1
            d9_house_classical = (classical_navamsa(exact) - classical_navamsa(Fraction(w))) % 12 + 1
            row = {
                "d1_house_rules_vs_w_cusps": house_rules == house_cusps,
                "d1_house_p_vs_w": rules.whole_sign_house(lam, p) == house_rules,
                "d9_sign_rules_vs_classical": d9 == classical_navamsa(exact),
                "d9_house_rules_vs_classical": d9_house == d9_house_classical,
                "d9_lagna_p_vs_w": rules.navamsa_sign(p) == rules.navamsa_sign(w),
            }
            checks += len(row)
            bad = [k for k, v in row.items() if not v]
            if bad:
                mismatches += len(bad)
                if len(examples) < 10:
                    examples.append({"loc": loc["id"], "jd": jd, "body": name, "failed": bad})
    return {"evidence_class": SWISS_CONFORMANCE + "+" + INDEPENDENT_MATHEMATICS,
            "checks": checks, "mismatches": mismatches, "examples": examples}


def lahiri_definition(swe, folder) -> dict:
    """SCI-01a: Swiss mode 1 at its defining epoch, plus secondary published IAE values."""
    t0 = 2435553.5  # 1956-03-21 0h TT
    defined = 23 + 15 / 60 + 0.658 / 3600
    epoch = {}
    for label, bits in (("default", 0), ("SIDBIT_NO_PREC_OFFSET", swe.SIDBIT_NO_PREC_OFFSET),
                        ("SIDBIT_PREC_ORIG", swe.SIDBIT_PREC_ORIG)):
        # set_sid_mode alone does not undo SIDBIT_PREC_ORIG (see wrong_configurations):
        # reset the path as the engine does on every call.
        reset(swe, folder)
        swe.set_sid_mode(swe.SIDM_LAHIRI | bits, 0, 0)
        true_v = swe.get_ayanamsa_ex(t0, swe.FLG_SWIEPH)[1]
        mean_v = swe.get_ayanamsa_ex(t0, swe.FLG_SWIEPH | swe.FLG_NONUT)[1]
        epoch[label] = {"true_minus_definition_arcsec": (true_v - defined) * ARCSEC,
                        "true_minus_mean_arcsec": (true_v - mean_v) * ARCSEC}
    reset(swe, folder)
    # Mean ayanamsa values attributed to IAE in Swiss docs Appendix E (secondary source).
    published = [
        {"label": "IAE 1989 p.512 mean 1989.0", "jd_tt": 2447527.5, "value_dms": [23, 42, 12.34]},
        {"label": "IAE 1989 p.512 mean 1990.0", "jd_tt": 2447892.5, "value_dms": [23, 43, 2.62]},
        {"label": "IAE 2019 p.429 mean 2000 Jan 1 12h TT", "jd_tt": 2451545.0, "value_dms": [23, 51, 25.53]},
    ]
    rows = []
    for p in published:
        value = p["value_dms"][0] + p["value_dms"][1] / 60 + p["value_dms"][2] / 3600
        default = swe.get_ayanamsa_ex(p["jd_tt"], swe.FLG_SWIEPH | swe.FLG_NONUT)[1]
        swe.set_sid_mode(swe.SIDM_LAHIRI | swe.SIDBIT_PREC_ORIG, 0, 0)
        orig = swe.get_ayanamsa_ex(p["jd_tt"], swe.FLG_SWIEPH | swe.FLG_NONUT)[1]
        reset(swe, folder)
        rows.append({**p, "swiss_mode1_default_minus_published_arcsec": (default - value) * ARCSEC,
                     "swiss_mode1_prec_orig_minus_published_arcsec": (orig - value) * ARCSEC})
    modes = {}
    jd = 2451545.0
    lahiri = swe.get_ayanamsa_ex_ut(jd, swe.FLG_SWIEPH)[1]
    for name in ("SIDM_LAHIRI_ICRC", "SIDM_LAHIRI_1940", "SIDM_LAHIRI_VP285", "SIDM_KRISHNAMURTI",
                 "SIDM_RAMAN", "SIDM_FAGAN_BRADLEY"):
        swe.set_sid_mode(getattr(swe, name), 0, 0)
        modes[name] = (swe.get_ayanamsa_ex_ut(jd, swe.FLG_SWIEPH)[1] - lahiri) * ARCSEC
    reset(swe, folder)
    return {
        "evidence_class": SWISS_CONFORMANCE + " (definition) + secondary published values",
        "definition": "23d15m00.658s true ayanamsha at 1956-03-21 0h TT (Swiss docs 2.8.5)",
        "at_defining_epoch": epoch,
        "published_comparisons": rows,
        "other_modes_minus_lahiri_at_J2000_arcsec": modes,
    }


def planet_frame(swe, grid) -> dict:
    """SCI-01d: sidereal longitude equals tropical apparent of date minus the true ayanamsha."""
    flags = swe.FLG_SWIEPH
    worst = {}
    rnd = random.Random(7)
    for _ in range(2000):
        jd = rnd.uniform(2415020.5, 2488434.5)
        ayan = swe.get_ayanamsa_ex_ut(jd, flags)[1]
        mean_ayan = swe.get_ayanamsa_ex_ut(jd, flags | swe.FLG_NONUT)[1]
        for name in BODIES:
            body = getattr(swe, name)
            s = swe.calc_ut(jd, body, flags | swe.FLG_SIDEREAL)[0][0]
            t = swe.calc_ut(jd, body, flags)[0][0]
            w = worst.setdefault(name, {"true_ayanamsha_max_abs_arcsec": 0.0, "mean_ayanamsha_max_abs_arcsec": 0.0})
            w["true_ayanamsha_max_abs_arcsec"] = max(w["true_ayanamsha_max_abs_arcsec"],
                                                    abs(signed_delta(s, t - ayan)) * ARCSEC)
            w["mean_ayanamsha_max_abs_arcsec"] = max(w["mean_ayanamsha_max_abs_arcsec"],
                                                    abs(signed_delta(s, t - mean_ayan)) * ARCSEC)
    return {"evidence_class": SWISS_CONFORMANCE, "samples": 2000, "per_body": worst}


_WRONG_CONFIG_SCRIPT = r"""
import json, sys, tempfile, swisseph as swe
folder, jd, lat, lon = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4])
sid = swe.FLG_SIDEREAL
out = {}
swe.set_ephe_path(folder)
out["sid_mode_never_set"] = swe.houses_ex(jd, lat, lon, b"W", sid)[1][0]
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
out["lahiri"] = swe.houses_ex(jd, lat, lon, b"W", sid)[1][0]
out["lahiri_flag_missing"] = swe.houses_ex(jd, lat, lon, b"W", 0)[1][0]
out["lahiri_nonut"] = swe.houses_ex(jd, lat, lon, b"W", sid | swe.FLG_NONUT)[1][0]
with tempfile.TemporaryDirectory() as empty:
    swe.set_ephe_path(empty)
    out["lahiri_empty_ephe_dir"] = swe.houses_ex(jd, lat, lon, b"W", sid)[1][0]
    pos, ret = swe.calc_ut(jd, swe.MOON, swe.FLG_SWIEPH | sid)
    out["moon_flags_with_empty_dir_has_swieph"] = bool(ret & swe.FLG_SWIEPH)
swe.set_ephe_path(folder)
swe.set_sid_mode(swe.SIDM_KRISHNAMURTI, 0, 0)
out["krishnamurti"] = swe.houses_ex(jd, lat, lon, b"W", sid)[1][0]
swe.set_sid_mode(swe.SIDM_LAHIRI | swe.SIDBIT_PREC_ORIG, 0, 0)
out["lahiri_prec_orig"] = swe.houses_ex(jd, lat, lon, b"W", sid)[1][0]
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
out["lahiri_after_prec_orig_mode_reset_only"] = swe.houses_ex(jd, lat, lon, b"W", sid)[1][0]
swe.set_ephe_path(folder)
swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
out["lahiri_after_path_and_mode_reset"] = swe.houses_ex(jd, lat, lon, b"W", sid)[1][0]
print(json.dumps(out))
"""


def wrong_configurations(folder, jd=2451545.0, lat=28.6139, lon=77.2090) -> dict:
    """Deliberately incorrect Swiss configurations, each in a fresh interpreter."""
    raw = subprocess.run([sys.executable, "-I", "-c", _WRONG_CONFIG_SCRIPT, str(folder), repr(jd),
                          repr(lat), repr(lon)], capture_output=True, text=True, check=True).stdout
    r = json.loads(raw)
    ref = r["lahiri"]
    return {
        "evidence_class": SWISS_CONFORMANCE,
        "case": {"jd_ut": jd, "lat": lat, "lon": lon},
        "lahiri_reference_deg": ref,
        "minus_reference_arcsec": {k: signed_delta(v, ref) * ARCSEC for k, v in r.items()
                                   if isinstance(v, float) and k != "lahiri"},
        "moon_flags_with_empty_dir_has_swieph": r["moon_flags_with_empty_dir_has_swieph"],
    }


def engine_cases(swe, grid, folder) -> list[dict]:
    from sabpuja_kundali.engine import _parse_birth
    from .common import engine_jd
    out = []
    for case in grid["engine_cases"]:
        req = {k: case[k] for k in ("birth_datetime", "timezone", "latitude", "longitude")}
        jd = engine_jd(swe, _parse_birth(req["birth_datetime"], req["timezone"]))
        p = houses(swe, jd, req["latitude"], req["longitude"], b"P", swe.FLG_SIDEREAL)
        cusps, ascmc = swe.houses_ex(jd, req["latitude"], req["longitude"], b"W", swe.FLG_SIDEREAL)
        row = {"id": case["id"], "jd_ut": jd, "w_asc": ascmc[0], "p_asc": p[1][0] if p else None}
        try:
            result = calculate(req, ephe_path=str(folder))
        except ChartComputationError as exc:
            row["engine"] = {"refused": exc.code}
        else:
            lagna = result["lagna"]
            houses_w = {name: rules.whole_sign_house(v["longitude_deg"], ascmc[0])
                        for name, v in result["planets"].items()}
            row["engine"] = {
                "lagna_display": lagna["longitude_deg"],
                "display_equals_w": lagna["longitude_deg"] == _display_deg(ascmc[0]),
                "rashi_equals_w": lagna["rashi"] == rules.sign(ascmc[0]),
                "navamsa_equals_w": lagna["navamsa_rashi"] == rules.navamsa_sign(ascmc[0]),
                "all_houses_equal_w": all(result["planets"][n]["whole_sign_house"] == h
                                          for n, h in houses_w.items()),
            }
        out.append(row)
    reset(swe, folder)
    return out


def run(folder) -> dict:
    swe = swiss(folder)
    grid = load_fixture("lagna_grid.json")
    rows = []
    for loc, jd in _structured_points(grid):
        r = compare_point(swe, jd, loc["lat"], loc["lon"])
        polar = 90.0 - true_obliquity(swe, jd)
        r["band"] = band_name(abs(loc["lat"]), polar)
        rows.append((loc, r))
    structured = aggregate(rows)
    per_group: dict[str, dict] = {}
    for loc, r in rows:
        g = per_group.setdefault(loc["group"], {"samples": 0, "p_refused": 0, "p_w_unequal": 0})
        g["samples"] += 1
        g["p_refused"] += not r["p_ok"]
        g["p_w_unequal"] += r["p_ok"] and not r["p_equals_w_bitwise"]
    rand_rows = []
    for loc, jd in _random_points(grid["random_sample"], 0.0, grid["random_sample"]["abs_lat_max"]):
        r = compare_point(swe, jd, loc["lat"], loc["lon"])
        r["band"] = band_name(abs(loc["lat"]), 90.0)
        rand_rows.append((loc, r))
    polar_spec = grid["random_polar_sample"]
    polar_rows = []
    for loc, jd in _random_points(polar_spec, polar_spec["abs_lat_min"], polar_spec["abs_lat_max"]):
        r = compare_point(swe, jd, loc["lat"], loc["lon"])
        r["band"] = band_name(abs(loc["lat"]), 90.0 - true_obliquity(swe, jd))
        polar_rows.append((loc, r))
    return {
        "structured_grid": {"evidence_class": SWISS_CONFORMANCE + "+" + INDEPENDENT_MATHEMATICS,
                            "points": len(rows), "by_band": structured, "by_group": per_group},
        "random_within_66": {"evidence_class": SWISS_CONFORMANCE + "+" + INDEPENDENT_MATHEMATICS,
                             "points": len(rand_rows), "by_band": aggregate(rand_rows)},
        "random_66_to_89": {"evidence_class": SWISS_CONFORMANCE + "+" + INDEPENDENT_MATHEMATICS,
                            "points": len(polar_rows), "by_band": aggregate(polar_rows)},
        "placidus_threshold": threshold_report(swe, grid),
        "boundary_sweep": boundary_sweep(swe, grid),
        "chart_consistency": chart_consistency(swe, grid),
        "lahiri_definition": lahiri_definition(swe, folder),
        "planet_frame": planet_frame(swe, grid),
        "wrong_configurations": wrong_configurations(folder),
        "engine_cases": {"evidence_class": ENGINE_BEHAVIOUR, "cases": engine_cases(swe, grid, folder)},
    }
