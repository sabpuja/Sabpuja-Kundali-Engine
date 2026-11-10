// Customer-journey acceptance in a real browser (KUN-COM-UX-CLAIM-001). Synthetic data only.
//
//   cd commerce/tests/browser && npm ci
//   SABPUJA_TEST_EPHE_PATH=... PYTHON=python3 node --test journey.test.cjs
//
// Starts journey_server.py (real App, Store, transport and Essentials renderer; mock mailer; fake Shopify) and
// drives the claim page with Playwright Chromium at desktop and phone sizes. SHOTS=<dir> saves screenshots.
"use strict";
const { test, before, after } = require("node:test");
const assert = require("node:assert/strict");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const { chromium, devices } = require("playwright");

const ROOT = path.resolve(__dirname, "../../..");
const PORT = 18771, CONTROL = 18772;
const BASE = `http://127.0.0.1:${PORT}`;
const EMAIL = "synthetic.buyer@example.invalid";
const SHOTS = process.env.SHOTS || "";
const AXE = require.resolve("axe-core/axe.min.js");

let proc, browser, nextOrder = 7100;

async function control(p, body) {
  const r = await fetch(`http://127.0.0.1:${CONTROL}${p}`, body === undefined ? {} :
    { method: "POST", body: JSON.stringify(body), headers: { "Content-Type": "application/json" } });
  return r.json();
}
async function codesTo(email) { return (await control("/codes")).sent.filter((m) => m.to === email); }
async function lastCode(email) { const c = await codesTo(email || EMAIL); return c.length ? c[c.length - 1].code : null; }
async function stats() { return control("/stats"); }
async function newOrder(extra) {
  nextOrder += 1;
  const o = Object.assign({ order_id: nextOrder * 1000 + 17, number: nextOrder, email: EMAIL }, extra || {});
  await control("/clock", { seconds: 61 }); // fresh rate-limit window per test
  o.outcome = (await control("/paid", o)).outcome;
  return o;
}
async function shot(page, name) {
  if (SHOTS) await page.screenshot({ path: path.join(SHOTS, name + ".png"), fullPage: true });
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
  const ctx = await browser.newContext(Object.assign({ acceptDownloads: true, locale: "en-IN" }, o.device || {},
    o.locale ? { locale: o.locale } : {}, o.bypassCSP ? { bypassCSP: true } : {}));
  const page = await ctx.newPage();
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e)));
  // The page asks /api/session on load; "no session yet" is a 401 by contract, which Chromium logs. Anything else counts.
  page.on("console", (m) => {
    if (m.type() === "error" && !/status of 401 \(Unauthorized\)/.test(m.text())) errors.push(m.text());
  });
  await page.goto(BASE + "/" + (o.hash || ""));
  return { ctx, page, errors };
}
const status = (page) => page.locator("#status").innerText();
const alertText = (page) => page.locator("#alert-text").innerText();

async function claimAndVerify(page, order, opts) {
  const o = opts || {};
  if (!o.byRef) await page.fill("#order_number", "#" + order.number);
  await page.fill("#email", o.email || EMAIL);
  await page.click("#claim-submit");
  await page.locator("#step-code").waitFor();
  if (o.stopAtCode) return;
  await page.fill("#code", await lastCode(o.email));
  await page.click("#code-submit");
  await page.locator("#step-birth").waitFor();
}
async function fillBirth(page, b) {
  const v = Object.assign({ place: "in-jaipur", date: "1990-05-17", time: "14:30:00" }, b || {});
  await page.locator("#place_id option[value='in-jaipur']").waitFor({ state: "attached" });
  if (v.place) await page.selectOption("#place_id", v.place);
  if (v.date) await page.fill("#birth_date", v.date);
  if (v.time) await page.fill("#birth_time", v.time);
  if (v.consent !== false) await page.check("#consent");
}
async function generate(page) {
  const [download] = await Promise.all([page.waitForEvent("download", { timeout: 90000 }), page.click("#generate")]);
  await page.locator("#step-done").waitFor();
  const file = await download.path();
  return { name: download.suggestedFilename(), bytes: fs.readFileSync(file) };
}

