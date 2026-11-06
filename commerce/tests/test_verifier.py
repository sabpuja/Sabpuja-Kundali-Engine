"""GraphQLOrderVerifier against a local fake Admin API (no network, no real store), the 60-day horizon,
and the bounded mail worker under sustained claim traffic."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
import unittest

import helpers as h
from sabpuja_commerce import shopify

V = h.PRODUCT.variant_id


def order(status="PAID", cancelled=None, test=False, lines=((50011, V, 1),), refunded=()):
    return {"data": {"order": {
        "id": "gid://shopify/Order/5001", "cancelledAt": cancelled, "displayFinancialStatus": status, "test": test,
        "lineItems": {"nodes": [{"id": f"gid://shopify/LineItem/{lid}", "currentQuantity": q,
                                 "variant": {"id": f"gid://shopify/ProductVariant/{vid}"}} for lid, vid, q in lines]},
        "refunds": [{"refundLineItems": {"nodes": [{"lineItem": {"id": f"gid://shopify/LineItem/{lid}"}}
                                                   for lid in refunded]}}]}}}


ANSWERS = {}
SEEN = []


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        SEEN.append((self.path, self.headers.get("X-Shopify-Access-Token"), req))
        oid = int(req["variables"]["id"].rsplit("/", 1)[1])
        status, payload = ANSWERS[oid]
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class GraphQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.s = h.settings(require_order_verification=True, admin_api_token="shpat_synthetic")
        cls.v = shopify.GraphQLOrderVerifier(cls.s, base_url=f"http://127.0.0.1:{cls.httpd.server_address[1]}")

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def check(self, status, payload, oid=5001):
        ANSWERS[oid] = (status, payload)
        return self.v.lines(oid)

    def test_paid_order_lines(self):
        self.assertEqual(self.check(200, order()), {50011: V})
        path, token, req = SEEN[-1]
        self.assertEqual(path, "/admin/api/2025-10/graphql.json")
        self.assertEqual(token, "shpat_synthetic")
        self.assertEqual(req["variables"], {"id": "gid://shopify/Order/5001"})
        for field in ("email", "customer", "phone", "billingAddress", "shippingAddress"):
            self.assertNotIn(field, req["query"])            # no protected customer data requested

    def test_partially_refunded_order_keeps_unrefunded_line(self):
        ans = order(status="PARTIALLY_REFUNDED", lines=((50011, V, 1), (50012, V, 1)), refunded=(50012,))
        self.assertEqual(self.check(200, ans), {50011: V})

    def test_refunded_line_zero_quantity_cancelled_unpaid_test_missing(self):
        for ans in (order(refunded=(50011,)), order(lines=((50011, V, 0),)), order(cancelled="2027-01-01T00:00:00Z"),
                    order(status="REFUNDED"), order(status="PENDING"), order(status="VOIDED"), order(test=True),
                    {"data": {"order": None}}):
            self.assertEqual(self.check(200, ans), {}, ans)

    def test_unusable_answers_fail_closed(self):
        for status, ans in ((500, {}), (429, {}), (200, {"errors": [{"message": "Throttled"}]}), (200, b"not json"),
                            (200, {"data": {"order": {"id": "x"}}}), (200, []), (401, {"errors": "bad token"})):
            self.assertIsNone(self.check(status, ans), (status, ans))

    def test_unreachable_fails_closed(self):
        v = shopify.GraphQLOrderVerifier(self.s, base_url="http://127.0.0.1:9", timeout=1)
        self.assertIsNone(v.lines(5001))

    def test_end_to_end_with_fake_shopify(self):
        hh = h.Harness(verifier=self.v)
        hh.paid()
        ANSWERS[5001] = (200, order())
        cookie = hh.login()
        self.assertEqual(hh.generate(cookie).status, 200)
        ANSWERS[5001] = (200, order(status="REFUNDED", refunded=(50011,)))   # webhook missed
        self.assertEqual(hh.generate(cookie).json()["error"]["code"], "ORDER_NOT_ACTIVE")
        self.assertEqual(hh.store.order_status(h.SHOP, 5001)["used"], 1)


class Horizon(unittest.TestCase):
    def test_entitlement_hard_expires_at_order_read_horizon(self):
        # Backstop for the config rule claim + window <= horizon: even a later window is cut at the horizon.
        hh = h.Harness()
        with hh.store.tx() as db:
            hh.store.add_entitlement(db, shop=h.SHOP, order_id=1, order_number=1, line_item_id=1, variant_id=V,
                                     edition=h.PRODUCT.edition, email_hash=None, capacity=4, claim_days=30,
                                     window_days=30, horizon_days=40)
        hh.clock.advance(29 * 86400)
        eid, _ = hh.store.reserve(h.SHOP, 1)
        self.assertTrue(hh.store.commit_delivery(eid))            # first delivery on day 29
        hh.clock.advance(11 * 86400 - 1)
        self.assertEqual(hh.store.order_status(h.SHOP, 1)["remaining"], 3)
        hh.clock.advance(1)                                       # day 40: cut at the horizon, not day 59
        self.assertEqual(hh.store.order_status(h.SHOP, 1)["remaining"], 0)
        self.assertEqual(hh.store.reserve(h.SHOP, 1), (None, "expired"))
        self.assertEqual(hh.store.active_order_ids(h.SHOP), [])

    def test_default_windows_fit_the_60_day_horizon(self):
        s = h.settings()
        self.assertLessEqual(s.claim_validity_days + s.generation_window_days, s.order_read_horizon_days)
        self.assertEqual(s.order_read_horizon_days, 60)


class MailWorker(unittest.TestCase):
    def test_sustained_claims_use_one_worker_and_bounded_queue(self):
        hh = h.Harness(mail_queue_size=5, claim_rate_per_minute=10_000, otp_max_per_order_per_day=10_000,
                       otp_resend_cooldown_seconds=0)
        hh.app._async_mail = True
        gate = threading.Event()
        sent = []
        hh.mail.send = lambda msg: (gate.wait(5), sent.append(msg))
        for i in range(300):
            hh.paid(order_id=6000 + i, number=3000 + i)
        before = threading.active_count()
        for i in range(300):
            self.assertEqual(hh.start(number=str(3000 + i)).status, 202)
        self.assertLessEqual(threading.active_count(), before + 1)    # one worker, not one thread per mail
        self.assertLessEqual(hh.app._mail_queue.qsize(), 5)
        gate.set()
        hh.app.flush_mail()
        self.assertLessEqual(len(sent), 6)                            # the rest were dropped, not queued forever
        self.assertGreaterEqual(len(sent), 1)
        # After the backlog clears, mail flows again.
        count = len(sent)
        hh.clock.advance(1)
        hh.start(number="3000")
        hh.app.flush_mail()
        self.assertEqual(len(sent), count + 1)


if __name__ == "__main__":
    unittest.main()
