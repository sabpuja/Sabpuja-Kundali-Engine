"""Request handling for the paid fulfilment flow, independent of the HTTP transport.

Flow: Shopify `orders/paid` webhook -> entitlement. Customer enters order number + checkout
e-mail -> one-time code by e-mail -> verified code opens a short HttpOnly session -> private
birth-details form -> PDF rendered in memory and streamed once. The generation counts only after
the PDF bytes were written to the client; refused input, render faults and failed sends do not
consume the quota. Refunds and cancellations revoke the order and its sessions.

Nothing in this module logs, stores or echoes a request body, an e-mail address, a code, a token,
a client address or any birth detail. Security log lines contain bounded labels only.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from importlib import resources
import json
import re
import secrets
import sys
import threading
import time

from . import PAID_LOCALE, mailer, shopify
from .config import Settings
from .renderer import InputRefused, RendererUnavailable, screen
from .store import Store

MAX_BODY_BYTES = 4096
COOKIE = "__Host-sbk_session"
_ORDER = re.compile(r"^#?\s*([0-9]{1,12})$")
_CODE = re.compile(r"^[0-9]{6}$")
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}$")
GENERIC_CLAIM = {"status": "sent_if_matching",
                 "message": "If these details match a paid order, we have e-mailed a 6-digit code."}

SECURITY_HEADERS = {
    "Content-Security-Policy": ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; "
                                "connect-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Cross-Origin-Opener-Policy": "same-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Cache-Control": "no-store",
    "X-Robots-Tag": "noindex, nofollow",
    "Strict-Transport-Security": "max-age=31536000",
}
STATIC = {"/": ("index.html", "text/html; charset=utf-8"),
          "/static/app.js": ("app.js", "text/javascript; charset=utf-8"),
          "/static/app.css": ("app.css", "text/css; charset=utf-8")}


@dataclass
class Response:
    status: int
    body: bytes = b""
    content_type: str = "application/json; charset=utf-8"
    headers: list = field(default_factory=list)
    # Called by the transport with True once every byte was written, False if sending failed.
    after: object = None

    def json(self):
        return json.loads(self.body.decode("utf-8"))


def _json(status: int, payload: dict, headers=None) -> Response:
    return Response(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), headers=headers or [])


def _error(status: int, code: str, message: str, **extra) -> Response:
    return _json(status, {"error": {"code": code, "message": message, **extra}})


def _no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate key")
    return dict(pairs)


def security_log(event: str, status: int, route: str) -> None:
    print(json.dumps({"event": event, "status": status, "route": route, "t": int(time.time())}),
          file=sys.stderr, flush=True)


class RateLimiter:
    """Fixed-window counter per key, in memory (the gateway applies its own per-IP limits too)."""

    def __init__(self, per_minute: int, clock=time.time):
        self._limit, self._clock, self._lock, self._hits = per_minute, clock, threading.Lock(), {}

    def allow(self, key: str) -> bool:
        window = int(self._clock() // 60)
        with self._lock:
            if len(self._hits) > 50_000:
                self._hits = {k: v for k, v in self._hits.items() if v[0] == window}
            win, count = self._hits.get(key, (window, 0))
            if win != window:
                win, count = window, 0
            self._hits[key] = (win, count + 1)
            return count + 1 <= self._limit


class App:
    def __init__(self, settings: Settings, store: Store, mail, render, places: dict,
                 verifier=None, public_places=None, async_mail: bool = True):
        self.s, self.store, self.mail, self.render, self.places = settings, store, mail, render, places
        self.verifier = verifier
        self._public_places = public_places or (lambda: [{"id": k} for k in sorted(places)])
        self._render_slots = threading.BoundedSemaphore(settings.max_concurrent_renders)
        self._claim_limit = RateLimiter(settings.claim_rate_per_minute, store._clock)
        self._async_mail = async_mail
        self._mail_threads: list[threading.Thread] = []

    # ---- transport entry ------------------------------------------------------------------
    def handle(self, method: str, path: str, headers, body: bytes, peer: str) -> Response:
        path = path.split("?", 1)[0]
        try:
            if method in ("GET", "HEAD"):
                return self._get(path, headers)
            if method != "POST":
                return _error(405, "METHOD_NOT_ALLOWED", "method not allowed")
            if path == "/webhooks/shopify":
                return self.webhook(headers, body)
            if not path.startswith("/api/"):
                return _error(404, "NOT_FOUND", "not found")
            if (headers.get("Origin") or "") != self.s.public_origin:
                security_log("ORIGIN_REJECTED", 403, "api")
                return _error(403, "ORIGIN_REJECTED", "request not accepted")
            if not (headers.get("Content-Type") or "").startswith("application/json"):
                return _error(415, "CONTENT_TYPE", "send application/json")
            if len(body) > MAX_BODY_BYTES:
                return _error(413, "BODY_TOO_LARGE", "request too large")
            client = self.client_key(headers, peer)
            routes = {"/api/claim/start": lambda: self.claim_start(body, client),
                      "/api/claim/verify": lambda: self.claim_verify(body, client),
                      "/api/generate": lambda: self.generate(headers, body),
                      "/api/logout": lambda: self.logout(headers)}
            route = routes.get(path)
            return route() if route else _error(404, "NOT_FOUND", "not found")
        except Exception as exc:  # a defect: fixed response, the exception type only in the log
            security_log("INTERNAL_ERROR:" + type(exc).__name__, 500, "any")
            return _error(500, "INTERNAL_ERROR", "unexpected error")

    def client_key(self, headers, peer: str) -> str:
        if peer in self.s.trusted_proxies:
            forwarded = (headers.get("X-Forwarded-For") or "").split(",")[-1].strip()
            if forwarded:
                return forwarded
        return peer

    def _get(self, path: str, headers) -> Response:
        if path in STATIC:
            name, ctype = STATIC[path]
            data = resources.files("sabpuja_commerce").joinpath("static", name).read_bytes()
            data = data.replace(b"{{SOURCE_URL}}", self.s.source_url.encode())
            return Response(200, data, ctype)
        if path == "/api/places":
            return _json(200, {"places": self._public_places()})
        if path == "/api/session":
            order = self._session(headers)
            if order is None:
                return _error(401, "SESSION_REQUIRED", "please verify your order again")
            st = self.store.order_status(*order)
            return _json(200, {"remaining": st["remaining"], "used": st["used"],
                               "window_ends_at": st["window_ends_at"], "language": PAID_LOCALE})
        if path == "/healthz":
            return _json(200, {"ok": True})
        return _error(404, "NOT_FOUND", "not found")

    # ---- webhook --------------------------------------------------------------------------
    def webhook(self, headers, body: bytes) -> Response:
        try:
            topic, webhook_id = shopify.verify(self.s, headers, body, self.store.now())
            if topic not in shopify.TOPICS:
                return _json(200, {"ok": True, "outcome": "ignored_topic"})
            outcome = shopify.handle(self.s, self.store, topic, webhook_id, body)
        except shopify.WebhookRejected as exc:
            security_log(exc.code, exc.status, "webhook")
            return _error(exc.status, exc.code, "webhook not accepted")
        return _json(200, {"ok": True, "outcome": outcome})

    # ---- claim ----------------------------------------------------------------------------
    def _claim_fields(self, body: bytes, want_code: bool):
        try:
            data = json.loads(body.decode("utf-8"), object_pairs_hook=_no_duplicates)
        except (UnicodeDecodeError, ValueError, RecursionError):
            return None
        keys = {"order_number", "email"} | ({"code"} if want_code else set())
        if not isinstance(data, dict) or set(data) != keys or not all(isinstance(data[k], str) for k in keys):
            return None
        order = _ORDER.match(data["order_number"].strip())
        if order is None or not _EMAIL.match(data["email"].strip()):
            return None
        if want_code and not _CODE.match(data["code"].strip()):
            return None
        return int(order.group(1)), data["email"], data.get("code", "").strip()

    def claim_start(self, body: bytes, client: str) -> Response:
        if not self._claim_limit.allow("start:" + client):
            security_log("CLAIM_RATE_LIMITED", 429, "claim_start")
            return _error(429, "RATE_LIMITED", "too many attempts; try again in a minute")
        fields = self._claim_fields(body, want_code=False)
        if fields is None:
            return _error(400, "CLAIM_INVALID", "enter your order number and the e-mail used at checkout")
        number, email, _ = fields
        email_hash = self.store.email_hash(email)
        order_id = self.store.claimable_order(self.s.shop_domain, number, email_hash)
        if order_id is not None and self._may_send(order_id):
            code = f"{secrets.randbelow(10 ** 6):06d}"
            self.store.new_otp(self.s.shop_domain, order_id, email_hash, code, self.s.otp_ttl_seconds)
            msg = mailer.compose(self.s.mail_from, email.strip(), number, code, self.s.otp_ttl_seconds // 60)
            self._send_mail(msg)
        # Same status and body whether or not the order exists, matches or is rate-limited (no enumeration).
        return _json(202, GENERIC_CLAIM)

    def _may_send(self, order_id: int) -> bool:
        now = self.store.now()
        last = self.store.last_otp_at(self.s.shop_domain, order_id)
        if last is not None and now - last < self.s.otp_resend_cooldown_seconds:
            return False
        return self.store.otp_count_since(self.s.shop_domain, order_id, now - 86400) < self.s.otp_max_per_order_per_day

    def _send_mail(self, msg) -> None:
        def run():
            try:
                self.mail.send(msg)
            except Exception as exc:  # noqa: BLE001 - delivery failure is logged as a type only
                security_log("MAIL_FAILED:" + type(exc).__name__, 0, "claim_start")
        if not self._async_mail:
            run()
            return
        t = threading.Thread(target=run, daemon=True)
        self._mail_threads.append(t)
        t.start()

    def flush_mail(self) -> None:
        for t in self._mail_threads:
            t.join(5)
        self._mail_threads.clear()

    def claim_verify(self, body: bytes, client: str) -> Response:
        if not self._claim_limit.allow("verify:" + client):
            security_log("VERIFY_RATE_LIMITED", 429, "claim_verify")
            return _error(429, "RATE_LIMITED", "too many attempts; try again in a minute")
        fields = self._claim_fields(body, want_code=True)
        if fields is None:
            return _error(400, "CLAIM_INVALID", "enter the order number, e-mail and 6-digit code")
        number, email, code = fields
        email_hash = self.store.email_hash(email)
        order_id = self.store.claimable_order(self.s.shop_domain, number, email_hash)
        ok = order_id is not None and self.store.check_otp(self.s.shop_domain, order_id, email_hash, code,
                                                           self.s.otp_max_attempts)
        if not ok:
            security_log("OTP_REJECTED", 401, "claim_verify")
            return _error(401, "CODE_INVALID", "the code is not valid; it may have expired or been used")
        if self.verifier is not None and not self.verifier.order_ok(order_id):
            return _error(403, "ORDER_NOT_ACTIVE", "this order can no longer be fulfilled; contact support")
        token = secrets.token_urlsafe(32)
        self.store.new_session(token, self.s.shop_domain, order_id, self.s.session_ttl_seconds)
        cookie = (f"{COOKIE}={token}; Path=/; Secure; HttpOnly; SameSite=Strict; "
                  f"Max-Age={self.s.session_ttl_seconds}")
        st = self.store.order_status(self.s.shop_domain, order_id)
        return _json(200, {"remaining": st["remaining"], "language": PAID_LOCALE},
                     headers=[("Set-Cookie", cookie)])

    # ---- session --------------------------------------------------------------------------
    @staticmethod
    def _token(headers) -> str | None:
        for part in (headers.get("Cookie") or "").split(";"):
            name, _, value = part.strip().partition("=")
            if name == COOKIE and re.fullmatch(r"[A-Za-z0-9_-]{20,100}", value):
                return value
        return None

    def _session(self, headers):
        token = self._token(headers)
        return None if token is None else self.store.session_order(token)

    def logout(self, headers) -> Response:
        token = self._token(headers)
        if token:
            self.store.end_session(token)
        return Response(204, headers=[("Set-Cookie", f"{COOKIE}=; Path=/; Secure; HttpOnly; SameSite=Strict; Max-Age=0")])

    # ---- generation -----------------------------------------------------------------------
    def generate(self, headers, body: bytes) -> Response:
        order = self._session(headers)
        if order is None:
            return _error(401, "SESSION_REQUIRED", "please verify your order again")
        shop, order_id = order
        try:
            form = json.loads(body.decode("utf-8"), object_pairs_hook=_no_duplicates)
            form = screen(form)
        except (UnicodeDecodeError, ValueError, RecursionError):
            return _error(400, "REQUEST_INVALID", "the request must be one UTF-8 JSON object")
        except InputRefused as exc:
            return _error(exc.status, exc.code, exc.message)
        if self.verifier is not None and not self.verifier.order_ok(order_id):
            return _error(403, "ORDER_NOT_ACTIVE", "this order can no longer be fulfilled; contact support")
        entitlement, reason = self.store.reserve(shop, order_id)
        if entitlement is None:
            status, code, message = {
                "revoked": (403, "ORDER_NOT_ACTIVE", "this order can no longer be fulfilled; contact support"),
                "in_progress": (409, "GENERATION_IN_PROGRESS", "your report is already being prepared"),
                "quota_exhausted": (403, "GENERATIONS_USED", "all report generations for this order are used"),
                "expired": (403, "ENTITLEMENT_EXPIRED", "the generation period for this order has ended"),
            }[reason]
            return _error(status, code, message)
        if not self._render_slots.acquire(blocking=False):
            self.store.release(entitlement)
            return _error(429, "REPORT_BUSY", "try again shortly", retry_after_seconds=5)
        try:
            pdf = self.render(form)
        except InputRefused as exc:
            self.store.release(entitlement)
            return _error(exc.status, exc.code, exc.message, **exc.extra)
        except RendererUnavailable:
            self.store.release(entitlement)
            security_log("RENDERER_UNAVAILABLE", 503, "generate")
            return _error(503, "REPORT_UNAVAILABLE", "the report cannot be prepared right now; nothing was used")
        except Exception as exc:  # noqa: BLE001
            self.store.release(entitlement)
            security_log("REPORT_FAILURE:" + type(exc).__name__, 503, "generate")
            return _error(503, "REPORT_UNAVAILABLE", "the report cannot be prepared right now; nothing was used")
        finally:
            self._render_slots.release()
        if not self.store.still_active(entitlement):
            self.store.release(entitlement)
            return _error(403, "ORDER_NOT_ACTIVE", "this order can no longer be fulfilled; contact support")

        def after(sent: bool) -> None:
            (self.store.commit_delivery if sent else self.store.release)(entitlement)
            if not sent:
                security_log("DELIVERY_FAILED", 0, "generate")

        return Response(200, pdf, "application/pdf",
                        headers=[("Content-Disposition", 'attachment; filename="Sabpuja-Janam-Kundali.pdf"')],
                        after=after)
