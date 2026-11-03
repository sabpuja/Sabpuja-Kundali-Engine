"""KUN-RPT-002B: /api/report renders the ten-page premium saffron PDF through the real HTTP path.

Synthetic inputs only. Success cases run the pinned engine (SABPUJA_TEST_EPHE_PATH) behind a
real PrototypeServer; every PDF is fetched over HTTP and inspected with PyMuPDF. Failure cases
replace the trusted engine response inside the server to prove that invalid scientific input,
renderer failures and resource limits never produce a PDF.
"""
import builtins
import contextlib
import copy
import http.client
import io
import json
import math
import os
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from kundali_prototype import server
from kundali_prototype.places import load_places

from support import EPHE, requires_data

try:
    import fitz
except ImportError:  # PyMuPDF is in report/phase1/requirements-qa.txt
    fitz = None
from report.phase1 import premium_report as premium
from report.phase1 import premium_layout as layout

ROOT = Path(__file__).resolve().parents[2]
SCENARIO_DIR = ROOT / "report/phase1/tests/fixtures/premium"
MANIFEST = json.loads((SCENARIO_DIR / "manifest.json").read_text())
SCENARIOS = {c["id"]: json.loads((SCENARIO_DIR / f"{c['id']}.json").read_text()) for c in MANIFEST["cases"]}
REQUESTS = {c["id"]: c["request"] for c in MANIFEST["cases"]}
PRIMARY = "s07-noon"
A4 = (595.2756, 841.8898)
SAFFRON = premium.Palette("baseline").hex
MAROON = premium.THEMES["palettes"]["od10-candidate"]["roles"]["primary"]
needs_fitz = unittest.skipUnless(fitz, "PyMuPDF unavailable: install report/phase1/requirements-qa.txt")


def rgb(hex_):
    return tuple(round(int(hex_[i:i + 2], 16) / 255, 3) for i in (1, 3, 5))


def rows(page):
    """Words grouped into table rows by baseline (same grouping as the report tests)."""
    grouped = {}
    for x0, y0, x1, y1, word, *_ in page.get_text("words"):
        grouped.setdefault(round(y1), []).append((x0, word))
    merged = {}
    for y in sorted(grouped):
        target = next((k for k in merged if abs(k - y) <= 3), y)
        merged.setdefault(target, []).extend(grouped[y])
    return [" ".join(w for _, w in sorted(items)) for _, items in sorted(merged.items())]


def flat(page):
    return " ".join(page.get_text().split())


class Server(unittest.TestCase):
    places = None

    @classmethod
    def setUpClass(cls):
        cls.srv = server.PrototypeServer(0, EPHE or "", cls.places or load_places())
        cls.port = cls.srv.server_address[1]
        cls.host = f"127.0.0.1:{cls.port}"
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.thread.join(timeout=5)

    def post(self, path, body, origin="same", content_type="application/json"):
        raw = body if isinstance(body, bytes) else json.dumps(body).encode()
        headers = {"Host": self.host, "Content-Type": content_type, "Content-Length": str(len(raw))}
        if origin == "same":
            headers["Origin"] = f"http://{self.host}"
        elif origin is not None:
            headers["Origin"] = origin
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=60)
        conn.request("POST", path, raw, headers)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, {k.lower(): v for k, v in resp.getheaders()}, data

    def assertRefusedWithoutPDF(self, status, headers, data, want_status, code):
        self.assertEqual(status, want_status, data[:200])
        self.assertTrue(headers["content-type"].startswith("application/json"), headers)
        self.assertNotIn("content-disposition", headers)
        self.assertFalse(data.lstrip().startswith(b"%PDF"))
        self.assertEqual(json.loads(data)["error"]["code"], code)
        self.assertEqual(headers["cache-control"], "no-store")
        for leak in (b"Traceback", b"File \"", b".py", b"Error:"):
            self.assertNotIn(leak, data)


