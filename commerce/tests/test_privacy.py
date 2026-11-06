"""No birth data, PDF, e-mail, code or token at rest or in logs, after a full flow on a file database."""
import contextlib
import io
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

import helpers as h
from sabpuja_commerce import store as store_mod

NAME = "Synthetic Testname"


class AtRest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.dir.name, "commerce.sqlite")
        self.h = h.Harness(db_path=self.db)
        self.log = io.StringIO()
        with contextlib.redirect_stderr(self.log):
            self.h.paid()
            self.h.start()
            self.code = self.h.last_code()
            resp = self.h.verify(self.code)
            self.token = dict(resp.headers)["Set-Cookie"].split(";")[0].split("=", 1)[1]
            self.cookie = f"{'__Host-sbk_session'}={self.token}"
            self.pdf = self.h.generate(self.cookie, dict(h.BIRTH, display_name=NAME)).body
            self.h.generate(self.cookie, dict(h.BIRTH, birth_time=""))         # refusal path
            self.h.render.fail = RuntimeError(f"{h.BIRTH['birth_date']} {NAME}")
            self.h.generate(self.cookie)                                      # fault path
            self.h.post("/api/generate", h.BIRTH, cookie=self.cookie, origin="https://evil.invalid")
            self.h.verify("000000" if self.code != "000000" else "111111")
        self.h.store._db.execute("PRAGMA wal_checkpoint(FULL)")

    def tearDown(self):
        self.h.store.close()
        self.dir.cleanup()

    def secrets(self):
        return [*h.BIRTH.values(), "1990-05-17", "14:30", "Jaipur", NAME, h.EMAIL, h.EMAIL.split("@")[0], self.code,
                self.token]

    def test_database_files_hold_none_of_it(self):
        blob = b"".join(Path(self.dir.name, f).read_bytes() for f in os.listdir(self.dir.name))
        for value in self.secrets():
            self.assertNotIn(value.encode(), blob, value)
            self.assertNotIn(value.lower().encode(), blob, value)
        self.assertNotIn(b"%PDF", blob)

    def test_schema_has_no_personal_columns(self):
        db = sqlite3.connect(self.db)
        columns = {row[1] for table in ("entitlements", "otp_challenges", "sessions", "webhook_events", "revocations")
                   for row in db.execute(f"PRAGMA table_info({table})")}
        db.close()
        allowed = {"id", "shop", "order_id", "order_number", "line_item_id", "edition", "email_hash", "capacity",
                   "used", "status", "revoke_reason", "created_at", "claim_expires_at", "window_days",
                   "first_delivered_at", "in_flight_since", "code_hash", "expires_at", "attempts", "state",
                   "token_hash", "webhook_id", "topic", "received_at", "outcome", "reason", "at"}
        self.assertEqual(columns - allowed, set())

    def test_logs_hold_none_of_it(self):
        text = self.log.getvalue()
        self.assertTrue(text)  # the flow did log bounded events
        for value in self.secrets() + ["203.0.113.5", "evil.invalid"]:
            self.assertNotIn(value, text, value)

    def test_secure_delete_enabled(self):
        self.assertEqual(self.h.store._db.execute("PRAGMA secure_delete").fetchone()[0], 1)

    def test_purge_removes_expired_rows(self):
        self.h.clock.advance(2 * 86400)
        self.h.store.purge(webhook_retention_days=1)
        db = self.h.store._db
        self.assertEqual(db.execute("SELECT COUNT(*) FROM sessions").fetchone()[0], 0)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM otp_challenges").fetchone()[0], 0)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM webhook_events").fetchone()[0], 0)
        self.assertEqual(db.execute("SELECT COUNT(*) FROM entitlements").fetchone()[0], 1)

    def test_copied_database_without_pepper_cannot_match_email(self):
        other = store_mod.Store(":memory:", b"another-pepper-0123456789abcdef-0123")
        self.assertNotEqual(other.email_hash(h.EMAIL), self.h.store.email_hash(h.EMAIL))


if __name__ == "__main__":
    unittest.main()
