"""KUN-I18N-001: report language on /api/report, through the real HTTP path.

Synthetic birth details and synthetic names only. report_locale is presentation data: accepted
by /api/report alone, validated against exactly "en" and "hi", removed before the name split and
the unchanged chart handler, passed to the renderer separately from the engine response, and
never stored, logged or echoed. The interface catalog is checked against the page and engine.
"""
import contextlib
import copy
import http.client
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

from kundali_prototype import server

from support import EPHE, requires_data
from test_display_name_http import BODY, CANARY, HINDI, named
from test_premium_pdf_http import PRIMARY, REQUESTS, SCENARIOS, Server, fitz, needs_fitz, premium

ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "prototype/kundali_prototype/static"
CATALOG = json.loads((STATIC / "i18n.json").read_text(encoding="utf-8"))


def localized(request, locale):
    body = dict(request)
    body["report_locale"] = locale
    return body


@requires_data
@needs_fitz
class LocaleOverHTTP(Server):
    def test_omitted_and_explicit_en_are_the_pr58_bytes(self):
        expected = premium.generate(SCENARIOS[PRIMARY], synthetic=False, palette="baseline")
        for body in (REQUESTS[PRIMARY], localized(REQUESTS[PRIMARY], "en")):
            with self.subTest(body=sorted(body)):
                status, headers, data = self.post("/api/report", body)
                self.assertEqual(status, 200)
                self.assertEqual(data, expected)
                self.assertEqual(headers["content-disposition"], 'attachment; filename="Sabpuja-Janma-Kundali.pdf"')
                self.assertEqual(headers["cache-control"], "no-store")

    def test_hindi_report(self):
        for name in (None, HINDI, "Zoë-Anne O’Brien"):
            with self.subTest(name=name):
                body = localized(REQUESTS[PRIMARY], "hi")
                if name is not None:
                    body = named(body, name)
                status, headers, data = self.post("/api/report", body)
                self.assertEqual(status, 200)
                self.assertEqual(data, premium.generate(SCENARIOS[PRIMARY], synthetic=False, palette="baseline",
                                                        locale="hi", **({} if name is None else {"display_name": name})))
                self.assertEqual(headers["content-type"], "application/pdf")
                self.assertEqual(headers["content-disposition"], 'attachment; filename="Sabpuja-Janma-Kundali.pdf"')
                self.assertEqual(headers["cache-control"], "no-store")
                pdf = fitz.open(stream=data, filetype="pdf")
                self.assertEqual(len(pdf), 10)
                self.assertIn("जन्म कुंडली", pdf[0].get_text())
                for value in ("hi", "Hindi", "report_locale"):
                    self.assertNotIn(value, headers["content-disposition"])

    def test_locale_never_reaches_the_chart_handler(self):
        seen = []
        real = server.handle_chart
        with mock.patch.object(server, "handle_chart", side_effect=lambda r, *a: seen.append(r) or real(r, *a)):
            for body in (localized(REQUESTS[PRIMARY], "hi"), named(localized(REQUESTS[PRIMARY], "en"), CANARY)):
                self.assertEqual(self.post("/api/report", body)[0], 200)
        self.assertEqual([json.loads(r) for r in seen], [REQUESTS[PRIMARY], REQUESTS[PRIMARY]])

    def test_same_engine_values_in_both_languages(self):
        status, _, chart = self.post("/api/chart", REQUESTS[PRIMARY])
        self.assertEqual(status, 200)
        number = re.compile(r"\d+\.\d{8}°")
        texts = {}
        for locale in ("en", "hi"):
            data = self.post("/api/report", localized(REQUESTS[PRIMARY], locale))[2]
            texts[locale] = sorted(number.findall(fitz.open(stream=data, filetype="pdf")[6].get_text()))
        self.assertEqual(texts["en"], texts["hi"])
        response = json.loads(chart)
        for g, body in response["chart"]["planets"].items():
            self.assertIn(f'{body["longitude_deg"]:.8f}°', texts["hi"], g)

    def test_chart_api_refuses_report_locale(self):
        for locale in ("en", "hi"):
            self.assertRefusedWithoutPDF(*self.post("/api/chart", localized(BODY, locale)), 400, "REQUEST_INVALID")
        for case in SCENARIOS:
            status, _, data = self.post("/api/chart", REQUESTS[case])
            self.assertEqual(json.loads(data), SCENARIOS[case])

    def test_hindi_renderer_failure_is_a_fixed_refusal(self):
        captured = io.StringIO()
        with mock.patch.object(server, "compute", return_value=copy.deepcopy(SCENARIOS[PRIMARY])), \
                mock.patch.object(premium, "generate", side_effect=RuntimeError(CANARY)), \
                contextlib.redirect_stderr(captured):
            status, headers, data = self.post("/api/report", named(localized(BODY, "hi"), CANARY))
        self.assertRefusedWithoutPDF(status, headers, data, 503, "REPORT_UNAVAILABLE")
        self.assertNotIn(CANARY, captured.getvalue())
        self.assertNotIn(CANARY.encode(), data)


