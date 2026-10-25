"""HTTP layer: routes, headers, request limits, host and origin checks, controlled errors."""
import hashlib
import http.client
import json
import re
import threading
import unittest
from html.parser import HTMLParser
from unittest import mock

from kundali_prototype import server
from kundali_prototype.places import load_places

from support import EPHE, requires_data

GOOD = {"place_id": "in-mumbai", "birth_date": "1990-05-15", "birth_time": "10:30"}


class _Tags(HTMLParser):
    """Collects URLs the page loads by itself and the external links a user can click."""

    def __init__(self):
        super().__init__()
        self.loads, self.links = [], []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("script", "img", "source", "iframe") and "src" in attrs:
            self.loads.append((tag, attrs["src"]))
        elif tag == "link":
            self.loads.append((tag, attrs.get("href", "")))
        elif tag == "a" and not attrs.get("href", "#").startswith("#"):
            self.links.append(attrs)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = server.PrototypeServer(0, EPHE or "", load_places())
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        hdrs = {"Host": f"127.0.0.1:{self.port}"}
        if body is not None:
            hdrs["Content-Type"] = "application/json"
            if not isinstance(body, bytes):
                body = json.dumps(body).encode()
        hdrs.update(headers or {})
        conn.request(method, path, body=body, headers=hdrs)
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp, data


class Routes(Base):
    def test_index_and_static_with_security_headers(self):
        for path, ctype in (("/", "text/html"), ("/static/app.js", "text/javascript"),
                            ("/static/chart.js", "text/javascript"), ("/static/app.css", "text/css"),
                            ("/static/fonts.css", "text/css")):
            with self.subTest(path):
                resp, data = self.request("GET", path)
                self.assertEqual(resp.status, 200)
                self.assertTrue(resp.getheader("Content-Type").startswith(ctype))
                self.assertIn("default-src 'none'", resp.getheader("Content-Security-Policy"))
                self.assertEqual(resp.getheader("X-Content-Type-Options"), "nosniff")
                self.assertEqual(resp.getheader("Cache-Control"), "no-store")
                self.assertEqual(resp.getheader("Referrer-Policy"), "no-referrer")
                self.assertNotIn("Python", resp.getheader("Server"))

    def test_page_loads_nothing_external(self):
        _, html = self.request("GET", "/")
        page = _Tags()
        page.feed(html.decode("utf-8"))
        # Everything the browser loads by itself (scripts, styles, images) is local.
        self.assertTrue(page.loads)
        for tag, url in page.loads:
            with self.subTest(tag=tag, url=url):
                self.assertTrue(url.startswith("/static/"))
        # The only external URL is the user-clicked link to sabpuja.com, opened without opener or referrer.
        self.assertEqual(len(page.links), 2)
        for attrs in page.links:
            self.assertEqual(attrs["href"], "https://sabpuja.com")
            self.assertEqual(attrs["target"], "_blank")
            self.assertEqual(set(attrs["rel"].split()), {"noopener", "noreferrer"})
        rest = html.replace(b'href="https://sabpuja.com"', b"").replace(b">https://sabpuja.com<", b"><")
        for marker in (b"http://", b"https://", b"//cdn", b"googletagmanager", b"analytics", b"fonts.g"):
            self.assertNotIn(marker, rest)
        for css in ("/static/app.css", "/static/fonts.css"):
            _, body = self.request("GET", css)
            self.assertNotIn(b"@import", body)
            self.assertNotIn(b"http", body)
            for url in re.findall(rb"url\(([^)]*)\)", body):
                self.assertTrue(url.startswith(b"/static/fonts/"), url)

    def test_brand_and_font_assets(self):
        # Approved masters from sabpuja/design-system assets/logo/brand-assets.json (2026-10-07 rebrand).
        logos = {"/static/brand/sabpuja-logo-horizontal-color.svg":
                 "2f9acce59b19cac8e1abed203686cb791b82fa97678005189416ccf7e10f7b14",
                 "/static/brand/sabpuja-emblem-color.svg":
                 "c52269c8b475f60c0b1a5d5342bc18380b8dffaf88f960f43e7361db6656a2b8"}
        for path, digest in logos.items():
            with self.subTest(path):
                resp, data = self.request("GET", path)
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.getheader("Content-Type"), "image/svg+xml")
                self.assertEqual(hashlib.sha256(data).hexdigest(), digest)
                self.assertNotIn(b"<script", data)
                self.assertNotIn(b"href", data)
        _, css = self.request("GET", "/static/fonts.css")
        fonts = re.findall(rb"url\((/static/fonts/[a-z0-9-]+\.woff2)\)", css)
        self.assertEqual(len(fonts), 12)
        for path in fonts:
            with self.subTest(path.decode()):
                resp, data = self.request("GET", path.decode())
                self.assertEqual(resp.status, 200)
                self.assertEqual(resp.getheader("Content-Type"), "font/woff2")
                self.assertEqual(data[:4], b"wOF2")
        resp, _ = self.request("GET", "/")
        self.assertIn("font-src 'self';", resp.getheader("Content-Security-Policy"))

    def test_places(self):
        resp, data = self.request("GET", "/api/places")
        places = json.loads(data)["places"]
        self.assertEqual(len(places), 12)
        self.assertNotIn("provenance", places[0])

    def test_unknown_paths_and_traversal(self):
        for path in ("/static/../server.py", "/static/places.json", "/places.json", "/static/", "/api/chart",
                     "/%2e%2e/server.py", "/static/app.js?x=1"):
            with self.subTest(path):
                resp, data = self.request("GET", path)
                self.assertEqual(resp.status, 404)
                self.assertEqual(json.loads(data)["error"]["code"], "NOT_FOUND")

    def test_other_methods(self):
        for method in ("PUT", "DELETE", "PATCH", "OPTIONS"):
            resp, data = self.request(method, "/api/chart")
            self.assertEqual(resp.status, 405)
        resp, _ = self.request("TRACE", "/")
        self.assertEqual(resp.status, 501)


