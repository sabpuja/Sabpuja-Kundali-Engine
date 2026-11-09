"""One-time code delivery. The message holds the code and the order number only, never birth data."""
from __future__ import annotations

from email.message import EmailMessage
import re
import smtplib
import socket
import ssl
import threading

SUBJECT = "Your Sabpuja Janam Kundali access code"


def compose(sender: str, to: str, order_number: int, code: str, ttl_minutes: int) -> EmailMessage:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, to, SUBJECT
    msg.set_content(
        f"Your access code for Sabpuja order #{order_number} is {code}.\n\n"
        f"It expires in {ttl_minutes} minutes and can be used once. If you did not ask for it, "
        "you can ignore this message; nobody can open your order without the code.\n\n"
        "Sabpuja will never ask for this code by phone or chat.\n")
    return msg


class MockMailer:
    """Offline test double: keeps sent messages in memory."""

    def __init__(self, fail: bool = False):
        self.sent: list[EmailMessage] = []
        self.fail = fail
        self._lock = threading.Lock()

    def send(self, msg: EmailMessage) -> None:
        if self.fail:
            raise OSError("mock delivery failure")
        with self._lock:
            self.sent.append(msg)


class _IPv4SMTP(smtplib.SMTP):
    """Connects over IPv4 only. Google's SMTP relay authorises by the sender's IPv4 address; an IPv6 path would be
    refused. The host name is kept for the STARTTLS certificate check."""

    def _get_socket(self, host, port, timeout):
        last = OSError("no IPv4 address")
        for *_, addr in socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_STREAM):
            try:
                return socket.create_connection(addr, timeout, self.source_address)
            except OSError as exc:
                last = exc
        raise last


class SmtpMailer:
    """SMTP submission with mandatory STARTTLS (TLS 1.2 or later) and certificate verification.

    auth "login": username and password (a provider account, or Mailpit in QA).
    auth "none": no SMTP AUTH; the relay authorises this host's IPv4 address (Google Workspace SMTP relay with
    "Only addresses in my SMTP relay servers" and TLS required). `ipv4_only` and `ehlo_name` exist for that case."""

    def __init__(self, host: str, port: int, username: str = "", password: str = "", timeout: float = 10.0,
                 auth: str = "login", ehlo_name: str | None = None, ipv4_only: bool = False):
        if auth not in ("login", "none"):
            raise ValueError("smtp auth must be login or none")
        if auth == "login" and not (username and password):
            raise ValueError("smtp auth login needs a username and a password file")
        if ehlo_name is not None and not re.fullmatch(r"[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+",
                                                     ehlo_name):
            raise ValueError("ehlo_name must be a fully qualified host name")
        self._args = host, port, username, password, timeout
        self._auth, self._ehlo, self._ipv4 = auth, ehlo_name, ipv4_only

    def send(self, msg: EmailMessage) -> None:
        host, port, username, password, timeout = self._args
        ctx = ssl.create_default_context()
        ctx.minimum_version = ssl.TLSVersion.TLSv1_2
        cls = _IPv4SMTP if self._ipv4 else smtplib.SMTP
        with cls(host, port, local_hostname=self._ehlo, timeout=timeout) as smtp:
            smtp.starttls(context=ctx)     # raises if the server does not offer STARTTLS; never sent in clear
            if self._auth == "login":
                smtp.login(username, password)
            smtp.send_message(msg)


def from_config(cfg: dict) -> SmtpMailer:
    """Build the mailer from smtp.json. A password is read from `password_file` only for auth "login"."""
    auth = cfg.get("auth", "login")
    password = ""
    if auth == "login":
        with open(cfg["password_file"], encoding="utf-8") as fh:
            password = fh.read().strip()
    return SmtpMailer(cfg["host"], int(cfg["port"]), cfg.get("username", ""), password, auth=auth,
                      ehlo_name=cfg.get("ehlo_name"), ipv4_only=bool(cfg.get("ipv4_only", False)))
