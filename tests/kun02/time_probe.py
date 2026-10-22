"""KUN-02 Workstream B: local birth time -> IANA zone -> UTC -> Swiss time scale.

Test-only probe. Engine behaviour is exercised through the engine's own
functions; time-scale and civil-time facts are checked against transcribed
IANA and IERS records in fixtures/.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fractions import Fraction
from zoneinfo import ZoneInfo
import random

from sabpuja_kundali import rules
from sabpuja_kundali.engine import _parse_birth, calculate

from .common import (ARCSEC, ENGINE_BEHAVIOUR, INDEPENDENT_MATHEMATICS, SWISS_CONFORMANCE, TIMEKEEPING,
                     engine_jd, load_fixture, signed_delta, swiss)

DEFAULT_PLACE = (28.6139, 77.2090)
UTC = timezone.utc


def classify(case: dict) -> tuple[str, str | None]:
    """(outcome code, UTC ISO string or None) from the engine's own parser."""
    fixture = load_fixture("time_cases.json")
    by_message = {msg: code for code, msg in fixture["outcomes"].items() if code != "ACCEPT"}
    try:
        utc = _parse_birth(case["birth_datetime"], case["timezone"])
    except ValueError as exc:
        return by_message.get(str(exc), "UNEXPECTED:" + str(exc)), None
    return "ACCEPT", utc.isoformat().replace("+00:00", "Z")


def engine_time_cases(folder=None) -> dict:
    fixture = load_fixture("time_cases.json")
    rows = []
    for case in fixture["cases"]:
        outcome, utc = classify(case)
        row = {"id": case["id"], "topic": case["topic"], "birth_datetime": case["birth_datetime"],
               "timezone": case["timezone"], "expect": case["expect"], "actual": outcome,
               "expect_utc": case.get("expect_utc"), "actual_utc": utc, "proposed": case["proposed"]}
        row["matches_expectation"] = outcome == case["expect"] and utc == case.get("expect_utc")
        if folder is not None and outcome == "ACCEPT":
            lat, lon = case.get("latitude", DEFAULT_PLACE[0]), case.get("longitude", DEFAULT_PLACE[1])
            req = {"birth_datetime": case["birth_datetime"], "timezone": case["timezone"],
                   "latitude": lat, "longitude": lon}
            result = calculate(req, ephe_path=str(folder))
            row["engine_utc"] = result["birth"]["utc"]
            row["engine_utc_matches_parser"] = result["birth"]["utc"] == utc
        rows.append(row)
    platform_rows = []
    for case in fixture["platform_dependent"]:
        outcome, utc = classify(case)
        platform_rows.append({"id": case["id"], "topic": case["topic"], "actual": outcome, "actual_utc": utc})
    return {"evidence_class": ENGINE_BEHAVIOUR + "+" + TIMEKEEPING, "cases": rows,
            "all_match": all(r["matches_expectation"] for r in rows),
            "platform_dependent_observed": platform_rows}


def _hms(text: str) -> timedelta:
    sign = -1 if text.startswith("-") else 1
    parts = [int(p) for p in text.lstrip("-").split(":")]
    parts += [0] * (3 - len(parts))
    return sign * timedelta(hours=parts[0], minutes=parts[1], seconds=parts[2])


def transcribed_transitions(zone: dict) -> list[tuple[datetime, timedelta]]:
    """[(utc_start, offset)] from the hand transcription, independent of zoneinfo."""
    out = []
    start = datetime(1800, 1, 1, tzinfo=UTC)
    for line in zone["lines"]:
        offset = _hms(line["stdoff"]) + _hms(line["save"])
        out.append((start, offset))
        if line["until"] is None:
            break
        start = datetime.fromisoformat(line["until"]).replace(tzinfo=UTC) - offset
    return out


def transcribed_offset(transitions, instant: datetime) -> timedelta:
    current = transitions[0][1]
    for start, offset in transitions:
        if instant >= start:
            current = offset
    return current


