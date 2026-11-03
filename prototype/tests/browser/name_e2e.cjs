/* KUN-UX-NAME-001 browser QA: optional Full name on the form, result and PDF.
 *
 *   SABPUJA_TEST_EPHE_PATH=/path/to/ephe PROTOTYPE_PYTHON=/path/to/python \
 *     node prototype/tests/browser/name_e2e.cjs --out /tmp/name-shots
 *
 * Starts the real server (real engine, real Swiss data) and drives Chromium at 280, 375, 768
 * and 1440 px. Synthetic names only. Exit 0 only if every check passes.
 */
"use strict";
const { chromium } = require("playwright");
const { spawn } = require("child_process");
const fs = require("fs");
const net = require("net");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const outIdx = process.argv.indexOf("--out");
const OUT = outIdx > 0 ? process.argv[outIdx + 1] : path.join(ROOT, "name-shots");
const EPHE = process.env.SABPUJA_TEST_EPHE_PATH;
const PYTHON = process.env.PROTOTYPE_PYTHON || "python3";
if (!EPHE) { console.log("UNAVAILABLE: SABPUJA_TEST_EPHE_PATH unset"); process.exit(3); }
fs.mkdirSync(OUT, { recursive: true });

const CANARY = "Zzyzx Qwertyuiop";
const HINDI = "क्षत्रिय प्रियंका सिद्धार्थ";
const results = [];
function check(view, name, ok, detail) {
  results.push({ view, name, ok: !!ok });
  console.log(`${ok ? "PASS" : "FAIL"} [${view}] ${name}${ok ? "" : " :: " + JSON.stringify(detail)}`);
}
function freePort() {
  return new Promise((resolve) => { const s = net.createServer(); s.listen(0, "127.0.0.1", () => { const p = s.address().port; s.close(() => resolve(p)); }); });
}
async function startServer(port) {
  const env = { PATH: process.env.PATH, SABPUJA_EPHE_PATH: EPHE, PYTHONDONTWRITEBYTECODE: "1",
                PYTHONPATH: `${path.join(ROOT, "src")}:${path.join(ROOT, "prototype")}:${ROOT}` };
  const proc = spawn(PYTHON, ["-m", "kundali_prototype", "--port", String(port)], { env, cwd: ROOT });
  let output = "";
  proc.stdout.on("data", (d) => { output += d; });
  proc.stderr.on("data", (d) => { output += d; });
  for (let i = 0; i < 300 && !output.includes("http://127.0.0.1:"); i++) { await new Promise((r) => setTimeout(r, 100)); }
  if (!output.includes("http://127.0.0.1:")) { throw new Error("server did not start: " + output); }
  return { proc, output: () => output };
}

async function fillBirth(page) {
  await page.selectOption("#place", "in-new-delhi");
  await page.fill("#birth-date", "1990-05-15");
  await page.fill("#birth-time", "10:30");
}

async function calculate(page) {
  const [resp] = await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/api/chart") && r.request().method() === "POST"),
    page.click("#submit")
  ]);
  await page.waitForSelector("#result:not([hidden])");
  return resp;
}

async function downloadPdf(page) {
  const [req, download] = await Promise.all([
    page.waitForRequest((r) => r.url().endsWith("/api/report")),
    page.waitForEvent("download"),
    page.click("#download-pdf")
  ]);
  const file = await download.path();
  return { body: JSON.parse(req.postData()), name: download.suggestedFilename(), bytes: fs.readFileSync(file) };
}

