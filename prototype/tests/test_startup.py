"""The server refuses to start unless every pinned resource verifies."""
import io
import os
import shutil
import socket
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from kundali_prototype import server
from kundali_prototype.places import PlaceFixtureError

from support import EPHE, requires_data


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class StartupFailsClosed(unittest.TestCase):
    def run_main(self, ephe):
        port = free_port()
        err = io.StringIO()
        with mock.patch.dict(os.environ, {"SABPUJA_EPHE_PATH": ephe}), redirect_stderr(err):
            code = server.main(["--port", str(port)])
        with socket.socket() as s:
            self.assertNotEqual(s.connect_ex(("127.0.0.1", port)), 0, "something is listening")
        return code, err.getvalue()

    def test_unset_and_wrong_path(self):
        for ephe in ("", "/nonexistent/ephe"):
            with self.subTest(ephe):
                code, err = self.run_main(ephe)
                self.assertEqual(code, 2)
                self.assertIn("EPHEMERIS_PATH_MISSING", err)
                self.assertNotIn("Traceback", err)

    def test_empty_dir(self):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp)
        code, err = self.run_main(tmp)
        self.assertEqual(code, 2)
        self.assertIn("EPHEMERIS_FILE_MISSING", err)
        self.assertNotIn(tmp, err)

    @requires_data
    def test_se_ephe_path_set(self):
        with mock.patch.dict(os.environ, {"SE_EPHE_PATH": EPHE}):
            with self.assertRaises(server.StartupError) as ctx:
                server.startup_verify(EPHE)
        self.assertEqual(ctx.exception.code, "EPHEMERIS_PATH_OVERRIDE")

    @requires_data
    def test_version_mismatch(self):
        for key, value in (("pyswisseph", "2.10.3.1"), ("swiss_library", "2.10.02"), ("tzdata", "2026.4")):
            with self.subTest(key):
                pins = dict(server.REQUIRED_VERSIONS, **{key: value})
                with mock.patch.object(server, "REQUIRED_VERSIONS", pins):
                    with self.assertRaises(server.StartupError) as ctx:
                        server.startup_verify(EPHE)
                self.assertIn(ctx.exception.code, ("SWISS_VERSION_MISMATCH", "TZDATA_VERSION_MISMATCH"))

    @requires_data
    def test_bad_fixture(self):
        with mock.patch.object(server, "load_places", side_effect=PlaceFixtureError("x")):
            with self.assertRaises(server.StartupError) as ctx:
                server.startup_verify(EPHE)
        self.assertEqual(ctx.exception.code, "PLACE_FIXTURE_INVALID")

    @requires_data
    def test_canary_failure(self):
        with mock.patch.object(server, "calculate", side_effect=RuntimeError("Swiss ephemeris files unavailable")):
            with self.assertRaises(server.StartupError) as ctx:
                server.startup_verify(EPHE)
        self.assertEqual(ctx.exception.code, "ENGINE_CANARY_FAILED")

    @requires_data
    def test_good_resources_start(self):
        places = server.startup_verify(EPHE)
        self.assertEqual(len(places), 12)


if __name__ == "__main__":
    unittest.main()
