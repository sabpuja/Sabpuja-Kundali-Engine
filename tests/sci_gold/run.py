"""KUN-SCI-GOLD-001 golden-reference comparison runner (test-only).

    python -m tests.sci_gold.run --ephe DIR [--swetest PATH --receipt RECEIPT.json] --report-dir DIR

Per fixture it records: the reference evidence (receipt file and SHA-256), the
exact input, the expected result (reference rules applied to swetest values;
UTC from the quoted IANA text), the engine's actual result, the difference and
tolerance, a classification and the method/provenance basis. Results are split
into layers that are never mixed:

  TIME      engine UTC vs the IANA-text UTC and an independent TZif reader
  SWISS     engine longitudes vs official swetest: label SWISS-CONFORMANCE (Swiss-on-Swiss)
  RULES     engine D1/D9/Nakshatra/house fields vs the isolated reference rules on swetest values
  METHOD    engine-emitted method metadata vs the canonical decisions (else METHOD-MISMATCH)
  LAGNA-F   independent ascendant formula on swetest ARMC/obliquity/ayanamsha (tolerance not frozen)
  ASTRO     independent JPL/INPOP astronomy: always BLOCKED (deferred, issue #15, REL-01 optional)
  REFUSAL   expected refusal code

With --swetest the committed receipts are re-captured live and must be byte
identical; otherwise the run is BLOCKED (reference not reproduced).

Input readiness (QA review 5737049196): a result is FAIL or METHOD-MISMATCH only
when the scientific inputs were verified (pinned ephemeris files against the
manifest, matrix/spec pins, no SE_EPHE_PATH) and the fixture's committed receipt
is present and hash-valid. When an input is missing or unverified, the affected
comparison is BLOCKED with a reason code, never FAIL and never PASS. Missing or
invalid paths are reported as reason codes, not tracebacks.
Exit: 0 every verified layer PASS/QUALIFIED; 1 any FAIL or METHOD-MISMATCH; 2 otherwise (BLOCKED or
BOUNDARY-INDETERMINATE present). ASTRO and LAGNA-F are reported but excluded from the exit code,
since their BLOCKED status is a standing owner decision, not a run defect.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from fractions import Fraction
from pathlib import Path
import argparse
import csv
import hashlib
import io
import json
import os
import platform
import subprocess
import sys

from . import asc_formula, reference_rules as rr, swiss_reference as sr, tzif_reference as tzr

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
PINS = HERE / "PINS.json"
SPEC = REPO / "tests" / "swiss_conformance" / "spec.json"

PASS, FAIL, MM, BI, BLOCKED, QUAL = "PASS", "FAIL", "METHOD-MISMATCH", "BOUNDARY-INDETERMINATE", "BLOCKED", "QUALIFIED"
SWISS_PASS, SWISS_FAIL = "SWISS-CONFORMANCE PASS", "SWISS-CONFORMANCE FAIL"
RANK = {PASS: 0, SWISS_PASS: 0, QUAL: 1, BI: 2, BLOCKED: 3, MM: 4, FAIL: 5, SWISS_FAIL: 5}
BODIES = ("sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu_mean", "ketu_mean")
LEAP_LIST_EXPIRY = datetime(2027, 6, 28, tzinfo=timezone.utc)   # tz 2026e leap-seconds.list expiry


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def frozen_tolerances() -> tuple[dict, str]:
    """The QA-frozen KUN-01-SWISS-01 tolerances (spec.json, pinned by tests/swiss_conformance/inputs.py)."""
    raw = SPEC.read_bytes()
    spec = json.loads(raw)
    return {k: v["value"] for k, v in spec["tolerances_deg"].items()}, sha256_bytes(raw)


def worst(values) -> str:
    values = list(values)
    return max(values, key=lambda v: RANK[v]) if values else PASS


# --- reference expectations ------------------------------------------------------

def reference_chart(ref: dict) -> dict:
    """Expected D1/D9 placements from swetest longitudes, by the isolated reference rules only."""
    lon = {b: rr.exact(ref["planets"][b]) for b in BODIES if b != "ketu_mean"}
    lon["ketu_mean"] = rr.ketu(ref["planets"]["rahu_mean"])
    lagna = rr.exact(ref["ascendant"])
    exp = {"lagna": {"longitude": lagna, "rashi": rr.rashi(lagna), "navamsa_rashi": rr.navamsa(lagna)}, "planets": {}}
    for b, x in lon.items():
        exp["planets"][b] = {"longitude": x, "rashi": rr.rashi(x), "navamsa_rashi": rr.navamsa(x),
                             "whole_sign_house": rr.d1_house(x, lagna), "navamsa_whole_sign_house": rr.d9_house(x, lagna)}
    exp["moon_nakshatra"] = rr.nakshatra(lon["moon"])
    d9_lagna = rr.navamsa_index(lagna)
    exp["d9_houses"] = [{"house": h, "rashi": rr.RASHIS[(d9_lagna + h - 1) % 12],
                         "grahas": sorted(b for b in BODIES if exp["planets"][b]["navamsa_whole_sign_house"] == h)}
                        for h in range(1, 13)]
    exp["d1_north_indian"] = rr.north_indian_sign_numbers(rr.rashi_index(lagna))
    return exp


def _near(value: Fraction, span: Fraction, tol: float) -> Fraction:
    r = rr.norm(value) % span
    return min(r, span - r)


# --- layers ------------------------------------------------------------------------

def time_layer(fx: dict, out: dict, tzdir: Path) -> dict:
    exp_utc = fx["time_reference"]["expected_utc"]
    got = out["birth"]["utc"]
    # Independent TZif reader: offsets valid for the wall time, from the pinned TZif bytes.
    text = fx["input"]["birth_datetime"]
    wall_text, sign, off = text[:-6], text[-6], text[-5:]
    given = (1 if sign == "+" else -1) * (int(off[:2]) * 3600 + int(off[3:]) * 60)
    wall = datetime.fromisoformat(wall_text).replace(tzinfo=timezone.utc)
    wall_s = int((wall - datetime(1970, 1, 1, tzinfo=timezone.utc)).total_seconds() // 1)
    tz = tzr.parse((tzdir / fx["input"]["timezone"]).read_bytes())
    offsets = tzr.local_offsets(tz, wall_s)
    tzif_text = (wall - timedelta(seconds=given)).replace(tzinfo=None).isoformat() + "Z"
    ok = got == exp_utc and given in offsets and tzif_text == exp_utc
    return {"layer": "TIME", "expected": exp_utc, "actual": got, "tzif_offsets_s": offsets, "given_offset_s": given,
            "tzif_utc": tzif_text, "difference": "equal" if got == exp_utc else "different", "tolerance": "exact",
            "classification": PASS if ok else FAIL,
            "basis": "IANA tz 2026e rule text quoted in the fixture (eggert/tz tag 2026e) and an independent RFC 8536 "
                     "reader over the pinned tzdata 2026.5 TZif bytes; IANA conformance, not historical civil-clock "
                     "evidence (DATA-01)"}


def swiss_layer(fx: dict, out: dict, ref: dict, exp: dict, tol: dict) -> list[dict]:
    rows = []
    limit = tol["engine_vs_swetest"]
    pairs = [(b, out["planets"][b]["longitude_deg"], exp["planets"][b]["longitude"]) for b in BODIES]
    pairs.append(("lagna", out["lagna"]["longitude_deg"], exp["lagna"]["longitude"]))
    for name, got, want in pairs:
        diff = float(rr.circular_diff(rr.exact(got), want))
        rows.append({"layer": "SWISS", "field": f"{name}.longitude_deg", "expected": float(want), "actual": got,
                     "difference_deg": diff, "tolerance_deg": limit,
                     "classification": SWISS_PASS if abs(diff) <= limit else SWISS_FAIL,
                     "basis": "official swetest 2.10.03 receipt (A or C); ketu = swetest mean node + 180 exactly; "
                              "tolerance engine_vs_swetest from the frozen KUN-01-SWISS-01 spec.json"})
    return rows


def rules_layer(fx: dict, out: dict, exp: dict, tol: dict) -> list[dict]:
    rows = []
    near = tol["binding_vs_swetest"]
    lagna = exp["lagna"]["longitude"]
    lagna_r_near = _near(lagna, rr.SIGN, near) <= near
    lagna_p_near = _near(lagna, rr.PADA_SPAN, near) <= near

    def add(field, want, got, near_flag, basis):
        cls = BI if near_flag else (PASS if want == got else FAIL)
        rows.append({"layer": "RULES", "field": field, "expected": want, "actual": got,
                     "difference": "equal" if want == got else "different", "tolerance": "category equality; "
                     f"BOUNDARY-INDETERMINATE when a reference longitude lies within {near} deg of a relevant edge",
                     "classification": cls, "basis": basis})

    d1 = "SCI-01f: Rashi = 30 deg sign of the unrounded longitude"
    d9 = "SCI-01f/SCI-02 C2: D9 by the classical movable/fixed/dual start rule (cross-checked by the elemental rule)"
    add("lagna.rashi", exp["lagna"]["rashi"], out["lagna"]["rashi"], lagna_r_near, d1)
    add("lagna.navamsa_rashi", exp["lagna"]["navamsa_rashi"], out["lagna"]["navamsa_rashi"], lagna_p_near, d9)
    add("d9.lagna_rashi", exp["lagna"]["navamsa_rashi"], out["d9"]["lagna_rashi"], lagna_p_near, d9)
    for b in BODIES:
        x = exp["planets"][b]["longitude"]
        e, g = exp["planets"][b], out["planets"][b]
        r_near = _near(x, rr.SIGN, near) <= near
        p_near = _near(x, rr.PADA_SPAN, near) <= near
        add(f"{b}.rashi", e["rashi"], g["rashi"], r_near, d1)
        add(f"{b}.navamsa_rashi", e["navamsa_rashi"], g["navamsa_rashi"], p_near, d9)
        add(f"{b}.whole_sign_house", e["whole_sign_house"], g["whole_sign_house"], r_near or lagna_r_near,
            "SCI-01f: D1 whole-sign house ((sign - Lagna sign) mod 12) + 1")
        add(f"{b}.navamsa_whole_sign_house", e["navamsa_whole_sign_house"], g["navamsa_whole_sign_house"],
            p_near or lagna_p_near, "SCI-02 C2: D9 whole-sign house from the D9 Lagna sign")
    m = out["moon_nakshatra"]
    add("moon_nakshatra", list(exp["moon_nakshatra"]), [m["name"], m["pada"]],
        _near(exp["planets"]["moon"]["longitude"], rr.PADA_SPAN, near) <= near,
        "27 equal Nakshatras of 13 deg 20 min from 0 deg Mesha, 4 Padas each")
    any_p_near = lagna_p_near or any(_near(exp["planets"][b]["longitude"], rr.PADA_SPAN, near) <= near for b in BODIES)
    got_houses = [{"house": h["house"], "rashi": h["rashi"], "grahas": sorted(h["grahas"])} for h in out["d9"]["houses"]]
    add("d9.houses (North Indian D9 cells)", exp["d9_houses"], got_houses, any_p_near,
        "SCI-02 C2: house h has D9 sign (D9 Lagna + h - 1) mod 12 and holds every body whose D9 house is h")
    return rows


def method_layer(out: dict, ref: dict) -> dict:
    c = out["calculation_metadata"]["conventions"]
    checks = {
        "schema_version 0.3.0": out["schema_version"] == "0.3.0",
        "ayanamsa Lahiri mode 1, true": (c["ayanamsa"]["swiss_mode_number"], c["ayanamsa"]["kind"]) == (1, "true_ayanamsha"),
        "positions calc_ut flags 65538": c["planetary_positions"]["swiss_flags_value"] == 65538,
        "mean node, Ketu opposite": c["nodes"]["rahu_swiss_body"] == "MEAN_NODE",
        "ascendant houses_ex W flags 65536 ascmc[0]": (c["ascendant"]["swiss_house_system"], c["ascendant"]["swiss_flags_value"],
                                                        c["ascendant"]["value"]) == ("W", 65536, "ascmc[0]"),
        "D1 whole-sign houses": c["houses"]["d1_model"] == "whole_sign",
        "D9 whole-sign houses": out["d9"]["house_system"] == "whole_sign",
        "swetest receipt ayanamsa Lahiri": ref["ayanamsa_text"] is not None,
        "Swiss library 2.10.03": out["calculation_metadata"]["swiss_ephemeris"]["library_version"] == "2.10.03",
    }
    bad = [k for k, v in checks.items() if not v]
    return {"layer": "METHOD", "expected": "canonical SCI-01a/b/c/d/e/f, SCI-02 C2", "actual": "match" if not bad else bad,
            "classification": PASS if not bad else MM, "basis": "main:docs/DECISIONS.md ledger rows 10-12, SCI-01b/c, SCI-02 C2"}


def disclosure_layer(fx: dict, out: dict) -> dict:
    utc = datetime.fromisoformat(fx["time_reference"]["expected_utc"][:-1]).replace(tzinfo=timezone.utc)
    want = (["FUTURE_CIVIL_TIME_PROJECTED"] if utc >= LEAP_LIST_EXPIRY else []) + \
           (["HIGH_LATITUDE_TIME_SENSITIVITY"] if abs(fx["input"]["latitude"]) > 60 else [])
    got = [d["code"] for d in out["calculation_metadata"]["disclosures"]]
    return {"layer": "DISCLOSURE", "expected": want, "actual": got,
            "classification": PASS if want == got else FAIL,
            "basis": "SCI-01h (projected civil time after the pinned 2027-06-28 leap-second list expiry) and "
                     "SCI-01g (>60 deg disclosure)"}


def lagna_formula_layer(fx: dict, ref: dict) -> dict:
    lat = fx["input"]["latitude"]
    calc = asc_formula.sidereal_ascendant(float(ref["armc"]), float(ref["eps_true"]), lat, float(ref["ayanamsa"]))
    diff = float(rr.circular_diff(Fraction(calc), rr.exact(ref["ascendant"])))
    return {"layer": "LAGNA-F", "expected": float(rr.exact(ref["ascendant"])), "actual": calc, "difference_deg": diff,
            "tolerance_deg": None, "classification": BLOCKED,
            "reason": "TOLERANCE_NOT_FROZEN (REL-01 ledger row 1: no tolerance frozen; SCI-01e: no golden-chart Lagna tolerance)",
            "basis": "Meeus ch. 14 ascendant relation on swetest ARMC, true obliquity and true Lahiri ayanamsha; "
                     "checks the Lagna transformation, not Swiss sidereal-time/nutation/precession models"}


ASTRO = {"layer": "ASTRO", "classification": BLOCKED,
         "reason": "EXTERNAL_REFERENCE_NOT_AUTHORIZED: independent JPL/INPOP assurance is optional and deferred "
                   "(issue #15; REL-01 ledger row 1; PRD OD-05). No external value was obtained or used."}


def retrograde_info(fx: dict, ref: dict) -> dict:
    status = {b: float(ref["speeds"][b][1]) < 0 for b in ref["speeds"]}
    info = {"reference_retrograde": status,
            "engine_field": "none: schema 0.3.0 has no speed or retrograde field, so retrograde status is not "
                            "compared (NOT-IN-SCHEMA)"}
    if fx["design"] and fx["design"].get("direction") == "backward":
        body = fx["focus"][0]
        info["design_check"] = PASS if status[body] else FAIL
    return info


# --- run -------------------------------------------------------------------------

def git_state() -> dict:
    def g(*a):
        return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, text=True, check=False).stdout.strip()
    return {"head": g("rev-parse", "HEAD"), "tree": g("rev-parse", "HEAD^{tree}"), "dirty": bool(g("status", "--porcelain"))}


def tzdata_dir() -> Path:
    import tzdata
    return Path(tzdata.__file__).resolve().parent / "zoneinfo"


def run_all(ephe: str, swetest: str | None, receipt: str | None) -> dict:
    sys.path.insert(0, str(REPO / "src"))
    from sabpuja_kundali import engine
    from sabpuja_kundali.ephemeris import load_manifest, verify_ephemeris_dir

    tol, spec_sha = frozen_tolerances()
    matrix_bytes = (HERE / "matrix.json").read_bytes()
    pins = json.loads(PINS.read_text(encoding="utf-8"))
    sums_bytes = (sr.RECEIPTS / "SHA256SUMS").read_bytes()
    run_blocks = []
    input_blocks = []   # failures that make every chart comparison undecidable
    if sha256_bytes(matrix_bytes) != pins["matrix_sha256"]:
        input_blocks.append("MATRIX_SHA256_MISMATCH")
    if sha256_bytes(sums_bytes) != pins["receipts_sha256sums_sha256"]:
        run_blocks.append("RECEIPT_SUMS_SHA256_MISMATCH")
    if spec_sha != pins["swiss_spec_sha256"]:
        input_blocks.append("FROZEN_SPEC_SHA256_MISMATCH")
    if os.environ.get("SE_EPHE_PATH"):
        input_blocks.append("SE_EPHE_PATH_SET")
    try:
        verify_ephemeris_dir(ephe, load_manifest())
        ephe_ok = True
    except Exception as exc:  # recorded as a code only
        ephe_ok = False
        input_blocks.append("EPHEMERIS_UNVERIFIED:" + getattr(exc, "code", type(exc).__name__))
    run_blocks += input_blocks
    inputs_ok = not input_blocks
    sums = dict(line.split("  ")[::-1] for line in sums_bytes.decode().splitlines() if line)
    matrix = json.loads(matrix_bytes)
    live = None
    if swetest and not (Path(swetest).is_file() and os.access(swetest, os.X_OK)):
        run_blocks.append("SWETEST_BINARY_MISSING")
    elif swetest and not ephe_ok:
        run_blocks.append("SWETEST_NOT_RERUN (ephemeris unverified)")
    elif swetest:
        from tests.swiss_conformance import inputs as sc_inputs  # receipt validation is reused unchanged
        binary_sha = sha256_bytes(Path(swetest).read_bytes())
        if not receipt or not Path(receipt).is_file():
            rec, source, errors = None, None, ["SWETEST_BUILD_RECEIPT_MISSING"]
        else:
            try:
                rec = json.loads(Path(receipt).read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, ValueError):
                rec = None
            source, errors = sc_inputs.validate_receipt(rec, binary_sha)
        live = {"swetest_sha256": binary_sha, "source": source, "receipt_errors": errors,
                "receipt": rec, "reproduced": 0, "not_reproduced": []}
        run_blocks += errors
    else:
        run_blocks.append("SWETEST_NOT_RERUN (committed receipts only)")
    tzdir = tzdata_dir()
    results = []
    for fx in matrix["fixtures"]:
        res = {"id": fx["id"], "group": fx["group"], "purpose": fx["purpose"], "input": fx["input"],
               "place": fx["place"], "expect": fx["expect"], "layers": [], "notes": []}
        try:
            out = engine.calculate(dict(fx["input"]), ephe)
            err = None
        except engine.EXPECTED_ERRORS as exc:
            out, err = None, exc.code
        except Exception as exc:  # an unexpected engine exception is a result, not a runner crash
            out, err = None, "UNEXPECTED_EXCEPTION:" + type(exc).__name__
        # A mismatch is a calculation defect only when the pinned inputs were verified.
        unverified = BLOCKED if not inputs_ok else FAIL
        if fx["expect"]["kind"] == "refusal":
            ok = err == fx["expect"]["code"]
            layer = {"layer": "REFUSAL", "expected": fx["expect"]["code"], "actual": err or "CHART",
                     "classification": PASS if ok else unverified,
                     "basis": fx["expect"]["basis"] + "; docs/api-contract.md P5 order"}
            if not ok and not inputs_ok:
                layer["reason"] = ["INPUT_UNVERIFIED"] + input_blocks
            res["layers"].append(layer)
            res["classification"] = res["layers"][0]["classification"]
            results.append(res)
            continue
        name = fx["id"] + ".txt"
        blocked = []
        try:
            text = (sr.RECEIPTS / name).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            text = None
            blocked.append("RECEIPT_FILE_MISSING")
        res["reference"] = {"receipt": f"tests/sci_gold/receipts/{name}",
                            "sha256": sr.sha256_text(text) if text is not None else None,
                            "sha256_listed": sums.get(name), "source": "official swetest 2.10.03, aloistr/swisseph@c69c14a"}
        if text is not None and sums.get(name) != sr.sha256_text(text):
            blocked.append("RECEIPT_HASH_MISMATCH")
        if live is not None and text is not None:
            try:
                again = sr.capture(fx, swetest, ephe)
            except (OSError, subprocess.SubprocessError):
                again = None
            if again == text:
                live["reproduced"] += 1
            else:
                live["not_reproduced"].append(fx["id"])
                blocked.append("RECEIPT_NOT_REPRODUCED")
        ref = None
        if text is not None:
            try:
                ref = sr.parse(text)
            except sr.ReceiptError as exc:
                blocked.append("RECEIPT_INVALID:" + str(exc))
        if err is not None:
            layer = {"layer": "ENGINE", "expected": "chart", "actual": err, "classification": unverified}
            if not inputs_ok:
                layer["reason"] = ["INPUT_UNVERIFIED"] + input_blocks
            res["layers"].append(layer)
        if ref is None or blocked:
            res["layers"].append({"layer": "REFERENCE", "classification": BLOCKED, "reason": blocked})
        if err is None and ref is not None and not blocked:
            exp = reference_chart(ref)
            res["reference"].update({"jd_ut": ref["header"]["jd_double"], "ayanamsa_dms": ref["ayanamsa_text"]})
            res["layers"].append(time_layer(fx, out, tzdir))
            res["layers"] += swiss_layer(fx, out, ref, exp, tol)
            res["layers"] += rules_layer(fx, out, exp, tol)
            res["layers"].append(method_layer(out, ref))
            res["layers"].append(disclosure_layer(fx, out))
            res["layers"].append(lagna_formula_layer(fx, ref))
            res["layers"].append(dict(ASTRO))
            res["retrograde"] = retrograde_info(fx, ref)
            if "design_check" in res["retrograde"]:
                res["layers"].append({"layer": "DESIGN", "field": "reference speed < 0 for the focus body",
                                      "classification": res["retrograde"]["design_check"]})
            res["edge_distance_deg"] = {b: float(rr.edge_distance(exp["planets"][b]["longitude"])) for b in BODIES}
            res["edge_distance_deg"]["lagna"] = float(rr.edge_distance(exp["lagna"]["longitude"]))
            res["engine_output_sha256"] = sha256_bytes(json.dumps(out, sort_keys=True).encode())
            res["d1_north_indian_expected"] = exp["d1_north_indian"]
        verified = [l["classification"] for l in res["layers"] if l["layer"] not in ("ASTRO", "LAGNA-F")]
        cls = worst(verified)
        if not inputs_ok or ((blocked or ref is None) and err is None):
            # Comparisons against unverified inputs or reference are undecidable, whatever they show.
            # Only a mismatch with verified inputs and a valid reference is a FAIL or METHOD-MISMATCH;
            # an engine refusal of a chart fixture with verified inputs stays FAIL without a reference.
            cls = BLOCKED
            res["notes"].append("BLOCKED: comparison not decidable; reasons " +
                                ", ".join((["INPUT_UNVERIFIED"] + input_blocks) if not inputs_ok else blocked))
        if cls in (PASS, SWISS_PASS) and fx["time_reference"]["expected_utc"] >= "2027-06-28":
            cls = QUAL
            res["notes"].append("QUALIFIED: after the pinned 2027-06-28 leap-second list expiry; civil time, "
                                "UT1-UTC and Delta T are projections (SCI-01h), so the reference is a projection too")
        res["classification"] = cls
        results.append(res)
    counts = {}
    for r in results:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1
    layer_counts = {}
    for r in results:
        for l in r["layers"]:
            key = f"{l['layer']}:{l['classification']}"
            layer_counts[key] = layer_counts.get(key, 0) + 1
    fx_cls = [r["classification"] for r in results]
    if run_blocks or any(c == BLOCKED for c in fx_cls):
        verdict = BLOCKED if not any(c in (FAIL, MM) for c in fx_cls) else FAIL
    elif any(c in (FAIL, MM) for c in fx_cls):
        verdict = FAIL
    elif any(c == BI for c in fx_cls):
        verdict = BI
    else:
        verdict = PASS
    from importlib.metadata import version
    import swisseph
    return {
        "schema": "sabpuja-sci-gold-report/1", "task": "KUN-SCI-GOLD-001",
        "claim_boundary": "Engineering-accuracy evidence only. SWISS rows are Swiss-on-Swiss integration conformance "
                          "(SWISS-CONFORMANCE), not independent astronomy. RULES rows verify the D1/D9 transformation "
                          "with an isolated reference on Swiss reference longitudes. Independent astronomical accuracy "
                          "(ASTRO) is BLOCKED for every fixture. No public accuracy claim is supported.",
        "environment": {"git": git_state(), "python": platform.python_version(), "platform": platform.platform(),
                        "pyswisseph": version("pyswisseph"), "swiss_library": swisseph.version,
                        "tzdata": version("tzdata"), "ephemeris_verified": ephe_ok,
                        "matrix_sha256": sha256_bytes(matrix_bytes), "receipts_sha256sums_sha256": sha256_bytes(sums_bytes),
                        "frozen_spec_sha256": spec_sha, "frozen_tolerances_deg": tol, "live_swetest": live},
        "run_blocking_reasons": run_blocks, "verdict_verified_layers": verdict,
        "fixture_counts": counts, "layer_counts": dict(sorted(layer_counts.items())), "results": results,
    }


def _fmt(v):
    if isinstance(v, float):
        return f"{v:.11g}"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return str(v)


def to_csv(report: dict) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["fixture", "group", "layer", "field", "expected", "actual", "difference", "tolerance", "classification", "basis"])
    for r in report["results"]:
        for l in r["layers"]:
            w.writerow([r["id"], r["group"], l["layer"], l.get("field", ""), _fmt(l.get("expected", "")),
                        _fmt(l.get("actual", "")), _fmt(l.get("difference_deg", l.get("difference", ""))),
                        _fmt(l.get("tolerance_deg", l.get("tolerance", ""))), l["classification"],
                        l.get("basis", l.get("reason", ""))])
    return buf.getvalue()


def to_markdown(report: dict) -> str:
    env = report["environment"]
    lines = [f"# KUN-SCI-GOLD-001 golden-reference comparison: verified layers {report['verdict_verified_layers']}", "",
             f"_{report['claim_boundary']}_", "",
             f"- Commit `{env['git']['head']}` tree `{env['git']['tree']}` dirty={env['git']['dirty']}",
             f"- Python {env['python']}; pyswisseph {env['pyswisseph']}; Swiss {env['swiss_library']}; tzdata {env['tzdata']}",
             f"- Ephemeris verified={env['ephemeris_verified']}; matrix sha256 `{env['matrix_sha256']}`; receipts SHA256SUMS sha256 `{env['receipts_sha256sums_sha256']}`",
             f"- Frozen tolerances (spec.json `{env['frozen_spec_sha256'][:12]}`): {env['frozen_tolerances_deg']}"]
    live = env["live_swetest"]
    if live:
        lines.append(f"- Live swetest sha256 `{live['swetest_sha256']}` source {live['source']}; receipt errors {live['receipt_errors']}; "
                     f"receipts reproduced byte-identically {live['reproduced']}; not reproduced {live['not_reproduced']}")
    lines += ["", f"Run-level blocking reasons: {report['run_blocking_reasons'] or 'none'}", "",
              f"Fixture classifications: {report['fixture_counts']}", "", "Layer results:", ""]
    lines += [f"- {k}: {v}" for k, v in report["layer_counts"].items()]
    lines += ["", "| Fixture | Group | Classification | Max |SWISS diff| deg | RULES (pass/total) | Notes |", "|---|---|---|---|---|---|"]
    for r in report["results"]:
        sw = [abs(l["difference_deg"]) for l in r["layers"] if l["layer"] == "SWISS"]
        ru = [l for l in r["layers"] if l["layer"] == "RULES"]
        note = "; ".join(r["notes"]) or ""
        if r["expect"]["kind"] == "refusal":
            note = f"refusal {r['layers'][0]['expected']} -> {r['layers'][0]['actual']}"
        bis = [l["field"] for l in ru if l["classification"] == BI]
        if bis:
            note += f" BOUNDARY-INDETERMINATE: {', '.join(bis)}"
        lines.append(f"| {r['id']} | {r['group']} | {r['classification']} | {max(sw):.3g} | "
                     f"{sum(l['classification'] == PASS for l in ru)}/{len(ru)} | {note} |" if sw else
                     f"| {r['id']} | {r['group']} | {r['classification']} |  |  | {note} |")
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ephe", default=os.environ.get("SABPUJA_TEST_EPHE_PATH"))
    ap.add_argument("--swetest", default=os.environ.get("SABPUJA_TEST_SWETEST"))
    ap.add_argument("--receipt", default=os.environ.get("SABPUJA_TEST_SWETEST_RECEIPT"))
    ap.add_argument("--report-dir", type=Path, default=REPO / "reports")
    args = ap.parse_args(argv)
    report = run_all(args.ephe, args.swetest, args.receipt)
    args.report_dir.mkdir(parents=True, exist_ok=True)
    stem = "sci-gold-" + report["environment"]["git"]["head"][:12]
    (args.report_dir / f"{stem}.json").write_text(json.dumps(report, indent=1, sort_keys=True, default=str, ensure_ascii=False) + "\n", encoding="utf-8")
    (args.report_dir / f"{stem}.csv").write_text(to_csv(report), encoding="utf-8")
    md = to_markdown(report)
    (args.report_dir / f"{stem}.md").write_text(md, encoding="utf-8")
    print(md)
    v = report["verdict_verified_layers"]
    return {PASS: 0, FAIL: 1}.get(v, 2)


if __name__ == "__main__":
    sys.exit(main())
