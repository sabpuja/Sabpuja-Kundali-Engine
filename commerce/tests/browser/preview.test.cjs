// Free preview -> paid hand-off -> claim -> PDF, plus the optional opt-in, in a real browser
// (KUN-FREEMIUM-PREVIEW-001). Synthetic data only. Same journey_server.py as journey.test.cjs (real App, transport,
// engine and Essentials renderer; mock mail; fake Shopify), on its own ports. SHOTS=<dir> saves screenshots.
"use strict";
const { test, before, after } = require("node:test");
const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { chromium, devices } = require("playwright");

const ROOT = path.resolve(__dirname, "../../..");
const PORT = 18781, CONTROL = 18782;
const BASE = `http://127.0.0.1:${PORT}`;
const SHOP = "sabpuja-synthetic-test.myshopify.com";
const BUY = `https://${SHOP}/cart/910001:1`;
const SHOTS = process.env.SHOTS || "";
const AXE = require.resolve("axe-core/axe.min.js");
const BIRTH = { place: "in-jaipur", date: "1990-05-17", time: "14:30:00" };
const LEAD = "synthetic.lead@example.invalid";
const BUYER = "synthetic.preview.buyer@example.invalid";

let proc, browser, peerOrder = 8100;

async function control(p, body) {
  const r = await fetch(`http://127.0.0.1:${CONTROL}${p}`, body === undefined ? {} :
    { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } });
  return r.json();
}
const funnel = () => control("/funnel");
async function freshWindow() { await control("/clock", { seconds: 3601 }); } // new rate-limit windows
async function shot(page, name) {
  if (SHOTS) await page.screenshot({ path: path.join(SHOTS, "preview-" + name + ".png"), fullPage: true });
}

before(async () => {
  proc = spawn(process.env.PYTHON || "python3",
    [path.join(__dirname, "journey_server.py"), "--port", String(PORT), "--control-port", String(CONTROL)],
    { cwd: ROOT, env: Object.assign({}, process.env, { PYTHONPATH: "src:prototype:.:commerce:commerce/tests" }),
      stdio: ["ignore", "pipe", "pipe"] });
  proc.stderr.on("data", (d) => { if (process.env.DEBUG) process.stderr.write(d); });
  await new Promise((resolve, reject) => {
    proc.stdout.once("data", resolve);
    proc.once("exit", (c) => reject(new Error("journey server exited " + c)));
  });
  browser = await chromium.launch();
  if (SHOTS) fs.mkdirSync(SHOTS, { recursive: true });
});
after(async () => { if (browser) await browser.close(); if (proc) proc.kill(); });

async function open(opts) {
  const o = opts || {};
  await freshWindow();
  const ctx = await browser.newContext(Object.assign({ locale: "en-IN", acceptDownloads: true }, o.device || {},
    o.locale ? { locale: o.locale } : {}, o.bypassCSP ? { bypassCSP: true } : {}));
  // The synthetic shop does not exist: record the hand-off and answer locally instead of leaving the machine.
  const handoffs = [];
  await ctx.route(`https://${SHOP}/**`, (route) => {
    handoffs.push(route.request().url());
    route.fulfill({ status: 200, contentType: "text/html", body: "<!doctype html><title>Synthetic checkout</title><h1>Checkout</h1>" });
  });
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  page.on("console", (m) => { if (m.type() === "error" && !/status of 4\d\d/.test(m.text())) errors.push(m.text()); });
  const requests = [];
  page.on("request", (r) => requests.push({ url: r.url(), method: r.method(), body: r.postData() }));
  await page.goto(BASE + (o.path || "/kundali"));
  await page.locator("#place_id option[value='in-jaipur']").waitFor({ state: "attached" });
  return { ctx, page, errors, requests, handoffs };
}
async function fill(page, b, name) {
  const v = Object.assign({}, BIRTH, b || {});
  if (name) await page.fill("#display_name", name);
  if (v.place) await page.selectOption("#place_id", v.place);
  if (v.date) await page.fill("#birth_date", v.date);
  if (v.time) await page.fill("#birth_time", v.time);
}
async function showPreview(page) {
  const [resp] = await Promise.all([page.waitForResponse((r) => r.url().endsWith("/api/preview")),
    page.click("#preview-submit")]);
  return resp;
}

