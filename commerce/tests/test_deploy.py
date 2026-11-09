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


if __name__ == "__main__":
    unittest.main()
