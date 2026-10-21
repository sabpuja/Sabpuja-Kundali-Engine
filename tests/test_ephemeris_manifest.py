"""Manifest gate tests with synthetic stand-in files (no Swiss data needed).

These prove only the file/hash gate; they say nothing about ephemeris accuracy.
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from sabpuja_kundali import ephemeris
from sabpuja_kundali.engine import calculate
from sabpuja_kundali.ephemeris import EphemerisDataError, load_manifest, verify_ephemeris_dir

SYNTHETIC = {
    "birth_datetime": "2000-01-01T17:30:00+05:30",
    "timezone": "Asia/Kolkata",
    "latitude": 28.6139,
    "longitude": 77.2090
}
CONTENT = {
    "sepl_18.se1": b"stand-in planets data",
    "semo_18.se1": b"stand-in moon data",
    "seas_18.se1": b"stand-in asteroid data",
}


def _entry(name, required):
    data = CONTENT[name]
    return {"name": name, "required": required, "size_bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


FAKE_MANIFEST = {
    "files": [_entry("sepl_18.se1", True), _entry("semo_18.se1", True)],
    "optional_files": [_entry("seas_18.se1", False)],
}


class ManifestGateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("SE_EPHE_PATH", None)

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, *names, overrides=None):
        for name in names:
            data = (overrides or {}).get(name, CONTENT[name])
            (self.dir / name).write_bytes(data)

    def assert_code(self, code):
        with self.assertRaises(EphemerisDataError) as ctx:
            verify_ephemeris_dir(str(self.dir), FAKE_MANIFEST)
        self.assertEqual(ctx.exception.code, code)
        self.assertIsInstance(ctx.exception, RuntimeError)
        return ctx.exception

    def test_full_required_set_passes(self):
        self.put("sepl_18.se1", "semo_18.se1")
        self.assertEqual(verify_ephemeris_dir(str(self.dir), FAKE_MANIFEST), self.dir.resolve())

    def test_full_set_with_optional_asteroid_file_passes(self):
        self.put("sepl_18.se1", "semo_18.se1", "seas_18.se1")
        verify_ephemeris_dir(str(self.dir), FAKE_MANIFEST)

    def test_planets_file_only_fails_d01(self):
        self.put("sepl_18.se1")
        err = self.assert_code("EPHEMERIS_FILE_MISSING")
        self.assertIn("semo_18.se1", str(err))

    def test_moon_file_only_fails(self):
        self.put("semo_18.se1")
        self.assertIn("sepl_18.se1", str(self.assert_code("EPHEMERIS_FILE_MISSING")))

    def test_asteroid_only_fails(self):
        self.put("seas_18.se1")
        self.assert_code("EPHEMERIS_FILE_MISSING")

    def test_unrelated_se1_files_do_not_satisfy_gate(self):
        (self.dir / "seplm18.se1").write_bytes(b"x")
        (self.dir / "semom18.se1").write_bytes(b"x")
        self.assert_code("EPHEMERIS_FILE_MISSING")

    def test_empty_folder_fails(self):
        self.assert_code("EPHEMERIS_FILE_MISSING")

    def test_missing_or_blank_path_fails(self):
        for value in ("", "   ", None, str(self.dir / "absent")):
            with self.assertRaises(EphemerisDataError) as ctx:
                verify_ephemeris_dir(value, FAKE_MANIFEST)
            self.assertEqual(ctx.exception.code, "EPHEMERIS_PATH_MISSING")

    def test_wrong_hash_moon_file_fails(self):
        same_size = bytes(len(CONTENT["semo_18.se1"]))
        self.put("sepl_18.se1", "semo_18.se1", overrides={"semo_18.se1": same_size})
        self.assert_code("EPHEMERIS_FILE_MISMATCH")

    def test_truncated_moon_file_fails(self):
        self.put("sepl_18.se1", "semo_18.se1", overrides={"semo_18.se1": CONTENT["semo_18.se1"][:-1]})
        self.assert_code("EPHEMERIS_FILE_MISMATCH")

    def test_directory_in_place_of_file_fails(self):
        self.put("sepl_18.se1")
        (self.dir / "semo_18.se1").mkdir()
        self.assert_code("EPHEMERIS_FILE_MISSING")

    def test_unreadable_file_fails(self):
        self.put("sepl_18.se1", "semo_18.se1")
        with mock.patch.object(ephemeris, "_sha256", side_effect=PermissionError("denied")):
            self.assert_code("EPHEMERIS_FILE_UNREADABLE")

    def test_se_ephe_path_override_fails(self):
        self.put("sepl_18.se1", "semo_18.se1")
        os.environ["SE_EPHE_PATH"] = str(self.dir)
        self.assert_code("EPHEMERIS_PATH_OVERRIDE")

    def test_calculate_fails_before_swiss_is_called(self):
        self.put("sepl_18.se1")
        with mock.patch("sabpuja_kundali.engine.verify_ephemeris_dir",
                        side_effect=lambda p: verify_ephemeris_dir(p, FAKE_MANIFEST)):
            with mock.patch.dict(sys.modules, {"swisseph": None}):
                # swisseph import would raise if reached; the gate must fire first.
                with self.assertRaises(EphemerisDataError):
                    calculate(SYNTHETIC, ephe_path=str(self.dir))


class PackagedManifestTests(unittest.TestCase):
    def test_required_set_is_planets_and_moon(self):
        manifest = load_manifest()
        required = {f["name"] for f in manifest["files"] if f["required"] is True}
        self.assertEqual(required, {"sepl_18.se1", "semo_18.se1"})
        self.assertTrue(all(f["required"] is False for f in manifest["optional_files"]))
        self.assertNotIn("seas_18.se1", required)

    def test_full_sha256_and_provenance_recorded(self):
        manifest = load_manifest()
        self.assertEqual(manifest["source"]["commit"], "c69c14adb7a0f94829586ffd92cd422aacb21e86")
        for f in manifest["files"] + manifest["optional_files"]:
            self.assertRegex(f["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(f["git_blob_sha1"], r"^[0-9a-f]{40}$")
            self.assertNotEqual(f["sha256"][:40], f["git_blob_sha1"])
            self.assertGreater(f["size_bytes"], 0)


class CliNegativeTests(unittest.TestCase):
    def test_cli_rejects_planets_only_folder_without_leaking_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Packaged manifest; a stand-in planets file cannot match its pinned hash.
            Path(tmp, "sepl_18.se1").write_bytes(b"stand-in")
            env = {k: v for k, v in os.environ.items() if k != "SE_EPHE_PATH"}
            env["SABPUJA_EPHE_PATH"] = tmp
            proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"],
                                  input=json.dumps(SYNTHETIC), capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")
        error = json.loads(proc.stderr)["error"]
        self.assertTrue(error.startswith("EPHEMERIS_FILE_MISMATCH: required file sepl_18.se1"))
        for secret in ("2000-01-01", "17:30", "28.6139", "77.209", "Asia/Kolkata"):
            self.assertNotIn(secret, proc.stderr)

    def test_cli_rejects_empty_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: v for k, v in os.environ.items() if k != "SE_EPHE_PATH"}
            env["SABPUJA_EPHE_PATH"] = tmp
            proc = subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"],
                                  input=json.dumps(SYNTHETIC), capture_output=True, text=True, env=env)
        self.assertEqual(proc.returncode, 2)
        self.assertTrue(re.match(r"^EPHEMERIS_FILE_MISSING: required file sepl_18.se1",
                                 json.loads(proc.stderr)["error"]))


class IntegrationGateTests(unittest.TestCase):
    """QA-002a-01: a requested real-data run must fail, never silently skip."""

    def run_integration(self, data_path):
        env = {k: v for k, v in os.environ.items() if k not in ("SE_EPHE_PATH", "SABPUJA_TEST_EPHE_PATH")}
        if data_path is not None:
            env["SABPUJA_TEST_EPHE_PATH"] = data_path
        return subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", str(Path(__file__).parent),
             "-p", "test_swiss_integration.py"],
            capture_output=True, text=True, env=env)

    def test_unset_path_skips(self):
        proc = self.run_integration(None)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("OK (skipped=8)", proc.stderr)

    def test_set_but_incomplete_path_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "sepl_18.se1").write_bytes(b"stand-in")
            proc = self.run_integration(tmp)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("is set but does not hold the pinned required files", proc.stderr)
        self.assertNotIn("skipped", proc.stderr)

    def test_set_but_empty_path_fails(self):
        proc = self.run_integration("")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("EPHEMERIS_PATH_MISSING", proc.stderr)
        self.assertNotIn("skipped", proc.stderr)


if __name__ == "__main__":
    unittest.main()
