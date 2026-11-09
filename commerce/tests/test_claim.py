"""One-time e-mail code: expiry, replay, enumeration, brute force, sessions and browser checks."""
import unittest

import helpers as h
from sabpuja_commerce import app as app_mod


class Enumeration(unittest.TestCase):
    def setUp(self):
        self.h = h.Harness()
        self.h.paid()

    def test_same_response_for_match_mismatch_and_unknown(self):
        responses = [self.h.start(),                                          # match
                     self.h.start(email="someone.else@example.invalid"),      # wrong e-mail
                     self.h.start(number="999999"),                           # unknown order
                     self.h.start()]                                          # cooldown
        self.assertEqual({(r.status, r.body) for r in responses}, {(202, responses[0].body)})
        self.assertEqual(len(self.h.mail.sent), 1)

    def test_code_goes_only_to_checkout_address_and_holds_no_birth_data(self):
        self.h.start(email="  Synthetic.Buyer@EXAMPLE.invalid ")
        msg = self.h.mail.sent[0]
        self.assertEqual(msg["To"], "Synthetic.Buyer@EXAMPLE.invalid")
        text = msg.get_content()
        self.assertIn("#1001", text)
        for value in h.BIRTH.values():
            self.assertNotIn(value, text)

    def test_hash_prefix_and_spaces_in_order_number(self):
        self.assertEqual(self.h.start(number="# 1001").status, 202)
        self.assertEqual(len(self.h.mail.sent), 1)

    def test_malformed_claim_requests(self):
        for payload in ({"order_number": "1001"}, {"order_number": 1001, "email": h.EMAIL},
                        {"order_number": "abc", "email": h.EMAIL}, {"order_number": "1001", "email": "no-at"},
                        {"order_number": "1001", "email": h.EMAIL, "extra": "x"}):
            self.assertEqual(self.h.post("/api/claim/start", payload).status, 400, payload)
        self.assertEqual(self.h.post("/api/claim/start", None, raw=b'{"order_number":"1","order_number":"2",'
                                                                    b'"email":"a@b"}').status, 400)

    def test_mail_failure_is_not_visible(self):
        self.h.mail.fail = True
        self.assertEqual(self.h.start().status, 202)


class Codes(unittest.TestCase):
    def setUp(self):
        self.h = h.Harness()
        self.h.paid()
        self.h.start()
        self.code = self.h.last_code()

    def wrong(self):
        return f"{(int(self.code) + 1) % 10 ** 6:06d}"

    def test_valid_code_opens_session_with_safe_cookie(self):
        resp = self.h.verify(self.code)
        self.assertEqual(resp.status, 200)
        cookie = dict(resp.headers)["Set-Cookie"]
        for flag in ("__Host-sbk_session=", "Path=/", "Secure", "HttpOnly", "SameSite=Strict", "Max-Age=1800"):
            self.assertIn(flag, cookie)
        self.assertNotIn("Domain=", cookie)
        self.assertEqual(resp.json(), {"remaining": 4, "language": "en"})

    def test_code_is_single_use(self):
        self.assertEqual(self.h.verify(self.code).status, 200)
        self.assertEqual(self.h.verify(self.code).status, 401)

    def test_code_expires(self):
        self.h.clock.advance(600)
        self.assertEqual(self.h.verify(self.code).status, 401)

    def test_code_valid_just_before_expiry(self):
        self.h.clock.advance(599)
        self.assertEqual(self.h.verify(self.code).status, 200)

    def test_wrong_email_with_right_code_fails(self):
        self.assertEqual(self.h.verify(self.code, email="other@example.invalid").status, 401)

    def test_brute_force_locks_challenge_even_for_right_code(self):
        for _ in range(5):
            self.assertEqual(self.h.verify(self.wrong()).status, 401)
        self.assertEqual(self.h.verify(self.code).status, 401)

    def test_new_code_replaces_old(self):
        self.h.clock.advance(61)
        self.h.start()
        new = self.h.last_code()
        if new != self.code:
            self.assertEqual(self.h.verify(self.code).status, 401)
        self.assertEqual(self.h.verify(new).status, 200)

    def test_resend_cooldown_and_daily_cap(self):
        self.h.start()                                # inside cooldown: nothing sent
        self.assertEqual(len(self.h.mail.sent), 1)
        for _ in range(10):
            self.h.clock.advance(61)
            self.h.start()
        self.assertEqual(len(self.h.mail.sent), 5)    # otp_max_per_order_per_day
        self.h.clock.advance(86400)
        self.h.start()
        self.assertEqual(len(self.h.mail.sent), 6)

    def test_daily_cap_bounds_total_guesses(self):
        # 5 codes per day x 5 attempts each = at most 25 guesses per order per day out of 10**6.
        guesses = 0
        for _ in range(8):
            self.h.clock.advance(61)
            self.h.start()
            for _ in range(5):
                self.h.verify("000000" if self.h.last_code() != "000000" else "000001")
                guesses += 1
        self.assertEqual(len(self.h.mail.sent), 5)

    def test_code_bound_to_its_order(self):
        self.h.paid(order_id=5002, number=1002)
        self.h.clock.advance(61)
        self.assertEqual(self.h.verify(self.code, number="1002").status, 401)

    def test_per_client_rate_limit(self):
        statuses = [self.h.verify(self.wrong(), peer="198.51.100.9").status for _ in range(12)]
        self.assertEqual(statuses.count(429), 2)
        self.assertEqual(self.h.verify(self.code, peer="198.51.100.10").status, 401)  # challenge locked by now

    def test_rate_limit_window_resets(self):
        for _ in range(10):
            self.h.start(peer="198.51.100.20")
        self.assertEqual(self.h.start(peer="198.51.100.20").status, 429)
        self.h.clock.advance(60)
        self.assertEqual(self.h.start(peer="198.51.100.20").status, 202)

    def test_forwarded_for_trusted_only_from_configured_proxy(self):
        app = self.h.app
        self.assertEqual(app.client_key({"X-Forwarded-For": "1.2.3.4"}, "203.0.113.5"), "203.0.113.5")
        trusted = h.Harness(trusted_proxies=("127.0.0.1",)).app
        self.assertEqual(trusted.client_key({"X-Forwarded-For": "9.9.9.9, 1.2.3.4"}, "127.0.0.1"), "1.2.3.4")


