/* North Indian D1 and D9 charts drawn from the engine's structured result.
 *
 * Nothing here computes a position or a house: each graha goes into the house
 * the engine reported (whole_sign_house for D1, navamsa_whole_sign_house for
 * D9). buildD1Model checks that every graha's reported rashi equals its house's
 * sign; buildD9Model checks the engine's d9 block against the per-graha D9
 * fields and the D9 Lagna. Both refuse to draw if the engine disagrees with itself.
 */
(function (root) {
  "use strict";

  var SIGNS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
               "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"];
  var SIGN_ENGLISH = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                      "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"];
  var GRAHAS = [
    { key: "sun", name: "Sun (Surya)", abbr: "Su" },
    { key: "moon", name: "Moon (Chandra)", abbr: "Mo" },
    { key: "mars", name: "Mars (Mangal)", abbr: "Ma" },
    { key: "mercury", name: "Mercury (Budha)", abbr: "Me" },
    { key: "jupiter", name: "Jupiter (Guru)", abbr: "Ju" },
    { key: "venus", name: "Venus (Shukra)", abbr: "Ve" },
    { key: "saturn", name: "Saturn (Shani)", abbr: "Sa" },
    { key: "rahu_mean", name: "Rahu (mean node)", abbr: "Ra" },
    { key: "ketu_mean", name: "Ketu (opposite mean Rahu)", abbr: "Ke" }
  ];

  // 600 x 600 North Indian square: house 1 is the top diamond and houses run
  // anticlockwise. box = [x0, y0, x1, y1] is a rectangle inside the polygon
  // that holds the graha labels; sign = where the sign number is drawn.
  var SIZE = 600;
  var HOUSES = [
    null,
    { poly: [[300, 0], [450, 150], [300, 300], [150, 150]], box: [225, 80, 375, 200], sign: [300, 250] },
    { poly: [[0, 0], [300, 0], [150, 150]], box: [100, 10, 200, 92], sign: [150, 125] },
    { poly: [[0, 0], [150, 150], [0, 300]], box: [10, 100, 92, 200], sign: [125, 150] },
    { poly: [[0, 300], [150, 150], [300, 300], [150, 450]], box: [80, 225, 200, 375], sign: [250, 300] },
    { poly: [[0, 300], [150, 450], [0, 600]], box: [10, 400, 92, 500], sign: [125, 450] },
    { poly: [[0, 600], [150, 450], [300, 600]], box: [100, 508, 200, 590], sign: [150, 475] },
    { poly: [[300, 600], [150, 450], [300, 300], [450, 450]], box: [225, 400, 375, 520], sign: [300, 350] },
    { poly: [[300, 600], [450, 450], [600, 600]], box: [400, 508, 500, 590], sign: [450, 475] },
    { poly: [[600, 600], [450, 450], [600, 300]], box: [508, 400, 590, 500], sign: [475, 450] },
    { poly: [[600, 300], [450, 450], [300, 300], [450, 150]], box: [400, 225, 520, 375], sign: [350, 300] },
    { poly: [[600, 300], [450, 150], [600, 0]], box: [508, 100, 590, 200], sign: [475, 150] },
    { poly: [[600, 0], [450, 150], [300, 0]], box: [400, 10, 500, 92], sign: [450, 125] }
  ];

  function signIndex(name) {
    var i = SIGNS.indexOf(name);
    if (i < 0) { throw new Error("unknown rashi in engine result"); }
    return i;
  }

  /* House-by-house model of the D1 chart, from the engine JSON only. */
  function buildD1Model(chart) {
    var lagnaIdx = signIndex(chart.lagna.rashi);
    var houses = [];
    for (var h = 1; h <= 12; h++) {
      var idx = (lagnaIdx + h - 1) % 12;
      houses.push({ house: h, signIndex: idx, signNumber: idx + 1, sign: SIGNS[idx],
                    signEnglish: SIGN_ENGLISH[idx], grahas: [], isLagna: h === 1 });
    }
    GRAHAS.forEach(function (g) {
      var p = chart.planets[g.key];
      if (!p) { throw new Error("engine result lacks " + g.key); }
      var house = p.whole_sign_house;
      if (!(house >= 1 && house <= 12) || Math.floor(house) !== house) {
        throw new Error("engine house out of range");
      }
      if (houses[house - 1].sign !== p.rashi) {
        throw new Error("engine rashi and whole-sign house disagree for " + g.key);
      }
      houses[house - 1].grahas.push({ key: g.key, abbr: g.abbr, name: g.name });
    });
    return { lagnaSign: SIGNS[lagnaIdx], houses: houses };
  }

  function isHouse(n) { return typeof n === "number" && Math.floor(n) === n && n >= 1 && n <= 12; }

  /* House-by-house model of the D9 chart, from the engine JSON only (schema 0.3.0 d9 block).
   * Every D9 field must agree: d9.lagna_rashi with lagna.navamsa_rashi, the twelve house
   * signs with the D9 Lagna order, and each house's grahas with planets.*.navamsa_rashi and
   * planets.*.navamsa_whole_sign_house. Any disagreement throws; nothing is drawn. */
  function buildD9Model(chart) {
    var d9 = chart.d9;
    if (!d9 || d9.house_system !== "whole_sign" || !Array.isArray(d9.houses) || d9.houses.length !== 12) {
      throw new Error("engine result lacks a whole-sign D9 house block");
    }
    if (d9.lagna_rashi !== chart.lagna.navamsa_rashi) { throw new Error("engine D9 Lagna fields disagree"); }
    var lagnaIdx = signIndex(d9.lagna_rashi);
    var houses = [], listed = {};
    d9.houses.forEach(function (h, i) {
      var idx = (lagnaIdx + i) % 12;
      if (h.house !== i + 1 || h.rashi !== SIGNS[idx] || !Array.isArray(h.grahas)) {
        throw new Error("engine D9 house " + (i + 1) + " is out of order or has the wrong rashi");
      }
      h.grahas.forEach(function (key) {
        if (listed[key] !== undefined) { throw new Error("engine D9 houses list " + key + " twice"); }
        listed[key] = i + 1;
      });
      houses.push({ house: i + 1, signIndex: idx, signNumber: idx + 1, sign: SIGNS[idx],
                    signEnglish: SIGN_ENGLISH[idx], grahas: [], isLagna: i === 0 });
    });
    if (Object.keys(listed).length !== GRAHAS.length) { throw new Error("engine D9 houses do not list every graha once"); }
    GRAHAS.forEach(function (g) {
      var p = chart.planets[g.key];
      if (!p) { throw new Error("engine result lacks " + g.key); }
      var house = p.navamsa_whole_sign_house;
      if (!isHouse(house)) { throw new Error("engine D9 house out of range"); }
      if (listed[g.key] !== house) { throw new Error("engine D9 house block and D9 house field disagree for " + g.key); }
      if (houses[house - 1].sign !== p.navamsa_rashi) {
        throw new Error("engine D9 rashi and D9 whole-sign house disagree for " + g.key);
      }
      houses[house - 1].grahas.push({ key: g.key, abbr: g.abbr, name: g.name });
    });
    return { lagnaSign: SIGNS[lagnaIdx], houses: houses };
  }

  /* Largest font (9..18 px) and grid that fit n labels inside the box. */
  function layoutLabels(labels, box) {
    var w = box[2] - box[0], h = box[3] - box[1], n = labels.length;
    if (n === 0) { return { fontSize: 0, items: [] }; }
    for (var f = 18; f >= 9; f--) {
      var cellW = f * 2.3, cellH = f * 1.35;
      for (var cols = 1; cols <= n; cols++) {
        var rows = Math.ceil(n / cols);
        if (cols * cellW <= w && rows * cellH <= h) {
          var items = [], gridW = cols * cellW, gridH = rows * cellH;
          var x0 = box[0] + (w - gridW) / 2, y0 = box[1] + (h - gridH) / 2;
          labels.forEach(function (label, i) {
            var r = Math.floor(i / cols), c = i % cols;
            var inRow = Math.min(cols, n - r * cols);
            var rowOffset = (cols - inRow) * cellW / 2;
            items.push({ label: label, x: x0 + rowOffset + c * cellW + cellW / 2, y: y0 + r * cellH + cellH / 2 });
          });
          return { fontSize: f, items: items };
        }
      }
    }
    throw new Error("labels do not fit");
  }

  function el(doc, name, attrs, text) {
    var node = doc.createElementNS("http://www.w3.org/2000/svg", name);
    Object.keys(attrs || {}).forEach(function (k) { node.setAttribute(k, attrs[k]); });
    if (text !== undefined) { node.textContent = text; }
    return node;
  }

  /* opts.id prefixes the title and desc ids; opts.title names the chart. D1 by default. */
  function renderNorthIndian(svg, model, opts) {
    opts = opts || { id: "d1", title: "North Indian D1 chart, Lagna " };
    var doc = svg.ownerDocument;
    while (svg.firstChild) { svg.removeChild(svg.firstChild); }
    svg.setAttribute("viewBox", "-4 -4 " + (SIZE + 8) + " " + (SIZE + 8));
    var summary = model.houses.map(function (h) {
      return "House " + h.house + ", " + h.sign + ": " +
        (h.grahas.length ? h.grahas.map(function (g) { return g.name; }).join(", ") : "empty");
    }).join(". ");
    svg.appendChild(el(doc, "title", { id: opts.id + "-title" }, opts.title + model.lagnaSign));
    svg.appendChild(el(doc, "desc", { id: opts.id + "-desc" }, summary + "."));
    model.houses.forEach(function (h) {
      var geo = HOUSES[h.house];
      var g = el(doc, "g", { "class": "house" + (h.isLagna ? " house--lagna" : ""), "data-house": String(h.house),
                             "data-sign": h.sign });
      g.appendChild(el(doc, "polygon", { points: geo.poly.map(function (p) { return p.join(","); }).join(" "),
                                         "class": "house-shape" }));
      g.appendChild(el(doc, "text", { x: geo.sign[0], y: geo.sign[1], "class": "sign-number",
                                      "data-role": "sign-number" }, String(h.signNumber)));
      var labels = h.grahas.map(function (gr) { return { text: gr.abbr, key: gr.key, cls: "graha" }; });
      if (h.isLagna) { labels.unshift({ text: "Asc", key: "lagna", cls: "graha graha--lagna" }); }
      var lay = layoutLabels(labels, geo.box);
      lay.items.forEach(function (it) {
        g.appendChild(el(doc, "text", { x: it.x.toFixed(1), y: it.y.toFixed(1), "class": it.label.cls,
                                        "font-size": lay.fontSize, "data-graha": it.label.key }, it.label.text));
      });
      svg.appendChild(g);
    });
    svg.appendChild(el(doc, "rect", { x: 0, y: 0, width: SIZE, height: SIZE, "class": "chart-frame" }));
  }

  var api = { SIGNS: SIGNS, SIGN_ENGLISH: SIGN_ENGLISH, GRAHAS: GRAHAS, HOUSES: HOUSES,
              buildD1Model: buildD1Model, buildD9Model: buildD9Model, layoutLabels: layoutLabels, renderNorthIndian: renderNorthIndian };
  root.SabpujaChart = api;
  if (typeof module !== "undefined" && module.exports) { module.exports = api; }
})(typeof self !== "undefined" ? self : this);