// ---------------------------------------------------------------------------------------------------------------

test("successful purchase from the Thank you page link: order ref, code, birth details, 14-page PDF", async () => {
  const order = await newOrder();
  const { ctx, page, errors } = await open({ hash: `#ref=${order.order_id}` });
  assert.equal(new URL(page.url()).hash, "", "fragment removed from the address bar");
  assert.ok(await page.locator("#ref-box").isVisible());
  assert.ok(!(await page.locator("#order-field").isVisible()));
  await shot(page, "desktop-01-claim-from-thank-you");
  await page.fill("#email", EMAIL);
  await page.click("#claim-submit");
  await page.locator("#step-code").waitFor();
  assert.match(await page.locator("#code-intro").innerText(), /synthetic\.buyer@example\.invalid/);
  assert.match(await page.locator("#code-limits").innerText(), /10 minutes/);
  assert.ok(await page.locator("#resend").isDisabled(), "resend waits for the cooldown");
  assert.match(await page.locator("#resend-wait").innerText(), /new code in \d+ seconds/);
  await shot(page, "desktop-02-code");
  const mails = await codesTo(EMAIL);
  const mail = mails[mails.length - 1];
  assert.match(mail.text, new RegExp(`order #${order.number} is [0-9]{6}`));
  assert.doesNotMatch(mail.text, /https?:\/\//, "code e-mail carries no link");
  await page.fill("#code", mail.code.slice(0, 3) + " " + mail.code.slice(3)); // pasted with a space
  await page.click("#code-submit");
  await page.locator("#step-birth").waitFor();
  assert.match(await page.locator("#allowance").innerText(), new RegExp(`Order #${order.number}\\..*English`, "s"));
  assert.match(await page.locator("#allowance").innerText(), /up to 3 corrected versions within 30 days/);
  assert.equal(await page.locator("#generate").innerText(), "Prepare my PDF");
  await fillBirth(page);
  await shot(page, "desktop-03-birth");
  const pdf = await generate(page);
  assert.equal(pdf.name, "Sabpuja-Janam-Kundali.pdf");
  assert.equal(pdf.bytes.subarray(0, 5).toString(), "%PDF-");
  const pages = (pdf.bytes.toString("latin1").match(/\/Type\s*\/Page[^s]/g) || []).length;
  assert.equal(pages, 14, "English Essentials has 14 pages");
  assert.match(await page.locator("#done-allowance").innerText(), /3 corrected versions left until \d{1,2} \w+ \d{4}/);
  await shot(page, "desktop-04-done");
  assert.deepEqual(errors, []);
  await ctx.close();
});

test("order status / e-mail link prefills the order number; repeated download does not use a generation", async () => {
  const order = await newOrder();
  const { ctx, page } = await open({ hash: `#order=${order.number}` });
  assert.equal(await page.inputValue("#order_number"), "#" + order.number);
  await claimAndVerify(page, order);
  await fillBirth(page);
  await generate(page);
  const calls = (await stats()).render_calls;
  const [again] = await Promise.all([page.waitForEvent("download"), page.click("#save-pdf")]);
  assert.equal(again.suggestedFilename(), "Sabpuja-Janam-Kundali.pdf");
  assert.equal((await stats()).render_calls, calls, "saving again re-uses the in-page copy");
  // A correction uses exactly one generation and says so on the button.
  await page.click("#correct");
  assert.equal(await page.locator("#generate").innerText(), "Prepare corrected PDF (uses 1 of 3)");
  await page.fill("#birth_time", "14:31:00");
  await generate(page);
  assert.match(await page.locator("#done-allowance").innerText(), /2 corrected versions left/);
  await ctx.close();
});

test("missing or malformed e-mail and order number are caught on the page with field messages", async () => {
  const { ctx, page } = await open();
  const sentBefore = (await control("/codes")).sent.length;
  await page.click("#claim-submit");
  assert.equal(await page.locator("#order_number").getAttribute("aria-invalid"), "true");
  assert.equal(await page.locator("#email").getAttribute("aria-invalid"), "true");
  assert.match(await page.locator("#email-error").innerText(), /Enter the e-mail address you used at checkout/);
  assert.equal(await page.evaluate(() => document.activeElement.id), "order_number", "focus moves to first error");
  await page.fill("#order_number", "ABC");
  await page.fill("#email", "buyer@");
  await page.click("#claim-submit");
  assert.match(await page.locator("#order_number-error").innerText(), /digits only/);
  assert.match(await page.locator("#email-error").innerText(), /looks incomplete/);
  await shot(page, "desktop-05-claim-errors");
  assert.equal((await control("/codes")).sent.length, sentBefore, "nothing sent");
  await ctx.close();
});

test("wrong e-mail, unknown order, unpaid order and missing checkout e-mail all get the same neutral reply", async () => {
  const paid = await newOrder();
  const unpaid = await newOrder({ status: "pending" });
  const noEmail = await newOrder({ email: null });
  assert.equal(unpaid.outcome, "ignored_not_sellable");
  assert.equal(noEmail.outcome, "created_without_email");
  const texts = [];
  for (const [number, email] of [[paid.number, "someone.else@example.invalid"], [999999, EMAIL],
    [unpaid.number, EMAIL], [noEmail.number, EMAIL]]) {
    const { ctx, page } = await open();
    await page.fill("#order_number", String(number));
    await page.fill("#email", email);
    await page.click("#claim-submit");
    await page.locator("#step-code").waitFor();
    texts.push(await page.locator("#step-code").innerText());
    await ctx.close();
    await control("/clock", { seconds: 61 });
  }
  assert.equal(new Set(texts.map((t) => t.replace(/[^\s]+@example\.invalid/, "<email>"))).size, 1,
    "identical page for every case");
  const sent = (await control("/codes")).sent;
  assert.equal(sent.filter((m) => m.to === "someone.else@example.invalid").length, 0);
  assert.equal(sent.filter((m) => new RegExp(`#(${unpaid.number}|${noEmail.number}|999999) `).test(m.text)).length, 0);
});

test("expired code: clear message, resend after the cooldown, new code works", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order, { stopAtCode: true });
  const first = await lastCode();
  await control("/clock", { seconds: 601 });
  await page.fill("#code", first);
  await page.click("#code-submit");
  await page.locator("#code-error").waitFor();
  assert.match(await page.locator("#code-error").innerText(), /expire after 10 minutes/);
  assert.equal(await page.locator("#code").getAttribute("aria-invalid"), "true");
  await shot(page, "desktop-06-code-expired");
  // The page counts down in real time; the server cooldown already passed on the test clock.
  await page.evaluate(() => { const b = document.getElementById("resend"); b.disabled = false; });
  await page.click("#resend");
  await page.waitForFunction(() => /new code is on its way/.test(document.getElementById("status").innerText));
  const second = await lastCode();
  assert.notEqual(second, first);
  await page.fill("#code", second);
  await page.click("#code-submit");
  await page.locator("#step-birth").waitFor();
  await ctx.close();
});

