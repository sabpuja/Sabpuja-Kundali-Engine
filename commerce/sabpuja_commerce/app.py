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
import html
import json
import queue
import re
import secrets
import sys
import threading
import time

from . import PAID_LOCALE, funnel as funnel_mod, leads as leads_mod, mailer, preview as preview_mod, shopify
from .config import Settings
from .renderer import InputRefused, RendererUnavailable, screen
from .store import Store

MAX_BODY_BYTES = 4096
COOKIE = "__Host-sbk_session"
_ORDER = re.compile(r"^#?\s*([0-9]{1,12})$")
# Shopify order id from the Thank you page link (URL fragment, never sent to a server by the browser).
_ORDER_REF = re.compile(r"^[0-9]{1,20}$")
_CODE = re.compile(r"^[0-9]{6}$")
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}$")
GENERIC_CLAIM = {"status": "sent_if_matching",
                 "message": "If these details match a paid order, we have e-mailed a 6-digit code."}


def generic_claim(settings: Settings) -> dict:
    """The one claim/start reply. Only configuration values are added (identical for every input), so the page
    can explain expiry and resend timing without revealing whether the order exists."""
    return GENERIC_CLAIM | {"code_ttl_minutes": settings.otp_ttl_seconds // 60,
                            "resend_after_seconds": settings.otp_resend_cooldown_seconds}

