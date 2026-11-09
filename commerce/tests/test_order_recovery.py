"""Operator recovery of paid orders whose webhook had no e-mail or could not be read, through the GraphQL
recovery query (the only query that reads the protected order e-mail), against a local fake Admin API."""
import contextlib
import io
import json
import unittest

import helpers as h
from sabpuja_commerce import shopify
import test_verifier as tv

V, P = h.PRODUCT.variant_id, h.PRODUCT.product_id
NOW = "2027-01-15T07:00:00Z"            # one hour before the harness clock


def answer(oid=5001, email=h.EMAIL, status="PAID", cancelled=None, test=False, created=NOW, currency="INR",
           lines=((50011, V, 1, "499.00"),), refunded=()):
    return {"data": {"order": {
        "id": f"gid://shopify/Order/{oid}", "name": "#1001", "email": email, "createdAt": created,
        "cancelledAt": cancelled, "displayFinancialStatus": status, "test": test, "currencyCode": currency,
        "lineItems": {"nodes": [{"id": f"gid://shopify/LineItem/{lid}", "sku": h.PRODUCT.sku, "currentQuantity": q,
                                 "variant": {"id": f"gid://shopify/ProductVariant/{vid}",
                                             "product": {"id": f"gid://shopify/Product/{P}"}},
                                 "originalUnitPriceSet": {"shopMoney": {"amount": price, "currencyCode": currency}}}
                                for lid, vid, q, price in lines]},
        "refunds": [{"refundLineItems": {"nodes": [{"lineItem": {"id": f"gid://shopify/LineItem/{lid}"}}
                                                   for lid in refunded]}}]}}}


class Recovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tv.GraphQL.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        self.h = h.Harness()
        self.log = io.StringIO()

    def recover(self, ans, oid=5001, status=200):
        tv.ANSWERS[oid] = (status, ans)
        with contextlib.redirect_stderr(self.log):
            return shopify.recover(self.h.s, self.h.store, self.v.order_for_recovery(oid), oid)

    def test_query_reads_email_and_nothing_else_personal(self):
        self.recover(answer())
        _, _, req = tv.SEEN[-1]
        self.assertIn("email", req["query"])
        for field in ("customer", "phone", "billingAddress", "shippingAddress", "note"):
            self.assertNotIn(field, req["query"])

    def test_paid_without_email_is_recovered_and_claimable(self):
        with contextlib.redirect_stderr(self.log):
            self.h.paid(email=None)
        self.assertEqual(len(self.h.store.open_exceptions()), 1)
        self.assertEqual(self.h.start().status, 202)
        self.assertEqual(self.h.mail.sent, [])                       # nothing to send to yet
        self.assertEqual(self.recover(answer()), "recovered")
        self.assertEqual(self.h.store.open_exceptions(), [])
        self.assertEqual(self.h.store.order_status(h.SHOP, 5001)["remaining"], 4)
        cookie = self.h.login()
        self.assertEqual(self.h.generate(cookie).status, 200)

    def test_malformed_webhook_order_is_recovered_by_id(self):
        body = b'{"id": 5001, "order_number": "not-a-number"'
        headers = h.webhook_headers("orders/paid", body, "wh-bad")
        with contextlib.redirect_stderr(self.log):
            self.assertEqual(self.h.app.handle("POST", "/webhooks/shopify", headers, body, "10.0.0.1").status, 200)
        self.assertEqual(self.recover(answer()), "recovered")
        self.assertEqual(self.h.store.order_status(h.SHOP, 5001)["remaining"], 4)
        self.h.login()

    def test_idempotent_and_never_overwrites_an_existing_email(self):
        self.h.paid()
        self.assertEqual(self.recover(answer(email="other@example.invalid")), "recovered")
        self.assertEqual(self.recover(answer()), "recovered")
        self.assertEqual(self.h.store._db.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0], 1)
        self.h.login()                                               # still the original buyer's e-mail

    def test_still_without_email_keeps_the_exception(self):
        with contextlib.redirect_stderr(self.log):
            self.h.paid(email=None)
        self.assertEqual(self.recover(answer(email=None)), "still_without_email")
        self.assertEqual(len(self.h.store.open_exceptions()), 1)

    def test_refunded_cancelled_unpaid_and_wrong_lines_create_nothing(self):
        for ans in (answer(refunded=(50011,)), answer(lines=((50011, V, 0, "499.00"),)),
                    answer(cancelled=NOW), answer(status="REFUNDED"), answer(status="PENDING"),
                    answer(test=True), answer(currency="USD"), answer(lines=((50011, V + 1, 1, "499.00"),)),
                    answer(lines=((50011, V, 1, "0.00"),))):
            self.assertEqual(self.recover(ans), "not_sellable", ans)
        self.assertEqual(self.h.store._db.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0], 0)

    def test_partial_refund_recovers_only_the_unrefunded_line(self):
        ans = answer(status="PARTIALLY_REFUNDED", lines=((50011, V, 1, "499.00"), (50012, V, 1, "499.00")),
                     refunded=(50012,))
        self.assertEqual(self.recover(ans), "recovered")
        rows = self.h.store._db.execute("SELECT line_item_id FROM entitlements").fetchall()
        self.assertEqual([r[0] for r in rows], [50011])

    def test_tombstone_beats_recovery(self):
        self.h.hook("orders/cancelled", {"id": 5001})
        self.assertEqual(self.recover(answer()), "revoked")
        self.assertEqual(self.h.store.order_status(h.SHOP, 5001)["remaining"], 0)

    def test_deadlines_run_from_the_order_time(self):
        self.assertEqual(self.recover(answer(created="2026-12-26T08:00:00Z")), "recovered")   # 20 days ago
        self.h.clock.advance(10 * 86400 - 60)
        self.assertEqual(self.h.start().status, 202)
        self.h.login()
        self.h.clock.advance(31 * 86400)                              # day 61 > 60-day horizon
        self.assertEqual(self.h.store.reserve(h.SHOP, 5001), (None, "expired"))

    def test_past_claim_window_is_not_recreated(self):
        self.assertEqual(self.recover(answer(created="2026-12-01T08:00:00Z")), "claim_window_over")
        self.assertEqual(self.h.store._db.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0], 0)

    def test_unusable_answers_fail_closed(self):
        for status, ans in ((500, {}), (200, {"errors": [{"message": "access denied: email"}]}), (200, b"x"),
                            (200, {"data": {"order": None}}), (200, {"data": {"order": {"id": "x"}}}),
                            (200, answer(created="yesterday")), (200, answer(created="2027-01-15T07:00:00"))):
            self.assertEqual(self.recover(ans, status=status), "unavailable", (status, ans))
        self.assertEqual(self.recover(answer(oid=5002), oid=5001), "unusable_answer")    # wrong order back
        self.assertEqual(self.h.store._db.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0], 0)

    def test_no_email_in_store_exceptions_or_logs(self):
        with contextlib.redirect_stderr(self.log):
            self.h.paid(email=None)
        self.recover(answer())
        blob = json.dumps([list(map(str, r)) for t in ("entitlements", "order_exceptions")
                           for r in self.h.store._db.execute(f"SELECT * FROM {t}")])
        for value in (h.EMAIL, h.EMAIL.split("@")[0]):
            self.assertNotIn(value, blob)
            self.assertNotIn(value, self.log.getvalue())


if __name__ == "__main__":
    unittest.main()