// ---------------------------------------------------------------------------------------------------------------

test("limits are disclosed before input and match the served places", async () => {
  const { ctx, page, errors } = await open();
  const order = await page.evaluate(() => {
    const pos = (id) => [...document.querySelectorAll("*")].indexOf(document.getElementById(id));
    return { elig: pos("h-elig"), form: pos("preview-form") };
  });
  assert.ok(order.elig < order.form, "eligibility comes before the form");
  const text = await page.locator("#elig-list").innerText();
  for (const city of ["New Delhi", "Mumbai", "Kolkata", "Chennai", "Bengaluru", "Hyderabad", "Jaipur", "Lucknow",
    "Varanasi", "Guwahati"]) assert.ok(text.includes(city), city);
  assert.match(text, /1 January 1970/);
  assert.match(text, /never guess a time/);
  assert.equal(await page.locator("#place_id option").count(), 11);           // prompt + 10 cities, no London/Tromsø
  assert.equal(await page.getAttribute("#birth_date", "min"), "1970-01-01");
  assert.ok(await page.locator("#step-result").isHidden());
  assert.ok(await page.locator("#step-leads").isHidden(), "no sign-up before a preview");
  await shot(page, "desktop-01-start");
  assert.deepEqual(errors, []);
  await ctx.close();
});

test("complete preview -> buy -> Shopify hand-off -> claim -> re-entered details -> 14-page PDF", async () => {
  const before = await funnel();
  const { ctx, page, errors, requests, handoffs } = await open();
  await fill(page, BIRTH, "Synthetic Asha");
  const resp = await showPreview(page);
  const json = await resp.json();
  assert.equal(resp.status(), 200);
  assert.deepEqual(Object.keys(json.fields).sort(), ["lagna_rashi", "moon_rashi"]);
  // Only birthplace, date and time leave the page; the name stays in the browser.
  const sent = requests.filter((r) => r.url.endsWith("/api/preview"));
  assert.equal(sent.length, 1);
  assert.deepEqual(JSON.parse(sent[0].body), { place_id: "in-jaipur", birth_date: "1990-05-17", birth_time: "14:30:00" });
  for (const r of requests) assert.ok(!(r.body || "").includes("Synthetic Asha") && !r.url.includes("Asha"));
  await page.locator("#step-result").waitFor();
  assert.equal(await page.locator("#h-result").innerText(), "Synthetic Asha, here is your free Kundali preview");
  assert.equal(await page.locator("#result-for").innerText(),
    "For someone born 17 May 1990 at 14:30:00 (2:30:00 pm) in Jaipur, Rajasthan.");
  assert.equal(await page.locator("#fact-lagna_rashi .fact__value").innerText(), "Kanya");
  assert.equal(await page.locator("#fact-lagna_rashi .fact__meta").innerText(), "Sidereal Rashi 6 of 12");
  assert.equal(await page.locator("#fact-moon_rashi .fact__value").innerText(), "Makara");
  assert.ok(await page.locator("#check-changed").isHidden());
  assert.ok(await page.locator("#qa-banner").isVisible(), "QA store banner");
  assert.ok(await page.locator(".compare").isHidden(), "full contents collapsed");
  await page.click("#contents summary");
  assert.match(await page.locator(".compare").innerText(), /D9 Navamsa chart\s+No\s+Yes/);
  assert.doesNotMatch(await page.locator("#step-offer").innerText(), /Vara|[Ss]unrise|Virgo/);
  assert.equal(await page.locator("#price-text").innerText(), "to be confirmed");
  assert.ok(await page.locator("#lead_consent").isVisible());
  assert.equal(await page.locator("#lead_consent").isChecked(), false, "marketing consent is unchecked");
  await shot(page, "desktop-02-preview-and-offer");

  await page.click("#buy");
  await page.locator("#handoff").waitFor();
  assert.match(await page.locator("#handoff").innerText(), /After payment you will enter your birth details again/);
  assert.equal(await page.getAttribute("#checkout", "href"), BUY);
  await shot(page, "desktop-03-handoff");
  await Promise.all([page.waitForURL(BUY), page.click("#checkout")]);
  assert.deepEqual(handoffs, [BUY], "hand-off carries no birth detail, name or identifier");
  const after = await funnel();
  for (const [k, d] of [["preview_initiated", 1], ["preview_generated", 1], ["full_report_selected", 1],
    ["checkout_link_clicked", 1]]) assert.equal(after[k] - before[k], d, k);

  // Shopify's orders/paid webhook (synthetic), then the existing claim flow with the details typed again.
  peerOrder += 1;
  await control("/clock", { seconds: 61 });
  assert.equal((await control("/paid", { order_id: peerOrder * 1000 + 3, number: peerOrder, email: BUYER })).outcome,
    "created");
  assert.equal((await funnel()).paid_orders_all_sources - after.paid_orders_all_sources, 1);
  await page.goto(`${BASE}/#order=${peerOrder}`);
  await page.fill("#email", BUYER);
  await page.click("#claim-submit");
  await page.locator("#step-code").waitFor();
  const mails = (await control("/codes")).sent.filter((m) => m.to === BUYER);
  await page.fill("#code", mails[mails.length - 1].code);
  await page.click("#code-submit");
  await page.locator("#step-birth").waitFor();
  assert.equal(await page.inputValue("#birth_date"), "", "birth details were not carried over");
  await page.selectOption("#place_id", "in-jaipur");
  await page.fill("#birth_date", BIRTH.date);
  await page.fill("#birth_time", BIRTH.time);
  await page.check("#consent");
  const [download] = await Promise.all([page.waitForEvent("download", { timeout: 90000 }), page.click("#generate")]);
  const bytes = fs.readFileSync(await download.path());
  assert.equal(bytes.subarray(0, 5).toString(), "%PDF-");
  assert.equal((bytes.toString("latin1").match(/\/Type\s*\/Page[^s]/g) || []).length, 14);
  await shot(page, "desktop-04-paid-pdf-ready");
  assert.deepEqual(errors, []);
  await ctx.close();
});

