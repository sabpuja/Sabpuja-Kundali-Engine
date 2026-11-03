"""PAN-QA-04 evaluator: the 50 PAN-REF-PHASE-2026 events against the frozen D15-a window.

For every independently rechecked case the engine is asked, through the public
`sabpuja-panchanga/1` path, for the Karana (and, at 0 and 180 deg, Tithi)
transition from two synthetic birth instants: 3 h before the earliest published
minute (the *end* of the current sector) and 3 h after the latest one (its
*start*). Both searches must return the same whole second, inside the closed
window [earliest - 60 s, latest + 60 s] (D15-a-R). Indices one second before,
at and one second after the instant are checked with a test-side Swiss call
and the independent rational oracle.

Claim boundary: agreement with publisher-printed whole minutes inside the
declared window only; no seconds-level astronomical accuracy (tolerances.json
`claims_limit`).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from . import oracle
from .common import fixture, parse_utc, request_at_utc, tolerances

OFFSET = timedelta(hours=3)


def _minute(text: str) -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


class SideSwiss:
    """Test-side Swiss evaluation (not the production session): same flags, own state reset."""

    def __init__(self, ephe: str):
        import swisseph as swe
        self.swe, self.ephe = swe, ephe

    def sun_moon(self, moment: datetime) -> tuple[float, float]:
        swe = self.swe
        swe.set_ephe_path(self.ephe)
        swe.set_sid_mode(swe.SIDM_LAHIRI, 0, 0)
        swe.set_delta_t_userdef(swe.DELTAT_AUTOMATIC)
        jd = swe.julday(moment.year, moment.month, moment.day,
                        moment.hour + moment.minute / 60 + (moment.second + moment.microsecond / 1e6) / 3600)
        out = []
        for body in (swe.SUN, swe.MOON):
            pos, flags = swe.calc_ut(jd, body, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
            if not flags & swe.FLG_SWIEPH:
                raise RuntimeError("SWISS_EPHEMERIS_FALLBACK_REFUSED")
            out.append(pos[0])
        return out[0], out[1]


def evaluate(ephe: str) -> dict:
    from sabpuja_kundali.panchanga import calculate
    tol = tolerances()
    d15 = tol["D15_a_R_C2"]
    allowed_ids = tol["source_reference"]["independently_rechecked_case_ids"]
    cases = [c for c in fixture()["cases"] if c["case_id"] in allowed_ids]
    side = SideSwiss(ephe)
    before = timedelta(seconds=d15["before_earliest_published_minute_seconds"])
    after = timedelta(seconds=d15["after_latest_published_minute_seconds"])
    near = timedelta(seconds=d15["near_window_edge_report_threshold_seconds"])
    rows = []
    for case in cases:
        angle = case["event"]["elongation_deg"]
        minutes = sorted(_minute(p["value_utc_minute"]) for p in case["published_values"])
        lo, hi = minutes[0] - before, minutes[-1] + after
        frm, to = (int(x) for x in case["panchanga_meaning"]["karana_boundary_one_based"].split("->"))
        problems = []
        if angle not in d15["allowed_reference_event_angles_degrees"]:
            problems.append("ANGLE_NOT_ALLOWED")
        if [_iso(lo), _iso(hi)] != case["proposed_tolerance"]["accept_window_utc"]:
            problems.append("FIXTURE_WINDOW_DIFFERS_FROM_FROZEN_RULE")
        if (frm % 60) + 1 != to or to != round(angle / 6) % 60 + 1:
            problems.append("FIXTURE_INDEX_MEANING_INCONSISTENT")
        doc_end = calculate(request_at_utc(minutes[0] - OFFSET), ephe)
        doc_start = calculate(request_at_utc(minutes[-1] + OFFSET), ephe)
        t_end = parse_utc(doc_end["karana"]["end"]["utc"])
        t_start = parse_utc(doc_start["karana"]["start"]["utc"])
        if doc_end["karana"]["index"] != frm or doc_start["karana"]["index"] != to:
            problems.append("KARANA_INDEX_MISMATCH")
        if t_end != t_start:
            problems.append("END_AND_START_SEARCH_DISAGREE")
        tithi = None
        if angle in (0, 180):
            tithi = {"end": doc_end["tithi"]["end"]["utc"], "start": doc_start["tithi"]["start"]["utc"],
                     "number_before": doc_end["tithi"]["number"], "number_after": doc_start["tithi"]["number"]}
            want = (30, 1) if angle == 0 else (15, 16)
            if (tithi["number_before"], tithi["number_after"]) != want:
                problems.append("TITHI_NUMBER_MISMATCH")
            if tithi["end"] != _iso(t_end) or tithi["start"] != _iso(t_end):
                problems.append("TITHI_AND_KARANA_INSTANT_DIFFER")
        idx = {}
        for label, delta in (("minus_1s", -1), ("at", 0), ("plus_1s", 1)):
            sun, moon = side.sun_moon(t_end + timedelta(seconds=delta))
            idx[label] = oracle.karana_index(sun, moon)
        if (idx["minus_1s"], idx["at"], idx["plus_1s"]) != (frm, to, to):
            problems.append("INDEX_AT_PLUS_MINUS_1S_MISMATCH")
        inside = lo <= t_end <= hi
        edge_distance = min(t_end - lo, hi - t_end)
        status = "PASS" if inside and not problems else "FAIL"
        rows.append({
            "case_id": case["case_id"], "phase": case["event"]["published_phase_name"], "angle_deg": angle,
            "published_minutes_utc": [m.strftime("%Y-%m-%dT%H:%MZ") for m in minutes],
            "window_utc": [_iso(lo), _iso(hi)],
            "engine_utc": _iso(t_end),
            "residual_vs_earliest_minute_s": (t_end - minutes[0]).total_seconds(),
            "residual_vs_latest_minute_s": (t_end - minutes[-1]).total_seconds(),
            "margin_to_window_edge_s": edge_distance.total_seconds(),
            "near_window_edge": inside and edge_distance <= near,
            "karana_boundary_one_based": f"{frm}->{to}",
            "indices_minus_at_plus_1s": [idx["minus_1s"], idx["at"], idx["plus_1s"]],
            "tithi": tithi,
            "problems": problems,
            "status": status,
        })
    counts = {s: sum(r["status"] == s for r in rows) for s in ("PASS", "FAIL")}
    complete = len(rows) == d15["expected_case_count"] == len(allowed_ids)
    verdict = "PASS" if complete and counts["FAIL"] == 0 else ("FAIL" if counts["FAIL"] else "BLOCKED")
    return {"gate": "PAN-QA-04", "verdict": verdict, "counts": counts, "case_count": len(rows),
            "expected_case_count": d15["expected_case_count"],
            "near_window_edge_cases": [r["case_id"] for r in rows if r["near_window_edge"]],
            "claim_boundary": tol["source_reference"]["claims_limit"],
            "time_scale_caveat": d15["time_scale_caveat"], "rows": rows}
