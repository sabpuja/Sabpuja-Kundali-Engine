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
import sys
import urllib.error
import urllib.request

from . import admin_auth
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


def _paid_lines(settings: Settings, order: dict) -> tuple[list[tuple[int, int, str, int]], bool]:
    """(line_item_id, units, edition, variant_id) for every sellable line, and whether any line of a
    configured product was rejected on a paid order (a purchase that must not be lost silently)."""
    if order.get("financial_status") != "paid" or order.get("cancelled_at"):
        return [], False
    product_ids = {p.product_id for p in settings.products}
    out, rejected = [], False
    for line in order.get("line_items") or []:
        if not isinstance(line, dict):
            continue
        ours = line.get("product_id") in product_ids and not isinstance(line.get("product_id"), bool)
        try:
            variant = _int(line.get("variant_id"))
            product = settings.product_for(_int(line.get("product_id")), variant, str(line.get("sku") or ""))
            qty = int(line.get("current_quantity", line.get("quantity", 0)))
            price = Decimal(str(line.get("price", "0")))
        except (ValueError, TypeError, InvalidOperation):
            rejected = rejected or ours
            continue
        if product is None or qty < 1 or price <= 0 or order.get("currency") != product.currency:
            rejected = rejected or ours
            continue
        if order.get("test") is True and not settings.allow_test_orders:
            continue  # a test order on the production store is not a lost purchase
        out.append((_int(line["id"]), qty, product.edition, variant))
    return out, rejected


def _exception(store, db, kind, order_id, webhook_id) -> None:
    store.add_exception(db, kind, order_id, webhook_id)
    # Bounded operational alert: kind and ids only, never an e-mail, a name or an order body.
    print(json.dumps({"event": "PAID_ORDER_EXCEPTION", "kind": kind, "order_id": order_id}), file=sys.stderr,
          flush=True)