async function runView(browser, base, width) {
  const view = `${width}px`;
  const context = await browser.newContext({ viewport: { width, height: 900 }, acceptDownloads: true });
  const page = await context.newPage();
  const chartBodies = [], reportBodies = [], urls = [], errors = [];
  page.on("request", (r) => {
    urls.push(r.url());
    if (r.url().endsWith("/api/chart")) { chartBodies.push(r.postData() || ""); }
    if (r.url().endsWith("/api/report")) { reportBodies.push(r.postData() || ""); }
  });
  page.on("console", (m) => { if (m.type() === "error" && !/status of 422/.test(m.text())) { errors.push(m.text()); } });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(base + "/");
  await page.waitForSelector("#place optgroup", { state: "attached" });

  // Accessible field before the birthplace.
  const field = await page.evaluate(() => {
    const input = document.getElementById("full-name");
    const label = document.querySelector("label[for='full-name']");
    const order = [...document.querySelectorAll("#birth-form input, #birth-form select")].map((e) => e.id);
    return { label: label && label.textContent.replace(/\s+/g, " ").trim(), required: input.required,
             describedby: input.getAttribute("aria-describedby"), autocomplete: input.getAttribute("autocomplete"),
             first: order[0], beforePlace: order.indexOf("full-name") < order.indexOf("place"),
             help: document.getElementById("name-help").textContent };
  });
  check(view, "labelled optional Full name field before the birthplace",
        field.label === "Full name (for Kundali report) optional" && !field.required && field.first === "full-name" &&
        field.beforePlace && field.describedby === "name-help name-error" && field.autocomplete === "off", field);
  check(view, "help text says the name is not used in the calculation and not saved",
        /not used in the calculation/.test(field.help) && /not saved/.test(field.help), field.help);

  // 1. No name: unchanged anonymous flow.
  await fillBirth(page);
  await calculate(page);
  let ui = await page.evaluate(() => ({ forHidden: document.getElementById("result-for").hidden,
    rows: [...document.querySelectorAll("#confirm-list dt")].map((d) => d.textContent) }));
  check(view, "no name: no 'Prepared for' line and no name row", ui.forHidden && ui.rows[0] === "Birthplace", ui);
  let pdf = await downloadPdf(page);
  check(view, "no name: report request has no display_name, filename generic",
        !("display_name" in pdf.body) && pdf.name === "Sabpuja-Janma-Kundali.pdf" && pdf.bytes.slice(0, 5).toString() === "%PDF-", pdf.body);

  // 2. Hindi name.
  await page.fill("#full-name", "  " + HINDI + " ");
  check(view, "a name edit hides the previous result and disables the PDF",
        await page.evaluate(() => document.getElementById("result").hidden && document.getElementById("download-pdf").disabled), "");
  await calculate(page);
  ui = await page.evaluate(() => {
    const strong = document.getElementById("result-name");
    const dd = document.querySelector("#confirm-list [data-field='display_name']");
    return { heading: strong.textContent, shown: !document.getElementById("result-for").hidden,
             children: strong.children.length, dt: dd && dd.previousElementSibling.textContent, dd: dd && dd.textContent,
             overflow: document.documentElement.scrollWidth - window.innerWidth,
             font: getComputedStyle(strong).fontFamily };
  });
  check(view, "Hindi name shown in the heading and confirmed details (trimmed, literal)",
        ui.shown && ui.heading === HINDI && ui.dd === HINDI && ui.dt === "Name on report" && ui.children === 0, ui);
  check(view, "no horizontal page overflow with a name", ui.overflow <= 0, ui.overflow);
  const devaFont = await page.evaluate(async () => {
    await document.fonts.ready;
    return [...document.fonts].filter((f) => f.family.replace(/"/g, "") === "Poppins" && /U\+0?900-97F/i.test(f.unicodeRange))
      .map((f) => f.weight + ":" + f.status);
  });
  check(view, "the bundled Poppins Devanagari face is loaded for the Hindi name",
        devaFont.length === 3 && devaFont.some((f) => /loaded$/.test(f)), devaFont);
  await page.screenshot({ path: path.join(OUT, `name-hindi-${width}.png`), fullPage: true });
  pdf = await downloadPdf(page);
  const lastChart = chartBodies[chartBodies.length - 1];
  check(view, "chart request never carries the name", !/display_name/.test(lastChart) && !lastChart.includes(HINDI), lastChart);
  check(view, "report request carries the trimmed name once", pdf.body.display_name === HINDI &&
        Object.keys(pdf.body).sort().join(",") === "birth_date,birth_time,display_name,place_id", pdf.body);
  check(view, "named PDF downloaded with the generic filename", pdf.name === "Sabpuja-Janma-Kundali.pdf" &&
        pdf.bytes.slice(0, 5).toString() === "%PDF-" && !pdf.name.includes("क्ष"), pdf.name);
  fs.writeFileSync(path.join(OUT, `name-hindi-${width}.pdf`), pdf.bytes);

  // 3. Long Latin name with accents: wraps inside the heading.
  const long = "Zoë-Anne O’Brien " + "Mmmmmmmmm ".repeat(6).trim();
  await page.fill("#full-name", long);
  await calculate(page);
  ui = await page.evaluate(() => ({ overflow: document.documentElement.scrollWidth - window.innerWidth,
    heading: document.getElementById("result-name").textContent,
    within: (() => { const r = document.getElementById("result-name").getBoundingClientRect(); return r.right <= window.innerWidth + 0.5 && r.left >= -0.5; })() }));
  check(view, "long name wraps without page overflow", ui.overflow <= 0 && ui.within && ui.heading === long, ui);
  await page.screenshot({ path: path.join(OUT, `name-long-${width}.png`), fullPage: true });

  // 4. Malicious input: refused on the client, never rendered as markup, never sent.
  const before = chartBodies.length;
  await page.fill("#full-name", "<img src=x onerror=window.__pwned=1>" + CANARY);
  await page.click("#submit");
  ui = await page.evaluate(() => ({ err: document.getElementById("name-error").textContent,
    invalid: document.getElementById("full-name").getAttribute("aria-invalid"),
    focused: document.activeElement && document.activeElement.id, injected: document.querySelectorAll("#result img, #result-name *").length,
    pwned: window.__pwned === 1, resultHidden: document.getElementById("result").hidden }));
  check(view, "markup-like name refused with an accessible error and focus", /letters/.test(ui.err) && ui.invalid === "true" &&
        ui.focused === "full-name" && ui.resultHidden, ui);
  check(view, "no markup injected and nothing sent", ui.injected === 0 && !ui.pwned && chartBodies.length === before, ui);
  await page.fill("#full-name", "A".repeat(81));
  await page.click("#submit");
  check(view, "81-character name refused on the client",
        /at most 80/.test(await page.textContent("#name-error")) && chartBodies.length === before, "");

  // 5. Edit/download race: a name edit during the PDF request aborts it and nothing is saved.
  await page.fill("#full-name", "Asha Verma");
  await calculate(page);
  await page.route("**/api/report", async (route) => { await new Promise((r) => setTimeout(r, 1500)); await route.continue().catch(() => {}); });
  let downloads = 0;
  page.on("download", () => { downloads += 1; });
  await page.click("#download-pdf");
  await page.waitForTimeout(200);
  await page.fill("#full-name", "Asha Verma Rao");
  await page.waitForTimeout(2200);
  ui = await page.evaluate(() => ({ hidden: document.getElementById("result").hidden, disabled: document.getElementById("download-pdf").disabled,
    label: document.getElementById("download-pdf").textContent, name: document.getElementById("result-name").textContent }));
  check(view, "name edit during a PDF request: aborted, no download, result cleared",
        downloads === 0 && ui.hidden && ui.disabled && ui.label === "Download Kundali PDF" && ui.name === "", ui);
  await page.unroute("**/api/report");

  // 6. Clear removes the name and the result.
  await calculate(page);
  await page.click("#clear");
  ui = await page.evaluate(() => ({ value: document.getElementById("full-name").value, hidden: document.getElementById("result").hidden,
    name: document.getElementById("result-name").textContent }));
  check(view, "Clear empties the name and hides the result", ui.value === "" && ui.hidden && ui.name === "", ui);

  // 7. Privacy: no storage, cookies or URL carrying the name.
  const storage = await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length, cookie: document.cookie,
    url: location.href }));
  const cookies = await context.cookies();
  const leakedUrl = urls.filter((u) => /Zzyzx|Asha|%E0%A4|display_name/i.test(u));
  check(view, "no localStorage, sessionStorage, cookies or URL carrying a name",
        storage.local === 0 && storage.session === 0 && storage.cookie === "" && cookies.length === 0 &&
        storage.url === base + "/" && leakedUrl.length === 0, { storage, cookies, leakedUrl });
  check(view, "no unexpected console errors", errors.length === 0, errors);
  await context.close();
}

(async () => {
  const port = await freePort();
  const srv = await startServer(port);
  const base = `http://127.0.0.1:${port}`;
  const browser = await chromium.launch();
  try {
    for (const width of [280, 375, 768, 1440]) { await runView(browser, base, width); }
  } finally {
    await browser.close();
    srv.proc.kill();
  }
  const log = srv.output();
  check("server", "server output contains no synthetic name or birth detail",
        ![CANARY, "Zzyzx", "Asha", "क्षत्रिय", "Mmmmmmmmm", "1990-05-15", "in-new-delhi"].some((s) => log.includes(s)), log);
  const failed = results.filter((r) => !r.ok).length;
  console.log(`NAME_E2E ${failed ? "FAIL" : "PASS"} ${results.length - failed}/${results.length}`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
