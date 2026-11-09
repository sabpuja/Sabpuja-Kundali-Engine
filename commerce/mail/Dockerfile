# Send-only outbound mail for one-time login codes (KUN-COM-PROD-HARDEN-001, owner choice 2026-11-09).
# Postfix accepts mail only from the commerce container's private network, over STARTTLS, only from the configured
# sender; OpenDKIM signs it; it delivers directly to recipients' MX over IPv4. No inbox, no published port, queue in
# memory (codes expire after 10 minutes, so nothing is worth keeping across a restart).
# Pin the digest at build time and record it in the evidence: docker build --build-arg BASE=debian:bookworm-slim@sha256:...
ARG BASE=debian:bookworm-slim
FROM ${BASE}
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends postfix opendkim ca-certificates \
 && rm -rf /var/lib/apt/lists/* /etc/postfix/main.cf \
 && dpkg-query -W postfix opendkim > /usr/local/share/outbound-mail-versions.txt
COPY entrypoint.sh /usr/local/bin/outbound-mail
COPY redact.sed /usr/local/share/outbound-mail-redact.sed
RUN chmod 0755 /usr/local/bin/outbound-mail
EXPOSE 2587
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD postfix status >/dev/null 2>&1 && kill -0 "$(cat /run/opendkim/opendkim.pid)"
ENTRYPOINT ["/usr/local/bin/outbound-mail"]
