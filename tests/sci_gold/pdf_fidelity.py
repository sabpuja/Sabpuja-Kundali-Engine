"""KUN-SCI-GOLD-001 report fidelity: premium PDF positions vs engine output and vs the reference.

    python -m tests.sci_gold.pdf_fidelity --root CHECKOUT --ephe DIR --out DIR [--locales en,hi]

CHECKOUT is a read-only checkout whose report/phase1 renderer is tested (this
branch for English; PR #61's exact head for English and Hindi). For every chart
fixture the engine response is rendered with synthetic=True, the text is
extracted with PyMuPDF and checked independently of the renderer's own layout
tables:

* D1 and D9 chart pages: every graha/Lagna label and every sign number found in
  the chart square is assigned to a North Indian house cell by the isolated
  `reference_rules.north_indian_house_at` geometry (house 1 top centre,
  anticlockwise), not by the renderer's polygons. Only the chart square's
  position and size are read from the render audit.
* Positions table: the 8-decimal sidereal longitude printed for each row.
* Navamsa table: the printed D1 sign number, D9 sign number and D9 house.

Each check is made against the engine output (report consistency) and against
the reference expectation from swetest + reference rules (fidelity to the
validated value). Fields that are BOUNDARY-INDETERMINATE in the comparison run
are compared to the engine only. With two locales it also checks that English
and Hindi place every label in the same cell and print the same numbers, and
that rendering never mutates the engine response.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import copy
import importlib
import json
import re
import sys

from . import reference_rules as rr, swiss_reference as sr
from .run import BODIES, reference_chart

HERE = Path(__file__).resolve().parent
LON8 = re.compile(r"^(\d{1,3}\.\d{8})°$")
DEG = re.compile(r"\d+°$")
FOLDS = {"GOLD-Z04", "GOLD-Z05", "GOLD-Z06", "GOLD-Z07", "GOLD-Z08", "GOLD-Z09"}


def load_renderer(root: Path):
    for p in (root / "src", root / "prototype", root / "report" / "phase1"):
        sys.path.insert(0, str(p))
    premium = importlib.import_module("premium_report")
    try:
        loc = importlib.import_module("report_locale")
    except ImportError:
        loc = None
    engine = importlib.import_module("sabpuja_kundali.engine")
    return premium, loc, engine


def labels(premium, loc, locale: str) -> dict[str, str]:
    """Printed chart label -> body key ('lagna' for the ascendant)."""
    if locale == "en":
        out = {abbr: key for key, (_, abbr) in premium.DISPLAY.items()}
        out["Asc"] = "lagna"
        return out
    tr = loc.Translator(locale)
    out = {tr.graha(key)[1]: key for key in premium.GRAHAS}
    out[tr.lagna()[1]] = "lagna"
    return out


def response_for(fx: dict, out: dict, places: dict) -> dict:
    key = fx["place"]["key"]
    p = places.get(key)
    lat, lon, tz = fx["input"]["latitude"], fx["input"]["longitude"], fx["input"]["timezone"]
    place = {"id": key, "name": p["name"] if p else f"Synthetic place {key}", "region": p["region"] if p else "Synthetic",
             "country": p["country"] if p else "Synthetic", "latitude": lat, "longitude": lon, "timezone": tz,
             "in_supported_latitude_band": abs(lat) <= 66.0}
    if p:  # the prototype's own summary of the gazetteer provenance (places.public_place)
        place["source"] = (f"GeoNames {p['provenance']['geonames_id']}; Natural Earth cross-check "
                           f"{p['provenance']['cross_check']['distance_km']} km")
    dt = fx["input"]["birth_datetime"]
    return {"input": {"place": place, "local_date": dt[:10], "local_time": dt[11:19], "utc_offset": dt[-6:],
                      "offset_resolution": "user_selected_repeated_hour" if fx["id"] in FOLDS else "unique"},
            "chart": out}


def segment(text: str, label_map: dict) -> list[str] | None:
    """Split text into a sequence of known labels, or None.

    PyMuPDF joins adjacent Hindi labels of one house line into a single word or span
    (for example 'शुश' = Venus 'शु' + Saturn 'श'). Joined labels are always on one line
    of one house cell, so every part gets that cell. Exhaustive search, longest first.
    """
    if text in label_map:
        return [text]
    for label in sorted(label_map, key=len, reverse=True):
        if text.startswith(label):
            rest = segment(text[len(label):], label_map)
            if rest is not None:
                return [label] + rest
    return None


def chart_cells(page, info, label_map):
    """{body: [cells]}, {cell: [sign numbers]}, unknown tokens."""
    x0, y0, size = info["origin"][0], info["origin"][1], info["size"]
    h = page.rect.height
    top = h - y0 - size
    import fitz
    rect = fitz.Rect(x0, top, x0 + size, top + size)
    bodies, numbers, unknown = {}, {}, []
    # Text spans (one per drawn label), not words: PyMuPDF can join adjacent Devanagari labels into one word.
    for block in page.get_text("dict", clip=rect)["blocks"]:
        for line in block.get("lines", []):
            for span in line["spans"]:
                for word in span["text"].split():
                    wx0, wy0, wx1, wy1 = span["bbox"]
                    u, v = ((wx0 + wx1) / 2 - x0) / size, ((wy0 + wy1) / 2 - top) / size
                    cell = rr.north_indian_house_at(u, v)
                    if word.isdigit():
                        numbers.setdefault(cell, []).append(int(word))
                        continue
                    name = DEG.sub("", word)
                    if not name:            # a separate degree token ("17°")
                        continue
                    parts = segment(name, label_map)
                    if parts is None:
                        unknown.append(word)
                    for part in parts or ():
                        bodies.setdefault(label_map[part], []).append(cell)
    return bodies, numbers, unknown


def table_rows(page):
    grouped = {}
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        grouped.setdefault(round(y1), []).append((x0, word))
    merged = {}
    for y in sorted(grouped):
        target = next((k for k in merged if abs(k - y) <= 3), y)
        merged.setdefault(target, []).extend(grouped[y])
    return [[w for _, w in sorted(items)] for _, items in sorted(merged.items())]


def check_fixture(fx, ref_exp, out, premium, loc, locale, bi_fields, response):
    before = copy.deepcopy(response)
    data, audit = premium.render(response, synthetic=True, locale=locale) if loc else premium.render(response, synthetic=True)
    import fitz
    doc = fitz.open(stream=data, filetype="pdf")
    label_map = labels(premium, loc, locale)
    problems, checks = [], 0
    eng = {"d1": {b: out["planets"][b]["whole_sign_house"] for b in BODIES},
           "d9": {b: out["planets"][b]["navamsa_whole_sign_house"] for b in BODIES}}
    ref = {"d1": {b: ref_exp["planets"][b]["whole_sign_house"] for b in BODIES},
           "d9": {b: ref_exp["planets"][b]["navamsa_whole_sign_house"] for b in BODIES}}
    lagna_idx = {"d1": rr.rashi_index(ref_exp["lagna"]["longitude"]), "d9": rr.navamsa_index(ref_exp["lagna"]["longitude"])}
    eng_lagna_idx = {"d1": rr.RASHIS.index(out["lagna"]["rashi"]), "d9": rr.RASHIS.index(out["d9"]["lagna_rashi"])}
    layout = {}
    for mode in ("d1", "d9"):
        page = doc[premium.PAGE_OF[mode] - 1]
        bodies, numbers, unknown = chart_cells(page, audit["charts"][mode], label_map)
        layout[mode] = (bodies, numbers)
        if unknown:
            problems.append(f"{mode}: unrecognised chart tokens {unknown}")
        checks += 1
        if bodies.get("lagna") != [1]:
            problems.append(f"{mode}: Lagna label cells {bodies.get('lagna')} (want [1])")
        for b in BODIES:
            checks += 2
            if bodies.get(b) != [eng[mode][b]]:
                problems.append(f"{mode}: {b} drawn in {bodies.get(b)}, engine house {eng[mode][b]}")
            fld = f"{b}.{'whole_sign_house' if mode == 'd1' else 'navamsa_whole_sign_house'}"
            if fld not in bi_fields and bodies.get(b) != [ref[mode][b]]:
                problems.append(f"{mode}: {b} drawn in {bodies.get(b)}, reference house {ref[mode][b]}")
        for cell in range(1, 13):
            checks += 2
            want_eng = (eng_lagna_idx[mode] + cell - 1) % 12 + 1
            want_ref = (lagna_idx[mode] + cell - 1) % 12 + 1
            if numbers.get(cell) != [want_eng]:
                problems.append(f"{mode}: cell {cell} sign numbers {numbers.get(cell)}, engine {want_eng}")
            if not ({"lagna.rashi", "lagna.navamsa_rashi"} & bi_fields) and numbers.get(cell) != [want_ref]:
                problems.append(f"{mode}: cell {cell} sign numbers {numbers.get(cell)}, reference {want_ref}")
        if None in numbers or None in [c for v in bodies.values() for c in v]:
            problems.append(f"{mode}: a token lies on a cell line")
    # Positions table: 8-decimal longitudes in row order (Lagna then canonical graha order).
    lons = [m.group(1) for row in table_rows(doc[premium.PAGE_OF["positions"] - 1]) for w in row for m in [LON8.match(w)] if m]
    order = ["lagna"] + list(premium.GRAHAS)
    if len(lons) != len(order):
        problems.append(f"positions: {len(lons)} longitudes printed, want {len(order)}")
    for key, text in zip(order, lons):
        checks += 2
        e = out["lagna"]["longitude_deg"] if key == "lagna" else out["planets"][key]["longitude_deg"]
        r = ref_exp["lagna"]["longitude"] if key == "lagna" else ref_exp["planets"][key]["longitude"]
        if text != f"{e:.8f}":
            problems.append(f"positions: {key} printed {text}, engine {e:.8f}")
        if abs(float(rr.circular_diff(rr.exact(text), r))) > 1e-8:
            problems.append(f"positions: {key} printed {text} differs from reference {float(r):.11f} by > 1e-8 deg")
    # Navamsa table: digits per graha row = [D1 sign no, D9 sign no, D9 house].
    abbr_to_key = {k: v for k, v in label_map.items() if v != "lagna"}
    nav = {}
    for row in table_rows(doc[premium.PAGE_OF["navamsa"] - 1]):
        if row and row[0] in abbr_to_key:
            nav[abbr_to_key[row[0]]] = [int(w) for w in row if w.isdigit()]
    for b in BODIES:
        checks += 2
        e = [rr.RASHIS.index(out["planets"][b]["rashi"]) + 1, rr.RASHIS.index(out["planets"][b]["navamsa_rashi"]) + 1,
             out["planets"][b]["navamsa_whole_sign_house"]]
        r = [rr.rashi_index(ref_exp["planets"][b]["longitude"]) + 1, rr.navamsa_index(ref_exp["planets"][b]["longitude"]) + 1,
             ref_exp["planets"][b]["navamsa_whole_sign_house"]]
        if nav.get(b) != e:
            problems.append(f"navamsa: {b} row digits {nav.get(b)}, engine {e}")
        if not any(f.startswith(b + ".") for f in bi_fields) and nav.get(b) != r:
            problems.append(f"navamsa: {b} row digits {nav.get(b)}, reference {r}")
    checks += 1
    if response != before:
        problems.append("render mutated the engine response")
    # Every number printed on the D1, D9, positions, navamsa and house pages, as a sorted multiset per page.
    numeric = [sorted(re.findall(r"\d+(?:\.\d+)?", doc[i].get_text())) for i in
               range(premium.PAGE_OF["d1"] - 1, premium.PAGE_OF["houses"])]
    return {"locale": locale, "pages": len(doc), "checks": checks, "problems": problems,
            "classification": "PASS" if not problems and len(doc) == 10 else "FAIL",
            "layout": {m: {"bodies": layout[m][0], "numbers": {str(k): v for k, v in layout[m][1].items()}} for m in layout},
            "numeric_tokens": numeric}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, required=True)
    ap.add_argument("--ephe", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--locales", default="en")
    ap.add_argument("--gold-report", type=Path, help="comparison JSON from tests.sci_gold.run (for BOUNDARY-INDETERMINATE fields)")
    args = ap.parse_args(argv)
    premium, loc, engine = load_renderer(args.root.resolve())
    locales = args.locales.split(",")
    places = {p["id"]: p for p in json.loads((args.root / "prototype/kundali_prototype/places.json").read_text())["places"]}
    matrix = json.loads((HERE / "matrix.json").read_text(encoding="utf-8"))
    bi = {}
    if args.gold_report:
        for r in json.loads(args.gold_report.read_text())["results"]:
            bi[r["id"]] = {l["field"] for l in r["layers"] if l["layer"] == "RULES" and l["classification"] == "BOUNDARY-INDETERMINATE"}
    results, total = [], {"PASS": 0, "FAIL": 0}
    for fx in matrix["fixtures"]:
        if fx["expect"]["kind"] != "chart":
            continue
        ref_exp = reference_chart(sr.parse((sr.RECEIPTS / f"{fx['id']}.txt").read_text(encoding="utf-8")))
        out = engine.calculate(dict(fx["input"]), args.ephe)
        response = response_for(fx, out, places)
        per, skipped = [], {}
        for l in locales:
            if l != "en" and fx["place"]["key"] not in places:
                # The Hindi renderer refuses a birthplace outside its terminology register (fail-closed),
                # so these synthetic places cannot be rendered in Hindi at all.
                skipped[l] = {"classification": "BLOCKED", "problems": [],
                              "reason": "PLACE_NOT_IN_HINDI_REGISTER: renderer refuses (ReportLocaleError); not rendered"}
                continue
            per.append(check_fixture(fx, ref_exp, out, premium, loc, l, bi.get(fx["id"], set()), response))
        entry = {"id": fx["id"], "locales": {p["locale"]: {k: p[k] for k in ("pages", "checks", "problems", "classification")} for p in per}}
        entry["locales"].update(skipped)
        if len(per) == 2:
            a, b = per
            same_layout = a["layout"] == b["layout"]
            same_numbers = a["numeric_tokens"] == b["numeric_tokens"]
            entry["en_hi_same_cells"] = same_layout
            entry["en_hi_same_numbers"] = same_numbers
            if not (same_layout and same_numbers):
                entry["locales"][b["locale"]]["classification"] = "FAIL"
                entry["locales"][b["locale"]]["problems"].append("Hindi differs from English in cells or printed numbers")
        cls = [v["classification"] for v in entry["locales"].values()]
        entry["classification"] = "FAIL" if "FAIL" in cls else "BLOCKED" if "BLOCKED" in cls else "PASS"
        total[entry["classification"]] = total.get(entry["classification"], 0) + 1
        results.append(entry)
    args.out.mkdir(parents=True, exist_ok=True)
    report = {"schema": "sabpuja-sci-gold-pdf-fidelity/1", "root": str(args.root), "locales": locales,
              "totals": total, "checks": sum(v.get("checks", 0) for e in results for v in e["locales"].values()), "results": results}
    (args.out / "pdf-fidelity.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("locales", "totals", "checks")}))
    for e in results:
        if e["classification"] == "FAIL":
            print(e["id"], json.dumps(e["locales"], ensure_ascii=False)[:800])
    return 1 if total["FAIL"] else 2 if total.get("BLOCKED") else 0


if __name__ == "__main__":
    sys.exit(main())
