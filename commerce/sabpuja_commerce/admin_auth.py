"""Shopify Admin API access tokens (KUN-COM-PROD-HARDEN-001, F4).

A Dev Dashboard app installed on one store gets its Admin API token through the client-credentials grant:
POST https://<shop>/admin/oauth/access_token with the app's client id and secret. The token expires
(`expires_in`, about 24 h on the QA store) and comes with no refresh token, so the service asks again before it
expires.

Rules:
* The token lives only in this process's memory. It is never written to disk, logged or put in an error, so a
  restart simply asks for a new one; there is no file that a crash could leave half-written.
* Single flight: one renewal at a time. While a renewal runs, callers keep using the old token if it is still
  valid, otherwise they wait for the renewal (bounded) instead of starting their own.
* A new token is used only after the grant names every required scope and a `shop { myshopifyDomain }` query
  with it, answered under the configured API version, names the configured shop.
* A failed renewal is not retried before `retry_backoff` seconds have passed. With no valid token the caller gets
  None and fails closed (503, nothing granted, nothing revoked).
* `invalidate(token)` drops a token Shopify answered 401 for, so the next call makes one fresh request.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

SHOP_QUERY = "query SabpujaShopCheck { shop { myshopifyDomain } }"
_TOKEN = re.compile(r"^[\x21-\x7e]{16,512}$")
MIN_LIFETIME = 120                 # shorter grants are refused: they could not be renewed safely
MAX_LIFETIME = 366 * 86400


def _log(event: str, **fields) -> None:
    # Bounded operational line: an event name plus status codes or scope names, never a token, a secret or an order.
    print(json.dumps({"event": event, **fields}), file=sys.stderr, flush=True)


def granted_scopes(scope_text) -> frozenset[str]:
    """Shopify lists granted scopes comma-separated; a write_ scope implies the matching read_ scope."""
    if not isinstance(scope_text, str):
        return frozenset()
    names = {s.strip() for s in scope_text.split(",") if s.strip()}
    return frozenset(names | {"read_" + n[len("write_"):] for n in names if n.startswith("write_")})


class StaticToken:
    """A non-expiring token from a file (a store-admin custom app's shpat_ token). Kept for that case and for
    offline tests; Dev Dashboard apps use ClientCredentialsTokens."""

    def __init__(self, token: str):
        self._token = token

    def token(self) -> str | None:
        return self._token or None

    def invalidate(self, token: str) -> None:
        pass  # nothing to renew; a 401 keeps failing closed until the operator replaces the file


class ClientCredentialsTokens:
    def __init__(self, settings, base_url: str | None = None, timeout: float = 5.0, clock=time.monotonic,
                 opener=None, retry_backoff: float = 30.0, wait_limit: float | None = None):
        self._s = settings
        self._base = base_url or f"https://{settings.shop_domain}"
        self._timeout = timeout
        self._clock = clock
        self._open = opener or urllib.request.urlopen
        self._backoff = retry_backoff
        self._wait_limit = wait_limit if wait_limit is not None else 3 * timeout + 1
        self._cond = threading.Condition()
        self._token: str | None = None
        self._renew_at = 0.0
        self._expires_at = 0.0
        self._retry_after = 0.0
        self._refreshing = False
        self.requests = 0          # grant requests made; tests use it to prove single flight

    # ---- public ----------------------------------------------------------------------------------
    def token(self) -> str | None:
        with self._cond:
            deadline = self._clock() + self._wait_limit
            while True:
                now = self._clock()
                valid = self._token is not None and now < self._expires_at
                if valid and now < self._renew_at:
                    return self._token
                if self._refreshing:
                    if valid:
                        return self._token           # renewal in progress; the old token still works
                    if now >= deadline:
                        return None
                    self._cond.wait(timeout=max(0.01, min(0.25, deadline - now)))
                    continue
                if now < self._retry_after:
                    return self._token if valid else None
                self._refreshing = True
                break
        started = self._clock()      # lifetimes count from the request, not from the answer
        try:
            new = self._acquire()
        except Exception:   # noqa: BLE001 - any failure is a failed renewal; the flag must be cleared below
            _log("SHOPIFY_TOKEN_FAILED", status="internal")
            new = None
        with self._cond:
            self._refreshing = False
            now = self._clock()
            if new is not None:
                token, lifetime = new
                self._token = token
                self._renew_at = started + lifetime - min(600.0, lifetime / 10)
                self._expires_at = started + lifetime - min(30.0, lifetime / 20)
                self._retry_after = 0.0
            else:
                self._retry_after = now + self._backoff
            self._cond.notify_all()
            valid = self._token is not None and now < self._expires_at
            return self._token if valid else None

    def invalidate(self, token: str) -> None:
        with self._cond:
            if token is not None and token == self._token:
                self._token = None
                self._renew_at = self._expires_at = 0.0

    # ---- grant -----------------------------------------------------------------------------------
    def _acquire(self) -> tuple[str, float] | None:
        self.requests += 1
        form = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": self._s.admin_client_id,
                                       "client_secret": self._s.admin_client_secret.decode()}).encode()
        req = urllib.request.Request(self._base + "/admin/oauth/access_token", data=form, method="POST", headers={
            "Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"})
        try:
            with self._open(req, timeout=self._timeout) as resp:   # noqa: S310 - fixed shop host
                data = json.loads(resp.read(16 * 1024).decode("utf-8"))
        except urllib.error.HTTPError as exc:
            _log("SHOPIFY_TOKEN_FAILED", status=exc.code)
            return None
        except (OSError, ValueError):
            _log("SHOPIFY_TOKEN_FAILED", status=0)
            return None
        if not isinstance(data, dict):
            _log("SHOPIFY_TOKEN_FAILED", status="unusable_answer")
            return None
        token, lifetime = data.get("access_token"), data.get("expires_in")
        if not isinstance(token, str) or not _TOKEN.match(token) or isinstance(lifetime, bool) \
                or not isinstance(lifetime, int) or not MIN_LIFETIME <= lifetime <= MAX_LIFETIME:
            _log("SHOPIFY_TOKEN_FAILED", status="unusable_answer")
            return None
        missing = sorted(set(self._s.required_scopes) - granted_scopes(data.get("scope")))
        if missing:
            _log("SHOPIFY_TOKEN_SCOPE_MISSING", missing=missing)
            return None
        if not self._shop_matches(token):
            return None
        return token, float(lifetime)

    def _shop_matches(self, token: str) -> bool:
        url = f"{self._base}/admin/api/{self._s.admin_api_version}/graphql.json"
        req = urllib.request.Request(url, data=json.dumps({"query": SHOP_QUERY}).encode(), method="POST", headers={
            "X-Shopify-Access-Token": token, "Content-Type": "application/json", "Accept": "application/json"})
        try:
            with self._open(req, timeout=self._timeout) as resp:   # noqa: S310 - fixed shop host
                served = resp.headers.get("X-Shopify-API-Version")
                data = json.loads(resp.read(16 * 1024).decode("utf-8"))
        except urllib.error.HTTPError as exc:
            _log("SHOPIFY_TOKEN_CHECK_FAILED", status=exc.code)
            return False
        except (OSError, ValueError):
            _log("SHOPIFY_TOKEN_CHECK_FAILED", status=0)
            return False
        if served != self._s.admin_api_version:
            _log("SHOPIFY_API_VERSION_MISMATCH", served=served if isinstance(served, str) and len(served) <= 16
                 else "absent")
            return False
        try:
            domain = data["data"]["shop"]["myshopifyDomain"]
        except (KeyError, TypeError):
            domain = None
        if domain != self._s.shop_domain:
            _log("SHOPIFY_TOKEN_SHOP_MISMATCH")
            return False
        return True


def for_settings(settings, base_url: str | None = None, timeout: float = 5.0):
    if settings.admin_client_id:
        return ClientCredentialsTokens(settings, base_url=base_url, timeout=timeout)
    return StaticToken(settings.admin_api_token)
