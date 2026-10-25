/* Browser QA for the prototype: starts the real server (real engine and Swiss data)
 * and drives Chromium at desktop and mobile sizes.
 *
 *   SABPUJA_TEST_EPHE_PATH=/path/to/ephe PROTOTYPE_PYTHON=/path/to/python \
 *     node prototype/tests/browser/e2e.cjs --out /tmp/gate3b-shots
 *
 * Needs Node and the `playwright` package with Chromium (not a runtime
 * dependency of the prototype). Exit 0 only if every check passes.
 */
"use strict";
const { chromium } = require("playwright");
const { spawn, spawnSync } = require("child_process");
const fs = require("fs");
const net = require("net");
const path = require("path");
const crypto = require("crypto");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const outIdx = process.argv.indexOf("--out");
const OUT = outIdx > 0 ? process.argv[outIdx + 1] : path.join(ROOT, "prototype-shots");
const EPHE = process.env.SABPUJA_TEST_EPHE_PATH;
const PYTHON = process.env.PROTOTYPE_PYTHON || "python3";
if (!EPHE) { console.log("UNAVAILABLE: SABPUJA_TEST_EPHE_PATH unset; browser QA needs real Swiss data"); process.exit(3); }
fs.mkdirSync(OUT, { recursive: true });

const results = [];
function check(view, name, ok, detail) {
  results.push({ view, name, ok: !!ok, detail: ok ? undefined : detail });
  console.log(`${ok ? "PASS" : "FAIL"} [${view}] ${name}${ok ? "" : " :: " + JSON.stringify(detail)}`);
}

function freePort() {
  return new Promise((resolve) => { const s = net.createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => resolve(p)); }); });
}

async function startServer(port, ephe = EPHE) {
  const env = { PATH: process.env.PATH, SABPUJA_EPHE_PATH: ephe, PYTHONDONTWRITEBYTECODE: "1",
                PYTHONPATH: `${path.join(ROOT, "src")}:${path.join(ROOT, "prototype")}` };
  const proc = spawn(PYTHON, ["-m", "kundali_prototype", "--port", String(port)], { env, cwd: ROOT });
  let output = "";
  proc.stdout.on("data", (d) => { output += d; });
  proc.stderr.on("data", (d) => { output += d; });
  for (let i = 0; i < 300 && !output.includes("http://127.0.0.1:"); i++) { await new Promise((r) => setTimeout(r, 100)); }
  if (!output.includes("http://127.0.0.1:")) { throw new Error("server did not start: " + output); }
  return { proc, output: () => output };
}

// Graha names as chart.js writes them into the SVG description.
const SABPUJA_NAMES = { sun: "Sun (Surya)", moon: "Moon (Chandra)", mars: "Mars (Mangal)", mercury: "Mercury (Budha)",
                        jupiter: "Jupiter (Guru)", venus: "Venus (Shukra)", saturn: "Saturn (Shani)",
                        rahu_mean: "Rahu (mean node)", ketu_mean: "Ketu (opposite mean Rahu)" };
const SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"];
const BODIES = ["sun", "moon", "mars", "mercury", "jupiter", "venus", "saturn", "rahu_mean", "ketu_mean"];

async function fillAndSubmit(page, placeId, date, time) {
  await page.selectOption("#place", placeId);
  await page.fill("#birth-date", date);
  await page.fill("#birth-time", time);
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/api/chart") && r.request().method() === "POST"),
    page.click("#submit")
  ]);
  const body = await resp.json();
  if (resp.status() === 200) { received.push(body); }
  return { status: resp.status(), body };
}

// Every chart the browser received, for the Gate 3D comparison with the engine CLI.
const received = [];
function canon(v) {
  if (Array.isArray(v)) { return "[" + v.map(canon).join(",") + "]"; }
  if (v && typeof v === "object") { return "{" + Object.keys(v).sort().map((k) => JSON.stringify(k) + ":" + canon(v[k])).join(",") + "}"; }
  return JSON.stringify(v);
}

/* Gate 3D: browser charts equal the hardened engine CLI, and a real server-side
 * fault (pinned data corrupted after a READY start-up) shows a controlled 503 with
 * no chart, after which the next valid chart is unchanged. */
function cliChart(input) {
  const req = { birth_datetime: `${input.local_date}T${input.local_time}${input.utc_offset}`, timezone: input.place.timezone,
                latitude: input.place.latitude, longitude: input.place.longitude };
  const env = { PATH: process.env.PATH, SABPUJA_EPHE_PATH: EPHE, PYTHONDONTWRITEBYTECODE: "1", PYTHONPATH: path.join(ROOT, "src") };
  const r = spawnSync(PYTHON, ["-m", "sabpuja_kundali.cli"], { input: JSON.stringify(req), env, cwd: ROOT });
  return { status: r.status, stderr: String(r.stderr), chart: r.status === 0 ? JSON.parse(String(r.stdout)) : null };
}

function cliChecks() {
  const seen = new Map();
  received.forEach((b) => seen.set(canon(b.input), b));
  const bad = [];
  for (const b of seen.values()) {
    const cli = cliChart(b.input);
    if (cli.status !== 0 || cli.stderr !== "" || canon(cli.chart) !== canon(b.chart)) { bad.push({ input: b.input, status: cli.status }); }
  }
  check("gate3d", `every chart the browser received (${seen.size} distinct) equals the hardened engine CLI output`,
        seen.size >= 12 && bad.length === 0, { distinct: seen.size, bad });
}

