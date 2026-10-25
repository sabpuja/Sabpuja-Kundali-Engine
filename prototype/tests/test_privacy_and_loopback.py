"""Run the real server process: loopback-only listener, no output or files from requests."""
import http.client
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

from kundali_prototype import server

from support import EPHE, requires_data

ROOT = Path(__file__).resolve().parents[2]
MARKERS = ("1983-03-14", "04:44:44", "in-lucknow")


def non_loopback_addresses():
    addrs = set()
    try:
        out = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5).stdout.split()
        addrs.update(a for a in out if not a.startswith("127.") and ":" not in a)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            addr = s.getsockname()[0]
            if not addr.startswith("127."):
                addrs.add(addr)
    except OSError:
        pass
    return sorted(addrs)


def listening_entries(port):
    """(local address hex, port) rows in LISTEN state from /proc/net/tcp and tcp6."""
    rows = []
    for name in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            lines = Path(name).read_text().splitlines()[1:]
        except OSError:
            continue
        for line in lines:
            parts = line.split()
            addr, p = parts[1].rsplit(":", 1)
            if int(p, 16) == port and parts[3] == "0A":
                rows.append((name, addr))
    return rows


class LoopbackConstants(unittest.TestCase):
    def test_host_is_fixed(self):
        self.assertEqual(server.HOST, "127.0.0.1")
        import inspect
        self.assertNotIn("host", inspect.signature(server.PrototypeServer.__init__).parameters)
        self.assertNotIn("--host", inspect.getsource(server.main))

    def test_in_process_socket_is_loopback(self):
        srv = server.PrototypeServer(0, "", {})
        try:
            self.assertEqual(srv.socket.getsockname()[0], "127.0.0.1")
            self.assertEqual(srv.socket.family, socket.AF_INET)
        finally:
            srv.server_close()

    def test_source_has_no_logging_storage_or_network_client(self):
        src = (ROOT / "prototype" / "kundali_prototype" / "server.py").read_text()
        for word in ("import logging", "sqlite", "urllib", "import requests", "open(", ".write_text", "pickle", "shelve",
                     "socket.create_connection", "http.client", "print(body", "traceback"):
            self.assertNotIn(word, src, word)


@requires_data
class RealProcess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            cls.port = s.getsockname()[1]
        env = {"PATH": os.environ.get("PATH", ""), "HOME": cls.tmp, "TMPDIR": cls.tmp,
               "SABPUJA_EPHE_PATH": EPHE, "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'prototype'}",
               "PYTHONDONTWRITEBYTECODE": "1"}
        cls.proc = subprocess.Popen([sys.executable, "-m", "kundali_prototype", "--port", str(cls.port)],
                                    cwd=cls.tmp, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        cls.banner = cls.proc.stdout.readline().decode()
        deadline = time.time() + 60
        while time.time() < deadline:
            with socket.socket() as s:
                if s.connect_ex(("127.0.0.1", cls.port)) == 0:
                    break
            time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)
        import shutil
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def post(self, body):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=30)
        conn.request("POST", "/api/chart", json.dumps(body),
                     {"Content-Type": "application/json", "Host": f"127.0.0.1:{self.port}"})
        resp = conn.getresponse()
        data = resp.read()
        conn.close()
        return resp.status, data

    def test_1_banner_names_loopback_only(self):
        self.assertIn("http://127.0.0.1:", self.banner)

    def test_2_listener_is_loopback_only(self):
        rows = listening_entries(self.port)
        self.assertTrue(rows, "no listening socket found in /proc/net/tcp")
        self.assertEqual({addr for _, addr in rows}, {"0100007F"})  # 127.0.0.1, IPv4 only

    def test_3_not_reachable_on_other_interfaces(self):
        addrs = non_loopback_addresses()
        if not addrs:
            self.skipTest("no non-loopback IPv4 address on this host")
        for addr in addrs:
            with self.subTest(addr), socket.socket() as s:
                s.settimeout(3)
                self.assertNotEqual(s.connect_ex((addr, self.port)), 0)

    def test_4_requests_leave_no_output_or_files(self):
        before = sorted(p.name for p in Path(self.tmp).rglob("*"))
        good = {"place_id": "in-lucknow", "birth_date": "1983-03-14", "birth_time": "04:44:44"}
        self.assertEqual(self.post(good)[0], 200)
        self.assertEqual(self.post(dict(good, birth_date="1983-02-30"))[0], 422)
        self.assertEqual(self.post(dict(good, birth_date="1963-03-14"))[0], 422)
        self.assertEqual(self.post(dict(good, extra="x"))[0], 400)
        after = sorted(p.name for p in Path(self.tmp).rglob("*"))
        self.assertEqual(before, after)
        self.proc.terminate()
        out, err = self.proc.communicate(timeout=10)
        text = (out + err).decode()
        for marker in MARKERS + ("Traceback",):
            self.assertNotIn(marker, text)
        type(self).proc = subprocess.Popen(["true"])  # tearDown target


if __name__ == "__main__":
    unittest.main()