def iana_crosscheck() -> dict:
    fixture = load_fixture("iana_zone_transcriptions.json")
    results = []
    for zone in fixture["zones"]:
        tz = ZoneInfo(zone["key"])
        trans = transcribed_transitions(zone)
        limit = (datetime.fromisoformat(zone["valid_until_utc"]).replace(tzinfo=UTC)
                 if zone["valid_until_utc"] else datetime(2101, 1, 2, tzinfo=UTC))
        probes = []
        for start, _ in trans[1:]:
            probes += [start - timedelta(seconds=1), start, start + timedelta(seconds=1)]
        day = datetime(1850, 1, 1, tzinfo=UTC)
        while day < limit:
            probes += [day, day + timedelta(hours=12)]
            day += timedelta(days=15)
        probes = [p for p in probes if p < limit]
        mismatches = []
        for p in probes:
            expected = transcribed_offset(trans, p)
            actual = p.astimezone(tz).utcoffset()
            if expected != actual:
                mismatches.append({"utc": p.isoformat(), "transcribed": str(expected), "zoneinfo": str(actual)})
        results.append({
            "zone": zone["key"], "source_line": zone["source_line"], "probes": len(probes),
            "mismatches": mismatches[:20], "mismatch_count": len(mismatches),
            "transitions_utc": [{"from_utc": s.isoformat(), "offset": str(o)} for s, o in trans],
        })
    return {"evidence_class": TIMEKEEPING, "source_sha256": fixture["source_sha256"], "zones": results}


def tzdata_source_agreement() -> dict:
    """System tzdata versus the PyPI tzdata package, offsets compared monthly 1900-2100.

    The engine uses whichever zoneinfo finds first (system TZPATH), so a host
    tzdata update can change results; this records whether the two copies agree.
    """
    from importlib import resources
    import zoneinfo
    try:
        package = resources.files("tzdata.zoneinfo")
    except ModuleNotFoundError:
        return {"evidence_class": TIMEKEEPING, "compared": False, "reason": "tzdata package not installed"}
    keys = sorted(k for k in zoneinfo.available_timezones() if k.startswith("Asia/"))
    keys += [c["timezone"] for c in load_fixture("time_cases.json")["cases"] if "/" in c["timezone"]]
    differing = {}
    for key in sorted(set(keys)):
        system = ZoneInfo(key)
        with package.joinpath(*key.split("/")).open("rb") as handle:
            packaged = ZoneInfo.from_file(handle, key=key)
        t = datetime(1900, 1, 1, tzinfo=UTC)
        while t.year <= 2100:
            if t.astimezone(system).utcoffset() != t.astimezone(packaged).utcoffset():
                differing.setdefault(key, []).append(t.isoformat())
            t += timedelta(days=30, hours=7)
    return {"evidence_class": TIMEKEEPING, "compared": True, "zones": len(set(keys)),
            "zones_differing": {k: {"samples": len(v), "first": v[0], "last": v[-1]}
                                for k, v in differing.items()}}


def kolkata_local_anomalies() -> dict:
    """Nonexistent and repeated local intervals of Asia/Kolkata from 1900, found by scanning zoneinfo."""
    tz = ZoneInfo("Asia/Kolkata")
    t = datetime(1899, 12, 31, tzinfo=UTC)
    end = datetime(2101, 1, 1, tzinfo=UTC)
    prev = t.astimezone(tz).utcoffset()
    events = []
    while t < end:
        nxt = t + timedelta(hours=6)
        off = nxt.astimezone(tz).utcoffset()
        if off != prev:
            # Bisect on whole seconds: IANA transitions fall on whole seconds.
            lo, hi = int(t.timestamp()), int(nxt.timestamp())
            while hi - lo > 1:
                mid = (lo + hi) // 2
                if datetime.fromtimestamp(mid, UTC).astimezone(tz).utcoffset() == prev:
                    lo = mid
                else:
                    hi = mid
            hi = datetime.fromtimestamp(hi, UTC)
            jump = off - prev
            wall_before = (hi + prev).replace(tzinfo=None)
            events.append({
                "utc": hi.isoformat(), "from": str(prev), "to": str(off),
                "kind": "nonexistent local interval" if jump > timedelta(0) else "repeated local interval",
                "local_interval": [wall_before.isoformat(), (wall_before + abs(jump)).isoformat()]
                if jump > timedelta(0) else
                [(wall_before - abs(jump)).isoformat(), wall_before.isoformat()],
            })
            prev = off
        t = nxt
    return {"evidence_class": TIMEKEEPING, "zone": "Asia/Kolkata", "events_1900_2100": events}


