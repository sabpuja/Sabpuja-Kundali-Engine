#!/bin/bash
# KUN-SEC-AUTHLOG-001: failed logins must leave no user-supplied credential or identity text in
# the gateway or engine logs or temp files, while refusals, throttling and upstream errors stay
# observable. Runs against a real gateway + engine stack. Synthetic credentials only.
#
#   auth-log-privacy.sh BASE_URL ORIGIN USER PASSWORD_FILE GATEWAY_CONTAINER ENGINE_CONTAINER [--upstream-check]
#
# USER:PASSWORD must be a throwaway htpasswd entry in the running gateway. The password is read
# from PASSWORD_FILE. A random canary stands for a password typed into the user-name box. No
# credential, canary or raw log line is ever printed: lines that contain one are withheld.
# --upstream-check pauses the engine container for about 25 s (isolated QA stacks only).
set -u
B=$1; O=$2; U=$3; PW=$(cat "$4"); GW=$5; EN=$6; UPSTREAM=${7:-}
TMPD=$(mktemp -d); chmod 700 "$TMPD"; trap 'rm -rf "$TMPD"' EXIT
rnd(){ od -An -N"$1" -tx1 /dev/urandom | tr -d ' \n'; }
TAG=$(rnd 4)
CANARY="Kq$(rnd 12)Zx"            # synthetic "misplaced password"
SINCE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
fail=0
code(){ curl -s -o /dev/null -w '%{http_code}' --max-time 30 "$@"; }
check(){ if [ "$2" = "$3" ]; then echo "PASS $1 ($2)"; else echo "FAIL $1 (got $2, want $3)"; fail=1; fi; }
b64(){ printf '%s' "$1" | base64 | tr -d '\n'; }
basic(){ printf 'Authorization: Basic %s' "$(b64 "$1:$2")"; }
yes_if(){ awk '{print ($1>0)?"yes":"no"}'; }
J='{"place_id":"in-new-delhi","birth_date":"1990-05-15","birth_time":"10:30"}'
POST=(-X POST -H "Origin: $O" -H 'Content-Type: application/json' -d "$J")

# Strings that must never reach a log, a temp file or this script's output.
LONGU="L$(head -c 3000 /dev/zero | tr '\0' x)$CANARY"
UNI="Ünïcødé-नमस्ते-$CANARY"
SPACE="space user $CANARY"
QUOTE="q\"uo'te\"$CANARY"
CTRL=$(printf 'ctl\001\033[31m\t%s' "$CANARY")
NL=$(printf 'nl\r\n%s' "$CANARY")
UNKNOWN="kunqa-unknown-$TAG"
WRONGPW="WrongPw-$CANARY"
printf '%s\n' "$CANARY" "$UNKNOWN" "$WRONGPW" "$PW" "$U" "$(b64 "$UNKNOWN:$WRONGPW")" "$(b64 "$U:$WRONGPW")" \
  "$(b64 "$CANARY:")" "$(b64 "$PW:x")" "$(b64 "$CANARY")" "kunqa-" > "$TMPD/secrets"

