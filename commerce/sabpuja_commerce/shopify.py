"""Shopify webhook verification and order handling.

Verification follows Shopify's documented scheme: base64(HMAC-SHA256(secret, raw body)) in
X-Shopify-Hmac-Sha256, compared in constant time against the exact bytes received, before the
body is parsed. Duplicate deliveries are recognised by X-Shopify-Webhook-Id and, independently,
by the (shop, order, line item) uniqueness of entitlements.

No birth data ever reaches Shopify, and nothing from an order except ids, the order number, a
keyed e-mail hash, quantities and the edition is stored.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import hmac
import json
import urllib.request

from .config import Settings
from .store import Store

TOPICS = ("orders/paid", "orders/cancelled", "refunds/create")
MAX_WEBHOOK_BYTES = 256 * 1024


class WebhookRejected(Exception):
    def __init__(self, status: int, code: str):
        super().__init__(code)
        self.status, self.code = status, code


def sign(secret: bytes, body: bytes) -> str:
    return base64.b64encode(hmac.new(secret, body, hashlib.sha256).digest()).decode()


def verify(settings: Settings, headers, body: bytes, now: float) -> tuple[str, str]:
    """Return (topic, webhook id) for an authentic webhook, else raise WebhookRejected."""
    if len(body) > MAX_WEBHOOK_BYTES:
        raise WebhookRejected(413, "WEBHOOK_TOO_LARGE")
    given = headers.get("X-Shopify-Hmac-Sha256") or ""
    expected = sign(settings.webhook_secret, body)
    if not hmac.compare_digest(given.encode(), expected.encode()):
        raise WebhookRejected(401, "WEBHOOK_SIGNATURE_INVALID")
    if (headers.get("X-Shopify-Shop-Domain") or "") != settings.shop_domain:
        raise WebhookRejected(403, "WEBHOOK_SHOP_MISMATCH")
    topic = headers.get("X-Shopify-Topic") or ""
    webhook_id = headers.get("X-Shopify-Webhook-Id") or ""
    if not webhook_id or len(webhook_id) > 128:
        raise WebhookRejected(400, "WEBHOOK_ID_MISSING")
    if settings.webhook_max_age_seconds:
        try:
            sent = datetime.fromisoformat((headers.get("X-Shopify-Triggered-At") or "").replace("Z", "+00:00"))
            age = now - sent.astimezone(timezone.utc).timestamp()
        except ValueError:
            raise WebhookRejected(400, "WEBHOOK_TIMESTAMP_INVALID") from None
        if age > settings.webhook_max_age_seconds or age < -300:
            raise WebhookRejected(400, "WEBHOOK_STALE")
    return topic, webhook_id


def _int(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("id")
    out = int(value)
    if out <= 0:
        raise ValueError("id")
    return out


def _paid_lines(settings: Settings, order: dict) -> list[tuple[int, int, str]]:
    """(line_item_id, units, edition) for every line of a sellable variant, after order checks."""
    if order.get("financial_status") != "paid" or order.get("cancelled_at"):
        return []
    if order.get("test") is True and not settings.allow_test_orders:
        return []
    out = []
    for line in order.get("line_items") or []:
        if not isinstance(line, dict):
            continue
        try:
            product = settings.product_for(_int(line.get("product_id")), _int(line.get("variant_id")),
                                           str(line.get("sku") or ""))
            qty = int(line.get("current_quantity", line.get("quantity", 0)))
            price = Decimal(str(line.get("price", "0")))
        except (ValueError, TypeError, InvalidOperation):
            continue
        if product is None or qty < 1 or price <= 0 or order.get("currency") != product.currency:
            continue
        out.append((_int(line["id"]), qty, product.edition))
    return out


def handle(settings: Settings, store: Store, topic: str, webhook_id: str, body: bytes) -> str:
    """Apply one authentic webhook exactly once. Returns a bounded outcome label."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        raise WebhookRejected(400, "WEBHOOK_BODY_INVALID") from None
    if not isinstance(payload, dict):
        raise WebhookRejected(400, "WEBHOOK_BODY_INVALID")
    shop = settings.shop_domain
    with store.tx() as db:
        if not store.record_webhook(db, webhook_id, topic):
            return "duplicate"
        try:
            outcome = _apply(settings, store, db, shop, topic, payload)
        except (KeyError, ValueError, TypeError):
            outcome = "malformed"
        store.set_webhook_outcome(db, webhook_id, outcome)
        return outcome


def _apply(settings, store, db, shop, topic, payload) -> str:
    if topic == "orders/paid":
        order_id, number = _int(payload["id"]), _int(payload["order_number"])
        email = payload.get("email") or payload.get("contact_email")
        email_hash = store.email_hash(email) if isinstance(email, str) and "@" in email else None
        lines = _paid_lines(settings, payload)
        if not lines:
            return "ignored_not_sellable"
        results = [store.add_entitlement(db, shop=shop, order_id=order_id, order_number=number, line_item_id=lid,
                                         edition=edition, email_hash=email_hash,
                                         capacity=units * settings.generations_per_unit,
                                         claim_days=settings.claim_validity_days,
                                         window_days=settings.generation_window_days)
                   for lid, units, edition in lines]
        if email_hash is None:
            return "created_without_email"
        return "created" if "created" in results else results[0]
    if topic == "orders/cancelled":
        store.revoke(db, shop, _int(payload["id"]), 0, "cancelled")
        return "revoked_cancelled"
    if topic == "refunds/create":
        order_id = _int(payload["order_id"])
        lines = [r for r in payload.get("refund_line_items") or [] if isinstance(r, dict)]
        if not lines:
            # A money-only refund on a digital order: revoke the whole order (seller-protective default).
            store.revoke(db, shop, order_id, 0, "refunded")
        for r in lines:
            store.revoke(db, shop, order_id, _int(r["line_item_id"]), "refunded")
        return "revoked_refunded"
    return "ignored_topic"


class AdminOrderVerifier:
    """Optional re-check at claim/generation time that an order is still paid and not refunded.

    Uses the Admin REST order endpoint with fields limited to status. Not exercised against a live
    store in this change: the offline tests run it against a local fake server.
    """

    def __init__(self, settings: Settings, base_url: str | None = None, timeout: float = 5.0):
        self._s = settings
        self._base = base_url or f"https://{settings.shop_domain}"
        self._timeout = timeout

    def order_ok(self, order_id: int) -> bool:
        url = (f"{self._base}/admin/api/{self._s.admin_api_version}/orders/{int(order_id)}.json"
               "?fields=id,financial_status,cancelled_at")
        req = urllib.request.Request(url, headers={"X-Shopify-Access-Token": self._s.admin_api_token,
                                                   "Accept": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310 - fixed https host
                order = json.loads(resp.read(65536).decode("utf-8")).get("order") or {}
        except (OSError, ValueError):
            return False  # fail closed
        return order.get("financial_status") == "paid" and not order.get("cancelled_at")
