"""Order/payment verification, signatures, duplicates, refunds and cancellations (synthetic payloads)."""
import json
import unittest

import helpers as h


class Signature(unittest.TestCase):
    def setUp(self):
        self.h = h.Harness()
        self.body = json.dumps(h.order()).encode()

    def send(self, headers, body=None):
        return self.h.app.handle("POST", "/webhooks/shopify", headers, self.body if body is None else body, "10.0.0.1")

    def test_valid_signature_creates_entitlement(self):
        resp = self.send(h.webhook_headers("orders/paid", self.body, "wh-a"))
        self.assertEqual((resp.status, resp.json()["outcome"]), (200, "created"))
        self.assertEqual(self.h.store.order_status(h.SHOP, 5001)["remaining"], 4)

    def test_wrong_secret_rejected(self):
        resp = self.send(h.webhook_headers("orders/paid", self.body, "wh-a", secret=b"x" * 32))
        self.assertEqual((resp.status, resp.json()["error"]["code"]), (401, "WEBHOOK_SIGNATURE_INVALID"))
        self.assertEqual(self.h.store.order_status(h.SHOP, 5001)["remaining"], 0)

    def test_tampered_body_rejected(self):
        headers = h.webhook_headers("orders/paid", self.body, "wh-a")
        tampered = self.body.replace(b'"quantity": 1', b'"quantity": 9')
        self.assertNotEqual(tampered, self.body)
        self.assertEqual(self.send(headers, tampered).status, 401)

    def test_missing_signature_rejected(self):
        headers = h.webhook_headers("orders/paid", self.body, "wh-a")
        del headers["X-Shopify-Hmac-Sha256"]
        self.assertEqual(self.send(headers).status, 401)

    def test_other_shop_rejected(self):
        resp = self.send(h.webhook_headers("orders/paid", self.body, "wh-a", shop="other.myshopify.com"))
        self.assertEqual(resp.status, 403)

    def test_missing_webhook_id_rejected(self):
        self.assertEqual(self.send(h.webhook_headers("orders/paid", self.body, "")).status, 400)

    def test_oversized_body_rejected_before_parsing(self):
        big = b"{" + b" " * (256 * 1024) + b"}"
        self.assertEqual(self.send(h.webhook_headers("orders/paid", big, "wh-a"), big).status, 413)

    def test_invalid_json_with_valid_signature(self):
        body = b"not json"
        self.assertEqual(self.send(h.webhook_headers("orders/paid", body, "wh-a"), body).status, 400)

    def test_stale_webhook_rejected_when_freshness_enabled(self):
        hh = h.Harness(webhook_max_age_seconds=600)
        hh.clock.t = 1_800_000_000  # 2027-01-15T08:00:00Z is 1_800_000_000 -> exactly fresh
        body = json.dumps(h.order()).encode()
        headers = h.webhook_headers("orders/paid", body, "wh-f")
        self.assertEqual(hh.app.handle("POST", "/webhooks/shopify", headers, body, "x").status, 200)
        hh.clock.advance(601)
        headers = h.webhook_headers("orders/paid", body, "wh-g")
        self.assertEqual(hh.app.handle("POST", "/webhooks/shopify", headers, body, "x").json()["error"]["code"],
                         "WEBHOOK_STALE")

    def test_webhook_does_not_need_browser_origin(self):
        # Server-to-server: authenticated by HMAC, never by Origin or cookies.
        headers = h.webhook_headers("orders/paid", self.body, "wh-a")
        headers["Origin"] = "https://evil.invalid"
        self.assertEqual(self.send(headers).status, 200)


