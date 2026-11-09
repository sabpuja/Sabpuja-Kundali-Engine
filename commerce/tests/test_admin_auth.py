"""KUN-COM-PROD-HARDEN-001 F4: Admin API token renewal (client-credentials grant), deterministic.

The grant endpoint is a fake opener (no network, no real store, synthetic ids and secrets only). The verifier's
401/403 handling is checked against a local fake Admin API.
"""
from contextlib import redirect_stderr
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import io
import json
import re
from pathlib import Path
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.parse

import helpers as h
from sabpuja_commerce import admin_auth, config, shopify

CLIENT_ID = "0123456789abcdef0123456789abcdef"
CLIENT_SECRET = b"synthetic-client-secret-for-tests-only"
V = h.PRODUCT.variant_id


def cc_settings(**kw):
    return h.settings(require_order_verification=True, admin_client_id=CLIENT_ID,
                      admin_client_secret=CLIENT_SECRET, **kw)


class Resp:
    def __init__(self, body, version="2026-10"):
        self._body = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.headers = {"X-Shopify-API-Version": version} if version else {}

    def read(self, n=-1):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeShopify:
    """Grant endpoint plus the shop check, as a urlopen replacement."""

    def __init__(self, lifetime=86399, scope="read_orders,read_products", shop=h.SHOP, version="2026-10",
                 grant_status=200, delay=0.0, clock=None):
        self.lifetime, self.scope, self.shop, self.version = lifetime, scope, shop, version
        self.grant_status, self.delay = grant_status, delay
        self.grants, self.checks, self.issued, self.clock = [], [], [], clock
        self.lock = threading.Lock()

    def __call__(self, req, timeout=None):
        if req.full_url.endswith("/admin/oauth/access_token"):
            if self.delay:
                time.sleep(self.delay)
            with self.lock:
                self.grants.append(dict(urllib.parse.parse_qsl(req.data.decode())))
                n = len(self.grants)
            if self.grant_status != 200:
                raise urllib.error.HTTPError(req.full_url, self.grant_status, "refused", {}, None)
            token = f"shpat_synthetic_token_{n:04d}"
            self.issued.append((token, self.clock() if self.clock else 0.0))
            body = {"access_token": token, "scope": self.scope}
            if self.lifetime is not None:
                body["expires_in"] = self.lifetime
            return Resp(body)
        self.checks.append((req.full_url, req.headers.get("X-shopify-access-token"), json.loads(req.data)))
        return Resp({"data": {"shop": {"myshopifyDomain": self.shop}}}, self.version)


def tokens(fake, clock, **kw):
    return admin_auth.ClientCredentialsTokens(cc_settings(), base_url="https://shop.invalid", clock=clock,
                                              opener=fake, **kw)