test("refusals: pre-1970, future, missing time and malformed values show field errors, nothing shown", async () => {
  const { ctx, page, errors } = await open();
  await page.click("#preview-submit");
  assert.match(await page.locator("#place_id-error").innerText(), /Choose your birthplace/);
  assert.match(await page.locator("#birth_date-error").innerText(), /valid birth date/);
  assert.match(await page.locator("#birth_time-error").innerText(), /exact birth time/);
  assert.equal(await page.evaluate(() => document.activeElement.id), "place_id");
  await shot(page, "desktop-05-missing-fields");
  await fill(page, { date: "1969-12-31" });
  await page.click("#preview-submit");
  assert.match(await page.locator("#birth_date-error").innerText(), /before 1 January 1970/);
  await fill(page, { date: "2099-01-01" });
  await page.click("#preview-submit");
  assert.match(await page.locator("#birth_date-error").innerText(), /cannot be in the future/);
  assert.ok(await page.locator("#step-result").isHidden());
  // The server refuses the same things even if the page's checks are bypassed.
  const direct = await page.evaluate(async () => {
    const post = async (b) => { const r = await fetch("/api/preview", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(b) }); return [r.status, (await r.json()).error.code]; };
    return [await post({ place_id: "in-jaipur", birth_date: "1969-12-31", birth_time: "10:00" }),
      await post({ place_id: "gb-london", birth_date: "1990-05-17", birth_time: "10:00" }),
      await post({ place_id: "in-jaipur", birth_date: "1990-05-17", birth_time: "" }),
      await post({ place_id: "in-jaipur", birth_date: "1990-05-17", birth_time: "10:00", display_name: "x" })];
  });
  assert.deepEqual(direct, [[422, "HISTORICAL_CLOCK_UNVERIFIED"], [422, "PLACE_UNKNOWN"], [422, "BIRTH_TIME_REQUIRED"],
    [400, "REQUEST_INVALID"]]);
  assert.deepEqual(errors, []);
  await ctx.close();
});

test("birth-time note is withheld by default, even next to a Lagna boundary (SCI-06 pending)", async () => {
  const { ctx, page } = await open();
  await fill(page, { place: "in-mumbai", date: "1995-03-21", time: "06:26:00" });
  const json = await (await showPreview(page)).json();
  await page.locator("#step-result").waitFor();
  assert.ok(!("birth_time_check" in json), "not computed or returned");
  assert.ok(await page.locator("#check-changed").isHidden());
  assert.ok(await page.locator("#check-unassessable").isHidden());
  assert.equal(await page.locator("#fact-lagna_rashi .fact__value").innerText(), "Kumbha");
  await shot(page, "desktop-06-near-boundary-no-note");
  await page.click("#again");
  assert.ok(await page.locator("#step-result").isHidden());
  assert.equal(await page.inputValue("#birth_time"), "");
  await ctx.close();
});

