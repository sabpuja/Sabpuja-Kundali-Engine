"""PAN-QA-07 evaluator: D15-b-R Swiss-on-Swiss conformance against the official swetest.

Swiss-on-Swiss implementation conformance, NOT independent astronomical accuracy:
the engine and swetest share the Swiss C library 2.10.03 and the pinned files.

Reference side (no production Panchanga code): the separately built official
swetest (receipt-verified, `tests/swiss_conformance` parser), run as
`-ut -sid1 -i65538 -p01 -fPl -ep -g,` (Sun and Moon; the frozen KUN-01-SWISS-01
switches restricted to bodies 0 and 1), values parsed as exact decimals,
classified with the independent rational oracle, and an independent bisection
(1 h steps, its own exact JD from the Unix epoch, converged to 1 ms) for every
transition. Frozen thresholds from tests/panchanga/tolerances.json (D15_b_R_C3):

  binding Sun/Moon vs swetest            <= 1e-9 deg
  engine-emitted Sun/Moon (chart 8 dp)   <= 1e-8 deg
  engine-emitted E and S (8 dp)          <= 2e-8 deg
  indices identical, except BOUNDARY-INDETERMINATE when the swetest value lies
  within the applicable tolerance of a sector edge (E/S indices 2e-8, Moon
  indices 1e-9, the binding tolerance of the chart harness)
  transition vs independent swetest bisection  <= 1 s, gated on the engine's whole
  second against the oracle's first whole second under the same D09 rule (both
  sides output whole seconds); the residual to the oracle's continuous crossing
  estimate (bracket <= 1 ms) is reported for every transition.
"""
from __future__ import annotations

from datetime import timedelta
from fractions import Fraction
from pathlib import Path
import json
import math

from tests.swiss_conformance import swetest_cli
from tests.swiss_conformance.inputs import validate_receipt

from . import oracle
from .common import gold_chart_requests, fixture, parse_utc, request_at_utc, tolerances

UNIX_EPOCH_JD = Fraction(4881175, 2)
ARGS = ("-ut", "-sid1", "-i65538", "-p01", "-fPl", "-ep", "-g,")
COUNTS = {"tithi": 30, "karana": 60, "yoga": 27, "nakshatra": 27, "pada": 108}
DOC_KEYS = {"tithi": ("tithi", "start", "end"), "karana": ("karana", "start", "end"),
            "yoga": ("yoga", "start", "end"), "nakshatra": ("nakshatra", "start", "end"),
            "pada": ("nakshatra", "pada_start", "pada_end")}


