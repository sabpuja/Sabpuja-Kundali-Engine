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
const { spawn } = require("child_process");
const fs = require("fs");
const net = require("net");
const path = require("path");

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

async function startServer(port) {
  const env = { PATH: process.env.PATH, SABPUJA_EPHE_PATH: EPHE, PYTHONDONTWRITEBYTECODE: "1",
                PYTHONPATH: `${path.join(ROOT, "src")}:${path.join(ROOT, "prototype")}` };
  const proc = spawn(PYTHON, ["-m", "kundali_prototype", "--port", String(port)], { env, cwd: ROOT });
  let output = "";
  proc.stdout.on("data", (d) => { output += d; });
  proc.stderr.on("data", (d) => { output += d; });
  for (let i = 0; i < 300 && !output.includes("http://127.0.0.1:"); i++) { await new Promise((r) => setTimeout(r, 100)); }
  if (!output.includes("http://127.0.0.1:")) { throw new Error("server did not start: " + output); }
  return { proc, output: () => output };
}

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
  return { status: resp.status(), body: await resp.json() };
}

/* Compare the rendered chart and tables with the engine JSON the page received. */
async function verifyRender(page, view, label, chart) {
  const dom = await page.evaluate(() => {
    const houses = [...document.querySelectorAll("#d1-chart g.house")].map((g) => ({
      house: Number(g.dataset.house), sign: g.dataset.sign,
      signNumber: g.querySelector("[data-role=sign-number]").textContent,
      grahas: [...g.querySelectorAll("text[data-graha]")].map((t) => t.dataset.graha).sort()
    }));
    function inside(pt, poly) {
      let c = false;
      for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
        const [xi, yi] = poly[i], [xj, yj] = poly[j];
        if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi) { c = !c; }
      }
      return c;
    }
    const outside = [];
    const boxes = [];
    document.querySelectorAll("#d1-chart g.house").forEach((g) => {
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
    const rows = (sel, f) => Object.fromEntries([...document.querySelectorAll(sel + " tbody tr")].map((tr) =>
      [tr.dataset.graha, Object.fromEntries([...tr.querySelectorAll("[data-field]")].map((c) => [c.dataset.field, c.textContent]))]));
    const facts = Object.fromEntries([...document.querySelectorAll("dd[data-field]")].map((d) => [d.dataset.field, d.textContent]));
    return { houses, outside, overlaps, d1: rows("#d1-table"), d9: rows("#d9-table"), facts,
             overflow: document.documentElement.scrollWidth - window.innerWidth,
             tableOverflow: [...document.querySelectorAll(".table-scroll")].map((t) => t.scrollWidth - t.clientWidth),
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

  const d1Errors = [], d9Errors = [];
  const lag = dom.d1.lagna || {};
  if (lag.longitude !== chart.lagna.longitude_deg.toFixed(8) + "°" || !lag.rashi.startsWith(chart.lagna.rashi + " ") || lag.house !== "1") { d1Errors.push({ lagna: lag }); }
  BODIES.forEach((b) => {
    const r = dom.d1[b] || {}, p = chart.planets[b];
    if (r.longitude !== p.longitude_deg.toFixed(8) + "°" || !String(r.rashi).startsWith(p.rashi + " ") || r.house !== String(p.whole_sign_house)) { d1Errors.push({ b, r, p }); }
    const n = (dom.d9[b] || {}).navamsa;
    if (!String(n).startsWith(p.navamsa_rashi + " ")) { d9Errors.push({ b, n, expected: p.navamsa_rashi }); }
  });
  if (!String((dom.d9.lagna || {}).navamsa).startsWith(chart.lagna.navamsa_rashi + " ")) { d9Errors.push({ lagna: dom.d9.lagna }); }
  check(view, `${label}: D1 table equals engine JSON (10 rows)`, Object.keys(dom.d1).length === 10 && d1Errors.length === 0, d1Errors);
  check(view, `${label}: D9 table equals engine D9 signs and D9 Lagna (10 rows)`, Object.keys(dom.d9).length === 10 && d9Errors.length === 0, d9Errors);
  const f = dom.facts;
  check(view, `${label}: key facts and method versions equal engine JSON`,
        f.lagna_rashi.startsWith(chart.lagna.rashi) && f.d9_lagna.startsWith(chart.lagna.navamsa_rashi) &&
        f.moon_nakshatra === `${chart.moon_nakshatra.name}, Pada ${chart.moon_nakshatra.pada}` &&
        f.utc === chart.birth.utc && f.schema_version === "0.2.0" && f.metadata_schema === "sabpuja-calculation-metadata/3", f);
  check(view, `${label}: method panel states the claim boundary`, dom.claim.includes("not independently astronomically certified"), dom.claim);
  check(view, `${label}: no horizontal page overflow`, dom.overflow <= 0, dom.overflow);
  check(view, `${label}: D1 and D9 tables fit without horizontal scrolling`, dom.tableOverflow.every((o) => o <= 0), dom.tableOverflow);
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
  await shot("03-result");
  await shot("04-d1-chart", ".chart-card");
  await shot("05-d9-table", "#d9-heading >> xpath=..");

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
  const wanted = ["skip-link", "place", "birth-date", "birth-time", "time-unknown", "submit", "clear"];
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
