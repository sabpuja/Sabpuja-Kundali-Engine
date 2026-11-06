"""Settings file loading: secrets by file path only, example file shape, fail-closed validation."""
import json
from pathlib import Path
import tempfile
import unittest

import helpers as h
from sabpuja_commerce import config

EXAMPLE = Path(__file__).resolve().parents[1] / "deploy" / "commerce.example.json"


class Load(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        d = Path(self.dir.name)
        (d / "wh").write_bytes(h.SECRET)
        (d / "pp").write_bytes(h.PEPPER)
        raw = json.loads(EXAMPLE.read_text())
        raw.update(shop_domain=h.SHOP, public_origin=h.ORIGIN, webhook_secret_file=str(d / "wh"),
                   pepper_file=str(d / "pp"), db_path=":memory:")
        raw["products"][0].update(product_id=1, variant_id=2, sku="SBK-ESS-EN-1")
        self.raw, self.path = raw, d / "c.json"

    def tearDown(self):
        self.dir.cleanup()

    def load(self):
        self.path.write_text(json.dumps(self.raw))
        return config.load(str(self.path))

    def test_example_loads_when_filled_in(self):
        s = self.load()
        self.assertEqual((s.generations_per_unit, s.generation_window_days), (4, 30))
        self.assertEqual(s.trusted_proxies, ("127.0.0.1",))
        self.assertNotIn(h.SECRET.decode(), repr(s.admin_api_token))

    def test_example_placeholders_do_not_validate(self):
        with self.assertRaises(config.ConfigError):
            raw = json.loads(EXAMPLE.read_text())
            raw.update(webhook_secret_file=self.raw["webhook_secret_file"], pepper_file=self.raw["pepper_file"])
            self.path.write_text(json.dumps(raw))
            config.load(str(self.path))

    def test_inline_secret_refused(self):
        self.raw["webhook_secret"] = "inline"
        with self.assertRaises(TypeError):
            self.load()

    def test_empty_secret_file_refused(self):
        Path(self.raw["pepper_file"]).write_bytes(b"\n")
        with self.assertRaises(config.ConfigError):
            self.load()


if __name__ == "__main__":
    unittest.main()