test("five wrong codes lock the code; the page explains how to recover", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order, { stopAtCode: true });
  const good = await lastCode();
  const bad = String((Number(good) + 1) % 1000000).padStart(6, "0");
  for (let i = 0; i < 5; i += 1) {
    await page.fill("#code", bad);
    await page.click("#code-submit");
    await page.locator("#code-error").waitFor();
  }
  await page.fill("#code", good);
  await page.click("#code-submit");
  await page.waitForFunction(() => document.getElementById("code").getAttribute("aria-invalid") === "true");
  assert.match(await page.locator("#code-error").innerText(), /send a new code/);
  assert.ok(await page.locator("#step-code").isVisible());
  await ctx.close();
});

test("refund after verification: the session ends, nothing is produced, and a new claim gets no code", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order);
  await fillBirth(page);
  assert.equal((await control("/refund", { order_id: order.order_id })).outcome, "revoked_refunded");
  const calls = (await stats()).render_calls;
  await page.click("#generate");
  // A refund ends every session on the order (existing security rule), so the page asks to verify again ...
  await page.locator("#step-claim").waitFor();
  assert.match(await alertText(page), /verify your order again/);
  assert.equal((await stats()).render_calls, calls);
  await shot(page, "desktop-07-refunded");
  // ... and the refunded order no longer receives a code (same neutral reply as any other input).
  await control("/clock", { seconds: 61 });
  const sent = (await codesTo(EMAIL)).length;
  await page.click("#claim-submit");
  await page.locator("#step-code").waitFor();
  assert.equal((await codesTo(EMAIL)).length, sent);
  await ctx.close();
});

