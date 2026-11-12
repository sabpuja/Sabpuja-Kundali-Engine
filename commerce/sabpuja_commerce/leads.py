"""Optional marketing sign-up after a free preview (KUN-FREEMIUM-PREVIEW-001 phase 3). ISOLATED QA ONLY.

Separate SQLite file from the entitlement database. It holds only what a lawful opt-in needs:
the e-mail address, its keyed hash (for uniqueness), the consent state and timestamps, the consent wording
version, the purpose, the source page, the page language and the visitor's own "18 or older" confirmation.
There is no column for a name, a birth date, time or place, a chart value, an order, an IP address or a
device identifier, and nothing from the preview is ever passed here.

Flow: unchecked box on the page -> /api/leads/subscribe -> state "pending" and one confirmation e-mail
(double opt-in, so nobody can sign up someone else) -> /api/leads/confirm -> "subscribed". Every e-mail
carries a manage link. Withdrawal keeps a minimal "withdrawn" record so the withdrawal is honoured; deletion
removes the row. Unconfirmed sign-ups are deleted after `pending_days`. This module sends no marketing:
the only mails are the confirmation and the manage link, and in QA they go to the private Mailpit sink.
Tokens are random, stored only as HMACs, and travel in the URL fragment (never sent to a server by a browser).

Deleted data on disk (KUN-FREEMIUM-PRIVACY-004). The file uses WAL journaling with `secure_delete`. A DELETE is
committed at once (autocommit), but SQLite keeps the earlier page versions, which still hold the address, in the
`-wal` file until a checkpoint copies the pages back and the WAL is reset. So after a deletion (`delete`, and `purge`
of expired sign-ups) the store runs `PRAGMA wal_checkpoint(TRUNCATE)`: it succeeds only when no reader still holds an
older snapshot, and then the WAL is truncated to 0 bytes and the main file holds only zeroed (secure_delete) pages.
The checkpoint never waits: `busy_timeout` is 0 and it is tried a bounded number of times
(`checkpoint_attempts` with `checkpoint_pause` seconds between). If it cannot complete, the deletion itself still
stands, `cleanup_pending` is set and the checkpoint is retried on the next call and at start-up; `--leads-summary`
reports `wal_cleanup_pending`. Withdrawal is not a deletion: it keeps the address with status "withdrawn" so the
withdrawal is honoured, and needs no cleanup. This does not erase copies made outside the live files (backups,
filesystem or volume snapshots, earlier copies of the directory): those follow their own retention.
"""
from __future__ import annotations

from email.message import EmailMessage
from email.utils import formatdate, make_msgid
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import threading
import time

from .store import normalize_email

CONSENT_VERSION = "sabpuja-offers-email-en/0.1-draft"
PURPOSE = "sabpuja_offers_email"
SOURCE = "kundali_free_preview"
LOCALES = frozenset({"en", "hi"})
CONFIRM_SUBJECT = "Please confirm: Sabpuja offers by e-mail"
LINK_SUBJECT = "Your Sabpuja e-mail preferences link"
BUSY_TIMEOUT_MS = 2000
_EMAIL = re.compile(r"^[^@\s]{1,64}@[^@\s]{1,255}$")
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{30,64}$")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL,
    email_hash BLOB NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'subscribed', 'withdrawn')),
    purpose TEXT NOT NULL, consent_version TEXT NOT NULL, source TEXT NOT NULL, locale TEXT NOT NULL,
    adult_confirmed INTEGER NOT NULL CHECK (adult_confirmed = 1),
    created_at INTEGER NOT NULL, consented_at INTEGER NOT NULL, confirmed_at INTEGER, withdrawn_at INTEGER,
    token_hash BLOB, token_expires_at INTEGER,
    mails_day INTEGER NOT NULL DEFAULT 0, mails_on_day INTEGER NOT NULL DEFAULT 0, last_mail_at INTEGER);
