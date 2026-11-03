"""Build tests/sci_gold/matrix.json (KUN-SCI-GOLD-001 synthetic fixture matrix).

DESIGN-TIME ONLY. This script chooses the synthetic birth instants. For the
boundary fixtures it searches with the pinned pyswisseph binding for the moment
a body or the Lagna crosses an edge and then places the birth a stated number
of seconds before or after it. That search only *selects* inputs: no value it
computes is written as an expected result. Every expected longitude comes from
the official swetest receipts (capture.py), every expected category from the
isolated reference rules, and every expected UTC from the IANA 2026e rule text
quoted in the fixture (verified by tzif_reference.py).

Re-running it with the same pinned binding and data must reproduce matrix.json
byte for byte (test_sci_gold.MatrixTest.test_builder_is_deterministic runs it
only when SABPUJA_TEST_EPHE_PATH is set).

    SABPUJA_EPHE_PATH=/abs/ephe python tests/sci_gold/design/build_matrix.py > tests/sci_gold/matrix.json
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
import sys

IST = "Asia/Kolkata"
IST_LINE = ("asia", "Zone\tAsia/Kolkata\t5:53:28 -\tLMT\t1854 Jun 28 # Kolkata ... final line '\t\t\t5:30\t-\tIST'"
            " (no rule since 1945 Oct 15): UTC = local - 05:30")

# Ten Indian places, London and Tromsoe come from the committed prototype gazetteer
# (prototype/kundali_prototype/places.json: GeoNames cities15000 via geonamescache
# 2.0.0, cross-checked with Natural Earth v5.1.2). Others are SYNTHETIC coordinates
# (rounded city points) used only as inputs; no gazetteer claim is made for them.
PLACES = {
    "in-new-delhi": (28.63576, 77.22445, IST, "places.json"),
    "in-mumbai": (19.07283, 72.88261, IST, "places.json"),
    "in-kolkata": (22.56263, 88.36304, IST, "places.json"),
    "in-chennai": (13.08784, 80.27847, IST, "places.json"),
    "in-bengaluru": (12.97194, 77.59369, IST, "places.json"),
    "in-hyderabad": (17.38405, 78.45636, IST, "places.json"),
    "in-jaipur": (26.91962, 75.78781, IST, "places.json"),
    "in-lucknow": (26.83928, 80.92313, IST, "places.json"),
    "in-varanasi": (25.31668, 83.01041, IST, "places.json"),
    "in-guwahati": (26.1844, 91.7458, IST, "places.json"),
    "gb-london": (51.50853, -0.12574, "Europe/London", "places.json"),
    "no-tromso": (69.6489, 18.95508, "Europe/Oslo", "places.json"),
    "syn-kathmandu": (27.7, 85.3, "Asia/Kathmandu", "synthetic"),
    "syn-dhaka": (23.8, 90.4, "Asia/Dhaka", "synthetic"),
    "syn-new-york": (40.7, -74.0, "America/New_York", "synthetic"),
    "syn-sydney": (-33.87, 151.21, "Australia/Sydney", "synthetic"),
    "syn-helsinki": (60.17, 24.94, "Europe/Helsinki", "synthetic"),
    "syn-ushuaia": (-54.8, -68.3, "America/Argentina/Ushuaia", "synthetic"),
    "syn-band-north": (66.0, 25.0, "Europe/Helsinki", "synthetic"),
    "syn-band-south": (-66.0, 140.0, "Antarctica/DumontDUrville", "synthetic"),
    "syn-murmansk": (68.97, 33.08, "Europe/Moscow", "synthetic"),
}

IANA = {
    "IST": [IST_LINE],
    "Kathmandu": [("asia", "Zone\tAsia/Kathmandu\t5:41:16 -\tLMT\t1920 / 5:30\t-\t%z\t1986 / 5:45\t-\t%z: "
                   "the clock jumps from 1986-01-01T00:00 +05:30 to 00:15 +05:45")],
    "Dhaka": [("asia", "Rule\tDhaka\t2009\tonly\t-\tJun\t19\t23:00\t1:00\t- ; Rule\tDhaka\t2009\tonly\t-\tDec\t31\t24:00\t0\t- ;"
               " Zone Asia/Dhaka 6:00 Dhaka %z: 2009-06-19 23:00 +06 -> 2009-06-20 00:00 +07")],
    "US": [("northamerica", "Rule\tUS\t2007\tmax\t-\tMar\tSun>=8\t2:00\t1:00\tD ; Rule\tUS\t2007\tmax\t-\tNov\tSun>=1\t2:00\t0\tS ;"
            " Zone America/New_York -5:00 US E%sT")],
    "EU": [("europe", "Rule\tEU\t1981\tmax\t-\tMar\tlastSun\t 1:00u\t1:00\tS ; Rule\tEU\t1996\tmax\t-\tOct\tlastSun\t 1:00u\t0\t- ;"
            " Zone Europe/London 0:00 EU GMT/BST (since 1996)")],
    "AN": [("australasia", "Rule\tAN\t2008\tmax\t-\tApr\tSun>=1\t2:00s\t0\tS ; Rule\tAN\t2008\tmax\t-\tOct\tSun>=1\t2:00s\t1:00\tD ;"
            " Zone Australia/Sydney 10:00 AN AE%sT (since 1971)")],
}


def utc_text(dt: datetime) -> str:
    text = dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat()
    return text + "Z"


def local_text(utc: datetime, offset: timedelta) -> str:
    local = (utc + offset).replace(tzinfo=None)
    sign = "+" if offset >= timedelta(0) else "-"
    total = abs(int(offset.total_seconds()))
    return f"{local.isoformat()}{sign}{total // 3600:02d}:{total % 3600 // 60:02d}"


def chart(fid, group, purpose, place, local, utc, iana, focus=(), design=None):
    lat, lon, tz, src = PLACES[place]
    return {"id": fid, "group": group, "purpose": purpose, "synthetic": True,
            "input": {"birth_datetime": local, "timezone": tz, "latitude": lat, "longitude": lon},
            "place": {"key": place, "coordinate_source": src},
            "expect": {"kind": "chart"},
            "time_reference": {"expected_utc": utc, "source": "IANA tz 2026e source text (eggert/tz tag 2026e)",
                               "rule_text": [list(x) for x in iana]},
            "focus": list(focus), "design": design}


def refusal(fid, group, purpose, req, code, basis, place=None):
    return {"id": fid, "group": group, "purpose": purpose, "synthetic": True, "input": req,
            "place": {"key": place, "coordinate_source": PLACES[place][3] if place else "synthetic"},
            "expect": {"kind": "refusal", "code": code, "basis": basis},
            "time_reference": None, "focus": [], "design": None}


# --- design-time search (pinned pyswisseph; selection only) ---------------------

def _swe():
    import swisseph as swe
    ephe = os.environ["SABPUJA_EPHE_PATH"]
    swe.set_ephe_path(ephe)
    swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
    return swe


def _jd(swe, dt):
    u = dt.astimezone(timezone.utc)
    return swe.julday(u.year, u.month, u.day, u.hour + u.minute / 60 + (u.second + u.microsecond / 1e6) / 3600)


def _from_jd(swe, jd):
    y, m, d, h = swe.revjul(jd)
    return datetime(y, m, d, tzinfo=timezone.utc) + timedelta(hours=h)


def _lon(swe, what, jd, lat=None, lon=None):
    if what == "lagna":
        return swe.houses_ex(jd, lat, lon, b"W", swe.FLG_SIDEREAL)[1][0]
    body = {"sun": swe.SUN, "moon": swe.MOON, "mercury": swe.MERCURY, "mars": swe.MARS,
            "rahu_mean": swe.MEAN_NODE, "jupiter": swe.JUPITER, "saturn": swe.SATURN}[what]
    return swe.calc_ut(jd, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)[0][0]


def crossing(swe, what, target, start, step_days, lat=None, lon=None, direction=None, limit=40000):
    """First instant after start when what's sidereal longitude crosses target (bisection to ~1 microsecond)."""
    def f(jd):
        return (_lon(swe, what, jd, lat, lon) - target + 180) % 360 - 180
    a = _jd(swe, start)
    fa = f(a)
    for _ in range(limit):
        b = a + step_days
        fb = f(b)
        if fa != 0 and (fa < 0) != (fb < 0) and abs(fa - fb) < 90:
            if direction is None or (direction == "forward") == (fb > fa):
                lo, hi = a, b
                for _ in range(80):
                    mid = (lo + hi) / 2
                    if (f(mid) < 0) == (fa < 0):
                        lo = mid
                    else:
                        hi = mid
                return _from_jd(swe, (lo + hi) / 2)
        a, fa = b, fb
    raise RuntimeError("no crossing found")