@requires_data
@needs_fitz
class PremiumReportOverHTTP(Server):
    """Success path: birth form -> engine -> /api/report -> ten-page saffron premium PDF."""

    _pdfs = {}

    def download(self, case):
        if case not in self._pdfs:
            status, headers, data = self.post("/api/report", REQUESTS[case])
            self.assertEqual(status, 200, data[:300])
            self._pdfs[case] = (headers, data, fitz.open(stream=data, filetype="pdf"))
        return self._pdfs[case]

    # 1, 11. The route returns the premium layout with the existing download contract.
    def test_every_scenario_returns_the_premium_report_with_download_headers(self):
        for case in SCENARIOS:
            headers, data, pdf = self.download(case)
            self.assertEqual(headers["content-type"], "application/pdf", case)
            self.assertEqual(headers["content-disposition"], 'attachment; filename="Sabpuja-Janma-Kundali.pdf"')
            self.assertEqual(headers["cache-control"], "no-store")
            self.assertEqual(int(headers["content-length"]), len(data))
            self.assertTrue(data.startswith(b"%PDF-"))
            self.assertEqual(pdf.metadata["title"], "Sabpuja Janma Kundali")
            self.assertEqual(pdf.metadata["creator"], "Sabpuja Kundali report generator")

    # 1, 3. The bytes are exactly the validated premium renderer's saffron output for the engine response.
    def test_http_pdf_equals_premium_saffron_render_of_the_engine_response(self):
        for case in SCENARIOS:
            _, data, _ = self.download(case)
            status, response = server.handle_chart(json.dumps(REQUESTS[case]).encode(), self.srv.places, EPHE)
            self.assertEqual(status, 200)
            self.assertEqual(response, SCENARIOS[case], f"{case}: engine output differs from the reviewed fixture")
            self.assertEqual(data, premium.generate(response, synthetic=False, palette="baseline"), case)
            self.assertNotEqual(data, premium.generate(response, synthetic=False, palette="od10-candidate"))

    # 2, 10. Ten A4 pages, every section in order.
    def test_ten_a4_pages_with_sections_in_order(self):
        for case in SCENARIOS:
            _, _, pdf = self.download(case)
            self.assertEqual(len(pdf), 10, case)
            for number, (key, title, _) in enumerate(premium.PAGES, 1):
                page = pdf[number - 1]
                self.assertAlmostEqual(page.rect.width, A4[0], 2)
                self.assertAlmostEqual(page.rect.height, A4[1], 2)
                text = page.get_text()
                if key == "cover":
                    self.assertIn("Janma Kundali", text)
                    continue
                self.assertIn(f"Page {number} of 10", text, (case, key))
                self.assertIn(title.upper(), text, (case, key))

    # 3. Saffron Foundation, never maroon.
    def test_saffron_foundation_palette_and_no_maroon(self):
        for case in SCENARIOS:
            _, _, pdf = self.download(case)
            fills = {tuple(round(v, 3) for v in d["fill"]) for p in pdf for d in p.get_drawings() if d.get("fill")}
            strokes = {tuple(round(v, 3) for v in d["color"]) for p in pdf for d in p.get_drawings() if d.get("color")}
            self.assertIn(rgb(SAFFRON["page"]), fills, case)        # ivory
            self.assertIn(rgb(SAFFRON["primary"]), fills | strokes)  # saffron
            self.assertIn(rgb(SAFFRON["accent"]), fills | strokes)   # gold
            self.assertNotIn(rgb(MAROON), fills | strokes, case)
            text_colours = {span["color"] for p in pdf for b in p.get_text("dict")["blocks"]
                            for line in b.get("lines", []) for span in line["spans"]}
            self.assertNotIn(int(MAROON[1:], 16), text_colours, case)
        self.assertEqual((SAFFRON["primary"], SAFFRON["accent"], SAFFRON["page"]), ("#D35400", "#F4B400", "#FFFBEF"))

    def test_brand_fonts_embedded_and_minimum_size(self):
        _, _, pdf = self.download(PRIMARY)
        fonts = [f for p in pdf for f in p.get_fonts(full=True)]
        names = {re.sub(r"^[A-Z]{6}\+", "", f[3]) for f in fonts}
        self.assertEqual(names, {"Inter-Regular", "Inter-Medium", "Inter-SemiBold", "Poppins-SemiBold", "Poppins-Bold"})
        for xref, ext, *_ in fonts:
            self.assertEqual(ext, "ttf", "every font is embedded")
            self.assertTrue(pdf.extract_font(xref)[3], "embedded font program present")
        for page in pdf:
            for b in page.get_text("dict")["blocks"]:
                for line in b.get("lines", []):
                    for span in line["spans"]:
                        if span["text"].strip():
                            self.assertGreaterEqual(span["size"], 7.99)

    # 4, 6. D1 positions and houses match the engine.
    def test_d1_positions_and_houses_match_engine(self):
        for case in SCENARIOS:
            _, _, pdf = self.download(case)
            chart = SCENARIOS[case]["chart"]
            table = rows(pdf[premium.PAGE_OF["positions"] - 1])
            for name in premium.GRAHAS:
                body = chart["planets"][name]
                full, abbr = premium.DISPLAY[name]
                pos = layout.sign_position(body["longitude_deg"], body["rashi"])
                self.assertIn(f'{abbr} {full} {layout.SIGNS.index(body["rashi"]) + 1} {body["rashi"]} '
                              f'{body["whole_sign_house"]} {pos.dms()} {body["longitude_deg"]:.8f}°', table, case)
            lag = chart["lagna"]
            self.assertIn(f'Asc Lagna {layout.SIGNS.index(lag["rashi"]) + 1} {lag["rashi"]} 1 '
                          f'{layout.sign_position(lag["longitude_deg"], lag["rashi"]).dms()} '
                          f'{lag["longitude_deg"]:.8f}°', table, case)

    # 5. D9 placements and house directory match the engine.
    def test_d9_placements_and_house_directory_match_engine(self):
        for case in SCENARIOS:
            _, _, pdf = self.download(case)
            chart = SCENARIOS[case]["chart"]
            d9_house = {g: row["house"] for row in chart["d9"]["houses"] for g in row["grahas"]}
            table = rows(pdf[premium.PAGE_OF["navamsa"] - 1])
            for name in premium.GRAHAS:
                body = chart["planets"][name]
                full, abbr = premium.DISPLAY[name]
                self.assertEqual(d9_house[name], body["navamsa_whole_sign_house"])
                self.assertIn(f'{abbr} {full} {layout.SIGNS.index(body["rashi"]) + 1} {body["rashi"]} '
                              f'{layout.SIGNS.index(body["navamsa_rashi"]) + 1} {body["navamsa_rashi"]} '
                              f'{d9_house[name]}', table, case)
            directory = rows(pdf[premium.PAGE_OF["houses"] - 1])
            l1 = layout.SIGNS.index(chart["lagna"]["rashi"])
            d9 = {row["house"]: row for row in chart["d9"]["houses"]}
            for h in range(1, 13):
                g1 = " ".join((["Asc"] if h == 1 else []) + [premium.DISPLAY[n][1] for n in premium.GRAHAS
                                                              if chart["planets"][n]["whole_sign_house"] == h]) or "–"
                g9 = " ".join((["Asc"] if h == 1 else []) + [premium.DISPLAY[n][1] for n in premium.GRAHAS
                                                              if n in d9[h]["grahas"]]) or "–"
                s1, s9 = layout.SIGNS[(l1 + h - 1) % 12], d9[h]["rashi"]
                self.assertIn(f"{h} {layout.SIGNS.index(s1) + 1} {s1} {g1} {layout.SIGNS.index(s9) + 1} {s9} {g9}",
                              directory, (case, h))

    # 4, 5. Chart drawings: every label lies in the engine's house, every house shows the engine's Rashi.
    def test_d1_and_d9_chart_labels_in_engine_houses(self):
        for case in SCENARIOS:
            _, _, pdf = self.download(case)
            chart = SCENARIOS[case]["chart"]
            _, audit = premium.render(SCENARIOS[case], synthetic=False, palette="baseline")  # geometry only
            for mode, key in (("d1", "whole_sign_house"), ("d9", "navamsa_whole_sign_house")):
                info = audit["charts"][mode]
                x0, y0 = info["origin"]
                size, s = info["size"], info["size"] / 600
                top = A4[1] - y0 - size
                want = {"Asc": 1, **{premium.DISPLAY[n][1]: chart["planets"][n][key] for n in premium.GRAHAS}}
                page = pdf[premium.PAGE_OF[mode] - 1]
                found = {}
                for a, b, c, d, word, *_ in page.get_text("words", clip=fitz.Rect(x0, top, x0 + size, top + size)):
                    if word in want:
                        ux, uy = ((a + c) / 2 - x0) / s, ((b + d) / 2 - top) / s
                        found[word] = [h for h in range(1, 13) if layout.inside_house(h, ux, uy)]
                self.assertEqual(set(found), set(want), (case, mode))
                for word, houses in found.items():
                    self.assertEqual(houses, [want[word]], (case, mode, word))
                lagna = chart["lagna"]["rashi"] if mode == "d1" else chart["d9"]["lagna_rashi"]
                start = layout.SIGNS.index(lagna)
                for h in range(1, 13):
                    nx, ny = layout.number_position(h)
                    clip = fitz.Rect(x0 + (nx - 14) * s, top + (ny - 12) * s, x0 + (nx + 14) * s, top + (ny + 12) * s)
                    self.assertEqual(page.get_text(clip=clip).split(), [str((start + h - 1) % 12 + 1)], (case, mode, h))

    # 7. Moon Nakshatra and Pada.
    def test_moon_nakshatra_and_pada(self):
        for case in SCENARIOS:
            _, _, pdf = self.download(case)
            moon = SCENARIOS[case]["chart"]["moon_nakshatra"]
            self.assertIn(f"MOON NAKSHATRA p. 7 {moon['name']} Pada {moon['pada']} of 4", flat(pdf[1]), case)

    # 8. Birthplace, local and UTC birth information.
    def test_birthplace_and_local_and_utc_time(self):
        for case in SCENARIOS:
            _, _, pdf = self.download(case)
            info, birth = SCENARIOS[case]["input"], SCENARIOS[case]["chart"]["birth"]
            text = flat(pdf[premium.PAGE_OF["birth"] - 1])
            place = info["place"]
            for expected in (f"Birthplace {place['name']}", f"Region and country {place['region']}, {place['country']}",
                             f"({info['local_date']})", f"Local time {info['local_time']}",
                             f"Time zone (IANA) {birth['timezone']}", f"UTC offset applied UTC{info['utc_offset']}",
                             "Exact UTC instant " + birth["utc"].replace("T", " ").replace("Z", " UTC"),
                             layout.coordinate(birth["latitude"], "N", "S"),
                             layout.coordinate(birth["longitude"], "E", "W")):
                self.assertIn(expected, text, (case, expected))
            self.assertEqual(info["local_date"], REQUESTS[case]["birth_date"])
            self.assertEqual(place["id"], REQUESTS[case]["place_id"])

    # 9. Methodology and validation-status disclosure.
    def test_methodology_and_validation_status_disclosed(self):
        for case in SCENARIOS:
            _, _, pdf = self.download(case)
            chart = SCENARIOS[case]["chart"]
            text = flat(pdf[premium.PAGE_OF["method"] - 1])
            self.assertIn(f"VALIDATION STATUS: {chart['validation_status']}", text)
            self.assertEqual(chart["validation_status"], "UNVERIFIED_GOLDEN_CHARTS")
            self.assertIn("not yet been certified against an independent set of golden reference charts", text)
            self.assertIn("Chart schema 0.3.0; sabpuja-calculation-metadata/3", text)
            self.assertIn("Absolute longitudes are printed to eight decimals", text)
            self.assertIn("truncated to the arc-second", text)
            self.assertIn("Panchanga, Vimshottari Dasha", text)
            for banned in (r"\byou will\b", r"\bcertified\b(?! against)", r"\bguarantee"):
                self.assertIsNone(re.search(banned, " ".join(flat(p) for p in pdf), re.I), (case, banned))

    def test_no_out_of_page_or_missing_glyph_text(self):
        for case in SCENARIOS:
            _, _, pdf = self.download(case)
            for page in pdf:
                for b in page.get_text("dict")["blocks"]:
                    for line in b.get("lines", []):
                        for span in line["spans"]:
                            if span["text"].strip():
                                self.assertTrue(page.rect.contains(fitz.Rect(span["bbox"])), (case, span["text"]))
                                self.assertNotIn("�", span["text"])

    # 12. In memory and bounded.
    def test_generated_in_memory_without_files_and_within_size_limit(self):
        writes = []
        real_open = builtins.open

        def guarded_open(file, mode="r", *a, **k):
            if any(m in mode for m in "wax+"):
                writes.append(str(file))
            return real_open(file, mode, *a, **k)
        with tempfile.TemporaryDirectory() as tmp:
            cwd = os.getcwd()
            os.chdir(tmp)
            builtins.open = guarded_open
            try:
                status, _, data = self.post("/api/report", REQUESTS["s11-afternoon"])
            finally:
                builtins.open = real_open
                os.chdir(cwd)
            self.assertEqual(os.listdir(tmp), [])
        self.assertEqual(status, 200)
        self.assertEqual(writes, [])
        self.assertLessEqual(len(data), server.MAX_PDF_BYTES)
        for _, data, _ in (self.download(c) for c in SCENARIOS):
            self.assertLess(len(data), server.MAX_PDF_BYTES)
        pdf = fitz.open(stream=data, filetype="pdf")
        info = SCENARIOS["s11-afternoon"]["input"]
        for secret in (info["local_date"], info["local_time"], info["place"]["name"]):
            self.assertNotIn(secret, json.dumps(pdf.metadata))
        self.assertNotIn("Sample report", flat(pdf[1]))  # customer requests are never marked synthetic

    def test_server_logs_nothing_on_success(self):
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured), contextlib.redirect_stdout(captured):
            status, _, _ = self.post("/api/report", REQUESTS[PRIMARY])
        self.assertEqual(status, 200)
        self.assertEqual(captured.getvalue(), "")

    def test_chart_endpoint_unchanged_for_scenarios(self):
        for case in SCENARIOS:
            status, headers, data = self.post("/api/chart", REQUESTS[case])
            self.assertEqual(status, 200)
            self.assertEqual(data, json.dumps(SCENARIOS[case], ensure_ascii=False).encode("utf-8"), case)

    def test_engine_refusals_return_json_not_pdf(self):
        cases = [
            ({"place_id": "in-atlantis", "birth_date": "1990-05-15", "birth_time": "10:30"}, 422, "PLACE_UNKNOWN"),
            ({"place_id": "in-new-delhi", "birth_date": "1990-02-30", "birth_time": "10:30"}, 422, "BIRTH_DATE_INVALID"),
            ({"place_id": "in-new-delhi", "birth_date": "15-05-1990", "birth_time": "10:30"}, 422, "BIRTH_DATE_INVALID"),
            ({"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": "24:00"}, 422, "BIRTH_TIME_INVALID"),
            ({"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": ""}, 422, "BIRTH_TIME_REQUIRED"),
            ({"place_id": "gb-london", "birth_date": "2020-10-25", "birth_time": "01:30"}, 409, "TIME_AMBIGUOUS_LOCAL"),
            ({"place_id": "in-new-delhi", "birth_date": "1990-05-15"}, 400, "REQUEST_INVALID"),
            ({"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": "10:30", "palette": "od10-candidate"},
             400, "REQUEST_INVALID"),
        ]
        for body, status, code in cases:
            self.assertRefusedWithoutPDF(*self.post("/api/report", body), status, code)