echo "== 1. missing, malformed and rejected credentials (expect 401 + unchanged challenge)"
sleep 2
check "missing Authorization 401" "$(code $B/api/places)" 401
check "challenge realm unchanged" "$(curl -s -o /dev/null -D - --max-time 10 $B/ | tr -d '\r' | grep -i '^www-authenticate:' | sed 's/^[^:]*: //')" 'Basic realm="Sabpuja private client preview"'
check "challenge on rejected login" "$(curl -s -o /dev/null -D - --max-time 10 -H "$(basic "$UNKNOWN" "$WRONGPW")" $B/ | tr -d '\r' | grep -ci '^www-authenticate: Basic realm="Sabpuja private client preview"$')" 1
check "unknown user 401" "$(code -H "$(basic "$UNKNOWN" "$WRONGPW")" $B/api/places)" 401
check "correct user, wrong password 401" "$(code -H "$(basic "$U" "$WRONGPW")" $B/api/places)" 401
check "canary password typed as user name 401" "$(code -H "$(basic "$CANARY" "")" $B/api/places)" 401
check "real password typed as user name 401" "$(code -H "$(basic "$PW" "x")" $B/api/places)" 401
check "3 KB user name 401" "$(code -H "$(basic "$LONGU" "x")" $B/api/places)" 401
check "Unicode user name 401" "$(code -H "$(basic "$UNI" "x")" $B/api/places)" 401
check "user name with spaces 401" "$(code -H "$(basic "$SPACE" "x")" $B/api/places)" 401
check "user name with quotes 401" "$(code -H "$(basic "$QUOTE" "x")" $B/api/places)" 401
check "user name with control characters 401" "$(code -H "$(basic "$CTRL" "x")" $B/api/places)" 401
check "user name with CR/LF 401" "$(code -H "$(basic "$NL" "x")" $B/api/places)" 401
check "Basic without colon 401" "$(code -H "Authorization: Basic $(b64 "$CANARY")" $B/api/places)" 401
check "Basic not base64 401" "$(code -H 'Authorization: Basic !!!not-base64' $B/api/places)" 401
check "Basic empty 401" "$(code -H 'Authorization: Basic ' $B/api/places)" 401
check "Bearer scheme 401" "$(code -H "Authorization: Bearer $CANARY" $B/api/places)" 401
check "bare token 401" "$(code -H "Authorization: $CANARY" $B/api/places)" 401
sleep 2
check "wrong password on /api/report 401" "$(code -H "$(basic "$U" "$WRONGPW")" "${POST[@]}" $B/api/report)" 401
sleep 2
check "canary user on /api/chart 401" "$(code -H "$(basic "$CANARY" "")" "${POST[@]}" $B/api/chart)" 401
check "duplicate Authorization (rejected, then valid) refused 400" "$(code -H "$(basic "$UNKNOWN" "$WRONGPW")" -H "$(basic "$U" "$PW")" $B/api/places)" 400
check "duplicate Authorization (valid, then rejected) refused 400" "$(code -H "$(basic "$U" "$PW")" -H "$(basic "$UNKNOWN" "$WRONGPW")" $B/api/places)" 400
check "duplicate Authorization (valid twice) refused 400" "$(code -H "$(basic "$U" "$PW")" -H "$(basic "$U" "$PW")" $B/api/places)" 400
sleep 5

echo "== 2. every endpoint without valid credentials (expect 401; bad Origin 403 first)"
for p in / /static/app.js /static/app.css /static/chart.js /static/fonts.css /api/places /no-such-path /_sabpuja_auth/; do
  check "GET $p anonymous 401" "$(code $B$p)" 401
  check "GET $p rejected login 401" "$(code -H "$(basic "$CANARY" "")" $B$p)" 401
done
# The internal auth-check location answers 404 to any outside request (internal; checked before
# access), with or without credentials. It must never answer 2xx.
for p in /_sabpuja_auth /%5Fsabpuja_auth //_sabpuja_auth; do
  check "GET $p anonymous not reachable (401 or 404)" "$(code $B$p | grep -c -E '^(401|404)$')" 1
  check "GET $p rejected login not reachable (401 or 404)" "$(code -H "$(basic "$CANARY" "")" $B$p | grep -c -E '^(401|404)$')" 1
done
check "HEAD / anonymous 401" "$(code -I $B/)" 401
check "OPTIONS /api/chart anonymous 401" "$(code -X OPTIONS -H "Origin: $O" $B/api/chart)" 401
sleep 2
check "POST /api/chart anonymous 401" "$(code "${POST[@]}" $B/api/chart)" 401
sleep 2
check "POST /api/report anonymous 401" "$(code "${POST[@]}" $B/api/report)" 401
sleep 2
check "POST /api/chart anonymous bad Origin 403" "$(code -X POST -H 'Origin: https://evil.example' -H 'Content-Type: application/json' -d "$J" $B/api/chart)" 403
check "forged X-Forwarded-For/X-Real-IP does not skip auth 401" "$(code -H 'X-Forwarded-For: 127.0.0.1' -H 'X-Real-IP: 127.0.0.1' $B/api/places)" 401
sleep 5

