"use strict";
// Claim -> code -> birth details -> in-memory PDF download (KUN-COM-UX-CLAIM-001).
// Nothing is written to the URL, local storage, session storage or script-readable cookies. The session cookie is
// HttpOnly and set by the server. The order number and e-mail stay in memory only until the code is verified.
// A link from Shopify may carry "#order=<number>" (order status page, confirmation e-mail) or "#ref=<order id>"
// (Thank you page) in the fragment, which browsers never send to a server; it is removed from the address bar at once.
(function () {
  const $ = (id) => document.getElementById(id);
  const REQUEST_TIMEOUT_MS = 20000;
  const GENERATE_TIMEOUT_MS = 120000;

  let claim = null;          // {order_number|order_ref, email} until verified
  let orderRef = null;       // Shopify order id from the Thank you page link
  let resendTimer = null;
  let busy = false;
  let pdfUrl = null;
  let session = null;        // last /api/session answer

  // ---- messages ----------------------------------------------------------------------------------------------
  // Customer wording per server code. A code missing here falls back to the server's fixed message.
  const MESSAGES = {
    NETWORK: "We could not reach Sabpuja. Check your internet connection and try again.",
    TIMEOUT: "This is taking longer than expected. Check your connection and try again.",
    RATE_LIMITED: "Too many attempts in a short time. Please wait a minute and try again.",
    CLAIM_INVALID: "Enter your order number and the e-mail address you used at checkout.",
    CODE_INVALID: "That code did not work. Use the newest code we sent. Codes expire after 10 minutes and stop " +
      "working after 5 wrong tries; if so, send a new code.",
    ORDER_CHECK_UNAVAILABLE: "We cannot confirm your order with the store right now. Nothing was used. Please try " +
      "again in a few minutes.",
    ORDER_NOT_ACTIVE: "This order can no longer be used for a report, for example because it was refunded or " +
      "cancelled. Reply to your order confirmation e-mail if you think this is a mistake.",
    SESSION_REQUIRED: "For your security, verification lasts 30 minutes. Please verify your order again; the " +
      "details you typed on this page are kept.",
    GENERATIONS_USED: "All report generations for this order have been used.",
    ENTITLEMENT_EXPIRED: "The period for preparing reports on this order has ended.",
    GENERATION_IN_PROGRESS: "Your report is already being prepared. Please wait a moment, then try again.",
    REPORT_BUSY: "Many reports are being prepared right now. Nothing was used. Please try again in a few seconds.",
    REPORT_UNAVAILABLE: "The report cannot be prepared right now. Nothing was used. Please try again later.",
    PAID_EDITION_ENGLISH_ONLY: "This report is available in English only.",
    PLACE_UNKNOWN: "Choose your birthplace from the list.",
    BIRTH_TIME_REQUIRED: "Enter the exact birth time. We never assume a time.",
    BIRTH_TIME_INVALID: "Enter the birth time as hours, minutes and (optionally) seconds.",
    BIRTH_DATE_INVALID: "Enter a valid birth date.",
    DATE_INVALID: "This date does not exist in the calendar. Check the birth date.",
    DATE_OUTSIDE_SUPPORTED_RANGE: "Birth dates from 1 January 1970 to 31 December 2100 can be calculated.",
    HISTORICAL_CLOCK_UNVERIFIED: "Births before 1 January 1970 cannot be calculated yet, because local clock " +
      "records for that period are still being verified. Nothing was used. Reply to your order confirmation e-mail " +
      "and we will help.",
    TIME_NONEXISTENT_LOCAL: "This local time did not exist at this place (clocks moved forward that night). " +
      "Check the time on the birth record.",
  };
  const FIELD_OF = {
    PLACE_UNKNOWN: "place_id", BIRTH_TIME_REQUIRED: "birth_time", BIRTH_TIME_INVALID: "birth_time",
    TIME_NONEXISTENT_LOCAL: "birth_time", BIRTH_DATE_INVALID: "birth_date", DATE_INVALID: "birth_date",
    DATE_OUTSIDE_SUPPORTED_RANGE: "birth_date", HISTORICAL_CLOCK_UNVERIFIED: "birth_date",
  };

  function say(text) { $("status").textContent = text || ""; }
  function alertMsg(text) {
    $("alert-text").textContent = text || "";
    $("alert").hidden = !text;
  }
  function clearMessages() { say(""); alertMsg(""); }

  function fieldError(id, text) {
    const input = $(id), err = $(id + "-error");
    if (err) { err.textContent = text || ""; err.hidden = !text; }
    if (input) {
      if (text) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid");
    }
  }
  function clearFieldErrors(form) {
    for (const el of form.querySelectorAll("[aria-invalid]")) el.removeAttribute("aria-invalid");
    for (const el of form.querySelectorAll(".field-error")) { el.textContent = ""; el.hidden = true; }
  }

  // ---- requests ----------------------------------------------------------------------------------------------
  async function call(path, body, timeoutMs) {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs || REQUEST_TIMEOUT_MS);
    const init = { credentials: "same-origin", signal: ctrl.signal, cache: "no-store" };
    if (body !== undefined) {
      init.method = "POST";
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(body);
    }
    try {
      const resp = await fetch(path, init);
      const type = resp.headers.get("Content-Type") || "";
      if (type.startsWith("application/pdf")) return { ok: resp.ok, status: resp.status, blob: await resp.blob() };
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
    return { code: code, message: MESSAGES[code] || e.message || "Something went wrong. Please try again.", raw: e };
  }

  // ---- steps -------------------------------------------------------------------------------------------------
  const STEPS = ["step-claim", "step-code", "step-birth", "step-done"];
  function show(step, focusHeading) {
    for (const id of STEPS) $(id).hidden = id !== step;
    const nav = { "step-claim": 0, "step-code": 1, "step-birth": 2, "step-done": 2 }[step];
    ["nav-claim", "nav-code", "nav-birth"].forEach((id, i) => {
      const li = $(id);
      if (i === nav) li.setAttribute("aria-current", "step"); else li.removeAttribute("aria-current");
      li.classList.toggle("done", i < nav || step === "step-done");
    });
    $("logout").hidden = !(step === "step-birth" || step === "step-done");
    if (focusHeading !== false) {
      const h = $(step).querySelector("h2");
      if (h) h.focus();
    }
  }
  function setBusy(button, on, label) {
    if (on) { button.dataset.label = button.textContent; button.textContent = label; }
    else if (button.dataset.label) { button.textContent = button.dataset.label; }
    button.disabled = on;
    button.setAttribute("aria-busy", on ? "true" : "false");
  }

  // ---- step 1: order and e-mail ------------------------------------------------------------------------------
  function readFragment() {
    const m = /^#(order|ref)=(?:%23)?([0-9]{1,20})$/.exec(location.hash || "");
    if (location.hash && history.replaceState) history.replaceState(null, "", location.pathname + location.search);
    if (!m) return;
    const value = m[2];
    if (m[1] === "order" && value.length <= 12) $("order_number").value = "#" + value;
    if (m[1] === "ref") { orderRef = value; showRef(true); }
  }
  function showRef(on) {
    $("ref-box").hidden = !on;
    $("order-field").hidden = on;
    if (!on) orderRef = null;
  }
  $("ref-clear").addEventListener("click", () => { showRef(false); $("order_number").focus(); });

  function validateClaim() {
    clearFieldErrors($("claim-form"));
    let first = null;
    const number = $("order_number").value.trim();
    const email = $("email").value.trim();
    if (!orderRef && !/^#?\s*[0-9]{1,12}$/.test(number)) {
      fieldError("order_number", number ? "Enter the order number with digits only, for example #1001." :
        "Enter your order number.");
      first = first || "order_number";
    }
    if (!/^[^@\s]{1,64}@[^@\s]+\.[^@\s]+$/.test(email)) {
      fieldError("email", email ? "Check the e-mail address; it looks incomplete." : "Enter the e-mail address you used at checkout.");
      first = first || "email";
    }
    if (first) { $(first).focus(); return null; }
    return orderRef ? { order_ref: orderRef, email: email } : { order_number: number, email: email };
  }

  async function sendCode(isResend) {
    const button = isResend ? $("resend") : $("claim-submit");
    if (busy) return;
    busy = true; clearMessages();
    setBusy(button, true, "Sending…");
    try {
      const r = await call("/api/claim/start", claim);
      if (r.status === 202) {
        const j = r.json || {};
        $("code-ttl").textContent = String(j.code_ttl_minutes || 10);
        $("code-email").textContent = claim.email;
        startResendTimer(j.resend_after_seconds || 60);
        if (isResend) {
          say("If the details match a paid order, a new code is on its way. Use the newest code.");
          $("code").value = ""; $("code").focus();
        } else {
          show("step-code"); $("code").focus();
        }
      } else {
        alertMsg(errorOf(r).message);
      }
    } finally {
      setBusy(button, false); busy = false;
      if (isResend && resendTimer) $("resend").disabled = true;
    }
  }

  $("claim-form").addEventListener("submit", (ev) => {
    ev.preventDefault();
    const c = validateClaim();
    if (!c) return;
    claim = c;
    sendCode(false);
  });

  // ---- step 2: code ------------------------------------------------------------------------------------------
  function startResendTimer(seconds) {
    clearInterval(resendTimer);
    let left = seconds;
    const btn = $("resend"), wait = $("resend-wait");
    btn.disabled = true;
    const tick = () => {
      if (left <= 0) {
        clearInterval(resendTimer); resendTimer = null;
        btn.disabled = false; wait.textContent = "";
        return;
      }
      // Announce only on the first tick and at the end, so screen readers are not flooded.
      wait.setAttribute("aria-live", left === seconds ? "polite" : "off");
      wait.textContent = "You can ask for a new code in " + left + " seconds.";
      left -= 1;
    };
    tick();
    resendTimer = setInterval(tick, 1000);
  }
  $("resend").addEventListener("click", () => { if (claim) sendCode(true); });
  $("change-details").addEventListener("click", () => {
    clearInterval(resendTimer); resendTimer = null;
    clearMessages(); $("code").value = ""; show("step-claim");
  });
  $("code").addEventListener("input", () => {
    const digits = $("code").value.replace(/[^0-9]/g, "");
    if (digits !== $("code").value) $("code").value = digits.slice(0, 6);
  });

  $("code-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (busy || !claim) return;
    clearMessages(); clearFieldErrors($("code-form"));
    const code = $("code").value.replace(/\s+/g, "");
    if (!/^[0-9]{6}$/.test(code)) { fieldError("code", "Enter the 6 digits from the e-mail."); $("code").focus(); return; }
    busy = true; setBusy($("code-submit"), true, "Checking…");
    try {
      const r = await call("/api/claim/verify", Object.assign({ code: code }, claim));
      if (r.ok) {
        claim = null; $("code").value = ""; clearInterval(resendTimer); resendTimer = null;
        await enterBirthStep(false);
        return;
      }
      const e = errorOf(r);
      if (e.code === "CODE_INVALID") { fieldError("code", e.message); $("code").select(); }
      else alertMsg(e.message);
    } finally { setBusy($("code-submit"), false); busy = false; }
  });

  // ---- step 3: birth details ---------------------------------------------------------------------------------
  function formatDate(epochSeconds) {
    try {
      return new Date(epochSeconds * 1000).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" });
    } catch (e) { return new Date(epochSeconds * 1000).toDateString(); }
  }
  function allowanceText(s) {
    const order = s.order_number ? "Order #" + s.order_number + ". " : "";
    if (s.remaining <= 0) return [order + "All report generations for this order have been used."];
    if (s.used === 0) {
      const extra = s.remaining - 1;
      const lines = [order + "Your report is in English."];
      if (extra > 0) lines.push("After your first download you can prepare up to " + extra + " corrected version" +
        (extra === 1 ? "" : "s") + (s.window_days ? " within " + s.window_days + " days" : "") +
        ", for example if a birth detail was wrong.");
      return lines;
    }
    const until = s.window_ends_at ? " until " + formatDate(s.window_ends_at) : "";
    return [order + s.remaining + " corrected version" + (s.remaining === 1 ? "" : "s") + " left" + until + ".",
      "Preparing a new PDF uses one. Downloading the same PDF again does not."];
  }
  function renderAllowance(s) {
    for (const id of ["allowance", "done-allowance"]) {
      const box = $(id); box.textContent = "";
      for (const line of allowanceText(s)) { const p = document.createElement("p"); p.textContent = line; box.appendChild(p); }
    }
    const btn = $("generate");
    if (!busy) {
      btn.textContent = s.used === 0 ? "Prepare my PDF" : "Prepare corrected PDF (uses 1 of " + s.remaining + ")";
    }
    btn.disabled = s.remaining <= 0;
    $("correct").hidden = s.remaining <= 0;
  }
  // The server counts a generation once the PDF has been sent, which can land after this page reads the count.
  // Show the delivered PDF's count at once, then re-read until the server reports it (a few short retries).
  async function markDelivered() {
    if (!session) return;
    const delivered = session.used + 1;
    session = { ...session, used: delivered, remaining: Math.max(0, session.remaining - 1) };
    renderAllowance(session);
    for (let attempt = 0; attempt < 4; attempt++) {
      await new Promise((resolve) => setTimeout(resolve, attempt === 0 ? 0 : 700));
      const ok = await refreshSession();
      if (ok === false) return;
      if (session && session.used >= delivered) return;
    }
  }
  async function refreshSession() {
    const r = await call("/api/session");
    if (r.ok && r.json) { session = r.json; renderAllowance(session); return true; }
    return r.status === 401 ? false : null;
  }
  async function enterBirthStep(returning) {
    const ok = await refreshSession();
    if (!ok) {
      if (!returning) alertMsg(ok === false ? MESSAGES.SESSION_REQUIRED : MESSAGES.NETWORK);
      show("step-claim", !returning);
      return false;
    }
    show("step-birth", !returning);
    if (returning) say("Welcome back. Your order is still verified on this device.");
    loadPlaces();
    return true;
  }

  let placesLoaded = false;
  async function loadPlaces() {
    if (placesLoaded) return;
    const r = await call("/api/places");
    if (!r.ok || !r.json) { alertMsg("The birthplace list could not be loaded. " + MESSAGES.NETWORK); return; }
    const sel = $("place_id");
    for (const p of r.json.places) {
      const o = document.createElement("option");
      o.value = p.id; o.textContent = p.name ? p.name + (p.region ? ", " + p.region : "") : p.id;
      sel.appendChild(o);
    }
    placesLoaded = true;
  }

  // Read the entered date and time back in words, independent of the device's date format (05/17 vs 17/05).
  const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
    "November", "December"];
  function birthSummary() {
    const d = /^([0-9]{4})-([0-9]{2})-([0-9]{2})$/.exec($("birth_date").value);
    const t = /^([0-9]{2}):([0-9]{2})(?::([0-9]{2}))?$/.exec($("birth_time").value);
    const box = $("birth-summary");
    if (!d && !t) { box.hidden = true; box.textContent = ""; return; }
    const parts = [];
    if (d) parts.push(Number(d[3]) + " " + MONTHS[Number(d[2]) - 1] + " " + d[1]);
    if (t) {
      const hh = Number(t[1]), clock = t[1] + ":" + t[2] + (t[3] ? ":" + t[3] : "");
      const h12 = ((hh + 11) % 12) + 1;
      parts.push("at " + clock + " (" + h12 + ":" + t[2] + (t[3] ? ":" + t[3] : "") + " " + (hh < 12 ? "am" : "pm") + ")");
    }
    const sel = $("place_id");
    if (sel.value) parts.push("in " + sel.options[sel.selectedIndex].textContent);
    box.textContent = "Please check: born " + parts.join(" ") + ".";
    box.hidden = false;
  }
  for (const id of ["place_id", "birth_date", "birth_time"]) {
    $(id).addEventListener("input", birthSummary);
    $(id).addEventListener("change", birthSummary);
  }

  function resetOccurrence() { $("occurrence").hidden = true; $("occurrence-choices").textContent = ""; }
  for (const id of ["place_id", "birth_date", "birth_time"]) $(id).addEventListener("change", resetOccurrence);

  function validateBirth() {
    clearFieldErrors($("birth-form"));
    const checks = [
      ["place_id", $("place_id").value ? "" : "Choose your birthplace."],
      ["birth_date", $("birth_date").value ? ($("birth_date").validity.valid ? "" :
        "Enter a date between 1 January 1970 and 31 December 2100.") : "Enter the birth date."],
      ["birth_time", $("birth_time").value ? "" : "Enter the exact birth time. We never assume a time."],
      ["consent", $("consent").checked ? "" : "Please confirm how your details are used."],
    ];
    if (!$("occurrence").hidden && !document.querySelector("input[name=utc_offset]:checked"))
      checks.push(["occurrence-choices", "Choose which occurrence of this time is on the birth record."]);
    let first = null;
    for (const [id, msg] of checks) {
      if (!msg) continue;
      if (id === "occurrence-choices") { alertMsg(msg); first = first || document.querySelector("input[name=utc_offset]"); continue; }
      fieldError(id, msg);
      first = first || $(id);
    }
    if (first) { first.focus(); return false; }
    return true;
  }
  function birthBody() {
    const body = { place_id: $("place_id").value, birth_date: $("birth_date").value, birth_time: $("birth_time").value };
    const chosen = document.querySelector("input[name=utc_offset]:checked");
    if (chosen && !$("occurrence").hidden) body.utc_offset = chosen.value;
    const name = $("display_name").value.trim();
    if (name) body.display_name = name;
    return body;
  }
  function showOccurrence(choices) {
    const box = $("occurrence-choices"); box.textContent = "";
    for (const c of choices) {
      const l = document.createElement("label");
      const r = document.createElement("input"); r.type = "radio"; r.name = "utc_offset"; r.value = c.utc_offset;
      l.appendChild(r); l.appendChild(document.createTextNode(" " + c.label)); box.appendChild(l);
    }
    $("occurrence").hidden = false;
    box.querySelector("input").focus();
  }

  function setGenerating(on) {
    busy = on;
    $("progress").hidden = !on;
    $("birth-form").setAttribute("aria-busy", on ? "true" : "false");
    for (const el of $("birth-form").querySelectorAll("input, select, button")) el.disabled = on;
    $("logout").disabled = on;
    if (on) {
      $("generate").textContent = "Preparing…";
      say("Preparing your report. This usually takes under a minute. Please keep this page open.");
    } else if (session) {
      renderAllowance(session);
    }
  }
  function warnLeave(ev) { ev.preventDefault(); ev.returnValue = ""; }

  $("birth-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (busy) return;
    clearMessages();
    if (!validateBirth()) return;
    setGenerating(true);
    window.addEventListener("beforeunload", warnLeave);
    const slow = setTimeout(() => { $("progress-text").textContent = "Still working. Thank you for waiting; please keep this page open."; }, 20000);
    let r;
    try {
      r = await call("/api/generate", birthBody(), GENERATE_TIMEOUT_MS);
    } finally {
      clearTimeout(slow);
      $("progress-text").textContent = "Preparing your report. This usually takes under a minute. Please keep this page open.";
      window.removeEventListener("beforeunload", warnLeave);
      setGenerating(false);
    }
    if (r.ok && r.blob) {
      deliver(r.blob);
      markDelivered();
      return;
    }
    const e = errorOf(r);
    if (e.code === "TIME_AMBIGUOUS_LOCAL" && e.raw && e.raw.choices) {
      showOccurrence(e.raw.choices);
      alertMsg("This local time happened twice at this place. Choose the one on the birth record, then prepare again.");
    } else if (e.code === "SESSION_REQUIRED") {
      alertMsg(e.message); show("step-claim");
    } else if (r.network) {
      alertMsg(e.message + " A generation is used only when the PDF reaches your device; the count below is up to date.");
    } else {
      const field = FIELD_OF[e.code];
      if (field) { fieldError(field, e.message); $(field).focus(); }
      else alertMsg(e.message);
    }
    if (session) await refreshSession();
  });

  function deliver(blob) {
    if (pdfUrl) URL.revokeObjectURL(pdfUrl);
    pdfUrl = URL.createObjectURL(blob);
    const link = $("save-pdf");
    link.href = pdfUrl;
    show("step-done");
    say("Your PDF is ready. We do not keep a copy, so please save it.");
    // Start the download once; the visible button saves the same file again without a new generation.
    const a = document.createElement("a");
    a.href = pdfUrl; a.download = "Sabpuja-Janam-Kundali.pdf"; a.hidden = true;
    document.body.appendChild(a); a.click(); a.remove();
  }

  $("correct").addEventListener("click", () => { clearMessages(); show("step-birth"); $("place_id").focus(); });

  $("logout").addEventListener("click", async () => {
    await call("/api/logout", {});
    if (pdfUrl) { URL.revokeObjectURL(pdfUrl); pdfUrl = null; $("save-pdf").href = "#"; }
    $("birth-form").reset(); resetOccurrence(); birthSummary(); session = null;
    clearMessages(); say("Signed out. Your birth details were cleared from this page.");
    show("step-claim");
  });

  // ---- start -------------------------------------------------------------------------------------------------
  readFragment();
  enterBirthStep(true);
})();