class Grant(unittest.TestCase):
    def setUp(self):
        self.clock = h.Clock(1000.0)
        self.fake = FakeShopify()
        self.t = tokens(self.fake, self.clock)

    def test_grant_request_and_shop_check(self):
        self.assertEqual(self.t.token(), "shpat_synthetic_token_0001")
        self.assertEqual(self.fake.grants, [{"grant_type": "client_credentials", "client_id": CLIENT_ID,
                                             "client_secret": CLIENT_SECRET.decode()}])
        url, token, body = self.fake.checks[0]
        self.assertEqual(url, "https://shop.invalid/admin/api/2026-10/graphql.json")
        self.assertEqual(token, "shpat_synthetic_token_0001")
        self.assertIn("myshopifyDomain", body["query"])

    def test_cached_until_renewal_point_then_renewed(self):
        first = self.t.token()
        renew = 86399 - 600                          # 10 % of the lifetime, capped at 600 s
        self.clock.advance(renew - 1)
        self.assertEqual(self.t.token(), first)
        self.assertEqual(len(self.fake.grants), 1)
        self.clock.advance(1)                         # exactly at the renewal point
        self.assertEqual(self.t.token(), "shpat_synthetic_token_0002")
        self.assertEqual(len(self.fake.grants), 2)

    def test_short_lifetime_uses_proportional_margin(self):
        fake = FakeShopify(lifetime=1000)
        t = tokens(fake, self.clock)
        t.token()
        self.clock.advance(899)
        t.token()
        self.assertEqual(len(fake.grants), 1)
        self.clock.advance(1)
        t.token()
        self.assertEqual(len(fake.grants), 2)

    def test_failed_renewal_keeps_valid_token_then_fails_closed_at_expiry(self):
        first = self.t.token()
        self.fake.grant_status = 503
        self.clock.advance(86399 - 600)
        with redirect_stderr(io.StringIO()):
            self.assertEqual(self.t.token(), first)  # renewal failed; old token still inside its lifetime
            self.assertEqual(len(self.fake.grants), 2)
            self.clock.advance(10)
            self.assertEqual(self.t.token(), first)  # inside the back-off: no new request
            self.assertEqual(len(self.fake.grants), 2)
            self.clock.advance(600 - 30 - 10)        # expiry point (30 s safety before Shopify's)
            self.assertIsNone(self.t.token())
        self.fake.grant_status = 200
        self.clock.advance(30)
        self.assertEqual(self.t.token(), "shpat_synthetic_token_0004")   # recovers once Shopify answers

    def test_backoff_bounds_requests_when_shopify_refuses(self):
        self.fake.grant_status = 401
        with redirect_stderr(io.StringIO()):
            for _ in range(50):
                self.assertIsNone(self.t.token())
            self.assertEqual(len(self.fake.grants), 1)
            self.clock.advance(30)
            self.assertIsNone(self.t.token())
        self.assertEqual(len(self.fake.grants), 2)

    def test_unusable_grants_fail_closed(self):
        cases = [dict(lifetime=None), dict(lifetime=True), dict(lifetime=60), dict(lifetime="86399"),
                 dict(scope="read_orders"), dict(scope=""), dict(shop="other-store.myshopify.com"),
                 dict(version="2026-07"), dict(version=None), dict(grant_status=400), dict(grant_status=403),
                 dict(grant_status=500)]
        for case in cases:
            fake = FakeShopify(**case)
            with redirect_stderr(io.StringIO()):
                self.assertIsNone(tokens(fake, self.clock).token(), case)

    def test_bad_token_shapes_refused(self):
        for bad in ("", "short", "has space in it 0123456789", "x" * 600, None, 12345):
            opener = lambda req, timeout=None, b=bad: Resp({"access_token": b, "expires_in": 86399,  # noqa: E731
                                                            "scope": "read_orders,read_products"})
            t = admin_auth.ClientCredentialsTokens(cc_settings(), base_url="https://shop.invalid", clock=self.clock,
                                                   opener=opener)
            with redirect_stderr(io.StringIO()):
                self.assertIsNone(t.token(), bad)

    def test_write_scope_implies_read(self):
        self.assertEqual(admin_auth.granted_scopes("write_orders, read_products"),
                         {"write_orders", "read_orders", "read_products"})
        self.assertIsNotNone(tokens(FakeShopify(scope="write_orders,read_products"), self.clock).token())

    def test_invalidate_only_drops_the_named_token(self):
        first = self.t.token()
        self.t.invalidate("shpat_some_other_token_value")
        self.assertEqual(self.t.token(), first)
        self.t.invalidate(first)
        self.assertEqual(self.t.token(), "shpat_synthetic_token_0002")

    def test_no_secret_or_token_in_logs(self):
        err = io.StringIO()
        with redirect_stderr(err):
            for case in (dict(grant_status=401), dict(scope="read_orders"), dict(shop="x.myshopify.com"),
                         dict(version="2025-10")):
                tokens(FakeShopify(**case), self.clock).token()
        out = err.getvalue()
        self.assertTrue(out)
        for secret in (CLIENT_SECRET.decode(), "shpat_synthetic_token", CLIENT_ID):
            self.assertNotIn(secret, out)
        for line in out.splitlines():
            self.assertLessEqual(set(json.loads(line)), {"event", "status", "missing", "served"})

    def test_repr_hides_client_secret(self):
        self.assertNotIn(CLIENT_SECRET.decode(), repr(cc_settings()))

    def test_restart_needs_no_stored_token(self):
        # The token is never written anywhere: a fresh process (new instance) simply asks again.
        with tempfile.TemporaryDirectory() as d:
            before = set(Path(d).iterdir())
            first = self.t.token()
            again = tokens(self.fake, self.clock)
            self.assertNotEqual(again.token(), first)
            self.assertEqual(set(Path(d).iterdir()), before)
        src = Path(admin_auth.__file__).read_text()
        self.assertIsNone(re.search(r"(?<![\w.])open\(|write_text|write_bytes|os\.replace|tempfile", src))