test("rate limit: the seventh preview in a minute is refused politely", async () => {
  const { ctx, page } = await open();
  await fill(page);
  const codes = [];
  for (let i = 0; i < 7; i += 1) codes.push((await showPreview(page)).status());
  assert.deepEqual(codes, [200, 200, 200, 200, 200, 200, 429]);
  assert.match(await page.locator("#alert-text").innerText(), /many previews in a short time/);
  await ctx.close();
});

test("optional opt-in: unchecked, separate from the preview, double opt-in, withdraw and delete", async () => {
  const { ctx, page, errors } = await open();
  await fill(page);
  await showPreview(page);
  await page.locator("#step-leads").waitFor();
  await page.fill("#lead_email", LEAD);
  await page.click("#lead-submit");
  assert.match(await page.locator("#lead_consent-error").innerText(), /Tick the box/);
  assert.match(await page.locator("#lead_adult-error").innerText(), /18 or older/);
  await shot(page, "desktop-07-optin-errors");
  await page.check("#lead_consent");
  await page.check("#lead_adult");
  await page.click("#lead-submit");
  await page.locator("#lead-status").filter({ hasText: "confirmation link" }).waitFor();
  let leads = await control("/leads");
  assert.deepEqual(leads.mailable, [], "nothing is mailable before confirmation");
  for (const needle of ["1990", "Jaipur", "jaipur", "Kanya", "Makara", "14:30"]) assert.ok(!leads.dump.includes(needle), needle);
  const mail = (await control("/codes")).sent.filter((m) => m.to === LEAD).pop();
  assert.match(mail.subject, /confirm/i);
  const token = /#confirm=([A-Za-z0-9_-]+)/.exec(mail.text)[1];
  for (const needle of ["1990", "Jaipur", "Kanya"]) assert.ok(!mail.text.includes(needle));

  // Opening the link (as a person or a script-running link scanner) only shows the state; it never subscribes.
  await page.goto(`${BASE}/marketing#confirm=${token}`);
  await page.locator("#manage-state").filter({ hasText: "waiting for confirmation" }).waitFor();
  assert.equal(new URL(page.url()).hash, "", "token removed from the address bar");
  await page.waitForTimeout(500);
  assert.deepEqual((await control("/leads")).mailable, [], "page load did not confirm");
  assert.equal((await control("/leads")).counts.pending, 1);
  await page.reload();
  assert.deepEqual((await control("/leads")).mailable, [], "reload did not confirm");
  // A link scanner without scripts just fetches the page: still pending.
  await fetch(`${BASE}/marketing#confirm=${token}`);
  assert.deepEqual((await control("/leads")).mailable, []);
  await page.goto("about:blank");
  await page.goto(`${BASE}/marketing#confirm=${token}`);
  await page.locator("#confirm").waitFor();
  await shot(page, "desktop-08a-marketing-pending");
  await page.click("#confirm");
  await page.locator("#manage-state").filter({ hasText: "signed up" }).waitFor();
  assert.deepEqual((await control("/leads")).mailable, [LEAD]);
  await shot(page, "desktop-08-marketing-confirmed");
  await page.click("#withdraw");
  await page.locator("#manage-state").filter({ hasText: "stopped" }).waitFor();
  assert.deepEqual((await control("/leads")).mailable, []);
  await page.click("#delete");
  await page.locator("#manage-state").filter({ hasText: "deleted" }).waitFor();
  leads = await control("/leads");
  assert.ok(!leads.dump.includes(LEAD), "address erased");
  await shot(page, "desktop-09-marketing-deleted");
  assert.deepEqual(errors, []);
  await ctx.close();
});