async function serverFaultChecks(browser) {
  const tmp = fs.mkdtempSync(path.join(require("os").tmpdir(), "gate3d-ephe-"));
  for (const f of ["sepl_18.se1", "semo_18.se1"]) { fs.copyFileSync(path.join(EPHE, f), path.join(tmp, f)); }
  const port = await freePort();
  const srv = await startServer(port, tmp);
  const base = `http://127.0.0.1:${port}`;
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
  const mobile = await browser.newContext({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const semo = path.join(tmp, "semo_18.se1"), original = fs.readFileSync(semo);
  try {
    for (const [view, ctx] of [["desktop", context], ["mobile", mobile]]) {
      const page = await ctx.newPage();
      const unexpected = [];
      page.on("console", (m) => {
        if (m.type() === "error" && !/^Failed to load resource: the server responded with a status of (500|503) /.test(m.text())) { unexpected.push(m.text()); }
      });
      page.on("pageerror", (e) => unexpected.push(String(e)));
      await page.goto(base + "/");
      await page.waitForSelector("#place optgroup", { state: "attached" });
      const before = await fillAndSubmit(page, "in-new-delhi", "1990-05-15", "10:30:00");
      await page.waitForSelector("#result:not([hidden])");
      // Corrupt one byte of the pinned Moon file under the running server (real fault, real server).
      const bad = Buffer.from(original); bad[Math.floor(bad.length / 2)] ^= 0x01; fs.writeFileSync(semo, bad);
      await page.click("#edit");
      const fault = await fillAndSubmit(page, "in-mumbai", "1984-11-02", "23:59:59");
      await page.waitForSelector("#error-card:not([hidden])");
      const shown = await page.evaluate(() => ({ code: document.getElementById("error-code").textContent,
        resultHidden: document.getElementById("result").hidden, text: document.getElementById("error-message").textContent,
        page: document.body.innerText }));
      const leaks = ["1984-11-02", "23:59:59", "19.0", "72.8", tmp, "Traceback", "semo_18"].filter((m) => JSON.stringify(fault.body).includes(m));
      check(view, "real ephemeris corruption after start-up: HTTP 503 EPHEMERIS_FILE_MISMATCH, category resources, no chart, nothing echoed",
            fault.status === 503 && fault.body.error && fault.body.error.code === "EPHEMERIS_FILE_MISMATCH" &&
            fault.body.error.category === "resources" && !("chart" in fault.body) && leaks.length === 0 &&
            shown.code === "EPHEMERIS_FILE_MISMATCH" && shown.resultHidden && /not available on this computer/.test(shown.text),
            { status: fault.status, body: fault.body, shown: { code: shown.code, text: shown.text }, leaks });
      await page.screenshot({ path: path.join(OUT, `${view}-12-error-server-resources-503.png`), fullPage: true });
      // Restore the file: the next valid request gives exactly the chart from before the fault.
      fs.writeFileSync(semo, original);
      const after = await fillAndSubmit(page, "in-new-delhi", "1990-05-15", "10:30:00");
      await page.waitForSelector("#result:not([hidden])");
      check(view, "after the 503 the next valid chart is byte-identical to the chart before the fault",
            after.status === 200 && canon(after.body) === canon(before.body), { status: after.status });
      await verifyRender(page, view, "after server fault", after.body.chart);
      check(view, "server-fault page: no unexpected console errors", unexpected.length === 0, unexpected);
      await page.close();
    }
  } finally {
    fs.writeFileSync(semo, original);
    await context.close(); await mobile.close();
    srv.proc.kill("SIGTERM");
    await new Promise((r) => setTimeout(r, 300));
    fs.rmSync(tmp, { recursive: true, force: true });
  }
  check("gate3d", "fault server printed nothing about requests (banner only)",
        srv.output().trim().split("\n").length === 1 && !srv.output().includes("1984-11-02"), srv.output());
}

/* Compare the rendered chart and tables with the engine JSON the page received. */
async function verifyRender(page, view, label, chart, opts = {}) {
  const dom = await page.evaluate(() => {
    function inside(pt, poly) {
      let c = false;
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const [xi, yi] = poly[i], [xj, yj] = poly[j];
        if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi) { c = !c; }
      }
      return c;
    }
    // Gate 3E: the same geometry checks for the D1 and the D9 SVG.
    function chartDom(sel) {
      const svg = document.querySelector(sel);
      const houses = [...svg.querySelectorAll("g.house")].map((g) => ({
        house: Number(g.dataset.house), sign: g.dataset.sign,
        signNumber: g.querySelector("[data-role=sign-number]").textContent,
        grahas: [...g.querySelectorAll("text[data-graha]")].map((t) => t.dataset.graha).sort()
      }));
      const outside = [];
      const boxes = [];
      svg.querySelectorAll("g.house").forEach((g) => {
        const poly = g.querySelector("polygon").getAttribute("points").split(" ").map((p) => p.split(",").map(Number));
        g.querySelectorAll("text").forEach((t) => {
          const b = t.getBBox();
          const corners = [[b.x, b.y], [b.x + b.width, b.y], [b.x, b.y + b.height], [b.x + b.width, b.y + b.height]];
          if (!corners.every((c) => inside(c, poly))) { outside.push({ house: g.dataset.house, text: t.textContent, b: [b.x, b.y, b.width, b.height] }); }
          boxes.push({ house: g.dataset.house, text: t.textContent, b: [b.x, b.y, b.x + b.width, b.y + b.height] });
        });
      });
      const overlaps = [];
      for (let i = 0; i < boxes.length; i++) {
        for (let j = i + 1; j < boxes.length; j++) {
          const a = boxes[i].b, c = boxes[j].b;
          if (a[0] < c[2] && c[0] < a[2] && a[1] < c[3] && c[1] < a[3]) { overlaps.push([boxes[i].text, boxes[j].text, boxes[i].house]); }
        }
      }
      const ids = (svg.getAttribute("aria-labelledby") || "").split(" ");
      const named = ids.map((id) => document.getElementById(id));
      return { houses, outside, overlaps, role: svg.getAttribute("role"), labelledBy: ids,
               labelsInside: named.every((n) => n && svg.contains(n)),
               title: (svg.querySelector("title") || {}).textContent, desc: (svg.querySelector("desc") || {}).textContent,
               width: svg.getBoundingClientRect().width };
    }
    const d1Chart = chartDom("#d1-chart"), d9Chart = chartDom("#d9-chart");
    const { houses, outside, overlaps } = d1Chart;
    const rows = (sel, f) => Object.fromEntries([...document.querySelectorAll(sel + " tbody tr")].map((tr) =>
      [tr.dataset.graha, Object.fromEntries([...tr.querySelectorAll("[data-field]")].map((c) => [c.dataset.field, c.textContent]))]));
    const facts = Object.fromEntries([...document.querySelectorAll("dd[data-field]")].map((d) => [d.dataset.field, d.textContent]));
    return { houses, outside, overlaps, d1Chart, d9Chart, d1: rows("#d1-table"), d9: rows("#d9-table"), facts,
             overflow: document.documentElement.scrollWidth - window.innerWidth,
             tableOverflow: [...document.querySelectorAll(".table-scroll")].map((t) => t.scrollWidth - t.clientWidth),
             tableRegions: [...document.querySelectorAll(".table-scroll")].map((t) => t.tabIndex === 0 && t.getAttribute("role") === "region" &&
               !!document.getElementById(t.getAttribute("aria-labelledby"))),
             claim: document.getElementById("claim").textContent };
  });

  const lagnaIdx = SIGNS.indexOf(chart.lagna.rashi);
  const houseErrors = [];
  dom.houses.forEach((h) => {
    const idx = (lagnaIdx + h.house - 1) % 12;
    const expected = BODIES.filter((b) => chart.planets[b].whole_sign_house === h.house);
    if (h.house === 1) { expected.push("lagna"); }
    if (h.sign !== SIGNS[idx] || h.signNumber !== String(idx + 1) || JSON.stringify(h.grahas) !== JSON.stringify(expected.sort())) {
      houseErrors.push({ house: h.house, dom: h, expectedSign: SIGNS[idx], expected });
    }
  });
  check(view, `${label}: D1 chart houses, signs and grahas equal engine JSON`, dom.houses.length === 12 && houseErrors.length === 0, houseErrors);
  check(view, `${label}: every chart label inside its house (no clipping)`, dom.outside.length === 0, dom.outside);
  check(view, `${label}: no overlapping chart labels`, dom.overlaps.length === 0, dom.overlaps);
  check(view, `${label}: D1 SVG title and description unchanged in form`, dom.d1Chart.role === "img" && dom.d1Chart.labelsInside &&
        dom.d1Chart.labelledBy.join(" ") === "d1-title d1-desc" && dom.d1Chart.title === `North Indian D1 chart, Lagna ${chart.lagna.rashi}`,
        { role: dom.d1Chart.role, labelledBy: dom.d1Chart.labelledBy, title: dom.d1Chart.title });

  // Gate 3E: the D9 chart equals the engine's d9 block and per-graha D9 fields; nothing recomputed.
  const d9 = chart.d9, d9Lagna = SIGNS.indexOf(d9.lagna_rashi);
  const d9HouseErrors = [];
  dom.d9Chart.houses.forEach((h) => {
    const idx = (d9Lagna + h.house - 1) % 12, block = d9.houses[h.house - 1];
    const expected = BODIES.filter((b) => chart.planets[b].navamsa_whole_sign_house === h.house);
    const fromBlock = [...block.grahas];
    if (h.house === 1) { expected.push("lagna"); fromBlock.push("lagna"); }
    if (h.sign !== SIGNS[idx] || h.sign !== block.rashi || h.signNumber !== String(idx + 1) ||
        JSON.stringify(h.grahas) !== JSON.stringify(expected.sort()) || JSON.stringify(h.grahas) !== JSON.stringify(fromBlock.sort())) {
      d9HouseErrors.push({ house: h.house, dom: h, block, expected });
    }
  });
  check(view, `${label}: D9 chart houses, D9 signs and grahas equal engine JSON`,
        d9.lagna_rashi === chart.lagna.navamsa_rashi && dom.d9Chart.houses.length === 12 && d9HouseErrors.length === 0, d9HouseErrors);
  check(view, `${label}: every D9 chart label inside its house (no clipping)`, dom.d9Chart.outside.length === 0, dom.d9Chart.outside);
  check(view, `${label}: no overlapping D9 chart labels`, dom.d9Chart.overlaps.length === 0, dom.d9Chart.overlaps);
  const descWant = d9.houses.map((h) => `House ${h.house}, ${h.rashi}: ` +
    (h.grahas.length ? h.grahas.map((k) => SABPUJA_NAMES[k]).join(", ") : "empty")).join(". ") + ".";
  check(view, `${label}: D9 SVG is an accessible image with its own title and description`,
        dom.d9Chart.role === "img" && dom.d9Chart.labelsInside && dom.d9Chart.labelledBy.join(" ") === "d9-title d9-desc" &&
        dom.d9Chart.title === `North Indian D9 Navamsa chart, D9 Lagna ${d9.lagna_rashi}` && dom.d9Chart.desc === descWant,
        { title: dom.d9Chart.title, desc: dom.d9Chart.desc, descWant });

  const d1Errors = [], d9Errors = [];
  const lag = dom.d1.lagna || {};
  if (lag.longitude !== chart.lagna.longitude_deg.toFixed(8) + "°" || !lag.rashi.startsWith(chart.lagna.rashi + " ") || lag.house !== "1") { d1Errors.push({ lagna: lag }); }
  BODIES.forEach((b) => {
    const r = dom.d1[b] || {}, p = chart.planets[b];
    if (r.longitude !== p.longitude_deg.toFixed(8) + "°" || !String(r.rashi).startsWith(p.rashi + " ") || r.house !== String(p.whole_sign_house)) { d1Errors.push({ b, r, p }); }
    const n = (dom.d9[b] || {}).navamsa, dh = (dom.d9[b] || {}).d9_house;
    if (!String(n).startsWith(p.navamsa_rashi + " ") || dh !== String(p.navamsa_whole_sign_house) ||
        !chart.d9.houses[p.navamsa_whole_sign_house - 1].grahas.includes(b)) {
      d9Errors.push({ b, n, dh, expected: [p.navamsa_rashi, p.navamsa_whole_sign_house] });
    }
  });
  const dl = dom.d9.lagna || {};
  if (!String(dl.navamsa).startsWith(chart.lagna.navamsa_rashi + " ") || dl.d9_house !== "1") { d9Errors.push({ lagna: dl }); }
  check(view, `${label}: D1 table equals engine JSON (10 rows)`, Object.keys(dom.d1).length === 10 && d1Errors.length === 0, d1Errors);
  check(view, `${label}: D9 table equals engine D9 signs, D9 houses and D9 Lagna (10 rows)`, Object.keys(dom.d9).length === 10 && d9Errors.length === 0, d9Errors);
  const f = dom.facts;
  check(view, `${label}: key facts and method versions equal engine JSON`,
        f.lagna_rashi.startsWith(chart.lagna.rashi) && f.d9_lagna.startsWith(chart.lagna.navamsa_rashi) &&
        f.moon_nakshatra === `${chart.moon_nakshatra.name}, Pada ${chart.moon_nakshatra.pada}` &&
        f.utc === chart.birth.utc && f.schema_version === "0.3.0" && f.metadata_schema === "sabpuja-calculation-metadata/3", f);
  check(view, `${label}: method panel states the claim boundary`, dom.claim.includes("not independently astronomically certified"), dom.claim);
  check(view, `${label}: no horizontal page overflow`, dom.overflow <= 0, dom.overflow);
  if (opts.allowTableScroll) {
    // Very narrow widths: a table may scroll only inside its labelled, keyboard-focusable region.
    check(view, `${label}: any table scrolling stays inside a labelled, focusable region`,
          dom.tableRegions.every(Boolean), { tableOverflow: dom.tableOverflow, regions: dom.tableRegions });
  } else {
    check(view, `${label}: D1 and D9 tables fit without horizontal scrolling`, dom.tableOverflow.every((o) => o <= 0), dom.tableOverflow);
  }
  return dom;
}