@needs_fitz
class PremiumReportFailsClosed(Server):
    """Invalid scientific input or renderer failure: fixed REPORT_UNAVAILABLE, never a PDF."""

    places = {}  # the trusted engine response is supplied by patching server.compute

    def report_with(self, response):
        captured = io.StringIO()
        with mock.patch.object(server, "compute", return_value=response), contextlib.redirect_stderr(captured):
            status, headers, data = self.post("/api/report", {"place_id": "in-new-delhi", "birth_date": "1990-05-15",
                                                              "birth_time": "10:30"})
        return status, headers, data, captured.getvalue()

    def assertUnavailable(self, response, label):
        status, headers, data, log = self.report_with(response)
        self.assertRefusedWithoutPDF(status, headers, data, 503, "REPORT_UNAVAILABLE")
        self.assertEqual(json.loads(data)["error"]["message"], "the PDF could not be generated", label)
        for secret in ("Jaipur", "2039-07-31", "12:00:00", "26.91962"):
            self.assertNotIn(secret, log, label)
            self.assertNotIn(secret.encode(), data, label)
        self.assertRegex(log.strip(), r'^\{"event": "REPORT_FAILURE", "type": "[A-Za-z]+"\}$', label)

    def mutated(self, change):
        data = copy.deepcopy(SCENARIOS[PRIMARY])
        change(data)
        return data

    def test_valid_patched_response_still_renders(self):
        status, headers, data, log = self.report_with(copy.deepcopy(SCENARIOS[PRIMARY]))
        self.assertEqual(status, 200)
        self.assertEqual(data, premium.generate(SCENARIOS[PRIMARY], palette="baseline"))
        self.assertEqual(log, "")

    def test_missing_calculation_metadata(self):
        self.assertUnavailable(self.mutated(lambda d: d["chart"].pop("calculation_metadata")), "no metadata")
        self.assertUnavailable(self.mutated(lambda d: d["chart"]["calculation_metadata"].update(
            metadata_schema="sabpuja-calculation-metadata/2")), "metadata /2")

    def test_wrong_schema(self):
        self.assertUnavailable(self.mutated(lambda d: d["chart"].update(schema_version="0.4.0")), "schema 0.4.0")
        self.assertUnavailable(self.mutated(lambda d: d["chart"].update(schema_version="0.2.0")), "schema 0.2.0")

    def test_mismatched_d1_house(self):
        def change(d):
            body = d["chart"]["planets"]["sun"]
            body["whole_sign_house"] = body["whole_sign_house"] % 12 + 1
        self.assertUnavailable(self.mutated(change), "D1 house")

    def test_mismatched_d9_house(self):
        def change(d):
            body = d["chart"]["planets"]["moon"]
            body["navamsa_whole_sign_house"] = body["navamsa_whole_sign_house"] % 12 + 1
        self.assertUnavailable(self.mutated(change), "D9 house")

        def change_block(d):
            rows_ = d["chart"]["d9"]["houses"]
            src = next(r for r in rows_ if "moon" in r["grahas"])
            src["grahas"].remove("moon")
            next(r for r in rows_ if r is not src)["grahas"].append("moon")
        self.assertUnavailable(self.mutated(change_block), "D9 block")

    def test_invalid_longitude(self):
        for value in (math.nan, math.inf, -1.0, 360.0, 400.0, "12.5", None, True):
            self.assertUnavailable(self.mutated(lambda d, v=value: d["chart"]["planets"]["mars"].update(
                longitude_deg=v)), f"longitude {value!r}")

        def wrong_rashi(d):
            body = d["chart"]["planets"]["mars"]
            body["longitude_deg"] = (body["longitude_deg"] + 30) % 360
        self.assertUnavailable(self.mutated(wrong_rashi), "longitude outside the engine Rashi")

    def test_unsupported_glyphs(self):
        self.assertUnavailable(self.mutated(lambda d: d["input"]["place"].update(name="नई दिल्ली")), "Devanagari")
        self.assertUnavailable(self.mutated(lambda d: d["input"]["place"].update(region="Region 中")), "CJK")

    def test_oversized_generated_pdf(self):
        big = b"%PDF-1.7 " + b"x" * server.MAX_PDF_BYTES
        with mock.patch.object(premium, "generate", return_value=big) as gen:
            self.assertUnavailable(copy.deepcopy(SCENARIOS[PRIMARY]), "oversize")
        gen.assert_called_once()
        self.assertEqual(gen.call_args.kwargs, {"synthetic": False, "palette": "baseline"})

    def test_not_a_pdf(self):
        with mock.patch.object(premium, "generate", return_value=b"<html>not a pdf</html>"):
            self.assertUnavailable(copy.deepcopy(SCENARIOS[PRIMARY]), "not a PDF")

    def test_rendering_exception_text_never_leaks(self):
        with mock.patch.object(premium, "generate", side_effect=RuntimeError("Jaipur 2039-07-31 12:00:00 26.91962")):
            self.assertUnavailable(copy.deepcopy(SCENARIOS[PRIMARY]), "exception")

    def test_renderer_failure_keeps_the_route_available(self):
        with mock.patch.object(premium, "generate", side_effect=MemoryError()):
            self.assertUnavailable(copy.deepcopy(SCENARIOS[PRIMARY]), "MemoryError")
        status, _, data, _ = self.report_with(copy.deepcopy(SCENARIOS[PRIMARY]))
        self.assertEqual(status, 200)
        self.assertTrue(data.startswith(b"%PDF-"))

    def test_concurrent_report_requests(self):
        started, release = threading.Event(), threading.Event()
        real = premium.generate

        def slow(*a, **k):
            started.set()
            release.wait(20)
            return real(*a, **k)
        results = {}
        body = {"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": "10:30"}
        with mock.patch.object(server, "compute", return_value=copy.deepcopy(SCENARIOS[PRIMARY])), \
                mock.patch.object(premium, "generate", side_effect=slow):
            first = threading.Thread(target=lambda: results.update(first=self.post("/api/report", body)))
            first.start()
            self.assertTrue(started.wait(20))
            busy = [self.post("/api/report", body) for _ in range(3)]
            chart = self.post("/api/chart", body)
            release.set()
            first.join(30)
        for status, headers, data in busy:
            self.assertRefusedWithoutPDF(status, headers, data, 429, "REPORT_BUSY")
        self.assertEqual(chart[0], 200, "chart requests are not blocked by a running PDF render")
        status, headers, data = results["first"]
        self.assertEqual(status, 200)
        self.assertEqual(data, real(SCENARIOS[PRIMARY], synthetic=False, palette="baseline"))
        self.assertTrue(server._PDF_RENDER_SLOT.acquire(blocking=False), "render slot released")
        server._PDF_RENDER_SLOT.release()

    def test_malformed_json(self):
        for raw in (b"{", b"not json", b"[]", b'{"place_id": "a", "place_id": "b"}', b"\xff\xfe"):
            with mock.patch.object(premium, "generate") as gen:
                status, headers, data = self.post("/api/report", raw)
            gen.assert_not_called()
            self.assertRefusedWithoutPDF(status, headers, data, 400, "REQUEST_INVALID")

    def test_disallowed_origin_and_request_limits(self):
        with mock.patch.object(server, "compute") as compute, mock.patch.object(premium, "generate") as gen:
            self.assertRefusedWithoutPDF(*self.post("/api/report", {}, origin="https://evil.example"),
                                         403, "ORIGIN_NOT_ALLOWED")
            self.assertRefusedWithoutPDF(*self.post("/api/report", {}, origin="null"), 403, "ORIGIN_NOT_ALLOWED")
            self.assertRefusedWithoutPDF(*self.post("/api/report", {}, content_type="text/plain"),
                                         415, "CONTENT_TYPE_INVALID")
            self.assertRefusedWithoutPDF(*self.post("/api/report", b"x" * (server.MAX_BODY_BYTES + 1)),
                                         413, "REQUEST_TOO_LARGE")
            compute.assert_not_called()
            gen.assert_not_called()


