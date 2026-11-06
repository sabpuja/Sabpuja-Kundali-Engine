"""Real engine, real HTTP on loopback: webhook -> code -> session -> 14-page English PDF.

Needs SABPUJA_TEST_EPHE_PATH (the pinned .se1 directory), like the other engine-backed suites.
Uses the QA-only PipelineRenderer until the frozen Essentials entry point (KUN-RC-ESS-001) lands.
"""
import http.client
import json
import re
import threading
import unittest

import helpers as h
from sabpuja_commerce import app as app_mod, mailer, renderer, server
from sabpuja_commerce.store import Store

needs_data = unittest.skipUnless(h.EPHE, "set SABPUJA_TEST_EPHE_PATH to run engine-backed tests")
DEVANAGARI = re.compile("[ऀ-ॿ]")


def _places():
    from kundali_prototype.places import load_places
    return {k: v for k, v in load_places().items() if k.startswith("in-")}


@needs_data
class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.places = _places()
        cls.render = h.PipelineRenderer(cls.places, h.EPHE)

    def setUp(self):
        self.h = h.Harness(render=self.render)
        self.h.paid()
        self.cookie = self.h.login()

    def pdf_text(self, data):
        import fitz
        doc = fitz.open(stream=data, filetype="pdf")
        return doc, "\n".join(page.get_text() for page in doc)

    def test_english_fourteen_pages_searchable_no_devanagari(self):
        resp = self.h.generate(self.cookie)
        self.assertEqual(resp.status, 200, resp.body[:200])
        doc, text = self.pdf_text(resp.body)
        self.assertEqual(doc.page_count, 14)
        self.assertGreater(len(text), 2000)                 # real text, not images: searchable/screen-readable
        self.assertIsNone(DEVANAGARI.search(text))
        self.assertIn("Swiss Ephemeris", text)
        for page in doc:
            fonts = page.get_fonts()
            self.assertTrue(fonts)
            self.assertTrue(all(f[1] != "n/a" for f in fonts))  # embedded font programs

    def test_display_name_rendered_only_when_given(self):
        resp = self.h.generate(self.cookie, dict(h.BIRTH, display_name="Synthetic Testname"))
        _, text = self.pdf_text(resp.body)
        self.assertIn("Synthetic Testname", text)

    def test_input_refusals_keep_existing_codes_and_do_not_count(self):
        cases = [(dict(h.BIRTH, birth_time=""), 422, "BIRTH_TIME_REQUIRED"),
                 (dict(h.BIRTH, birth_date="1990-02-30"), 422, "BIRTH_DATE_INVALID"),
                 (dict(h.BIRTH, birth_time="25:00"), 422, "BIRTH_TIME_INVALID"),
                 (dict(h.BIRTH, place_id="gb-london"), 422, "PLACE_UNKNOWN"),     # not sold outside India list
                 (dict(h.BIRTH, place_id="nowhere"), 422, "PLACE_UNKNOWN"),
                 ({"place_id": "in-jaipur", "birth_date": "1990-05-17"}, 400, "REQUEST_INVALID"),
                 (dict(h.BIRTH, birth_date="1890-01-01"), 422, None)]
        for body, status, code in cases:
            resp = self.h.generate(self.cookie, body)
            self.assertEqual(resp.status, status, (body, resp.body))
            if code:
                self.assertEqual(resp.json()["error"]["code"], code)
            for value in body.values():
                if len(value) > 4:
                    self.assertNotIn(value.encode(), resp.body)
        self.assertEqual(self.h.store.order_status(h.SHOP, 5001)["remaining"], 4)

    def test_hindi_refused_before_engine(self):
        resp = self.h.generate(self.cookie, dict(h.BIRTH, report_locale="hi"))
        self.assertEqual(resp.json()["error"]["code"], "PAID_EDITION_ENGLISH_ONLY")