/* Approved Sabpuja logo masters (sabpuja/design-system assets/logo/brand-assets.json, release 2026-10-07-rebrand). */
const LOGOS = {
  "/static/brand/sabpuja-logo-horizontal-color.svg": { sha256: "2f9acce59b19cac8e1abed203686cb791b82fa97678005189416ccf7e10f7b14", ratio: 2172 / 724 },
  "/static/brand/sabpuja-emblem-color.svg": { sha256: "c52269c8b475f60c0b1a5d5342bc18380b8dffaf88f960f43e7361db6656a2b8", ratio: 1 }
};

async function logoHashes(base) {
  const out = {};
  for (const p of Object.keys(LOGOS)) {
    const buf = Buffer.from(await (await fetch(base + p)).arrayBuffer());
    out[p] = crypto.createHash("sha256").update(buf).digest("hex");
  }
  return out;
}

/* Logo, links, fonts and colour contrast on the current page. */
async function designChecks(page, view, label) {
  const d = await page.evaluate(async () => {
    await document.fonts.ready;
    const shown = [...document.querySelectorAll(".brand img")].filter((i) => getComputedStyle(i).display !== "none");
    const logos = shown.map((i) => { const r = i.getBoundingClientRect();
      return { src: new URL(i.src).pathname, alt: i.alt, complete: i.complete, natural: i.naturalWidth,
               w: r.width, h: r.height, left: r.left, right: r.right, vw: document.documentElement.clientWidth }; });
    const links = [...document.querySelectorAll("a.site-link")].map((a) => { const r = a.getBoundingClientRect();
      return { id: a.id, href: a.href, target: a.target, rel: a.rel, text: a.textContent.trim(), visible: r.width > 0 && r.height > 0 }; });
    const loaded = [...document.fonts].filter((f) => f.status === "loaded").map((f) => `${f.family.replace(/["']/g, "")} ${f.weight}`);
    const first = (el) => getComputedStyle(el).fontFamily.split(",")[0].replace(/["']/g, "").trim();
    const families = {};
    document.querySelectorAll("body *:not(script):not(style):not(code)").forEach((el) => {
      if (el.closest("svg") && el.tagName.toLowerCase() !== "text") { return; }
      if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) { return; }
      const f = first(el); families[f] = (families[f] || 0) + 1;
    });
    const roles = { h1: first(document.querySelector("h1")), h3: first(document.querySelector("h3")),
                    body: first(document.body), label: first(document.querySelector("label")),
                    input: first(document.querySelector("input")), button: first(document.querySelector("button")),
                    help: first(document.querySelector(".help")) };
    // WCAG contrast of text against the nearest opaque background.
    const rgb = (s) => { const v = (s.match(/[\d.]+/g) || []).map(Number);
                         return s.startsWith("color(srgb") ? v.map((x, i) => (i < 3 ? x * 255 : x)) : v; };
    const lum = ([r, g, b]) => { const c = [r, g, b].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
                                 return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
    const bgOf = (el) => { for (let e = el; e; e = e.parentElement) { const c = rgb(getComputedStyle(e).backgroundColor);
                             if (c.length === 3 || (c.length === 4 && c[3] === 1)) { return c.slice(0, 3); } } return [255, 255, 255]; };
    const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m); return (x + 0.05) / (y + 0.05); };
    const sels = ["body", ".lede", ".help", ".badge", ".product-name", "#header-site-link", "#footer-site-link", ".status-label",
                  ".button--primary", ".button--ghost", ".notice p", "h1", "label", "thead th", "td .en", ".footnote", ".facts dt",
                  ".legend", ".error-card h2", ".error-code", ".field-error", ".site-footer p:last-child"];
    const contrast = [];
    sels.forEach((sel) => document.querySelectorAll(sel).forEach((el, i) => { if (i > 0) { return; }
      const cs = getComputedStyle(el); const r = ratio(rgb(cs.color).slice(0, 3), bgOf(el));
      contrast.push({ sel, ratio: Math.round(r * 100) / 100 }); }));
    // SVG chart text against its house fill.
    document.querySelectorAll("#d1-chart g.house, #d9-chart g.house").forEach((g, i) => { if (i % 12 > 0 && !g.classList.contains("house--lagna")) { return; }
      const fill = rgb(getComputedStyle(g.querySelector("polygon")).fill).slice(0, 3);
      g.querySelectorAll("text").forEach((t) => contrast.push({ sel: `svg ${t.getAttribute("class")} (house ${g.dataset.house})`,
        ratio: Math.round(ratio(rgb(getComputedStyle(t).fill).slice(0, 3), fill) * 100) / 100 })); });
    // Gate 3E: the chart section links.
    document.querySelectorAll(".chart-nav a").forEach((a) => contrast.push({ sel: `.chart-nav a#${a.id}`,
      ratio: Math.round(ratio(rgb(getComputedStyle(a).color).slice(0, 3), bgOf(a)) * 100) / 100 }));
    return { logos, links, loaded, families, roles, contrast };
  });
  const lg = d.logos;
  check(view, `${label}: exactly one approved logo shown, loaded, with alt text`, lg.length === 1 && LOGOS[lg[0].src] &&
        lg[0].complete && lg[0].natural > 0 && lg[0].alt === "Sabpuja", lg);
  check(view, `${label}: logo keeps its original proportions and fits the viewport`, lg.length === 1 &&
        Math.abs(lg[0].w / lg[0].h - LOGOS[lg[0].src].ratio) < 0.01 && lg[0].left >= 0 && lg[0].right <= lg[0].vw && lg[0].h >= 40, lg);
  check(view, `${label}: header and footer link to https://sabpuja.com (new tab, noopener noreferrer)`,
        d.links.length === 2 && d.links.every((l) => l.href === "https://sabpuja.com/" && l.target === "_blank" &&
        /\bnoopener\b/.test(l.rel) && /\bnoreferrer\b/.test(l.rel) && l.visible && l.text.includes("sabpuja.com")), d.links);
  const r = d.roles;
  check(view, `${label}: Poppins for headings; Inter for body, labels, fields, buttons and help`,
        r.h1 === "Poppins" && r.h3 === "Poppins" && ["body", "label", "input", "button", "help"].every((k) => r[k] === "Inter"), r);
  const want = ["Inter 400", "Inter 500", "Inter 600", "Poppins 600"];
  check(view, `${label}: local Poppins and Inter faces loaded`, want.every((w) => d.loaded.includes(w)), d.loaded);
  check(view, `${label}: no text uses a font other than Poppins or Inter`,
        Object.keys(d.families).every((f) => f === "Poppins" || f === "Inter"), d.families);
  const low = d.contrast.filter((c) => c.ratio < 4.5);
  check(view, `${label}: text contrast at least 4.5:1 (WCAG AA) for ${d.contrast.length} sampled styles`, d.contrast.length >= 15 && low.length === 0, low.length ? low : d.contrast);
  return d;
}