test("cancellation before claiming: neutral reply, no code, no session", async () => {
  const order = await newOrder();
  await control("/cancel", { order_id: order.order_id });
  const { ctx, page } = await open();
  await claimAndVerify(page, order, { stopAtCode: true });
  assert.equal((await codesTo(EMAIL)).filter((m) => m.text.includes(`#${order.number} `)).length, 0);
  await ctx.close();
});

test("birthplace, date and time problems: field messages, nothing used", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order);
  await page.locator("#place_id option[value='in-jaipur']").waitFor({ state: "attached" });
  await page.click("#generate");
  assert.match(await page.locator("#place_id-error").innerText(), /Choose your birthplace/);
  assert.match(await page.locator("#birth_time-error").innerText(), /never assume a time/);
  assert.match(await page.locator("#consent-error").innerText(), /confirm/);
  assert.match(await page.locator("#place_id-help").innerText(), /do not pick another city/);
  await shot(page, "desktop-08-birth-errors");
  // A place that is not offered (tampered request) is refused by the server, not guessed.
  await fillBirth(page);
  await page.evaluate(() => { const o = document.createElement("option"); o.value = "gb-london"; o.textContent = "x";
    document.getElementById("place_id").appendChild(o); document.getElementById("place_id").value = "gb-london"; });
  await page.click("#generate");
  await page.locator("#place_id-error").waitFor();
  assert.match(await page.locator("#place_id-error").innerText(), /Choose your birthplace from the list/);
  // Before 1970: refused with an explanation (calculation boundary unchanged).
  await page.selectOption("#place_id", "in-jaipur");
  await page.evaluate(() => { document.getElementById("birth_date").removeAttribute("min"); });
  await page.fill("#birth_date", "1965-03-02");
  await page.click("#generate");
  await page.waitForFunction(() => !document.getElementById("birth_date-error").hidden);
  assert.match(await page.locator("#birth_date-error").innerText(), /before 1 January 1970/);
  const s = await page.evaluate(async () => (await fetch("/api/session")).json());
  assert.equal(s.remaining, 4);
  assert.equal(s.used, 0);
  await ctx.close();
});

test("PDF generation failure: message says nothing was used; retry succeeds", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order);
  await fillBirth(page);
  await control("/render", { mode: "fail" });
  try {
    await page.click("#generate");
    await page.locator("#alert").waitFor();
    assert.match(await alertText(page), /cannot be prepared right now\. Nothing was used/);
    assert.ok(await page.locator("#generate").isEnabled());
    await shot(page, "desktop-09-render-failed");
  } finally { await control("/render", { mode: "ok" }); }
  await generate(page);
  assert.match(await page.locator("#done-allowance").innerText(), /3 corrected versions left/);
  await ctx.close();
});

test("double submit and slow generation: one render, progress shown, controls disabled", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order);
  await fillBirth(page);
  await control("/render", { mode: "ok", delay: 1.5 });
  const before = (await stats()).render_calls;
  try {
    const dl = page.waitForEvent("download", { timeout: 90000 });
    await page.click("#generate");
    await page.locator("#progress").waitFor();
    assert.ok(await page.locator("#generate").isDisabled());
    assert.ok(await page.locator("#place_id").isDisabled());
    assert.equal(await page.locator("#birth-form").getAttribute("aria-busy"), "true");
    await shot(page, "desktop-10-preparing");
    await page.locator("#birth-form").evaluate((f) => { f.requestSubmit(); f.requestSubmit(); });
    await dl;
  } finally { await control("/render", { mode: "ok", delay: 0 }); }
  assert.equal((await stats()).render_calls - before, 1);
  await ctx.close();
});