class RequestLimits(Base):
    def test_host_header_must_be_loopback_name(self):
        for host in ("evil.example", f"127.0.0.1.nip.io:{self.port}", "127.0.0.1", f"[::1]:{self.port}"):
            with self.subTest(host):
                resp, data = self.request("GET", "/", headers={"Host": host})
                self.assertEqual(resp.status, 421)
        resp, _ = self.request("GET", "/", headers={"Host": f"localhost:{self.port}"})
        self.assertEqual(resp.status, 200)

    def test_cross_origin_post_refused(self):
        for origin in ("http://evil.example", "null", f"http://127.0.0.1:{self.port + 1}"):
            resp, data = self.request("POST", "/api/chart", GOOD, {"Origin": origin})
            self.assertEqual((resp.status, json.loads(data)["error"]["code"]), (403, "ORIGIN_NOT_ALLOWED"))

    def test_content_type_required(self):
        resp, data = self.request("POST", "/api/chart", GOOD, {"Content-Type": "text/plain"})
        self.assertEqual(resp.status, 415)

    def test_size_limit(self):
        big = json.dumps(dict(GOOD, pad="x" * 5000)).encode()
        resp, data = self.request("POST", "/api/chart", big)
        self.assertEqual((resp.status, json.loads(data)["error"]["code"]), (413, "REQUEST_TOO_LARGE"))

    def test_chunked_refused(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.putrequest("POST", "/api/chart", skip_host=True)
        conn.putheader("Host", f"127.0.0.1:{self.port}")
        conn.putheader("Content-Type", "application/json")
        conn.putheader("Transfer-Encoding", "chunked")
        conn.endheaders()
        conn.send(b"0\r\n\r\n")
        self.assertEqual(conn.getresponse().status, 411)
        conn.close()

    def test_malformed_request_line_gets_fixed_body(self):
        import socket
        with socket.create_connection(("127.0.0.1", self.port), timeout=10) as s:
            s.sendall(b"GET /1987-07-07-secret HTTP/9.9\r\n\r\n")
            reply = s.recv(4096)
        self.assertNotIn(b"1987-07-07", reply)
        self.assertNotIn(b"Traceback", reply)


class ControlledErrors(Base):
    def assertSafe(self, resp, data, status, code):
        self.assertEqual(resp.status, status)
        body = json.loads(data)
        self.assertEqual(body["error"]["code"], code)
        text = data.decode()
        for leak in ("Traceback", "File \"", "/home/", "secret", "1990-05-15", "Mumbai"):
            self.assertNotIn(leak, text)

    def test_unexpected_exception_is_500_without_details(self):
        boom = ValueError("secret 1990-05-15 /home/user/path")
        with mock.patch.object(server, "calculate", side_effect=boom):
            resp, data = self.request("POST", "/api/chart", GOOD)
        self.assertSafe(resp, data, 500, "INTERNAL_ERROR")

    def test_untyped_runtime_error_is_a_500_defect_not_a_resource_fault(self):
        # Gate 3D: typed Swiss faults are 503; an untyped RuntimeError is a defect.
        with mock.patch.object(server, "calculate", side_effect=RuntimeError("Swiss ephemeris files unavailable: secret")):
            resp, data = self.request("POST", "/api/chart", GOOD)
        self.assertSafe(resp, data, 500, "INTERNAL_ERROR")

    def test_typed_swiss_runtime_error_is_503_without_details(self):
        from sabpuja_kundali.engine import ChartComputationError
        fault = ChartComputationError("SWISS_BINDING_MISSING", "secret /home/user/path")
        with mock.patch.object(server, "calculate", side_effect=fault):
            resp, data = self.request("POST", "/api/chart", GOOD)
        self.assertSafe(resp, data, 503, "SWISS_BINDING_MISSING")
        self.assertEqual(json.loads(data)["error"]["category"], "resources")

    def test_invariant_failure_is_500(self):
        with mock.patch.object(server, "calculate", return_value={"chart": "should never be shown"}):
            resp, data = self.request("POST", "/api/chart",
                                      {"place_id": "gb-london", "birth_date": "2020-03-29", "birth_time": "01:30"})
        self.assertEqual(resp.status, 500)
        self.assertNotIn(b"should never be shown", data)

    @requires_data
    def test_valid_request(self):
        resp, data = self.request("POST", "/api/chart", GOOD, {"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(resp.status, 200)
        self.assertEqual(json.loads(data)["chart"]["schema_version"], "0.3.0")  # Gate 3E proposed candidate (owner approval pending)

    @requires_data
    def test_concurrent_requests_match_serial(self):
        bodies = [dict(GOOD, birth_time=f"{h:02d}:15") for h in range(12)]
        serial = [json.loads(self.request("POST", "/api/chart", b)[1]) for b in bodies]
        results = [None] * len(bodies)

        def worker(i):
            results[i] = json.loads(self.request("POST", "/api/chart", bodies[i])[1])
        threads = [threading.Thread(target=worker, args=(i,)) for i in range(len(bodies))]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(results, serial)


if __name__ == "__main__":
    unittest.main()