/* Fluid layout at QA sample widths (not CSS breakpoints). 640 px also stands for a 1280 px window at 200% zoom. */
const FLUID_WIDTHS = [280, 320, 360, 414, 480, 600, 640, 768, 900, 1024, 1180, 1280, 1440, 1920];

async function fluidChecks(browser, base) {
  const fluidOut = path.join(OUT, "fluid");
  fs.mkdirSync(fluidOut, { recursive: true });
  const metrics = [];
  for (const width of FLUID_WIDTHS) {
    const view = `w${width}`;
    const context = await browser.newContext({ viewport: { width, height: 900 } });
    const page = await context.newPage();
    const external = [];
    page.on("request", (rq) => { if (!rq.url().startsWith(base)) { external.push(rq.url()); } });
    await page.goto(base + "/");
    await page.waitForSelector("#place optgroup", { state: "attached" });
    let res = await fillAndSubmit(page, "in-new-delhi", "1990-05-15", "10:30:00");
    await page.waitForSelector("#result:not([hidden])");
    const dom = await verifyRender(page, view, "New Delhi chart", res.body.chart, { allowTableScroll: width < 360 });
    const d = await designChecks(page, view, "design");
    const m = await page.evaluate(() => {
      const px = (sel, prop) => parseFloat(getComputedStyle(document.querySelector(sel))[prop]);
      return { h1: px("h1", "fontSize"), body: px("body", "fontSize"), gutter: px("main", "paddingLeft"),
               logo: Math.max(...[...document.querySelectorAll(".brand img")].map((i) => i.getBoundingClientRect().width)),
               chart: document.getElementById("d1-chart").getBoundingClientRect().width,
               d9chart: document.getElementById("d9-chart").getBoundingClientRect().width,
               columns: getComputedStyle(document.querySelector(".bento")).gridTemplateColumns.split(" ").length };
    });
    m.width = width; m.tableOverflow = dom.tableOverflow; m.logoShown = d.logos.map((l) => path.basename(l.src));
    metrics.push(m);
    await page.screenshot({ path: path.join(fluidOut, `${view}-result.png`), fullPage: true });
    await page.locator(".chart-card--d9").screenshot({ path: path.join(fluidOut, `${view}-d9-chart.png`) });
    check(view, "D9 chart is drawn at least as large as the D1 chart", m.d9chart >= m.chart - 0.5, { d1: m.chart, d9: m.d9chart });
    res = await fillAndSubmit(page, "in-new-delhi", "2070-10-04", "06:00:00");
    await page.waitForSelector("#result:not([hidden])");
    await verifyRender(page, view, "crowded Lagna house", res.body.chart, { allowTableScroll: width < 360 });
    await page.locator(".chart-card").screenshot({ path: path.join(fluidOut, `${view}-crowded-chart.png`) });
    res = await fillAndSubmit(page, "in-new-delhi", "2025-04-09", "04:56:00");
    await page.waitForSelector("#result:not([hidden])");
    await verifyRender(page, view, "crowded D9 Lagna house", res.body.chart, { allowTableScroll: width < 360 });
    await page.locator(".chart-card--d9").screenshot({ path: path.join(fluidOut, `${view}-crowded-d9-chart.png`) });
    check(view, "no request leaves 127.0.0.1", external.length === 0, external);
    await context.close();
  }
  // Type, gutters and logo scale continuously: never shrink as the window widens.
  const mono = (k) => metrics.every((m, i) => i === 0 || m[k] >= metrics[i - 1][k] - 0.01 || metrics[i - 1].logoShown[0] !== m.logoShown[0]);
  check("fluid", "heading size, body size, gutter and logo width never decrease as width grows",
        ["h1", "body", "gutter", "logo"].every(mono), metrics);
  check("fluid", "compact emblem only where the header is too narrow for the horizontal logo",
        metrics.every((m) => (m.width < 288) === (m.logoShown[0] === "sabpuja-emblem-color.svg")), metrics.map((m) => [m.width, m.logoShown]));
  fs.writeFileSync(path.join(OUT, "fluid-metrics.json"), JSON.stringify(metrics, null, 1));
}