class Sessions(unittest.TestCase):
    def setUp(self):
        self.h = h.Harness()
        self.h.paid()
        self.cookie = self.h.login()

    def test_session_status(self):
        resp = self.h.get("/api/session", self.cookie)
        self.assertEqual((resp.status, resp.json()["remaining"], resp.json()["language"]), (200, 4, "en"))

    def test_session_expires(self):
        self.h.clock.advance(1800)
        self.assertEqual(self.h.get("/api/session", self.cookie).status, 401)
        self.assertEqual(self.h.generate(self.cookie).status, 401)

    def test_forged_and_missing_cookie(self):
        self.assertEqual(self.h.generate(None).status, 401)
        self.assertEqual(self.h.generate("__Host-sbk_session=" + "A" * 43).status, 401)
        self.assertEqual(self.h.generate("__Host-sbk_session=../../etc").status, 401)

    def test_logout_ends_session(self):
        resp = self.h.post("/api/logout", {}, cookie=self.cookie)
        self.assertEqual(resp.status, 204)
        self.assertIn("Max-Age=0", dict(resp.headers)["Set-Cookie"])
        self.assertEqual(self.h.generate(self.cookie).status, 401)

    def test_cross_origin_and_wrong_content_type_refused(self):
        resp = self.h.post("/api/generate", h.BIRTH, cookie=self.cookie, origin="https://evil.invalid")
        self.assertEqual(resp.status, 403)
        resp = self.h.app.handle("POST", "/api/generate", {"Origin": h.ORIGIN, "Content-Type": "text/plain",
                                                           "Cookie": self.cookie}, b"{}", "x")
        self.assertEqual(resp.status, 415)
        self.assertEqual(self.h.store.order_status(h.SHOP, 5001)["remaining"], 4)

    def test_body_limit(self):
        resp = self.h.post("/api/generate", None, cookie=self.cookie, raw=b"{" + b" " * 5000 + b"}")
        self.assertEqual(resp.status, 413)

    def test_unknown_routes_and_methods(self):
        self.assertEqual(self.h.get("/api/nope").status, 404)
        self.assertEqual(self.h.app.handle("PUT", "/api/generate", {}, b"", "x").status, 405)
        self.assertEqual(self.h.post("/admin", {}).status, 404)

    def test_static_pages_carry_source_link(self):
        page = self.h.get("/").body.decode()
        self.assertIn("https://github.com/sabpuja/Sabpuja-Kundali-Engine", page)
        self.assertIn("AGPL-3.0", page)
        self.assertIn('lang="en"', page)

    def test_security_headers_defined(self):
        for name in ("Content-Security-Policy", "Cache-Control", "X-Frame-Options", "Referrer-Policy"):
            self.assertIn(name, app_mod.SECURITY_HEADERS)
        self.assertEqual(app_mod.SECURITY_HEADERS["Cache-Control"], "no-store")


if __name__ == "__main__":
    unittest.main()