echo "== 3. valid synthetic login (expect unchanged behaviour)"
check "valid login 200" "$(code -u "$U:$PW" $B/api/places)" 200
check "valid login page 200" "$(code -u "$U:$PW" $B/)" 200
check "valid login bad Origin 403" "$(code -u "$U:$PW" -X POST -H 'Origin: https://evil.example' -H 'Content-Type: application/json' -d "$J" $B/api/chart)" 403
check "valid login 5 KB body 413" "$(code -u "$U:$PW" -X POST -H "Origin: $O" -H 'Content-Type: application/json' --data-binary "$(head -c 5000 /dev/zero | tr '\0' x)" $B/api/chart)" 413
for p in /_sabpuja_auth /_sabpuja_auth/ /%5Fsabpuja_auth //_sabpuja_auth; do
  check "valid login GET $p is not the auth check (404)" "$(code -u "$U:$PW" $B$p)" 404
done
sleep 2
check "valid login chart 200" "$(code -u "$U:$PW" "${POST[@]}" $B/api/chart)" 200
sleep 2
s=$(curl -s -D "$TMPD/h" -o "$TMPD/pdf" -w '%{http_code}' --max-time 30 -u "$U:$PW" "${POST[@]}" $B/api/report)
pages=$(python3 -c 'import re,sys; d=open(sys.argv[1],"rb").read(); print(len(re.findall(rb"/Type /Page[^s]", d)) if d.startswith(b"%PDF-") else 0)' "$TMPD/pdf")
check "valid login ten-page PDF 200" "$s/$pages" "200/10"
check "PDF headers unchanged" "$(tr -d '\r' < "$TMPD/h" | grep -iE '^(content-type: application/pdf|content-disposition: attachment; filename="Sabpuja-Janma-Kundali.pdf"|cache-control: no-store)$' | tr 'A-Z' 'a-z' | sort -u | wc -l)" 3
rm -f "$TMPD/pdf" "$TMPD/h"
sleep 5

echo "== 4. repeated and concurrent attempts"
burst=$(for i in $(seq 1 70); do curl -s -o /dev/null -w '%{http_code}\n' --max-time 10 -H "$(basic "$CANARY" "")" $B/api/places & done; wait)
check "70 failed logins: some throttled 429" "$(echo "$burst" | grep -c '^429$' | yes_if)" yes
check "70 failed logins: otherwise only 401" "$(echo "$burst" | grep -v -c -E '^(401|429)$')" 0
sleep 6
mixed=$( (for i in $(seq 1 10); do curl -s -o /dev/null -w 'valid %{http_code}\n' --max-time 10 -u "$U:$PW" $B/api/places & curl -s -o /dev/null -w 'bad %{http_code}\n' --max-time 10 -H "$(basic "$UNI" "x")" $B/api/places & done; wait) )
check "concurrent: a valid login never gets 401 or 5xx" "$(echo "$mixed" | grep -c -E '^valid (401|5..)$')" 0
check "concurrent: some valid logins succeed" "$(echo "$mixed" | grep -c '^valid 200$' | yes_if)" yes
check "concurrent: a rejected login never gets 2xx" "$(echo "$mixed" | grep -c -E '^bad 2')" 0
check "concurrent: rejected logins only 401/429" "$(echo "$mixed" | grep '^bad' | grep -v -c -E '^bad (401|429)$')" 0
sleep 5

if [ "$UPSTREAM" = "--upstream-check" ]; then
  echo "== 5. upstream unavailable"
  docker pause "$EN" >/dev/null
  t=$(code -u "$U:$PW" $B/api/places)
  docker unpause "$EN" >/dev/null
  check "paused engine gives 504" "$t" 504
  sleep 3
  check "engine recovers 200" "$(code -u "$U:$PW" $B/api/places)" 200
