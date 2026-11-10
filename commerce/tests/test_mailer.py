"""KUN-COM-PROD-HARDEN-001: SMTP submission modes (login for Mailpit/providers, none for Google's IP-authorised
relay). A recording stand-in replaces smtplib.SMTP; no network, no real mailbox."""
import json
from pathlib import Path
import socket
import tempfile
import unittest
from unittest import mock

from sabpuja_commerce import mailer

MSG = mailer.compose("Sabpuja <no-reply@example.invalid>", "buyer@example.invalid", 1001, "123456", 10)


class Recorder:
    calls = []

    def __init__(self, host, port, local_hostname=None, timeout=None):
        Recorder.calls.append(("connect", host, port, local_hostname, timeout))
        self.starttls_ok = True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def starttls(self, context):
        Recorder.calls.append(("starttls", context.verify_mode, context.check_hostname, context.minimum_version))

    def login(self, user, password):
        Recorder.calls.append(("login", user))

    def send_message(self, msg):
        Recorder.calls.append(("send", msg["To"]))


class Modes(unittest.TestCase):
    def setUp(self):
        Recorder.calls = []

    def send(self, m, ipv4=False):
        target = "sabpuja_commerce.mailer._IPv4SMTP" if ipv4 else "smtplib.SMTP"
        with mock.patch(target, Recorder):
            m.send(MSG)
        return Recorder.calls

    def test_login_mode_uses_starttls_then_login(self):
        import ssl
        calls = self.send(mailer.SmtpMailer("mailpit", 1025, "qa", "synthetic-password"))
        self.assertEqual([c[0] for c in calls], ["connect", "starttls", "login", "send"])
        self.assertEqual(calls[1][1:], (ssl.CERT_REQUIRED, True, ssl.TLSVersion.TLSv1_2))

    def test_relay_mode_has_no_login_and_names_itself(self):
        m = mailer.SmtpMailer("smtp-relay.gmail.com", 587, auth="none", ehlo_name="kundali.example.com",
                              ipv4_only=True)
        calls = self.send(m, ipv4=True)
        self.assertEqual([c[0] for c in calls], ["connect", "starttls", "send"])
        self.assertEqual(calls[0][1:4], ("smtp-relay.gmail.com", 587, "kundali.example.com"))

    def test_starttls_failure_never_sends_in_clear(self):
        class NoTLS(Recorder):
            def starttls(self, context):
                raise mailer.smtplib.SMTPNotSupportedError("STARTTLS extension not supported by server.")
        with mock.patch("smtplib.SMTP", NoTLS), self.assertRaises(mailer.smtplib.SMTPException):
            mailer.SmtpMailer("relay.example", 587, auth="none").send(MSG)
        self.assertNotIn("send", [c[0] for c in Recorder.calls])

    def test_bad_settings_refused(self):
        for kw in (dict(auth="plain"), dict(auth="login"), dict(auth="none", ehlo_name="localhost"),
                   dict(auth="none", ehlo_name="bad_name.example")):
            with self.assertRaises(ValueError, msg=kw):
                mailer.SmtpMailer("relay.example", 587, **kw)

    def test_ipv4_only_connects_over_ipv4(self):
        seen = []
        with mock.patch("socket.getaddrinfo", lambda h, p, fam, typ: (seen.append(fam), [
                (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.0.2.10", p))])[1]), \
                mock.patch("socket.create_connection", lambda addr, *a: (_ for _ in ()).throw(OSError("offline"))):
            with self.assertRaises(OSError):
                mailer._IPv4SMTP("relay.example", 587, timeout=1)
        self.assertEqual(seen, [socket.AF_INET])


class Headers(unittest.TestCase):
    def test_date_and_message_id_in_sender_domain(self):
        from email.utils import parsedate_to_datetime
        msg = mailer.compose("Sabpuja <noreply@sabpuja.example>", "buyer@example.invalid", 1001, "123456", 10)
        self.assertIsNotNone(parsedate_to_datetime(msg["Date"]))
        self.assertRegex(msg["Message-ID"], r"^<[^@<>]+@sabpuja\.example>$")
        self.assertNotEqual(msg["Message-ID"], mailer.compose("Sabpuja <noreply@sabpuja.example>", "b@x.invalid",
                                                              1, "1", 10)["Message-ID"])


class FromConfig(unittest.TestCase):
    def test_examples_build(self):
        root = Path(__file__).resolve().parents[1] / "integration"
        relay = json.loads((root / "smtp.google-relay.example.json").read_text())
        relay["ehlo_name"] = "kundali.example.com"
        m = mailer.from_config(relay)
        self.assertEqual((m._auth, m._ipv4, m._ehlo), ("none", True, "kundali.example.com"))
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "pw").write_text("synthetic-password\n")
            login = json.loads((root / "smtp.example.json").read_text())
            login.update(username="qa", password_file=str(Path(d) / "pw"))
            m = mailer.from_config(login)
            self.assertEqual((m._auth, m._args[3]), ("login", "synthetic-password"))
            self.assertNotIn("synthetic-password", repr(m.__dict__.get("_auth")))

    def test_relay_reads_no_password_file(self):
        m = mailer.from_config({"host": "smtp-relay.gmail.com", "port": 587, "auth": "none",
                                "password_file": "/nonexistent/never-read"})
        self.assertEqual(m._args[3], "")


if __name__ == "__main__":
    unittest.main()