/* G3B-UI-01/02: late or reordered responses never replace the current form.
 * Responses for birth_time A are held at a gate the test opens, so the order
 * is fixed, not timed. form.dataset.ignoredResponses counts dropped replies. */
async function raceChecks(page, view) {
  const A = "10:30:00", B = "18:20:10";
  let gate = null;
  const gated = [];
  await page.route("**/api/chart", async (route) => {
    const body = route.request().postDataJSON();
    if (body.birth_time !== A || !gate) { return route.continue(); }
    const response = await route.fetch();
    gated.push(body);
    await gate.promise;
    try { await route.fulfill({ response }); } catch (e) { /* request was aborted by the page */ }
  });
  const newGate = () => { let open; const promise = new Promise((r) => { open = r; }); gate = { promise, open }; };
  const ignoredCount = () => page.evaluate(() => Number(document.getElementById("birth-form").dataset.ignoredResponses || 0));
  const state = () => page.evaluate(() => ({
    result: !document.getElementById("result").hidden, error: !document.getElementById("error-card").hidden,
    status: document.getElementById("status").textContent, submitDisabled: document.getElementById("submit").disabled,
    localTime: (document.querySelector("dd[data-field=local_time]") || {}).textContent,
    place: document.getElementById("place").value, time: document.getElementById("birth-time").value }));
  async function startA(placeId) {
    await page.selectOption("#place", placeId);
    await page.fill("#birth-date", "1990-05-15");
    await page.fill("#birth-time", A);
    const before = gated.length;
    await page.click("#submit");
    for (let i = 0; i < 100 && gated.length === before; i++) { await page.waitForTimeout(20); }
    return gated.length > before;
  }
  // Settles when the page drops the late reply, or when it wrongly shows it.
  async function releaseAndSettle(before, shownBefore) {
    gate.open();
    await page.waitForFunction(([n, shown]) => {
      const dropped = Number(document.getElementById("birth-form").dataset.ignoredResponses || 0) > n;
      const visible = !document.getElementById("result").hidden || !document.getElementById("error-card").hidden;
      const time = (document.querySelector("dd[data-field=local_time]") || {}).textContent;
      return dropped || (shown ? time !== shown : visible);
    }, [before, shownBefore || null], { timeout: 10000 });
    gate = null;
  }

  // 1. Submit A, Clear, then A's 200 arrives: nothing is shown.
  await page.goto(page.url().split("#")[0]);
  await page.waitForSelector("#place optgroup", { state: "attached" });
  newGate();
  let held = await startA("in-new-delhi");
  let before = await ignoredCount();
  await page.click("#clear");
  await releaseAndSettle(before);
  let st = await state();
  check(view, "late 200 after Clear is ignored (no chart, no status, form empty)",
        held && !st.result && !st.error && st.status === "" && st.place === "" && !st.submitDisabled, st);

  // 2. Submit A, edit the time, submit B; B completes, then A: B stays.
  newGate();
  held = await startA("in-new-delhi");
  before = await ignoredCount();
  await page.fill("#birth-time", B);
  const [respB] = await Promise.all([page.waitForResponse((r) => r.url().endsWith("/api/chart")), page.click("#submit")]);
  const bodyB = await respB.json();
  await page.waitForSelector("#result:not([hidden])");
  await releaseAndSettle(before, B);
  st = await state();
  check(view, "late A after B is ignored; B's chart stays shown", held && st.result && st.localTime === B && st.time === B, st);
  await verifyRender(page, view, "after reordered A/B responses", bodyB.chart);

  // 3. Submit A, edit the date (no resubmit), then A arrives: nothing is shown.
  newGate();
  held = await startA("in-mumbai");
  before = await ignoredCount();
  await page.fill("#birth-date", "1991-06-16");
  await releaseAndSettle(before);
  st = await state();
  check(view, "late 200 after a field edit is ignored", held && !st.result && !st.error && st.status === "" && !st.submitDisabled, st);

  // 4. Submit A for a refused place, Clear, then the late 422 arrives: no error shown.
  newGate();
  held = await startA("no-tromso");
  before = await ignoredCount();
  await page.click("#clear");
  await releaseAndSettle(before);
  st = await state();
  check(view, "late refusal after Clear is ignored (no error card)", held && !st.error && !st.result, st);

  // 5. G3B-UI-02: a shown result is hidden as soon as a field is edited ...
  let res = await fillAndSubmit(page, "in-jaipur", "2024-08-15", "06:05:00");
  await page.waitForSelector("#result:not([hidden])");
  await page.fill("#birth-date", "2024-08-16");
  st = await state();
  check(view, "editing a field hides the previous result", res.status === 200 && !st.result, st);
  // ... and an invalid submit after a result leaves no result shown.
  res = await fillAndSubmit(page, "in-jaipur", "2024-08-15", "06:05:00");
  await page.waitForSelector("#result:not([hidden])");
  await page.evaluate(() => { const t = document.getElementById("birth-time"); t.value = ""; });
  await page.click("#submit");
  st = await state();
  const invalidTime = await page.getAttribute("#birth-time", "aria-invalid");
  check(view, "invalid submit after a result hides the result and marks the field", !st.result && invalidTime === "true", { st, invalidTime });
  // Unknown-time toggle after a result also hides it.
  res = await fillAndSubmit(page, "in-jaipur", "2024-08-15", "06:05:00");
  await page.waitForSelector("#result:not([hidden])");
  await page.check("#time-unknown");
  st = await state();
  check(view, "checking 'unknown time' hides the previous result", !st.result && st.submitDisabled, st);
  await page.uncheck("#time-unknown");
  await page.unroute("**/api/chart");
}

