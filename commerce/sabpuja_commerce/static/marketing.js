"use strict";
// E-mail preference management (KUN-FREEMIUM-PREVIEW-001). The token arrives in the URL fragment (never sent to a
// server by the browser), is removed from the address bar at once and kept in memory only.
(function () {
  const $ = (id) => document.getElementById(id);
  let token = null;
  const STATE = {
    pending: "Your sign-up is waiting for confirmation. Nothing is sent until you confirm.",
    subscribed: "You are signed up for occasional offers and news from Sabpuja by e-mail.",
    withdrawn: "You have stopped offers by e-mail. We will not send you offers.",
    deleted: "Your sign-up has been deleted. We no longer hold your e-mail address for offers.",
  };
  function say(t) { $("status").textContent = t || ""; }
  function alertMsg(t) { $("alert-text").textContent = t || ""; $("alert").hidden = !t; }
  async function post(path, body) {
    try {
      const r = await fetch(path, { method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      let j = null; try { j = await r.json(); } catch (e) { j = null; }
      return { ok: r.ok, status: r.status, json: j };
    } catch (e) { return { ok: false, status: 0, json: null }; }
  }
  function render(state) {
    $("manage").hidden = false;
    $("manage-state").textContent = STATE[state] || "";
    $("confirm").hidden = state !== "pending";
    $("withdraw").hidden = state !== "subscribed" && state !== "pending";
    $("delete").hidden = state === "deleted";
    $("h-manage").focus();
  }
  async function act(action) {
    alertMsg("");
    const r = await post("/api/leads/" + action, { token: token });
    if (r.ok && r.json) { render(r.json.status); say(STATE[r.json.status] || ""); return; }
    alertMsg(r.status === 0 ? "We could not reach Sabpuja. Check your connection and try again." :
      "This link is not valid or has expired. Ask for a new one below.");
    $("manage").hidden = true;
  }
  document.addEventListener("DOMContentLoaded", () => {
    const m = /^#(confirm|manage)=([A-Za-z0-9_-]{30,64})$/.exec(location.hash || "");
    if (location.hash) history.replaceState(null, "", location.pathname);
    if (m) { token = m[2]; act(m[1] === "confirm" ? "confirm" : "status"); }
    $("confirm").addEventListener("click", () => act("confirm"));
    $("withdraw").addEventListener("click", () => act("withdraw"));
    $("delete").addEventListener("click", () => act("delete"));
    $("link-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const email = $("email").value.trim();
      $("email-error").hidden = true; $("email").removeAttribute("aria-invalid");
      if (!/^[^@\s]{1,64}@[^@\s]{1,255}$/.test(email)) {
        $("email-error").textContent = "Enter a valid e-mail address."; $("email-error").hidden = false;
        $("email").setAttribute("aria-invalid", "true"); $("email").focus(); return;
      }
      const r = await post("/api/leads/link", { email: email });
      say(r.ok ? "If this address is signed up, we have sent it a link." : "Please try again in a minute.");
    });
  });
})();
