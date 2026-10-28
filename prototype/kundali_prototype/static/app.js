/* Prototype page logic. Every number shown comes from the server's engine result;
 * this file only validates the form, sends it, and lays the result out. */
(function () {
  "use strict";
  var C = window.SabpujaChart;
  var $ = function (id) { return document.getElementById(id); };
  var form = $("birth-form"), placeSel = $("place"), dateIn = $("birth-date"), timeIn = $("birth-time");
  var unknown = $("time-unknown"), submitBtn = $("submit"), downloadBtn = $("download-pdf");
  var places = {};
  var pendingChoice = null; // set only while the server is asking which repeated hour

  var SHORT = { sun: "Sun", moon: "Moon", mars: "Mars", mercury: "Mercury", jupiter: "Jupiter", venus: "Venus",
                saturn: "Saturn", rahu_mean: "Rahu", ketu_mean: "Ketu" };
  var MESSAGES = {
    HISTORICAL_CLOCK_UNVERIFIED: "Births before 1970-01-01 are not supported yet: historical clock records for these dates have not been verified, so no chart is produced.",
    DATE_OUTSIDE_SUPPORTED_RANGE: "This date is outside the supported range. The prototype charts local dates up to 2100-12-31 (and from 1970-01-01, see above).",
    LATITUDE_OUTSIDE_SUPPORTED_BAND: "This birthplace is beyond 66° latitude, where the Lagna changes very quickly. Such charts are not supported, so none is produced.",
    TIME_NONEXISTENT_LOCAL: "This local time never happened at this place: clocks moved forward that night and skipped it. Please check the birth record.",
    TIME_AMBIGUOUS_LOCAL: "This local time happened twice at this place. Choose which occurrence is on the birth record.",
    BIRTH_TIME_REQUIRED: "An exact birth time is required. No time is assumed for you.",
    BIRTH_TIME_INVALID: "Enter the birth time as hours and minutes (seconds optional), in 24-hour local time.",
    BIRTH_DATE_INVALID: "This date does not exist. Please check the day and month.",
    PLACE_UNKNOWN: "Choose a birthplace from the list.",
    REQUEST_INVALID: "The form could not be sent correctly. Please reload the page and try again.",
    INTERNAL_ERROR: "Something unexpected went wrong. No chart was produced."
  };
  // Server-side faults (HTTP 503) by category; the code is still shown as sent.
  var SERVER_FAULTS = {
    resources: "The calculation engine is not available on this computer right now. No chart was produced.",
    computation: "The calculation engine could not compute this chart on this computer. No chart was produced."
  };

  function setFieldError(input, errId, text) {
    var el = $(errId);
    if (text) { el.textContent = text; el.hidden = false; input.setAttribute("aria-invalid", "true"); }
    else { el.textContent = ""; el.hidden = true; input.removeAttribute("aria-invalid"); }
  }

  function clearErrors() {
    setFieldError(placeSel, "place-error", "");
    setFieldError(dateIn, "date-error", "");
    setFieldError(timeIn, "time-error", "");
    $("error-card").hidden = true;
  }

  function showError(code, message) {
    var card = $("error-card");
    $("error-message").textContent = MESSAGES[code] || message || "No chart was produced.";
    $("error-code").textContent = code;
    card.hidden = false;
    card.focus();
  }

  function setStatus(text) { $("status").textContent = text; }

  function loadPlaces() {
    return fetch("/api/places", { headers: { "Accept": "application/json" } })
      .then(function (r) { if (!r.ok) { throw new Error("places"); } return r.json(); })
      .then(function (data) {
        placeSel.textContent = "";
        placeSel.appendChild(new Option("Choose a birthplace", ""));
        var india = document.createElement("optgroup"); india.label = "India";
        var other = document.createElement("optgroup"); other.label = "Test coverage (outside India)";
        data.places.forEach(function (p) {
          places[p.id] = p;
          var label = p.name + ", " + p.region + (p.country === "India" ? "" : ", " + p.country);
          (p.country === "India" ? india : other).appendChild(new Option(label, p.id));
        });
        placeSel.appendChild(india);
        placeSel.appendChild(other);
      })
      .catch(function () { placeSel.textContent = ""; placeSel.appendChild(new Option("Places unavailable", "")); });
  }

  function validate() {
    clearErrors();
    var ok = true;
    if (!placeSel.value) { setFieldError(placeSel, "place-error", "Choose a birthplace."); ok = false; }
    if (!dateIn.value) { setFieldError(dateIn, "date-error", "Enter the date of birth."); ok = false; }
    else if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(dateIn.value)) { setFieldError(dateIn, "date-error", "Use the format YYYY-MM-DD."); ok = false; }
    if (unknown.checked) { setFieldError(timeIn, "time-error", "An exact time is required; see the note below."); ok = false; }
    else if (!timeIn.value) { setFieldError(timeIn, "time-error", "Enter the exact time of birth."); ok = false; }
    else if (!/^[0-9]{2}:[0-9]{2}(:[0-9]{2})?$/.test(timeIn.value)) { setFieldError(timeIn, "time-error", "Use HH:MM or HH:MM:SS."); ok = false; }
    var first = form.querySelector("[aria-invalid='true']");
    if (first) { first.focus(); }
    return ok;
  }

  function payload() {
    var body = { place_id: placeSel.value, birth_date: dateIn.value, birth_time: timeIn.value };
    if (pendingChoice) {
      var picked = form.querySelector("input[name='occurrence']:checked");
      if (picked) { body.utc_offset = picked.value; }
    }
    return body;
  }

  function showAmbiguity(choices) {
    var box = $("ambiguity-choices");
    box.textContent = "";
    choices.forEach(function (c, i) {
      var label = document.createElement("label");
      var input = document.createElement("input");
      input.type = "radio"; input.name = "occurrence"; input.value = c.utc_offset; input.required = true;
      if (i === 0) { input.id = "occurrence-0"; }
      label.appendChild(input);
      label.appendChild(document.createTextNode(c.label));
      box.appendChild(label);
    });
    pendingChoice = choices;
    $("ambiguity").hidden = false;
    submitBtn.textContent = "Calculate with this occurrence";
    $("occurrence-0").focus();
  }

  function hideAmbiguity() {
    pendingChoice = null;
    $("ambiguity").hidden = true;
    $("ambiguity-choices").textContent = "";
    submitBtn.textContent = "Calculate Kundali";
  }

  function dl(list, rows) {
    list.textContent = "";
    rows.forEach(function (r) {
      var dt = document.createElement("dt"); dt.textContent = r[0];
      var dd = document.createElement("dd"); dd.textContent = r[1];
      if (r[2]) { dd.setAttribute("data-field", r[2]); }
      list.appendChild(dt); list.appendChild(dd);
    });
  }

  function signLabel(name) { return name + " (" + C.SIGN_ENGLISH[C.SIGNS.indexOf(name)] + ")"; }

  function row(tbody, cells, cls, key) {
    var tr = document.createElement("tr");
    if (cls) { tr.className = cls; }
    tr.setAttribute("data-graha", key);
    cells.forEach(function (c, i) {
      var cell = document.createElement(i === 0 ? "th" : "td");
      if (i === 0) { cell.scope = "row"; }
      if (c.sign) {
        cell.appendChild(document.createTextNode(c.sign + " "));
        var en = document.createElement("span");
        en.className = "en";
        en.textContent = "(" + C.SIGN_ENGLISH[C.SIGNS.indexOf(c.sign)] + ")";
        cell.appendChild(en);
      } else {
        cell.textContent = c.text;
      }
      if (c.field) { cell.setAttribute("data-field", c.field); }
      if (c.cls) { cell.className = c.cls; }
      tr.appendChild(cell);
    });
    tbody.appendChild(tr);
  }

  function render(data) {
    var chart = data.chart, input = data.input, meta = chart.calculation_metadata;
    // Both models are built before anything is drawn: either throws if the engine result is
    // inconsistent, and then no chart is shown (the result stays hidden).
    var model = C.buildD1Model(chart), d9Model = C.buildD9Model(chart);
    C.renderNorthIndian($("d1-chart"), model);
    C.renderNorthIndian($("d9-chart"), d9Model, { id: "d9", title: "North Indian D9 Navamsa chart, D9 Lagna " });

    var p = input.place;
    dl($("confirm-list"), [
      ["Birthplace", p.name + ", " + p.region + ", " + p.country],
      ["Coordinates", p.latitude.toFixed(5) + "°, " + p.longitude.toFixed(5) + "°"],
      ["Timezone", p.timezone],
      ["Local date", input.local_date, "local_date"],
      ["Local time", input.local_time, "local_time"],
      ["UTC offset", input.utc_offset + (input.offset_resolution === "user_selected_repeated_hour" ? " (your choice of repeated hour)" : ""), "utc_offset"],
      ["Universal time", chart.birth.utc, "utc"]
    ]);
    dl($("key-list"), [
      ["Lagna (D1)", signLabel(chart.lagna.rashi), "lagna_rashi"],
      ["Moon sign", signLabel(chart.planets.moon.rashi), "moon_rashi"],
      ["Moon Nakshatra", chart.moon_nakshatra.name + ", Pada " + chart.moon_nakshatra.pada, "moon_nakshatra"],
      ["D9 Lagna", signLabel(chart.lagna.navamsa_rashi), "d9_lagna"]
    ]);

    var d1 = $("d1-table").tBodies[0], d9 = $("d9-table").tBodies[0];
    d1.textContent = ""; d9.textContent = "";
    row(d1, [{ text: "Lagna" }, { text: chart.lagna.longitude_deg.toFixed(8) + "°", cls: "num", field: "longitude" },
             { sign: chart.lagna.rashi, field: "rashi" }, { text: "1", field: "house", cls: "num" }], "row--lagna", "lagna");
    row(d9, [{ text: "D9 Lagna" }, { sign: chart.lagna.navamsa_rashi, field: "navamsa" },
             { text: "1", field: "d9_house", cls: "num" }], "row--lagna", "lagna");
    C.GRAHAS.forEach(function (g) {
      var pl = chart.planets[g.key];
      row(d1, [{ text: SHORT[g.key] }, { text: pl.longitude_deg.toFixed(8) + "°", cls: "num", field: "longitude" },
               { sign: pl.rashi, field: "rashi" }, { text: String(pl.whole_sign_house), field: "house", cls: "num" }], "", g.key);
      row(d9, [{ text: SHORT[g.key] }, { sign: pl.navamsa_rashi, field: "navamsa" },
               { text: String(pl.navamsa_whole_sign_house), field: "d9_house", cls: "num" }], "", g.key);
    });

    var eph = meta.ephemeris_data, tz = meta.timezone_data, sw = meta.swiss_ephemeris;
    $("claim").textContent = "A computational chart generated under the conventions below with Swiss Ephemeris. " +
      "It is not independently astronomically certified. Engine status: " + meta.validation.status + " (" +
      meta.validation.claim_boundary + ").";
    var rows = [
      ["Zodiac and ayanamsa", "Sidereal, " + meta.conventions.ayanamsa.definition],
      ["Nodes", "Mean Rahu; Ketu exactly opposite"],
      ["Houses", "Whole-sign houses from the sidereal Lagna"],
      ["D9", "Navamsa signs from 3°20′ divisions of the sidereal longitude; D9 whole-sign houses counted from the D9 Lagna sign"],
      ["Swiss Ephemeris", "Library " + sw.library_version + ", " + sw.python_binding + " " + sw.python_binding_version],
      ["Ephemeris data", eph.source_repository + " @ " + eph.source_commit.slice(0, 12) + "; " +
        eph.required_files.map(function (f) { return f.name + " sha256 " + f.sha256.slice(0, 12) + "…"; }).join(", ")],
      ["Timezone data", tz.source + " " + tz.package_version + " (IANA " + tz.iana_version + "), verified before use"],
      ["Time scale", meta.time_scale.ut1_assumption],
      ["Chart schema", chart.schema_version, "schema_version"],
      ["Metadata schema", meta.metadata_schema, "metadata_schema"],
      ["Birthplace data", p.source + " (prototype fixture, not the production gazetteer)"]
    ];
    (meta.disclosures || []).forEach(function (d) {
      rows.push(["Disclosure " + d.code, d.description]);
    });
    dl($("method-list"), rows);

    $("result").hidden = false;
    downloadBtn.disabled = false;
    $("result").focus();
  }

  /* Every submit, Clear and field edit starts a new generation and aborts the
   * request in flight. A response from an older generation is ignored, so a
   * late chart or error can never replace what the current fields describe. */
  var generation = 0, inflight = null, pdfInflight = null, lastSuccessfulPayload = null;

  function invalidate() {
    generation += 1;
    if (inflight) { inflight.abort(); inflight = null; }
    if (pdfInflight) { pdfInflight.abort(); pdfInflight = null; }
    lastSuccessfulPayload = null;
    downloadBtn.disabled = true;
    // An aborted PDF request skips its own reset, so restore the label here.
    downloadBtn.textContent = "Download Kundali PDF";
    $("result").hidden = true;
    $("error-card").hidden = true;
    setStatus("");
    submitBtn.disabled = unknown.checked;
  }

  function ignored() {
    form.dataset.ignoredResponses = String(Number(form.dataset.ignoredResponses || 0) + 1);
  }

  function submit(ev) {
    ev.preventDefault();
    invalidate();
    if (!validate()) { return; }
    if (pendingChoice && !form.querySelector("input[name='occurrence']:checked")) {
      showError("TIME_AMBIGUOUS_LOCAL"); return;
    }
    var mine = generation, controller = new AbortController();
    inflight = controller;
    var requestPayload = payload();
    submitBtn.disabled = true;
    setStatus("Calculating with the local engine…");
    fetch("/api/chart", { method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/json" },
                          body: JSON.stringify(requestPayload), signal: controller.signal })
      .then(function (r) { return r.json().then(function (j) { return { status: r.status, body: j }; }); })
      .then(function (res) {
        if (mine !== generation) { ignored(); return; }
        setStatus("");
        if (res.status === 200) { hideAmbiguity(); render(res.body); lastSuccessfulPayload = requestPayload; setStatus("Chart calculated."); return; }
        var e = res.body.error || {};
        if (e.code === "TIME_AMBIGUOUS_LOCAL" && e.choices) { showAmbiguity(e.choices); setStatus(MESSAGES.TIME_AMBIGUOUS_LOCAL); return; }
        hideAmbiguity();
        if (e.code === "BIRTH_DATE_INVALID") { setFieldError(dateIn, "date-error", MESSAGES[e.code]); }
        if (e.code === "BIRTH_TIME_INVALID" || e.code === "BIRTH_TIME_REQUIRED") { setFieldError(timeIn, "time-error", MESSAGES[e.code]); }
        showError(e.code || "INTERNAL_ERROR", (res.status === 503 && SERVER_FAULTS[e.category]) || e.message);
      })
      .catch(function () {
        if (mine !== generation) { ignored(); return; }
        setStatus(""); showError("INTERNAL_ERROR");
      })
      .then(function () {
        if (mine !== generation) { return; }
        inflight = null;
        submitBtn.disabled = unknown.checked;
      });
  }

  downloadBtn.addEventListener("click", function () {
    if (downloadBtn.disabled || !lastSuccessfulPayload || $("result").hidden) { return; }
    var mine = generation, controller = new AbortController();
    pdfInflight = controller;
    downloadBtn.disabled = true;
    downloadBtn.textContent = "Preparing PDF...";
    setStatus("Creating your Kundali PDF in memory...");
    fetch("/api/report", {
      method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/pdf" },
      body: JSON.stringify(lastSuccessfulPayload), signal: controller.signal
    }).then(function (r) {
      if (!r.ok || !(r.headers.get("Content-Type") || "").startsWith("application/pdf")) {
        throw new Error("report refused");
      }
      return r.blob();
    }).then(function (pdf) {
      if (mine !== generation) { ignored(); return; }
      if (pdf.size < 100 || pdf.size > 1048576) { throw new Error("invalid PDF size"); }
      return pdf.slice(0, 5).text().then(function (signature) {
        if (signature !== "%PDF-") { throw new Error("invalid PDF response"); }
        if (mine !== generation) { ignored(); return; }
        var blobUrl = URL.createObjectURL(pdf);
        var a = document.createElement("a");
        a.href = blobUrl;
        a.download = "Sabpuja-Janma-Kundali.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(function () { URL.revokeObjectURL(blobUrl); }, 2000);
        setStatus("PDF downloaded.");
      });
    }).catch(function () {
      if (mine === generation && !controller.signal.aborted) {
        setStatus("PDF download is unavailable. Your chart is still available.");
      }
    }).then(function () {
      if (mine !== generation) { return; }
      pdfInflight = null;
      downloadBtn.disabled = false;
      downloadBtn.textContent = "Download Kundali PDF";
    });
  });

  form.addEventListener("submit", submit);
  // An edit means any shown result or pending request no longer matches the form.
  [placeSel, dateIn, timeIn].forEach(function (el) {
    ["input", "change"].forEach(function (type) {
      el.addEventListener(type, function () { invalidate(); hideAmbiguity(); });
    });
  });
  unknown.addEventListener("change", function () {
    $("unknown-time-panel").hidden = !unknown.checked;
    timeIn.disabled = unknown.checked;
    if (unknown.checked) { timeIn.value = ""; }
    invalidate(); hideAmbiguity();
  });
  $("clear").addEventListener("click", function () {
    form.reset(); clearErrors(); hideAmbiguity();
    timeIn.disabled = false; $("unknown-time-panel").hidden = true;
    invalidate();
    placeSel.focus();
  });
  // Chart section links move focus to the section, so keyboard users land on it.
  [].forEach.call(document.querySelectorAll(".chart-nav a"), function (a) {
    a.addEventListener("click", function (ev) {
      var target = $(a.getAttribute("href").slice(1));
      if (!target) { return; }
      ev.preventDefault();
      target.scrollIntoView();
      target.focus();
    });
  });
  $("edit").addEventListener("click", function () {
    $("form-section").scrollIntoView(); placeSel.focus();
  });
  loadPlaces();
})();