class LocaleRefusals(Server):
    """Unsupported values are refused before the engine or renderer runs, without echo or log."""

    UNSUPPORTED = ["fr", "HI", "En", "hi-IN", "en-US", "", " hi", "hin", "हिंदी", "<script>alert(1)</script>",
                   "../../etc/passwd", "hi\n", "hi\x00", "%68%69", CANARY, "e" * 3000]
    WRONG_TYPE = [None, 1, 0, True, ["hi"], {"locale": "hi"}, 1.5]

    def post_quiet(self, body):
        captured = io.StringIO()
        with mock.patch.object(server, "compute") as compute, mock.patch.object(premium, "generate") as gen, \
                contextlib.redirect_stderr(captured), contextlib.redirect_stdout(captured):
            result = self.post("/api/report", body)
        compute.assert_not_called()
        gen.assert_not_called()
        return result, captured.getvalue()

    def test_unsupported_values(self):
        for bad in self.UNSUPPORTED:
            with self.subTest(bad=bad[:20]):
                (status, headers, data), log = self.post_quiet(named(localized(BODY, bad), CANARY))
                self.assertRefusedWithoutPDF(status, headers, data, 422, "REPORT_LOCALE_UNSUPPORTED")
                self.assertEqual(json.loads(data)["error"]["message"], "report_locale must be en or hi")
                self.assertEqual(log, "")
                if bad.strip() and bad.strip() not in "report_locale must be en or hi":
                    self.assertNotIn(bad.encode(), data)
                    self.assertNotIn(json.dumps(bad).encode(), data)
                self.assertNotIn(CANARY.encode(), data)

    def test_wrong_type(self):
        for bad in self.WRONG_TYPE:
            with self.subTest(bad=bad):
                (status, headers, data), log = self.post_quiet(localized(BODY, bad))
                self.assertRefusedWithoutPDF(status, headers, data, 400, "REQUEST_INVALID")
                self.assertEqual(json.loads(data)["error"]["message"], "report_locale must be a string")
                self.assertEqual(log, "")

    def test_duplicate_key_and_oversized_body(self):
        raw = b'{"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": "10:30", ' \
              b'"report_locale": "hi", "report_locale": "en"}'
        (status, headers, data), log = self.post_quiet(raw)
        self.assertRefusedWithoutPDF(status, headers, data, 400, "REQUEST_INVALID")
        self.assertEqual(log, "")
        big = json.dumps(localized(BODY, "hi" + " " * (server.MAX_BODY_BYTES + 10))).encode()
        (status, headers, data), _ = self.post_quiet(big)
        self.assertRefusedWithoutPDF(status, headers, data, 413, "REQUEST_TOO_LARGE")

    def test_name_validation_unchanged_with_a_locale(self):
        (status, headers, data), log = self.post_quiet(named(localized(BODY, "hi"), "Asha\nVerma"))
        self.assertEqual(status, 422)
        self.assertEqual(json.loads(data)["error"]["code"], "DISPLAY_NAME_INVALID")
        self.assertEqual(log, "")

    def test_auth_and_origin_unchanged_with_a_locale(self):
        body = localized(BODY, "hi")
        with mock.patch.object(server, "compute") as compute, mock.patch.object(premium, "generate") as gen:
            self.assertRefusedWithoutPDF(*self.post("/api/report", body, origin="https://evil.example"),
                                         403, "ORIGIN_NOT_ALLOWED")
            self.assertRefusedWithoutPDF(*self.post("/api/report", body, content_type="text/plain"),
                                         415, "CONTENT_TYPE_INVALID")
            compute.assert_not_called()
            gen.assert_not_called()

    def test_renderer_receives_the_locale_separately(self):
        with mock.patch.object(server, "handle_chart", return_value=(200, {"input": {}, "chart": {}})) as chart, \
                mock.patch.object(premium, "generate", return_value=b"%PDF-1.7 ok") as gen:
            status, body = server.handle_report(
                '{"report_locale": "hi", "display_name": "Zoë", "place_id": "x"}'.encode(), {}, "/unused")
        self.assertEqual((status, body), (200, b"%PDF-1.7 ok"))
        gen.assert_called_once_with({"input": {}, "chart": {}}, synthetic=False, palette="baseline",
                                    display_name="Zoë", locale="hi")
        self.assertEqual(json.loads(chart.call_args.args[0]), {"place_id": "x"})
        with mock.patch.object(server, "handle_chart", return_value=(200, {"input": {}, "chart": {}})) as chart, \
                mock.patch.object(premium, "generate", return_value=b"%PDF-1.7 ok") as gen:
            server.handle_report(b'{"report_locale": "en", "place_id": "x"}', {}, "/unused")
        gen.assert_called_once_with({"input": {}, "chart": {}}, synthetic=False, palette="baseline")

    def test_request_without_locale_is_passed_byte_for_byte(self):
        for raw in (b'{"place_id":"x",  "birth_date":"y"}', b'not json', b'[1,2]', b'{"a":"\\u00e9"}'):
            self.assertEqual(server._split_report_locale(raw), (raw, None))

    def test_chart_parsing_is_unchanged(self):
        import inspect
        self.assertEqual(server._FORM_KEYS, {"place_id", "birth_date", "birth_time"})
        for fn in (server._parse_form, server.compute, server.handle_chart, server._split_display_name):
            self.assertNotIn("locale", inspect.getsource(fn))


