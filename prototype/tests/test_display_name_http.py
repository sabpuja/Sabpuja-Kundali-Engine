"""KUN-UX-NAME-001: optional report name on /api/report, through the real HTTP path.

Synthetic birth details and synthetic names only. The name is presentation data: it is
accepted by /api/report alone, validated separately, removed before the unchanged chart
handler runs, drawn by the premium renderer, and never stored, logged or echoed.
"""
import contextlib
import copy
import io
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

from kundali_prototype import server
from kundali_prototype.places import load_places

from support import EPHE, requires_data
from test_premium_pdf_http import (PRIMARY, REQUESTS, SCENARIOS, Server, fitz, needs_fitz, premium)

ROOT = Path(__file__).resolve().parents[2]
CANARY = "Zzyzx Qwertyuiop"          # synthetic, never a real person; searched for in every log
HINDI = "क्षत्रिय प्रियंका सिद्धार्थ"
BODY = {"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": "10:30"}


def named(request, name):
    body = dict(request)
    body["display_name"] = name
    return body


@requires_data
@needs_fitz
class NamedReportOverHTTP(Server):
    def test_no_name_request_is_unchanged(self):
        """Existing clients: the same bytes as the renderer without a name, and the chart handler
        receives the request body byte for byte."""
        raw = json.dumps(REQUESTS[PRIMARY]).encode()
        seen = []
        real = server.handle_chart
        with mock.patch.object(server, "handle_chart", side_effect=lambda r, *a: seen.append(r) or real(r, *a)):
            status, headers, data = self.post("/api/report", raw)
        self.assertEqual(status, 200)
        self.assertEqual(seen, [raw])
        self.assertEqual(data, premium.generate(SCENARIOS[PRIMARY], synthetic=False, palette="baseline"))
        self.assertEqual(headers["content-disposition"], 'attachment; filename="Sabpuja-Janma-Kundali.pdf"')

    def test_empty_or_null_name_is_the_anonymous_report(self):
        anonymous = premium.generate(SCENARIOS[PRIMARY], synthetic=False, palette="baseline")
        for value in ("", "   ", " ", None):
            with self.subTest(value=value):
                status, _, data = self.post("/api/report", named(REQUESTS[PRIMARY], value))
                self.assertEqual(status, 200)
                self.assertEqual(data, anonymous)

    def test_named_report(self):
        for name in ("Asha Verma", HINDI, "Zoë-Anne O’Brien", "Ravi रवि Kumār", "  R. K. Sharma  "):
            with self.subTest(name=name):
                status, headers, data = self.post("/api/report", named(REQUESTS[PRIMARY], name))
                self.assertEqual(status, 200, data[:200])
                shown = name.strip()
                self.assertEqual(data, premium.generate(SCENARIOS[PRIMARY], synthetic=False, palette="baseline",
                                                        display_name=shown))
                pdf = fitz.open(stream=data, filetype="pdf")
                self.assertEqual(len(pdf), 10)
                self.assertIn(shown, pdf[0].get_text())
                self.assertIn(shown, pdf[3].get_text())
                self.assertEqual(pdf.metadata["title"], "Sabpuja Janma Kundali")
                self.assertEqual(headers["content-type"], "application/pdf")
                self.assertEqual(headers["content-disposition"], 'attachment; filename="Sabpuja-Janma-Kundali.pdf"')
                self.assertEqual(headers["cache-control"], "no-store")
                self.assertNotIn("set-cookie", headers)
                for value in headers.values():
                    self.assertNotIn(shown, value)

    def test_name_never_reaches_the_chart_handler_or_engine(self):
        seen_raw, seen_engine = [], []
        real_chart, real_calc = server.handle_chart, server.calculate
        with mock.patch.object(server, "handle_chart", side_effect=lambda r, *a: seen_raw.append(r) or real_chart(r, *a)), \
                mock.patch.object(server, "calculate", side_effect=lambda req, **k: seen_engine.append(req) or real_calc(req, **k)):
            status, _, data = self.post("/api/report", named(REQUESTS[PRIMARY], CANARY))
        self.assertEqual(status, 200)
        self.assertEqual([json.loads(r) for r in seen_raw], [REQUESTS[PRIMARY]])
        for raw in seen_raw:
            self.assertNotIn(b"display_name", raw)
            self.assertNotIn(CANARY.encode(), raw)
        self.assertTrue(seen_engine)
        for req in seen_engine:
            self.assertNotIn(CANARY, json.dumps(req))
            self.assertEqual(set(req), {"birth_datetime", "timezone", "latitude", "longitude"})

    def test_d1_d9_values_identical_with_and_without_name(self):
        """Every scenario: the name changes only the cover and page 4; positions, D1/D9 charts,
        Navamsa and house pages carry exactly the anonymous report's words."""
        for case in SCENARIOS:
            with self.subTest(case):
                _, _, plain = self.post("/api/report", REQUESTS[case])
                _, _, withname = self.post("/api/report", named(REQUESTS[case], HINDI))
                a, b = fitz.open(stream=plain, filetype="pdf"), fitz.open(stream=withname, filetype="pdf")
                for number in (2, 3, 5, 6, 7, 8, 9, 10):
                    self.assertEqual(a[number - 1].get_text("words"), b[number - 1].get_text("words"), number)

    def test_chart_api_is_unchanged_and_still_refuses_a_name(self):
        for case in SCENARIOS:
            status, _, data = self.post("/api/chart", REQUESTS[case])
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(data), SCENARIOS[case])
            self.assertEqual(json.loads(data)["chart"]["schema_version"], "0.3.0")
        self.assertRefusedWithoutPDF(*self.post("/api/chart", named(BODY, "Asha Verma")), 400, "REQUEST_INVALID")