fi

echo "== 6. logs and temp files"
{ docker logs --since "$SINCE" "$GW" 2>&1; docker logs --since "$SINCE" "$EN" 2>&1; } > "$TMPD/log"
leaks=0
while IFS= read -r x; do [ -n "$x" ] || continue; n=$(grep -c -F -- "$x" "$TMPD/log" || true); leaks=$((leaks+n)); done < "$TMPD/secrets"
check "canary and credential strings in gateway+engine logs" "$leaks" 0
check "Authorization header text in logs" "$(grep -v '^sabpuja_security ' "$TMPD/log" | grep -c -i -E 'authorization|basic [A-Za-z0-9+/=]{8,}|bearer ' || true)" 0
check "birth data in logs" "$(grep -c -E '1990-05-15|in-new-delhi' "$TMPD/log" || true)" 0
check "auth_basic user lines in logs" "$(grep -c -E 'password mismatch|was not found in' "$TMPD/log" || true)" 0
tmp_hits=0
for c in "$GW" "$EN"; do
  n=$(printf '%s\n' "$CANARY" | docker exec -i "$c" sh -c 'read -r c; grep -rlF -- "$c" /tmp 2>/dev/null | wc -l' 2>/dev/null || echo 0); tmp_hits=$((tmp_hits+n))
done
check "canary in gateway/engine /tmp" "$tmp_hits" 0
echo "-- observability (counts only)"
check "rate limiting still in error log" "$(grep -c 'limiting requests' "$TMPD/log" | yes_if)" yes
for e in auth_failed rate_limited forbidden body_too_large bad_request; do
  check "security event $e logged" "$(grep -c "^sabpuja_security .* event=$e " "$TMPD/log" | yes_if)" yes
done
check "security event lines hold bounded fields only" "$(grep '^sabpuja_security ' "$TMPD/log" | grep -v -c -E '^sabpuja_security time=[0-9T:+-]+ event=(bad_request|auth_failed|forbidden|body_too_large|rate_limited|server_error) status=[0-9]{3} method=(GET|HEAD|POST|OPTIONS|other) path=(page|places|chart|report|static|other) auth_input=(none|basic|other_scheme) upstream_status=[-0-9, :]+ request_time=[0-9.]+$')" 0
if [ "$UPSTREAM" = "--upstream-check" ]; then
  check "upstream timeout still in error log" "$(grep -c 'upstream timed out' "$TMPD/log" | yes_if)" yes
  check "security event server_error 504 logged" "$(grep -c '^sabpuja_security .* event=server_error status=504 ' "$TMPD/log" | yes_if)" yes
fi
echo "security events by class:"; grep '^sabpuja_security ' "$TMPD/log" | sed -E 's/^sabpuja_security time=[^ ]+ //; s/ upstream_status=.*//' | sort | uniq -c | sort -rn
echo "gateway+engine log lines in window: $(grep -c . "$TMPD/log")"
echo "other log line kinds (lines holding a test credential are withheld):"
grep -v '^sabpuja_security ' "$TMPD/log" | while IFS= read -r l; do
  hit=0; while IFS= read -r x; do [ -n "$x" ] && case "$l" in *"$x"*) hit=1; break;; esac; done < "$TMPD/secrets"
  [ $hit = 1 ] && echo '<withheld: line contained a test credential>' || printf '%s\n' "$l"
done | sed -E 's/^[0-9\/: ]+//; s/\*[0-9]+ //; s/, client:.*//; s/excess: [0-9.]+/excess: N/; s/user "[^"]*"/user "<redacted>"/g; s/[^[:print:]]/?/g' | cut -c1-110 | sort | uniq -c | sort -rn | head -12
[ $fail = 0 ] && echo AUTH_LOG_PRIVACY_PASS || { echo AUTH_LOG_PRIVACY_FAIL; exit 1; }
