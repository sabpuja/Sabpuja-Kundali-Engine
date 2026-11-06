"""Entitlement store (SQLite). Holds order entitlements only.

There is deliberately no column for a name, birth date, time, place, PDF or raw e-mail address.
E-mails, one-time codes and session tokens are stored only as keyed HMACs (the pepper is outside
the database), so a copied database or backup cannot be used to claim or to read a customer's
address. Entitlements and the keyed e-mail hash are still customer-linked order data and need the
same backup, access and retention care as other order records. `secure_delete` overwrites deleted rows.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import hmac
import sqlite3
import threading
import time
import unicodedata

SCHEMA_VERSION = 2

_SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS webhook_events (
    webhook_id TEXT PRIMARY KEY, topic TEXT NOT NULL, received_at INTEGER NOT NULL, outcome TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entitlements (
    id INTEGER PRIMARY KEY,
    shop TEXT NOT NULL, order_id INTEGER NOT NULL, order_number INTEGER NOT NULL,
    line_item_id INTEGER NOT NULL, variant_id INTEGER NOT NULL, edition TEXT NOT NULL,
    email_hash BLOB,
    capacity INTEGER NOT NULL CHECK (capacity >= 1),
    used INTEGER NOT NULL DEFAULT 0 CHECK (used >= 0 AND used <= capacity),
    status TEXT NOT NULL CHECK (status IN ('active', 'revoked')),
    revoke_reason TEXT,
    created_at INTEGER NOT NULL, claim_expires_at INTEGER NOT NULL, hard_expires_at INTEGER NOT NULL,
    window_days INTEGER NOT NULL, first_delivered_at INTEGER,
    in_flight_since INTEGER,
    UNIQUE (shop, order_id, line_item_id));
CREATE INDEX IF NOT EXISTS entitlements_claim ON entitlements (shop, order_number);
CREATE TABLE IF NOT EXISTS revocations (
    shop TEXT NOT NULL, order_id INTEGER NOT NULL, line_item_id INTEGER NOT NULL,  -- 0: whole order
    reason TEXT NOT NULL, at INTEGER NOT NULL, PRIMARY KEY (shop, order_id, line_item_id));
CREATE TABLE IF NOT EXISTS otp_challenges (
    id INTEGER PRIMARY KEY, shop TEXT NOT NULL, order_id INTEGER NOT NULL, email_hash BLOB NOT NULL,
    code_hash BLOB NOT NULL, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0, state TEXT NOT NULL CHECK (state IN ('open', 'used', 'locked', 'replaced')));
CREATE INDEX IF NOT EXISTS otp_order ON otp_challenges (shop, order_id);
CREATE TABLE IF NOT EXISTS sessions (
    token_hash BLOB PRIMARY KEY, shop TEXT NOT NULL, order_id INTEGER NOT NULL,
    created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL);
-- Paid purchases that could not become a claimable entitlement. Ids and a bounded kind only, no PII.
CREATE TABLE IF NOT EXISTS order_exceptions (
    id INTEGER PRIMARY KEY, at INTEGER NOT NULL, kind TEXT NOT NULL, order_id INTEGER, webhook_id TEXT,
    resolved_at INTEGER);
"""

EXCEPTION_KINDS = frozenset({"paid_without_email", "sellable_line_rejected", "malformed_paid_webhook"})

# A reservation older than this is treated as abandoned (process crash mid-render).
STALE_RESERVATION_SECONDS = 300


def normalize_email(value: str) -> str:
    return unicodedata.normalize("NFKC", value).strip().lower()