def retrograde_edge(swe, what, start, limit_days=1500):
    """The first Rashi edge (multiple of 30 deg) that what crosses while moving backwards after start."""
    jd = _jd(swe, start)
    prev = _lon(swe, what, jd)
    for _ in range(limit_days * 4):
        jd += 0.25
        cur = _lon(swe, what, jd)
        if int(cur // 30) != int(prev // 30) and ((cur - prev + 180) % 360 - 180) < 0:
            return float(round(prev / 30) * 30 % 360), _from_jd(swe, jd - 1)
        prev = cur
    raise RuntimeError("no retrograde edge found")


def boundary_pair(swe, fid, purpose, place, what, target, start, step, seconds, focus, direction=None, iana="IST"):
    lat, lon, tz, _ = PLACES[place]
    if target is None:
        target, start = retrograde_edge(swe, what, start)
        purpose = f"{purpose} ({target:g} deg)"
    t0 = crossing(swe, what, target, start, step, lat, lon, direction)
    t0 = t0.replace(microsecond=0) + timedelta(seconds=round(t0.microsecond / 1e6))
    out = []
    for suffix, s in (("a", -seconds), ("b", seconds)):
        utc = t0 + timedelta(seconds=s)
        out.append(chart(f"{fid}{suffix}", "boundary", f"{purpose}; {abs(s)} s {'before' if s < 0 else 'after'} the crossing",
                         place, local_text(utc, timedelta(hours=5, minutes=30)), utc_text(utc), IANA[iana], focus,
                         {"selected_with": "pinned pyswisseph 2.10.3.2 design-time search; NOT a reference value",
                          "target": f"{what} sidereal longitude crosses {target} deg", "offset_seconds": s,
                          "direction": direction}))
    return out


def exact_edge(swe, fid, place, what, target, start, step, focus):
    """A birth within about a microsecond of an edge, to exercise BOUNDARY-INDETERMINATE."""
    lat, lon, tz, _ = PLACES[place]
    t0 = crossing(swe, what, target, start, step, lat, lon)
    return chart(fid, "boundary-exact", f"{what} within ~1 microsecond of the {target} deg edge (expected to be undecidable at the frozen tolerance)",
                 place, local_text(t0, timedelta(hours=5, minutes=30)), utc_text(t0), IANA["IST"], focus,
                 {"selected_with": "pinned pyswisseph 2.10.3.2 design-time search; NOT a reference value",
                  "target": f"{what} sidereal longitude crosses {target} deg", "offset_seconds": 0})


def build() -> list[dict]:
    swe = _swe()
    ist = timedelta(hours=5, minutes=30)
    fx = []
    # 1. Typical Indian charts: ten places, five decades, different months, local times.
    typical = [
        ("in-new-delhi", "1975-03-14T06:10:00"), ("in-mumbai", "1983-07-22T23:45:00"),
        ("in-kolkata", "1991-11-05T12:00:00"), ("in-chennai", "1999-02-28T04:20:00"),
        ("in-bengaluru", "2004-08-15T18:30:00"), ("in-hyderabad", "2012-02-29T09:05:00"),
        ("in-jaipur", "2026-10-02T15:15:15"), ("in-lucknow", "2047-01-26T07:07:07"),
        ("in-varanasi", "2069-09-09T21:40:00"), ("in-guwahati", "2099-12-31T11:11:00"),
    ]
    for n, (place, local) in enumerate(typical, 1):
        utc = datetime.fromisoformat(local).replace(tzinfo=timezone(ist)).astimezone(timezone.utc)
        fx.append(chart(f"GOLD-T{n:02d}", "typical", f"typical chart, {PLACES[place][2]} place {place}",
                        place, local + "+05:30", utc_text(utc), IANA["IST"]))
    # 2. Midnight and date-line handling in IST (the UTC date is the previous day).
    for fid, place, local, why in (
            ("GOLD-M01", "in-new-delhi", "2001-12-31T23:59:59", "one second before local midnight, year end"),
            ("GOLD-M02", "in-new-delhi", "2002-01-01T00:00:00", "local midnight, new year; UTC is 2001-12-31T18:30Z"),
            ("GOLD-M03", "in-chennai", "2024-02-29T00:00:00.000001", "one microsecond after midnight on 29 February"),
            ("GOLD-M04", "in-kolkata", "1970-01-01T00:00:00", "first local instant accepted by the historical-clock gate"),
            ("GOLD-M05", "in-guwahati", "2100-12-31T23:59:59.999999", "last local instant of the supported window")):
        utc = datetime.fromisoformat(local).replace(tzinfo=timezone(ist)).astimezone(timezone.utc)
        fx.append(chart(fid, "midnight", why, place, local + "+05:30", utc_text(utc), IANA["IST"]))
    # 3. Boundary charts (selected by design-time search; expected values from swetest).
    fx += boundary_pair(swe, "GOLD-B01", "Moon crosses 0 deg (Meena -> Mesha, 0/360 wrap, Revati 4 -> Ashwini 1)",
                        "in-mumbai", "moon", 0.0, datetime(2031, 1, 1, tzinfo=timezone.utc), 0.25, 2, ["moon"])
    fx += boundary_pair(swe, "GOLD-B02", "Moon crosses 13 deg 20 min (Ashwini 4 -> Bharani 1; D9 Karka -> Simha)",
                        "in-hyderabad", "moon", 40 / 3, datetime(1997, 5, 1, tzinfo=timezone.utc), 0.25, 2, ["moon"])
    fx += boundary_pair(swe, "GOLD-B03", "Moon crosses 3 deg 20 min (Pada 1 -> 2 inside Ashwini; D9 Mesha -> Vrishabha)",
                        "in-lucknow", "moon", 10 / 3, datetime(2058, 8, 1, tzinfo=timezone.utc), 0.25, 2, ["moon"])
    fx += boundary_pair(swe, "GOLD-B04", "Sun crosses 0 deg (Mesha sankranti)",
                        "in-varanasi", "sun", 0.0, datetime(2026, 4, 1, tzinfo=timezone.utc), 1.0, 60, ["sun"])
    fx += boundary_pair(swe, "GOLD-B05", "Sun crosses 120 deg (Karka -> Simha)",
                        "in-bengaluru", "sun", 120.0, datetime(2077, 8, 1, tzinfo=timezone.utc), 1.0, 60, ["sun"])
    fx += boundary_pair(swe, "GOLD-B06", "Lagna crosses 90 deg (Mithuna -> Karka): every D1 house changes",
                        "in-new-delhi", "lagna", 90.0, datetime(2005, 6, 10, tzinfo=timezone.utc), 1 / 1440, 2, ["lagna"])
    fx += boundary_pair(swe, "GOLD-B07", "Lagna crosses 196 deg 40 min (a D9 edge inside Tula): every D9 house changes, D1 does not",
                        "in-chennai", "lagna", 196 + 2 / 3, datetime(2016, 9, 3, tzinfo=timezone.utc), 1 / 1440, 1, ["lagna"])
    fx += boundary_pair(swe, "GOLD-B08", "Mean Rahu crosses 30 deg (Vrishabha -> Mesha, retrograde node); Ketu crosses 210 deg",
                        "in-kolkata", "rahu_mean", 30.0, datetime(2040, 1, 1, tzinfo=timezone.utc), 2.0, 600,
                        ["rahu_mean", "ketu_mean"])
    fx += boundary_pair(swe, "GOLD-B09", "Mercury retrograde crosses a Rashi edge backwards",
                        "in-jaipur", "mercury", None, datetime(2027, 1, 1, tzinfo=timezone.utc), 0.5, 300, ["mercury"],
                        direction="backward")
    fx += boundary_pair(swe, "GOLD-B10", "Mars retrograde crosses a Rashi edge backwards",
                        "in-guwahati", "mars", None, datetime(2033, 1, 1, tzinfo=timezone.utc), 0.5, 300, ["mars"],
                        direction="backward")
    fx.append(exact_edge(swe, "GOLD-E01", "in-new-delhi", "moon", 120.0, datetime(2008, 1, 1, tzinfo=timezone.utc), 0.25, ["moon"]))
    # 4. Time zones, DST and historical offsets (expected UTC derived by hand from the quoted IANA text).
    def tz_chart(fid, purpose, place, local, utc, iana):
        fx.append(chart(fid, "timezone", purpose, place, local, utc, IANA[iana]))
    tz_chart("GOLD-Z01", "Kathmandu, last standard minute before the 1986 change to +05:45", "syn-kathmandu",
             "1985-12-31T23:59:00+05:30", "1985-12-31T18:29:00Z", "Kathmandu")
    tz_chart("GOLD-Z02", "Kathmandu, first minute after the 1986 change", "syn-kathmandu",
             "1986-01-01T00:15:00+05:45", "1985-12-31T18:30:00Z", "Kathmandu")
    tz_chart("GOLD-Z03", "Dhaka 2009 daylight time (+07)", "syn-dhaka",
             "2009-08-01T12:00:00+07:00", "2009-08-01T05:00:00Z", "Dhaka")
    tz_chart("GOLD-Z04", "New York, repeated hour 2026-11-01 01:30, first (EDT) instance", "syn-new-york",
             "2026-11-01T01:30:00-04:00", "2026-11-01T05:30:00Z", "US")
    tz_chart("GOLD-Z05", "New York, repeated hour 2026-11-01 01:30, second (EST) instance", "syn-new-york",
             "2026-11-01T01:30:00-05:00", "2026-11-01T06:30:00Z", "US")
    tz_chart("GOLD-Z06", "London, repeated hour 2026-10-25 01:30 BST instance", "gb-london",
             "2026-10-25T01:30:00+01:00", "2026-10-25T00:30:00Z", "EU")
    tz_chart("GOLD-Z07", "London, repeated hour 2026-10-25 01:30 GMT instance", "gb-london",
             "2026-10-25T01:30:00+00:00", "2026-10-25T01:30:00Z", "EU")
    tz_chart("GOLD-Z08", "Sydney (southern hemisphere), repeated hour 2026-04-05 02:30 AEDT instance", "syn-sydney",
             "2026-04-05T02:30:00+11:00", "2026-04-04T15:30:00Z", "AN")
    tz_chart("GOLD-Z09", "Sydney, repeated hour 2026-04-05 02:30 AEST instance", "syn-sydney",
             "2026-04-05T02:30:00+10:00", "2026-04-04T16:30:00Z", "AN")
    tz_chart("GOLD-Z10", "Asia/Calcutta (IANA backward link to Asia/Kolkata) gives the same UTC and chart as GOLD-T03",
             "in-kolkata", "1991-11-05T12:00:00+05:30", "1991-11-05T06:30:00Z", "IST")
    fx[-1]["input"]["timezone"] = "Asia/Calcutta"
    fx[-1]["time_reference"]["rule_text"].append(["backward", "Link\tAsia/Kolkata\t\tAsia/Calcutta"])
    # 5. Latitude: southern, high (disclosure) and the band edges.
    tz_chart("GOLD-L01", "southern latitude -54.8 (Ushuaia, fixed -03)", "syn-ushuaia",
             "2030-06-21T12:00:00-03:00", "2030-06-21T15:00:00Z", "IST")
    fx[-1]["time_reference"]["rule_text"] = [["southamerica", "Zone America/Argentina/Ushuaia ... -3:00 Arg %z 2008 Oct 18 / -3:00 - %z (no DST since 2009)"]]
    tz_chart("GOLD-L02", "high latitude 60.17 N accepted with HIGH_LATITUDE_TIME_SENSITIVITY", "syn-helsinki",
             "2035-12-21T12:00:00+02:00", "2035-12-21T10:00:00Z", "EU")
    fx[-1]["time_reference"]["rule_text"] = [["europe", "Zone Europe/Helsinki 2:00 EU EE%sT (since 1983): 21 December is standard time, +02"]]
    tz_chart("GOLD-L03", "latitude exactly +66.0 (band edge, inclusive)", "syn-band-north",
             "2044-03-20T06:00:00+02:00", "2044-03-20T04:00:00Z", "EU")
    fx[-1]["time_reference"]["rule_text"] = [["europe", "Zone Europe/Helsinki 2:00 EU EE%sT: 20 March 2044 is before the last Sunday of March, +02"]]
    tz_chart("GOLD-L04", "latitude exactly -66.0 (band edge, inclusive)", "syn-band-south",
             "2052-09-23T18:00:00+10:00", "2052-09-23T08:00:00Z", "IST")
    fx[-1]["time_reference"]["rule_text"] = [["backward", "Link\tPacific/Port_Moresby\tAntarctica/DumontDUrville"], ["australasia", "Zone Pacific/Port_Moresby 9:48:40 - LMT 1880 / 9:48:32 - PMMT 1895 / 10:00 - %z"]]
    # 6. Refusals (expected codes from docs/api-contract.md, KUN-03 P5 order and SCI-01g/SCI-03).
    d = PLACES["in-new-delhi"]
    req = lambda dt, tz=IST, lat=d[0], lon=d[1]: {"birth_datetime": dt, "timezone": tz, "latitude": lat, "longitude": lon}
    fx += [
        refusal("GOLD-R01", "timezone", "New York DST gap 2026-03-08 02:30 does not exist",
                req("2026-03-08T02:30:00-05:00", "America/New_York", 40.7, -74.0), "TIME_NONEXISTENT_LOCAL",
                "US rule Mar Sun>=8 2:00: 02:00 EST -> 03:00 EDT", "syn-new-york"),
        refusal("GOLD-R02", "timezone", "London DST gap 2026-03-29 01:30 does not exist",
                req("2026-03-29T01:30:00+00:00", "Europe/London", 51.50853, -0.12574), "TIME_NONEXISTENT_LOCAL",
                "EU rule Mar lastSun 1:00u", "gb-london"),
        refusal("GOLD-R03", "timezone", "Sydney DST gap 2026-10-04 02:30 does not exist (southern spring)",
                req("2026-10-04T02:30:00+10:00", "Australia/Sydney", -33.87, 151.21), "TIME_NONEXISTENT_LOCAL",
                "AN rule Oct Sun>=1 2:00s", "syn-sydney"),
        refusal("GOLD-R04", "timezone", "Kathmandu 1986-01-01 00:10 falls in the 15-minute historical gap",
                req("1986-01-01T00:10:00+05:30", "Asia/Kathmandu", 27.7, 85.3), "TIME_NONEXISTENT_LOCAL",
                "Zone Asia/Kathmandu 5:30 until 1986, then 5:45", "syn-kathmandu"),
        refusal("GOLD-R05", "timezone", "Dhaka 2009-06-19 23:30 falls in the DST gap",
                req("2009-06-19T23:30:00+06:00", "Asia/Dhaka", 23.8, 90.4), "TIME_NONEXISTENT_LOCAL",
                "Rule Dhaka 2009 Jun 19 23:00 1:00", "syn-dhaka"),
        refusal("GOLD-R06", "timezone", "IST with a wrong offset (+05:00) is refused, not corrected",
                req("2010-05-05T10:00:00+05:00"), "TIME_OFFSET_MISMATCH", "P5 step 10; IST is +05:30", "in-new-delhi"),
        refusal("GOLD-R07", "timezone", "New York fold with an offset that is neither EDT nor EST",
                req("2026-11-01T01:30:00-06:00", "America/New_York", 40.7, -74.0), "TIME_OFFSET_MISMATCH",
                "P5 step 10", "syn-new-york"),
        refusal("GOLD-R08", "timezone", "no offset: never guessed", req("2010-05-05T10:00:00"), "TIME_OFFSET_REQUIRED",
                "P5 step 2", "in-new-delhi"),
        refusal("GOLD-R09", "timezone", "UTC is not a birthplace zone (no silent UTC fallback)",
                req("2010-05-05T04:30:00Z", "UTC"), "TIMEZONE_NOT_LOCATION_BASED", "D3 v2, P5 step 7", "in-new-delhi"),
        refusal("GOLD-R10", "timezone", "unknown zone key", req("2010-05-05T10:00:00+05:30", "India/Delhi"),
                "TIMEZONE_INVALID", "P5 step 6; key not in the pinned TZif manifest", "in-new-delhi"),
        refusal("GOLD-R11", "timezone", "IST one second before 1970-01-01 (historical clock unverified)",
                req("1969-12-31T23:59:59+05:30"), "HISTORICAL_CLOCK_UNVERIFIED", "SCI-03 Option B, P8", "in-new-delhi"),
        refusal("GOLD-R12", "timezone", "IST 1956 (historical IST period, still refused under Option B)",
                req("1956-04-01T10:00:00+05:30"), "HISTORICAL_CLOCK_UNVERIFIED", "SCI-03 Option B", "in-new-delhi"),
        refusal("GOLD-R13", "latitude", "latitude 69.6489 N (Tromsoe) outside the band",
                req("2030-01-01T12:00:00+01:00", "Europe/Oslo", 69.6489, 18.95508), "LATITUDE_OUTSIDE_SUPPORTED_BAND",
                "SCI-01g", "no-tromso"),
        refusal("GOLD-R14", "latitude", "latitude 66.0000001 just outside the band",
                req("2044-03-20T06:00:00+02:00", "Europe/Helsinki", 66.0000001, 25.0), "LATITUDE_OUTSIDE_SUPPORTED_BAND",
                "SCI-01g", "syn-band-north"),
        refusal("GOLD-R15", "latitude", "latitude -66.5 (southern) outside the band",
                req("2052-09-23T18:00:00+10:00", "Antarctica/DumontDUrville", -66.5, 140.0), "LATITUDE_OUTSIDE_SUPPORTED_BAND",
                "SCI-01g", "syn-band-south"),
        refusal("GOLD-R16", "latitude", "Murmansk 68.97 N outside the band",
                req("2030-01-01T12:00:00+03:00", "Europe/Moscow", 68.97, 33.08), "LATITUDE_OUTSIDE_SUPPORTED_BAND",
                "SCI-01g", "syn-murmansk"),
        refusal("GOLD-R17", "window", "local date 2101-01-01 outside the window",
                req("2101-01-01T00:00:00+05:30"), "DATE_OUTSIDE_SUPPORTED_RANGE", "SCI-03", "in-new-delhi"),
        refusal("GOLD-R18", "timezone", "leap second 23:59:60 refused", req("2016-12-31T23:59:60+05:30"),
                "TIME_LEAP_SECOND_UNSUPPORTED", "P5 step 3", "in-new-delhi"),
    ]
    return fx


def main() -> int:
    doc = {
        "schema": "sabpuja-sci-gold-matrix/1",
        "task": "KUN-SCI-GOLD-001",
        "status": "PREDECLARED before the first comparison run; all records synthetic, none a real birth",
        "baseline": "PR #58 fde3ec670618a02f2b913e9bbbedd1521d3840c7",
        "built_with": "tests/sci_gold/design/build_matrix.py (pyswisseph 2.10.3.2 design-time search only)",
        "fixtures": build(),
    }
    json.dump(doc, sys.stdout, indent=1, ensure_ascii=False, sort_keys=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
