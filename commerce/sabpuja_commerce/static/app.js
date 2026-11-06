"use strict";
// Claim -> code -> birth details -> in-memory PDF download. Nothing is put in the URL, local
// storage or cookies by this script; the session cookie is HttpOnly and set by the server.
(function () {
  const $ = (id) => document.getElementById(id);
  const status = $("status");
  let claim = null;      // order number + e-mail, kept in memory only until the code is verified
  let busy = false;

  function say(text, isError) {
    status.textContent = text || "";
    status.className = isError ? "error" : "";
  }
  async function post(path, body) {
    return fetch(path, { method: "POST", credentials: "same-origin", headers: { "Content-Type": "application/json" },
                         body: JSON.stringify(body) });
  }
  async function errorText(resp) {
    try { const j = await resp.json(); return (j.error && j.error.message) || "Something went wrong."; }
    catch (e) { return "Something went wrong."; }
  }
  function show(step) {
    for (const id of ["step-claim", "step-code", "step-birth"]) $(id).hidden = id !== step;
  }
  function remaining(n) {
    $("remaining").textContent = n === 1 ? "1 report generation left on this order." : n + " report generations left on this order.";
  }

  $("claim-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    claim = { order_number: $("order_number").value.trim(), email: $("email").value.trim() };
    const resp = await post("/api/claim/start", claim);
    if (resp.status === 202) { say((await resp.json()).message); show("step-code"); $("code").focus(); }
    else say(await errorText(resp), true);
  });

  $("code-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const resp = await post("/api/claim/verify", Object.assign({ code: $("code").value.trim() }, claim));
    if (resp.ok) {
      const j = await resp.json();
      claim = null; $("code").value = "";
      remaining(j.remaining); say(""); show("step-birth"); loadPlaces();
    } else say(await errorText(resp), true);
  });

  async function loadPlaces() {
    const sel = $("place_id");
    if (sel.options.length) return;
    const resp = await fetch("/api/places", { credentials: "same-origin" });
    const j = await resp.json();
    for (const p of j.places) {
      const o = document.createElement("option");
      o.value = p.id; o.textContent = p.name ? p.name + (p.region ? ", " + p.region : "") : p.id;
      sel.appendChild(o);
    }
  }

  function birthBody() {
    const body = { place_id: $("place_id").value, birth_date: $("birth_date").value, birth_time: $("birth_time").value };
    const chosen = document.querySelector("input[name=utc_offset]:checked");
    if (chosen) body.utc_offset = chosen.value;
    const name = $("display_name").value.trim();
    if (name) body.display_name = name;
    return body;
  }

  for (const id of ["place_id", "birth_date", "birth_time"]) {
    $(id).addEventListener("change", () => { $("occurrence").hidden = true; $("occurrence-choices").textContent = ""; });
  }

  $("birth-form").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    if (busy) return;
    if (!$("consent").checked) { say("Please confirm how your details are used.", true); $("consent").focus(); return; }
    busy = true; $("generate").disabled = true; say("Preparing your report. This takes a few seconds.");
    try {
      const resp = await post("/api/generate", birthBody());
      if (resp.ok) {
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url; a.download = "Sabpuja-Janam-Kundali.pdf"; document.body.appendChild(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 30000);
        say("Your PDF has been downloaded. Keep it safe: we do not keep a copy.");
        const s = await fetch("/api/session", { credentials: "same-origin" });
        if (s.ok) remaining((await s.json()).remaining);
      } else if (resp.status === 409) {
        const j = await resp.json();
        if (j.error && j.error.choices) {
          const box = $("occurrence-choices"); box.textContent = "";
          for (const c of j.error.choices) {
            const l = document.createElement("label"); l.className = "check";
            const r = document.createElement("input"); r.type = "radio"; r.name = "utc_offset"; r.value = c.utc_offset;
            l.appendChild(r); l.appendChild(document.createTextNode(" " + c.label)); box.appendChild(l);
          }
          $("occurrence").hidden = false;
        }
        say(j.error ? j.error.message : "Please check the details.", true);
      } else if (resp.status === 401) {
        say("Your session ended. Please verify your order again.", true); show("step-claim");
      } else say(await errorText(resp), true);
    } finally { busy = false; $("generate").disabled = false; }
  });

  $("logout").addEventListener("click", async () => {
    await post("/api/logout", {});
    $("birth-form").reset(); say("Signed out."); show("step-claim");
  });
})();