async function runView(browser, base, view, contextOpts) {
  const context = await browser.newContext(contextOpts);
  const page = await context.newPage();
  const external = [], consoleErrors = [];
  page.on("request", (r) => { if (!r.url().startsWith(base)) { external.push(r.url()); } });
  // Chromium logs every 4xx response as a console error; the expected 409/422
  // refusals are checked separately, so only other errors count here.
  page.on("console", (m) => {
    if (m.type() === "error" && !/^Failed to load resource: the server responded with a status of (409|422) /.test(m.text())) { consoleErrors.push(m.text()); }
  });
  page.on("pageerror", (e) => consoleErrors.push(String(e)));
  const shot = (name, el) => (el ? page.locator(el).screenshot({ path: path.join(OUT, `${view}-${name}.png`) })
                                 : page.screenshot({ path: path.join(OUT, `${view}-${name}.png`), fullPage: true }));

  await page.goto(base + "/");
  await page.waitForSelector("#place optgroup", { state: "attached" });
  const optionCount = await page.locator("#place option").count();
  check(view, "page loads with 12 places plus placeholder", optionCount === 13, optionCount);
  const labelled = await page.evaluate(() => [...document.querySelectorAll("input, select")].every((el) => el.labels && el.labels.length > 0));
  check(view, "every form control has a label", labelled, null);
  await shot("01-form");
  await shot("00-header", ".site-header");

  // Client-side validation of an empty form.
  await page.click("#submit");
  const invalid = await page.evaluate(() => [...document.querySelectorAll("[aria-invalid=true]")].map((e) => e.id));
  check(view, "empty form shows field errors and sends nothing", JSON.stringify(invalid) === JSON.stringify(["place", "birth-date", "birth-time"]), invalid);
  await shot("02-validation");

  // Valid synthetic chart.
  let res = await fillAndSubmit(page, "in-new-delhi", "1990-05-15", "10:30:00");
  await page.waitForSelector("#result:not([hidden])");
  check(view, "valid request returns a chart (HTTP 200)", res.status === 200, res.status);
  await verifyRender(page, view, "New Delhi 1990-05-15 10:30:00", res.body.chart);
  await designChecks(page, view, "result page");
  await shot("03-result");
  await shot("04-d1-chart", ".chart-card");
  await shot("05-d9-table", "#d9-heading >> xpath=..");
  await shot("13-d9-chart", ".chart-card--d9");

  // Gate 3E: keyboard chart navigation. From "Edit birth details", Tab reaches the D1 and D9
  // section links; Enter on the D9 link moves focus (with a visible ring) to the D9 chart card,
  // and the next Tab reaches the D9 table region.
  await page.focus("#edit");
  const navOrder = [];
  for (let i = 0; i < 2; i++) { await page.keyboard.press("Tab"); navOrder.push(await page.evaluate(() => document.activeElement.id)); }
  await page.keyboard.press("Enter");
  const navTarget = await page.evaluate(() => { const el = document.activeElement, cs = getComputedStyle(el);
    return { id: el.id, ring: cs.outlineStyle !== "none" && cs.outlineWidth !== "0px", top: el.getBoundingClientRect().top, vh: window.innerHeight }; });
  await page.keyboard.press("Tab");
  const afterNav = await page.evaluate(() => ({ role: document.activeElement.getAttribute("role"), labelledBy: document.activeElement.getAttribute("aria-labelledby") }));
  check(view, "keyboard: Tab reaches the D1 and D9 chart links; Enter moves focus to the D9 chart; Tab then reaches the D9 table",
        JSON.stringify(navOrder) === JSON.stringify(["nav-d1", "nav-d9"]) && navTarget.id === "d9-section" && navTarget.ring &&
        navTarget.top >= -1 && navTarget.top < navTarget.vh && afterNav.role === "region" && afterNav.labelledBy === "d9-heading",
        { navOrder, navTarget, afterNav });
  await page.focus("#nav-d1");
  await page.keyboard.press("Enter");
  const d1Target = await page.evaluate(() => document.activeElement.id);
  check(view, "keyboard: Enter on the D1 link moves focus to the D1 chart", d1Target === "d1-section", d1Target);

  // Edit and recalculate.
  await page.click("#edit");
  const focused = await page.evaluate(() => document.activeElement.id);
  check(view, "edit moves focus to the birthplace field", focused === "place", focused);
  res = await fillAndSubmit(page, "in-chennai", "2000-02-29", "05:45:30");
  await page.waitForSelector("#result:not([hidden])");
  await verifyRender(page, view, "recalculated Chennai 2000-02-29 05:45:30", res.body.chart);

  // Crowded houses: seven grahas share one house, in eleven different houses.
  for (const hour of ["00", "02", "04", "06", "08", "10", "12", "16", "18", "20", "22"]) {
    res = await fillAndSubmit(page, "in-new-delhi", "2070-10-04", `${hour}:00:00`);
    await page.waitForSelector("#result:not([hidden])");
    await verifyRender(page, view, `crowded 2070-10-04 ${hour}:00`, res.body.chart);
    if (hour === "06") { await shot("06-crowded-lagna-house", ".chart-card"); }
    if (hour === "04") { await shot("07-crowded-triangle-house", ".chart-card"); }
  }

  // Gate 3E crowded D9 houses: seven grahas in D9 house 1 (with Asc) through house 12 in turn.
  const d9Crowded = [["04:56", 1], ["04:48", 2], ["04:40", 3], ["04:28", 4], ["04:20", 5], ["04:08", 6],
                     ["04:00", 7], ["03:48", 8], ["03:40", 9], ["03:28", 10], ["05:16", 11], ["05:08", 12]];
  const d9Seen = [];
  for (const [time, house] of d9Crowded) {
    res = await fillAndSubmit(page, "in-new-delhi", "2025-04-09", `${time}:00`);
    await page.waitForSelector("#result:not([hidden])");
    await verifyRender(page, view, `crowded D9 2025-04-09 ${time}`, res.body.chart);
    const counts = res.body.chart.d9.houses.map((h) => h.grahas.length);
    d9Seen.push([house, counts[house - 1]]);
    if (house === 1) { await shot("14-d9-crowded-lagna-house", ".chart-card--d9"); }
    if (house === 12) { await shot("15-d9-crowded-triangle-house", ".chart-card--d9"); }
  }
  check(view, "crowded D9 cases put seven grahas in every D9 house 1..12 in turn",
        d9Seen.every(([, n]) => n === 7), d9Seen);

  // Refusals from the engine, shown clearly, with no chart.
  const refusals = [
    ["no-tromso", "1990-05-15", "10:30:00", "LATITUDE_OUTSIDE_SUPPORTED_BAND", "08-error-latitude"],
    ["in-mumbai", "1965-05-15", "10:30:00", "HISTORICAL_CLOCK_UNVERIFIED", "09-error-pre-1970"],
    ["gb-london", "2020-03-29", "01:30:00", "TIME_NONEXISTENT_LOCAL", null],
    ["in-mumbai", "2101-01-01", "00:00:00", "DATE_OUTSIDE_SUPPORTED_RANGE", null]
  ];
  for (const [pid, d, t, code, name] of refusals) {
    res = await fillAndSubmit(page, pid, d, t);
    await page.waitForSelector("#error-card:not([hidden])");
    const shown = await page.evaluate(() => ({ code: document.getElementById("error-code").textContent,
      resultHidden: document.getElementById("result").hidden, focus: document.activeElement.id,
      text: document.getElementById("error-message").textContent }));
    check(view, `${code} shown with no chart and focus on the message`,
          res.status === 422 && shown.code === code && shown.resultHidden && shown.focus === "error-card" && shown.text.length > 20, shown);
    if (name) { await shot(name); }
    if (code === "LATITUDE_OUTSIDE_SUPPORTED_BAND") { await designChecks(page, view, "error state"); }
  }

  // Repeated hour: the user must choose; nothing is guessed.
  res = await fillAndSubmit(page, "gb-london", "2020-10-25", "01:30:00");
  await page.waitForSelector("#ambiguity:not([hidden])");
  const choiceCount = await page.locator("input[name=occurrence]").count();
  check(view, "repeated local time asks for the occurrence (HTTP 409, 2 choices, no chart)",
        res.status === 409 && choiceCount === 2 && await page.locator("#result").isHidden(), { status: res.status, choiceCount });
  await shot("10-ambiguous-time");
  await page.check("input[name=occurrence][value='+00:00']");
  const [resp2] = await Promise.all([page.waitForResponse((r) => r.url().endsWith("/api/chart")), page.click("#submit")]);
  const chosen = await resp2.json();
  await page.waitForSelector("#result:not([hidden])");
  const utcOffset = await page.textContent("dd[data-field=utc_offset]");
  check(view, "chosen occurrence is used and labelled", resp2.status() === 200 && chosen.chart.birth.utc === "2020-10-25T01:30:00Z" &&
        utcOffset.startsWith("+00:00") && utcOffset.includes("your choice"), { utcOffset, utc: chosen.chart && chosen.chart.birth.utc });
  await verifyRender(page, view, "London repeated hour, second occurrence", chosen.chart);

  // Unknown birth time: explanation, no calculation.
  await page.click("#clear");
  await page.check("#time-unknown");
  const unknownState = await page.evaluate(() => ({ panel: !document.getElementById("unknown-time-panel").hidden,
    submitDisabled: document.getElementById("submit").disabled, timeDisabled: document.getElementById("birth-time").disabled }));
  check(view, "unknown time shows the explanation and disables calculation", unknownState.panel && unknownState.submitDisabled && unknownState.timeDisabled, unknownState);
  await shot("11-unknown-time");
  await page.uncheck("#time-unknown");

  // Keyboard: Tab reaches every control in order, with a visible focus ring.
  await page.goto(base + "/");
  await page.waitForSelector("#place optgroup", { state: "attached" });
  // Native date and time inputs take one Tab per segment, so keep the first
  // focus of each control and record whether it shows the focus ring.
  const order = [];
  for (let i = 0; i < 20 && !order.some((o) => o.id === "clear"); i++) {
    await page.keyboard.press("Tab");
    const now = await page.evaluate(() => {
      const el = document.activeElement, cs = getComputedStyle(el);
      return { id: el.id || el.className, ring: cs.outlineStyle !== "none" && cs.outlineWidth !== "0px" };
    });
    if (!order.length || order[order.length - 1].id !== now.id) { order.push(now); }
  }
  const ids = order.map((o) => o.id);
  const wanted = ["skip-link", "header-site-link", "place", "birth-date", "birth-time", "time-unknown", "submit", "clear"];
  check(view, "keyboard Tab order reaches all controls in order", JSON.stringify(ids) === JSON.stringify(wanted), ids);
  check(view, "focused controls show a focus ring", order.every((o) => o.ring), order);
  // Keyboard-only submission.
  await page.focus("#place");
  await page.keyboard.press("ArrowDown");
  await page.fill("#birth-date", "1975-06-25");
  await page.fill("#birth-time", "18:20:10");
  await page.focus("#submit");
  const [kresp] = await Promise.all([page.waitForResponse((r) => r.url().endsWith("/api/chart")), page.keyboard.press("Enter")]);
  check(view, "keyboard-only submission calculates", kresp.status() === 200, kresp.status());
  await page.waitForSelector("#result:not([hidden])");
  await verifyRender(page, view, "keyboard submission", (await kresp.json()).chart);

  await raceChecks(page, view);

  check(view, "no request leaves 127.0.0.1", external.length === 0, external);
  check(view, "no console errors", consoleErrors.length === 0, consoleErrors);
  await context.close();
}

