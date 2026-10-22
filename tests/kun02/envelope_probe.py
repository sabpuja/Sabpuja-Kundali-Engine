"""KUN-02 Workstream C: supported birth dates and latitudes (test-only probe)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import zoneinfo

from sabpuja_kundali.engine import ChartComputationError, calculate

from .common import ENGINE_BEHAVIOUR, SWISS_CONFORMANCE, TIMEKEEPING, swiss, true_obliquity

UTC = timezone.utc
BODIES = ("SUN", "MOON", "MARS", "MERCURY", "JUPITER", "VENUS", "SATURN", "MEAN_NODE")


def _fmt(offset: timedelta) -> str:
    seconds = int(offset.total_seconds())
    sign = "-" if seconds < 0 else "+"
    seconds = abs(seconds)
    return f"{sign}{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def zone_offset_extremes() -> dict:
    """Largest and smallest UTC offsets at the local-date window edges, all keys and location keys only."""
    edges = {"start": datetime(1900, 1, 1), "end": datetime(2100, 12, 31, 23, 59, 59)}
    out = {}
    keys = sorted(zoneinfo.available_timezones())
    for label, wall in edges.items():
        for scope, selected in (("all_keys", keys),
                                ("location_keys", [k for k in keys if "/" in k and not k.startswith("Etc/")])):
            out[f"{label}/{scope}"] = _extremes(wall, selected)
    return {"evidence_class": TIMEKEEPING, "edges": out}


def _extremes(wall: datetime, keys) -> dict:
    offsets = []
    for key in keys:
        try:
            tz = zoneinfo.ZoneInfo(key)
        except (zoneinfo.ZoneInfoNotFoundError, ValueError):
            continue
        offsets.append((wall.replace(tzinfo=tz).utcoffset(), key))
    hi, lo = max(offsets), min(offsets)
    return {"local_wall_time": wall.isoformat(), "zones": len(offsets),
            "max_offset": _fmt(hi[0]), "max_zone": hi[1], "min_offset": _fmt(lo[0]), "min_zone": lo[1],
            "utc_range": [(wall - hi[0]).isoformat() + "Z", (wall - lo[0]).isoformat() + "Z"]}


def ephemeris_coverage(folder) -> dict:
    swe = swiss(folder)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    instants = {
        "earliest UTC of local window (1899-12-31T10:00Z)": swe.julday(1899, 12, 31, 10.0),
        "latest UTC of local window (2101-01-01T12:00Z)": swe.julday(2101, 1, 1, 12.0),
        "1800-06-01": swe.julday(1800, 6, 1, 0.0), "2399-06-01": swe.julday(2399, 6, 1, 0.0),
        "1799-06-01 (outside data)": swe.julday(1799, 6, 1, 0.0),
        "2400-06-01 (outside data)": swe.julday(2400, 6, 1, 0.0),
    }
    rows = []
    for label, jd in instants.items():
        swieph = {}
        for name in BODIES:
            ret = swe.calc_ut(jd, getattr(swe, name), flags)[1]
            swieph[name] = bool(ret & swe.FLG_SWIEPH)
        rows.append({"instant": label, "jd_ut": jd, "all_bodies_swiss_files": all(swieph.values()),
                     "bodies_falling_back": [k for k, v in swieph.items() if not v]})
    return {"evidence_class": SWISS_CONFORMANCE, "rows": rows}


def latitude_behaviour(folder) -> dict:
    """Engine acceptance near the polar circle: today the refusal depends on the date."""
    swe = swiss(folder)
    cases = [
        ("1900-01-01T12:00:00+00:00", 66.55), ("2100-12-31T12:00:00+00:00", 66.55),
        ("2000-01-01T12:00:00+00:00", 66.0), ("2000-01-01T12:00:00+00:00", -66.0),
        ("2000-01-01T12:00:00+00:00", 66.5623), ("2000-01-01T12:00:00+00:00", 66.5624),
        ("2000-01-01T12:00:00+00:00", 88.999999), ("2000-01-01T12:00:00+00:00", 89.0),
    ]
    rows = []
    for when, lat in cases:
        req = {"birth_datetime": when, "timezone": "UTC", "latitude": lat, "longitude": 0.0}
        utc = datetime.fromisoformat(when).astimezone(UTC)
        jd = swe.julday(utc.year, utc.month, utc.day, utc.hour + utc.minute / 60)
        row = {"birth_datetime": when, "latitude": lat, "polar_circle_latitude": 90 - true_obliquity(swe, jd)}
        try:
            out = calculate(req, ephe_path=str(folder))
            row["engine"] = "ACCEPT lagna " + out["lagna"]["rashi"]
        except ChartComputationError as exc:
            row["engine"] = "REFUSE " + exc.code
        except ValueError as exc:
            row["engine"] = "REFUSE input: " + str(exc)
        rows.append(row)
    return {"evidence_class": ENGINE_BEHAVIOUR, "rows": rows}


def delta_t_edges(folder) -> dict:
    swe = swiss(folder)
    rows = []
    for y in (1900, 1901, 2099, 2100):
        jd = swe.julday(y, 1, 1, 0.0)
        rows.append({"year": y, "delta_t_swieph_s": swe.deltat_ex(jd, swe.FLG_SWIEPH) * 86400,
                     "delta_t_moseph_s": swe.deltat_ex(jd, swe.FLG_MOSEPH) * 86400})
    return {"evidence_class": SWISS_CONFORMANCE, "rows": rows}


def run(folder) -> dict:
    return {"zone_offset_extremes": zone_offset_extremes(), "ephemeris_coverage": ephemeris_coverage(folder),
            "latitude_behaviour": latitude_behaviour(folder), "delta_t_edges": delta_t_edges(folder)}