"""


class LeadStore:
    def __init__(self, path: str, pepper: bytes, clock=time.time, pending_days: int = 7,
                 resend_cooldown_seconds: int = 600, max_mails_per_day: int = 3, token_days: int = 30,
                 checkpoint_attempts: int = 3, checkpoint_pause: float = 0.05, sleep=time.sleep):
        if not pepper or len(pepper) < 32:
            raise ValueError("lead store needs the service pepper")
        self._pepper = hmac.new(pepper, b"sabpuja-leads/1", hashlib.sha256).digest()  # domain-separated key
        self._clock, self._lock = clock, threading.RLock()
        self.pending_days, self.cooldown, self.max_mails = pending_days, resend_cooldown_seconds, max_mails_per_day
        self.token_days = token_days
        self._attempts, self._pause, self._sleep = max(1, int(checkpoint_attempts)), checkpoint_pause, sleep
        self._path, self._wal = path, path != ":memory:"
        self.cleanup_pending = False
        self._db = sqlite3.connect(path, isolation_level=None, check_same_thread=False, timeout=BUSY_TIMEOUT_MS / 1000)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA secure_delete = ON")
        if self._wal:
            self._db.execute("PRAGMA journal_mode = WAL")
        self._db.executescript(_SCHEMA)
        if self._wal:
            self.scrub()  # fold in anything a previous process left in the WAL

    def close(self) -> None:
        with self._lock:
            self._db.close()

    def scrub(self) -> bool:
        """Checkpoint the WAL into the main file and truncate it, so deleted rows leave no old page copies behind.
        True only when the checkpoint completed and the WAL is empty. Never blocks for long (see module doc)."""
        if not self._wal:
            self.cleanup_pending = False
            return True
        with self._lock:
            if self._db.in_transaction:  # autocommit store: a deletion is always committed before this point
                raise RuntimeError("checkpoint inside a transaction")
            # Ordinary statements may wait up to BUSY_TIMEOUT_MS for another writer; the checkpoint never waits for
            # readers (busy_timeout 0 while it runs), it is only retried a bounded number of times.
            self._db.execute("PRAGMA busy_timeout = 0")
            try:
                for attempt in range(self._attempts):
                    if attempt:
                        self._sleep(self._pause)
                    try:
                        busy, log, done = self._db.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                    except sqlite3.OperationalError:  # locked by another connection
                        continue
                    if busy == 0 and log == done and self._wal_bytes() == 0:
                        self.cleanup_pending = False
                        return True
                self.cleanup_pending = True
                return False
            finally:
                self._db.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}")

    def _wal_bytes(self) -> int:
        try:
            return os.path.getsize(self._path + "-wal")
        except FileNotFoundError:
            return 0

    def _retry_cleanup(self) -> None:
        if self.cleanup_pending:
            self.scrub()

    def now(self) -> int:
        return int(self._clock())

    def _h(self, value: str) -> bytes:
        return hmac.new(self._pepper, value.encode("utf-8"), hashlib.sha256).digest()

    @staticmethod
    def valid_email(value) -> bool:
        return isinstance(value, str) and len(value.strip()) <= 254 and bool(_EMAIL.match(value.strip()))

    def purge(self) -> int:
        """Delete sign-ups never confirmed within `pending_days`."""
        with self._lock:
            cur = self._db.execute("DELETE FROM leads WHERE status = 'pending' AND created_at < ?",
                                   (self.now() - self.pending_days * 86400,))
            if cur.rowcount:
                self.scrub()
            else:
                self._retry_cleanup()
            return cur.rowcount

    def _may_mail(self, row) -> bool:
        now, day = self.now(), self.now() // 86400
        if row["last_mail_at"] is not None and now - row["last_mail_at"] < self.cooldown:
            return False
        return not (row["mails_day"] == day and row["mails_on_day"] >= self.max_mails)

    def _issue_token(self, lead_id: int) -> str:
        token = secrets.token_urlsafe(32)
        now, day = self.now(), self.now() // 86400
        self._db.execute(
            "UPDATE leads SET token_hash = ?, token_expires_at = ?, last_mail_at = ?, "
            "mails_on_day = CASE WHEN mails_day = ? THEN mails_on_day + 1 ELSE 1 END, mails_day = ? WHERE id = ?",
            (self._h(token), now + self.token_days * 86400, now, day, day, lead_id))
        return token

    def subscribe(self, email: str, locale: str) -> tuple[str, str] | None:
        """Record a pending opt-in. Returns (normalised e-mail, token) when a confirmation mail should be sent,
        or None (already subscribed, or mail limits reached). The caller replies identically either way."""
        if locale not in LOCALES:
            raise ValueError("locale")
        address = normalize_email(email)
        key, now = self._h(address), self.now()
        with self._lock:
            self.purge()
            row = self._db.execute("SELECT * FROM leads WHERE email_hash = ?", (key,)).fetchone()
            if row is None:
                cur = self._db.execute(
                    "INSERT INTO leads (email, email_hash, status, purpose, consent_version, source, locale, "
                    "adult_confirmed, created_at, consented_at) VALUES (?, ?, 'pending', ?, ?, ?, ?, 1, ?, ?)",
                    (address, key, PURPOSE, CONSENT_VERSION, SOURCE, locale, now, now))
                return address, self._issue_token(cur.lastrowid)
            if row["status"] == "subscribed" or not self._may_mail(row):
                return None
            # pending again, or withdrawn and opting in anew: fresh consent record, new token
            self._db.execute("UPDATE leads SET status = 'pending', consent_version = ?, locale = ?, consented_at = ?, "
                             "confirmed_at = NULL, withdrawn_at = NULL, created_at = ? WHERE id = ?",
                             (CONSENT_VERSION, locale, now, now, row["id"]))
            return address, self._issue_token(row["id"])

    def manage_link(self, email: str) -> tuple[str, str] | None:
        """A new manage token for an address on file (subject to the mail limits), else None."""
        address = normalize_email(email)
        with self._lock:
            row = self._db.execute("SELECT * FROM leads WHERE email_hash = ?", (self._h(address),)).fetchone()
            if row is None or not self._may_mail(row):
                return None
            return address, self._issue_token(row["id"])

    def _by_token(self, token: str):
        if not isinstance(token, str) or not _TOKEN.match(token):
            return None
        row = self._db.execute("SELECT * FROM leads WHERE token_hash = ?", (self._h(token),)).fetchone()
        if row is None or row["token_expires_at"] is None or row["token_expires_at"] < self.now():
            return None
        return row

    def status(self, token: str) -> str | None:
        with self._lock:
            self._retry_cleanup()
            row = self._by_token(token)
            return None if row is None else row["status"]

    def confirm(self, token: str) -> str | None:
        with self._lock:
            row = self._by_token(token)
            if row is None:
                return None
            if row["status"] == "pending":
                self._db.execute("UPDATE leads SET status = 'subscribed', confirmed_at = ? WHERE id = ?",
                                 (self.now(), row["id"]))
                return "subscribed"
            return row["status"]

    def withdraw(self, token: str) -> str | None:
        with self._lock:
            row = self._by_token(token)
            if row is None:
                return None
            self._db.execute("UPDATE leads SET status = 'withdrawn', withdrawn_at = ? WHERE id = ?",
                             (self.now(), row["id"]))
            return "withdrawn"

    def delete(self, token: str) -> str | None:
        with self._lock:
            row = self._by_token(token)
            if row is None:
                return None
            self._db.execute("DELETE FROM leads WHERE id = ?", (row["id"],))  # committed (autocommit)
            self.scrub()  # the deletion stands even if this has to be retried later (cleanup_pending)
            return "deleted"

    def mailable(self) -> list[str]:
        """Addresses that may receive offers: confirmed and not withdrawn. Nothing sends to them yet."""
        with self._lock:
            return [r[0] for r in self._db.execute(
                "SELECT email FROM leads WHERE status = 'subscribed' ORDER BY id").fetchall()]

    def counts(self) -> dict:
        with self._lock:
            rows = self._db.execute("SELECT status, COUNT(*) FROM leads GROUP BY status").fetchall()
        return {"pending": 0, "subscribed": 0, "withdrawn": 0} | {s: c for s, c in rows}


def _message(sender: str, to: str, subject: str, body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, to, subject
    domain = sender.rsplit("@", 1)[-1].strip(" >") if "@" in sender else None
    msg["Date"] = formatdate(localtime=False)
    msg["Message-ID"] = make_msgid(domain=domain)
    msg.set_content(body)
    return msg


def compose_confirm(sender: str, to: str, origin: str, token: str) -> EmailMessage:
    """Confirmation of a marketing opt-in (DRAFT copy, consent version CONSENT_VERSION). Holds no birth data."""
    return _message(sender, to, CONFIRM_SUBJECT,
                    "You asked to receive occasional offers and news from Sabpuja by e-mail.\n\n"
                    f"To confirm, open this link:\n{origin}/marketing#confirm={token}\n\n"
                    "If you did not ask for this, ignore this message: you will not be added, and the request is "
                    "deleted after 7 days.\n\n"
                    f"You can withdraw or delete your sign-up at any time:\n{origin}/marketing#manage={token}\n")


def compose_link(sender: str, to: str, origin: str, token: str) -> EmailMessage:
    return _message(sender, to, LINK_SUBJECT,
                    "Here is the link to manage your Sabpuja e-mail preferences. You can stop offers or delete "
                    f"your sign-up completely:\n{origin}/marketing#manage={token}\n\n"
                    "If you did not ask for this, you can ignore this message.\n")