class StaticCatalog(Server):
    def get(self, path):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("GET", path, headers={"Host": self.host})
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, {k.lower(): v for k, v in resp.getheaders()}, data

    def test_catalog_is_served_as_utf8_json(self):
        status, headers, data = self.get("/static/i18n.json")
        self.assertEqual(status, 200)
        self.assertEqual(headers["content-type"], "application/json; charset=utf-8")
        self.assertEqual(json.loads(data), CATALOG)
        for font in (400, 500, 600, 700):
            status, headers, _ = self.get(f"/static/fonts/poppins-devanagari-{font}-normal.woff2")
            self.assertEqual((status, headers["content-type"]), (200, "font/woff2"), font)

    def test_page_text_matches_the_english_catalog(self):
        """The page's built-in English is the catalog English, so the page reads the same before
        the catalog has loaded, and no key on the page is missing from the catalog."""
        html = (STATIC / "index.html").read_text(encoding="utf-8")
        found = re.findall(r'data-i18n="([^"]+)"[^>]*>([^<]*)<', html)
        self.assertGreater(len(found), 40)
        for key, text in found:
            self.assertTrue(key in CATALOG["ui"], key)
            self.assertEqual(" ".join(text.split()), " ".join(CATALOG["ui"][key]["en"].split()), key)
        for key in re.findall(r'data-i18n-aria="([^"]+)"', html):
            self.assertIn(key, CATALOG["ui"], key)
        js = (STATIC / "app.js").read_text(encoding="utf-8")
        for key in set(re.findall(r'\bt\("([a-z0-9_.]+)"', js)) | set(re.findall(r'setStatus\("([a-z0-9_.]+)"', js)):
            if not key.endswith("."):   # a prefix such as "fault." + category is checked below
                self.assertTrue(key in CATALOG["ui"], key)

    def test_every_message_the_pr58_page_translated_has_both_languages(self):
        codes = ("HISTORICAL_CLOCK_UNVERIFIED DATE_OUTSIDE_SUPPORTED_RANGE LATITUDE_OUTSIDE_SUPPORTED_BAND "
                 "TIME_NONEXISTENT_LOCAL TIME_AMBIGUOUS_LOCAL BIRTH_TIME_REQUIRED BIRTH_TIME_INVALID "
                 "BIRTH_DATE_INVALID PLACE_UNKNOWN REQUEST_INVALID DISPLAY_NAME_INVALID DISPLAY_NAME_TOO_LONG "
                 "INTERNAL_ERROR").split()
        for code in codes:
            entry = CATALOG["ui"]["msg." + code]
            self.assertTrue(entry["en"] and entry["hi"], code)
        for key in ("fault.resources", "fault.computation", "error.fallback"):
            self.assertTrue(CATALOG["ui"][key]["hi"], key)

    def test_every_place_has_a_hindi_name(self):
        places = json.loads((ROOT / "prototype/kundali_prototype/places.json").read_text())["places"]
        for place in places:
            entry = CATALOG["terms"]["place"][place["id"]]
            self.assertEqual(entry["en"], [place["name"], place["region"], place["country"]])
            self.assertTrue(all(entry["hi"]), place["id"])

    def test_catalog_marks_itself_unreviewed(self):
        self.assertIn("pending independent human Hindi editorial review", CATALOG["status"])
        self.assertIn("Not owner-approved", CATALOG["status"])
        self.assertEqual(CATALOG["default_locale"], "en")


