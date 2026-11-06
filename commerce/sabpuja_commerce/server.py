"""Loopback HTTP transport for the fulfilment App. Put the hardened gateway in front of it.

Run (offline / staging only):  python -m sabpuja_commerce --config /run/secrets/commerce.json --port 8770
"""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import sys

from .app import MAX_BODY_BYTES, SECURITY_HEADERS, App
from .shopify import MAX_WEBHOOK_BYTES

HOST = "127.0.0.1"


class Handler(BaseHTTPRequestHandler):
    server_version = "sabpuja"
    sys_version = ""
    timeout = 15  # socket timeout per request: slow clients cannot hold a worker
    app: App

    def log_message(self, format, *args):  # noqa: A002 - no request line, address or body is logged
        pass

    def send_error(self, code, message=None, explain=None):
        self._write(code, b'{"error":{"code":"HTTP_ERROR","message":"request not accepted"}}',
                    "application/json; charset=utf-8", [])

    def _write(self, status, body, ctype, headers) -> bool:
        try:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for name, value in list(SECURITY_HEADERS.items()) + list(headers):
                self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
                self.wfile.flush()
            return True
        except OSError:
            self.close_connection = True
            return False

    def _dispatch(self, method: str) -> None:
        body = b""
        if method == "POST":
            limit = MAX_WEBHOOK_BYTES if self.path.split("?", 1)[0] == "/webhooks/shopify" else MAX_BODY_BYTES
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return self.send_error(411)
            if length < 0 or length > limit:
                self.close_connection = True
                return self._write(413, b'{"error":{"code":"BODY_TOO_LARGE","message":"request too large"}}',
                                   "application/json; charset=utf-8", [])
            body = self.rfile.read(length)
        resp = self.app.handle(method, self.path, self.headers, body, self.client_address[0])
        sent = self._write(resp.status, resp.body, resp.content_type, resp.headers)
        if resp.after is not None:
            resp.after(sent)

    def do_GET(self):
        self._dispatch("GET")

    def do_HEAD(self):
        self._dispatch("HEAD")

    def do_POST(self):
        self._dispatch("POST")

    def do_PUT(self):
        self._dispatch("PUT")

    def do_DELETE(self):
        self._dispatch("DELETE")


class Server(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 16


def serve(app: App, port: int) -> Server:
    handler = type("BoundHandler", (Handler,), {"app": app})
    return Server((HOST, port), handler)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sabpuja Janam Kundali fulfilment (offline/staging)")
    parser.add_argument("--config", required=True)
    parser.add_argument("--port", type=int, default=8770)
    parser.add_argument("--smtp-config", help="JSON with host, port, username, password_file")
    args = parser.parse_args(argv)
    import json
    from . import config as cfg, mailer, renderer, shopify
    from .store import Store
    settings = cfg.load(args.config)
    sys.path[:0] = ["src", "prototype", "."]
    from kundali_prototype import places as pl
    from kundali_prototype.server import startup_verify
    # Paid orders use the same India reference places as the preview image (no test-only foreign fixtures).
    places = {k: v for k, v in startup_verify(settings.ephe_path).items() if k.startswith("in-")}
    if args.smtp_config:
        with open(args.smtp_config, encoding="utf-8") as fh:
            smtp = json.load(fh)
        with open(smtp["password_file"], encoding="utf-8") as fh:
            password = fh.read().strip()
        mail = mailer.SmtpMailer(smtp["host"], int(smtp["port"]), smtp["username"], password)
    else:
        print("no --smtp-config: codes go to an in-memory mock mailer (offline use only)", file=sys.stderr)
        mail = mailer.MockMailer()
    store = Store(settings.db_path, settings.pepper)
    verifier = shopify.AdminOrderVerifier(settings) if settings.verify_orders_with_admin_api else None
    app = App(settings, store, mail, renderer.EssentialsRenderer(
        places, settings.ephe_path, enforce_release=not settings.allow_unreleased_edition), places,
              verifier=verifier, public_places=lambda: [pl.public_place(places[k]) | {"id": k}
                                                         for k in places])
    httpd = serve(app, args.port)
    print(f"listening on {HOST}:{args.port}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0