class Concurrency(unittest.TestCase):
    def test_single_flight_first_acquisition(self):
        fake = FakeShopify(delay=0.2)
        t = admin_auth.ClientCredentialsTokens(cc_settings(), base_url="https://shop.invalid", opener=fake)
        got, threads = [], [threading.Thread(target=lambda: got.append(t.token())) for _ in range(20)]
        for th in threads:
            th.start()
        for th in threads:
            th.join(5)
        self.assertEqual(len(fake.grants), 1)
        self.assertEqual(got, ["shpat_synthetic_token_0001"] * 20)

    def test_callers_keep_old_token_while_renewal_runs(self):
        clock = h.Clock(1000.0)
        fake = FakeShopify()
        t = tokens(fake, clock)
        first = t.token()
        clock.advance(86399 - 600)
        gate, release = threading.Event(), threading.Event()
        orig = fake.__call__

        def slow(req, timeout=None):
            if req.full_url.endswith("access_token"):
                gate.set()
                release.wait(5)
            return orig(req, timeout)
        t._open = slow
        renewer = threading.Thread(target=t.token)
        renewer.start()
        gate.wait(5)
        self.assertEqual(t.token(), first)          # not blocked, no second grant
        release.set()
        renewer.join(5)
        self.assertEqual(len(fake.grants), 2)
        self.assertEqual(t.token(), "shpat_synthetic_token_0002")

    def test_waiters_give_up_when_renewal_hangs_and_no_token_is_valid(self):
        release = threading.Event()
        fake = FakeShopify()

        def hang(req, timeout=None):
            release.wait(5)
            return fake(req, timeout)
        t = admin_auth.ClientCredentialsTokens(cc_settings(), base_url="https://shop.invalid", opener=hang,
                                               wait_limit=0.3)
        first = threading.Thread(target=t.token)
        first.start()
        time.sleep(0.05)
        started = time.monotonic()
        self.assertIsNone(t.token())
        self.assertLess(time.monotonic() - started, 2)
        release.set()
        first.join(5)
        self.assertEqual(len(fake.grants), 1)


# ---- verifier with a renewing token source, against a local fake Admin API ----------------------------------
STATE = {"valid": set(), "status_for_invalid": 401, "seen": [], "is_valid": None}


