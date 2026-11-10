"""Customer-journey test server (KUN-COM-UX-CLAIM-001). Synthetic data only; loopback only; never deployed.

Runs the real App, Store, claim page and production EssentialsRenderer (release gate off, as in
helpers.essentials_renderer) behind the real loopback transport, with a mock mailer and a fake
Shopify order check. A second loopback port takes test-control commands that stand in for Shopify
(signed webhooks) and for faults the browser tests need (mail, renderer, order check, clock).

    PYTHONPATH=src:prototype:.:commerce:commerce/tests SABPUJA_TEST_EPHE_PATH=... \
        python commerce/tests/browser/journey_server.py --port 8771 --control-port 8772
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import re
import sys
import tempfile
import threading

import helpers as h
from sabpuja_commerce import app as app_mod, funnel as funnel_mod, leads as leads_mod, mailer, preview as preview_mod, \
    server
from sabpuja_commerce.renderer import RendererUnavailable
from sabpuja_commerce.store import Store


class Renderer:
    """Production renderer with switchable faults: ok, fail (server fault), unavailable, slow (seconds)."""

    def __init__(self, real):
        self.real, self.mode, self.delay, self.calls = real, "ok", 0.0, 0

    def __call__(self, body):
        self.calls += 1
        if self.delay:
            threading.Event().wait(self.delay)
        if self.mode == "fail":
            raise RuntimeError("synthetic render fault")
        if self.mode == "unavailable":
            raise RendererUnavailable("synthetic")
        return self.real(body)


class Verifier:
    """Stands in for the live Shopify order re-check: agrees with the store unless switched down."""

    def __init__(self, store, shop):
        self.store, self.shop, self.down = store, shop, False

    def lines(self, order_id):
        return None if self.down else self.store.active_lines(self.shop, order_id)


def build(port: int):
    ephe = os.environ["SABPUJA_TEST_EPHE_PATH"]
    from kundali_prototype import places as pl
    from kundali_prototype.server import startup_verify
    places = {k: v for k, v in startup_verify(ephe).items() if k.startswith("in-")}
    clock = h.Clock(__import__("time").time())
    db = os.path.join(tempfile.mkdtemp(prefix="sbk-journey-"), "entitlements.sqlite")
    # The fake Verifier below is passed to App, so the live re-check path (reconcile) still runs on every claim.
    s = h.settings(db_path=db, public_origin=f"http://127.0.0.1:{port}", require_order_verification=False,
                   source_url="https://github.com/sabpuja/Sabpuja-Kundali-Engine",
                   # KUN-FREEMIUM-PREVIEW-001: free preview, aggregate funnel and isolated opt-in store (synthetic).
                   preview_enabled=True, lead_capture_enabled=True, leads_db_path=db + ".leads",
                   funnel_db_path=db + ".funnel", preview_price_display=os.environ.get("SBK_PRICE", ""))
    store = Store(s.db_path, s.pepper, clock=clock)
    mail = mailer.MockMailer()
    render = Renderer(h.essentials_renderer(places))
    verifier = Verifier(store, s.shop_domain)
    funnel = funnel_mod.Funnel(s.funnel_db_path)
    leads = leads_mod.LeadStore(s.leads_db_path, s.pepper, clock=clock)
    app = app_mod.App(s, store, mail, render, places, verifier=verifier, async_mail=False,
                      public_places=lambda: [pl.public_place(places[k]) | {"id": k} for k in places],
                      preview=preview_mod.PreviewService(places, ephe), funnel=funnel, leads=leads)
    return app, store, mail, render, verifier, clock, db


def control_handler(app, store, mail, render, verifier, clock, db):
    counter = {"n": 0}

    def hook(topic, payload):
        counter["n"] += 1
        body = json.dumps(payload).encode()
        headers = h.webhook_headers(topic, body, f"journey-{counter['n']}")
        return app.handle("POST", "/webhooks/shopify", headers, body, "127.0.0.1").json()

    class Control(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _reply(self, payload, status=200):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length") or 0)) or b"{}")
            path = self.path
            if path == "/paid":
                kw = {k: body[k] for k in ("order_id", "number", "email", "qty", "status") if k in body}
                return self._reply(hook("orders/paid", h.order(**kw)))
            if path == "/refund":
                return self._reply(hook("refunds/create", {"id": body["order_id"] * 7, "order_id": body["order_id"],
                                                           "refund_line_items": []}))
            if path == "/cancel":
                return self._reply(hook("orders/cancelled", {"id": body["order_id"]}))
            if path == "/render":
                render.mode, render.delay = body.get("mode", "ok"), float(body.get("delay", 0))
                return self._reply({"ok": True})
            if path == "/verifier":
                verifier.down = bool(body.get("down"))
                return self._reply({"ok": True})
            if path == "/mail":
                mail.fail = bool(body.get("fail"))
                return self._reply({"ok": True})
            if path == "/clock":
                clock.advance(float(body["seconds"]))
                return self._reply({"ok": True, "t": clock()})
            return self._reply({"error": "unknown"}, 404)

        def do_GET(self):
            if self.path.startswith("/codes"):
                out = []
                for m in mail.sent:
                    found = re.search(r"is ([0-9]{6})\.", m.get_content())
                    out.append({"to": m["To"], "subject": m["Subject"], "code": found and found.group(1),
                                "text": m.get_content()})
                return self._reply({"sent": out})
            if self.path == "/funnel":
                return self._reply(app.funnel.totals())
            if self.path == "/leads":
                return self._reply({"counts": app.leads.counts(), "mailable": app.leads.mailable(),
                                    "dump": "\n".join(app.leads._db.iterdump())})
            if self.path == "/stats":
                return self._reply({"render_calls": render.calls, "db": db, "exceptions": store.open_exceptions()})
            return self._reply({"error": "unknown"}, 404)

    return Control


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8771)
    p.add_argument("--control-port", type=int, default=8772)
    a = p.parse_args(argv)
    app, store, mail, render, verifier, clock, db = build(a.port)
    httpd = server.serve(app, a.port)
    ctl = ThreadingHTTPServer(("127.0.0.1", a.control_port), control_handler(app, store, mail, render, verifier,
                                                                              clock, db))
    threading.Thread(target=ctl.serve_forever, daemon=True).start()
    print(json.dumps({"listening": a.port, "control": a.control_port, "db": db}), flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
