#!/bin/sh
# Configure and run send-only Postfix + OpenDKIM. All settings come from the environment; the DKIM private key and
# the TLS key are mounted read-only from /run/outbound-mail (0400, outside Git).
set -eu

: "${MAIL_HOSTNAME:?FQDN this host announces, must match the IP's reverse DNS, e.g. mail.sabpuja.com}"
: "${MAIL_DOMAIN:?signing and sender domain, e.g. sabpuja.com}"
: "${MAIL_SENDER:?the only envelope sender accepted, e.g. noreply@sabpuja.com}"
: "${MAIL_CLIENT_NETWORK:?CIDR of the private network the commerce container sends from}"
: "${DKIM_SELECTOR:?DKIM selector, e.g. kun2026}"
SECRETS=/run/outbound-mail
for f in dkim.private tls.crt tls.key; do
  [ -s "$SECRETS/$f" ] || { echo "missing $SECRETS/$f" >&2; exit 64; }
done
case "$MAIL_SENDER" in *"@$MAIL_DOMAIN") ;; *) echo "MAIL_SENDER must be in MAIL_DOMAIN" >&2; exit 64;; esac

# ---- OpenDKIM: sign mail from the client network for MAIL_DOMAIN only -------------------------------------------
mkdir -p /run/opendkim /var/spool/postfix/opendkim
install -o opendkim -g opendkim -m 0400 "$SECRETS/dkim.private" /run/opendkim/dkim.private
printf '%s\n' "127.0.0.1" "$MAIL_CLIENT_NETWORK" > /run/opendkim/trusted
cat > /run/opendkim/opendkim.conf <<CONF
Syslog                  no
LogWhy                  no
UMask                   007
Mode                    s
Domain                  $MAIL_DOMAIN
Selector                $DKIM_SELECTOR
KeyFile                 /run/opendkim/dkim.private
Canonicalization        relaxed/simple
SignatureAlgorithm      rsa-sha256
OversignHeaders         From
InternalHosts           refile:/run/opendkim/trusted
Socket                  inet:8891@127.0.0.1
PidFile                 /run/opendkim/opendkim.pid
UserID                  opendkim:opendkim
CONF
chown -R opendkim:opendkim /run/opendkim

# ---- Postfix --------------------------------------------------------------------------------------------------
# The data directory is a tmpfs mounted as root; master needs it owned by postfix (master.lock, TLS caches).
chown postfix:postfix /var/lib/postfix
# main.cf must exist before postmap runs (the image deletes Debian's default).
: > /etc/postfix/main.cf
install -m 0444 "$SECRETS/tls.crt" /etc/postfix/tls.crt
install -m 0400 "$SECRETS/tls.key" /etc/postfix/tls.key
printf '%s OK\n' "$MAIL_SENDER" > /etc/postfix/allowed_senders
postmap /etc/postfix/allowed_senders
postconf -e \
  "compatibility_level = 3.6" \
  "myhostname = $MAIL_HOSTNAME" \
  "mydomain = $MAIL_DOMAIN" \
  "myorigin = \$mydomain" \
  "mydestination =" \
  "relay_domains =" \
  "local_transport = error:local delivery is disabled" \
  "local_recipient_maps =" \
  "alias_maps =" "alias_database =" \
  "inet_interfaces = all" \
  "inet_protocols = ipv4" \
  "mynetworks = 127.0.0.0/8 $MAIL_CLIENT_NETWORK" \
  "smtpd_banner = \$myhostname ESMTP" \
  "smtpd_tls_cert_file = /etc/postfix/tls.crt" \
  "smtpd_tls_key_file = /etc/postfix/tls.key" \
  "smtpd_tls_security_level = encrypt" \
  "smtpd_tls_mandatory_protocols = >=TLSv1.2" \
  "smtpd_tls_protocols = >=TLSv1.2" \
  "smtpd_client_restrictions = permit_mynetworks, reject" \
  "smtpd_sender_restrictions = check_sender_access hash:/etc/postfix/allowed_senders, reject" \
  "smtpd_relay_restrictions = permit_mynetworks, reject" \
  "smtpd_recipient_restrictions = permit_mynetworks, reject" \
  "smtpd_client_message_rate_limit = 120" \
  "smtpd_client_recipient_rate_limit = 120" \
  "anvil_rate_time_unit = 60s" \
  "message_size_limit = 65536" \
  "smtpd_recipient_limit = 1" \
  "smtp_helo_name = \$myhostname" \
  "smtp_tls_security_level = may" \
  "smtp_tls_protocols = >=TLSv1.2" \
  "smtp_tls_CAfile = /etc/ssl/certs/ca-certificates.crt" \
  "smtp_tls_loglevel = 1" \
  "milter_default_action = tempfail" \
  "milter_protocol = 6" \
  "smtpd_milters = inet:127.0.0.1:8891" \
  "non_smtpd_milters = inet:127.0.0.1:8891" \
  "maximal_queue_lifetime = 15m" \
  "bounce_queue_lifetime = 15m" \
  "minimal_backoff_time = 60s" \
  "maximal_backoff_time = 180s" \
  "queue_run_delay = 60s" \
  "notify_classes =" \
  "biff = no" \
  "maillog_file_prefixes = /run/postfix-log" \
  "maillog_file = /run/postfix-log.fifo" \
  "disable_vrfy_command = yes" \
  "smtputf8_enable = no"
if [ -n "${TEST_TRANSPORT:-}" ]; then
  # QA only: deliver everything to a private capture service instead of the internet (DKIM verification).
  postconf -e "default_transport = $TEST_TRANSPORT"
fi
# Submission on 2587 inside the container network only (no published port); the default port 25 listener is removed.
postconf -M# smtp/inet
postconf -M "2587/inet=2587 inet n - n - - smtpd"
postconf -F '*/*/chroot = n'

# Redacted log: Postfix writes to a FIFO, sed strips addresses, stdout goes to the container log.
rm -f /run/postfix-log.fifo && mkfifo -m 0600 /run/postfix-log.fifo
# Hold the FIFO open read-write so the reader never sees EOF when one writer closes (otherwise logging blocks Postfix).
exec 3<>/run/postfix-log.fifo
sed -u -E -f /usr/local/share/outbound-mail-redact.sed <&3 &

opendkim -x /run/opendkim/opendkim.conf
postfix check
exec postfix start-fg
