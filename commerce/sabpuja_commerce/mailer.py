"""One-time code delivery. The message holds the code and the order number only, never birth data."""
from __future__ import annotations

from email.message import EmailMessage
import smtplib
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


class SmtpMailer:
    """SMTP submission with mandatory STARTTLS and certificate verification. Not used in tests."""

    def __init__(self, host: str, port: int, username: str, password: str, timeout: float = 10.0):
        self._args = host, port, username, password, timeout

    def send(self, msg: EmailMessage) -> None:
        host, port, username, password, timeout = self._args
        with smtplib.SMTP(host, port, timeout=timeout) as smtp:
            smtp.starttls(context=ssl.create_default_context())
            smtp.login(username, password)
            smtp.send_message(msg)
