"""Generation quota, duplicates, failed downloads, cross-order access, English-only, failure recovery."""
import threading
import unittest

import helpers as h
from sabpuja_commerce import renderer, store as store_mod


def code(resp):
    return resp.json()["error"]["code"]


class Quota(unittest.TestCase):
    def setUp(self):
        self.h = h.Harness()
        self.h.paid()
        self.cookie = self.h.login()

    def remaining(self):
        return self.h.store.order_status(h.SHOP, 5001)["remaining"]

    def test_pdf_response(self):
        resp = self.h.generate(self.cookie)
        self.assertEqual((resp.status, resp.content_type), (200, "application/pdf"))
        self.assertTrue(resp.body.startswith(b"%PDF-"))
        self.assertIn(("Content-Disposition", 'attachment; filename="Sabpuja-Janam-Kundali.pdf"'), resp.headers)

    def test_initial_plus_three_then_refused(self):
        for expected in (3, 2, 1, 0):
            self.assertEqual(self.h.generate(self.cookie).status, 200)
            self.assertEqual(self.remaining(), expected)
        resp = self.h.generate(self.cookie)
        self.assertEqual((resp.status, code(resp)), (403, "GENERATIONS_USED"))
        self.assertEqual(self.h.render.calls, 4)

    def test_policy_is_configurable(self):
        hh = h.Harness(additional_generations=1)
        hh.paid()
        cookie = hh.login()
        self.assertEqual([hh.generate(cookie).status for _ in range(3)], [200, 200, 403])

    def test_fully_used_order_cannot_be_claimed_again(self):
        for _ in range(4):
            self.h.generate(self.cookie)
        self.h.start()
        self.assertEqual(len(self.h.mail.sent), 1)  # only the original login code

    def test_window_30_days_from_first_delivery(self):
        self.h.generate(self.cookie)
        self.h.clock.advance(30 * 86400 - 200)
        cookie = self.h.login()                     # advances 61 s
        self.assertEqual(self.h.generate(cookie).status, 200)
        self.h.clock.advance(140)                   # session still valid, the window has closed
        resp = self.h.generate(cookie)
        self.assertEqual((resp.status, code(resp)), (403, "ENTITLEMENT_EXPIRED"))

    def test_unclaimed_entitlement_expires(self):
        self.h.clock.advance(180 * 86400)
        resp = self.h.generate(self.cookie)
        self.assertEqual(resp.status, 401)  # session long gone
        self.assertEqual(self.h.start().status, 202)
        self.assertEqual(len(self.h.mail.sent), 1)

    def test_failed_send_does_not_count(self):
        self.assertEqual(self.h.generate(self.cookie, sent=False).status, 200)
        self.assertEqual(self.remaining(), 4)
        self.assertEqual(self.h.generate(self.cookie).status, 200)
        self.assertEqual(self.remaining(), 3)

    def test_input_refusal_does_not_count_and_does_not_echo(self):
        body = dict(h.BIRTH, birth_time="")
        resp = self.h.generate(self.cookie, body)
        self.assertEqual((resp.status, code(resp)), (422, "BIRTH_TIME_REQUIRED"))
        self.assertEqual(self.remaining(), 4)
        self.assertNotIn(h.BIRTH["birth_date"].encode(), resp.body)

    def test_renderer_fault_does_not_count(self):
        self.h.render.fail = RuntimeError("boom with secret 1990-05-17")
        resp = self.h.generate(self.cookie)
        self.assertEqual((resp.status, code(resp)), (503, "REPORT_UNAVAILABLE"))
        self.assertNotIn(b"1990", resp.body)
        self.assertEqual(self.remaining(), 4)
        self.h.render.fail = None
        self.assertEqual(self.h.generate(self.cookie).status, 200)   # recovery

    def test_renderer_unavailable_does_not_count(self):
        self.h.render.fail = renderer.RendererUnavailable("x")
        self.assertEqual(self.h.generate(self.cookie).status, 503)
        self.assertEqual(self.remaining(), 4)

    def test_concurrent_duplicate_generation_refused(self):
        results = {}
        gate = threading.Event()
        release = threading.Event()

        def hold():
            gate.set()
            release.wait(5)
        self.h.render.hook = hold
        t = threading.Thread(target=lambda: results.setdefault("a", self.h.generate(self.cookie)))
        t.start()
        gate.wait(5)
        self.h.render.hook = None
        second = self.h.post("/api/generate", h.BIRTH, cookie=self.cookie)
        release.set()
        t.join(5)
        self.assertEqual((second.status, code(second)), (409, "GENERATION_IN_PROGRESS"))
        self.assertEqual(results["a"].status, 200)
        self.assertEqual(self.remaining(), 3)

    def test_abandoned_reservation_recovers(self):
        resp = self.h.post("/api/generate", h.BIRTH, cookie=self.cookie)  # never sent: transport died
        self.assertEqual(resp.status, 200)
        self.assertEqual(code(self.h.post("/api/generate", h.BIRTH, cookie=self.cookie)), "GENERATION_IN_PROGRESS")
        self.h.clock.advance(store_mod.STALE_RESERVATION_SECONDS)
        self.assertEqual(self.h.generate(self.cookie).status, 200)
        self.assertEqual(self.remaining(), 3)

    def test_refund_during_render_blocks_delivery(self):
        def refund():
            self.h.hook("refunds/create", {"id": 1, "order_id": 5001, "refund_line_items": [{"line_item_id": 50011}]})
        self.h.render.hook = refund
        resp = self.h.generate(self.cookie)
        self.assertEqual((resp.status, code(resp)), (403, "ORDER_NOT_ACTIVE"))
        self.assertEqual(self.h.store.order_status(h.SHOP, 5001)["used"], 0)

    def test_render_busy(self):
        self.assertTrue(self.h.app._render_slots.acquire(blocking=False))
        try:
            resp = self.h.generate(self.cookie)
        finally:
            self.h.app._render_slots.release()
        self.assertEqual((resp.status, code(resp)), (429, "REPORT_BUSY"))
        self.assertEqual(self.remaining(), 4)


