"use strict";
// Free Kundali preview -> paid report hand-off -> optional e-mail opt-in (KUN-FREEMIUM-PREVIEW-001).
// Nothing is written to the URL, cookies, local storage or session storage. The optional name never leaves this
// page: only birthplace id, date and time are sent, once, to /api/preview. The two funnel beacons carry only an
// event name. The checkout link carries no birth detail. All customer copy here is DRAFT pending editorial review.
(function () {
  const $ = (id) => document.getElementById(id);
  const REQUEST_TIMEOUT_MS = 20000;
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
    "October", "November", "December"];
  const LABELS = { lagna_rashi: "Lagna", moon_rashi: "Moon sign" };

  let config = null;
  let busy = false;

  const MESSAGES = {
    NETWORK: "We could not reach Sabpuja. Check your internet connection and try again.",
    TIMEOUT: "This is taking longer than expected. Check your connection and try again.",
    PREVIEW_RATE_LIMITED: "You have asked for many previews in a short time. Please wait a little and try again.",
    PREVIEW_BUSY: "The free preview is busy right now. Please try again in a minute.",
    PREVIEW_UNAVAILABLE: "The preview cannot be calculated right now. Please try again later.",
    REQUEST_INVALID: "Please check the birth details and try again.",
    BODY_TOO_LARGE: "Please check the birth details and try again.",
    PLACE_UNKNOWN: "Choose your birthplace from the list.",
    BIRTH_TIME_REQUIRED: "Enter the exact birth time. We never assume a time.",
    BIRTH_TIME_INVALID: "Enter the birth time as hours, minutes and (optionally) seconds.",
    BIRTH_DATE_INVALID: "Enter a valid birth date.",
    BIRTH_DATE_FUTURE: "The birth date cannot be in the future.",
    DATE_INVALID: "This date does not exist in the calendar. Check the birth date.",
    DATE_OUTSIDE_SUPPORTED_RANGE: "Birth dates from 1 January 1970 can be calculated.",
    HISTORICAL_CLOCK_UNVERIFIED: "Births before 1 January 1970 cannot be calculated yet, because local clock " +
      "records for that period are still being verified.",
    TIME_NONEXISTENT_LOCAL: "This local time did not exist at this place. Check the time on the birth record.",
    TIME_AMBIGUOUS_LOCAL: "This local time occurred twice at this place, so the preview cannot be calculated.",
    UTC_OFFSET_INVALID: "Please check the birth details and try again.",
    RATE_LIMITED: "Too many attempts in a short time. Please wait a minute and try again.",
    LEAD_INVALID: "Enter a valid e-mail address.",
    CONSENT_REQUIRED: "Tick the box if you would like offers by e-mail, or simply skip this step.",
    ADULT_REQUIRED: "E-mail sign-up is only for people aged 18 or older.",
    CONSENT_VERSION_CHANGED: "This sign-up text has changed. Please reload the page and try again.",
  };
  const FIELD_OF = {
    PLACE_UNKNOWN: "place_id", BIRTH_TIME_REQUIRED: "birth_time", BIRTH_TIME_INVALID: "birth_time",
    TIME_NONEXISTENT_LOCAL: "birth_time", TIME_AMBIGUOUS_LOCAL: "birth_time", BIRTH_DATE_INVALID: "birth_date",
    BIRTH_DATE_FUTURE: "birth_date", DATE_INVALID: "birth_date", DATE_OUTSIDE_SUPPORTED_RANGE: "birth_date",
    HISTORICAL_CLOCK_UNVERIFIED: "birth_date",
  };

  function say(text) { $("status").textContent = text || ""; }
  function alertMsg(text) { $("alert-text").textContent = text || ""; $("alert").hidden = !text; }
  function fieldError(id, text) {
    const input = $(id), err = $(id + "-error");
    if (err) { err.textContent = text || ""; err.hidden = !text; }
    if (input) { if (text) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid"); }
  }
  function clearFieldErrors(form) {
    for (const el of form.querySelectorAll("[aria-invalid]")) el.removeAttribute("aria-invalid");
    for (const el of form.querySelectorAll(".field-error")) { el.textContent = ""; el.hidden = true; }
  }

  async function call(path, body) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), REQUEST_TIMEOUT_MS);
    const init = { credentials: "same-origin", signal: ctrl.signal, cache: "no-store" };
    if (body !== undefined) {
      init.method = "POST";
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(body);
    }
    try {
      const resp = await fetch(path, init);
      let json = null;
      try { json = await resp.json(); } catch (e) { json = null; }
      return { ok: resp.ok, status: resp.status, json: json };
    } catch (e) {
      return { ok: false, status: 0, network: e && e.name === "AbortError" ? "TIMEOUT" : "NETWORK" };
    } finally {
      clearTimeout(timer);
    }
  }
  function errorOf(r) {
    if (r.network) return { code: r.network, message: MESSAGES[r.network] };
    const e = (r.json && r.json.error) || {};
    const code = e.code || "UNKNOWN";
    return { code: code, message: MESSAGES[code] || e.message || "Something went wrong. Please try again." };
  }
  function beacon(event) {
    // Aggregate counter only: the body is the event name, nothing else. Failure is ignored.
    try {
      fetch("/api/funnel", { method: "POST", credentials: "same-origin", keepalive: true, cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify({ event: event }) }).catch(() => {});
    } catch (e) { /* ignore */ }
  }

  // ---- set-up ------------------------------------------------------------------------------------------------
  async function loadConfig() {
    const r = await call("/api/preview/config");
    if (!r.ok || !r.json) { alertMsg(errorOf(r).message); $("preview-submit").disabled = true; return; }
    config = r.json;
    const sel = $("place_id");
    const names = [];
    for (const p of config.places) {
      const o = document.createElement("option");
      o.value = p.id;
      o.textContent = p.name + ", " + p.region;
      sel.appendChild(o);
      names.push(p.name);
    }
    if (names.length) {
      $("elig-cities").textContent = names.length > 1 ? names.slice(0, -1).join(", ") + " or " + names[names.length - 1]
        : names[0];
    }
    $("birth_date").min = config.date_min;
    $("birth_date").max = config.date_max;
    $("price-text").textContent = config.price_display || "to be confirmed";
    $("checkout").href = config.buy_url;
  }

  function birthSummary() {
    const d = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/.exec($("birth_date").value);
    const t = /^([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?$/.exec($("birth_time").value);
    const box = $("birth-summary");
    if (!d && !t) { box.hidden = true; box.textContent = ""; return ""; }
    const parts = [];
    if (d) parts.push(Number(d[3]) + " " + MONTHS[Number(d[2]) - 1] + " " + d[1]);
    if (t) {
      const hh = Number(t[1]), clock = t[1] + ":" + t[2] + (t[3] ? ":" + t[3] : "");
      const h12 = ((hh + 11) % 12) + 1;
      parts.push("at " + clock + " (" + h12 + ":" + t[2] + (t[3] ? ":" + t[3] : "") + " " + (hh < 12 ? "am" : "pm") + ")");
    }
    const sel = $("place_id");
    if (sel.value) parts.push("in " + sel.options[sel.selectedIndex].textContent);
    const text = "born " + parts.join(" ");
    box.textContent = "Please check: " + text + ".";
    box.hidden = false;
    return text;
  }

  function validate() {
    const form = $("preview-form");
    clearFieldErrors(form);
    let first = null;
    const fail = (id, msg) => { fieldError(id, msg); if (!first) first = id; };
    const name = $("display_name").value.trim();
    if (name.length > 60) fail("display_name", "Use at most 60 characters.");
    if (!$("place_id").value) fail("place_id", MESSAGES.PLACE_UNKNOWN);
    const date = $("birth_date").value;
    if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(date)) fail("birth_date", MESSAGES.BIRTH_DATE_INVALID);
    else if (date < config.date_min) fail("birth_date", MESSAGES.HISTORICAL_CLOCK_UNVERIFIED);
    else if (date > config.date_max) fail("birth_date", MESSAGES.BIRTH_DATE_FUTURE);
    const time = $("birth_time").value;
    if (!time) fail("birth_time", MESSAGES.BIRTH_TIME_REQUIRED);
    else if (!/^[0-9]{2}:[0-9]{2}(:[0-9]{2})?$/.test(time)) fail("birth_time", MESSAGES.BIRTH_TIME_INVALID);
    if (first) { $(first).focus(); return null; }
    return { place_id: $("place_id").value, birth_date: date, birth_time: time };
  }

  function showResult(res, readBack) {
    const name = $("display_name").value.trim();
    $("h-result").textContent = name ? name + ", here is your free Kundali preview" : "Your free Kundali preview";
    $("result-for").textContent = "For someone " + readBack + ".";
    for (const key of Object.keys(LABELS)) {
      const box = $("fact-" + key), f = res.fields[key];
      box.hidden = !f;
      if (!f) continue;
      box.querySelector('[data-part="rashi"]').textContent = f.rashi;
      box.querySelector('[data-part="meta"]').textContent = "Rashi " + f.number + " of 12 · " + f.western;
    }
    $("sensitive-note").hidden = !res.birth_time_sensitive;
    $("step-result").hidden = false;
    $("step-offer").hidden = false;
    $("step-leads").hidden = !config.lead_capture;
    $("handoff").hidden = true;
    $("h-result").focus();
  }

  async function submitPreview(ev) {
    ev.preventDefault();
    if (busy || !config) return;
    alertMsg("");
    const form = validate();
    if (!form) return;
    const readBack = birthSummary();
    busy = true;
    const btn = $("preview-submit");
    btn.disabled = true;
    say("Calculating your preview…");
    const r = await call("/api/preview", form);
    busy = false;
    btn.disabled = false;
    say("");
    if (r.ok && r.json && r.json.fields) { showResult(r.json, readBack); return; }
    const e = errorOf(r);
    const field = FIELD_OF[e.code];
    if (field) { fieldError(field, e.message); $(field).focus(); }
    else alertMsg(e.message);
  }

  function again() {
    $("step-result").hidden = true;
    $("step-offer").hidden = true;
    $("step-leads").hidden = true;
    $("preview-form").reset();
    birthSummary();
    $("h-form").focus();
  }

  // ---- paid hand-off -----------------------------------------------------------------------------------------
  function buy() {
    beacon("full_report_selected");
    $("handoff").hidden = false;
    $("h-handoff").focus();
  }
  function checkout() {
    beacon("checkout_started");   // the link itself navigates to the Shopify cart; no birth detail travels
  }

  // ---- optional e-mail opt-in --------------------------------------------------------------------------------
  async function submitLead(ev) {
    ev.preventDefault();
    const form = $("lead-form");
    clearFieldErrors(form);
    $("lead-status").textContent = "";
    const email = $("lead_email").value.trim();
    let first = null;
    if (!/^[^@\s]{1,64}@[^@\s]{1,255}$/.test(email)) { fieldError("lead_email", MESSAGES.LEAD_INVALID); first = first || "lead_email"; }
    if (!$("lead_consent").checked) { fieldError("lead_consent", MESSAGES.CONSENT_REQUIRED); first = first || "lead_consent"; }
    if (!$("lead_adult").checked) { fieldError("lead_adult", MESSAGES.ADULT_REQUIRED); first = first || "lead_adult"; }
    if (first) { $(first).focus(); return; }
    const btn = $("lead-submit");
    btn.disabled = true;
    const r = await call("/api/leads/subscribe", { email: email, marketing_consent: true, adult: true,
      consent_version: config.consent_version, locale: "en" });
    btn.disabled = false;
    if (r.ok) {
      $("lead-status").textContent = "Thank you. If this address can be added, we have sent a confirmation link to " +
        email + ". Nothing else is sent until you confirm.";
      form.reset();
      return;
    }
    const e = errorOf(r);
    const field = { LEAD_INVALID: "lead_email", CONSENT_REQUIRED: "lead_consent", ADULT_REQUIRED: "lead_adult" }[e.code];
    if (field) { fieldError(field, e.message); $(field).focus(); } else $("lead-status").textContent = e.message;
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("preview-form").addEventListener("submit", submitPreview);
    for (const id of ["birth_date", "birth_time", "place_id"]) $(id).addEventListener("change", birthSummary);
    $("again").addEventListener("click", again);
    $("buy").addEventListener("click", buy);
    $("checkout").addEventListener("click", checkout);
    $("handoff-back").addEventListener("click", () => { $("handoff").hidden = true; $("buy").focus(); });
    $("lead-form").addEventListener("submit", submitLead);
    loadConfig();
  });
})();
