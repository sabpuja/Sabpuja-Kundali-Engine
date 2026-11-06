"""Restart recovery and rollback behaviour of the entitlement store."""
import os
import tempfile
import unittest

import helpers as h
from sabpuja_commerce.store import Store


class Restart(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.dir.name, "c.sqlite")

    def tearDown(self):
        self.dir.cleanup()

    def reopen(self, old):
        old.store.close()
        new = h.Harness(db_path=self.db)
        new.clock.t = old.clock.t
        return new

    def test_entitlements_quota_and_dedupe_survive_restart(self):
        a = h.Harness(db_path=self.db)
        a.paid()
        a.hook("orders/paid", h.order(), "wh-persist")
        cookie = a.login()
        a.generate(cookie)
        b = self.reopen(a)
        self.assertEqual(b.store.order_status(h.SHOP, 5001)["remaining"], 3)
        self.assertEqual(b.hook("orders/paid", h.order(), "wh-persist").json()["outcome"], "duplicate")
        self.assertEqual(b.generate(cookie).status, 200)   # session rows persist until expiry
        b.store.close()

    def test_crash_mid_render_releases_after_stale_window(self):
        a = h.Harness(db_path=self.db)
        a.paid()
        cookie = a.login()
        a.post("/api/generate", h.BIRTH, cookie=cookie)     # reservation taken, process "dies" before send
        b = self.reopen(a)
        self.assertEqual(b.generate(cookie).status, 409)
        b.clock.advance(300)
        self.assertEqual(b.generate(cookie).status, 200)
        self.assertEqual(b.store.order_status(h.SHOP, 5001)["used"], 1)
        b.store.close()

    def test_schema_creation_is_idempotent(self):
        Store(self.db, h.PEPPER).close()
        s = Store(self.db, h.PEPPER)
        self.assertEqual(s._db.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()[0], "1")
        s.close()

    def test_rollback_disable_switch(self):
        # Rollback step 1 is stopping the container; while stopped nothing is consumed. Simulated by an
        # unavailable renderer: every request is refused with 503 and the quota is untouched.
        from sabpuja_commerce.renderer import RendererUnavailable
        a = h.Harness(db_path=self.db)
        a.paid()
        cookie = a.login()
        a.render.fail = RendererUnavailable("rolled back")
        self.assertEqual([a.generate(cookie).status for _ in range(3)], [503, 503, 503])
        self.assertEqual(a.store.order_status(h.SHOP, 5001)["remaining"], 4)
        a.store.close()


if __name__ == "__main__":
    unittest.main()