class ReferenceBlocked(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class Swetest:
    """Receipt-verified official swetest, Sun and Moon only, cached per JD."""

    def __init__(self, path: str | None, receipt_path: str | None, ephe: str):
        if not path or not Path(path).is_file():
            raise ReferenceBlocked("SWETEST_MISSING")
        if not receipt_path or not Path(receipt_path).is_file():
            raise ReferenceBlocked("SWETEST_RECEIPT_MISSING")
        try:
            receipt = json.loads(Path(receipt_path).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise ReferenceBlocked("SWETEST_RECEIPT_INVALID") from None
        source, errors = validate_receipt(receipt, swetest_cli.sha256_file(Path(path)))
        if errors:
            raise ReferenceBlocked(errors[0])
        self.path, self.ephe, self.source = path, ephe, source
        self.sha256 = receipt["swetest_sha256"]
        self.calls = 0
        self._cache: dict[float, tuple[Fraction, Fraction]] = {}

    def sun_moon(self, jd: float) -> tuple[Fraction, Fraction]:
        if jd in self._cache:
            return self._cache[jd]
        argv = [self.path, f"-edir{self.ephe}", swetest_cli.jd_arg(jd), *ARGS]
        run = swetest_cli.run(argv, self.ephe)
        self.calls += 1
        if run.exit_code != 0:
            raise ReferenceBlocked("SWETEST_EXIT_NONZERO")
        if run.warnings:
            raise ReferenceBlocked("SWETEST_WARNING")
        if run.version != "2.10.03" or run.ayanamsa_name != "Lahiri":
            raise ReferenceBlocked("SWETEST_VERSION_OR_AYANAMSA")
        if set(run.values) != {"Sun", "Moon"}:
            raise ReferenceBlocked("SWETEST_OUTPUT_INCOMPLETE")
        # Exact decimal text, not the float: re-read from the redacted stdout line.
        exact = {}
        for line in run.stdout.splitlines():
            name, _, value = line.partition(",")
            if name.strip() in ("Sun", "Moon"):
                exact[name.strip()] = Fraction(value.strip())
        out = (exact["Sun"], exact["Moon"])
        self._cache[jd] = out
        return out


def jd_of_seconds(t: Fraction) -> float:
    """Independent JD(UT): exact rational from Unix seconds, rounded once to a double."""
    return float(UNIX_EPOCH_JD + t / 86400)


def oracle_transition(ref: Swetest, element: str, t0: Fraction, direction: int) -> dict:
    """Independent bisection on swetest values: 1 h steps (max 60 h), then to <= 1 ms."""
    n = COUNTS[element]
    sec = lambda t: oracle.all_sectors(*ref.sun_moon(jd_of_seconds(t)))[element]
    k0 = sec(t0)
    inside, outside = t0, None
    for i in range(1, 61):
        t = t0 + direction * 3600 * i
        if sec(t) != k0:
            outside = t
            break
        inside = t
    if outside is None:
        raise ReferenceBlocked("ORACLE_NO_SECTOR_CHANGE")
    lo, hi = (inside, outside) if direction == 1 else (outside, inside)
    p_lo = sec(lo) == k0
    while hi - lo > Fraction(1, 1000):
        mid = (lo + hi) / 2
        if (sec(mid) == k0) == p_lo:
            lo = mid
        else:
            hi = mid
    s = math.floor(lo) + 1
    if s < hi and (sec(Fraction(s)) == k0) == p_lo:
        s += 1
    return {"lo": lo, "hi": hi, "first_whole_second": s, "n": n}


def _angdiff(a: Fraction, b: Fraction) -> Fraction:
    d = (a - b) % 360
    return min(d, 360 - d)


def instant_sets() -> list[tuple[str, dict]]:
    sets = [(f"GOLD:{fid}", req) for fid, req, _ in gold_chart_requests()]
    for case in fixture()["cases"]:
        minute = min(p["value_utc_minute"] for p in case["published_values"])
        t = parse_utc(minute.replace("Z", ":00Z")) - timedelta(hours=3)
        sets.append((f"PHASE:{case['case_id']}", request_at_utc(t)))
    return sets


def boundary_instants(docs: list[tuple[str, dict]], limit: int = 6) -> list[tuple[str, dict]]:
    """Births exactly on, and one second before, engine transition seconds (edge behaviour)."""
    out = []
    for label, doc in docs[:limit]:
        for element, (block, _, end_key) in DOC_KEYS.items():
            t = parse_utc(doc[block][end_key]["utc"])
            if t.year < 1970:
                continue
            out.append((f"EDGE:{label}:{element}:at", request_at_utc(t)))
            out.append((f"EDGE:{label}:{element}:minus1", request_at_utc(t - timedelta(seconds=1))))
    return out


def evaluate(ephe: str, swetest: str | None, receipt: str | None, *, subset: int | None = None) -> dict:
    from sabpuja_kundali import engine
    from sabpuja_kundali.ephemeris import verify_ephemeris_dir
    from sabpuja_kundali.panchanga import calculate
    from sabpuja_kundali.panchanga.astro import SwissSession, utc_micros

    tol = tolerances()["D15_b_R_C3"]
    ref = Swetest(swetest, receipt, ephe)
    tol_bind = Fraction(str(tol["binding_vs_swetest_max_abs_degrees"]))
    tol_eng = Fraction(str(tol["sun_moon_engine_vs_swetest_max_abs_degrees"]))
    tol_es = Fraction(str(tol["E_S_engine_vs_swetest_max_abs_degrees"]))
    tol_tr = Fraction(str(tol["transition_vs_independent_swetest_bisection_max_abs_seconds"]))
    sets = instant_sets()
    if subset is not None:
        sets = sets[:subset] + sets[50:50 + subset]
    docs = []
    for label, req in sets:
        docs.append((label, req, engine.calculate(req, ephe), calculate(req, ephe)))
    edge = boundary_instants([(lbl, d) for lbl, _, _, d in docs], limit=2 if subset else 6)
    for label, req in edge:
        docs.append((label, req, engine.calculate(req, ephe), calculate(req, ephe)))
    swe = engine.swiss_runtime()
    folder = verify_ephemeris_dir(ephe)
    rows = []
    for label, req, chart, doc in docs:
        birth = parse_utc(doc["birth"]["utc"])
        t0_us = utc_micros(birth)
        with SwissSession(swe, folder) as session:
            from sabpuja_kundali.panchanga.astro import julian_day
            jd = julian_day(swe, birth)
            b_sun, b_moon = session.sun_moon(t0_us)
        r_sun, r_moon = ref.sun_moon(jd)
        checks = []

        def add(name, actual, reference, limit):
            diff = _angdiff(Fraction(actual), reference)
            checks.append({"check": name, "diff_deg": float(diff), "tolerance_deg": float(limit),
                           "status": "PASS" if diff <= limit else "FAIL"})
        add("binding_sun", b_sun, r_sun, tol_bind)
        add("binding_moon", b_moon, r_moon, tol_bind)
        add("engine_sun_8dp", chart["planets"]["sun"]["longitude_deg"], r_sun, tol_eng)
        add("engine_moon_8dp", chart["planets"]["moon"]["longitude_deg"], r_moon, tol_eng)
        r_e, r_s = oracle.elongation(r_sun, r_moon), oracle.yoga_sum(r_sun, r_moon)
        add("engine_E_8dp", doc["angles"]["elongation_deg"], r_e, tol_es)
        add("engine_S_8dp", doc["angles"]["yoga_sum_deg"], r_s, tol_es)
        ref_sec = oracle.all_sectors(r_sun, r_moon)
        got = {"tithi": doc["tithi"]["number"] - 1, "karana": doc["karana"]["index"] - 1,
               "yoga": doc["yoga"]["index"] - 1, "nakshatra": doc["nakshatra"]["index"],
               "pada": doc["nakshatra"]["index"] * 4 + doc["nakshatra"]["pada"] - 1}
        values = {"tithi": (r_e, tol_es), "karana": (r_e, tol_es), "yoga": (r_s, tol_es),
                  "nakshatra": (r_moon, tol_bind), "pada": (r_moon, tol_bind)}
        for element, n in COUNTS.items():
            value, limit = values[element]
            margin = oracle.distance_to_nearest_edge(value, n)
            if got[element] == ref_sec[element]:
                status = "PASS"
            elif margin <= limit:
                status = "BOUNDARY-INDETERMINATE"
            else:
                status = "FAIL"
            checks.append({"check": f"index_{element}", "engine": got[element], "reference": ref_sec[element],
                           "edge_margin_deg": float(margin), "status": status})
        t0 = Fraction(t0_us, 1_000_000)
        for element, (block, s_key, e_key) in DOC_KEYS.items():
            for key, direction in ((s_key, -1), (e_key, 1)):
                engine_s = int(parse_utc(doc[block][key]["utc"]).timestamp())
                o = oracle_transition(ref, element, t0, direction)
                mid = (o["lo"] + o["hi"]) / 2
                # Gated: engine whole second vs the oracle's own first whole second (same D09 rule).
                diff = abs(Fraction(engine_s - o["first_whole_second"]))
                checks.append({"check": f"transition_{element}_{'end' if direction == 1 else 'start'}",
                               "engine_utc": doc[block][key]["utc"], "oracle_crossing_unix_s": float(mid),
                               "oracle_first_whole_second": o["first_whole_second"],
                               "whole_second_identical": o["first_whole_second"] == engine_s,
                               "engine_minus_oracle_crossing_s": float(Fraction(engine_s) - mid),
                               "diff_s": float(diff), "tolerance_s": float(tol_tr),
                               "status": "PASS" if diff <= tol_tr else "FAIL"})
        statuses = {c["status"] for c in checks}
        status = "FAIL" if "FAIL" in statuses else ("BOUNDARY-INDETERMINATE"
                                                     if "BOUNDARY-INDETERMINATE" in statuses else "PASS")
        rows.append({"instant_id": label, "jd_ut": repr(jd), "status": status, "checks": checks})
    counts = {s: sum(r["status"] == s for r in rows) for s in ("PASS", "FAIL", "BOUNDARY-INDETERMINATE")}
    all_checks = [c for r in rows for c in r["checks"]]
    verdict = ("SWISS-CONFORMANCE FAIL" if counts["FAIL"] else
               "SWISS-CONFORMANCE BOUNDARY-INDETERMINATE" if counts["BOUNDARY-INDETERMINATE"] else
               "SWISS-CONFORMANCE PASS")
    worst = {}
    for c in all_checks:
        key = c["check"].split("_")[0] if c["check"].startswith(("index", "transition")) else c["check"]
        val = c.get("diff_deg", c.get("diff_s"))
        if val is not None:
            worst[key] = max(worst.get(key, 0.0), val)
    return {"gate": "PAN-QA-07", "verdict": verdict, "counts": counts, "instants": len(rows),
            "checks": len(all_checks), "checks_failed": sum(c["status"] == "FAIL" for c in all_checks),
            "transition_checks": sum(c["check"].startswith("transition") for c in all_checks),
            "transition_whole_second_identical": sum(bool(c.get("whole_second_identical")) for c in all_checks),
            "worst": worst, "swetest_sha256": ref.sha256, "swetest_source": ref.source,
            "swetest_calls": ref.calls, "claim_boundary": tol["comparison_kind"], "rows": rows}
