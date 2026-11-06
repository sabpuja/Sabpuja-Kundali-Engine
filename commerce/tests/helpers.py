"""Synthetic fixtures for the commerce tests. No real customer, order, e-mail or birth data.

Run from the repository root:
    PYTHONPATH=src:prototype:.:commerce:commerce/tests SABPUJA_TEST_EPHE_PATH=/path/to/ephe \
        python -m unittest discover -s commerce/tests -v
"""
from __future__ import annotations

import json
import os
import re

from sabpuja_commerce import EDITION_REQUIRED, app as app_mod, mailer, renderer, shopify
from sabpuja_commerce.config import Product, Settings
from sabpuja_commerce.store import Store

EPHE = os.environ.get("SABPUJA_TEST_EPHE_PATH")
SHOP = "sabpuja-synthetic-test.myshopify.com"
SECRET = b"synthetic-webhook-secret-for-tests-only"
PEPPER = b"synthetic-pepper-for-tests-only-0123456789abcdef"
ORIGIN = "https://kundali.synthetic.invalid"
PRODUCT = Product(product_id=900001, variant_id=910001, sku="SBK-ESS-EN-1", currency="INR",
                  edition=EDITION_REQUIRED)
EMAIL = "synthetic.buyer@example.invalid"
# Synthetic birth record used only in tests.
BIRTH = {"place_id": "in-jaipur", "birth_date": "1990-05-17", "birth_time": "14:30:00"}


class Clock:
    def __init__(self, t: float = 1_800_000_000.0):
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def settings(**kw) -> Settings:
    base = dict(shop_domain=SHOP, webhook_secret=SECRET, pepper=PEPPER, products=(PRODUCT,), db_path=":memory:",
                public_origin=ORIGIN)
    base.update(kw)
    return Settings(**base).validate()


def order(order_id=5001, number=1001, email=EMAIL, qty=1, status="paid", test=False, currency="INR",
          price="499.00", variant=PRODUCT.variant_id, sku=PRODUCT.sku, line_id=None, extra_lines=()):
    lines = [{"id": line_id or order_id * 10 + 1, "product_id": PRODUCT.product_id, "variant_id": variant, "sku": sku,
              "quantity": qty, "current_quantity": qty, "price": price}] + list(extra_lines)
    return {"id": order_id, "order_number": number, "name": f"#{number}", "email": email,
            "financial_status": status, "cancelled_at": None, "test": test, "currency": currency,
            "line_items": lines}


def webhook_headers(topic: str, body: bytes, webhook_id: str, secret: bytes = SECRET, shop: str = SHOP) -> dict:
    return {"X-Shopify-Hmac-Sha256": shopify.sign(secret, body), "X-Shopify-Shop-Domain": shop,
            "X-Shopify-Topic": topic, "X-Shopify-Webhook-Id": webhook_id,
            "X-Shopify-Triggered-At": "2027-01-15T08:00:00Z"}


class StubRenderer:
    """Stands in for the Essentials pipeline in flow tests; applies the real paid-form screening."""

    def __init__(self):
        self.calls = 0
        self.fail: Exception | None = None
        self.hook = None

    def __call__(self, body: dict) -> bytes:
        self.calls += 1
        body = renderer.screen(body)
        if self.hook:
            self.hook()
        if self.fail is not None:
            raise self.fail
        if body.get("birth_time") == "":
            raise renderer.InputRefused(422, "BIRTH_TIME_REQUIRED", "an exact birth time is required; no time is assumed")
        return b"%PDF-1.7\n% synthetic stub\n%%EOF\n"


class Harness:
    def __init__(self, render=None, verifier=None, **kw):
        self.clock = Clock()
        self.s = settings(**kw)
        self.store = Store(self.s.db_path, self.s.pepper, clock=self.clock)
        self.mail = mailer.MockMailer()
        self.render = render or StubRenderer()
        self.app = app_mod.App(self.s, self.store, self.mail, self.render, {"in-jaipur": {}}, verifier=verifier,
                               async_mail=False)
        self._n = 0

    # webhooks
    def hook(self, topic: str, payload: dict, webhook_id: str | None = None, **hdr):
        body = json.dumps(payload).encode()
        self._n += 1
        headers = webhook_headers(topic, body, webhook_id or f"wh-{self._n}", **hdr)
        return self.app.handle("POST", "/webhooks/shopify", headers, body, "10.0.0.1")

    def paid(self, **kw):
        return self.hook("orders/paid", order(**kw))

    # browser
    def post(self, path: str, payload, cookie: str | None = None, origin: str = ORIGIN, peer: str = "203.0.113.5",
             raw: bytes | None = None):
        headers = {"Origin": origin, "Content-Type": "application/json"}
        if cookie:
            headers["Cookie"] = cookie
        body = raw if raw is not None else json.dumps(payload).encode()
        return self.app.handle("POST", path, headers, body, peer)

    def get(self, path: str, cookie: str | None = None):
        return self.app.handle("GET", path, {"Cookie": cookie} if cookie else {}, b"", "203.0.113.5")

    def last_code(self) -> str:
        return re.search(r"is ([0-9]{6})\.", self.mail.sent[-1].get_content()).group(1)

    def start(self, number="1001", email=EMAIL, **kw):
        return self.post("/api/claim/start", {"order_number": number, "email": email}, **kw)

    def verify(self, code, number="1001", email=EMAIL, **kw):
        return self.post("/api/claim/verify", {"order_number": number, "email": email, "code": code}, **kw)

    def login(self, number="1001", email=EMAIL) -> str:
        assert self.start(number, email).status == 202
        resp = self.verify(self.last_code(), number, email)
        assert resp.status == 200, resp.body
        cookie = dict(resp.headers)["Set-Cookie"].split(";", 1)[0]
        self.clock.advance(61)  # past the resend cooldown for later tests
        return cookie

    def generate(self, cookie, body=None, sent=True):
        resp = self.post("/api/generate", BIRTH if body is None else body, cookie=cookie)
        if resp.after is not None:
            resp.after(sent)
        return resp


def essentials_renderer(places: dict) -> renderer.EssentialsRenderer:
    """The production renderer over the frozen Essentials edition. Release gating is off here only because
    the edition's wording is not owner-approved yet; test_end_to_end separately checks the gate is on by default."""
    return renderer.EssentialsRenderer(places, EPHE, enforce_release=False)
