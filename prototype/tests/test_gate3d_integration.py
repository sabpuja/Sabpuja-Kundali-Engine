"""Gate 3D: the prototype on the hardened engine (PR #39 + PR #40).

Start-up must run the engine's own readiness.require_ready() before any socket
exists, and refuse with a stable code and no path. Request errors follow one
rule: client refusals stay 422/409, typed server faults are 503, anything else
is a fixed 500. No failure returns a chart or leaks the request, and none
changes the next valid chart. Synthetic inputs only.
"""
import io
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

from sabpuja_kundali import engine, ephemeris, provenance, readiness, timezones
from sabpuja_kundali.engine import ChartComputationError, InputRefusalError, UnsupportedInputError
from sabpuja_kundali.ephemeris import EphemerisDataError
from sabpuja_kundali.timezones import TimezoneDataError
from kundali_prototype import server
from kundali_prototype.places import load_places

from support import EPHE, SYNTHETIC, requires_data

ROOT = Path(__file__).resolve().parents[2]
PLACES = load_places()
GOOD = {"place_id": "in-new-delhi", "birth_date": "1990-05-15", "birth_time": "10:30"}
SWISS_RUNTIME = ("SWISS_BINDING_MISSING", "SWISS_LIBRARY_VERSION_MISMATCH", "SWISS_BINDING_METADATA_MISSING",
                 "SWISS_BINDING_VERSION_MISMATCH", "SWISS_EPHEMERIS_FALLBACK_REFUSED")
# Values from the request, the server and Swiss that a server-fault response must never contain.
LEAKS = ("1990-05-15", "10:30", "28.6", "77.2", "Asia/Kolkata", "New Delhi", "/home", "/tmp", "/srv",
         "Traceback", "secret", "swisseph", "2.10.0", "2.10.3")


def post(body, ephe=None):
    return server.handle_chart(json.dumps(body).encode(), PLACES, EPHE if ephe is None else ephe)


def moshier_after(bodies_ok):
    """A calc_ut that drops FLG_SWIEPH after `bodies_ok` real calls (a real Moshier fallback)."""
    import swisseph as swe
    real = swe.calc_ut
    calls = []

    def fake(jd, body, flags):
        pos, got = real(jd, body, flags)
        calls.append(body)
        return (pos, got & ~swe.FLG_SWIEPH) if len(calls) > bodies_ok else (pos, got)
    return fake


class Isolated(unittest.TestCase):
    def setUp(self):
        env = mock.patch.dict(os.environ)
        env.start()
        self.addCleanup(env.stop)
        os.environ.pop("SE_EPHE_PATH", None)
        os.environ.pop("SABPUJA_EPHE_PATH", None)


