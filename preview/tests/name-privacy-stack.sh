#!/bin/bash
# KUN-UX-NAME-001 isolated QA runner for the optional report name through the gateway.
# Brings up preview/compose.yml from SRC_DIR on a throwaway Docker network with a throwaway
# synthetic htpasswd user, then checks over HTTP (curl):
#   A. anonymous and named /api/report PDFs (ten pages, name on cover and page 4, generic filename)
#   B. refused names (422, no echo), /api/chart still refuses the field, schema 0.3.0 unchanged
#   C. 401 without login, 403 foreign Origin, 413 oversized body, 429 concurrent renders, with a name
#   D. gateway and engine logs and container file systems contain no synthetic name
# and removes everything, shredding the credential files. Never point it at a live deployment.
#
#   name-privacy-stack.sh SRC_DIR ENGINE_IMAGE EPHE_DIR [OUT_DIR]
#
# Needs docker, curl, openssl, a Python with PyMuPDF on the host (QA_PYTHON, default python3),
# root for shred. Requests are spaced 1.2 s apart: the gateway allows /api/chart and /api/report
# at 1 request per second per client (burst 1), and this script tests the engine, not that limit.
set -u
SRC=$(cd "$1" && pwd); IMG=$2; EPHE=$3; OUT=${4:-}
NET=${NAME_QA_NETWORK:-kun-name-qa}; SUB=${NAME_QA_SUBNET:-172.31.252}
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
for label in canary hindi; do
  name=$CANARY; [ $label = hindi ] && name=$HINDI
  check "named report ($label) 200" "$(post "$W/$label.pdf" "{$birth,\"display_name\":$(json "$name")}")" 200
  check "named report ($label) filename generic" "$(grep -ci 'content-disposition: attachment; filename="Sabpuja-Janma-Kundali.pdf"' "$W/$label.pdf.h")" 1
  check "named report ($label) no-store" "$(grep -ci '^cache-control: no-store' "$W/$label.pdf.h" | awk '{print ($1>0)?"yes":"no"}')" yes
  check "named report ($label) name not in headers" "$(grep -c -F "$(echo "$name" | cut -d' ' -f1)" "$W/$label.pdf.h" || true)" 0
  r=$("$PY" - "$W/$label.pdf" "$W/anon.pdf" "$name" <<'EOF'
import sys, fitz
pdf, anon, name = fitz.open(sys.argv[1]), fitz.open(sys.argv[2]), sys.argv[3]
same = all(pdf[i].get_text('words') == anon[i].get_text('words') for i in (1, 2, 4, 5, 6, 7, 8, 9))
meta = any(w in (v or '') for v in pdf.metadata.values() for w in name.split())
print(len(pdf), name in pdf[0].get_text(), name in pdf[3].get_text(), same, meta)
EOF
)
  check "named report ($label): pages, cover, page 4, other pages unchanged, metadata" "$r" "10 True True True False"
done
[ -n "$OUT" ] && { mkdir -p "$OUT"; cp "$W/anon.pdf" "$OUT/gateway-anonymous.pdf"; cp "$W/canary.pdf" "$OUT/gateway-named-latin.pdf"; cp "$W/hindi.pdf" "$OUT/gateway-named-hindi.pdf"; }

echo; echo "######## B. refusals and the unchanged chart API"
for bad in "<script>x</script>$CANARY" "$CANARY
x" "‮$CANARY" "$(printf 'A%.0s' $(seq 81))"; do
  s=$(post "$W/bad.json" "{$birth,\"display_name\":$(json "$bad")}")
  check "refused name 422" "$s" 422
  check "refused name not echoed" "$(grep -c -F -e Zzyzx -e AAAAAAAAAA "$W/bad.json" || true)" 0
done
sleep 1.2; s=$(curl -s -o "$W/chart.json" -w '%{http_code}' "${AUTH[@]}" -H "Origin: $B" -H 'Content-Type: application/json' --data-binary "{$birth,\"display_name\":\"Asha\"}" $B/api/chart)
check "/api/chart still refuses display_name" "$s $("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["error"]["code"])' "$W/chart.json")" "400 REQUEST_INVALID"
sleep 1.2; s=$(curl -s -o "$W/chart.json" -w '%{http_code}' "${AUTH[@]}" -H "Origin: $B" -H 'Content-Type: application/json' --data-binary "{$birth}" $B/api/chart)
check "/api/chart schema" "$s $("$PY" -c 'import json,sys;print(json.load(open(sys.argv[1]))["chart"]["schema_version"])' "$W/chart.json")" "200 0.3.0"