def timescale(folder) -> dict:
    swe = swiss(folder)
    leap = load_fixture("iers_leap_seconds.json")
    rows = []
    for year in list(range(1900, 2101, 10)) + [1955, 1961, 1972, 1973, 2016, 2017, 2026, 2028, 2029,
                                               2031, 2032, 2033, 2034]:
        utc = datetime(year, 7, 1, 12, tzinfo=UTC)
        jd = engine_jd(swe, utc)
        jd_et, jd_ut1 = swe.utc_to_jd(year, 7, 1, 12, 0, 0.0, swe.GREG_CAL)
        rows.append({"utc": utc.isoformat(), "delta_t_s": swe.deltat_ex(jd, swe.FLG_SWIEPH) * 86400,
                     "swiss_utc_to_jd_ut1_minus_engine_s": (jd_ut1 - jd) * 86400,
                     "swiss_tt_minus_engine_ut_s": (jd_et - jd) * 86400})
    rows.sort(key=lambda r: r["utc"])
    # IERS consistency: UT1-UTC implied by Swiss Delta T and IERS TAI-UTC must stay within 0.9 s.
    implied = []
    entries = leap["entries"]
    for year in range(1972, 2027):
        for month in (1, 7):
            when = datetime(year, month, 1, tzinfo=UTC)
            tai_utc = [e["tai_minus_utc"] for e in entries if e["effective_utc"] <= when.strftime("%Y-%m-%d")][-1]
            dt = swe.deltat_ex(engine_jd(swe, when), swe.FLG_SWIEPH) * 86400
            implied.append({"utc": when.strftime("%Y-%m-%d"), "tai_minus_utc": tai_utc,
                            "implied_ut1_minus_utc_s": 32.184 + tai_utc - dt})
    worst = max(implied, key=lambda r: abs(r["implied_ut1_minus_utc_s"]))
    # Swiss built-in leap seconds versus the IERS list.
    accepted, refused_wrongly = [], []
    for e in entries[1:]:
        day = datetime.fromisoformat(e["effective_utc"]) - timedelta(days=1)
        try:
            swe.utc_to_jd(day.year, day.month, day.day, 23, 59, 60.0, swe.GREG_CAL)
            accepted.append(day.strftime("%Y-%m-%d"))
        except swe.Error:
            refused_wrongly.append(day.strftime("%Y-%m-%d"))
    not_leap = []
    for y, m, d in ((2018, 12, 31), (2020, 12, 31), (2024, 6, 30), (2025, 12, 31)):
        try:
            swe.utc_to_jd(y, m, d, 23, 59, 60.0, swe.GREG_CAL)
            not_leap.append({"date": f"{y}-{m:02d}-{d:02d}", "swiss": "accepted"})
        except swe.Error:
            not_leap.append({"date": f"{y}-{m:02d}-{d:02d}", "swiss": "refused"})
    future = []
    last_tai_utc = entries[-1]["tai_minus_utc"]
    for year in (2027, 2028, 2029, 2030, 2035, 2040, 2050, 2075, 2100):
        dt = swe.deltat_ex(engine_jd(swe, datetime(year, 1, 1, tzinfo=UTC)), swe.FLG_SWIEPH) * 86400
        future.append({"year": year, "delta_t_s": dt,
                       "ut1_minus_utc_if_no_new_leap_seconds_s": 32.184 + last_tai_utc - dt})
    return {
        "evidence_class": TIMEKEEPING + "+" + SWISS_CONFORMANCE,
        "per_epoch": rows,
        "iers_consistency_1972_2026": {"samples": len(implied), "worst": worst,
                                       "all_within_0_9_s": all(abs(r["implied_ut1_minus_utc_s"]) < 0.9 for r in implied)},
        "swiss_leap_seconds": {"iers_leap_dates": len(entries) - 1, "swiss_accepts_23_59_60": len(accepted),
                               "swiss_refuses_iers_leap": refused_wrongly, "non_leap_dates": not_leap},
        "iers_list": {"sha256": leap["source_sha256"], "updated": leap["file_updated_utc"],
                      "expires": leap["file_expires_utc"], "last_tai_minus_utc": last_tai_utc},
        "future_delta_t": future,
    }


