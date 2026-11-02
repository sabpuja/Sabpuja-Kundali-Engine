/* Prototype page logic. Every number shown comes from the server's engine result;
 * this file only validates the form, sends it, and lays the result out. */
(function () {
  "use strict";
  var C = window.SabpujaChart;
  var $ = function (id) { return document.getElementById(id); };
  var form = $("birth-form"), placeSel = $("place"), dateIn = $("birth-date"), timeIn = $("birth-time");
  var unknown = $("time-unknown"), submitBtn = $("submit"), downloadBtn = $("download-pdf");
  var nameIn = $("full-name");
  var places = {};
  var pendingChoice = null; // set only while the server is asking which repeated hour

  /* Language (KUN-I18N-001). Every customer-facing string comes from the one catalog,
   * /static/i18n.json (ui strings, the shared terminology register and Hindi forms of fixed
   * engine sentences). The language is held in memory only: no cookie, storage or URL. A
   * language change re-renders the text of what is already on screen from the result held in
   * memory; it never recalculates, never changes a value and never touches the form fields.
   * English is the default and is what index.html contains before the catalog loads. */
  var I18N = null, locale = "en";
  function t(key, values) {
    var entry = I18N && I18N.ui[key];
    if (!entry) { throw new Error("missing interface string " + key); }
    return entry[locale].replace(/\{([a-z_]+)\}/g, function (m, k) { return values && values[k] !== undefined ? String(values[k]) : m; });
  }
  function terms() { return I18N.terms; }
  function grahaName(key) { return terms().graha[key][locale]; }
  function grahaLong(key) { return terms().graha[key][locale + "_long"]; }
  function grahaAbbr(key) { return terms().graha[key][locale + "_abbr"]; }
  function rashiName(name) { var r = terms().rashi[name]; return r ? r[locale] : name; }
  function nakshatraName(name) { return locale === "hi" && terms().nakshatra[name] ? terms().nakshatra[name] : name; }
  function placeText(p) {
    var entry = terms().place[p.id];
    if (locale === "hi" && entry && entry.en[0] === p.name && entry.en[1] === p.region && entry.en[2] === p.country) {
      return { name: entry.hi[0], region: entry.hi[1], country: entry.hi[2] };
    }
    return { name: p.name, region: p.region, country: p.country };
  }
  function placeSource(text) {
    var rule = terms().place_source, m = new RegExp(rule.pattern).exec(text);
    if (locale !== "hi" || !m) { return text; }
    return rule.hi.replace("{1}", m[1]).replace("{2}", m[2]);
  }
  // A fixed engine sentence in Hindi only when the engine sent exactly the catalogued English.
  function engineText(key, value) {
    var entry = I18N.engine_text[key];
    return locale === "hi" && entry && entry.en === value ? entry.hi : value;
  }
  function message(code) { var entry = I18N && I18N.ui["msg." + code]; return entry ? entry[locale] : null; }

  // What is on screen, kept as keys so a language change can redraw it in the other language.
  var fieldErrors = {}, errorState = null, statusKey = null, lastRender = null;

  function setFieldError(input, errId, key) {
    var el = $(errId);
    if (key) { fieldErrors[errId] = { input: input, key: key }; el.textContent = t(key); el.hidden = false; input.setAttribute("aria-invalid", "true"); }
    else { delete fieldErrors[errId]; el.textContent = ""; el.hidden = true; input.removeAttribute("aria-invalid"); }
  }

  /* Report name (KUN-UX-NAME-001): the same rule as report/phase1/display_name.py, which the
   * server applies again. Presentation only: the name is never sent to /api/chart, never
   * stored (no cookie, storage or URL) and is shown only with textContent. */
  var NAME = (function () {
    function ranges(pairs) {
      var set = {};
      pairs.forEach(function (p) { for (var c = p[0]; c <= p[1]; c += 1) { set[c] = true; } });
      return set;
    }
    var latin = [[0x41, 0x5A], [0x61, 0x7A], [0xC0, 0xD6], [0xD8, 0xF6], [0xF8, 0x107], [0x10A, 0x11B],
                 [0x11E, 0x123], [0x128, 0x130], [0x136, 0x137], [0x139, 0x148], [0x14C, 0x15B], [0x15E, 0x165],
                 [0x168, 0x17E], [0x18F, 0x18F], [0x218, 0x21B], [0x259, 0x259]];
    var deva = [[0x901, 0x903], [0x905, 0x90D], [0x90F, 0x911], [0x913, 0x928], [0x92A, 0x933], [0x935, 0x939],
                [0x93C, 0x945], [0x947, 0x949], [0x94B, 0x94D], [0x960, 0x963], [0x972, 0x972]];
    var LETTERS = ranges(latin.concat(deva));
    var SEPARATORS = { 0x20: true, 0x27: true, 0x2019: true, 0x2D: true, 0x2E: true };
    var VIRAMA = 0x94D, ZWNJ = 0x200C, ZWJ = 0x200D;
    var FORBIDDEN = /[\p{Cc}\p{Cs}\p{Co}\p{Cn}\p{Zl}\p{Zp}]|(?![\u200C\u200D])\p{Cf}/u;
    var MARK = /\p{M}/u, OUTER = /^\p{Zs}+|\p{Zs}+$/gu;
    function isDeva(cp) { return cp >= 0x900 && cp <= 0x97F; }
    function isMark(cp) { return MARK.test(String.fromCodePoint(cp)); }
    function visible(cps) { return cps.filter(function (cp) { return !isMark(cp) && cp !== ZWJ && cp !== ZWNJ; }).length; }
    // Returns { name: string|null } or { error: code }.
    function check(value) {
      if (Array.from(value).length > 320) { return { error: "DISPLAY_NAME_TOO_LONG" }; }
      if (FORBIDDEN.test(value)) { return { error: "DISPLAY_NAME_INVALID" }; }
      var text = value.normalize("NFC").replace(OUTER, "");
      if (!text) { return { name: null }; }
      var cps = Array.from(text, function (ch) { return ch.codePointAt(0); });
      if (visible(cps) > 80) { return { error: "DISPLAY_NAME_TOO_LONG" }; }
      if (!LETTERS[cps[0]]) { return { error: "DISPLAY_NAME_INVALID" }; }
      for (var i = 0; i < cps.length; i += 1) {
        var cp = cps[i], prev = i ? cps[i - 1] : null, next = i + 1 < cps.length ? cps[i + 1] : null;
        var ok;
        if (!(LETTERS[cp] || SEPARATORS[cp] || cp === ZWJ || cp === ZWNJ)) { ok = false; }
        else if (isMark(cp)) { ok = isDeva(cp) && prev !== null && isDeva(prev); }
        else if (cp === ZWJ || cp === ZWNJ) { ok = prev === VIRAMA && next !== null && isDeva(next) && !isMark(next); }
        else if (cp === 0x20) { ok = prev !== 0x20; }
        else if (cp === 0x27 || cp === 0x2019 || cp === 0x2D) { ok = prev !== null && !SEPARATORS[prev] && next !== null && !SEPARATORS[next]; }
        else if (cp === 0x2E) { ok = prev !== null && !SEPARATORS[prev] && (next === null || next === 0x20); }
        else { ok = true; }
        if (!ok) { return { error: "DISPLAY_NAME_INVALID" }; }
      }
      return { name: text };
    }
    return { check: check };
  }());

  function clearErrors() {
    setFieldError(nameIn, "name-error", "");
    setFieldError(placeSel, "place-error", "");
    setFieldError(dateIn, "date-error", "");
    setFieldError(timeIn, "time-error", "");
    $("error-card").hidden = true;
  }

  // fault: a server-fault category (HTTP 503); serverMessage: the server's fixed English text,
  // shown only in English and only for codes the catalog does not describe.
  function errorText(state) {
    var known = state.fault ? t("fault." + state.fault) : message(state.code);
    if (known) { return known; }
    return (locale === "en" && state.serverMessage) || t("error.fallback");
  }
  function showError(code, serverMessage, fault) {
    var card = $("error-card");
    errorState = { code: code, serverMessage: serverMessage || null, fault: fault || null };
    $("error-message").textContent = errorText(errorState);
    $("error-code").textContent = code;
    card.hidden = false;
    card.focus();
  }

  function setStatus(key) { statusKey = key || null; $("status").textContent = key && I18N ? t(key) : ""; }

  var placeList = null;
  // Rebuilds the option labels in the current language; the selected place id is kept.
  function renderPlaces() {
    var keep = placeSel.value;
    placeSel.textContent = "";
    if (!placeList) { placeSel.appendChild(new Option(t("place.unavailable"), "")); return; }
    placeSel.appendChild(new Option(t("place.choose"), ""));
    var india = document.createElement("optgroup"); india.label = t("place.group_india");
    var other = document.createElement("optgroup"); other.label = t("place.group_other");
    placeList.forEach(function (p) {
      var shown = placeText(p);
      var label = shown.name + ", " + shown.region + (p.country === "India" ? "" : ", " + shown.country);
      (p.country === "India" ? india : other).appendChild(new Option(label, p.id));
    });
    placeSel.appendChild(india);
    placeSel.appendChild(other);
    placeSel.value = keep;
  }

  function loadPlaces() {
    return fetch("/api/places", { headers: { "Accept": "application/json" } })
      .then(function (r) { if (!r.ok) { throw new Error("places"); } return r.json(); })
      .then(function (data) {
        placeList = data.places;
        data.places.forEach(function (p) { places[p.id] = p; });
        renderPlaces();
      })
      .catch(function () { placeList = null; renderPlaces(); });
  }

  function validate() {
    clearErrors();
    var ok = true;
    var named = NAME.check(nameIn.value);
    if (named.error) { setFieldError(nameIn, "name-error", "msg." + named.error); ok = false; }
    if (!placeSel.value) { setFieldError(placeSel, "place-error", "val.place"); ok = false; }
    if (!dateIn.value) { setFieldError(dateIn, "date-error", "val.date_missing"); ok = false; }
    else if (!/^[0-9]{4}-[0-9]{2}-[0-9]{2}$/.test(dateIn.value)) { setFieldError(dateIn, "date-error", "val.date_format"); ok = false; }
    if (unknown.checked) { setFieldError(timeIn, "time-error", "val.time_unknown"); ok = false; }
    else if (!timeIn.value) { setFieldError(timeIn, "time-error", "val.time_missing"); ok = false; }
    else if (!/^[0-9]{2}:[0-9]{2}(:[0-9]{2})?$/.test(timeIn.value)) { setFieldError(timeIn, "time-error", "val.time_format"); ok = false; }
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

  // Choice labels are built from the offsets in the current language; a language change
  // relabels them and keeps the checked choice.
  function renderAmbiguity() {
    var box = $("ambiguity-choices"), picked = form.querySelector("input[name='occurrence']:checked");
    var keep = picked ? picked.value : null;
    box.textContent = "";
    pendingChoice.forEach(function (c, i) {
      var label = document.createElement("label");
      var input = document.createElement("input");
      input.type = "radio"; input.name = "occurrence"; input.value = c.utc_offset; input.required = true;
      if (i === 0) { input.id = "occurrence-0"; }
      if (c.utc_offset === keep) { input.checked = true; }
      label.appendChild(input);
      label.appendChild(document.createTextNode(t(i === 0 ? "ambiguity.choice0" : "ambiguity.choice1", { offset: c.utc_offset })));
      box.appendChild(label);
    });
    submitBtn.textContent = t("submit.occurrence");
  }

  function showAmbiguity(choices) {
    pendingChoice = choices.slice(0, 2);
    $("ambiguity").hidden = false;
    renderAmbiguity();
    $("occurrence-0").focus();
  }

  function hideAmbiguity() {
    pendingChoice = null;
    $("ambiguity").hidden = true;
    $("ambiguity-choices").textContent = "";
    if (I18N) { submitBtn.textContent = t("submit"); }
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

  function signLabel(name) {
    return locale === "en" ? name + " (" + C.SIGN_ENGLISH[C.SIGNS.indexOf(name)] + ")" : rashiName(name);
  }

  function row(tbody, cells, cls, key) {
    var tr = document.createElement("tr");
    if (cls) { tr.className = cls; }
    tr.setAttribute("data-graha", key);
    cells.forEach(function (c, i) {
      var cell = document.createElement(i === 0 ? "th" : "td");
      if (i === 0) { cell.scope = "row"; }
      if (c.sign && locale !== "en") {
        cell.textContent = rashiName(c.sign);
      } else if (c.sign) {
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

  function chartLabels() {
    return { lagna: terms().lagna[locale + "_abbr"], abbr: grahaAbbr, name: grahaLong, sign: rashiName, empty: t("svg.empty"),
             house: function (n, sign, grahas) { return t("svg.house", { house: n, sign: sign, grahas: grahas }); } };
  }

  // refresh: redraw the shown result in the current language (no focus move, no new request).
  function render(data, name, refresh) {
    var chart = data.chart, input = data.input, meta = chart.calculation_metadata;
    // Both models are built before anything is drawn: either throws if the engine result is
    // inconsistent, and then no chart is shown (the result stays hidden).
    var model = C.buildD1Model(chart), d9Model = C.buildD9Model(chart);
    C.renderNorthIndian($("d1-chart"), model, { id: "d1", title: t("svg.d1_title"), labels: chartLabels() });
    C.renderNorthIndian($("d9-chart"), d9Model, { id: "d9", title: t("svg.d9_title"), labels: chartLabels() });

    var p = input.place, shown = placeText(p);
    // The name is set with textContent only, never parsed as markup.
    $("result-name").textContent = name || "";
    $("result-for").hidden = !name;
    dl($("confirm-list"), (name ? [[t("fact.name"), name, "display_name"]] : []).concat([
      [t("fact.birthplace"), shown.name + ", " + shown.region + ", " + shown.country],
      [t("fact.coordinates"), p.latitude.toFixed(5) + "°, " + p.longitude.toFixed(5) + "°"],
      [t("fact.timezone"), p.timezone],
      [t("fact.local_date"), input.local_date, "local_date"],
      [t("fact.local_time"), input.local_time, "local_time"],
      [t("fact.utc_offset"), input.utc_offset + (input.offset_resolution === "user_selected_repeated_hour" ? t("fact.utc_choice") : ""), "utc_offset"],
      [t("fact.utc"), chart.birth.utc, "utc"]
    ]));
    var nameDd = $("confirm-list").querySelector("[data-field='display_name']");
    if (nameDd) { nameDd.className = "name-text"; }
    dl($("key-list"), [
      [t("key.lagna"), signLabel(chart.lagna.rashi), "lagna_rashi"],
      [t("key.moon_rashi"), signLabel(chart.planets.moon.rashi), "moon_rashi"],
      [t("key.moon_nakshatra"), t("key.nakshatra_value", { name: nakshatraName(chart.moon_nakshatra.name), pada: chart.moon_nakshatra.pada }), "moon_nakshatra"],
      [t("key.d9_lagna"), signLabel(chart.lagna.navamsa_rashi), "d9_lagna"]
    ]);

    var d1 = $("d1-table").tBodies[0], d9 = $("d9-table").tBodies[0];
    d1.textContent = ""; d9.textContent = "";
    row(d1, [{ text: t("row.lagna") }, { text: chart.lagna.longitude_deg.toFixed(8) + "°", cls: "num", field: "longitude" },
             { sign: chart.lagna.rashi, field: "rashi" }, { text: "1", field: "house", cls: "num" }], "row--lagna", "lagna");
    row(d9, [{ text: t("row.d9_lagna") }, { sign: chart.lagna.navamsa_rashi, field: "navamsa" },
             { text: "1", field: "d9_house", cls: "num" }], "row--lagna", "lagna");
    C.GRAHAS.forEach(function (g) {
      var pl = chart.planets[g.key];
      row(d1, [{ text: grahaName(g.key) }, { text: pl.longitude_deg.toFixed(8) + "°", cls: "num", field: "longitude" },
               { sign: pl.rashi, field: "rashi" }, { text: String(pl.whole_sign_house), field: "house", cls: "num" }], "", g.key);
      row(d9, [{ text: grahaName(g.key) }, { sign: pl.navamsa_rashi, field: "navamsa" },
               { text: String(pl.navamsa_whole_sign_house), field: "d9_house", cls: "num" }], "", g.key);
    });

    var eph = meta.ephemeris_data, tz = meta.timezone_data, sw = meta.swiss_ephemeris;
    $("claim").textContent = t("claim", { status: meta.validation.status,
                                          boundary: engineText("claim_boundary", meta.validation.claim_boundary) });
    var rows = [
      [t("m.zodiac"), t("m.zodiac_value", { definition: engineText("ayanamsa_definition", meta.conventions.ayanamsa.definition) })],
      [t("m.nodes"), t("m.nodes_value")],
      [t("m.houses"), t("m.houses_value")],
      [t("m.d9"), t("m.d9_value")],
      [t("m.swiss"), t("m.swiss_value", { library: sw.library_version, binding: sw.python_binding, binding_version: sw.python_binding_version })],
      [t("m.ephe"), eph.source_repository + " @ " + eph.source_commit.slice(0, 12) + "; " +
        eph.required_files.map(function (f) { return f.name + " sha256 " + f.sha256.slice(0, 12) + "…"; }).join(", ")],
      [t("m.tz"), t("m.tz_value", { source: tz.source, package: tz.package_version, iana: tz.iana_version })],
      [t("m.time_scale"), engineText("ut1_assumption", meta.time_scale.ut1_assumption)],
      [t("m.schema"), chart.schema_version, "schema_version"],
      [t("m.metadata"), meta.metadata_schema, "metadata_schema"],
      [t("m.place"), t("m.place_value", { source: placeSource(p.source) })]
    ];
    (meta.disclosures || []).forEach(function (d) {
      rows.push([t("m.disclosure", { code: d.code }), engineText("disclosure." + d.code, d.description)]);
    });
    dl($("method-list"), rows);

    lastRender = { data: data, name: name };
    if (refresh) { return; }
    $("result").hidden = false;
    downloadBtn.disabled = false;
    $("result").focus();
  }

  /* Every submit, Clear and field edit starts a new generation and aborts the
   * request in flight. A response from an older generation is ignored, so a
   * late chart or error can never replace what the current fields describe. */
  // pdfGeneration also moves on a language change, so a PDF requested in the old language is
  // aborted and, if it still arrives, discarded instead of downloaded.
  var generation = 0, pdfGeneration = 0, inflight = null, pdfInflight = null, lastSuccessfulPayload = null, lastSuccessfulName = null;

  function invalidate() {
    generation += 1;
    pdfGeneration += 1;
    if (inflight) { inflight.abort(); inflight = null; }
    if (pdfInflight) { pdfInflight.abort(); pdfInflight = null; }
    lastSuccessfulPayload = null;
    lastSuccessfulName = null;
    lastRender = null;
    $("result-name").textContent = "";
    $("result-for").hidden = true;
    downloadBtn.disabled = true;
    // An aborted PDF request skips its own reset, so restore the label here.
    if (I18N) { downloadBtn.textContent = t("download"); }
    $("result").hidden = true;
    $("error-card").hidden = true;
    errorState = null;
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
    var requestName = NAME.check(nameIn.value).name; // validated above; held in memory only
    submitBtn.disabled = true;
    setStatus("status.calculating");
    fetch("/api/chart", { method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/json" },
                          body: JSON.stringify(requestPayload), signal: controller.signal })
      .then(function (r) { return r.json().then(function (j) { return { status: r.status, body: j }; }); })
      .then(function (res) {
        if (mine !== generation) { ignored(); return; }
        setStatus("");
        if (res.status === 200) { hideAmbiguity(); render(res.body, requestName); lastSuccessfulPayload = requestPayload; lastSuccessfulName = requestName; setStatus("status.calculated"); return; }
        var e = res.body.error || {};
        if (e.code === "TIME_AMBIGUOUS_LOCAL" && e.choices) { showAmbiguity(e.choices); setStatus("msg.TIME_AMBIGUOUS_LOCAL"); return; }
        hideAmbiguity();
        if (e.code === "BIRTH_DATE_INVALID") { setFieldError(dateIn, "date-error", "msg." + e.code); }
        if (e.code === "BIRTH_TIME_INVALID" || e.code === "BIRTH_TIME_REQUIRED") { setFieldError(timeIn, "time-error", "msg." + e.code); }
        var fault = res.status === 503 && (e.category === "resources" || e.category === "computation") ? e.category : null;
        showError(e.code || "INTERNAL_ERROR", e.message, fault);
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

  // /api/report alone accepts the optional name and the report language; the chart request never
  // carries either. English sends no report_locale, exactly as before (the server default).
  function reportPayload(reportLocale) {
    var body = {};
    Object.keys(lastSuccessfulPayload).forEach(function (k) { body[k] = lastSuccessfulPayload[k]; });
    if (lastSuccessfulName) { body.display_name = lastSuccessfulName; }
    if (reportLocale !== "en") { body.report_locale = reportLocale; }
    return body;
  }

  downloadBtn.addEventListener("click", function () {
    if (downloadBtn.disabled || !lastSuccessfulPayload || $("result").hidden) { return; }
    var mine = generation, minePdf = pdfGeneration, controller = new AbortController();
    var current = function () { return mine === generation && minePdf === pdfGeneration; };
    pdfInflight = controller;
    downloadBtn.disabled = true;
    downloadBtn.textContent = t("download.preparing");
    setStatus("status.pdf_creating");
    fetch("/api/report", {
      method: "POST", headers: { "Content-Type": "application/json", "Accept": "application/pdf" },
      body: JSON.stringify(reportPayload(locale)), signal: controller.signal
    }).then(function (r) {
      if (!r.ok || !(r.headers.get("Content-Type") || "").startsWith("application/pdf")) {
        throw new Error("report refused");
      }
      return r.blob();
    }).then(function (pdf) {
      if (!current()) { ignored(); return; }
      if (pdf.size < 100 || pdf.size > 1048576) { throw new Error("invalid PDF size"); }
      return pdf.slice(0, 5).text().then(function (signature) {
        if (signature !== "%PDF-") { throw new Error("invalid PDF response"); }
        if (!current()) { ignored(); return; }
        var blobUrl = URL.createObjectURL(pdf);
        var a = document.createElement("a");
        a.href = blobUrl;
        a.download = "Sabpuja-Janma-Kundali.pdf";
        document.body.appendChild(a);
        a.click();
        a.remove();
        setTimeout(function () { URL.revokeObjectURL(blobUrl); }, 2000);
        setStatus("status.pdf_done");
      });
    }).catch(function () {
      if (current() && !controller.signal.aborted) {
        setStatus("status.pdf_unavailable");
      }
    }).then(function () {
      if (!current()) { return; }
      pdfInflight = null;
      downloadBtn.disabled = false;
      downloadBtn.textContent = t("download");
    });
  });

  // Every static string in the page, in the current language.
  function applyStatic() {
    document.documentElement.lang = I18N.locales[locale].html_lang;
    [].forEach.call(document.querySelectorAll("[data-i18n]"), function (el) { el.textContent = t(el.getAttribute("data-i18n")); });
    [].forEach.call(document.querySelectorAll("[data-i18n-aria]"), function (el) { el.setAttribute("aria-label", t(el.getAttribute("data-i18n-aria"))); });
    [].forEach.call(document.querySelectorAll(".lang-option"), function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-locale") === locale));
    });
  }

  /* Language switch. Redraws the text of the page, any field error, error card, repeated-hour
   * choice, place list and shown result in the new language, from memory. The form values,
   * the shown chart values and any chart request in flight are untouched. A PDF still being
   * prepared was asked for in the old language: it is aborted and its late response ignored. */
  function setLocale(next) {
    if (!I18N || !I18N.locales[next] || next === locale) { return; }
    locale = next;
    var pdfCancelled = !!pdfInflight;
    if (pdfInflight) { pdfInflight.abort(); pdfInflight = null; }
    pdfGeneration += 1;
    applyStatic();
    renderPlaces();
    Object.keys(fieldErrors).forEach(function (id) { setFieldError(fieldErrors[id].input, id, fieldErrors[id].key); });
    if (errorState && !$("error-card").hidden) { $("error-message").textContent = errorText(errorState); }
    if (pendingChoice) { renderAmbiguity(); } else { submitBtn.textContent = t("submit"); }
    if (lastRender && !$("result").hidden) {
      render(lastRender.data, lastRender.name, true);
      downloadBtn.disabled = false;
    }
    downloadBtn.textContent = t("download");
    setStatus(pdfCancelled ? "status.pdf_language_changed" : statusKey);
    $("lang-announce").textContent = t("lang.announce");
  }

  form.addEventListener("submit", submit);
  // An edit means any shown result or pending request no longer matches the form.
  [placeSel, dateIn, timeIn].forEach(function (el) {
    ["input", "change"].forEach(function (type) {
      el.addEventListener(type, function () { invalidate(); hideAmbiguity(); });
    });
  });
  // A name edit changes the report, so the shown result and any pending chart or PDF request
  // are discarded too; it does not touch a repeated-hour choice, which depends on the time only.
  ["input", "change"].forEach(function (type) {
    nameIn.addEventListener(type, function () { invalidate(); });
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
  [].forEach.call(document.querySelectorAll(".lang-option"), function (b) {
    b.addEventListener("click", function () { setLocale(b.getAttribute("data-locale")); });
  });

  // The catalog is loaded before the place list, so every label is drawn from it. Until it has
  // loaded the page is the English HTML and the Hindi option stays disabled.
  fetch("/static/i18n.json", { headers: { "Accept": "application/json" } })
    .then(function (r) { if (!r.ok) { throw new Error("catalog"); } return r.json(); })
    .then(function (catalog) {
      I18N = catalog;
      applyStatic();
      $("lang-hi").disabled = false;
      return loadPlaces();
    })
    .catch(function () {
      placeSel.textContent = "";
      placeSel.appendChild(new Option("Page resources unavailable. Please reload.", ""));
      submitBtn.disabled = true;
    });
})();
