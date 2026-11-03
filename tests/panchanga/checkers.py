"""Independent checkers shared by the gate tests and the mutation controls.

Each checker returns a list of failure codes; the gate tests require an empty
list and every mutation control requires a non-empty one. Nothing here calls
production Panchanga rules or search code: values come from a test-side Swiss
call (`phase_events.SideSwiss`) and the rational oracle.
"""
from __future__ import annotations

from datetime import timedelta
from fractions import Fraction
import math

from . import oracle
from .common import parse_utc

SPANS = {"tithi": ("tithi", "start", "end"), "karana": ("karana", "start", "end"),
         "yoga": ("yoga", "start", "end"), "nakshatra": ("nakshatra", "start", "end"),
         "pada": ("nakshatra", "pada_start", "pada_end")}


def doc_sectors(doc: dict) -> dict:
    n = doc["nakshatra"]
    return {"tithi": doc["tithi"]["number"] - 1, "karana": doc["karana"]["index"] - 1,
            "yoga": doc["yoga"]["index"] - 1, "nakshatra": n["index"], "pada": n["index"] * 4 + n["pada"] - 1}


def check_document(doc: dict, side, chart: dict | None = None) -> list[str]:
    """Birth-instant indices, angles and every transition second, checked independently."""
    failures = []
    birth = parse_utc(doc["birth"]["utc"])
    sun, moon = side.sun_moon(birth)
    want = oracle.all_sectors(sun, moon)
    got = doc_sectors(doc)
    for element in want:
        if got[element] != want[element]:
            failures.append(f"INDEX_{element.upper()}")
    t = doc["tithi"]
    if t["paksha"] != ("shukla" if t["number"] <= 15 else "krishna") or t["paksha_day"] != (t["number"] - 1) % 15 + 1:
        failures.append("PAKSHA")
    e, s = oracle.elongation(sun, moon), oracle.yoga_sum(sun, moon)
    for key, ref in (("elongation_deg", e), ("yoga_sum_deg", s)):
        d = (Fraction(doc["angles"][key]) - ref) % 360
        if min(d, 360 - d) > Fraction(2, 10**8):
            failures.append(f"ANGLE_{key.upper()}")
    if chart is not None and {k: doc["nakshatra"][k] for k in ("index", "name", "pada")} != chart["moon_nakshatra"]:
        failures.append("NAKSHATRA_IDENTITY")
    for element, (block, s_key, e_key) in SPANS.items():
        k0 = want[element]
        for key, direction in ((s_key, -1), (e_key, 1)):
            at = parse_utc(doc[block][key]["utc"])
            # A start may follow a fractional-second birth by under 1 s (first whole second rule).
            if (direction == 1 and not at > birth) or (direction == -1 and not at < birth + timedelta(seconds=1)):
                failures.append(f"ORDER_{element.upper()}_{key.upper()}")
            now = oracle.all_sectors(*side.sun_moon(at))[element]
            before = oracle.all_sectors(*side.sun_moon(at - timedelta(seconds=1)))[element]
            if direction == 1 and not (before == k0 and now != k0):
                failures.append(f"TRANSITION_{element.upper()}_END")
            if direction == -1 and not (now == k0 and before != k0):
                failures.append(f"TRANSITION_{element.upper()}_START")
    return failures


def check_rules(rules_module) -> list[str]:
    """Edges and float neighbours of every sector family against the oracle (PAN-QA-01 core)."""
    failures = []
    for n, fn in ((30, lambda x: rules_module.tithi_number(x) - 1), (60, lambda x: rules_module.karana_index(x) - 1),
                  (27, lambda x: rules_module.yoga_index(x) - 1)):
        for k in range(n):
            edge = Fraction(360 * k, n)
            for x in (edge, math.nextafter(float(edge), -1.0) if k else math.nextafter(360.0, 0.0),
                      math.nextafter(float(edge), 400.0)):
                if fn(x) != oracle.sector(x, n):
                    failures.append(f"EDGE_{n}_{k}")
                    break
    for sun, moon in ((10.0, 9.5), (300.0, 10.0), (359.0, 1.0), (1.0, 359.0), (200.0, 200.0), (123.25, 45.5)):
        if rules_module.elongation(sun, moon) != oracle.elongation(sun, moon):
            failures.append("ELONGATION")
        if rules_module.yoga_sum(sun, moon) != oracle.yoga_sum(sun, moon):
            failures.append("YOGA_SUM")
        if rules_module.element_sectors(sun, moon) != oracle.all_sectors(sun, moon):
            failures.append("ELEMENT_SECTORS")
    return sorted(set(failures))