def independent_gast(swe, jd_ut: float) -> float:
    """Greenwich apparent sidereal time in degrees from IERS Conventions 2010 eq. 5.32 (ERA + IAU 2006
    polynomial) plus the equation of the equinoxes dpsi*cos(eps). Nutation values come from Swiss;
    the complementary terms (< 0.003 arcsec) are omitted."""
    import math
    tu = jd_ut - 2451545.0
    t = (jd_ut + swe.deltat_ex(jd_ut, swe.FLG_SWIEPH) - 2451545.0) / 36525
    era = 360.0 * ((0.7790572732640 + 0.00273781191135448 * tu + tu) % 1.0)
    poly = (0.014506 + 4612.156534 * t + 1.3915817 * t ** 2 - 0.00000044 * t ** 3
            - 0.000029956 * t ** 4 - 0.0000000368 * t ** 5) / 3600
    eps_true, _, dpsi, _ = swe.calc_ut(jd_ut, swe.ECL_NUT, 0)[0][:4]
    return (era + poly + dpsi * math.cos(math.radians(eps_true))) % 360


def sidereal_time_check(folder) -> dict:
    """Swiss default sidereal time (the input to ARMC and the Lagna) versus IERS 2010."""
    swe = swiss(folder)
    rnd = random.Random(17)
    inside, outside = [], []
    for _ in range(4000):
        jd = rnd.uniform(2415020.5, 2488434.5)
        d = signed_delta(swe.sidtime(jd) * 15, independent_gast(swe, jd)) * ARCSEC
        (inside if 2396758.5 < jd < 2469807.5 else outside).append(d)
    edge = 2469807.5  # 2050-01-01 0h UT, where Swiss switches to its long-term model
    step = (signed_delta(swe.sidtime(edge + 1e-6) * 15, swe.sidtime(edge - 1e-6) * 15) * ARCSEC
            - 2e-6 * 360.98564736629 * ARCSEC)
    return {"evidence_class": INDEPENDENT_MATHEMATICS,
            "reference": "IERS Conventions 2010 eq. 5.32 (Capitaine et al. 2003), Swiss nutation",
            "max_abs_arcsec_1900_2049": max(abs(x) for x in inside),
            "range_arcsec_2050_2100": [min(outside), max(outside)],
            "samples": [len(inside), len(outside)],
            "swiss_step_at_2050_arcsec": step}


def rates(folder) -> dict:
    """Seconds-of-time sensitivity of Moon, Sun and Lagna (Swiss values, finite differences)."""
    swe = swiss(folder)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    rnd = random.Random(11)
    moon = sun = 0.0
    lagna = {lat: 0.0 for lat in (0.0, 13.0827, 28.6139, 34.1526, 45.0, 55.0, 60.0, 63.0, 66.0)}
    h = 10.0 / 86400
    for _ in range(3000):
        jd = rnd.uniform(2415020.5, 2488434.5)
        moon = max(moon, abs(signed_delta(swe.calc_ut(jd + h, swe.MOON, flags)[0][0],
                                           swe.calc_ut(jd, swe.MOON, flags)[0][0])) / 10 * ARCSEC)
        sun = max(sun, abs(signed_delta(swe.calc_ut(jd + h, swe.SUN, flags)[0][0],
                                         swe.calc_ut(jd, swe.SUN, flags)[0][0])) / 10 * ARCSEC)
        lon = rnd.uniform(-180, 180)
        for lat in lagna:
            a0 = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)[1][0]
            a1 = swe.houses_ex(jd + h, lat, lon, b"W", swe.FLG_SIDEREAL)[1][0]
            lagna[lat] = max(lagna[lat], abs(signed_delta(a1, a0)) / 10 * ARCSEC)
    return {"evidence_class": SWISS_CONFORMANCE, "samples": 3000,
            "moon_max_arcsec_per_s": moon, "sun_max_arcsec_per_s": sun,
            "lagna_max_arcsec_per_s_by_latitude": {str(k): v for k, v in lagna.items()}}