class Access(unittest.TestCase):
    def setUp(self):
        self.h = h.Harness()
        self.h.paid(order_id=5001, number=1001)
        self.h.paid(order_id=5002, number=1002, email="second.buyer@example.invalid")

    def test_session_only_uses_its_own_order(self):
        cookie = self.h.login()
        self.h.generate(cookie)
        self.assertEqual(self.h.store.order_status(h.SHOP, 5001)["remaining"], 3)
        self.assertEqual(self.h.store.order_status(h.SHOP, 5002)["remaining"], 4)

    def test_order_number_with_other_buyers_email_fails(self):
        self.h.start(number="1002", email=h.EMAIL)
        self.assertEqual(self.h.mail.sent, [])

    def test_request_cannot_name_another_order(self):
        cookie = self.h.login()
        resp = self.h.generate(cookie, dict(h.BIRTH, order_id="5002"))
        self.assertEqual(resp.status, 400)

    def test_live_check_unavailable_fails_closed(self):
        class Down:
            def lines(self, order_id):
                return None
        hh = h.Harness(verifier=Down())
        hh.paid()
        hh.start()
        resp = hh.verify(hh.last_code())
        self.assertEqual((resp.status, code(resp)), (503, "ORDER_CHECK_UNAVAILABLE"))

    def test_required_verification_without_verifier_fails_closed(self):
        hh = h.Harness(require_order_verification=True, admin_api_token="shpat_synthetic")
        hh.paid()
        hh.start()
        self.assertEqual(code(hh.verify(hh.last_code())), "ORDER_CHECK_UNAVAILABLE")

    def test_reconciliation_revokes_what_shopify_no_longer_allows(self):
        state = {"lines": {50011: h.PRODUCT.variant_id}}

        class Live:
            def lines(self, order_id):
                return state["lines"]
        hh = h.Harness(verifier=Live())
        hh.paid()
        cookie = hh.login()
        self.assertEqual(hh.generate(cookie).status, 200)
        state["lines"] = {}            # refunded in Shopify, webhook never arrived
        resp = hh.generate(cookie)
        self.assertEqual((resp.status, code(resp)), (403, "ORDER_NOT_ACTIVE"))
        self.assertEqual(hh.store.order_status(h.SHOP, 5001)["used"], 1)
        self.assertFalse(hh.store.active_lines(h.SHOP, 5001))

    def test_reconciliation_detects_variant_change(self):
        class Live:
            def lines(self, order_id):
                return {50011: 1}      # same line, different variant
        hh = h.Harness(verifier=Live())
        hh.paid()
        hh.start()
        self.assertEqual(code(hh.verify(hh.last_code())), "ORDER_NOT_ACTIVE")

    def test_reconcile_all_pass(self):
        answers = {5001: {50011: h.PRODUCT.variant_id}, 5002: {}, 5003: None}

        class Live:
            def lines(self, order_id):
                return answers[order_id]
        hh = h.Harness(verifier=Live())
        for oid, num in ((5001, 1001), (5002, 1002), (5003, 1003)):
            hh.paid(order_id=oid, number=num)
        self.assertEqual(hh.app.reconcile_all(), {"ok": 1, "inactive": 1, "unavailable": 1})
        self.assertEqual(hh.store.active_order_ids(h.SHOP), [5001, 5003])