test("network failure during generation: message, nothing counted, retry works", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order);
  await fillBirth(page);
  await page.route("**/api/generate", (route) => route.abort("internetdisconnected"));
  await page.click("#generate");
  await page.locator("#alert").waitFor();
  assert.match(await alertText(page), /could not reach Sabpuja/);
  await page.unroute("**/api/generate");
  assert.match(await page.locator("#allowance").innerText(), /up to 3 corrected/);
  await generate(page);
  await ctx.close();
});

test("network failure when asking for a code is reported, not swallowed", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await page.route("**/api/claim/start", (route) => route.abort("internetdisconnected"));
  await page.fill("#order_number", String(order.number));
  await page.fill("#email", EMAIL);
  await page.click("#claim-submit");
  await page.locator("#alert").waitFor();
  assert.match(await alertText(page), /check your internet connection/i);
  assert.ok(await page.locator("#claim-submit").isEnabled());
  await ctx.close();
});

test("refresh after verification returns to the birth step; refresh during code entry starts over safely", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order, { stopAtCode: true });
  await page.reload();
  assert.ok(await page.locator("#step-claim").isVisible());
  assert.equal(await page.inputValue("#email"), "", "e-mail is not kept anywhere by the page");
  await control("/clock", { seconds: 61 });
  await claimAndVerify(page, order);
  await page.reload();
  await page.locator("#step-birth").waitFor();
  assert.match(await status(page), /Welcome back/);
  await ctx.close();
});

test("order check unavailable and session expiry give recoverable messages", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order, { stopAtCode: true });
  await control("/verifier", { down: true });
  try {
    await page.fill("#code", await lastCode());
    await page.click("#code-submit");
    await page.locator("#alert").waitFor();
    assert.match(await alertText(page), /cannot confirm your order.*Nothing was used/);
  } finally { await control("/verifier", { down: false }); }
  await control("/clock", { seconds: 61 });
  await page.click("#change-details");
  await claimAndVerify(page, order);
  await fillBirth(page);
  await control("/clock", { seconds: 1801 });
  await page.click("#generate");
  await page.locator("#step-claim").waitFor();
  assert.match(await alertText(page), /verification lasts 30 minutes/);
  await ctx.close();
});

test("all generations used: button disabled, message explains", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order);
  await fillBirth(page);
  for (let i = 0; i < 4; i += 1) {
    if (i) { await page.click("#correct"); await page.fill("#birth_time", `14:3${i}:00`); }
    await generate(page);
  }
  assert.match(await page.locator("#done-allowance").innerText(), /All report generations for this order have been used/);
  assert.ok(await page.locator("#correct").isHidden());
  await ctx.close();
});

test("sign out clears the page and the session", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await claimAndVerify(page, order);
  await fillBirth(page);
  await page.click("#logout");
  await page.locator("#step-claim").waitFor();
  assert.equal(await page.inputValue("#birth_time"), "");
  const s = await page.evaluate(async () => (await fetch("/api/session")).status);
  assert.equal(s, 401);
  await ctx.close();
});

test("keyboard only: skip link, labels, Enter submits, focus lands on each step heading", async () => {
  const order = await newOrder();
  const { ctx, page } = await open();
  await page.keyboard.press("Tab");
  assert.equal(await page.evaluate(() => document.activeElement.className), "skip-link");
  for (const id of ["order_number", "email", "code", "place_id", "birth_date", "birth_time", "display_name", "consent"]) {
    assert.equal(await page.locator(`label[for='${id}'], label:has(#${id})`).count() >= 1, true, id + " has a label");
  }
  await page.focus("#order_number");
  await page.keyboard.type(String(order.number));
  await page.keyboard.press("Tab");
  await page.keyboard.type(EMAIL);
  await page.keyboard.press("Enter");
  await page.locator("#step-code").waitFor();
  assert.equal(await page.evaluate(() => document.activeElement.id), "code");
  await page.keyboard.type(await lastCode());
  await page.keyboard.press("Enter");
  await page.locator("#step-birth").waitFor();
  assert.equal(await page.evaluate(() => document.activeElement.id), "h-birth");
  await ctx.close();
});