class Store:
    def __init__(self, path: str, pepper: bytes, clock=time.time):
        self._pepper = pepper
        self._clock = clock
        self._lock = threading.RLock()
        self._db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA secure_delete = ON")
        if path != ":memory:":
            self._db.execute("PRAGMA journal_mode = WAL")
        self._db.executescript(_SCHEMA)
        self._db.execute("INSERT OR IGNORE INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
        version = self._db.execute("SELECT value FROM meta WHERE key = 'schema_version'").fetchone()[0]
        if version != str(SCHEMA_VERSION):
            raise RuntimeError("entitlement database schema version mismatch")

    # ---- keyed hashes -------------------------------------------------------------------
    def digest(self, purpose: str, value: str | bytes) -> bytes:
        data = value.encode("utf-8") if isinstance(value, str) else value
        return hmac.new(self._pepper, purpose.encode() + b"\x00" + data, hashlib.sha256).digest()

    def email_hash(self, email: str) -> bytes:
        return self.digest("email", normalize_email(email))

    def now(self) -> int:
        return int(self._clock())

    @contextmanager
    def tx(self):
        with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
            else:
                self._db.execute("COMMIT")

    def close(self) -> None:
        self._db.close()

    def __del__(self):
        try:
            self._db.close()
        except Exception:  # noqa: BLE001 - interpreter shutdown
            pass

    # ---- webhooks ---------------------------------------------------------------------
    def record_webhook(self, db, webhook_id: str, topic: str) -> bool:
        """True if this webhook id is new. Must be called inside tx()."""
        cur = db.execute("INSERT OR IGNORE INTO webhook_events VALUES (?, ?, ?, 'received')",
                         (webhook_id, topic, self.now()))
        return cur.rowcount == 1

    def set_webhook_outcome(self, db, webhook_id: str, outcome: str) -> None:
        db.execute("UPDATE webhook_events SET outcome = ? WHERE webhook_id = ?", (outcome, webhook_id))

    def add_exception(self, db, kind: str, order_id: int | None, webhook_id: str | None) -> None:
        if kind not in EXCEPTION_KINDS:
            raise ValueError("unknown exception kind")
        db.execute("INSERT INTO order_exceptions (at, kind, order_id, webhook_id) VALUES (?, ?, ?, ?)",
                   (self.now(), kind, order_id, webhook_id))

    def open_exceptions(self) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT id, at, kind, order_id, webhook_id FROM order_exceptions "
                                    "WHERE resolved_at IS NULL ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    def resolve_exception(self, exception_id: int) -> bool:
        with self.tx() as db:
            return db.execute("UPDATE order_exceptions SET resolved_at = ? WHERE id = ? AND resolved_at IS NULL",
                              (self.now(), exception_id)).rowcount == 1

    def is_revoked(self, db, shop: str, order_id: int, line_item_id: int) -> bool:
        row = db.execute("SELECT 1 FROM revocations WHERE shop = ? AND order_id = ? AND line_item_id IN (0, ?)",
                         (shop, order_id, line_item_id)).fetchone()
        return row is not None

    def add_entitlement(self, db, *, shop, order_id, order_number, line_item_id, variant_id, edition, email_hash,
                        capacity, claim_days, window_days, horizon_days) -> str:
        if self.is_revoked(db, shop, order_id, line_item_id):
            return "revoked_before_paid"
        now = self.now()
        cur = db.execute(
            "INSERT OR IGNORE INTO entitlements (shop, order_id, order_number, line_item_id, variant_id, edition,"
            " email_hash, capacity, status, created_at, claim_expires_at, hard_expires_at, window_days)"
            " VALUES (?,?,?,?,?,?,?,?,'active',?,?,?,?)",
            (shop, order_id, order_number, line_item_id, variant_id, edition, email_hash, capacity, now,
             now + claim_days * 86400, now + horizon_days * 86400, window_days))
        return "created" if cur.rowcount == 1 else "already_present"

    def revoke(self, db, shop: str, order_id: int, line_item_id: int, reason: str) -> int:
        """Revoke one line (or the whole order with line_item_id 0), keep a tombstone and drop any reservation,
        so an in-flight delivery can no longer be counted. Ends the order's sessions when nothing stays active."""
        db.execute("INSERT OR IGNORE INTO revocations VALUES (?, ?, ?, ?, ?)",
                   (shop, order_id, line_item_id, reason, self.now()))
        where, args = ("shop = ? AND order_id = ?", [shop, order_id])
        if line_item_id:
            where, args = where + " AND line_item_id = ?", args + [line_item_id]
        cur = db.execute(f"UPDATE entitlements SET status = 'revoked', revoke_reason = ?, in_flight_since = NULL "
                         f"WHERE {where} AND status = 'active'", [reason, *args])
        left = db.execute("SELECT COUNT(*) FROM entitlements WHERE shop = ? AND order_id = ? AND status = 'active'",
                          (shop, order_id)).fetchone()[0]
        if left == 0:
            db.execute("DELETE FROM sessions WHERE shop = ? AND order_id = ?", (shop, order_id))
        return cur.rowcount

    def revoke_now(self, shop: str, order_id: int, line_item_id: int, reason: str) -> int:
        with self.tx() as db:
            return self.revoke(db, shop, order_id, line_item_id, reason)

    def active_lines(self, shop: str, order_id: int) -> dict[int, int]:
        """line_item_id -> variant_id of the order's active entitlements."""
        with self._lock:
            rows = self._db.execute("SELECT line_item_id, variant_id FROM entitlements WHERE shop = ? AND "
                                    "order_id = ? AND status = 'active'", (shop, order_id)).fetchall()
        return {r["line_item_id"]: r["variant_id"] for r in rows}

    def active_order_ids(self, shop: str) -> list[int]:
        now = self.now()
        with self._lock:
            rows = self._db.execute("SELECT DISTINCT order_id FROM entitlements WHERE shop = ? AND status = 'active' "
                                    "AND hard_expires_at > ? ORDER BY order_id", (shop, now)).fetchall()
        return [r[0] for r in rows]

    # ---- claim -------------------------------------------------------------------------
    def claimable_order(self, shop: str, order_number: int, email_hash: bytes) -> int | None:
        """The order id if an active, unexpired, claimable entitlement matches; else None."""
        now = self.now()
        with self._lock:
            rows = self._db.execute("SELECT * FROM entitlements WHERE shop = ? AND order_number = ? AND "
                                    "status = 'active'", (shop, order_number)).fetchall()
        for row in rows:
            if row["email_hash"] is None or not hmac.compare_digest(row["email_hash"], email_hash):
                continue
            if self._usable(row, now):
                return row["order_id"]
        return None

    @staticmethod
    def _window_end(row) -> int | None:
        if row["first_delivered_at"] is None:
            return None
        return min(row["first_delivered_at"] + row["window_days"] * 86400, row["hard_expires_at"])

    def _usable(self, row, now: int) -> bool:
        if row["status"] != "active" or row["used"] >= row["capacity"] or now >= row["hard_expires_at"]:
            return False
        end = self._window_end(row)
        return now < row["claim_expires_at"] if end is None else now < end

    def otp_count_since(self, shop: str, order_id: int, since: int) -> int:
        with self._lock:
            return self._db.execute("SELECT COUNT(*) FROM otp_challenges WHERE shop = ? AND order_id = ? AND "
                                    "created_at >= ?", (shop, order_id, since)).fetchone()[0]

    def last_otp_at(self, shop: str, order_id: int) -> int | None:
        with self._lock:
            row = self._db.execute("SELECT MAX(created_at) FROM otp_challenges WHERE shop = ? AND order_id = ?",
                                   (shop, order_id)).fetchone()
        return row[0]

    def new_otp(self, shop: str, order_id: int, email_hash: bytes, code: str, ttl: int) -> None:
        now = self.now()
        with self.tx() as db:
            db.execute("UPDATE otp_challenges SET state = 'replaced' WHERE shop = ? AND order_id = ? AND "
                       "state = 'open'", (shop, order_id))
            db.execute("INSERT INTO otp_challenges (shop, order_id, email_hash, code_hash, created_at, expires_at,"
                       " state) VALUES (?,?,?,?,?,?,'open')",
                       (shop, order_id, email_hash, self.digest("otp", f"{order_id}:{code}"), now, now + ttl))

    def check_otp(self, shop: str, order_id: int, email_hash: bytes, code: str, max_attempts: int) -> bool:
        """Constant-time check of the single open challenge. Consumes it on success; locks it after
        max_attempts wrong codes. Expired, used, replaced or locked challenges never succeed."""
        now = self.now()
        with self.tx() as db:
            row = db.execute("SELECT * FROM otp_challenges WHERE shop = ? AND order_id = ? AND state = 'open' "
                             "ORDER BY id DESC LIMIT 1", (shop, order_id)).fetchone()
            if row is None or now >= row["expires_at"] or not hmac.compare_digest(row["email_hash"], email_hash):
                return False
            ok = hmac.compare_digest(row["code_hash"], self.digest("otp", f"{order_id}:{code}"))
            if ok:
                db.execute("UPDATE otp_challenges SET state = 'used' WHERE id = ?", (row["id"],))
                return True
            attempts = row["attempts"] + 1
            db.execute("UPDATE otp_challenges SET attempts = ?, state = ? WHERE id = ?",
                       (attempts, "locked" if attempts >= max_attempts else "open", row["id"]))
            return False

    # ---- sessions -----------------------------------------------------------------------
    def new_session(self, token: str, shop: str, order_id: int, ttl: int) -> None:
        now = self.now()
        with self.tx() as db:
            db.execute("INSERT INTO sessions VALUES (?,?,?,?,?)",
                       (self.digest("session", token), shop, order_id, now, now + ttl))

    def session_order(self, token: str) -> tuple[str, int] | None:
        with self._lock:
            row = self._db.execute("SELECT * FROM sessions WHERE token_hash = ?",
                                   (self.digest("session", token),)).fetchone()
        if row is None or self.now() >= row["expires_at"]:
            return None
        return row["shop"], row["order_id"]

    def end_session(self, token: str) -> None:
        with self.tx() as db:
            db.execute("DELETE FROM sessions WHERE token_hash = ?", (self.digest("session", token),))

    # ---- generation quota ---------------------------------------------------------------
    def order_status(self, shop: str, order_id: int) -> dict:
        now = self.now()
        with self._lock:
            rows = self._db.execute("SELECT * FROM entitlements WHERE shop = ? AND order_id = ? ORDER BY id",
                                    (shop, order_id)).fetchall()
        usable = [r for r in rows if self._usable(r, now)]
        ends = [self._window_end(r) for r in usable if self._window_end(r) is not None]
        return {"active": any(r["status"] == "active" for r in rows),
                "remaining": sum(r["capacity"] - r["used"] for r in usable),
                "used": sum(r["used"] for r in rows),
                "window_ends_at": min(ends) if ends else None}

    def reserve(self, shop: str, order_id: int) -> tuple[int | None, str]:
        """Reserve one generation on the order. Returns (entitlement id, reason)."""
        now = self.now()
        with self.tx() as db:
            rows = db.execute("SELECT * FROM entitlements WHERE shop = ? AND order_id = ? ORDER BY id",
                              (shop, order_id)).fetchall()
            if not rows or all(r["status"] != "active" for r in rows):
                return None, "revoked"
            if any(r["in_flight_since"] is not None and now - r["in_flight_since"] < STALE_RESERVATION_SECONDS
                   for r in rows):
                return None, "in_progress"
            for r in rows:
                if self._usable(r, now):
                    db.execute("UPDATE entitlements SET in_flight_since = ? WHERE id = ?", (now, r["id"]))
                    return r["id"], "reserved"
            active = [r for r in rows if r["status"] == "active"]
            if all(r["used"] >= r["capacity"] for r in active):
                return None, "quota_exhausted"
            return None, "expired"

    def release(self, entitlement_id: int) -> None:
        """Give the reservation back without counting it (refused input, render or send failure)."""
        with self.tx() as db:
            db.execute("UPDATE entitlements SET in_flight_since = NULL WHERE id = ?", (entitlement_id,))

    def deliverable(self, entitlement_id: int) -> bool:
        """The send-time check: still active and still holding its reservation (a revoke drops it)."""
        with self._lock:
            row = self._db.execute("SELECT status, in_flight_since FROM entitlements WHERE id = ?",
                                   (entitlement_id,)).fetchone()
        return row is not None and row["status"] == "active" and row["in_flight_since"] is not None

    def commit_delivery(self, entitlement_id: int) -> bool:
        """Count a delivered PDF, atomically and only if the entitlement is still active and still reserved.
        A revocation that landed while the bytes were being sent wins: nothing is counted or recorded."""
        now = self.now()
        with self.tx() as db:
            cur = db.execute("UPDATE entitlements SET used = used + 1, in_flight_since = NULL, "
                             "first_delivered_at = COALESCE(first_delivered_at, ?) WHERE id = ? AND status = 'active'"
                             " AND in_flight_since IS NOT NULL AND used < capacity", (now, entitlement_id))
            if cur.rowcount == 1:
                return True
            db.execute("UPDATE entitlements SET in_flight_since = NULL WHERE id = ?", (entitlement_id,))
            return False

    # ---- housekeeping -------------------------------------------------------------------
    def purge(self, webhook_retention_days: int) -> None:
        now = self.now()
        with self.tx() as db:
            db.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
            db.execute("DELETE FROM otp_challenges WHERE expires_at <= ?", (now - 86400,))
            db.execute("DELETE FROM webhook_events WHERE received_at <= ?", (now - webhook_retention_days * 86400,))