SECURITY_HEADERS = {
    "Content-Security-Policy": ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self'; font-src 'self'; "
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
# Free preview page (served only while preview_enabled) and the marketing preferences page (lead capture only).
PREVIEW_STATIC = {"/kundali": ("preview.html", "text/html; charset=utf-8"),
                  "/static/preview.js": ("preview.js", "text/javascript; charset=utf-8"),
                  "/static/preview.css": ("preview.css", "text/css; charset=utf-8")}
LEADS_STATIC = {"/marketing": ("marketing.html", "text/html; charset=utf-8"),
                "/static/marketing.js": ("marketing.js", "text/javascript; charset=utf-8")}
PREVIEW_DATE_MIN = "1970-01-01"   # SCI-03 RG-HIST Option B: earlier local dates are refused by the engine
# Sabpuja Foundations fonts and logo, served from the same files the preview uses (no copies, no font service).
SHARED_STATIC = {
    "/static/fonts/" + name: ("fonts/" + name, "font/woff2") for name in (
        "inter-latin-400-normal.woff2", "inter-latin-500-normal.woff2", "inter-latin-600-normal.woff2",
        "poppins-latin-600-normal.woff2", "poppins-devanagari-400-normal.woff2",
        "poppins-devanagari-600-normal.woff2")
} | {"/static/brand/sabpuja-logo-horizontal-color.svg": ("brand/sabpuja-logo-horizontal-color.svg",
                                                         "image/svg+xml")}


@dataclass
class Response:
    status: int
    body: bytes = b""
    content_type: str = "application/json; charset=utf-8"
    headers: list = field(default_factory=list)
    # Called by the transport immediately before writing; False means do not send this body.
    before: object = None
    # Called by the transport with True once every byte was written, False if sending failed or was withheld.
    after: object = None

    def json(self):
        return json.loads(self.body.decode("utf-8"))

    def deliver(self, write) -> "Response":
        """The one send path for every transport: re-check eligibility at send time, write, then settle.
        `write(response) -> bool` must return True only after every byte was handed to the client socket.
        A refund that arrives after this check cannot recall bytes already sent; it only stops them being
        counted (commit_delivery) and stops every later generation."""
        if self.before is not None and not self.before():
            withheld = _error(403, "ORDER_NOT_ACTIVE", "this order can no longer be fulfilled; contact support")
            write(withheld)
            if self.after is not None:
                self.after(False)
            return withheld
        sent = write(self)
        if self.after is not None:
            self.after(sent)
        return self


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
                 verifier=None, public_places=None, async_mail: bool = True, preview=None, funnel=None, leads=None):
        self.s, self.store, self.mail, self.render, self.places = settings, store, mail, render, places
        self.verifier = verifier
        self._public_places = public_places or (lambda: [{"id": k} for k in sorted(places)])
        self._render_slots = threading.BoundedSemaphore(settings.max_concurrent_renders)
        self._claim_limit = RateLimiter(settings.claim_rate_per_minute, store._clock)
        self._async_mail = async_mail
        self._mail_queue: queue.Queue = queue.Queue(maxsize=settings.mail_queue_size)
        self._mail_worker: threading.Thread | None = None
        self._mail_lock = threading.Lock()
        # Free preview, funnel and leads (KUN-FREEMIUM-PREVIEW-001). None of them can reach an entitlement,
        # a session, the renderer or the paid route; they share only the transport, the Origin check and the mailer.
        self.preview = preview if settings.preview_enabled else None
        self.funnel = funnel or funnel_mod.NullFunnel()
        self.leads = leads if (settings.lead_capture_enabled and self.preview is not None) else None
        clock = store._clock
        self._preview_slots = threading.BoundedSemaphore(settings.max_concurrent_previews)
        self._preview_minute = preview_mod.WindowLimiter(settings.preview_rate_per_minute, 60, clock)
        self._preview_hour = preview_mod.WindowLimiter(settings.preview_rate_per_hour, 3600, clock)
        self._preview_global = preview_mod.WindowLimiter(settings.preview_global_per_minute, 60, clock)
        self._beacon_limit = preview_mod.WindowLimiter(settings.beacon_rate_per_minute, 60, clock)
        self._lead_limit = preview_mod.WindowLimiter(settings.claim_rate_per_minute, 60, clock)

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
                      "/api/logout": lambda: self.logout(headers),
                      "/api/preview": lambda: self.preview_chart(body, client),
                      "/api/funnel": lambda: self.funnel_event(body, client),
                      "/api/leads/subscribe": lambda: self.lead_subscribe(body, client),
                      "/api/leads/link": lambda: self.lead_link(body, client),
                      "/api/leads/status": lambda: self.lead_token_action(body, client, "status"),
                      "/api/leads/confirm": lambda: self.lead_token_action(body, client, "confirm"),
                      "/api/leads/withdraw": lambda: self.lead_token_action(body, client, "withdraw"),
                      "/api/leads/delete": lambda: self.lead_token_action(body, client, "delete")}
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
        pages = dict(STATIC)
        if self.preview is not None:
            pages |= PREVIEW_STATIC
        if self.leads is not None:
            pages |= LEADS_STATIC
        if path == "/api/preview/config":
            return self.preview_config()
        if path in pages:
            name, ctype = pages[path]
            data = resources.files("sabpuja_commerce").joinpath("static", name).read_bytes()
            data = data.replace(b"{{SOURCE_URL}}", self.s.source_url.encode())
            if name == "index.html":
                data = data.replace(b"{{MAIL_FROM}}", html.escape(self.s.mail_from).encode())
            return Response(200, data, ctype)
        if path in SHARED_STATIC:
            name, ctype = SHARED_STATIC[path]
            try:
                data = resources.files("kundali_prototype").joinpath("static", name).read_bytes()
            except (ModuleNotFoundError, FileNotFoundError):
                return _error(404, "NOT_FOUND", "not found")
            return Response(200, data, ctype, headers=[("Cache-Control", "public, max-age=86400")])
        if path == "/api/places":
            return _json(200, {"places": self._public_places()})
        if path == "/api/session":
            order = self._session(headers)
            if order is None:
                return _error(401, "SESSION_REQUIRED", "please verify your order again")
            st = self.store.order_status(*order)
            return _json(200, {"remaining": st["remaining"], "used": st["used"],
                               "window_ends_at": st["window_ends_at"], "window_days": st["window_days"],
                               "order_number": st["order_number"], "language": PAID_LOCALE})
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
        if outcome in ("created", "created_without_email"):
            # Aggregate only: Shopify orders carry no link to a preview, so this is total paid orders.
            self.funnel.count("paid_orders_all_sources")
        return _json(200, {"ok": True, "outcome": outcome})

    # ---- claim ----------------------------------------------------------------------------
    def _claim_fields(self, body: bytes, want_code: bool):
        """(order_number, order_id, email, code) or None. The order is named by exactly one of `order_number`
        (what the buyer types, "#1001") or `order_ref` (the Shopify order id the Thank you page link carries)."""
        try:
            data = json.loads(body.decode("utf-8"), object_pairs_hook=_no_duplicates)
        except (UnicodeDecodeError, ValueError, RecursionError):
            return None
        if not isinstance(data, dict):
            return None
        by = "order_ref" if "order_ref" in data else "order_number"
        keys = {by, "email"} | ({"code"} if want_code else set())
        if set(data) != keys or not all(isinstance(data[k], str) for k in keys):
            return None
        number = order_id = None
        if by == "order_number":
            match = _ORDER.match(data["order_number"].strip())
            if match is None:
                return None
            number = int(match.group(1))
        else:
            if not _ORDER_REF.match(data["order_ref"].strip()):
                return None
            order_id = int(data["order_ref"].strip())
        if not _EMAIL.match(data["email"].strip()):
            return None
        if want_code and not _CODE.match(data["code"].strip()):
            return None
        return number, order_id, data["email"], data.get("code", "").strip()

    def claim_start(self, body: bytes, client: str) -> Response:
        if not self._claim_limit.allow("start:" + client):
            security_log("CLAIM_RATE_LIMITED", 429, "claim_start")
            return _error(429, "RATE_LIMITED", "too many attempts; try again in a minute")
        fields = self._claim_fields(body, want_code=False)
        if fields is None:
            return _error(400, "CLAIM_INVALID", "enter your order number and the e-mail used at checkout")
        number, order_ref, email, _ = fields
        email_hash = self.store.email_hash(email)
        found = self.store.claimable(self.s.shop_domain, email_hash, order_number=number, order_id=order_ref)
        order_id, number = found if found is not None else (None, None)
        if order_id is not None and self._may_send(order_id):
            code = f"{secrets.randbelow(10 ** 6):06d}"
            self.store.new_otp(self.s.shop_domain, order_id, email_hash, code, self.s.otp_ttl_seconds)
            msg = mailer.compose(self.s.mail_from, email.strip(), number, code, self.s.otp_ttl_seconds // 60)
            self._send_mail(msg)
        # Same status and body whether or not the order exists, matches or is rate-limited (no enumeration).
        return _json(202, generic_claim(self.s))

    def _may_send(self, order_id: int) -> bool:
        now = self.store.now()
        last = self.store.last_otp_at(self.s.shop_domain, order_id)
        if last is not None and now - last < self.s.otp_resend_cooldown_seconds:
            return False
        return self.store.otp_count_since(self.s.shop_domain, order_id, now - 86400) < self.s.otp_max_per_order_per_day

    def _deliver_mail(self, msg) -> None:
        try:
            self.mail.send(msg)
        except Exception as exc:  # noqa: BLE001 - delivery failure is logged as a type only
            security_log("MAIL_FAILED:" + type(exc).__name__, 0, "claim_start")

    def _mail_loop(self) -> None:
        while True:
            msg = self._mail_queue.get()
            try:
                self._deliver_mail(msg)
            finally:
                self._mail_queue.task_done()

    def _send_mail(self, msg) -> None:
        """One bounded queue and one long-lived worker thread: memory and threads stay constant under load.
        A full queue drops the message (the buyer can ask again after the cooldown) and logs a bounded event."""
        if not self._async_mail:
            self._deliver_mail(msg)
            return
        with self._mail_lock:
            if self._mail_worker is None or not self._mail_worker.is_alive():
                self._mail_worker = threading.Thread(target=self._mail_loop, name="sabpuja-mail", daemon=True)
                self._mail_worker.start()
        try:
            self._mail_queue.put_nowait(msg)
        except queue.Full:
            security_log("MAIL_QUEUE_FULL", 503, "claim_start")

    def flush_mail(self) -> None:
        self._mail_queue.join()

    # ---- live order re-check ----------------------------------------------------------------
    def reconcile(self, order_id: int) -> str:
        """Re-check one order with Shopify and revoke whatever Shopify no longer allows.

        Returns "ok" (something is still fulfillable), "inactive" (nothing is) or "unavailable" (Shopify could
        not be asked; the caller fails closed). With verification disabled (offline QA only) returns "ok"."""
        if self.verifier is None:
            return "unavailable" if self.s.require_order_verification else "ok"
        remote = self.verifier.lines(order_id)
        if remote is None:
            security_log("ORDER_CHECK_UNAVAILABLE", 503, "reconcile")
            return "unavailable"
        shop = self.s.shop_domain
        local = self.store.active_lines(shop, order_id)
        for line_id, variant in local.items():
            if remote.get(line_id) != variant:
                self.store.revoke_now(shop, order_id, line_id, "reconciled")
                security_log("ENTITLEMENT_RECONCILED", 0, "reconcile")
        return "ok" if self.store.active_lines(shop, order_id) else "inactive"

    def reconcile_all(self) -> dict:
        """One reconciliation pass over every active entitlement (for an operator-run job, not a daemon)."""
        out = {"ok": 0, "inactive": 0, "unavailable": 0}
        for order_id in self.store.active_order_ids(self.s.shop_domain):
            out[self.reconcile(order_id)] += 1
        return out

    def claim_verify(self, body: bytes, client: str) -> Response:
        if not self._claim_limit.allow("verify:" + client):
            security_log("VERIFY_RATE_LIMITED", 429, "claim_verify")
            return _error(429, "RATE_LIMITED", "too many attempts; try again in a minute")
        fields = self._claim_fields(body, want_code=True)
        if fields is None:
            return _error(400, "CLAIM_INVALID", "enter the order number, e-mail and 6-digit code")
        number, order_ref, email, code = fields
        email_hash = self.store.email_hash(email)
        found = self.store.claimable(self.s.shop_domain, email_hash, order_number=number, order_id=order_ref)
        order_id = found[0] if found is not None else None
        ok = order_id is not None and self.store.check_otp(self.s.shop_domain, order_id, email_hash, code,
                                                           self.s.otp_max_attempts)
        if not ok:
            security_log("OTP_REJECTED", 401, "claim_verify")
            return _error(401, "CODE_INVALID", "the code is not valid; it may have expired or been used")
        check = self.reconcile(order_id)
        if check == "unavailable":
            return _error(503, "ORDER_CHECK_UNAVAILABLE", "we cannot confirm your order right now; try again shortly")
        if check == "inactive":
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
        check = self.reconcile(order_id)
        if check == "unavailable":
            return _error(503, "ORDER_CHECK_UNAVAILABLE", "we cannot confirm your order right now; nothing was used")
        if check == "inactive":
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
        if not self.store.deliverable(entitlement):
            self.store.release(entitlement)
            return _error(403, "ORDER_NOT_ACTIVE", "this order can no longer be fulfilled; contact support")

        token = self._token(headers)

        def before() -> bool:
            # Send-time re-check: reservation still held (a refund or cancel drops it) and the session still valid.
            return (self.store.deliverable(entitlement) and token is not None
                    and self.store.session_order(token) == order)

        def after(sent: bool) -> None:
            if not sent:
                self.store.release(entitlement)
                security_log("DELIVERY_NOT_SENT", 0, "generate")
            elif not self.store.commit_delivery(entitlement):
                security_log("DELIVERY_NOT_COUNTED_REVOKED", 0, "generate")

        return Response(200, pdf, "application/pdf",
                        headers=[("Content-Disposition", 'attachment; filename="Sabpuja-Janam-Kundali.pdf"')],
                        before=before, after=after)

    # ---- free preview (KUN-FREEMIUM-PREVIEW-001) -------------------------------------------
    def preview_config(self) -> Response:
        if self.preview is None:
            return _error(404, "NOT_FOUND", "not found")
        return _json(200, {"fields": list(self.preview.fields), "price_display": self.s.preview_price_display or None,
                           "buy_url": self.s.buy_url, "lead_capture": self.leads is not None,
                           "consent_version": leads_mod.CONSENT_VERSION if self.leads is not None else None,
                           "date_min": PREVIEW_DATE_MIN, "date_max": self.preview._today().isoformat(),
                           "places": self._public_places(), "report_pages": 14, "report_language": PAID_LOCALE,
                           # QA store (test orders allowed) or unreleased wording: the page shows a QA banner.
                           "qa_store": self.s.allow_test_orders or self.s.allow_unreleased_edition})

    def preview_chart(self, body: bytes, client: str) -> Response:
        """Public, unauthenticated, no session, no store. Returns only the whitelisted preview fields."""
        if self.preview is None:
            return _error(404, "NOT_FOUND", "not found")
        if not (self._preview_minute.allow("m:" + client) and self._preview_hour.allow("h:" + client)):
            security_log("PREVIEW_RATE_LIMITED", 429, "preview")
            return _error(429, "PREVIEW_RATE_LIMITED", "too many previews from this connection; try again later",
                          retry_after_seconds=60)
        if not self._preview_global.allow("all"):
            security_log("PREVIEW_GLOBAL_LIMIT", 429, "preview")
            return _error(429, "PREVIEW_BUSY", "the free preview is busy; try again in a minute", retry_after_seconds=60)
        try:
            form = preview_mod.parse(body)
        except preview_mod.PreviewRefused as exc:
            return _error(exc.status, exc.code, exc.message, category=exc.category)
        self.funnel.count("preview_initiated")
        if not self._preview_slots.acquire(blocking=False):
            return _error(429, "PREVIEW_BUSY", "the free preview is busy; try again shortly", retry_after_seconds=5)
        try:
            result = self.preview(form)
        except preview_mod.PreviewRefused as exc:
            self.funnel.count("preview_refused")
            return _error(exc.status, exc.code, exc.message, category=exc.category, **exc.extra)
        except preview_mod.PreviewUnavailable as exc:
            security_log("PREVIEW_UNAVAILABLE:" + exc.code, 503, "preview")
            return _error(503, "PREVIEW_UNAVAILABLE", "the preview cannot be calculated right now; please try later")
        except Exception as exc:  # noqa: BLE001 - a defect: type only, never the input
            security_log("PREVIEW_FAILURE:" + type(exc).__name__, 503, "preview")
            return _error(503, "PREVIEW_UNAVAILABLE", "the preview cannot be calculated right now; please try later")
        finally:
            self._preview_slots.release()
        self.funnel.count("preview_generated")
        return _json(200, result)

    def funnel_event(self, body: bytes, client: str) -> Response:
        if self.preview is None:
            return _error(404, "NOT_FOUND", "not found")
        if not self._beacon_limit.allow(client):
            return Response(204)   # silently dropped: a beacon is never worth an error page
        try:
            data = json.loads(body.decode("utf-8"), object_pairs_hook=_no_duplicates)
        except (UnicodeDecodeError, ValueError, RecursionError):
            return _error(400, "REQUEST_INVALID", "the request must be one UTF-8 JSON object")
        if not isinstance(data, dict) or set(data) != {"event"} or data["event"] not in funnel_mod.BROWSER_EVENTS:
            return _error(400, "REQUEST_INVALID", "unknown event")
        self.funnel.count(data["event"])
        return Response(204)

    # ---- optional marketing opt-in (isolated QA store) ----------------------------------------
    def _lead_body(self, body: bytes, keys: set):
        try:
            data = json.loads(body.decode("utf-8"), object_pairs_hook=_no_duplicates)
        except (UnicodeDecodeError, ValueError, RecursionError):
            return None
        return data if isinstance(data, dict) and set(data) == keys else None

    def lead_subscribe(self, body: bytes, client: str) -> Response:
        if self.leads is None:
            return _error(404, "NOT_FOUND", "not found")
        if not self._lead_limit.allow("sub:" + client):
            return _error(429, "RATE_LIMITED", "too many attempts; try again in a minute")
        data = self._lead_body(body, {"email", "marketing_consent", "adult", "consent_version", "locale"})
        if data is None or not self.leads.valid_email(data["email"]):
            return _error(400, "LEAD_INVALID", "enter a valid e-mail address")
        # Consent must be the visitor's own explicit action on the current wording; never implied or pre-ticked.
        if data["marketing_consent"] is not True:
            return _error(400, "CONSENT_REQUIRED", "tick the box to agree to receive offers, or skip this step")
        if data["adult"] is not True:
            return _error(400, "ADULT_REQUIRED", "sign-up is for people aged 18 or older")
        if data["consent_version"] != leads_mod.CONSENT_VERSION:
            return _error(409, "CONSENT_VERSION_CHANGED", "the sign-up wording has changed; please reload the page")
        if data["locale"] not in leads_mod.LOCALES:
            return _error(400, "LEAD_INVALID", "unsupported language")
        issued = self.leads.subscribe(data["email"], data["locale"])
        if issued is not None:
            self._send_mail(leads_mod.compose_confirm(self.s.mail_from, issued[0], self.s.public_origin, issued[1]))
        return _json(202, {"status": "check_email",
                           "message": "If this address can be added, we have sent a confirmation link. "
                                      "Nothing is sent to you until you confirm."})

    def lead_link(self, body: bytes, client: str) -> Response:
        if self.leads is None:
            return _error(404, "NOT_FOUND", "not found")
        if not self._lead_limit.allow("link:" + client):
            return _error(429, "RATE_LIMITED", "too many attempts; try again in a minute")
        data = self._lead_body(body, {"email"})
        if data is None or not self.leads.valid_email(data["email"]):
            return _error(400, "LEAD_INVALID", "enter a valid e-mail address")
        issued = self.leads.manage_link(data["email"])
        if issued is not None:
            self._send_mail(leads_mod.compose_link(self.s.mail_from, issued[0], self.s.public_origin, issued[1]))
        return _json(202, {"status": "check_email",
                           "message": "If this address is signed up, we have sent it a link to manage or delete it."})

    def lead_token_action(self, body: bytes, client: str, action: str) -> Response:
        if self.leads is None:
            return _error(404, "NOT_FOUND", "not found")
        if not self._lead_limit.allow("tok:" + client):
            return _error(429, "RATE_LIMITED", "too many attempts; try again in a minute")
        data = self._lead_body(body, {"token"})
        if data is None:
            return _error(400, "LEAD_INVALID", "this link is not valid")
        outcome = getattr(self.leads, action)(data["token"])
        if outcome is None:
            return _error(404, "LINK_INVALID", "this link is not valid or has expired; ask for a new one below")
        return _json(200, {"status": outcome})
