"""Gate 3C (PKG-2): the fail-closed engine start-up preflight (readiness.py).

Every failure must give NOT_READY with a stable code, report the later checks as
NOT_RUN, never report READY, and stop a service before it accepts requests. The
result must carry no path, environment value or request value. Synthetic inputs only.

Most tests need the pinned data in SABPUJA_TEST_EPHE_PATH (unset skips, as in
test_swiss_integration); the ordering tests run without it.
"""
import contextlib
import json
import os
import shutil
import socket
import sys
import tempfile
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest import mock

from sabpuja_kundali import engine, provenance, readiness, timezones
from sabpuja_kundali.readiness import (CHECKS, FAIL, NOT_READY, NOT_RUN, PASS, READY, EngineNotReadyError,
                                       preflight, require_ready)

DATA_ENV = "SABPUJA_TEST_EPHE_PATH"
DATA = os.environ.get(DATA_ENV)
needs_data = unittest.skipIf(DATA is None, f"{DATA_ENV} unset: real-data readiness tests not requested")
TZ_MANIFEST = Path(timezones.__file__).with_name("tzif-manifest.json")


def start_service(ephe_path, listen):
    """The documented service start-up order: preflight first, listener only after READY."""
    require_ready(ephe_path)
    return listen()


class Isolated(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("SE_EPHE_PATH", None)
        os.environ.pop("SABPUJA_EPHE_PATH", None)

    def assertNotReady(self, result, check, code, cause=None):
        self.assertEqual(result.status, NOT_READY)
        self.assertFalse(result.ready)
        self.assertEqual(result.code, code)
        self.assertEqual(result.facts, ())
        statuses = [c.status for c in result.checks]
        index = CHECKS.index(check)
        self.assertEqual([c.name for c in result.checks], list(CHECKS))
        self.assertEqual(statuses, [PASS] * index + [FAIL] + [NOT_RUN] * (len(CHECKS) - index - 1))
        self.assertEqual((result.checks[index].code, result.checks[index].cause), (code, cause))
        self.assertPrivate(result)
        # No false READY: the raising form refuses too, with the same result.
        with mock.patch.object(readiness, "preflight", return_value=result):
            with self.assertRaises(EngineNotReadyError) as ctx:
                require_ready(DATA)
        self.assertEqual(str(ctx.exception), f"ENGINE_NOT_READY: {code}")
        self.assertIs(ctx.exception.result, result)

    def assertPrivate(self, result):
        text = json.dumps(result.as_dict())
        for secret in [p for p in (DATA, tempfile.gettempdir(), str(Path.home())) if p] + \
                ["Asia/Kolkata", "28.6139", "77.209", "2000-01-01", "17:30", "Traceback"]:
            self.assertNotIn(secret, text)


class OrderingTests(Isolated):
    """Run without data: the first failing check stops the preflight."""

    def test_missing_directory_stops_everything(self):
        for path in (None, "", "/nonexistent/sabpuja-ephemeris"):
            with self.subTest(path=path):
                calls = []
                with mock.patch.object(engine, "swiss_runtime", side_effect=lambda: calls.append(1)), \
                        mock.patch.object(engine, "calculate", side_effect=lambda *a, **k: calls.append(2)):
                    result = preflight(path)
                self.assertNotReady(result, "ephemeris_data", "EPHEMERIS_PATH_MISSING")
                self.assertEqual(calls, [])

    def test_forbidden_environment_override(self):
        os.environ["SE_EPHE_PATH"] = "/somewhere/else"
        self.assertNotReady(preflight("/nonexistent"), "ephemeris_data", "EPHEMERIS_PATH_OVERRIDE")

    def test_environment_default_is_the_engine_default(self):
        os.environ["SABPUJA_EPHE_PATH"] = "/nonexistent/from-environment"
        with mock.patch.object(readiness, "verify_ephemeris_dir", side_effect=RuntimeError("stop")) as gate:
            with self.assertRaises(RuntimeError):
                preflight()
        self.assertEqual(gate.call_args.args[0], "/nonexistent/from-environment")
        self.assertEqual(engine.ephemeris_path(), "/nonexistent/from-environment")

    def test_programming_defects_propagate_and_are_never_ready(self):
        for target in ("swiss_runtime", "calculate"):
            with self.subTest(target=target):
                with mock.patch.object(readiness, "verify_ephemeris_dir"), \
                        mock.patch.object(engine, target, side_effect=ZeroDivisionError("defect")), \
                        mock.patch.object(engine, "swiss_runtime" if target == "calculate" else "calculate"), \
                        mock.patch.object(readiness, "_timezone_data"), \
                        self.assertRaises(ZeroDivisionError):
                    preflight("/unused")

    def test_malformed_ephemeris_manifest_entries(self):
        # G3C-MAN-01: valid JSON with unusable entries is a typed NOT_READY, not a defect.
        from test_engine_hardening import MALFORMED_MANIFESTS, packaged_manifest_text
        with tempfile.TemporaryDirectory() as folder:
            for label, manifest in MALFORMED_MANIFESTS.items():
                with self.subTest(label):
                    calls = []
                    with packaged_manifest_text(json.dumps(manifest)), \
                            mock.patch.object(engine, "swiss_runtime", side_effect=lambda: calls.append(1)), \
                            mock.patch.object(engine, "calculate", side_effect=lambda *a, **k: calls.append(2)):
                        result = preflight(folder)
                    self.assertNotReady(result, "ephemeris_data", "EPHEMERIS_MANIFEST_INVALID")
                    self.assertNotIn(folder, json.dumps(result.as_dict()))
                    self.assertEqual(calls, [])

    def test_service_does_not_listen_after_a_failure(self):
        listened = []
        with self.assertRaises(EngineNotReadyError):
            start_service("/nonexistent/sabpuja-ephemeris", lambda: listened.append(True))
        self.assertEqual(listened, [])


@needs_data
class ReadinessTests(Isolated):
    def test_all_resources_valid(self):
        result = preflight(DATA)
        self.assertEqual(result.status, READY, result.as_dict())
        self.assertTrue(result.ready)
        self.assertIsNone(result.code)
        self.assertEqual([(c.name, c.status, c.code) for c in result.checks], [(n, PASS, None) for n in CHECKS])
        facts = dict(result.facts)
        self.assertEqual(facts["swiss_library_version"], "2.10.03")
        self.assertEqual(facts["swiss_binding_version"], "2.10.3.2")
        self.assertEqual(facts["tzdata_package_version"], "2026.5")
        self.assertEqual(facts["tzdata_iana_version"], "2026e")
        self.assertEqual(facts["tzdata_zones_verified"], len(json.loads(TZ_MANIFEST.read_text())["zones"]))
        self.assertEqual(facts["chart_schema_version"], "0.3.0")  # Gate 3E proposed candidate; baseline_projection gives 0.2.0
        self.assertEqual(facts["metadata_schema"], "sabpuja-calculation-metadata/3")
        self.assertEqual(facts["ephemeris_required_files"], ["semo_18.se1", "sepl_18.se1"])
        self.assertPrivate(result)
        self.assertIs(require_ready(DATA).status, READY)

    def test_environment_variable_supplies_the_directory(self):
        os.environ["SABPUJA_EPHE_PATH"] = DATA
        self.assertTrue(preflight().ready)

    def test_missing_ephemeris_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(Path(DATA, "sepl_18.se1"), tmp)
            self.assertNotReady(preflight(tmp), "ephemeris_data", "EPHEMERIS_FILE_MISSING")

    def test_corrupted_ephemeris_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(Path(DATA, "sepl_18.se1"), tmp)
            data = bytearray(Path(DATA, "semo_18.se1").read_bytes())
            data[len(data) // 3] ^= 0x01
            Path(tmp, "semo_18.se1").write_bytes(bytes(data))
            self.assertNotReady(preflight(tmp), "ephemeris_data", "EPHEMERIS_FILE_MISMATCH")

    def test_forbidden_environment_override_with_valid_data(self):
        os.environ["SE_EPHE_PATH"] = DATA  # even pointing at the verified files
        self.assertNotReady(preflight(DATA), "ephemeris_data", "EPHEMERIS_PATH_OVERRIDE")

    def test_corrupted_packaged_ephemeris_manifest(self):
        from sabpuja_kundali import ephemeris
        resource = mock.Mock()
        resource.read_text.return_value = "{not json"
        with mock.patch.object(ephemeris.resources, "files") as files:
            files.return_value.joinpath.return_value = resource
            self.assertNotReady(preflight(DATA), "ephemeris_data", "EPHEMERIS_MANIFEST_INVALID")

    def test_wrong_or_missing_binding(self):
        cases = ((mock.patch.object(provenance, "binding_distribution_version", return_value="2.10.3.1"),
                  "SWISS_BINDING_VERSION_MISMATCH"),
                 (mock.patch.object(provenance, "binding_distribution_version", return_value=None),
                  "SWISS_BINDING_METADATA_MISSING"),
                 (mock.patch.dict(sys.modules, {"swisseph": None}), "SWISS_BINDING_MISSING"))
        for patch, code in cases:
            with self.subTest(code=code), patch:
                self.assertNotReady(preflight(DATA), "swiss_runtime", code)

    def test_wrong_library_version(self):
        import swisseph
        with mock.patch.object(swisseph, "version", "2.10.04"):
            self.assertNotReady(preflight(DATA), "swiss_runtime", "SWISS_LIBRARY_VERSION_MISMATCH")

    def test_corrupted_timezone_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp, "tzif-manifest.json")
            for content, code in (("{not json", "TZDATA_MANIFEST_INVALID"),
                                  (TZ_MANIFEST.read_text().replace('"2026e"', '"2026f"', 1), "TZDATA_MANIFEST_INVALID")):
                with self.subTest(code=code):
                    bad.write_text(content)
                    with mock.patch.object(timezones, "_manifest_resource", return_value=bad):
                        self.assertNotReady(preflight(DATA), "timezone_data", code)
            with mock.patch.object(timezones, "_manifest_resource", return_value=Path(tmp, "absent.json")):
                self.assertNotReady(preflight(DATA), "timezone_data", "TZDATA_MANIFEST_MISSING")

    def test_corrupted_or_missing_timezone_file(self):
        import tzdata
        for key, code in (("Pacific/Chatham", "TZDATA_FILE_MISMATCH"), ("America/Nuuk", "TZDATA_FILE_MISSING")):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                name = f"tzdata_readiness_{code.lower()}"
                pkg = Path(tmp, name)
                shutil.copytree(Path(tzdata.__file__).parent, pkg)
                target = pkg.joinpath("zoneinfo", *key.split("/"))
                if code == "TZDATA_FILE_MISSING":
                    target.unlink()
                else:
                    data = bytearray(target.read_bytes())
                    data[-3] ^= 0x01
                    target.write_bytes(bytes(data))
                sys.path.insert(0, tmp)
                try:
                    fresh = lambda: timezones.PinnedZoneLoader(timezones.load_manifest(), package=name)
                    with mock.patch.object(readiness, "_fresh_zone_loader", fresh):
                        result = preflight(DATA)
                finally:
                    sys.path.remove(tmp)
                    for module in [m for m in sys.modules if m == name or m.startswith(name + ".")]:
                        sys.modules.pop(module)
                self.assertNotReady(result, "timezone_data", code)
                self.assertNotIn(key, json.dumps(result.as_dict()))

    def test_timezone_package_missing_or_not_the_pin(self):
        absent = lambda: timezones.PinnedZoneLoader(timezones.load_manifest(), package="sabpuja_absent_tzdata")
        with mock.patch.object(readiness, "_fresh_zone_loader", absent):
            self.assertNotReady(preflight(DATA), "timezone_data", "TZDATA_PACKAGE_MISSING")
        with mock.patch.object(readiness, "REQUIRED_TZDATA_VERSION", "2026.4"):
            self.assertNotReady(preflight(DATA), "timezone_data", "TZDATA_VERSION_MISMATCH")
        import tzdata
        with mock.patch.object(tzdata, "__version__", "2026.6"):
            self.assertNotReady(preflight(DATA), "timezone_data", "TZDATA_VERSION_MISMATCH")

    def test_failed_synthetic_canary(self):
        import swisseph as swe
        real_calc = swe.calc_ut

        def moshier(jd, body, flags):
            pos, got = real_calc(jd, body, flags)
            return pos, got & ~swe.FLG_SWIEPH

        cases = ((mock.patch.object(swe, "calc_ut", moshier), "SWISS_EPHEMERIS_FALLBACK_REFUSED"),
                 (mock.patch.object(swe, "houses_ex", side_effect=swe.Error("/srv/x")), "ASCENDANT_UNCOMPUTABLE"),
                 (mock.patch.object(readiness, "CANARY_REQUEST", {**readiness.CANARY_REQUEST, "latitude": 70.0}),
                  "LATITUDE_OUTSIDE_SUPPORTED_BAND"))
        for patch, cause in cases:
            with self.subTest(cause=cause), patch:
                self.assertNotReady(preflight(DATA), "canary_calculation", "ENGINE_CANARY_FAILED", cause)

    def test_output_contract_mismatch(self):
        real = engine.calculate(dict(readiness.CANARY_REQUEST), ephe_path=DATA)
        meta = real["calculation_metadata"]

        def altered(**changes):
            chart = json.loads(json.dumps(real))
            for path, value in changes.items():
                node = chart
                *parents, leaf = path.split(".")
                for key in parents:
                    node = node[key]
                if value is None:
                    del node[leaf]
                else:
                    node[leaf] = value
            return chart

        cases = ((altered(schema_version="0.1.0"), "ENGINE_SCHEMA_MISMATCH"),
                 (altered(**{"calculation_metadata.metadata_schema": "sabpuja-calculation-metadata/2"}),
                  "ENGINE_SCHEMA_MISMATCH"),
                 (altered(calculation_metadata=None), "ENGINE_SCHEMA_MISMATCH"),
                 (altered(**{"planets.ketu_mean": None}), "ENGINE_SCHEMA_MISMATCH"),
                 (altered(**{"calculation_metadata.swiss_ephemeris.library_version": "2.10.04"}),
                  "ENGINE_PROVENANCE_MISMATCH"),
                 (altered(**{"calculation_metadata.swiss_ephemeris.python_binding_version": None}),
                  "ENGINE_PROVENANCE_MISMATCH"),
                 (altered(**{"calculation_metadata.timezone_data.package_version": "2026.4"}),
                  "ENGINE_PROVENANCE_MISMATCH"),
                 (altered(**{"calculation_metadata.ephemeris_data.manifest_sha256": "0" * 64}),
                  "ENGINE_PROVENANCE_MISMATCH"))
        self.assertEqual(meta["metadata_schema"], "sabpuja-calculation-metadata/3")
        for chart, code in cases:
            with self.subTest(code=code), mock.patch.object(engine, "calculate", return_value=chart):
                self.assertNotReady(preflight(DATA), "output_contract", code)

    def test_preflight_does_not_change_the_next_chart(self):
        before = json.dumps(engine.calculate(dict(readiness.CANARY_REQUEST), ephe_path=DATA), sort_keys=True)
        self.assertTrue(preflight(DATA).ready)
        with tempfile.TemporaryDirectory() as empty:
            self.assertFalse(preflight(empty).ready)
        with mock.patch.object(provenance, "binding_distribution_version", return_value="0"):
            self.assertFalse(preflight(DATA).ready)
        after = json.dumps(engine.calculate(dict(readiness.CANARY_REQUEST), ephe_path=DATA), sort_keys=True)
        self.assertEqual(before, after)
        self.assertTrue(preflight(DATA).ready)

    def test_failure_happens_before_a_listener_exists(self):
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(204)
                self.end_headers()

            def log_message(self, *args):
                pass

        servers = []

        def listen():
            server = HTTPServer(("127.0.0.1", 0), Handler)
            servers.append(server)
            return server

        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(EngineNotReadyError) as ctx:
                start_service(empty, listen)
        self.assertEqual(ctx.exception.result.code, "EPHEMERIS_FILE_MISSING")
        self.assertEqual(servers, [])  # no socket was ever bound
        with mock.patch.object(provenance, "binding_distribution_version", return_value=None), \
                self.assertRaises(EngineNotReadyError):
            start_service(DATA, listen)
        self.assertEqual(servers, [])
        server = start_service(DATA, listen)  # READY: only now is a port bound
        try:
            self.assertEqual(len(servers), 1)
            with socket.create_connection(server.server_address, timeout=5):
                pass
        finally:
            server.server_close()

    def test_documented_service_integration_path(self):
        # What a future service needs, through public names only: preflight, calculate,
        # the typed error tuple and its codes; defects are not caught.
        require_ready(DATA)

        def handle(request):
            try:
                return 200, engine.calculate(request, ephe_path=DATA)
            except engine.EXPECTED_ERRORS as exc:
                return (422 if isinstance(exc, engine.InputRefusalError) else 503), {"error": exc.code}

        status, chart = handle(dict(readiness.CANARY_REQUEST))
        self.assertEqual((status, chart["schema_version"]), (200, "0.3.0"))  # Gate 3E proposed candidate; baseline_projection gives 0.2.0
        self.assertEqual(handle({**readiness.CANARY_REQUEST, "latitude": 70.0}),
                         (422, {"error": "LATITUDE_OUTSIDE_SUPPORTED_BAND"}))
        with mock.patch.object(provenance, "binding_distribution_version", return_value="2.10.3.1"):
            self.assertEqual(handle(dict(readiness.CANARY_REQUEST)), (503, {"error": "SWISS_BINDING_VERSION_MISMATCH"}))
        with mock.patch.object(engine, "_placement", side_effect=ZeroDivisionError), \
                self.assertRaises(ZeroDivisionError):
            handle(dict(readiness.CANARY_REQUEST))


if __name__ == "__main__":
    unittest.main()