def handle(settings: Settings, store: Store, topic: str, webhook_id: str, body: bytes) -> str:
    """Apply one authentic webhook exactly once. Returns a bounded outcome label."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError):
        payload = None
    shop = settings.shop_domain
    with store.tx() as db:
        if not store.record_webhook(db, webhook_id, topic):
            return "duplicate"
        if not isinstance(payload, dict):
            outcome = "malformed"
        else:
            try:
                outcome = _apply(settings, store, db, shop, topic, webhook_id, payload)
            except (KeyError, ValueError, TypeError):
                outcome = "malformed"
        if outcome == "malformed" and topic == "orders/paid":
            order_id = payload.get("id") if isinstance(payload, dict) and isinstance(payload.get("id"), int) else None
            _exception(store, db, "malformed_paid_webhook", order_id, webhook_id)
        store.set_webhook_outcome(db, webhook_id, outcome)
        return outcome


def _apply(settings, store, db, shop, topic, webhook_id, payload) -> str:
    if topic == "orders/paid":
        order_id, number = _int(payload["id"]), _int(payload["order_number"])
        email = payload.get("email") or payload.get("contact_email")
        email_hash = store.email_hash(email) if isinstance(email, str) and "@" in email else None
        lines, rejected = _paid_lines(settings, payload)
        if rejected:
            _exception(store, db, "sellable_line_rejected", order_id, webhook_id)
        if not lines:
            return "rejected_sellable_line" if rejected else "ignored_not_sellable"
        results = [store.add_entitlement(db, shop=shop, order_id=order_id, order_number=number, line_item_id=lid,
                                         variant_id=variant, edition=edition, email_hash=email_hash,
                                         capacity=units * settings.generations_per_unit,
                                         claim_days=settings.claim_validity_days,
                                         window_days=settings.generation_window_days,
                                         horizon_days=settings.order_read_horizon_days)
                   for lid, units, edition, variant in lines]
        if email_hash is None and "created" in results:
            _exception(store, db, "paid_without_email", order_id, webhook_id)
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


ORDER_QUERY = """query SabpujaOrderCheck($id: ID!) {
  order(id: $id) {
    id
    cancelledAt
    displayFinancialStatus
    test
    lineItems(first: 50) { nodes { id currentQuantity variant { id } } pageInfo { hasNextPage } }
    refunds(first: 50) { refundLineItems(first: 50) { nodes { lineItem { id } } pageInfo { hasNextPage } } }
  }
}"""
PAID_STATUSES = frozenset({"PAID", "PARTIALLY_REFUNDED"})
PAGE = 50   # first: N used for every list and connection above; a full page may hide more, so it fails closed


def _complete(order: dict) -> bool:
    """True only when no relevant list was cut: the order has <= PAGE lines, < PAGE refunds (Order.refunds is
    a plain list with a `first` limit, so exactly PAGE may be truncated) and every refund's lines fit one page.
    An incomplete answer is unusable: nothing is granted and nothing is revoked from it."""
    if order["lineItems"]["pageInfo"]["hasNextPage"] is not False:
        return False
    if not isinstance(order["refunds"], list) or len(order["refunds"]) >= PAGE:
        return False
    return all(r["refundLineItems"]["pageInfo"]["hasNextPage"] is False for r in order["refunds"])


def _gid_number(value) -> int | None:
    if not isinstance(value, str) or "/" not in value:
        return None
    tail = value.rsplit("/", 1)[1]
    return int(tail) if tail.isdigit() and int(tail) > 0 else None


def order_state(settings: Settings, data: dict) -> dict[int, int] | None:
    """From a GraphQL response: line_item_id -> variant_id of the lines that may still be fulfilled.
    An empty dict means nothing on the order may be fulfilled; None means the answer is unusable."""
    if not isinstance(data, dict) or data.get("errors") or not isinstance(data.get("data"), dict):
        return None
    order = data["data"].get("order")
    if order is None:
        return {}
    if not isinstance(order, dict) or not {"displayFinancialStatus", "lineItems", "refunds"} <= set(order):
        return None  # a partial answer must not revoke anything
    if order.get("cancelledAt") or order.get("displayFinancialStatus") not in PAID_STATUSES:
        return {}
    if order.get("test") is True and not settings.allow_test_orders:
        return {}
    try:
        if not _complete(order):
            return None
        refunded = {_gid_number(n["lineItem"]["id"]) for r in order["refunds"]
                    for n in r["refundLineItems"]["nodes"]}
        active = {}
        for n in order["lineItems"]["nodes"]:
            line, variant = _gid_number(n["id"]), _gid_number((n.get("variant") or {}).get("id"))
            if line and variant and int(n["currentQuantity"]) >= 1 and line not in refunded:
                active[line] = variant
    except (KeyError, TypeError, ValueError):
        return None
    return active


def _log_version_mismatch(served) -> None:
    served = served if isinstance(served, str) and len(served) <= 16 else "absent"
    print(json.dumps({"event": "SHOPIFY_API_VERSION_MISMATCH", "served": served}), file=sys.stderr, flush=True)


class GraphQLOrderVerifier:
    """Live Shopify re-check of one order through the GraphQL Admin API (scopes: read_orders and read_products,
    the latter for lineItem.variant; no customer fields in ORDER_QUERY). Returns the still-fulfillable lines, or
    None when Shopify cannot be asked or answers unusably; callers fail closed on None.

    Tokens come from `tokens` (admin_auth): renewed before expiry, and after a 401 dropped and requested once more
    for exactly one retry. A 403 (permission denied) is never retried."""

    def __init__(self, settings: Settings, base_url: str | None = None, timeout: float = 5.0, tokens=None):
        self._s = settings
        self._url = (base_url or f"https://{settings.shop_domain}") + \
            f"/admin/api/{settings.admin_api_version}/graphql.json"
        self._timeout = timeout
        self._tokens = tokens or admin_auth.for_settings(settings, base_url=base_url, timeout=timeout)

    def _post(self, query: str, order_id: int):
        body = json.dumps({"query": query, "variables": {"id": f"gid://shopify/Order/{int(order_id)}"}}).encode()
        for attempt in (1, 2):
            token = self._tokens.token()
            if token is None:
                print(json.dumps({"event": "SHOPIFY_TOKEN_UNAVAILABLE"}), file=sys.stderr, flush=True)
                return None
            req = urllib.request.Request(self._url, data=body, method="POST", headers={
                "X-Shopify-Access-Token": token, "Content-Type": "application/json", "Accept": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310 - fixed https host
                    served = resp.headers.get("X-Shopify-API-Version")
                    data = json.loads(resp.read(256 * 1024).decode("utf-8"))
            except urllib.error.HTTPError as exc:
                if exc.code == 401 and attempt == 1:
                    self._tokens.invalidate(token)     # expired or revoked: one fresh token, one retry
                    continue
                if exc.code in (401, 403):
                    print(json.dumps({"event": "SHOPIFY_AUTH_REFUSED", "status": exc.code}), file=sys.stderr,
                          flush=True)
                return None
            except (OSError, ValueError):
                return None
            if served != self._s.admin_api_version:
                # Shopify serves a retired or unknown version as the oldest supported one; the queries are only
                # validated for the configured version, so any other answer is unusable.
                _log_version_mismatch(served)
                return None
            return data
        return None

    def lines(self, order_id: int) -> dict[int, int] | None:
        data = self._post(ORDER_QUERY, order_id)
        return None if data is None else order_state(self._s, data)

    def order_for_recovery(self, order_id: int) -> dict | None:
        """The order as an `orders/paid`-shaped payload, for operator recovery only. This is the one query that
        reads a protected customer field (the order e-mail): the app needs Shopify's protected customer data
        access for e-mail. Used only in memory to compute the keyed hash; never stored or logged."""
        data = self._post(RECOVERY_QUERY, order_id)
        return None if data is None else recovery_payload(data)


RECOVERY_QUERY = """query SabpujaOrderRecovery($id: ID!) {
  order(id: $id) {
    id
    number
    email
    createdAt
    cancelledAt
    displayFinancialStatus
    test
    currencyCode
    lineItems(first: 50) {
      nodes {
        id
        sku
        currentQuantity
        variant { id product { id } }
        originalUnitPriceSet { shopMoney { amount currencyCode } }
      }
      pageInfo { hasNextPage }
    }
    refunds(first: 50) { refundLineItems(first: 50) { nodes { lineItem { id } } pageInfo { hasNextPage } } }
  }
}"""


def recovery_payload(data: dict) -> dict | None:
    """Map a recovery answer onto the `orders/paid` payload shape so the same _paid_lines rules apply.
    Refunded or zero-quantity lines get current_quantity 0 and are therefore never re-created."""
    if not isinstance(data, dict) or data.get("errors") or not isinstance(data.get("data"), dict):
        return None
    order = data["data"].get("order")
    if not isinstance(order, dict):
        return None
    try:
        number = order["number"]
        if not _complete(order):
            return None
        refunded = {_gid_number(n["lineItem"]["id"]) for r in order["refunds"] for n in r["refundLineItems"]["nodes"]}
        lines = []
        for n in order["lineItems"]["nodes"]:
            line = _gid_number(n["id"])
            variant = n.get("variant") or {}
            qty = 0 if line in refunded else int(n["currentQuantity"])
            lines.append({"id": line, "product_id": _gid_number((variant.get("product") or {}).get("id")),
                          "variant_id": _gid_number(variant.get("id")), "sku": n.get("sku") or "",
                          "quantity": qty, "current_quantity": qty,
                          "price": n["originalUnitPriceSet"]["shopMoney"]["amount"]})
        status = order["displayFinancialStatus"]
        created = datetime.fromisoformat(str(order["createdAt"]).replace("Z", "+00:00"))
        if created.tzinfo is None:
            return None
    except (KeyError, TypeError, ValueError):
        return None
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        return None
    return {"id": _gid_number(order["id"]), "order_number": number,
            "email": order.get("email"), "cancelled_at": order.get("cancelledAt"), "test": order.get("test"),
            "financial_status": "paid" if status in PAID_STATUSES else str(status).lower(),
            "currency": order.get("currencyCode"), "line_items": lines, "ordered_at": created.timestamp()}


def recover(settings: Settings, store: Store, payload: dict | None, order_id: int) -> str:
    """Operator recovery of one paid order from a live Shopify answer: create any missing entitlement, attach
    the keyed e-mail hash where the webhook had none, and resolve the order's open exceptions once it is
    claimable. Idempotent. Returns a bounded outcome label."""
    if payload is None:
        return "unavailable"
    if payload.get("id") != order_id or not payload.get("order_number"):
        return "unusable_answer"
    if store.now() > payload["ordered_at"] + settings.claim_validity_days * 86400:
        return "claim_window_over"
    shop = settings.shop_domain
    email = payload.get("email")
    email_hash = store.email_hash(email) if isinstance(email, str) and "@" in email else None
    with store.tx() as db:
        lines, _ = _paid_lines(settings, payload)
        if not lines:
            return "not_sellable"
        results = []
        for lid, units, edition, variant in lines:
            results.append(store.add_entitlement(db, shop=shop, order_id=order_id, order_number=payload["order_number"],
                                  line_item_id=lid, variant_id=variant, edition=edition, email_hash=email_hash,
                                  capacity=units * settings.generations_per_unit,
                                  claim_days=settings.claim_validity_days,
                                  window_days=settings.generation_window_days,
                                  horizon_days=settings.order_read_horizon_days,
                                  ordered_at=payload["ordered_at"]))
        if all(r == "revoked_before_paid" for r in results):
            return "revoked"
        if email_hash is None:
            return "still_without_email"
        store.attach_email(db, shop, order_id, email_hash)
        store.resolve_order_exceptions(db, order_id)
    return "recovered"
