"""AdminOrderVerifier against a local fake Admin API (no network, no real store)."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest

import helpers as h
from sabpuja_commerce.shopify import AdminOrderVerifier

ORDERS = {1: {"id": 1, "financial_status": "paid", "cancelled_at": None},
          2: {"id": 2, "financial_status": "refunded", "cancelled_at": None},
          3: {"id": 3, "financial_status": "paid", "cancelled_at": "2027-01-01T00:00:00Z"}}
SEEN = []


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        SEEN.append((self.path, self.headers.get("X-Shopify-Access-Token")))
        oid = int(self.path.split("/orders/")[1].split(".json")[0])
        if oid == 4:
            self.send_response(500)
            self.end_headers()
            return
        body = json.dumps({"order": ORDERS.get(oid, {})}).encode()
        self.send_response(200 if oid in ORDERS else 404)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class Verifier(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        s = h.settings(verify_orders_with_admin_api=True, admin_api_token="shpat_synthetic")
        cls.v = AdminOrderVerifier(s, base_url=f"http://127.0.0.1:{cls.httpd.server_address[1]}")

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def test_paid_ok(self):
        self.assertTrue(self.v.order_ok(1))
        path, token = SEEN[-1]
        self.assertEqual(token, "shpat_synthetic")
        self.assertIn("fields=id,financial_status,cancelled_at", path)

    def test_refunded_cancelled_missing_and_error_fail_closed(self):
        for oid in (2, 3, 4, 99):
            self.assertFalse(self.v.order_ok(oid), oid)

    def test_unreachable_fails_closed(self):
        s = h.settings(verify_orders_with_admin_api=True, admin_api_token="x")
        self.assertFalse(AdminOrderVerifier(s, base_url="http://127.0.0.1:9", timeout=1).order_ok(1))


if __name__ == "__main__":
    unittest.main()