@needs_data
class OverHttp(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.places = _places()
        cls.clock = h.Clock()
        cls.s = h.settings(public_origin="https://kundali.synthetic.invalid")
        cls.store = Store(":memory:", cls.s.pepper, clock=cls.clock)
        cls.mail = mailer.MockMailer()
        cls.app = app_mod.App(cls.s, cls.store, cls.mail, h.PipelineRenderer(cls.places, h.EPHE), cls.places,
                              async_mail=False)
        cls.httpd = server.serve(cls.app, 0)
        cls.port = cls.httpd.server_address[1]
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def call(self, method, path, body=b"", headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request(method, path, body=body, headers=headers or {})
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp, data

    def browser(self, path, payload, cookie=None):
        headers = {"Origin": self.s.public_origin, "Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        return self.call("POST", path, json.dumps(payload).encode(), headers)

    def test_full_purchase_flow(self):
        body = json.dumps(h.order(order_id=8001, number=2001)).encode()
        resp, data = self.call("POST", "/webhooks/shopify", body, h.webhook_headers("orders/paid", body, "wh-http-1"))
        self.assertEqual((resp.status, json.loads(data)["outcome"]), (200, "created"))
        resp, _ = self.call("POST", "/webhooks/shopify", body, h.webhook_headers("orders/paid", body, "wh-http-1"))
        self.assertEqual(resp.status, 200)                                        # duplicate is a quiet 200
        resp, _ = self.browser("/api/claim/start", {"order_number": "#2001", "email": h.EMAIL})
        self.assertEqual(resp.status, 202)
        code = re.search(r"is ([0-9]{6})\.", self.mail.sent[-1].get_content()).group(1)
        resp, _ = self.browser("/api/claim/verify", {"order_number": "2001", "email": h.EMAIL, "code": code})
        self.assertEqual(resp.status, 200)
        cookie = resp.getheader("Set-Cookie").split(";")[0]
        resp, pdf = self.browser("/api/generate", h.BIRTH, cookie)
        self.assertEqual((resp.status, resp.getheader("Content-Type")), (200, "application/pdf"))
        self.assertEqual(resp.getheader("Cache-Control"), "no-store")
        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertEqual(self.store.order_status(h.SHOP, 8001)["remaining"], 3)  # counted after the send

    def test_headers_and_limits(self):
        resp, data = self.call("GET", "/")
        self.assertEqual(resp.status, 200)
        for name in ("Content-Security-Policy", "X-Frame-Options", "Strict-Transport-Security", "X-Robots-Tag"):
            self.assertTrue(resp.getheader(name), name)
        self.assertNotIn("Python", resp.getheader("Server") or "")
        resp, _ = self.call("POST", "/api/generate", b"x" * 5000,
                            {"Origin": self.s.public_origin, "Content-Type": "application/json"})
        self.assertEqual(resp.status, 413)
        resp, _ = self.call("POST", "/api/generate", b"", {"Transfer-Encoding": "chunked"})
        self.assertEqual(resp.status, 411)
        resp, _ = self.call("DELETE", "/api/session")
        self.assertEqual(resp.status, 405)
        resp, data = self.call("GET", "/api/places")
        self.assertTrue(all(p["id"].startswith("in-") for p in json.loads(data)["places"]))

    def test_unauthenticated_generate(self):
        resp, data = self.browser("/api/generate", h.BIRTH)
        self.assertEqual(resp.status, 401)
        self.assertNotIn(b"1990", data)


class Isolation(unittest.TestCase):
    def test_only_loopback(self):
        self.assertEqual(server.HOST, "127.0.0.1")

    def test_pipeline_renderer_is_test_only(self):
        import sabpuja_commerce
        import pathlib
        src = "".join(p.read_text() for p in pathlib.Path(sabpuja_commerce.__file__).parent.glob("*.py"))
        self.assertNotIn("generate_extended", src)
        self.assertNotIn("PipelineRenderer", src)
        self.assertIn("report.phase1.essentials", renderer.__doc__ + src)


if __name__ == "__main__":
    unittest.main()