echo; echo "######## C. authentication, Origin, size and concurrency with a name"
nb="{$birth,\"display_name\":$(json "$CANARY")}"
sleep 1.2; check "no login 401" "$(curl -s -o /dev/null -w '%{http_code}' -H "Origin: $B" -H 'Content-Type: application/json' --data-binary "$nb" $B/api/report)" 401
sleep 1.2; check "foreign Origin 403" "$(curl -s -o /dev/null -w '%{http_code}' "${AUTH[@]}" -H 'Origin: https://evil.example' -H 'Content-Type: application/json' --data-binary "$nb" $B/api/report)" 403
big=$("$PY" -c "import json; print(json.dumps({'place_id':'in-new-delhi','birth_date':'1990-05-15','birth_time':'10:30','display_name':'A'*5000}))")
check "oversized body 413" "$(post /dev/null "$big")" 413
sleep 2
for i in 1 2; do curl -s -o "$W/c$i" -w '%{http_code}\n' --max-time 60 "${AUTH[@]}" -H "Origin: $B" -H 'Content-Type: application/json' --data-binary "$nb" $B/api/report > "$W/c$i.s" & done; wait
r=$(for i in 1 2; do printf '%s:%s ' "$(cat "$W/c$i.s")" "$(grep -o REPORT_BUSY "$W/c$i" || head -c 5 "$W/c$i")"; done | tr ' ' '\n' | sort | tr '\n' ' ')
check "two concurrent named renders: one PDF, one engine REPORT_BUSY" "$r" "200:%PDF- 429:REPORT_BUSY "

echo; echo "######## D. logs and file systems"
L=$(docker logs --since "$SINCE" "$GW" 2>&1; docker logs --since "$SINCE" "$EN" 2>&1)
echo "log lines: $(printf '%s\n' "$L" | grep -c .)"
printf '%s\n' "$L" | sed -E 's/time=[^ ]+/time=T/; s/request_time=[^ ]+/request_time=R/' | sort | uniq -c | sed 's/^/  /'
check "synthetic names in gateway/engine logs" "$(printf '%s' "$L" | grep -c -F -e Zzyzx -e Qwertyuiop -e "क्षत्रिय" -e "<script>" -e display_name || true)" 0
check "birth details in logs" "$(printf '%s' "$L" | grep -c -F -e 1990-05-15 -e in-new-delhi || true)" 0
for c in "$GW" "$EN"; do
  m=$(docker inspect -f '{{range .Mounts}}{{.Destination}} {{end}}' "$c")
  n=$(docker diff "$c" | while read -r k f; do case "$f" in /tmp|/tmp/*) continue;; esac; s=0; for d in $m; do case "$d/" in "$f"/*) s=1;; esac; done; [ $s = 1 ] || echo "$f"; done | grep -c . || true)
  check "$c writes nothing outside mounts and tmpfs" "$n" 0
  check "$c /tmp holds no name" "$(docker exec "$c" sh -c 'grep -rl -e Zzyzx -e Qwertyuiop /tmp 2>/dev/null | wc -l')" 0
done

echo; echo "######## E. existing gateway smokes against the same stack (if Node and Playwright are available)"
if node -e "require('playwright')" >/dev/null 2>&1; then
  for t in security-smoke pdf-download-smoke browser-smoke; do
    sleep 2
    QA_ORIGIN=$B QA_USER=$U QA_PASSWORD=$(cat "$W/qa-password") node "$SRC/preview/tests/$t.cjs" > "$W/$t.log" 2>&1
    rc=$?; sed "s/$U/<qa-user>/g" "$W/$t.log" | tail -n 6 | sed "s/^/  /"
    check "$t exit status" "$rc" 0
  done
else
  echo "SKIP: node with playwright unavailable"
fi
L=$(docker logs --since "$SINCE" "$GW" 2>&1; docker logs --since "$SINCE" "$EN" 2>&1)
check "synthetic names in logs after every step" "$(printf '%s' "$L" | grep -c -F -e Zzyzx -e Qwertyuiop -e "क्षत्रिय" -e display_name || true)" 0

echo; [ $fail = 0 ] && echo NAME_STACK_PASS || { echo NAME_STACK_FAIL; exit 1; }
