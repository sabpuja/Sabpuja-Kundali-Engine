#!/usr/bin/env python3
"""KUN-FREEMIUM-QA-DEPLOY-003: remote acceptance of the free preview on the isolated QA host.

Synthetic births only. Python 3 standard library. Nothing is written except the result file.
The QA basic-auth credentials are read from the environment and never printed.

    SBK_QA_BASIC='user:pass' python3 -I preview_acceptance.py \
        --base https://kundali-qa.srv2005300.hstgr.cloud --expected expected-10-cities.json --out result.json

It sends about 22 preview requests, spaced to stay inside the per-connection limit of 6 per minute, and then a short
burst that is expected to be refused (rate limit). It takes about 4 minutes. It creates no order, sends no e-mail and
does not touch the opt-in.
"""
import argparse, base64, json, os, ssl, sys, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", required=True)
    ap.add_argument("--expected", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--spacing", type=float, default=11.0, help="seconds between previews (6/min limit)")
    a = ap.parse_args()
    base = a.base.rstrip("/")
    cred = os.environ.get("SBK_QA_BASIC", "")
    headers = {"Content-Type": "application/json", "Origin": base}
    if cred:
        headers["Authorization"] = "Basic " + base64.b64encode(cred.encode()).decode()
    ctx = ssl.create_default_context()
    results, failures = [], []

    def call(method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, context=ctx, timeout=30) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def check(name, ok, detail=""):
        results.append({"check": name, "pass": bool(ok), "detail": detail})
        if not ok:
            failures.append(name)
        print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))

    def code_of(body):
        try:
            return json.loads(body)["error"]["code"]
        except Exception:
            return None

    # 1. Config and disclosure
    st, body, hdr = call("GET", "/api/preview/config")
    check("config 200", st == 200, str(st))
    cfg = json.loads(body) if st == 200 else {}
    ids = sorted(p["id"] for p in cfg.get("places", []))
    exp = json.load(open(a.expected))["cases"]
    check("exactly the 10 India places", ids == sorted(c["place_id"] for c in exp), ",".join(ids))
    check("date_min 1970-01-01", cfg.get("date_min") == "1970-01-01", str(cfg.get("date_min")))
    check("fields are lagna_rashi, moon_rashi", sorted(cfg.get("fields", [])) == ["lagna_rashi", "moon_rashi"],
          str(cfg.get("fields")))
    check("price is the placeholder (empty)", not cfg.get("price_display"), "price_display set")
    check("QA store flag on", cfg.get("qa_store") is True, str(cfg.get("qa_store")))
    check("buy_url is the QA store", str(cfg.get("buy_url", "")).startswith("https://sabpuja-qa.myshopify.com/"),
          str(cfg.get("buy_url")))
    st, page, _ = call("GET", "/kundali")
    text = page.decode("utf-8", "replace")
    check("/kundali 200", st == 200, str(st))
    check("page discloses 1970 and exact time before input",
          "1 January 1970" in text and text.find("1 January 1970") < text.find('id="preview-form"'))
    check("QA banner present in page", 'id="qa-banner"' in text)

    # 2. Ten cities: values equal the offline engine run at the same SHA
    for c in exp:
        time.sleep(a.spacing)
        st, body, _ = call("POST", "/api/preview", {"place_id": c["place_id"], "birth_date": c["birth_date"],
                                                    "birth_time": c["birth_time"]})
        name = f"preview {c['place_id']}"
        if st != 200:
            check(name, False, f"status {st} {code_of(body)}")
            continue
        r = json.loads(body)
        got = (r["fields"]["lagna_rashi"]["rashi"], r["fields"]["moon_rashi"]["rashi"])
        check(name + " Lagna/Moon equal offline reference", got == (c["lagna"], c["moon"]),
              f"got {got} expected {(c['lagna'], c['moon'])}")
        check(name + " response shape", sorted(r) == ["fields", "method", "preview_version"]
              and sorted(r["fields"]) == ["lagna_rashi", "moon_rashi"], ",".join(sorted(r)))
        f = r["fields"]
        check(name + " only Rashi name and number, method and version",
              all(sorted(v) == ["number", "rashi"] and isinstance(v["number"], int) for v in f.values())
              and r["method"] == "sidereal_lahiri_swiss_ephemeris" and "." not in json.dumps(f))

    # 3. Refusals (each spaced)
    refusals = [
        ("pre-1970 refused", {"place_id": "in-jaipur", "birth_date": "1969-12-31", "birth_time": "12:00:00"},
         None, (422,), "HISTORICAL_CLOCK_UNVERIFIED"),
        ("future date refused", {"place_id": "in-jaipur", "birth_date": "2099-01-01", "birth_time": "12:00:00"},
         None, (422,), "BIRTH_DATE_FUTURE"),
        ("unsupported place refused", {"place_id": "gb-london", "birth_date": "1990-05-17", "birth_time": "14:30:00"},
         None, (400, 404, 422), None),
        ("missing time refused", {"place_id": "in-jaipur", "birth_date": "1990-05-17"}, None, (400,), "REQUEST_INVALID"),
        ("extra key (name) refused", {"place_id": "in-jaipur", "birth_date": "1990-05-17", "birth_time": "14:30:00",
                                      "name": "Synthetic"}, None, (400,), "REQUEST_INVALID"),
        ("malformed time refused", {"place_id": "in-jaipur", "birth_date": "1990-05-17", "birth_time": "25:61"},
         None, (400, 422), None),
        ("duplicate keys refused", None, b'{"place_id":"in-jaipur","place_id":"in-mumbai","birth_date":"1990-05-17",'
                                         b'"birth_time":"14:30:00"}', (400,), "REQUEST_INVALID"),
        ("oversized body refused", None, b'{"place_id":"' + b"x" * 2000 + b'"}', (413,), None),
    ]
    for name, body_obj, raw, statuses, code in refusals:
        time.sleep(a.spacing)
        st, body, _ = call("POST", "/api/preview", body_obj, raw)
        ok = st in statuses and (code is None or code_of(body) == code)
        check(name, ok, f"status {st} code {code_of(body)}")

    # 4. Rate limit: a burst of 8 from this connection must include 429s and no 5xx
    time.sleep(65)
    one = {"place_id": "in-jaipur", "birth_date": "1990-05-17", "birth_time": "14:30:00"}
    with ThreadPoolExecutor(max_workers=8) as ex:
        statuses = list(ex.map(lambda _: call("POST", "/api/preview", one)[0], range(8)))
    check("burst of 8: some refused with 429, none 5xx", 429 in statuses and not any(s >= 500 for s in statuses),
          ",".join(map(str, statuses)))

    out = {"base": base, "ran_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "results": results,
           "failures": failures}
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"\n{len(results) - len(failures)}/{len(results)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