class Orders(unittest.TestCase):
    def setUp(self):
        self.h = h.Harness()

    def remaining(self, order_id=5001):
        return self.h.store.order_status(h.SHOP, order_id)["remaining"]

    def test_duplicate_webhook_id_applied_once(self):
        payload = h.order()
        self.assertEqual(self.h.hook("orders/paid", payload, "wh-same").json()["outcome"], "created")
        self.assertEqual(self.h.hook("orders/paid", payload, "wh-same").json()["outcome"], "duplicate")
        self.assertEqual(self.remaining(), 4)

    def test_same_order_redelivered_with_new_id_is_idempotent(self):
        self.h.paid()
        self.assertEqual(self.h.paid().json()["outcome"], "already_present")
        self.assertEqual(self.remaining(), 4)

    def test_unpaid_statuses_ignored(self):
        for i, status in enumerate(("pending", "authorized", "partially_paid", "refunded", "voided")):
            resp = self.h.paid(order_id=6000 + i, status=status)
            self.assertEqual(resp.json()["outcome"], "ignored_not_sellable", status)
            self.assertEqual(self.remaining(6000 + i), 0)

    def test_cancelled_at_ignored(self):
        payload = h.order()
        payload["cancelled_at"] = "2027-01-15T08:00:00Z"
        self.assertEqual(self.h.hook("orders/paid", payload).json()["outcome"], "ignored_not_sellable")

    def test_wrong_variant_sku_currency_or_price_ignored(self):
        cases = [dict(variant=999), dict(sku="OTHER"), dict(currency="USD"), dict(price="0.00"), dict(price="-1")]
        for i, kw in enumerate(cases):
            resp = self.h.paid(order_id=7000 + i, **kw)
            self.assertEqual(resp.json()["outcome"], "ignored_not_sellable", kw)

    def test_other_products_on_order_are_not_entitlements(self):
        other = {"id": 1, "product_id": 1, "variant_id": 1, "sku": "PUJA-KIT", "quantity": 3, "price": "10"}
        self.h.paid(extra_lines=[other])
        self.assertEqual(self.remaining(), 4)

    def test_test_orders_refused_unless_enabled(self):
        self.assertEqual(self.h.paid(test=True).json()["outcome"], "ignored_not_sellable")
        staging = h.Harness(allow_test_orders=True)
        self.assertEqual(staging.paid(test=True).json()["outcome"], "created")

    def test_quantity_multiplies_generations(self):
        self.h.paid(qty=2)
        self.assertEqual(self.remaining(), 8)

    def test_malformed_ids_do_not_create(self):
        payload = h.order()
        payload["id"] = "abc"
        self.assertEqual(self.h.hook("orders/paid", payload).json()["outcome"], "malformed")
        payload = h.order()
        payload["line_items"][0]["product_id"] = True
        self.assertEqual(self.h.hook("orders/paid", payload).json()["outcome"], "ignored_not_sellable")

    def test_missing_email_creates_unclaimable_entitlement(self):
        self.assertEqual(self.h.paid(email=None).json()["outcome"], "created_without_email")
        self.assertEqual(self.h.start().status, 202)
        self.assertEqual(self.h.mail.sent, [])

    def test_unknown_topic_ignored(self):
        self.assertEqual(self.h.hook("customers/create", {"id": 1}).json()["outcome"], "ignored_topic")

    def test_cancel_revokes_and_ends_sessions(self):
        self.h.paid()
        cookie = self.h.login()
        self.assertEqual(self.h.hook("orders/cancelled", {"id": 5001}).json()["outcome"], "revoked_cancelled")
        self.assertEqual(self.remaining(), 0)
        self.assertEqual(self.h.generate(cookie).status, 401)

    def test_refund_of_line_revokes(self):
        self.h.paid()
        cookie = self.h.login()
        refund = {"id": 1, "order_id": 5001, "refund_line_items": [{"line_item_id": 50011, "quantity": 1}]}
        self.assertEqual(self.h.hook("refunds/create", refund).json()["outcome"], "revoked_refunded")
        resp = self.h.generate(cookie)
        self.assertEqual((resp.status, resp.json()["error"]["code"]), (403, "ORDER_NOT_ACTIVE"))

    def test_money_only_refund_revokes_whole_order(self):
        self.h.paid()
        self.h.hook("refunds/create", {"id": 1, "order_id": 5001, "refund_line_items": []})
        self.assertEqual(self.remaining(), 0)

    def test_refund_before_paid_webhook_blocks_activation(self):
        # Out-of-order delivery: the refund tombstone wins over a late orders/paid.
        self.h.hook("refunds/create", {"id": 1, "order_id": 5001, "refund_line_items": [{"line_item_id": 50011}]})
        self.assertEqual(self.h.paid().json()["outcome"], "revoked_before_paid")
        self.assertEqual(self.remaining(), 0)

    def test_cancel_before_paid_blocks_activation(self):
        self.h.hook("orders/cancelled", {"id": 5001})
        self.assertEqual(self.h.paid().json()["outcome"], "revoked_before_paid")

    def test_revoked_order_cannot_be_claimed(self):
        self.h.paid()
        self.h.hook("orders/cancelled", {"id": 5001})
        self.h.start()
        self.assertEqual(self.h.mail.sent, [])


if __name__ == "__main__":
    unittest.main()