class SendRace(unittest.TestCase):
    """QA P0: a refund or cancel after the PDF is prepared and before (or while) the transport writes it."""

    def setUp(self):
        self.h = h.Harness()
        self.h.paid(qty=2, extra_lines=())
        self.cookie = self.h.login()

    def refund_line(self):
        self.h.hook("refunds/create", {"id": 9, "order_id": 5001, "refund_line_items": [{"line_item_id": 50011}]})

    def status(self):
        return self.h.store.order_status(h.SHOP, 5001)

    def test_refund_after_render_before_send_withholds_pdf(self):
        resp = self.h.post("/api/generate", h.BIRTH, cookie=self.cookie)
        self.assertEqual(resp.status, 200)
        self.refund_line()
        written = []
        final = resp.deliver(lambda r: written.append(r) or True)
        self.assertEqual((final.status, code(final)), (403, "ORDER_NOT_ACTIVE"))
        self.assertEqual([w.status for w in written], [403])          # the PDF body was never written
        row = self.h.store._db.execute("SELECT used, first_delivered_at FROM entitlements").fetchone()
        self.assertEqual((row[0], row[1]), (0, None))

    def test_cancel_after_render_before_send_withholds_pdf(self):
        resp = self.h.post("/api/generate", h.BIRTH, cookie=self.cookie)
        self.h.hook("orders/cancelled", {"id": 5001})
        self.assertEqual(resp.deliver(lambda r: True).status, 403)
        self.assertEqual(self.status()["used"], 0)

    def test_logout_after_render_before_send_withholds_pdf(self):
        resp = self.h.post("/api/generate", h.BIRTH, cookie=self.cookie)
        self.h.post("/api/logout", {}, cookie=self.cookie)
        self.assertEqual(resp.deliver(lambda r: True).status, 403)

    def test_refund_while_sending_is_not_counted(self):
        # The bytes cannot be recalled once handed to the socket; the delivery is simply never recorded.
        final = self.h.generate(self.cookie, during_send=self.refund_line)
        self.assertEqual(final.status, 200)
        row = self.h.store._db.execute("SELECT used, first_delivered_at, status, in_flight_since "
                                       "FROM entitlements").fetchone()
        self.assertEqual(tuple(row), (0, None, "revoked", None))

    def test_mid_stream_disconnect_released_and_retry_counts_once(self):
        self.assertEqual(self.h.generate(self.cookie, sent=False).status, 200)
        self.assertEqual(self.status()["used"], 0)
        self.assertEqual(self.h.generate(self.cookie).status, 200)
        self.assertEqual(self.status()["used"], 1)

    def test_commit_after_revoke_is_refused_at_store_level(self):
        eid, _ = self.h.store.reserve(h.SHOP, 5001)
        self.h.store.revoke_now(h.SHOP, 5001, 0, "refunded")
        self.assertFalse(self.h.store.deliverable(eid))
        self.assertFalse(self.h.store.commit_delivery(eid))
        row = self.h.store._db.execute("SELECT used, first_delivered_at FROM entitlements").fetchone()
        self.assertEqual(tuple(row), (0, None))

    def test_double_commit_counts_once(self):
        eid, _ = self.h.store.reserve(h.SHOP, 5001)
        self.assertTrue(self.h.store.commit_delivery(eid))
        self.assertFalse(self.h.store.commit_delivery(eid))
        self.assertEqual(self.status()["used"], 1)

    def test_over_http_refund_before_write(self):
        # Same path through the real transport: the handler calls Response.deliver.
        from sabpuja_commerce import server
        import http.client
        import threading
        app, refund = self.h.app, self.refund_line

        class RefundAfterHandle:
            """The real App; the refund lands after the PDF response is prepared, before the transport writes."""
            def handle(self, *args):
                resp = app.handle(*args)
                if resp.status == 200:
                    refund()
                return resp
        httpd = server.serve(RefundAfterHandle(), 0)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            conn = http.client.HTTPConnection("127.0.0.1", httpd.server_address[1], timeout=10)
            conn.request("POST", "/api/generate", body=b'{"place_id":"in-jaipur","birth_date":"1990-05-17",'
                         b'"birth_time":"14:30:00"}', headers={"Origin": h.ORIGIN, "Content-Type": "application/json",
                                                               "Cookie": self.cookie})
            r = conn.getresponse()
            body = r.read()
            conn.close()
        finally:
            httpd.shutdown()
            httpd.server_close()
        self.assertEqual(r.status, 403)
        self.assertNotIn(b"%PDF", body)
        self.assertEqual(self.status()["used"], 0)