test("Hindi-language browser: English page with a Hindi English-only notice, marked lang=hi", async () => {
  const { ctx, page } = await open({ locale: "hi-IN" });
  assert.equal(await page.getAttribute("html", "lang"), "en");
  assert.equal(await page.locator(".notice--hi").getAttribute("lang"), "hi");
  assert.match(await page.locator(".notice--hi").innerText(), /केवल अंग्रेज़ी/);
  const font = await page.locator(".notice--hi").evaluate((el) => getComputedStyle(el).fontFamily);
  assert.match(font, /Poppins/);
  await ctx.close();
});

test("security and privacy of the page: CSP, no storage, no third-party requests, source link", async () => {
  const order = await newOrder();
  const { ctx, page } = await open({ hash: `#ref=${order.order_id}` });
  const hosts = new Set();
  page.on("request", (r) => hosts.add(new URL(r.url()).host));
  const resp = await page.reload();
  const csp = resp.headers()["content-security-policy"];
  assert.match(csp, /default-src 'none'/);
  assert.match(csp, /font-src 'self'/);
  assert.equal(resp.headers()["referrer-policy"], "no-referrer");
  await page.fill("#order_number", String(order.number));
  await page.fill("#email", EMAIL);
  await page.click("#claim-submit");
  await page.locator("#step-code").waitFor();
  await page.fill("#code", await lastCode());
  await page.click("#code-submit");
  await page.locator("#step-birth").waitFor();
  await fillBirth(page, { time: "09:05:00" });
  await generate(page);
  const storage = await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length,
    cookie: document.cookie, url: location.href }));
  assert.deepEqual(storage, { local: 0, session: 0, cookie: "", url: BASE + "/" });
  assert.deepEqual([...hosts], [`127.0.0.1:${PORT}`]);
  assert.equal(await page.getAttribute("footer a", "href"), "https://github.com/sabpuja/Sabpuja-Kundali-Engine");
  const db = fs.readFileSync((await stats()).db);
  for (const needle of ["1990-05-17", "09:05", "in-jaipur", EMAIL]) assert.ok(!db.includes(Buffer.from(needle)), needle);
  await ctx.close();
});

for (const [label, device] of [["phone-pixel7", devices["Pixel 7"]], ["phone-iphone13", devices["iPhone 13"]],
  ["narrow-320", { viewport: { width: 320, height: 640 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 }],
  ["desktop-1366", { viewport: { width: 1366, height: 900 } }]]) {
  test(`layout at ${label}: no horizontal scroll, 44px targets, 16px inputs, full journey`, async () => {
    const order = await newOrder();
    const { ctx, page, errors } = await open({ device, hash: `#order=${order.number}` });
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
    await check("claim");
    await shot(page, `${label}-01-claim`);
    await page.fill("#email", EMAIL);
    await page.click("#claim-submit");
    await page.locator("#step-code").waitFor();
    await check("code");
    await shot(page, `${label}-02-code`);
    await page.fill("#code", await lastCode());
    await page.click("#code-submit");
    await page.locator("#step-birth").waitFor();
    await fillBirth(page);
    await check("birth");
    await shot(page, `${label}-03-birth`);
    await generate(page);
    await check("done");
    await shot(page, `${label}-04-done`);
    assert.deepEqual(errors, []);
    await ctx.close();
  });
}

test("automated accessibility scan (axe-core, WCAG 2.1 A/AA) on every step: no violations", async () => {
  const order = await newOrder();
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
  await scan("claim");
  await page.click("#claim-submit");
  await scan("claim-errors");
  await page.fill("#order_number", String(order.number));
  await page.fill("#email", EMAIL);
  await page.click("#claim-submit");
  await page.locator("#step-code").waitFor();
  await scan("code");
  await page.fill("#code", await lastCode());
  await page.click("#code-submit");
  await page.locator("#step-birth").waitFor();
  await page.click("#generate");
  await scan("birth-errors");
  await fillBirth(page);
  await generate(page);
  await scan("done");
  await ctx.close();
});
