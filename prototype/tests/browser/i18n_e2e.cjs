/* KUN-I18N-001 browser QA: English / Hindi interface and report language.
 *
 *   SABPUJA_TEST_EPHE_PATH=/path/to/ephe PROTOTYPE_PYTHON=/path/to/python \
 *     node prototype/tests/browser/i18n_e2e.cjs --out /tmp/i18n-shots
 *
 * Starts the real server (real engine, real Swiss data) and drives Chromium at 280, 375, 768
 * and 1440 px. PROTOTYPE_PYTHON must have PyMuPDF (fitz) to read the downloaded PDFs.
 * Synthetic names and birth details only. Exit 0 only if every check passes.
 */
"use strict";
const { chromium } = require("playwright");
const { spawn, execFileSync } = require("child_process");
const fs = require("fs");
const net = require("net");
const path = require("path");

const ROOT = path.resolve(__dirname, "..", "..", "..");
const outIdx = process.argv.indexOf("--out");
const OUT = outIdx > 0 ? process.argv[outIdx + 1] : path.join(ROOT, "i18n-shots");
const EPHE = process.env.SABPUJA_TEST_EPHE_PATH;
const PYTHON = process.env.PROTOTYPE_PYTHON || "python3";
if (!EPHE) { console.log("UNAVAILABLE: SABPUJA_TEST_EPHE_PATH unset"); process.exit(3); }
fs.mkdirSync(OUT, { recursive: true });
const CATALOG = JSON.parse(fs.readFileSync(path.join(ROOT, "prototype/kundali_prototype/static/i18n.json"), "utf8"));
const UI = CATALOG.ui;

const LATIN_NAME = "Zoë Qwertyuiop";
const HINDI_NAME = "क्षत्रिय प्रियंका सिद्धार्थ";
// Latin words allowed on a Hindi page: proper names of software, data and licences, codes,
// identifiers and engine values that are shown as data (catalog conventions.latin_kept).
const LATIN_ALLOWED = new Set(("Sabpuja Kundali Engine Swiss Ephemeris pyswisseph IANA tzdata PyPI GeoNames Natural Earth " +
  "AGPL Corresponding Source SIL OFL Poppins Inter CC BY UTC SHA sha IAE SE SIDM LAHIRI SIDBIT UNVERIFIED GOLDEN CHARTS " +
  "Asia Kolkata Delta IERS FUTURE CIVIL TIME PROJECTED HIGH LATITUDE SENSITIVITY https github com aloistr swisseph " +
  "sepl se semo sabpuja calculation metadata km English Code PDF HH MM SS YYYY DD www geonames org Mumbai").split(" "));
