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

    def test_verifier_fails_closed(self):
        class Down:
            def order_ok(self, order_id):
                return False
        hh = h.Harness(verifier=Down())
        hh.paid()
        hh.start()
        resp = hh.verify(hh.last_code())
        self.assertEqual((resp.status, code(resp)), (403, "ORDER_NOT_ACTIVE"))


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
