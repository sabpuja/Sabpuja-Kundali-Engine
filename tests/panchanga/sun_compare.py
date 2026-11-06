"""KUN-PAN-M2-SUN-001 comparison runner: IMD 47' versus USNO 50' sunrise, with independent references.

Layers (each one is separate; none is combined into another):

1. USNO published minutes (PAN-REF-SUN-2026, 12 located cases + 2 polar cases) against SUN-A-USNO-50;
2. IMD published minutes (PAN-REF-SUN-IMD-2026: Central Station, Chennai, Delhi, Kolkata, Mumbai)
   against SUN-D-IMD-47, and a day-length fit of the depression angle;
3. the independent pure-Python oracle (`sun_oracle`), same convention;
4. Swiss `rise_trans_true_hor` (Swiss-on-Swiss, different algorithm), geocentric flag set;
5. optional: the separately built official `swetest` (altitude at the engine instant).

Run:  python -m tests.panchanga.sun_compare --report-dir DIR   (needs SABPUJA_TEST_EPHE_PATH;
      SABPUJA_TEST_SWETEST optional). No birth data is used: every input is a synthetic place/date.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import os
import subprocess
import sys

from sabpuja_kundali.panchanga import sun
from . import sun_oracle

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
USNO_PATH = REPO / "research/panchanga/reference-fixtures/usno-sunrise-sunset-2026.json"
IMD_PATH = REPO / "research/panchanga/reference-fixtures/imd-sunrise-sunset-2026.json"
TOL_PATH = HERE / "sun-tolerances.json"
USNO_SHA256 = "15c10f56e33b27355f0263d2694bb0d59d83f6b4230bb7b03e29251f3334dd0d"
IMD_SHA256 = "d907d2f75df281d779c9d2e5e0f90b09b7803c324c7b44c47977f42a16c22541"
TOL_SHA256 = "f86df2450892295dd830d947fe60f75015ba5304e9a30a3afa3328728a26c39a"

IMD47, USNO50 = "SUN-D-IMD-47", "SUN-A-USNO-50"
IST = timezone(timedelta(hours=5, minutes=30))
EPOCH = datetime(1970, 1, 1, tzinfo=timezone.utc)

# Synthetic reference points across India (not a gazetteer; not birth data).
INDIA = (
    ("Delhi", 28.6139, 77.2090), ("Mumbai", 19.0760, 72.8777), ("Kolkata", 22.5726, 88.3639),
    ("Chennai", 13.0827, 80.2707), ("Bengaluru", 12.9716, 77.5946), ("Hyderabad", 17.3850, 78.4867),
    ("Ahmedabad", 23.0225, 72.5714), ("Jaipur", 26.9124, 75.7873), ("Guwahati", 26.1445, 91.7362),
    ("Srinagar", 34.0837, 74.7973), ("Leh", 34.1526, 77.5771), ("Kanyakumari", 8.0883, 77.5385),
    ("Port Blair", 11.6234, 92.7265), ("Dwarka (west)", 22.2394, 68.9678), ("Kibithu (east)", 28.0000, 97.0000),
    ("IMD Central Station", 23 + 11 / 60, 82.5),
)
INDIA_DATES = tuple(f"2026-{m:02d}-{d:02d}" for m in range(1, 13) for d in (1, 15)) + (
    "2026-03-20", "2026-06-21", "2026-09-23", "2026-12-21", "1970-01-01", "2000-02-29", "2100-12-31")
HIGH_LAT = (
    ("64.9N", 64.9, 25.0, "Europe/Helsinki"), ("65.1N", 65.1, 25.0, "Europe/Helsinki"),
    ("65.5N", 65.5, 25.0, "Europe/Helsinki"), ("60N Oslo", 59.91, 10.75, "Europe/Oslo"),
    ("33.9S Sydney", -33.8688, 151.2093, "Australia/Sydney"), ("65.5S", -65.5, -64.0, "America/Argentina/Ushuaia"),
)
HIGH_DATES = ("2026-03-20", "2026-05-20", "2026-06-10", "2026-07-05", "2026-09-23", "2026-12-05", "2026-12-21")


def pinned(path: Path, sha: str) -> dict:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != sha:
        raise AssertionError(f"{path.name} does not match its pinned SHA-256")
    return json.loads(data)


def utc_of(event: dict) -> datetime:
    return EPOCH + timedelta(microseconds=event["utc_us"])


def published_seconds_diff(event: dict, d: date, hhmm: str, tz) -> float:
    h, m = map(int, hhmm.split(":"))
    pub = datetime(d.year, d.month, d.day, h, m, tzinfo=tz)
    return (utc_of(event) - pub).total_seconds()


def _fixed_tz(offset: str):
    sign = -1 if offset.startswith("-") else 1
    h, m = map(int, offset.lstrip("+-").split(":"))
    return timezone(sign * timedelta(hours=h, minutes=m))


USNO_ZONES = {"+05:30": "Asia/Kolkata", "+10:00": "Australia/Sydney", "+03:00": "Europe/Helsinki",
              "+01:00": "Europe/Oslo"}


def usno_layer(ephe: str | None = None) -> list[dict]:
    rows = []
    for case in pinned(USNO_PATH, USNO_SHA256)["cases"]:
        loc, pub = case["location"], case["published"]
        lat, lon, d = loc["latitude_deg"], loc["longitude_deg"], date.fromisoformat(case["date_local"])
        zone = USNO_ZONES[case["utc_offset"]]
        row = {"case": case["case_id"], "label": loc["label"], "date": case["date_local"], "lat": lat, "lon": lon}
        try:
            out = {c: sun.sun_day(case["date_local"], lat, lon, zone, convention=c, ephe_path=ephe)
                   for c in (USNO50, IMD47)}
        except sun.EXPECTED_ERRORS as exc:
            row["engine_refusal"] = exc.code
            rows.append(row)
            continue
        tz = _fixed_tz(case["utc_offset"])
        for kind in ("sunrise", "sunset"):
            for c in (USNO50, IMD47):
                ev = out[c][kind]
                key = f"{kind}_{'usno50' if c == USNO50 else 'imd47'}"
                if ev["status"] != "available":
                    row[key] = ev["condition"]
                    continue
                row[key] = ev["local"]
                if pub.get(kind):
                    row[f"{key}_minus_published_s"] = round(published_seconds_diff(ev, d, pub[kind], tz), 1)
            row[f"{kind}_published"] = pub.get(kind)
        row["usno_sundata"] = [p["phen"] for p in pub.get("sundata", [])] or None
        rows.append(row)
    return rows


def imd_layer(ephe: str | None = None) -> list[dict]:
    doc = pinned(IMD_PATH, IMD_SHA256)
    rows = []
    entries = [("central", r["date"], r["sunrise"], r["sunset"]) for r in doc["central_station"]]
    entries += [(c, r["date"], r[c][0], r[c][1]) for r in doc["cities"] for c in ("chennai", "delhi", "kolkata", "mumbai")]
    for place, ds, pr, ps in entries:
        p = doc["places"][place]
        d = date.fromisoformat(ds)
        row = {"place": place, "date": ds, "published_sunrise": pr, "published_sunset": ps}
        for c in (IMD47, USNO50):
            out = sun.sun_day(ds, p["latitude_deg"], p["longitude_deg"], "Asia/Kolkata", convention=c, ephe_path=ephe)
            tag = "imd47" if c == IMD47 else "usno50"
            row[f"sunrise_{tag}_minus_published_s"] = round(published_seconds_diff(out["sunrise"], d, pr, IST), 3)
            row[f"sunset_{tag}_minus_published_s"] = round(published_seconds_diff(out["sunset"], d, ps, IST), 3)
            row[f"daylength_{tag}_minus_published_s"] = round(
                row[f"sunset_{tag}_minus_published_s"] - row[f"sunrise_{tag}_minus_published_s"], 3)
        rows.append(row)
    return rows


def _nearest_minute_consistent(diff_s: float) -> bool:
    # A computed time t prints as minute p under round-to-nearest iff -30 <= t - p < 30.
    return -30.0 <= diff_s < 30.0


def imd_summary(rows: list[dict]) -> dict:
    out = {}
    groups = {"all": rows, "central": [r for r in rows if r["place"] == "central"],
              "cities": [r for r in rows if r["place"] != "central"]}
    for name, rs in groups.items():
        g = {"days": len(rs), "values": 2 * len(rs)}
        for tag in ("imd47", "usno50"):
            diffs = [r[f"{k}_{tag}_minus_published_s"] for r in rs for k in ("sunrise", "sunset")]
            dl = [r[f"daylength_{tag}_minus_published_s"] for r in rs]
            mean = sum(dl) / len(dl)
            sd = math.sqrt(sum((x - mean) ** 2 for x in dl) / (len(dl) - 1))
            g[tag] = {"max_abs_s": round(max(abs(x) for x in diffs), 1),
                      "nearest_minute_consistent": sum(_nearest_minute_consistent(x) for x in diffs),
                      "daylength_mean_resid_s": round(mean, 1), "daylength_se_s": round(sd / math.sqrt(len(dl)), 1)}
        # Linear fit of the depression from the mean day-length residual (residual is linear in depression).
        a, b = g["imd47"]["daylength_mean_resid_s"], g["usno50"]["daylength_mean_resid_s"]
        g["best_fit_depression_arcmin"] = round(47 - a * 3 / (b - a), 1) if b != a else None
        se = g["imd47"]["daylength_se_s"] * 3 / abs(b - a) if b != a else None
        g["best_fit_depression_se_arcmin"] = round(se, 1) if se is not None else None
        out[name] = g
    by_group = {}
    for r in rows:
        season = "chaitra" if r["date"] < "2026-05-01" else ("ashadha" if r["date"] < "2026-08-01" else "kartika")
        by_group.setdefault(f"{r['place']} {season}", []).append(r)
    fits = {}
    for k, rs in sorted(by_group.items()):
        a = sum(r["daylength_imd47_minus_published_s"] for r in rs) / len(rs)
        b = sum(r["daylength_usno50_minus_published_s"] for r in rs) / len(rs)
        fits[k] = {"days": len(rs), "best_fit_depression_arcmin": round(47 - a * 3 / (b - a), 1)}
    out["best_fit_by_place_and_month"] = fits
    return out


def oracle_and_swiss_layer(ephe: str | None = None, swetest: str | None = None) -> list[dict]:
    import swisseph as swe
    rows = []
    cases = [(n, la, lo, "Asia/Kolkata", ds) for n, la, lo in INDIA for ds in INDIA_DATES]
    cases += [(n, la, lo, tz, ds) for n, la, lo, tz in HIGH_LAT for ds in HIGH_DATES]
    for name, lat, lon, tz, ds in cases:
        outs = {c: sun.sun_day(ds, lat, lon, tz, convention=c, ephe_path=ephe) for c in (IMD47, USNO50)}
        for kind in ("sunrise", "sunset"):
            row = {"place": name, "lat": lat, "lon": lon, "zone": tz, "date": ds, "event": kind}
            evs = {c: outs[c][kind] for c in outs}
            if any(e["status"] != "available" for e in evs.values()):
                row["unavailable"] = {c: e.get("condition") for c, e in evs.items()}
                rows.append(row)
                continue
            row["imd47_local"] = evs[IMD47]["local"]
            row["usno50_local"] = evs[USNO50]["local"]
            row["imd47_minus_usno50_s"] = round((evs[IMD47]["utc_us"] - evs[USNO50]["utc_us"]) / 1e6, 3)
            for c, tag in ((IMD47, "imd47"), (USNO50, "usno50")):
                ev, dep = evs[c], sun.CONVENTIONS[c]["depression_arcmin"]
                t = utc_of(ev)
                o = sun_oracle.event_utc(t + timedelta(minutes=20), lat, lon, dep, "rise" if kind == "sunrise" else "set")
                row[f"{tag}_minus_oracle_s"] = None if o is None else round((t - o).total_seconds(), 3)
                jd = ev["utc_us"] / 1e6 / 86400 + 2440587.5
                swe.set_ephe_path(ephe or os.environ.get("SABPUJA_EPHE_PATH", ""))
                flags = swe.BIT_DISC_CENTER | swe.BIT_NO_REFRACTION
                rs = swe.CALC_RISE if kind == "sunrise" else swe.CALC_SET
                for geo, label in ((128, "geocentric"), (0, "topocentric")):
                    res, tret = swe.rise_trans_true_hor(jd - 0.25, swe.SUN, rs | flags | geo, (lon, lat, 0), 0, 0,
                                                        -dep / 60, swe.FLG_SWIEPH)
                    row[f"{tag}_minus_swiss_rise_{label}_s"] = (
                        round((jd - tret[0]) * 86400, 3) if res == 0 else f"swiss_res_{res}")
                if swetest:
                    row[f"{tag}_swetest_check_arcsec"] = swetest_altitude_check(swetest, ephe, jd, lat, lon, dep)
            rows.append(row)
    return rows


def swetest_altitude_check(swetest: str, ephe: str | None, jd: float, lat: float, lon: float, dep: float) -> float:
    """swetest topocentric geometric altitude + parallax minus the target -depression, in arcseconds."""
    ephe = ephe or os.environ.get("SABPUJA_EPHE_PATH", "")
    proc = subprocess.run([swetest, f"-edir{ephe}", f"-bj{jd:.9f}", "-ut", "-p0", "-fhR",
                           f"-geopos{lon!r},{lat!r},0", "-g,", "-head"], capture_output=True, text=True, check=True)
    if proc.stderr.strip():
        raise AssertionError("swetest wrote to stderr")
    h, r = (float(x) for x in proc.stdout.strip().split(","))
    parallax = 8.794148 / r * math.cos(math.radians(h))
    return round((h * 3600 + parallax) - (-dep * 60), 3)


def write_reports(report_dir: Path, usno, imd, imd_stats, grid) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    doc = {"task": "KUN-PAN-M2-SUN-001", "usno": usno, "imd_summary": imd_stats, "imd_rows": imd, "grid": grid,
           "tolerances_sha256": TOL_SHA256, "usno_fixture_sha256": USNO_SHA256, "imd_fixture_sha256": IMD_SHA256}
    (report_dir / "sun-comparison.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    with open(report_dir / "sun-grid.csv", "w", newline="") as fh:
        keys = sorted({k for r in grid for k in r})
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in grid:
            w.writerow({k: (json.dumps(v) if isinstance(v, dict) else v) for k, v in r.items()})
    with open(report_dir / "sun-imd.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(imd[0]))
        w.writeheader()
        w.writerows(imd)


def grid_summary(grid: list[dict]) -> dict:
    ok = [r for r in grid if "unavailable" not in r]
    india = [r for r in ok if r["zone"] == "Asia/Kolkata"]
    def mx(rs, key):
        vals = [abs(r[key]) for r in rs if isinstance(r.get(key), (int, float))]
        return round(max(vals), 3) if vals else None
    out = {"events": len(grid), "available": len(ok), "unavailable": len(grid) - len(ok), "india_events": len(india)}
    for tag in ("imd47", "usno50"):
        for key in (f"{tag}_minus_oracle_s", f"{tag}_minus_swiss_rise_geocentric_s", f"{tag}_minus_swiss_rise_topocentric_s",
                    f"{tag}_swetest_check_arcsec"):
            out[f"max_abs_{key}_india"] = mx(india, key)
            out[f"max_abs_{key}_all"] = mx(ok, key)
    d = [r["imd47_minus_usno50_s"] for r in india]
    rise = [x for r, x in zip(india, d) if r["event"] == "sunrise"]
    sets = [x for r, x in zip(india, d) if r["event"] == "sunset"]
    out["india_imd47_minus_usno50_sunrise_s"] = [round(min(rise), 2), round(max(rise), 2)]
    out["india_imd47_minus_usno50_sunset_s"] = [round(min(sets), 2), round(max(sets), 2)]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--report-dir", required=True)
    args = ap.parse_args(argv)
    ephe = os.environ.get("SABPUJA_TEST_EPHE_PATH")
    if not ephe:
        print("SABPUJA_TEST_EPHE_PATH unset: BLOCKED")
        return 2
    swetest = os.environ.get("SABPUJA_TEST_SWETEST")
    pinned(TOL_PATH, TOL_SHA256)
    usno = usno_layer(ephe)
    imd = imd_layer(ephe)
    stats = imd_summary(imd)
    grid = oracle_and_swiss_layer(ephe, swetest)
    gsum = grid_summary(grid)
    write_reports(Path(args.report_dir), usno, imd, stats, grid)
    print(json.dumps({"usno": usno}, indent=1, ensure_ascii=False))
    print(json.dumps({"imd_summary": stats}, indent=1))
    print(json.dumps({"grid_summary": gsum, "swetest": "used" if swetest else "not provided"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