class NameRefusals(Server):
    """Invalid names are refused before the engine or renderer runs, without echo or log."""

    BAD = ["Asha\nVerma", "‮amreV", "<script>alert(1)</script>", "<img src=x onerror=alert(1)>",
           "Asha & Ravi", "javascript:alert(1)", "Asha​Verma", "Asha😀", "张伟", "A" * 81, "क्ष" * 41,
           "Asha\x00", "'Asha", "Asha  Verma", "ṛṣi"]

    def post_quiet(self, body):
        captured = io.StringIO()
        with mock.patch.object(server, "compute") as compute, mock.patch.object(premium, "generate") as gen, \
                contextlib.redirect_stderr(captured), contextlib.redirect_stdout(captured):
            result = self.post("/api/report", body)
        compute.assert_not_called()
        gen.assert_not_called()
        return result, captured.getvalue()

    def test_invalid_names(self):
        for bad in self.BAD:
            with self.subTest(bad=bad):
                (status, headers, data), log = self.post_quiet(named(BODY, bad))
                code = "DISPLAY_NAME_TOO_LONG" if bad in ("A" * 81, "क्ष" * 41) else "DISPLAY_NAME_INVALID"
                self.assertRefusedWithoutPDF(status, headers, data, 422, code)
                self.assertEqual(log, "")
                text = data.decode("utf-8")
                for part in bad.split():
                    if len(part) > 2:
                        self.assertNotIn(part, text)

    def test_wrong_type(self):
        for bad in (1, True, ["Asha"], {"first": "Asha"}):
            with self.subTest(bad=bad):
                (status, headers, data), log = self.post_quiet(named(BODY, bad))
                self.assertRefusedWithoutPDF(status, headers, data, 400, "REQUEST_INVALID")
                self.assertEqual(log, "")

    def test_duplicate_or_oversized(self):
        raw = b'{"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": "10:30", ' \
              b'"display_name": "Asha", "display_name": "Ravi"}'
        (status, headers, data), _ = self.post_quiet(raw)
        self.assertRefusedWithoutPDF(status, headers, data, 400, "REQUEST_INVALID")
        big = json.dumps(named(BODY, "A" * (server.MAX_BODY_BYTES))).encode()
        (status, headers, data), _ = self.post_quiet(big)
        self.assertRefusedWithoutPDF(status, headers, data, 413, "REQUEST_TOO_LARGE")
        # Within 4 KiB but over the 320 code point bound: refused before any other work.
        (status, headers, data), _ = self.post_quiet(named(BODY, " " * 330 + "Asha"))
        self.assertRefusedWithoutPDF(status, headers, data, 422, "DISPLAY_NAME_TOO_LONG")

    def test_scientific_refusals_still_win_for_valid_names(self):
        captured = io.StringIO()
        with contextlib.redirect_stderr(captured):
            status, headers, data = self.post("/api/report", named(
                {"place_id": "in-new-delhi", "birth_date": "1990-02-30", "birth_time": "10:30"}, CANARY))
        self.assertRefusedWithoutPDF(status, headers, data, 422, "BIRTH_DATE_INVALID")
        self.assertNotIn(CANARY.encode(), data)
        self.assertNotIn(CANARY, captured.getvalue())
        status, headers, data = self.post("/api/report", named({"place_id": "nowhere", "birth_date": "1990-05-15",
                                                                "birth_time": "10:30"}, CANARY))
        self.assertRefusedWithoutPDF(status, headers, data, 422, "PLACE_UNKNOWN")

    def test_auth_and_limits_unchanged_with_a_name(self):
        body = named(BODY, CANARY)
        with mock.patch.object(server, "compute") as compute, mock.patch.object(premium, "generate") as gen:
            self.assertRefusedWithoutPDF(*self.post("/api/report", body, origin="https://evil.example"),
                                         403, "ORIGIN_NOT_ALLOWED")
            self.assertRefusedWithoutPDF(*self.post("/api/report", body, content_type="text/plain"),
                                         415, "CONTENT_TYPE_INVALID")
            compute.assert_not_called()
            gen.assert_not_called()

    def test_busy_slot_with_a_name(self):
        started, release = threading.Event(), threading.Event()

        def slow(*a, **k):
            started.set()
            release.wait(20)
            return b"%PDF-1.7 ok"
        results = {}
        with mock.patch.object(server, "compute", return_value=copy.deepcopy(SCENARIOS[PRIMARY])), \
                mock.patch.object(premium, "generate", side_effect=slow) as gen:
            first = threading.Thread(target=lambda: results.update(first=self.post("/api/report", named(BODY, "Asha"))))
            first.start()
            self.assertTrue(started.wait(20))
            busy = self.post("/api/report", named(BODY, CANARY))
            release.set()
            first.join(30)
        self.assertRefusedWithoutPDF(*busy, 429, "REPORT_BUSY")
        self.assertNotIn(CANARY.encode(), busy[2])
        self.assertEqual(results["first"][0], 200)
        self.assertEqual(gen.call_args.kwargs, {"synthetic": False, "palette": "baseline", "display_name": "Asha"})

    def test_renderer_failure_logs_no_name(self):
        captured = io.StringIO()
        with mock.patch.object(server, "compute", return_value=copy.deepcopy(SCENARIOS[PRIMARY])), \
                mock.patch.object(premium, "generate", side_effect=RuntimeError(CANARY)), \
                contextlib.redirect_stderr(captured):
            status, headers, data = self.post("/api/report", named(BODY, CANARY))
        self.assertRefusedWithoutPDF(status, headers, data, 503, "REPORT_UNAVAILABLE")
        self.assertNotIn(CANARY, captured.getvalue())
        self.assertRegex(captured.getvalue().strip(), r'^\{"event": "REPORT_FAILURE", "type": "RuntimeError"\}$')