class EnglishOnly(unittest.TestCase):
    def setUp(self):
        self.h = h.Harness()
        self.h.paid()
        self.cookie = self.h.login()

    def test_hindi_refused_server_side(self):
        for body in (dict(h.BIRTH, report_locale="hi"), dict(h.BIRTH, locale="hi"),
                     dict(h.BIRTH, names="customer"), dict(h.BIRTH, panchanga_names="qa_preview"),
                     dict(h.BIRTH, edition="extended"), dict(h.BIRTH, synthetic=True), dict(h.BIRTH, palette="x")):
            resp = self.h.generate(self.cookie, body)
            self.assertEqual((resp.status, code(resp)), (422, "PAID_EDITION_ENGLISH_ONLY"), body)
        self.assertEqual(self.h.render.calls, 0)
        self.assertEqual(self.h.store.order_status(h.SHOP, 5001)["remaining"], 4)

    def test_explicit_english_accepted(self):
        self.assertEqual(self.h.generate(self.cookie, dict(h.BIRTH, report_locale="en")).status, 200)

    def test_unknown_field_refused(self):
        self.assertEqual(self.h.generate(self.cookie, dict(h.BIRTH, foo="1")).status, 400)

    def test_screen_unit(self):
        with self.assertRaises(renderer.InputRefused):
            renderer.screen([])
        self.assertEqual(renderer.screen(dict(h.BIRTH, report_locale="en")), h.BIRTH)


class EssentialsGate(unittest.TestCase):
    def test_missing_essentials_module_fails_closed(self):
        r = renderer.EssentialsRenderer({}, "", module="report.phase1.essentials_not_installed")
        with self.assertRaises(renderer.RendererUnavailable):
            r(dict(h.BIRTH))

    def test_wrong_edition_fails_closed(self):
        r = renderer.EssentialsRenderer({}, "", module="report.phase1.premium_report")
        with self.assertRaises(renderer.RendererUnavailable):
            r(dict(h.BIRTH))

    def test_config_only_sells_essentials_edition(self):
        from sabpuja_commerce.config import ConfigError, Product
        with self.assertRaises(ConfigError):
            h.settings(products=(Product(1, 1, "X", "INR", "extended-panchanga-m2-vara/1"),))

    def test_config_refuses_weak_secrets(self):
        from sabpuja_commerce.config import ConfigError
        for kw in (dict(webhook_secret=b"short"), dict(pepper=b"short"), dict(shop_domain="example.com"),
                   dict(public_origin="http://kundali.example"), dict(otp_max_attempts=0)):
            with self.assertRaises(ConfigError, msg=kw):
                h.settings(**kw)


if __name__ == "__main__":
    unittest.main()