class StartupUsesEngineReadiness(Isolated):
    """Workstream A: one readiness authority, before any listener."""

    def run_main(self, ephe):
        """Run main() with a recorder; serve_forever stops at once. Returns (exit, stderr, events)."""
        events = []
        real_ready, real_bind = readiness.require_ready, server.PrototypeServer.server_bind

        def ready(path):
            events.append(("require_ready", path))
            result = real_ready(path)
            events.append(("ready", result.status))
            return result

        def bind(srv):
            events.append(("bind", None))
            return real_bind(srv)

        err = io.StringIO()
        os.environ["SABPUJA_EPHE_PATH"] = ephe
        with mock.patch.object(readiness, "require_ready", side_effect=ready), \
                mock.patch.object(server.PrototypeServer, "server_bind", bind), \
                mock.patch.object(server.PrototypeServer, "serve_forever", side_effect=KeyboardInterrupt), \
                mock.patch("sys.stdout", io.StringIO()), redirect_stderr(err):
            code = server.main(["--port", "0"])
        return code, err.getvalue(), events

    def assertRefused(self, ephe, code, check, cause=None):
        status, err, events = self.run_main(ephe)
        self.assertEqual(status, 2)
        self.assertNotIn(("bind", None), events, "a socket was opened after a readiness failure")
        report = json.loads(err.strip().splitlines()[-1])
        expected = {"error": code, "check": check, "message": "prototype not started; nothing is listening"}
        if cause:
            expected["cause"] = cause
        self.assertEqual(report, expected)
        for leak in [p for p in (ephe, tempfile.gettempdir(), str(Path.home())) if p] + ["Traceback"]:
            self.assertNotIn(leak, err)
        return report

    def test_wrapper_has_no_second_engine_check(self):
        for name in ("REQUIRED_VERSIONS", "CANARY_REQUEST", "verify_ephemeris_dir", "default_loader", "metadata"):
            self.assertFalse(hasattr(server, name), name)
        source = Path(server.__file__).read_text()
        for literal in ("2.10.03", "2.10.3.2", "2026.5", "verify_all", "28.6139"):
            self.assertNotIn(literal, source)
        self.assertIn("readiness.require_ready(ephe_path)", source)

    def test_unset_path_is_refused_by_readiness(self):
        self.assertRefused("", "EPHEMERIS_PATH_MISSING", "ephemeris_data")

    @requires_data
    def test_1_valid_startup_is_ready_before_any_socket(self):
        status, err, events = self.run_main(EPHE)
        self.assertEqual(status, 0, err)
        # The same resolved path the requests use, READY, and only then the bind.
        self.assertEqual(events, [("require_ready", EPHE), ("ready", readiness.READY), ("bind", None)])
        self.assertEqual(err, "")

    @requires_data
    def test_2_missing_swiss_dependencies_prevent_startup(self):
        with mock.patch.dict(sys.modules, {"swisseph": None}):
            self.assertRefused(EPHE, "SWISS_BINDING_MISSING", "swiss_runtime")
        with mock.patch.object(provenance, "binding_distribution_version", return_value=None):
            self.assertRefused(EPHE, "SWISS_BINDING_METADATA_MISSING", "swiss_runtime")

    @requires_data
    def test_3_wrong_swiss_versions_prevent_startup(self):
        import swisseph
        with mock.patch.object(swisseph, "version", "2.10.04"):
            self.assertRefused(EPHE, "SWISS_LIBRARY_VERSION_MISMATCH", "swiss_runtime")
        with mock.patch.object(provenance, "binding_distribution_version", return_value="2.10.3.1"):
            self.assertRefused(EPHE, "SWISS_BINDING_VERSION_MISMATCH", "swiss_runtime")

    @requires_data
    def test_4_corrupt_ephemeris_data_prevents_startup(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(Path(EPHE, "sepl_18.se1"), tmp)
            data = bytearray(Path(EPHE, "semo_18.se1").read_bytes())
            data[len(data) // 2] ^= 0x01
            Path(tmp, "semo_18.se1").write_bytes(bytes(data))
            self.assertRefused(tmp, "EPHEMERIS_FILE_MISMATCH", "ephemeris_data")
            Path(tmp, "semo_18.se1").unlink()
            self.assertRefused(tmp, "EPHEMERIS_FILE_MISSING", "ephemeris_data")
        os.environ["SE_EPHE_PATH"] = EPHE
        self.assertRefused(EPHE, "EPHEMERIS_PATH_OVERRIDE", "ephemeris_data")

    @requires_data
    def test_5_corrupt_timezone_data_prevents_startup(self):
        manifest = Path(timezones.__file__).with_name("tzif-manifest.json")
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp, "tzif-manifest.json")
            bad.write_text(manifest.read_text().replace('"2026e"', '"2026f"', 1))
            with mock.patch.object(timezones, "_manifest_resource", return_value=bad):
                self.assertRefused(EPHE, "TZDATA_MANIFEST_INVALID", "timezone_data")
        import tzdata
        with mock.patch.object(tzdata, "__version__", "2026.6"):
            self.assertRefused(EPHE, "TZDATA_VERSION_MISMATCH", "timezone_data")

    @requires_data
    def test_6_malformed_manifest_entries_are_a_controlled_failure(self):
        for files in ([None], [{"required": True}], [{"required": True, "name": "../x", "size_bytes": 1,
                                                       "sha256": "0" * 64}]):
            with self.subTest(files=files):
                resource = mock.Mock()
                resource.read_text.return_value = json.dumps({"files": files})
                with mock.patch.object(ephemeris.resources, "files") as found:
                    found.return_value.joinpath.return_value = resource
                    self.assertRefused(EPHE, "EPHEMERIS_MANIFEST_INVALID", "ephemeris_data")

    @requires_data
    def test_failed_canary_names_its_engine_cause(self):
        import swisseph
        with mock.patch.object(swisseph, "calc_ut", moshier_after(0)):
            self.assertRefused(EPHE, "ENGINE_CANARY_FAILED", "canary_calculation", "SWISS_EPHEMERIS_FALLBACK_REFUSED")

    @requires_data
    def test_readiness_defect_is_not_disguised(self):
        # An untyped error inside readiness is a defect: it propagates (exit 1 with a
        # traceback at the console), is never reported as a readiness code, and nothing listens.
        with mock.patch.object(readiness, "_timezone_data", side_effect=KeyError("package_version")):
            with self.assertRaises(KeyError):
                self.run_main(EPHE)

    def test_real_process_exit_code_and_no_listener(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": f"{ROOT / 'src'}:{ROOT / 'prototype'}",
               "SABPUJA_EPHE_PATH": "/nonexistent/sabpuja-ephe", "PYTHONDONTWRITEBYTECODE": "1"}
        proc = subprocess.run([sys.executable, "-m", "kundali_prototype", "--port", str(port)], env=env,
                              capture_output=True, text=True, timeout=120)
        self.assertEqual((proc.returncode, proc.stdout), (2, ""))
        self.assertEqual(json.loads(proc.stderr), {"error": "EPHEMERIS_PATH_MISSING", "check": "ephemeris_data",
                                                   "message": "prototype not started; nothing is listening"})
        with socket.socket() as s:
            self.assertNotEqual(s.connect_ex(("127.0.0.1", port)), 0)


class ClassificationRule(unittest.TestCase):
    """Workstream B: one explicit rule, independent of any request."""

    def test_rule(self):
        D = "SECRET-DETAIL /home/user 1990-05-15"
        cases = [
            (server.FormError(400, "REQUEST_INVALID", "m"), (400, "REQUEST_INVALID", "input")),
            (server.FormError(409, "TIME_AMBIGUOUS_LOCAL", "m", "ambiguous"), (409, "TIME_AMBIGUOUS_LOCAL", "ambiguous")),
            (InputRefusalError("TIME_FORMAT_INVALID", "fixed"), (422, "TIME_FORMAT_INVALID", "input")),
            (UnsupportedInputError("LATITUDE_OUTSIDE_SUPPORTED_BAND", "fixed"),
             (422, "LATITUDE_OUTSIDE_SUPPORTED_BAND", "unsupported")),
            (EphemerisDataError("EPHEMERIS_FILE_MISMATCH", D), (503, "EPHEMERIS_FILE_MISMATCH", "resources")),
            (TimezoneDataError("TZDATA_FILE_MISMATCH", D), (503, "TZDATA_FILE_MISMATCH", "resources")),
            (ChartComputationError("ASCENDANT_UNCOMPUTABLE", D), (503, "ASCENDANT_UNCOMPUTABLE", "computation")),
            (ChartComputationError("SWISS_PLANET_CALCULATION_FAILED", D),
             (503, "SWISS_PLANET_CALCULATION_FAILED", "computation")),
            (server.InvariantError(D), (500, "INTERNAL_ERROR", "internal")),
            (RuntimeError(D), (500, "INTERNAL_ERROR", "internal")),
            (ValueError(D), (500, "INTERNAL_ERROR", "internal")),
            (KeyError(D), (500, "INTERNAL_ERROR", "internal")),
        ] + [(ChartComputationError(code, D), (503, code, "resources")) for code in SWISS_RUNTIME]
        for exc, (status, code, category) in cases:
            with self.subTest(exc=repr(exc)):
                got = server.classify(exc)
                self.assertEqual((got[0], got[1], got[3]), (status, code, category))
                if status >= 500:
                    self.assertNotIn(D, got[2])

    def test_every_typed_engine_error_is_classified_and_server_faults_are_5xx(self):
        for cls in engine.EXPECTED_ERRORS:
            status = server.classify(cls("SOME_CODE", "detail"))[0]
            self.assertEqual(status, 422 if issubclass(cls, InputRefusalError) else 503, cls)

    def test_swiss_runtime_codes_are_engine_codes(self):
        source = Path(engine.__file__).read_text()
        self.assertEqual(server.SWISS_RUNTIME_CODES, frozenset(SWISS_RUNTIME))
        for code in SWISS_RUNTIME:
            self.assertIn(f'"{code}"', source)


@requires_data
class RequestFaults(unittest.TestCase):
    """Real engine faults through handle_chart: status, envelope, no chart, no contamination."""

    @classmethod
    def setUpClass(cls):
        status, body = post(GOOD)
        assert status == 200, body
        cls.reference = json.dumps(body, sort_keys=True)

    def assertServerFault(self, result, status, code, category):
        got_status, body = result
        self.assertEqual(got_status, status, body)
        self.assertEqual(list(body), ["error"])  # 11: never a partial chart or echoed input
        self.assertEqual(sorted(body["error"]), ["category", "code", "message"])
        self.assertEqual((body["error"]["code"], body["error"]["category"]), (code, category))
        text = json.dumps(body)
        for leak in LEAKS:
            self.assertNotIn(leak, text)
        # 12: the next valid request gives the same chart as before the fault.
        self.assertEqual(json.dumps(post(GOOD)[1], sort_keys=True), self.reference)

    def test_7_swiss_runtime_errors_are_503(self):
        import swisseph
        cases = ((mock.patch.dict(sys.modules, {"swisseph": None}), "SWISS_BINDING_MISSING"),
                 (mock.patch.object(swisseph, "version", "2.10.04"), "SWISS_LIBRARY_VERSION_MISMATCH"),
                 (mock.patch.object(provenance, "binding_distribution_version", return_value=None),
                  "SWISS_BINDING_METADATA_MISSING"),
                 (mock.patch.object(provenance, "binding_distribution_version", return_value="2.10.3.1"),
                  "SWISS_BINDING_VERSION_MISMATCH"))
        for patch, code in cases:
            with self.subTest(code=code):
                with patch:
                    result = post(GOOD)
                self.assertServerFault(result, 503, code, "resources")

    def test_7_moshier_fallback_on_any_body_is_503_with_no_partial_chart(self):
        import swisseph
        for ok in range(8):  # SUN..SATURN and MEAN_NODE: eight calc_ut calls
            with self.subTest(bodies_before_fault=ok):
                with mock.patch.object(swisseph, "calc_ut", moshier_after(ok)):
                    result = post(GOOD)
                self.assertServerFault(result, 503, "SWISS_EPHEMERIS_FALLBACK_REFUSED", "resources")

    def test_other_calculation_failures_are_503(self):
        import swisseph
        with mock.patch.object(swisseph, "houses_ex", side_effect=swisseph.Error("/srv/secret")):
            result = post(GOOD)
        self.assertServerFault(result, 503, "ASCENDANT_UNCOMPUTABLE", "computation")
        with mock.patch.object(swisseph, "calc_ut", side_effect=swisseph.Error("/srv/secret")):
            result = post(GOOD)
        self.assertServerFault(result, 503, "SWISS_PLANET_CALCULATION_FAILED", "computation")

    def test_data_verification_failures_are_503(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = post(GOOD, ephe=tmp)
        self.assertServerFault(result, 503, "EPHEMERIS_FILE_MISSING", "resources")
        with mock.patch.object(server, "get_zone", side_effect=TimezoneDataError("TZDATA_FILE_MISMATCH", "/srv/x")):
            result = post(GOOD)
        self.assertServerFault(result, 503, "TZDATA_FILE_MISMATCH", "resources")

    def test_8_input_refusals_are_still_422(self):
        cases = [({"place_id": "in-mumbai", "birth_date": "1969-12-31", "birth_time": "23:59"},
                  "HISTORICAL_CLOCK_UNVERIFIED", "unsupported"),
                 ({"place_id": "no-tromso", "birth_date": "1990-05-15", "birth_time": "10:30"},
                  "LATITUDE_OUTSIDE_SUPPORTED_BAND", "unsupported"),
                 ({"place_id": "gb-london", "birth_date": "2020-03-29", "birth_time": "01:30"},
                  "TIME_NONEXISTENT_LOCAL", "input"),
                 ({"place_id": "in-mumbai", "birth_date": "1990-02-30", "birth_time": "10:30"},
                  "BIRTH_DATE_INVALID", "input"),
                 ({"place_id": "in-mumbai", "birth_date": "1990-05-15", "birth_time": ""},
                  "BIRTH_TIME_REQUIRED", "unknown_time")]
        for body, code, category in cases:
            with self.subTest(code=code):
                status, out = post(body)
                self.assertEqual((status, out["error"]["code"], out["error"]["category"]), (422, code, category))
                self.assertNotIn("chart", out)

    def test_input_refusal_precedes_a_broken_swiss_runtime(self):
        # Unchanged precedence: the request is refused as input before the runtime is consulted.
        with mock.patch.dict(sys.modules, {"swisseph": None}):
            status, out = post({"place_id": "no-tromso", "birth_date": "1990-05-15", "birth_time": "10:30"})
        self.assertEqual((status, out["error"]["code"]), (422, "LATITUDE_OUTSIDE_SUPPORTED_BAND"))

    def test_9_repeated_hour_is_409_then_the_choice_charts(self):
        fold = {"place_id": "gb-london", "birth_date": "2020-10-25", "birth_time": "01:30"}
        status, out = post(fold)
        self.assertEqual((status, out["error"]["code"], out["error"]["category"]), (409, "TIME_AMBIGUOUS_LOCAL", "ambiguous"))
        self.assertEqual([c["utc_offset"] for c in out["error"]["choices"]], ["+01:00", "+00:00"])
        self.assertNotIn("chart", out)
        status, out = post(dict(fold, utc_offset="+00:00"))
        self.assertEqual((status, out["chart"]["birth"]["utc"]), (200, "2020-10-25T01:30:00Z"))

    def test_repeated_hour_with_a_server_fault_is_503_not_409(self):
        fold = {"place_id": "gb-london", "birth_date": "2020-10-25", "birth_time": "01:30"}
        with mock.patch.dict(sys.modules, {"swisseph": None}):
            result = post(fold)
        status, body = result
        self.assertEqual((status, body["error"]["code"]), (503, "SWISS_BINDING_MISSING"))
        self.assertNotIn("choices", body["error"])

    def test_10_unexpected_defects_are_a_fixed_500(self):
        fixed = {"error": {"code": "INTERNAL_ERROR", "message": "unexpected error; no chart produced",
                           "category": "internal"}}
        for boom in (KeyError("secret 1990-05-15"), ZeroDivisionError("/home/x"), RuntimeError("secret"),
                     ValueError("28.6139"), AttributeError("swisseph")):
            with self.subTest(boom=type(boom).__name__):
                err = io.StringIO()
                with mock.patch.object(server, "calculate", side_effect=boom), redirect_stderr(err):
                    status, body = post(GOOD)
                self.assertEqual((status, body), (500, fixed))
                # Only the defect's type is named locally: no message, no request value.
                self.assertEqual(json.loads(err.getvalue()), {"event": "INTERNAL_ERROR", "type": type(boom).__name__})
                self.assertEqual(json.dumps(post(GOOD)[1], sort_keys=True), self.reference)


@requires_data
class SameAsHardenedEngineCli(unittest.TestCase):
    """13: the prototype's chart is the hardened engine CLI's chart, byte for byte as JSON."""

    def test_http_chart_equals_cli_output(self):
        env = {k: v for k, v in os.environ.items() if k not in ("SE_EPHE_PATH",)}
        env.update(SABPUJA_EPHE_PATH=EPHE, PYTHONPATH=str(ROOT / "src"))
        for pid, d, t in SYNTHETIC:
            with self.subTest(pid=pid, date=d):
                status, body = post({"place_id": pid, "birth_date": d, "birth_time": t})
                self.assertEqual(status, 200, body.get("error"))
                place = PLACES[pid]
                time = t if len(t) == 8 else t + ":00"
                request = {"birth_datetime": f"{d}T{time}{body['input']['utc_offset']}",
                           "timezone": place["timezone"], "latitude": place["latitude"],
                           "longitude": place["longitude"]}
                cli = subprocess.run([sys.executable, "-m", "sabpuja_kundali.cli"], input=json.dumps(request),
                                     env=env, capture_output=True, text=True, timeout=120)
                self.assertEqual((cli.returncode, cli.stderr), (0, ""))
                self.assertEqual(json.dumps(json.loads(cli.stdout), sort_keys=True),
                                 json.dumps(body["chart"], sort_keys=True))


if __name__ == "__main__":
    unittest.main()
