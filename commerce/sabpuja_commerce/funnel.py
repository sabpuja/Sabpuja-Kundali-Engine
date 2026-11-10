"""Aggregate conversion funnel (KUN-FREEMIUM-PREVIEW-001 phase 4). QA ONLY.

One counter per (UTC day, event). There is no row per visitor, no identifier, no address, no user agent,
no birth detail, no e-mail, no chart value and no time finer than a day, so a row cannot be tied to a person.
No cookie, pixel, fingerprint or third-party service is involved.

Events:
  preview_initiated       POST /api/preview arrived with a well-formed request (server side)
  preview_generated       a preview was returned (server side)
  preview_refused         the birth details were refused (server side; the refusal code is not kept)
  full_report_selected    "Buy Full Kundali Report" pressed below a preview (browser beacon)
  checkout_started        "Continue to secure checkout" pressed, the hand-off to Shopify (browser beacon)
  paid_order_completed    an orders/paid webhook created an entitlement (server side). Shopify orders carry no
                          link to a preview, so this is the total of paid orders, not an attributed conversion.
"""
from __future__ import annotations

import sqlite3
import threading
import time

EVENTS = ("preview_initiated", "preview_generated", "preview_refused", "full_report_selected",
          "checkout_started", "paid_order_completed")
BROWSER_EVENTS = frozenset({"full_report_selected", "checkout_started"})

_SCHEMA = """
CREATE TABLE IF NOT EXISTS funnel_daily (
    day TEXT NOT NULL, event TEXT NOT NULL, count INTEGER NOT NULL CHECK (count >= 0),
    PRIMARY KEY (day, event));
"""


class Funnel:
    def __init__(self, path: str = ":memory:", clock=time.time):
        self._clock, self._lock = clock, threading.Lock()
        self._db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self._db.execute("PRAGMA secure_delete = ON")
        self._db.executescript(_SCHEMA)

    def _day(self) -> str:
        return time.strftime("%Y-%m-%d", time.gmtime(self._clock()))

    def count(self, event: str) -> None:
        if event not in EVENTS:
            raise ValueError("unknown funnel event")
        with self._lock:
            self._db.execute("INSERT INTO funnel_daily VALUES (?, ?, 1) "
                             "ON CONFLICT (day, event) DO UPDATE SET count = count + 1", (self._day(), event))

    def report(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT day, event, count FROM funnel_daily ORDER BY day, event").fetchall()
        return [{"day": d, "event": e, "count": c} for d, e, c in rows]

    def totals(self) -> dict:
        out = dict.fromkeys(EVENTS, 0)
        for row in self.report():
            out[row["event"]] += row["count"]
        return out


class NullFunnel:
    """Measurement switched off."""

    def count(self, event: str) -> None:
        if event not in EVENTS:
            raise ValueError("unknown funnel event")

    def report(self) -> list[dict]:
        return []

    def totals(self) -> dict:
        return dict.fromkeys(EVENTS, 0)
