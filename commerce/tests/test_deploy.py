"""KUN-COM-PROD-HARDEN-001 F6/F7: the compose topology and gateway config keep the isolation and recover by
themselves. Text checks only (no Docker here); the live restart and recovery evidence comes from the QA staging."""
import json
from pathlib import Path
import re
import unittest

DEPLOY = Path(__file__).resolve().parents[1] / "deploy"
COMPOSE = (DEPLOY / "compose.yml").read_text()
NGINX = (DEPLOY / "gateway.nginx.conf").read_text()


def service(name):
    m = re.search(rf"^  {name}:\n(.*?)(?=^  [a-z]+:\n|^networks:)", COMPOSE, re.M | re.S)
    return m.group(1)


class Topology(unittest.TestCase):
    def test_no_shared_network_namespace(self):
        self.assertNotIn("network_mode", COMPOSE)               # the cause of the QA 502 (F6)

    def test_both_services_restart_unless_stopped(self):
        for name in ("commerce", "gateway"):
            self.assertIn("restart: unless-stopped", service(name), name)

    def test_commerce_is_not_on_the_edge_network(self):
        commerce = service("commerce")
        nets = re.search(r"networks:\n((?:      .*\n)+)", commerce).group(1)
        self.assertNotIn("edge", nets)                          # no route from the proxy around the gateway
        self.assertIn("backend", nets)
        self.assertIn("egress", nets)

    def test_gateway_bridges_edge_and_backend_only(self):
        nets = re.search(r"networks:\n((?:      .*\n)+)", service("gateway")).group(1)
        self.assertEqual(sorted(re.findall(r"^      ([a-z]+):", nets, re.M)), ["backend", "edge"])
        self.assertIn('aliases: ["${SBK_EDGE_ALIAS:-commerce}"]', nets)

    def test_backend_is_internal_with_fixed_addresses(self):
        backend = re.search(r"^  backend:\n((?:    .*\n)+)", COMPOSE, re.M).group(1)
        self.assertIn("internal: true", backend)
        self.assertIn("subnet: ${SBK_BACKEND_SUBNET:-10.231.47.0/29}", backend)
        self.assertIn("ipv4_address: ${SBK_COMMERCE_IP:-10.231.47.2}", service("commerce"))
        self.assertIn("ipv4_address: ${SBK_GATEWAY_IP:-10.231.47.3}", service("gateway"))

    def test_gateway_follows_commerce_restarts(self):
        self.assertIn("commerce: {condition: service_healthy, restart: true}", service("gateway"))

    def test_both_have_healthchecks(self):
        for name in ("commerce", "gateway"):
            self.assertIn("healthcheck:", service(name), name)

    def test_commerce_listens_on_its_backend_address_only(self):
        cmd = service("commerce")
        self.assertIn('"--host", "${SBK_COMMERCE_IP:-10.231.47.2}"', cmd)
        self.assertNotIn("0.0.0.0", COMPOSE)

    def test_hardening_kept(self):
        for name in ("commerce", "gateway"):
            s = service(name)
            for flag in ("read_only: true", "cap_drop: [ALL]", "no-new-privileges:true", "pids_limit: 64"):
                self.assertIn(flag, s, (name, flag))
        self.assertNotIn("ports:", COMPOSE)                     # nothing published on the host

    def test_nginx_only_forwards_to_commerce_backend(self):
        targets = set(re.findall(r"proxy_pass ([^;]+);", NGINX))
        self.assertEqual(targets, {"http://commerce-app:8770"})
        self.assertIn('"commerce-app:${SBK_COMMERCE_IP:-10.231.47.2}"', service("gateway"))
        self.assertIn("access_log off", NGINX)

    def test_trusted_proxy_in_examples_is_the_gateway(self):
        for path in (DEPLOY / "commerce.example.json",
                     DEPLOY.parent / "integration" / "commerce.qa-store.example.json"):
            self.assertEqual(json.loads(path.read_text())["trusted_proxies"], ["10.231.47.3"], path.name)


MAIL = DEPLOY.parent / "mail"
ENTRY = (MAIL / "entrypoint.sh").read_text()
OUTBOUND = (DEPLOY / "compose.outbound-mail.yml").read_text()


class OutboundMail(unittest.TestCase):
    """Self-hosted send-only mail (owner choice 2026-11-09): closed relay, signed, IPv4, nothing kept or logged."""

    def postconf(self, key):
        m = re.search(rf'"{re.escape(key)} =(?: ([^"]*))?"', ENTRY)
        return None if m is None else (m.group(1) or "")

    def test_closed_relay(self):
        self.assertEqual(self.postconf("mydestination"), "")
        self.assertEqual(self.postconf("smtpd_client_restrictions"), "permit_mynetworks, reject")
        self.assertEqual(self.postconf("smtpd_relay_restrictions"), "permit_mynetworks, reject")
        self.assertEqual(self.postconf("smtpd_sender_restrictions"),
                         "check_sender_access hash:/etc/postfix/allowed_senders, reject")
        self.assertEqual(self.postconf("mynetworks"), "127.0.0.0/8 $MAIL_CLIENT_NETWORK")
        self.assertIn("postconf -M# smtp/inet", ENTRY)        # no port-25 listener
        self.assertNotIn("ports:", OUTBOUND)                   # nothing published on the host

    def test_tls_dkim_and_ipv4(self):
        self.assertEqual(self.postconf("smtpd_tls_security_level"), "encrypt")
        self.assertEqual(self.postconf("smtpd_milters"), "inet:127.0.0.1:8891")
        self.assertEqual(self.postconf("milter_default_action"), "tempfail")   # never send unsigned
        self.assertEqual(self.postconf("inet_protocols"), "ipv4")
        self.assertIn("OversignHeaders         From", ENTRY)

    def test_nothing_kept(self):
        self.assertEqual(self.postconf("maximal_queue_lifetime"), "15m")
        self.assertIn("/var/spool/postfix:rw,nosuid,size=32m", OUTBOUND)   # queue in memory
        self.assertEqual(self.postconf("notify_classes"), "")

    def test_log_redaction(self):
        import subprocess
        line = ("Nov  9 postfix/smtp[12]: ABC: to=<buyer.synthetic@example.invalid>, relay=mx.example.invalid, "
                "status=sent; from=<noreply@sabpuja.com> also plain qa-buyer-1@example.com")
        out = subprocess.run(["sed", "-E", "-f", str(MAIL / "redact.sed")], input=line, capture_output=True,
                             text=True, check=True).stdout
        self.assertNotIn("@example", out)
        self.assertNotIn("noreply@sabpuja.com", out)
        self.assertIn("status=sent", out)

    def test_startup_order_and_log_fifo(self):
        # Found on QA staging: postmap needs main.cf, the tmpfs data dir must belong to postfix, and the log FIFO must
        # stay open read-write or Postfix blocks once the first writer closes.
        self.assertLess(ENTRY.index(": > /etc/postfix/main.cf"), ENTRY.index("postmap /etc/postfix/allowed_senders"))
        self.assertIn("chown postfix:postfix /var/lib/postfix", ENTRY)
        self.assertIn("exec 3<>/run/postfix-log.fifo", ENTRY)
        self.assertIn("<&3 &", ENTRY)

    def test_commerce_waits_for_mail_and_overlay_hardened(self):
        self.assertIn("outbound-mail: {condition: service_healthy}", OUTBOUND)
        self.assertIn("restart: unless-stopped", OUTBOUND)
        self.assertIn("cap_drop: [ALL]", OUTBOUND)
        self.assertNotIn("SYS_ADMIN", OUTBOUND)


if __name__ == "__main__":
    unittest.main()