def clock_error_impact(folder) -> dict:
    """How often a clock-offset error changes a category (fraction of sampled instants)."""
    swe = swiss(folder)
    flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL
    rnd = random.Random(13)
    places = {"IN-DEL": (28.6139, 77.2090), "IN-BOM": (19.0760, 72.8777), "IN-CCU": (22.5726, 88.3639)}
    errors = {"0.9 s (IERS bound on |UT1-UTC|)": 0.9, "1 min": 60.0, "5 min": 300.0,
              "23 min 20 s (+05:53:20 vs IST)": 1400.0, "38 min 29 s (LMT 72.8777E vs IST)": 2309.0,
              "60 min (war time vs IST)": 3600.0}
    samples = 2000
    instants = [rnd.uniform(2415020.5, 2488434.5) for _ in range(samples)]
    out = {}
    for label, seconds in errors.items():
        dt = seconds / 86400
        c = {"lagna_rashi": 0, "lagna_navamsa": 0, "moon_rashi": 0, "moon_nakshatra_pada": 0}
        max_lagna = 0.0
        for i, jd in enumerate(instants):
            lat, lon = list(places.values())[i % 3]
            a0 = swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)[1][0]
            a1 = swe.houses_ex(jd + dt, lat, lon, b"W", swe.FLG_SIDEREAL)[1][0]
            m0 = swe.calc_ut(jd, swe.MOON, flags)[0][0]
            m1 = swe.calc_ut(jd + dt, swe.MOON, flags)[0][0]
            max_lagna = max(max_lagna, abs(signed_delta(a1, a0)))
            c["lagna_rashi"] += rules.sign(a0) != rules.sign(a1)
            c["lagna_navamsa"] += rules.navamsa_sign(a0) != rules.navamsa_sign(a1)
            c["moon_rashi"] += rules.sign(m0) != rules.sign(m1)
            c["moon_nakshatra_pada"] += rules.nakshatra(m0) != rules.nakshatra(m1)
        out[label] = {"seconds": seconds, "max_lagna_shift_deg": max_lagna,
                      **{k + "_changed_fraction": v / samples for k, v in c.items()}}
    return {"evidence_class": SWISS_CONFORMANCE, "places": list(places), "samples": samples, "errors": out}


def lmt_table() -> dict:
    """Local mean time offset from longitude (exact arithmetic) versus IST, for synthetic city centres."""
    grid = load_fixture("lagna_grid.json")
    rows = []
    for loc in grid["locations"]:
        if loc["group"] != "india":
            continue
        seconds = Fraction(str(loc["lon"])) * 240  # 4 minutes of time per degree
        diff = seconds - 19800
        rows.append({"id": loc["id"], "lon": loc["lon"], "lmt_offset_s": float(seconds),
                     "lmt_minus_ist_min": float(diff / 60)})
    return {"evidence_class": INDEPENDENT_MATHEMATICS,
            "note": "Mean solar time only; a historical clock may have followed a different meridian.",
            "rows": rows}


def run(folder) -> dict:
    return {
        "engine_time_cases": engine_time_cases(folder),
        "iana_crosscheck": iana_crosscheck(),
        "kolkata_local_anomalies": kolkata_local_anomalies(),
        "tzdata_source_agreement": tzdata_source_agreement(),
        "timescale": timescale(folder),
        "sidereal_time": sidereal_time_check(folder),
        "rates": rates(folder),
        "clock_error_impact": clock_error_impact(folder),
        "lmt_table": lmt_table(),
    }