class FakeAdmin(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        self.rfile.read(int(self.headers["Content-Length"]))
        token = self.headers.get("X-Shopify-Access-Token")
        STATE["seen"].append(token)
        ok = STATE["is_valid"](token) if STATE["is_valid"] else token in STATE["valid"]
        if not ok:
            self.send_response(STATE["status_for_invalid"])
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")
            return
        body = json.dumps({"data": {"order": {
            "id": "gid://shopify/Order/5001", "cancelledAt": None, "displayFinancialStatus": "PAID", "test": False,
            "lineItems": {"nodes": [{"id": "gid://shopify/LineItem/50011", "currentQuantity": 1,
                                     "variant": {"id": f"gid://shopify/ProductVariant/{V}"}}],
                          "pageInfo": {"hasNextPage": False}},
            "refunds": []}}}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Shopify-API-Version", "2026-10")
        self.end_headers()
        self.wfile.write(body)


class Source:
    """Token source whose tokens the fake Admin API may treat as expired."""

    def __init__(self):
        self.n, self.invalidated, self.down = 0, [], False

    def token(self):
        if self.down:
            return None
        self.n += 1
        return f"shpat_synthetic_token_{self.n:04d}"

    def invalidate(self, token):
        self.invalidated.append(token)


class VerifierAuth(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeAdmin)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()
        cls.base = f"http://127.0.0.1:{cls.httpd.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()

    def setUp(self):
        STATE.update(valid=set(), status_for_invalid=401, seen=[], is_valid=None)
        self.src = Source()
        self.v = shopify.GraphQLOrderVerifier(cc_settings(), base_url=self.base, tokens=self.src)

    def test_expired_token_is_replaced_once_and_the_call_succeeds(self):
        STATE["valid"] = {"shpat_synthetic_token_0002"}       # token 1 has expired at Shopify
        self.assertEqual(self.v.lines(5001), {50011: V})
        self.assertEqual(self.src.invalidated, ["shpat_synthetic_token_0001"])
        self.assertEqual(STATE["seen"], ["shpat_synthetic_token_0001", "shpat_synthetic_token_0002"])

    def test_second_401_is_not_retried(self):
        with redirect_stderr(io.StringIO()):
            self.assertIsNone(self.v.lines(5001))
        self.assertEqual(len(STATE["seen"]), 2)

    def test_permission_denied_is_never_retried(self):
        STATE["status_for_invalid"] = 403
        with redirect_stderr(io.StringIO()):
            self.assertIsNone(self.v.lines(5001))
        self.assertEqual(len(STATE["seen"]), 1)
        self.assertEqual(self.src.invalidated, [])

    def test_no_token_means_no_request_and_fail_closed(self):
        self.src.down = True
        with redirect_stderr(io.StringIO()):
            self.assertIsNone(self.v.lines(5001))
        self.assertEqual(STATE["seen"], [])

    def test_generation_fails_closed_without_token_and_recovers(self):
        hh = h.Harness(verifier=self.v)
        hh.paid()
        STATE["valid"] = {"shpat_synthetic_token_0001", "shpat_synthetic_token_0002", "shpat_synthetic_token_0003",
                          "shpat_synthetic_token_0004"}
        cookie = hh.login()
        self.src.down = True
        with redirect_stderr(io.StringIO()):
            self.assertEqual(hh.generate(cookie).status, 503)
        self.assertEqual(hh.store.order_status(h.SHOP, 5001)["remaining"], 4)   # nothing used, nothing revoked
        self.src.down = False
        self.assertEqual(hh.generate(cookie).status, 200)


class BeyondOneDay(unittest.TestCase):
    """Acceptance criterion: valid orders keep verifying past the 24 h token lifetime, no manual step."""

    def test_three_days_of_checks_with_real_renewal(self):
        clock = h.Clock(1000.0)
        fake = FakeShopify(clock=clock)
        t = tokens(fake, clock)
        # Shopify accepts a token only inside its 86 399 s lifetime.
        STATE.update(valid=set(), status_for_invalid=401, seen=[],
                     is_valid=lambda tok: any(tok == i and clock() < at + 86399 for i, at in fake.issued))
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), FakeAdmin)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            v = shopify.GraphQLOrderVerifier(cc_settings(), base_url=f"http://127.0.0.1:{httpd.server_address[1]}",
                                             tokens=t)
            for step in range(72 * 6):                  # a check every 10 minutes for 72 hours
                self.assertEqual(v.lines(5001), {50011: V}, step)
                clock.advance(600)
            self.assertEqual(len(fake.grants), 4)       # about one per 23 h 50 min, not one per call
        finally:
            STATE["is_valid"] = None
            httpd.shutdown()
            httpd.server_close()


class Config(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = Path(self.dir.name)
        (d / "wh").write_bytes(h.SECRET)
        (d / "pp").write_bytes(h.PEPPER)
        (d / "cs").write_bytes(CLIENT_SECRET)
        self.raw = dict(shop_domain=h.SHOP, public_origin=h.ORIGIN, webhook_secret_file=str(d / "wh"),
                        pepper_file=str(d / "pp"), admin_client_id=CLIENT_ID, admin_client_secret_file=str(d / "cs"),
                        db_path=":memory:", products=[dict(product_id=1, variant_id=2, sku="SBK-ESS-EN-1",
                                                           currency="INR", edition=h.PRODUCT.edition)])
        self.d = d

    def tearDown(self):
        self.dir.cleanup()

    def load(self):
        (self.d / "c.json").write_text(json.dumps(self.raw))
        return config.load(str(self.d / "c.json"))

    def test_client_credentials_config_loads(self):
        s = self.load()
        self.assertEqual((s.admin_client_id, s.admin_client_secret), (CLIENT_ID, CLIENT_SECRET))
        self.assertEqual(s.required_scopes, ("read_orders", "read_products"))
        self.assertIsInstance(admin_auth.for_settings(s), admin_auth.ClientCredentialsTokens)
        self.assertNotIn(CLIENT_SECRET.decode(), repr(s))

    def test_refusals(self):
        (self.d / "tk").write_bytes(b"shpat_synthetic")
        for change in (dict(admin_api_token_file=str(self.d / "tk")), dict(admin_client_id="not-a-client-id"),
                       dict(required_scopes=["read_orders"])):
            raw = dict(self.raw)
            self.raw.update(change)
            with self.assertRaises(config.ConfigError, msg=change):
                self.load()
            self.raw = raw
        self.raw.pop("admin_client_secret_file")
        with self.assertRaises(config.ConfigError):
            self.load()


if __name__ == "__main__":
    unittest.main()