@requires_data
class ServerProcessLogs(unittest.TestCase):
    """The real server process writes nothing about a Hindi or refused-locale request."""

    def test_process_output_has_no_locale_or_names(self):
        import socket
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        env = dict(os.environ, SABPUJA_EPHE_PATH=EPHE, PYTHONDONTWRITEBYTECODE="1",
                   PYTHONPATH=os.pathsep.join([str(ROOT / "src"), str(ROOT / "prototype"), str(ROOT)]))
        with tempfile.TemporaryDirectory() as cwd:
            proc = subprocess.Popen([sys.executable, "-m", "kundali_prototype", "--port", str(port)], cwd=cwd, env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            try:
                for _ in range(300):
                    try:
                        socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
                        break
                    except OSError:
                        time.sleep(0.1)
                host = f"127.0.0.1:{port}"
                statuses = []
                for body in (named(localized(BODY, "hi"), HINDI), named(localized(BODY, "hi"), CANARY),
                             localized(BODY, CANARY), localized(BODY, "<script>x</script>"), localized(BODY, 7)):
                    raw = json.dumps(body).encode()
                    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
                    conn.request("POST", "/api/report", raw, {"Host": host, "Origin": f"http://{host}",
                                                              "Content-Type": "application/json",
                                                              "Content-Length": str(len(raw))})
                    statuses.append(conn.getresponse().status)
                    conn.close()
                files = [p for p in Path(cwd).rglob("*")]
            finally:
                proc.terminate()
                out, err = proc.communicate(timeout=10)
        self.assertEqual(statuses, [200, 200, 422, 422, 400])
        self.assertEqual(files, [], "no files written")
        for text in (out, err):
            for leak in (CANARY, HINDI, "report_locale", "<script>", "1990-05-15", "10:30", "in-new-delhi"):
                self.assertNotIn(leak, text)


if __name__ == "__main__":
    unittest.main()