class DisplayNameRouting(unittest.TestCase):
    def test_renderer_receives_the_validated_name_and_fixed_palette(self):
        with mock.patch.object(server, "handle_chart", return_value=(200, {"input": {}, "chart": {}})) as chart, \
                mock.patch.object(premium, "generate", return_value=b"%PDF-1.7 ok") as gen:
            status, body = server.handle_report(
                '{"palette": "od10-candidate", "display_name": "  Zoë  "}'.encode(), {}, "/unused")
        self.assertEqual((status, body), (200, b"%PDF-1.7 ok"))
        gen.assert_called_once_with({"input": {}, "chart": {}}, synthetic=False, palette="baseline", display_name="Zoë")
        self.assertEqual(json.loads(chart.call_args.args[0]), {"palette": "od10-candidate"})

    def test_parse_form_and_chart_handler_are_unchanged(self):
        self.assertEqual(server._FORM_KEYS, {"place_id", "birth_date", "birth_time"})
        self.assertEqual(server._OPTIONAL_KEYS, {"utc_offset"})
        import inspect
        for fn in (server._parse_form, server.compute, server.handle_chart):
            self.assertNotIn("display_name", inspect.getsource(fn))


@requires_data
class ServerProcessLogs(unittest.TestCase):
    """The real server process writes nothing about a named request, success or refusal."""

    def test_process_output_has_no_names(self):
        import http.client
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
                for body in (named(BODY, CANARY), named(BODY, HINDI), named(BODY, CANARY + "<script>"),
                             named({"place_id": "nowhere", "birth_date": "x", "birth_time": "y"}, CANARY)):
                    raw = json.dumps(body).encode()
                    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=60)
                    conn.request("POST", "/api/report", raw, {"Host": host, "Origin": f"http://{host}",
                                                              "Content-Type": "application/json",
                                                              "Content-Length": str(len(raw))})
                    conn.getresponse().read()
                    conn.close()
                files = [p for p in Path(cwd).rglob("*")]
            finally:
                proc.terminate()
                out, err = proc.communicate(timeout=10)
        self.assertEqual(files, [], "no files written")
        for text in (out, err):
            for secret in (CANARY, "Zzyzx", HINDI.split()[0], "1990-05-15", "in-new-delhi"):
                self.assertNotIn(secret, text)
        self.assertEqual(err, "")


if __name__ == "__main__":
    unittest.main()
