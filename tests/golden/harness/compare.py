"""Pure comparison of one fixture's reference values with one engine output.

Only called after every gate has passed. Takes resolved, frozen tolerances in
arcseconds per quantity. Categories for the reference side come from the
harness oracle, never from the engine's rules.
"""
from __future__ import annotations

from . import oracle
from .circular import PADA_DEG, RASHI_DEG, boundary_distance_arcsec, circular_diff_arcsec
from .outcomes import Outcome
from .schema import is_finite_number

PLANETS = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn")
NODES = ("rahu_mean", "ketu_mean")
KETU_LIMIT_ARCSEC = 1e-8 * 3600  # T-KETU, self-consistency only


def quantity_for(body: str) -> str:
    if body in NODES:
        return "node_longitude"
    return "lagna_longitude" if body == "lagna" else "planet_longitude"


def _engine_body(engine_output: dict, body: str) -> dict:
    return engine_output["lagna"] if body == "lagna" else engine_output["planets"][body]


def _category_mismatches(body: str, engine: dict, engine_output: dict, ref: float, ref_lagna: float | None) -> list[str]:
    found = []
    if engine.get("rashi") != oracle.rashi(ref):
        found.append("rashi")
    if engine.get("navamsa_rashi") != oracle.navamsa(ref):
        found.append("navamsa_rashi")
    if body == "moon":
        name, pada = oracle.nakshatra(ref)
        moon_nak = engine_output.get("moon_nakshatra") or {}
        if moon_nak.get("name") != name or moon_nak.get("pada") != pada:
            found.append("moon_nakshatra")
    if body != "lagna" and ref_lagna is not None:
        if engine.get("whole_sign_house") != oracle.whole_sign_house(ref, ref_lagna):
            found.append("whole_sign_house")
    return found


def compare_longitude(fixture_id: str, body: str, engine_output: dict, expected: dict,
                      tolerances: dict, qualification: str | None = None) -> dict:
    quantity = quantity_for(body)
    ref = expected[body]
    ref_lagna = expected.get("lagna")
    check = {"fixture_id": fixture_id, "quantity": quantity, "body": body,
             "reference_deg": ref, "engine_deg": None, "diff_arcsec": None,
             "tolerance_arcsec": tolerances.get(quantity), "boundary_distance_arcsec": None,
             "category_mismatches": [], "outcome": None, "reason": None}
    tol = check["tolerance_arcsec"]
    lagna_tol = tolerances.get("lagna_longitude")
    if tol is None:
        check.update(outcome=Outcome.BLOCKED.value, reason="TOLERANCE_NOT_FROZEN")
        return check
    if not is_finite_number(tol) or tol < 0 or (lagna_tol is not None and (
            not is_finite_number(lagna_tol) or lagna_tol < 0)):
        check.update(tolerance_arcsec=None, outcome=Outcome.BLOCKED.value, reason="TOLERANCE_INVALID")
        return check
    engine = _engine_body(engine_output, body)
    check["engine_deg"] = engine["longitude_deg"]
    check["diff_arcsec"] = circular_diff_arcsec(engine["longitude_deg"], ref)
    # Pada edges include every Nakshatra, Rashi and Navamsa edge.
    check["boundary_distance_arcsec"] = boundary_distance_arcsec(ref, PADA_DEG)
    near = check["boundary_distance_arcsec"] <= tol
    if body != "lagna" and ref_lagna is not None and lagna_tol is not None:
        near = near or boundary_distance_arcsec(ref_lagna, RASHI_DEG) <= lagna_tol
    check["category_mismatches"] = _category_mismatches(body, engine, engine_output, ref, ref_lagna)
    if near:
        check.update(outcome=Outcome.BOUNDARY_INDETERMINATE.value,
                     reason="reference within tolerance of a segment boundary; redesign fixture")
    elif not abs(check["diff_arcsec"]) <= tol:  # fails closed if anything is NaN
        check.update(outcome=Outcome.FAIL.value, reason="outside tolerance")
    elif check["category_mismatches"]:
        check.update(outcome=Outcome.FAIL.value, reason="category differs outside the indeterminate band")
    elif qualification:
        check.update(outcome=Outcome.QUALIFIED.value, reason=qualification)
    else:
        check["outcome"] = Outcome.PASS.value
    return check


def compare_time(fixture_id: str, engine_output: dict, expected_time: dict) -> dict | None:
    if expected_time["utc"] is None and expected_time["error_code"] is None:
        return None
    check = {"fixture_id": fixture_id, "quantity": "utc", "body": None,
             "expected": expected_time["utc"], "engine": None, "outcome": None, "reason": None}
    if expected_time["error_code"] is not None:
        check.update(outcome=Outcome.BLOCKED.value, reason="ERROR_EXPECTATION_UNSUPPORTED_IN_WP1")
        return check
    check["engine"] = engine_output["birth"]["utc"]
    check["outcome"] = Outcome.PASS.value if check["engine"] == check["expected"] else Outcome.FAIL.value
    return check


def compare_fixture(fixture: dict, engine_output: dict, tolerances: dict,
                    qualification: str | None = None) -> list[dict]:
    """Independent checks for one fixture, in a fixed order."""
    fid = fixture["fixture_id"]
    expected = fixture["expected"]["sidereal_longitude_deg"]
    checks = []
    time_check = compare_time(fid, engine_output, fixture["expected"]["time_conversion"])
    if time_check:
        checks.append(time_check)
    for body in (*PLANETS, *NODES, "lagna"):
        if expected.get(body) is not None:
            checks.append(compare_longitude(fid, body, engine_output, expected, tolerances, qualification))
    return checks


def ketu_identity(fixture_id: str, engine_output: dict) -> dict:
    """SELF-CONSISTENCY: Ketu = Rahu + 180. Never counted toward validation."""
    planets = engine_output["planets"]
    if "ketu_mean" not in planets or "rahu_mean" not in planets:
        return {"fixture_id": fixture_id, "check": "ketu_mean = rahu_mean + 180 deg", "diff_arcsec": None,
                "limit_arcsec": KETU_LIMIT_ARCSEC, "result": "SELF-CONSISTENCY FAIL"}
    diff = circular_diff_arcsec(planets["ketu_mean"]["longitude_deg"],
                                (planets["rahu_mean"]["longitude_deg"] + 180.0) % 360.0)
    return {"fixture_id": fixture_id, "check": "ketu_mean = rahu_mean + 180 deg", "diff_arcsec": diff,
            "limit_arcsec": KETU_LIMIT_ARCSEC,
            "result": "SELF-CONSISTENCY PASS" if abs(diff) <= KETU_LIMIT_ARCSEC else "SELF-CONSISTENCY FAIL"}