(async () => {
  const port = await freePort();
  const server = await startServer(port);
  const base = `http://127.0.0.1:${port}`;
  const browser = await chromium.launch();
  try {
    await runView(browser, base, "desktop", { viewport: { width: 1366, height: 900 } });
    await runView(browser, base, "mobile", { viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
    await fluidChecks(browser, base);
    await serverFaultChecks(browser);
    cliChecks();
    const hashes = await logoHashes(base);
    check("assets", "served logo files are byte-identical to the approved masters (SHA-256)",
          Object.entries(LOGOS).every(([p, l]) => hashes[p] === l.sha256), hashes);
  } catch (e) {
    check("run", "browser run completed", false, String(e && e.stack || e));
  } finally {
    await browser.close();
    server.proc.kill("SIGTERM");
  }
  await new Promise((r) => setTimeout(r, 500));
  const leaked = ["1990-05-15", "10:30:00", "2070-10-04", "1965-05-15", "Traceback"].filter((m) => server.output().includes(m));
  check("server", "server printed nothing about requests (banner only)", leaked.length === 0 && server.output().trim().split("\n").length === 1, { leaked, output: server.output() });
  const failed = results.filter((r) => !r.ok);
  fs.writeFileSync(path.join(OUT, "browser-results.json"), JSON.stringify({ base, results }, null, 1));
  console.log(`\nBROWSER QA: ${results.length - failed.length} passed, ${failed.length} failed, 0 skipped`);
  process.exit(failed.length ? 1 : 0);
})();
