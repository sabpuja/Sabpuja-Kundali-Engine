#!/bin/bash
# KUN-SEC-AUTHLOG-001: failed logins must leave no user-supplied credential string in the
# gateway or engine logs, while throttling and upstream errors stay logged. Synthetic only.
#
#   auth-log-privacy.sh BASE_URL ORIGIN USER PASSWORD_FILE GATEWAY_CONTAINER ENGINE_CONTAINER [--upstream-check]
#
# Needs a throwaway htpasswd entry USER:PASSWORD in the running gateway. The password is read
# from PASSWORD_FILE and is never printed. --upstream-check pauses the engine container for
# about 25 s to prove that an upstream timeout is still logged (isolated QA only, never live).
set -u
B=$1; O=$2; U=$3; PW=$(cat "$4"); GW=$5; EN=$6; UPSTREAM=${7:-}
TAG=$(od -An -N4 -tx1 /dev/urandom | tr -d ' \n')
SINCE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
fail=0
TMPD=$(mktemp -d); trap 'rm -rf "$TMPD"' EXIT
code(){ curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$@"; }
check(){ if [ "$2" = "$3" ]; then echo "PASS $1 ($2)"; else echo "FAIL $1 (got $2, want $3)"; fail=1; fi; }
b64(){ printf '%s' "$1" | base64 | tr -d '\n'; }
J='{"place_id":"in-new-delhi","birth_date":"1990-05-15","birth_time":"10:30"}'
# Strings that must never reach a log. The "password typed as user name" cases use a synthetic
# secret and the real throwaway password itself.
UNKNOWN="kunqa-unknown-$TAG"
WRONGPW="kunqa-wrongpw-$TAG"
PASTED="PwPastedAsUser-$TAG-Xq7"
SECRETS=("$UNKNOWN" "$WRONGPW" "$PASTED" "$PW" "$U" "$(b64 "$UNKNOWN:$WRONGPW")" "$(b64 "$U:$WRONGPW")" "$(b64 "$PASTED:")" "$(b64 "$PW:x")")

sleep 2
check "no credentials 401" "$(code $B/api/places)" 401
check "challenge realm unchanged" "$(curl -s -o /dev/null -D - --max-time 10 $B/ | tr -d '\r' | grep -i '^www-authenticate:' | sed 's/^[^:]*: //')" 'Basic realm="Sabpuja private client preview"'
check "unknown account 401" "$(code -u "$UNKNOWN:$WRONGPW" $B/api/places)" 401
check "wrong password 401" "$(code -u "$U:$WRONGPW" $B/api/places)" 401
check "password pasted as user name 401" "$(code -u "$PASTED:" $B/api/places)" 401
check "real password typed as user name 401" "$(code -u "$PW:x" $B/api/places)" 401
check "malformed Basic header 401" "$(code -H 'Authorization: Basic !!!not-base64' $B/api/places)" 401
check "wrong password on /api/report 401" "$(code -u "$U:$WRONGPW" -X POST -H "Origin: $O" -H 'Content-Type: application/json' -d "$J" $B/api/report)" 401
check "valid synthetic login 200" "$(code -u "$U:$PW" $B/api/places)" 200
check "valid login bad Origin 403" "$(code -u "$U:$PW" -X POST -H 'Origin: https://evil.example' -H 'Content-Type: application/json' -d "$J" $B/api/chart)" 403
check "valid login 5 KB body 413" "$(code -u "$U:$PW" -X POST -H "Origin: $O" -H 'Content-Type: application/json' --data-binary "$(head -c 5000 /dev/zero | tr '\0' x)" $B/api/chart)" 413
check "internal auth location not reachable 404" "$(code -u "$U:$PW" $B/_sabpuja_auth)" 404
sleep 2
s=$(curl -s -o "$TMPD/pdf" -w '%{http_code}' --max-time 30 -u "$U:$PW" -X POST -H "Origin: $O" -H 'Content-Type: application/json' -d "$J" $B/api/report)
pages=$(python3 -c 'import re,sys; d=open(sys.argv[1],"rb").read(); print(len(re.findall(rb"/Type /Page[^s]", d)) if d.startswith(b"%PDF-") else 0)' "$TMPD/pdf")
check "valid login ten-page PDF 200" "$s/$pages" "200/10"
rm -f "$TMPD/pdf"
# Throttling must still be logged: a burst of failed logins (also checks 429 before auth).
burst=$(for i in $(seq 1 70); do curl -s -o /dev/null -w '%{http_code}\n' --max-time 10 -u "$UNKNOWN:$WRONGPW" $B/api/places & done; wait)
check "failed-login burst throttled 429" "$(echo "$burst" | grep -c '^429$' | awk '{print ($1>0)?"yes":"no"}')" yes
check "failed-login burst otherwise 401" "$(echo "$burst" | grep -v -c -E '^(401|429)$')" 0
sleep 5
if [ "$UPSTREAM" = "--upstream-check" ]; then
  docker pause "$EN" >/dev/null
  t=$(code -u "$U:$PW" $B/api/places)
  docker unpause "$EN" >/dev/null
  check "paused engine gives 504" "$t" 504
fi
LOG=$(docker logs --since "$SINCE" "$GW" 2>&1; docker logs --since "$SINCE" "$EN" 2>&1)
leaks=0
for x in "${SECRETS[@]}"; do n=$(printf '%s' "$LOG" | grep -c -F -- "$x" || true); leaks=$((leaks+n)); done
check "credential strings in gateway+engine logs" "$leaks" 0
check "Authorization or Basic in logs" "$(printf '%s' "$LOG" | grep -c -i -E 'authorization|basic ' || true)" 0
check "birth data in logs" "$(printf '%s' "$LOG" | grep -c -E '1990-05-15|in-new-delhi' || true)" 0
check "auth_basic failure lines in logs" "$(printf '%s' "$LOG" | grep -c -E 'password mismatch|was not found in' || true)" 0
check "throttling still logged" "$(printf '%s' "$LOG" | grep -c 'limiting requests' | awk '{print ($1>0)?"yes":"no"}')" yes
if [ "$UPSTREAM" = "--upstream-check" ]; then
  check "upstream timeout still logged" "$(printf '%s' "$LOG" | grep -c 'upstream timed out' | awk '{print ($1>0)?"yes":"no"}')" yes
fi
echo "gateway+engine log lines in window: $(printf '%s\n' "$LOG" | grep -c .)"
echo "log line kinds (credential-free):"; printf '%s\n' "$LOG" | sed -E 's/^[0-9\/: ]+//; s/\*[0-9]+ //; s/, client:.*//; s/excess: [0-9.]+/excess: N/' | sort | uniq -c | sort -rn | head -8
[ $fail = 0 ] && echo AUTH_LOG_PRIVACY_PASS || { echo AUTH_LOG_PRIVACY_FAIL; exit 1; }
