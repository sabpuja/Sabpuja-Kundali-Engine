#!/bin/bash
# Isolated QA runner for report_locale through the gateway (KUN-I18N-001; committed in KUN-I18N-002,
# setup copied from preview/tests/name-privacy-stack.sh). QA tool only, not a CI job.
# Brings up preview/compose.yml from SRC_DIR on a throwaway Docker network with a throwaway
# synthetic htpasswd user, then checks over HTTP (curl):
#   A. omitted and explicit "en" give identical bytes; Hindi PDFs (anonymous, Devanagari name,
#      Latin name): ten pages, Hindi cover and positions, same longitudes as English, /Lang hi,
#      generic filename, no-store, no locale or name in headers
#   B. unsupported locales refused (422, not echoed), non-string 400, /api/chart refuses the
#      field and keeps schema 0.3.0, 401 without login, 403 foreign Origin, catalog behind login
#   C. gateway and engine logs and container file systems hold no locale, name or birth details
# and removes everything, shredding the credential files. Never point it at a live deployment.
#
#   locale-privacy-stack.sh SRC_DIR ENGINE_IMAGE EPHE_DIR [OUT_DIR]
#
# Needs docker, curl, openssl, a Python with PyMuPDF on the host (QA_PYTHON, default python3),
# root for shred. Requests are spaced 1.2 s apart: the gateway allows /api/chart and /api/report
# at 1 request per second per client (burst 1), and this script tests the engine, not that limit.
set -u
SRC=$(cd "$1" && pwd); IMG=$2; EPHE=$3; OUT=${4:-}
NET=${NAME_QA_NETWORK:-kun-i18n-qa}; SUB=${NAME_QA_SUBNET:-172.31.251}
P=$NET; W=$(mktemp -d); chmod 755 "$W"
ENG=$SUB.10; B=http://$ENG:8080
export NO_PROXY="$ENG,${NO_PROXY:-}" no_proxy="$ENG,${no_proxy:-}"
PY=${QA_PYTHON:-python3}
CANARY="Zzyzx Qwertyuiop"; HINDI="क्षत्रिय प्रियंका सिद्धार्थ"
fail=0
check(){ if [ "$2" = "$3" ]; then echo "PASS $1 ($2)"; else echo "FAIL $1 (got $2, want $3)"; fail=1; fi; }
C(){ (cd "$SRC" && docker compose -p "$P" --env-file "$W/qa.env" -f preview/compose.yml -f "$W/override.yml" "$@"); }
GW=$P-gateway-1; EN=$P-engine-1
cleanup(){ C down >/dev/null 2>&1; docker network rm "$NET" >/dev/null 2>&1; shred -u "$W"/qa-password "$W"/htpasswd 2>/dev/null; rm -rf "$W"; }
trap cleanup EXIT
wait_up(){ for i in $(seq 120); do [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 $B/)" = 401 ] && return 0; sleep 1; done; return 1; }

mkdir -p "$W/ephe" && cp "$EPHE"/se*_18.se1 "$W/ephe/" && chmod 0755 "$W/ephe" && chmod 0644 "$W"/ephe/*
openssl rand -hex 24 > "$W/qa-password"; chmod 600 "$W/qa-password"
U="kunqa-$(openssl rand -hex 3)"
printf '%s:%s\n' "$U" "$(openssl passwd -apr1 -stdin < "$W/qa-password")" > "$W/htpasswd"; chmod 0644 "$W/htpasswd"
echo "\"$B\" 0;" > "$W/allowed-origins.map"; echo "set_real_ip_from 127.0.0.1;" > "$W/trusted-proxy.conf"; chmod 0644 "$W"/*.map "$W"/*.conf
docker network create --subnet "$SUB.0/24" "$NET" >/dev/null
printf 'services:\n  engine:\n    image: %s\n    networks:\n      edge:\n        ipv4_address: %s\n' "$IMG" "$ENG" > "$W/override.yml"
printf 'SABPUJA_PREVIEW_EPHE_DIR=%s/ephe\nSABPUJA_PREVIEW_NETWORK=%s\nSABPUJA_PREVIEW_HTPASSWD_FILE=%s/htpasswd\nSABPUJA_PREVIEW_ALLOWED_ORIGINS_FILE=%s/allowed-origins.map\nSABPUJA_PREVIEW_TRUSTED_PROXY_FILE=%s/trusted-proxy.conf\n' "$W" "$NET" "$W" "$W" "$W" > "$W/qa.env"
SINCE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
C up -d --no-build >/dev/null 2>&1; wait_up || { echo "FAIL stack did not start"; exit 1; }
echo "== source $(git -C "$SRC" rev-parse HEAD 2>/dev/null || echo archive), image $(docker inspect -f '{{.Id}}' "$IMG")"
AUTH=(-u "$U:$(cat "$W/qa-password")")
post(){ # post OUTFILE JSON [extra curl args]: prints status
  local out=$1 body=$2 hdr; shift 2
  sleep 1.2
  hdr="$out.h"; [ "$out" = /dev/null ] && hdr=/dev/null
  curl -s -o "$out" -D "$hdr" -w '%{http_code}' --max-time 60 "${AUTH[@]}" -H "Origin: $B" -H 'Content-Type: application/json' \
       --data-binary "$body" "$@" "$B/api/report"; }
birth='"place_id":"in-new-delhi","birth_date":"1990-05-15","birth_time":"10:30"'
json(){ "$PY" -c 'import json,sys; print(json.dumps(sys.argv[1], ensure_ascii=False))' "$1"; }

echo; echo "######## A. anonymous and named PDFs"
check "anonymous report 200" "$(post "$W/anon.pdf" "{$birth}")" 200

echo; echo "######## A. English unchanged, Hindi edition"
check "omitted locale 200" "$(post "$W/en0.pdf" "{$birth}")" 200
check "explicit en 200" "$(post "$W/en1.pdf" "{$birth,\"report_locale\":\"en\"}")" 200
check "explicit en bytes identical to omitted" "$(cmp -s "$W/en0.pdf" "$W/en1.pdf" && echo same || echo differ)" same
for label in anon hindi latin; do
  extra=""; [ $label = hindi ] && extra=",\"display_name\":$(json "$HINDI")"; [ $label = latin ] && extra=",\"display_name\":$(json "$CANARY")"
  check "hi report ($label) 200" "$(post "$W/hi-$label.pdf" "{$birth,\"report_locale\":\"hi\"$extra}")" 200
  check "hi report ($label) filename generic" "$(grep -ci 'content-disposition: attachment; filename="Sabpuja-Janma-Kundali.pdf"' "$W/hi-$label.pdf.h")" 1
  check "hi report ($label) no-store" "$(grep -ci '^cache-control: no-store' "$W/hi-$label.pdf.h" | awk '{print ($1>0)?"yes":"no"}')" yes
  check "hi report ($label) no locale or name in headers" "$(grep -c -i -e report_locale -e Zzyzx -e hindi "$W/hi-$label.pdf.h" || true)" 0
  r=$("$PY" - "$W/hi-$label.pdf" "$W/en0.pdf" <<'EOF'
import re, sys, fitz
hi, en = fitz.open(sys.argv[1]), fitz.open(sys.argv[2])
num = re.compile(r'\d+\.\d{8}°')
same = sorted(num.findall(hi[6].get_text())) == sorted(num.findall(en[6].get_text()))
lang = hi.xref_get_key(hi.pdf_catalog(), 'Lang')[1]
print(len(hi), 'जन्म कुंडली' in hi[0].get_text(), 'ग्रहों की स्थिति' in hi[6].get_text() or 'ग्रह' in hi[6].get_text(), same, lang)
EOF
)
  check "hi report ($label): pages, Hindi cover, Hindi positions, same longitudes, /Lang" "$r" "10 True True True hi"
done
[ -n "$OUT" ] && { mkdir -p "$OUT"; cp "$W/en0.pdf" "$OUT/gateway-en.pdf"; cp "$W/hi-anon.pdf" "$OUT/gateway-hi-anonymous.pdf"; cp "$W/hi-hindi.pdf" "$OUT/gateway-hi-named-hindi.pdf"; cp "$W/hi-latin.pdf" "$OUT/gateway-hi-named-latin.pdf"; }

echo; echo "######## B. refusals and the unchanged chart API"
for bad in "fr" "HI" "hi-IN" "<script>x</script>" "$CANARY"; do
  s=$(post "$W/bad.json" "{$birth,\"report_locale\":$(json "$bad")}")
  check "unsupported locale 422" "$s $("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["error"]["code"])' "$W/bad.json")" "422 REPORT_LOCALE_UNSUPPORTED"
  check "unsupported locale not echoed" "$(grep -c -F -e Zzyzx -e '<script>' -e fr\" -e hi-IN "$W/bad.json" || true)" 0
done
s=$(post "$W/bad.json" "{$birth,\"report_locale\":7}")
check "non-string locale 400" "$s" 400
sleep 1.2; s=$(curl -s -o "$W/chart.json" -w '%{http_code}' "${AUTH[@]}" -H "Origin: $B" -H 'Content-Type: application/json' --data-binary "{$birth,\"report_locale\":\"hi\"}" $B/api/chart)
check "/api/chart refuses report_locale" "$s $("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["error"]["code"])' "$W/chart.json")" "400 REQUEST_INVALID"
sleep 1.2; s=$(curl -s -o "$W/chart.json" -w '%{http_code}' "${AUTH[@]}" -H "Origin: $B" -H 'Content-Type: application/json' --data-binary "{$birth}" $B/api/chart)
check "/api/chart schema" "$s $("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["chart"]["schema_version"])' "$W/chart.json")" "200 0.3.0"
sleep 1.2; check "no login 401" "$(curl -s -o /dev/null -w '%{http_code}' -H "Origin: $B" -H 'Content-Type: application/json' --data-binary "{$birth,\"report_locale\":\"hi\"}" $B/api/report)" 401
sleep 1.2; check "foreign Origin 403" "$(curl -s -o /dev/null -w '%{http_code}' "${AUTH[@]}" -H 'Origin: https://evil.example' -H 'Content-Type: application/json' --data-binary "{$birth,\"report_locale\":\"hi\"}" $B/api/report)" 403
sleep 1.2; s=$(curl -s -o "$W/i18n.json" -w '%{http_code}' "${AUTH[@]}" $B/static/i18n.json)
check "catalog served behind login" "$s $("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["default_locale"])' "$W/i18n.json")" "200 en"
sleep 1.2; check "catalog requires login" "$(curl -s -o /dev/null -w '%{http_code}' $B/static/i18n.json)" 401

echo; echo "######## C. logs and file systems"
L=$(docker logs --since "$SINCE" "$GW" 2>&1; docker logs --since "$SINCE" "$EN" 2>&1)
echo "log lines: $(printf '%s\n' "$L" | grep -c .)"
printf '%s\n' "$L" | sed -E 's/time=[^ ]+/time=T/; s/request_time=[^ ]+/request_time=R/' | sort | uniq -c | sed 's/^/  /'
check "locale, names or markup in gateway/engine logs" "$(printf '%s' "$L" | grep -c -F -e report_locale -e Zzyzx -e Qwertyuiop -e "क्षत्रिय" -e "<script>" -e hi-IN -e display_name || true)" 0
check "birth details in logs" "$(printf '%s' "$L" | grep -c -F -e 1990-05-15 -e in-new-delhi || true)" 0
for c in "$GW" "$EN"; do
  m=$(docker inspect -f '{{range .Mounts}}{{.Destination}} {{end}}' "$c")
  n=$(docker diff "$c" | while read -r k f; do case "$f" in /tmp|/tmp/*) continue;; esac; s=0; for d in $m; do case "$d/" in "$f"/*) s=1;; esac; done; [ $s = 1 ] || echo "$f"; done | grep -c . || true)
  check "$c writes nothing outside mounts and tmpfs" "$n" 0
  check "$c /tmp holds no PDF or name" "$(docker exec "$c" sh -c 'grep -rl -e Zzyzx -e %PDF /tmp 2>/dev/null | wc -l')" 0
done

echo; [ $fail = 0 ] && echo LOCALE_STACK_PASS || { echo LOCALE_STACK_FAIL; exit 1; }