class RouteSelection(unittest.TestCase):
    """The route is wired to the premium renderer with the fixed approved palette."""

    def test_route_uses_premium_renderer_with_saffron_palette(self):
        self.assertEqual(server.REPORT_PALETTE, "baseline")
        self.assertEqual(premium.THEMES["default_palette"], "baseline")
        self.assertEqual(premium.THEMES["palettes"]["baseline"]["status"], "approved")
        src = (ROOT / "prototype/kundali_prototype/server.py").read_text()
        self.assertIn("from report.phase1.premium_report import generate", src)
        self.assertNotIn("from report.phase1.generate_report import", src)
        self.assertNotIn("od10", src)
        self.assertNotIn("maroon", src.lower())

    def test_palette_never_read_from_the_request(self):
        with mock.patch.object(server, "handle_chart", return_value=(200, {"input": {}, "chart": {}})), \
                mock.patch.object(premium, "generate", return_value=b"%PDF-1.7 ok") as gen:
            status, body = server.handle_report(b'{"palette": "od10-candidate"}', {}, "/unused")
        self.assertEqual((status, body), (200, b"%PDF-1.7 ok"))
        gen.assert_called_once_with({"input": {}, "chart": {}}, synthetic=False, palette="baseline")

    def test_phase1_renderer_remains_available_for_rollback(self):
        from report.phase1 import generate_report
        fixture = json.loads((ROOT / "report/phase1/tests/fixtures/synthetic-new-delhi.json").read_text())
        data = generate_report.generate(fixture, synthetic=True)
        self.assertTrue(data.startswith(b"%PDF-"))
        if fitz:
            self.assertEqual(len(fitz.open(stream=data, filetype="pdf")), 8)


if __name__ == "__main__":
    unittest.main()