test("privacy: no storage, no cookies, no third-party requests, nothing in the URL", async () => {
  const { ctx, page, requests } = await open();
  await fill(page, BIRTH, "Synthetic Name");
  await showPreview(page);
  await page.locator("#step-result").waitFor();
  const storage = await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length,
    cookie: document.cookie, url: location.href }));
  assert.deepEqual(storage, { local: 0, session: 0, cookie: "", url: BASE + "/kundali" });
  assert.deepEqual((await ctx.cookies()).length, 0);
  const hosts = new Set(requests.map((r) => new URL(r.url).host));
  assert.deepEqual([...hosts], [`127.0.0.1:${PORT}`]);
  for (const r of requests) assert.ok(!r.url.includes("1990") && !r.url.includes("jaipur"), r.url);
  await ctx.close();
});

test("keyboard only and a Hindi-locale browser", async () => {
  const { ctx, page } = await open({ locale: "hi-IN" });
  assert.equal(await page.getAttribute("html", "lang"), "en");
  assert.equal(await page.getAttribute(".notice--hi", "lang"), "hi");
  await page.focus("#display_name");
  await page.keyboard.press("Tab");
  assert.equal(await page.evaluate(() => document.activeElement.id), "place_id");
  await page.selectOption("#place_id", "in-chennai");
  await page.fill("#birth_date", "2001-01-01");
  await page.fill("#birth_time", "09:15");
  await page.focus("#birth_time");
  await page.keyboard.press("Enter");
  await page.locator("#step-result").waitFor();
  assert.equal(await page.evaluate(() => document.activeElement.id), "h-result", "focus moves to the result");
  await ctx.close();
});

for (const [label, device] of [["phone-pixel7", devices["Pixel 7"]], ["phone-iphone13", devices["iPhone 13"]],
  ["narrow-320", { viewport: { width: 320, height: 640 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
  ["desktop-1366", { viewport: { width: 1366, height: 900 } }]]) {
  test(`layout at ${label}: no horizontal scroll, 44px targets, 16px inputs`, async () => {
    const { ctx, page, errors } = await open({ device });
    const check = async (step) => {
      const m = await page.evaluate(() => {
        const vis = (el) => el.offsetParent !== null;
        const small = [...document.querySelectorAll("button, a.button, input, select")].filter(vis)
          .filter((el) => el.type !== "checkbox" && el.type !== "radio" && el.getBoundingClientRect().height < 43.5)
          .map((el) => el.id || el.className);
        const tinyText = [...document.querySelectorAll("input, select")].filter(vis)
          .filter((el) => el.type !== "checkbox" && el.type !== "radio")
          .filter((el) => parseFloat(getComputedStyle(el).fontSize) < 16).map((el) => el.id);
        return { overflow: document.documentElement.scrollWidth - window.innerWidth, small, tinyText };
      });
      assert.ok(m.overflow <= 0, `${step}: horizontal overflow ${m.overflow}px`);
      assert.deepEqual(m.small, [], `${step}: small targets`);
      assert.deepEqual(m.tinyText, [], `${step}: inputs under 16px zoom on iOS`);
    };
    await check("start");
    await shot(page, `${label}-01-start`);
    await fill(page, BIRTH, "Synthetic Asha");
    await showPreview(page);
    await page.locator("#step-result").waitFor();
    await check("result");
    await shot(page, `${label}-02-result`);
    await page.click("#buy");
    await page.locator("#handoff").waitFor();
    await check("handoff");
    await shot(page, `${label}-03-handoff`);
    await page.click("#contents summary");
    await check("contents");
    await shot(page, `${label}-04-contents`);
    assert.deepEqual(errors, []);
    await ctx.close();
  });
}

test("automated accessibility scan (axe-core, WCAG 2.1 A/AA): start, errors, result, hand-off, opt-in, preferences", async () => {
  const { ctx, page } = await open({ bypassCSP: true });
  const scan = async (step) => {
    await page.addScriptTag({ path: AXE });
    const res = await page.evaluate(async () => {
      // eslint-disable-next-line no-undef
      const r = await axe.run(document, { runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"] } });
      return r.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
    });
    assert.deepEqual(res, [], step);
  };
  await scan("start");
  await page.click("#preview-submit");
  await scan("errors");
  await fill(page);
  await showPreview(page);
  await page.locator("#step-result").waitFor();
  await scan("result");
  await page.click("#buy");
  await scan("handoff");
  await page.click("#contents summary");
  await scan("contents-open");
  await page.click("#lead-submit");
  await scan("optin-errors");
  await page.goto(`${BASE}/marketing`);
  await scan("preferences");
  await ctx.close();
});
