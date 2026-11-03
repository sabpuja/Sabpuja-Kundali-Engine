#!/bin/bash
# KUN-SEC-AUTHLOG-001 isolated QA runner. Brings up preview/compose.yml from SRC_DIR on a
# throwaway Docker network with a throwaway synthetic htpasswd user, then runs:
#   A. auth-log-privacy.sh with --upstream-check
#   B. credential revocation (second synthetic user; gateway-only force-recreate)
#   C. auth-log-privacy.sh again after the full gateway container recreation
#   D. trusted-proxy behaviour (a client container at the trusted proxy address)
#   E. unreadable htpasswd (unexpected auth error) stays observable and fails closed
#   F. nginx -t as UID 101, a broken config copy is refused, port 8081 not reachable, docker diff
# and removes everything, shredding the credential files. Never point it at a live deployment.
#
#   auth-log-privacy-stack.sh SRC_DIR ENGINE_IMAGE EPHE_DIR [TEST_SCRIPT]
#
# SRC_DIR supplies preview/compose.yml and preview/Gateway.nginx.conf (use a git archive of the
# commit under test, or of the parent to reproduce the original leak). TEST_SCRIPT defaults to
# this directory's auth-log-privacy.sh. Needs docker, curl, openssl, python3, root for chmod/shred.
set -u
SRC=$(cd "$1" && pwd); IMG=$2; EPHE=$3
HERE=$(cd "$(dirname "$0")" && pwd); T=${4:-$HERE/auth-log-privacy.sh}
NET=${AUTHLOG_QA_NETWORK:-kun-authlog-qa}; SUB=${AUTHLOG_QA_SUBNET:-172.31.251}
P=$NET; W=$(mktemp -d); chmod 755 "$W"
ENG=$SUB.10; PROXY=$SUB.250; B=http://$ENG:8080
export NO_PROXY="$ENG,${NO_PROXY:-}" no_proxy="$ENG,${no_proxy:-}"
fail=0
check(){ if [ "$2" = "$3" ]; then echo "PASS $1 ($2)"; else echo "FAIL $1 (got $2, want $3)"; fail=1; fi; }
code(){ curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$@"; }
C(){ (cd "$SRC" && docker compose -p "$P" --env-file "$W/qa.env" -f preview/compose.yml -f "$W/override.yml" "$@"); }
GW=$P-gateway-1; EN=$P-engine-1
cleanup(){ C down >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1; shred -u "$W"/qa-password "$W"/rev-password "$W"/htpasswd "$W"/qa-user 2>/dev/null; rm -rf "$W"; }
trap cleanup EXIT
# Up = three consecutive 401s for an anonymous request.
wait_up(){ local ok=0; for i in $(seq 90); do if [ "$(code $B/)" = 401 ]; then ok=$((ok+1)); [ $ok -ge 3 ] && return 0; else ok=0; fi; sleep 1; done; echo "FAIL gateway did not come up"; fail=1; return 1; }
recreate(){ local out; out=$(C up -d --no-build --force-recreate gateway 2>&1) || { echo "FAIL gateway recreate: $out"; fail=1; }; sleep 2; wait_up; }
mountless_diff(){ local m; m=$(docker inspect -f '{{range .Mounts}}{{.Destination}} {{end}}' "$1"); docker diff "$1" | while read -r k f; do
  case "$f" in /tmp|/tmp/*) continue;; esac; skip=0; for d in $m; do case "$d/" in "$f"/*) skip=1;; esac; done; [ $skip = 1 ] || echo "$k $f"; done; }
user_line(){ printf '%s:%s\n' "$1" "$(openssl passwd -apr1 -stdin < "$2")"; }

echo "== setup: source $(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo archive) gateway config sha256 $(sha256sum "$SRC/preview/Gateway.nginx.conf" | cut -c1-64)"
mkdir -p "$W/ephe" && cp "$EPHE"/se*_18.se1 "$W/ephe/" && chmod 0755 "$W/ephe" && chmod 0644 "$W"/ephe/*
openssl rand -hex 24 > "$W/qa-password"; chmod 600 "$W/qa-password"
echo "kunqa-$(openssl rand -hex 3)" > "$W/qa-user"; chmod 600 "$W/qa-user"
user_line "$(cat "$W/qa-user")" "$W/qa-password" > "$W/htpasswd"; chmod 0644 "$W/htpasswd"
echo "\"$B\" 0;" > "$W/allowed-origins.map"; echo "set_real_ip_from $PROXY;" > "$W/trusted-proxy.conf"; chmod 0644 "$W"/*.map "$W"/*.conf
docker network create --subnet "$SUB.0/24" "$NET" >/dev/null
printf 'services:\n  engine:\n    image: %s\n    networks:\n      edge:\n        ipv4_address: %s\n' "$IMG" "$ENG" > "$W/override.yml"
printf 'SABPUJA_PREVIEW_EPHE_DIR=%s/ephe\nSABPUJA_PREVIEW_NETWORK=%s\nSABPUJA_PREVIEW_HTPASSWD_FILE=%s/htpasswd\nSABPUJA_PREVIEW_ALLOWED_ORIGINS_FILE=%s/allowed-origins.map\nSABPUJA_PREVIEW_TRUSTED_PROXY_FILE=%s/trusted-proxy.conf\n' "$W" "$NET" "$W" "$W" "$W" > "$W/qa.env"
C up -d --no-build >/dev/null 2>&1; wait_up || { echo "FAIL stack did not start"; exit 1; }
U=$(cat "$W/qa-user")
docker inspect -f 'gateway user={{.Config.User}} read_only={{.HostConfig.ReadonlyRootfs}} cap_drop={{.HostConfig.CapDrop}} security_opt={{.HostConfig.SecurityOpt}} mem={{.HostConfig.Memory}} pids={{.HostConfig.PidsLimit}} published_ports={{.HostConfig.PortBindings}}' "$GW"
docker inspect -f 'engine  user={{.Config.User}} read_only={{.HostConfig.ReadonlyRootfs}} cap_drop={{.HostConfig.CapDrop}} security_opt={{.HostConfig.SecurityOpt}} mem={{.HostConfig.Memory}} pids={{.HostConfig.PidsLimit}} published_ports={{.HostConfig.PortBindings}}' "$EN"

echo; echo "######## A. privacy matrix (with upstream check)"
bash "$T" $B $B "$U" "$W/qa-password" "$GW" "$EN" --upstream-check || fail=1

# The paused-engine check leaves the engine "unhealthy" until its next passing healthcheck
# (interval 30 s), and Compose will not recreate the gateway while it is unhealthy.
h=""; for i in $(seq 120); do h=$(docker inspect -f '{{.State.Health.Status}}' "$EN"); [ "$h" = healthy ] && break; sleep 1; done
echo "engine health after upstream check: $h (waited ${i}s)"

echo; echo "######## B. revocation (gateway-only force-recreate)"
RU="kunqa-rev-$(openssl rand -hex 3)"; openssl rand -hex 16 > "$W/rev-password"; chmod 600 "$W/rev-password"
SINCE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
user_line "$RU" "$W/rev-password" >> "$W/htpasswd"; recreate
check "second synthetic user before revocation 200" "$(code -u "$RU:$(cat "$W/rev-password")" $B/api/places)" 200
grep -v "^$RU:" "$W/htpasswd" > "$W/h2"; cat "$W/h2" > "$W/htpasswd"; shred -u "$W/h2"; recreate
check "revoked user after gateway recreate 401" "$(code -u "$RU:$(cat "$W/rev-password")" $B/api/places)" 401
check "remaining user after gateway recreate 200" "$(code -u "$U:$(cat "$W/qa-password")" $B/api/places)" 200
L=$(docker logs --since "$SINCE" "$GW" 2>&1; docker logs --since "$SINCE" "$EN" 2>&1)
check "revoked user name/password in logs" "$(printf '%s' "$L" | grep -c -F -e "$RU" -e "$(cat "$W/rev-password")" || true)" 0
check "revoked login recorded as auth_failed" "$(printf '%s\n' "$L" | grep -c '^sabpuja_security .* event=auth_failed ' | awk '{print ($1>0)?"yes":"no"}')" yes

echo; echo "######## C. privacy matrix again after full gateway container recreation"
recreate; sleep 3
bash "$T" $B $B "$U" "$W/qa-password" "$GW" "$EN" || fail=1

echo; echo "######## D. trusted proxy (client container at $PROXY)"
recreate
viaproxy(){ docker run --rm --network "$NET" --ip "$PROXY" --entrypoint sh nginx:1.28.0-alpine -c "$1"; }
r=$(viaproxy "for i in \$(seq 70); do curl -s -o /dev/null -w '%{http_code}\n' --max-time 10 -H 'X-Forwarded-For: 198.51.100.7' $B/api/places & done; wait; sleep 0.2; echo next \$(curl -s -o /dev/null -w '%{http_code}' -H 'X-Forwarded-For: 198.51.100.8' $B/api/places)")
check "trusted proxy: flooded client gets 429" "$(echo "$r" | grep -c '^429$' | awk '{print ($1>0)?"yes":"no"}')" yes
check "trusted proxy: a different client keeps its own bucket (401, not 429)" "$(echo "$r" | sed -n 's/^next //p')" 401
sleep 6
r=$(for i in $(seq 70); do curl -s -o /dev/null -w '%{http_code}\n' --max-time 10 -H "X-Forwarded-For: 198.51.100.$((i%200+1))" $B/api/places & done; wait)
check "untrusted client: forged X-Forwarded-For does not open new buckets (429)" "$(echo "$r" | grep -c '^429$' | awk '{print ($1>0)?"yes":"no"}')" yes
check "untrusted client: forged X-Forwarded-For never authenticates" "$(echo "$r" | grep -v -c -E '^(401|429)$')" 0

echo; echo "######## E. unexpected auth error: htpasswd unreadable by the gateway"
SINCE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
chmod 000 "$W/htpasswd"; recreate
check "valid login with unreadable htpasswd fails closed 500" "$(code -u "$U:$(cat "$W/qa-password")" $B/api/places)" 500
check "anonymous with unreadable htpasswd still refused (401 or 500)" "$(code $B/api/places | grep -c -E '^(401|500)$')" 1
L=$(docker logs --since "$SINCE" "$GW" 2>&1)
check "auth error visible in error log" "$(printf '%s\n' "$L" | grep -c -E 'auth request unexpected status: 500|open\(\) "/etc/nginx/private-htpasswd" failed' | awk '{print ($1>0)?"yes":"no"}')" yes
check "auth error recorded as server_error 500" "$(printf '%s\n' "$L" | grep -c '^sabpuja_security .* event=server_error status=500 ' | awk '{print ($1>0)?"yes":"no"}')" yes
check "user name not in logs" "$(printf '%s' "$L" | grep -c -F "$U" || true)" 0
echo "error-log line kinds:"; printf '%s\n' "$L" | grep -v '^sabpuja_security ' | sed -E 's/^[0-9\/: ]+//; s/\*[0-9]+ //; s/, client:.*//' | sort | uniq -c
chmod 0644 "$W/htpasswd"; recreate
check "recovers after htpasswd fixed 200" "$(code -u "$U:$(cat "$W/qa-password")" $B/api/places)" 200

echo; echo "######## F. configuration and isolation"
docker exec "$GW" nginx -t 2>&1 | sed 's/^/  /'
check "nginx -t as UID $(docker exec "$GW" id -u) passes" "$(docker exec "$GW" nginx -t >/dev/null 2>&1; echo $?)" 0
check "auth_request module present" "$(docker exec "$GW" sh -c 'nginx -V 2>&1 | grep -c http_auth_request_module')" 1
sed 's/auth_request \/_sabpuja_auth;/auth_request \/_sabpuja_auth/' "$SRC/preview/Gateway.nginx.conf" > "$W/broken.conf"; chmod 0644 "$W/broken.conf"
out=$(docker run --rm --user 101:101 --read-only --tmpfs /tmp -v "$W/broken.conf:/etc/nginx/nginx.conf:ro" -v "$W/htpasswd:/etc/nginx/private-htpasswd:ro" -v "$W/allowed-origins.map:/etc/nginx/preview-allowed-origins.map:ro" -v "$W/trusted-proxy.conf:/etc/nginx/preview-trusted-proxy.conf:ro" nginx:1.28.0-alpine nginx -t 2>&1)
check "broken config copy refused with an emerg message" "$(printf '%s' "$out" | grep -c '\[emerg\]' | awk '{print ($1>0)?"yes":"no"}')" yes
printf '%s\n' "$out" | grep emerg | sed "s#$W#<qa-dir>#; s/^/  /"
check "port 8081 not reachable from the network" "$(curl -s --noproxy '*' -o /dev/null -w '%{http_code}' --max-time 5 http://$ENG:8081/_sabpuja_auth)" 000
echo "  docker diff (mount points and /tmp excluded):"; for c in "$GW" "$EN"; do mountless_diff "$c" | sed "s/^/    $c /"; done
check "gateway writes nothing outside mounts and tmpfs" "$(mountless_diff "$GW" | grep -c . || true)" 0
check "engine writes nothing outside mounts and tmpfs" "$(mountless_diff "$EN" | grep -c . || true)" 0

echo; [ $fail = 0 ] && echo AUTHLOG_STACK_PASS || { echo AUTHLOG_STACK_FAIL; exit 1; }