const results = [];
function check(view, name, ok, detail) {
  results.push({ view, name, ok: !!ok });
  console.log(`${ok ? "PASS" : "FAIL"} [${view}] ${name}${ok ? "" : " :: " + JSON.stringify(detail).slice(0, 1500)}`);
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
function pdfText(file) {
  const code = "import sys,fitz,json;d=fitz.open(sys.argv[1]);print(json.dumps({'pages':len(d),'lang':d.pdf_catalog() and d.xref_get_key(d.pdf_catalog(),'Lang')[1],'text':[p.get_text() for p in d]}))";
  return JSON.parse(execFileSync(PYTHON, ["-c", code, file], { encoding: "utf8" }));
}
const squash = (s) => s.replace(/\s+/g, " ").trim();

async function fillBirth(page) {
  await page.selectOption("#place", "in-new-delhi");
  await page.fill("#birth-date", "1990-05-15");
  await page.fill("#birth-time", "10:30");
}
async function calculate(page) {
  await Promise.all([
    page.waitForResponse((r) => r.url().endsWith("/api/chart") && r.request().method() === "POST"),
    page.click("#submit")
  ]);
  await page.waitForSelector("#result:not([hidden])");
}
async function downloadPdf(page, file) {
  const [req, download] = await Promise.all([
    page.waitForRequest((r) => r.url().endsWith("/api/report")),
    page.waitForEvent("download"),
    page.click("#download-pdf")
  ]);
  await download.saveAs(file);
  return { body: JSON.parse(req.postData()), name: download.suggestedFilename(), bytes: fs.readFileSync(file) };
}
// Every value the engine produced, as shown: must be identical in both languages.
function values(page) {
  return page.evaluate(() => ({
    rows: [...document.querySelectorAll("#d1-table tbody tr, #d9-table tbody tr")].map((tr) =>
      [tr.dataset.graha, ...[...tr.querySelectorAll("[data-field=longitude], [data-field=house], [data-field=d9_house]")].map((c) => c.textContent)].join("|")),
    facts: ["local_date", "local_time", "utc_offset", "utc", "schema_version", "metadata_schema"].map((f) => {
      const d = document.querySelector(`dd[data-field=${f}]`); return d ? d.textContent.replace(/ \(.*\)$/, "") : null; }),
    houses: [...document.querySelectorAll("#d1-chart g.house, #d9-chart g.house")].map((g) =>
      g.dataset.house + ":" + g.dataset.sign + ":" + [...g.querySelectorAll("text[data-graha]")].map((t) => t.dataset.graha).join(","))
  }));
}
function form(page) {
  return page.evaluate(() => ({ name: document.getElementById("full-name").value, place: document.getElementById("place").value,
    date: document.getElementById("birth-date").value, time: document.getElementById("birth-time").value }));
}
async function switchTo(page, loc) {
  await page.click(`#lang-${loc}`);
  await page.waitForFunction((l) => document.documentElement.lang === l, loc);
}
// Visible Latin words on a Hindi page that are not proper names, codes or engine data.
function strayLatin(page, allowed) {
  return page.evaluate((allow) => {
    const set = new Set(allow), stray = {};
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const el = n.parentElement;
      if (!el || el.closest("script, style, code, [lang=en], #full-name, .name-text, title, desc")) { continue; }
      if (el.closest("[hidden]") || getComputedStyle(el).display === "none") { continue; }
      // Tokens with a digit are values or identifiers (hashes, UT1, sepl_18.se1, 2.10.03), not words.
      n.textContent.split(/\s+/).filter((tok) => !/[0-9]/.test(tok)).forEach((tok) =>
        (tok.match(/[A-Za-z]{2,}/g) || []).forEach((w) => { if (!set.has(w)) { stray[w] = (stray[w] || 0) + 1; } }));
    }
    return stray;
  }, [...allowed]);
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
  page.on("console", (m) => { if (m.type() === "error" && !/status of 4\d\d/.test(m.text())) { errors.push(m.text()); } });
  page.on("pageerror", (e) => errors.push(String(e)));
  await page.goto(base + "/");
  await page.waitForSelector("#place optgroup", { state: "attached" });

  // 1. Default English; accessible language switch.
  let ui = await page.evaluate(() => {
    const g = document.getElementById("lang-switch");
    return { lang: document.documentElement.lang, role: g.getAttribute("role"), label: g.getAttribute("aria-label"),
             en: document.getElementById("lang-en").getAttribute("aria-pressed"), hi: document.getElementById("lang-hi").getAttribute("aria-pressed"),
             hiLang: document.getElementById("lang-hi").lang, hiDisabled: document.getElementById("lang-hi").disabled,
             heading: document.getElementById("form-heading").textContent,
             targets: [...document.querySelectorAll(".lang-option")].map((b) => { const r = b.getBoundingClientRect(); return [r.width, r.height]; }) };
  });
  check(view, "English is the default; a labelled two-button language group with aria-pressed",
        ui.lang === "en" && ui.role === "group" && ui.label === "Language / भाषा" && ui.en === "true" && ui.hi === "false" &&
        ui.hiLang === "hi" && !ui.hiDisabled && ui.heading === "Birth details", ui);
  check(view, "language buttons are at least 44 px touch targets", ui.targets.every(([w, h]) => w >= 44 && h >= 44), ui.targets);

  // Static English text equals the catalog English (the catalog is the source of the page).
  const mismatch = await page.evaluate((ui) => [...document.querySelectorAll("[data-i18n]")]
    .filter((el) => el.textContent !== ui[el.dataset.i18n].en).map((el) => el.dataset.i18n), UI);
  check(view, "every data-i18n element shows its catalog English", mismatch.length === 0, mismatch);

  // 2. Keyboard: the switch is reachable by Tab, operable with Enter and Space.
  await page.keyboard.press("Tab");
  const tabs = [];
  for (let i = 0; i < 3; i++) { await page.keyboard.press("Tab"); tabs.push(await page.evaluate(() => document.activeElement.id)); }
  check(view, "Tab reaches English then Hindi then the site link", JSON.stringify(tabs) === JSON.stringify(["lang-en", "lang-hi", "header-site-link"]), tabs);
  await page.focus("#lang-hi");
  await page.keyboard.press("Enter");
  await page.waitForFunction(() => document.documentElement.lang === "hi");
  ui = await page.evaluate(() => ({ focus: document.activeElement.id, pressed: document.getElementById("lang-hi").getAttribute("aria-pressed"),
    announce: document.getElementById("lang-announce").textContent, title: document.title }));
  check(view, "Enter switches to Hindi, keeps focus on the switch and announces the language",
        ui.focus === "lang-hi" && ui.pressed === "true" && ui.announce === UI["lang.announce"].hi && ui.title === UI["meta.title"].hi, ui);
  await page.focus("#lang-en");
  await page.keyboard.press("Space");
  await page.waitForFunction(() => document.documentElement.lang === "en");
  check(view, "Space switches back to English", (await page.textContent("#form-heading")) === "Birth details", "");

  // 3. Switch before calculation: form values kept, Hindi labels, Hindi validation messages.
  await page.fill("#full-name", HINDI_NAME);
  await fillBirth(page);
  const before = await form(page);
  await switchTo(page, "hi");
  ui = await page.evaluate(() => ({ heading: document.getElementById("form-heading").textContent,
    label: document.querySelector("label[for='place']").textContent, option: document.getElementById("place").selectedOptions[0].textContent,
    submit: document.getElementById("submit").textContent }));
  check(view, "Hindi labels, place list and buttons after switching before calculation",
        ui.heading === UI["form.heading"].hi && ui.label === UI["place.label"].hi && ui.option.startsWith("नई दिल्ली") && ui.submit === UI["submit"].hi, ui);
  check(view, "birth details and name preserved through the switch", JSON.stringify(await form(page)) === JSON.stringify(before), await form(page));
  check(view, "a language switch sends no request", chartBodies.length === 0 && reportBodies.length === 0, chartBodies);
  // Hindi validation and recovery messages.
  await page.fill("#birth-time", "");
  await page.click("#submit");
  ui = await page.evaluate(() => ({ err: document.getElementById("time-error").textContent, invalid: document.getElementById("birth-time").getAttribute("aria-invalid") }));
  check(view, "client validation message in Hindi", ui.err === UI["val.time_missing"].hi && ui.invalid === "true", ui);
  await switchTo(page, "en");
  check(view, "a shown field error follows the language", (await page.textContent("#time-error")) === UI["val.time_missing"].en, "");
  await switchTo(page, "hi");
  await page.fill("#birth-date", "1960-01-01");
  await page.fill("#birth-time", "10:30");
  await page.click("#submit");
  await page.waitForSelector("#error-card:not([hidden])");
  ui = await page.evaluate(() => ({ msg: document.getElementById("error-message").textContent, code: document.getElementById("error-code").textContent,
                                     title: document.getElementById("error-title").textContent }));
  check(view, "server refusal shown in Hindi with its code", ui.msg === UI["msg.HISTORICAL_CLOCK_UNVERIFIED"].hi &&
        ui.code === "HISTORICAL_CLOCK_UNVERIFIED" && ui.title === UI["error.title"].hi, ui);
  await switchTo(page, "en");
  check(view, "the error card follows the language", (await page.textContent("#error-message")) === UI["msg.HISTORICAL_CLOCK_UNVERIFIED"].en, "");
  await page.fill("#birth-date", "1990-05-15");
  await switchTo(page, "hi");

  // 4. Calculate in Hindi.
  await calculate(page);
  const hiVals = await values(page);
  ui = await page.evaluate(() => ({
    forText: document.getElementById("result-for").textContent, name: document.getElementById("result-name").textContent,
    dt: [...document.querySelectorAll("#confirm-list dt")].map((d) => d.textContent),
    lagna: document.querySelector("dd[data-field=lagna_rashi]").textContent,
    d1title: document.querySelector("#d1-chart title").textContent, d1desc: document.querySelector("#d1-chart desc").textContent,
    lagnaLabel: document.querySelector("#d1-chart text[data-graha=lagna]").textContent,
    th: [...document.querySelectorAll("#d1-table th[scope=col]")].map((t) => t.textContent),
    claim: document.getElementById("claim").textContent,
    overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth }));
  check(view, "Hindi result: name line, confirmed details, chart labels and table headings",
        ui.forText === HINDI_NAME + UI["result.for_after"].hi && ui.name === HINDI_NAME && ui.dt[0] === UI["fact.name"].hi &&
        /^[ऀ-ॿ]/.test(ui.lagna) && ui.d1title.startsWith(UI["svg.d1_title"].hi) && ui.d1desc.startsWith("भाव 1") &&
        ui.lagnaLabel === "लग्न" && ui.th.join("|") === ["th.graha", "th.longitude", "th.rashi", "th.house"].map((k) => UI[k].hi).join("|") &&
        ui.claim.includes("UNVERIFIED_GOLDEN_CHARTS"), ui);
  check(view, "no horizontal scrolling in Hindi with a result", ui.overflow <= 0, ui.overflow);
  const stray = await strayLatin(page, LATIN_ALLOWED);
  check(view, "no English-only fragments on the Hindi page (only proper names, codes and data stay Latin)", Object.keys(stray).length === 0, stray);
  const devaFont = await page.evaluate(async () => {
    await document.fonts.ready;
    return [...document.fonts].filter((f) => f.family.replace(/"/g, "") === "Poppins" && /U\+0?900-97F/i.test(f.unicodeRange) && f.status === "loaded").map((f) => f.weight);
  });
  check(view, "Hindi text uses the bundled Poppins Devanagari faces (400 for body text)", devaFont.includes("400") && devaFont.length >= 2, devaFont);
  await page.screenshot({ path: path.join(OUT, `i18n-hi-${width}.png`), fullPage: true });

  // 5. Switch after calculation: same values, no request, result redrawn in English.
  const requestsBefore = chartBodies.length;
  await switchTo(page, "en");
  const enVals = await values(page);
  ui = await page.evaluate(() => ({ hidden: document.getElementById("result").hidden, dt: document.querySelector("#confirm-list dt").textContent,
    forText: document.getElementById("result-for").textContent, lagna: document.querySelector("dd[data-field=lagna_rashi]").textContent,
    download: document.getElementById("download-pdf").disabled }));
  check(view, "switching after calculation keeps the result and redraws it in English",
        !ui.hidden && ui.dt === "Name on report" && ui.forText === "Prepared for " + HINDI_NAME && /\(/.test(ui.lagna) && !ui.download, ui);
  check(view, "every longitude, house, D9 house, chart placement and time value identical in both languages",
        JSON.stringify(enVals) === JSON.stringify(hiVals) && enVals.rows.length === 20 && enVals.houses.length === 24, { enVals, hiVals });
  check(view, "no recalculation on a language change", chartBodies.length === requestsBefore, chartBodies.length);
  check(view, "form values unchanged after both switches", JSON.stringify(await form(page)) === JSON.stringify({ ...before }), await form(page));
  await page.screenshot({ path: path.join(OUT, `i18n-en-${width}.png`), fullPage: true });

  // 6. PDF language follows the page language.
  let pdf = await downloadPdf(page, path.join(OUT, `en-${width}.pdf`));
  let text = pdfText(path.join(OUT, `en-${width}.pdf`));
  check(view, "English PDF: no report_locale sent, English text, ten pages, generic filename",
        !("report_locale" in pdf.body) && pdf.name === "Sabpuja-Janma-Kundali.pdf" && text.pages === 10 &&
        squash(text.text[0]).includes("Janma Kundali") && !/[ऀ-ॿ]{3}/.test(squash(text.text[2])), pdf.body);
  await switchTo(page, "hi");
  pdf = await downloadPdf(page, path.join(OUT, `hi-${width}.pdf`));
  text = pdfText(path.join(OUT, `hi-${width}.pdf`));
  check(view, "Hindi PDF: report_locale hi with the name, Hindi text, ten pages, document language hi",
        pdf.body.report_locale === "hi" && pdf.body.display_name === HINDI_NAME && pdf.name === "Sabpuja-Janma-Kundali.pdf" &&
        text.pages === 10 && squash(text.text[0]).includes("जन्म कुंडली") && squash(text.text[0]).includes(HINDI_NAME) &&
        squash(text.text[9]).includes("गणना पद्धति और स्रोत") && /hi/.test(String(text.lang)), { body: pdf.body, lang: text.lang });
  const chartKeys = JSON.parse(chartBodies[chartBodies.length - 1]);
  check(view, "chart request never carries the report language or the name",
        !("report_locale" in chartKeys) && !("display_name" in chartKeys), chartKeys);

  // 7. Stale download: a language change while the PDF is being prepared aborts it.
  await page.route("**/api/report", async (route) => { await new Promise((r) => setTimeout(r, 1500)); await route.continue().catch(() => {}); });
  let downloads = 0;
  const onDownload = () => { downloads += 1; };
  page.on("download", onDownload);
  await page.click("#download-pdf");
  await page.waitForTimeout(250);
  await switchTo(page, "en");
  await page.waitForTimeout(2200);
  ui = await page.evaluate(() => ({ status: document.getElementById("status").textContent, disabled: document.getElementById("download-pdf").disabled,
    label: document.getElementById("download-pdf").textContent, hidden: document.getElementById("result").hidden }));
  check(view, "language change during a PDF request: no stale download, explained, download re-enabled",
        downloads === 0 && ui.status === UI["status.pdf_language_changed"].en && !ui.disabled && ui.label === "Download Kundali PDF" && !ui.hidden, ui);
  page.off("download", onDownload);
  await page.unroute("**/api/report");
  pdf = await downloadPdf(page, path.join(OUT, `after-switch-${width}.pdf`));
  text = pdfText(path.join(OUT, `after-switch-${width}.pdf`));
  check(view, "the next download is in the new language", !("report_locale" in pdf.body) && squash(text.text[0]).includes("Janma Kundali"), pdf.body);

  // 8. Latin name in Hindi mode.
  await switchTo(page, "hi");
  await page.fill("#full-name", LATIN_NAME);
  await calculate(page);
  ui = await page.evaluate(() => ({ name: document.getElementById("result-name").textContent, overflow: document.documentElement.scrollWidth - document.documentElement.clientWidth }));
  check(view, "Latin name in the Hindi interface", ui.name === LATIN_NAME && ui.overflow <= 0, ui);
  pdf = await downloadPdf(page, path.join(OUT, `hi-latin-${width}.pdf`));
  text = pdfText(path.join(OUT, `hi-latin-${width}.pdf`));
  check(view, "Hindi PDF with a Latin name", pdf.body.report_locale === "hi" && squash(text.text[0]).includes(LATIN_NAME) &&
        squash(text.text[3]).includes(LATIN_NAME), pdf.body);

  // 9. Anonymous Hindi PDF.
  await page.fill("#full-name", "");
  await calculate(page);
  pdf = await downloadPdf(page, path.join(OUT, `hi-anon-${width}.pdf`));
  text = pdfText(path.join(OUT, `hi-anon-${width}.pdf`));
  check(view, "anonymous Hindi PDF", pdf.body.report_locale === "hi" && !("display_name" in pdf.body) && text.pages === 10 &&
        !squash(text.text[0]).includes("जातक"), pdf.body);

  // 10. Narrow screens: no horizontal scroll on the Hindi form, with the error card and the result.
  for (const state of ["form", "result"]) {
    if (state === "form") { await page.click("#clear"); }
    const ov = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    check(view, `no horizontal scroll in Hindi (${state})`, ov <= 0, ov);
  }
  await page.screenshot({ path: path.join(OUT, `i18n-hi-form-${width}.png`), fullPage: true });

  // 11. Privacy.
  const storage = await page.evaluate(() => ({ local: localStorage.length, session: sessionStorage.length, cookie: document.cookie, url: location.href }));
  const cookies = await context.cookies();
  const leaked = urls.filter((u) => /Zo%C3%AB|Qwerty|%E0%A4|display_name|report_locale|1990|lang=|locale|[?#]/i.test(u.replace(base, "")));
  check(view, "no storage, cookies or URL carrying the language, a name or birth details",
        storage.local === 0 && storage.session === 0 && storage.cookie === "" && cookies.length === 0 && storage.url === base + "/" &&
        leaked.length === 0, { storage, cookies, leaked });
  check(view, "only same-origin requests", urls.every((u) => u.startsWith(base) || u.startsWith("blob:")), urls.filter((u) => !u.startsWith(base)));
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
  check("server", "server output contains no synthetic name, birth detail or language choice",
        !["Qwertyuiop", "क्षत्रिय", "1990-05-15", "in-new-delhi", "report_locale"].some((s) => log.includes(s)), log);
  const failed = results.filter((r) => !r.ok).length;
  console.log(`I18N_E2E ${failed ? "FAIL" : "PASS"} ${results.length - failed}/${results.length}`);
  process.exit(failed ? 1 : 0);
})().catch((e) => { console.error(e); process.exit(2); });
