/* Unit checks of static/chart.js without a browser: node --test prototype/tests/browser/ */
"use strict";
const test = require("node:test");
const assert = require("node:assert");
const C = require("../../kundali_prototype/static/chart.js");

function chart(lagna, planets) {
  const out = { lagna: { rashi: lagna }, planets: {} };
  C.GRAHAS.forEach((g) => { out.planets[g.key] = planets[g.key]; });
  return out;
}

function planetsInHouse(lagna, house) {
  const sign = C.SIGNS[(C.SIGNS.indexOf(lagna) + house - 1) % 12];
  const p = {};
  C.GRAHAS.forEach((g) => { p[g.key] = { rashi: sign, whole_sign_house: house }; });
  return p;
}

test("houses follow the Lagna sign anticlockwise", () => {
  const m = C.buildD1Model(chart("Karka", planetsInHouse("Karka", 1)));
  assert.deepStrictEqual(m.houses.map((h) => h.signNumber), [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]);
  assert.strictEqual(m.houses[0].isLagna, true);
});

test("every house can hold all nine grahas plus Asc inside its label box", () => {
  for (let house = 1; house <= 12; house++) {
    for (let n = 0; n <= 10; n++) {
      const labels = Array.from({ length: n }, (_, i) => ({ text: i === 0 ? "Asc" : "Su" }));
      const lay = C.layoutLabels(labels, C.HOUSES[house].box);
      const box = C.HOUSES[house].box;
      lay.items.forEach((it) => {
        const halfW = lay.fontSize * 1.0, halfH = lay.fontSize * 0.6; // generous estimate for 3 glyphs
        assert.ok(it.x - halfW >= box[0] && it.x + halfW <= box[2], `x house ${house} n ${n}`);
        assert.ok(it.y - halfH >= box[1] && it.y + halfH <= box[3], `y house ${house} n ${n}`);
      });
      if (n) { assert.ok(lay.fontSize >= 9); }
    }
  }
});

test("label boxes lie inside their house polygons", () => {
  function inside(pt, poly) {
    let c = false;
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const [xi, yi] = poly[i], [xj, yj] = poly[j];
      if ((yi > pt[1]) !== (yj > pt[1]) && pt[0] < (xj - xi) * (pt[1] - yi) / (yj - yi) + xi) { c = !c; }
    }
    return c;
  }
  for (let h = 1; h <= 12; h++) {
    const { box, poly, sign } = C.HOUSES[h];
    [[box[0], box[1]], [box[2], box[1]], [box[0], box[3]], [box[2], box[3]], sign].forEach((pt) => assert.ok(inside(pt, poly), `house ${h} ${pt}`));
  }
});

test("refuses to draw when the engine's rashi and house disagree", () => {
  const p = planetsInHouse("Mesha", 1);
  p.sun = { rashi: "Vrishabha", whole_sign_house: 1 };
  assert.throws(() => C.buildD1Model(chart("Mesha", p)), /disagree/);
  p.sun = { rashi: "Mesha", whole_sign_house: 13 };
  assert.throws(() => C.buildD1Model(chart("Mesha", p)), /out of range/);
  assert.throws(() => C.buildD1Model(chart("Aries", planetsInHouse("Mesha", 1))), /unknown rashi/);
});

/* Gate 3E: D9 model from the engine's d9 block (proposed schema 0.3.0). */
function d9Chart(d9Lagna, houseOf) {
  // houseOf: graha key -> D9 house. Builds a self-consistent engine-shaped chart.
  const l = C.SIGNS.indexOf(d9Lagna);
  const out = { lagna: { rashi: "Mesha", navamsa_rashi: d9Lagna }, planets: {}, d9: { house_system: "whole_sign", lagna_rashi: d9Lagna, houses: [] } };
  for (let h = 1; h <= 12; h++) { out.d9.houses.push({ house: h, rashi: C.SIGNS[(l + h - 1) % 12], grahas: [] }); }
  C.GRAHAS.forEach((g) => {
    const h = houseOf[g.key];
    out.planets[g.key] = { rashi: "Mesha", whole_sign_house: 1, navamsa_rashi: C.SIGNS[(l + h - 1) % 12], navamsa_whole_sign_house: h };
    out.d9.houses[h - 1].grahas.push(g.key);
  });
  return out;
}
const SPREAD = { sun: 1, moon: 2, mars: 3, mercury: 4, jupiter: 5, venus: 6, saturn: 12, rahu_mean: 4, ketu_mean: 10 };

test("D9 model places grahas in the engine's D9 houses, signs from the D9 Lagna", () => {
  const m = C.buildD9Model(d9Chart("Simha", SPREAD));
  assert.strictEqual(m.lagnaSign, "Simha");
  assert.deepStrictEqual(m.houses.map((h) => h.signNumber), [5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3, 4]);
  assert.deepStrictEqual(m.houses[3].grahas.map((g) => g.key), ["mercury", "rahu_mean"]);
  assert.deepStrictEqual(m.houses[11].grahas.map((g) => g.key), ["saturn"]);
  assert.strictEqual(m.houses[0].isLagna, true);
  assert.strictEqual(m.houses.filter((h) => h.grahas.length === 0).length, 4);
});

test("D9 model works for all twelve D9 Lagna signs and a fully crowded house", () => {
  C.SIGNS.forEach((s) => {
    const all = {}; C.GRAHAS.forEach((g) => { all[g.key] = 7; });
    const m = C.buildD9Model(d9Chart(s, all));
    assert.strictEqual(m.houses[6].grahas.length, 9);
    assert.strictEqual(m.houses[0].sign, s);
  });
});

test("D9 model refuses every internal disagreement in the engine result", () => {
  const cases = [
    [(c) => { delete c.d9; }, /lacks a whole-sign D9/],
    [(c) => { c.d9.house_system = "equal"; }, /lacks a whole-sign D9/],
    [(c) => { c.d9.houses.pop(); }, /lacks a whole-sign D9/],
    [(c) => { c.d9.lagna_rashi = "Kanya"; }, /D9 Lagna fields disagree/],
    [(c) => { c.lagna.navamsa_rashi = "Kanya"; }, /D9 Lagna fields disagree/],
    [(c) => { c.d9.houses[2].rashi = "Mesha"; }, /out of order or has the wrong rashi/],
    [(c) => { const t = c.d9.houses[0]; c.d9.houses[0] = c.d9.houses[1]; c.d9.houses[1] = t; }, /out of order/],
    [(c) => { c.d9.houses[5].grahas.push("sun"); }, /twice/],
    [(c) => { c.d9.houses[0].grahas = []; }, /every graha once/],
    [(c) => { c.planets.sun.navamsa_whole_sign_house = 13; }, /D9 house out of range/],
    [(c) => { c.planets.sun.navamsa_whole_sign_house = 1.5; }, /D9 house out of range/],
    [(c) => { c.planets.sun.navamsa_whole_sign_house = "1"; }, /D9 house out of range/],
    [(c) => { delete c.planets.sun.navamsa_whole_sign_house; }, /D9 house out of range/],
    [(c) => { c.planets.sun.navamsa_whole_sign_house = 2; c.planets.sun.navamsa_rashi = c.d9.houses[1].rashi; }, /block and D9 house field disagree/],
    [(c) => { c.planets.moon.navamsa_rashi = "Mesha"; }, /D9 rashi and D9 whole-sign house disagree/],
    [(c) => { c.d9.lagna_rashi = c.lagna.navamsa_rashi = "Aries"; }, /unknown rashi/]
  ];
  cases.forEach(([mutate, re], i) => {
    const c = d9Chart("Simha", SPREAD);
    mutate(c);
    assert.throws(() => C.buildD9Model(c), re, `case ${i}`);
  });
});

/* A minimal SVG document stand-in, enough for renderNorthIndian. */
function fakeSvg() {
  function node(name) {
    return { tagName: name, attrs: {}, children: [], textContent: "",
             setAttribute(k, v) { this.attrs[k] = String(v); },
             appendChild(c) { this.children.push(c); return c; },
             removeChild(c) { this.children.splice(this.children.indexOf(c), 1); },
             get firstChild() { return this.children[0] || null; } };
  }
  const doc = { createElementNS: (ns, name) => node(name) };
  const svg = node("svg"); svg.ownerDocument = doc;
  return svg;
}

test("shared renderer: D1 title unchanged by default, D9 gets its own ids and title", () => {
  const d1 = fakeSvg();
  C.renderNorthIndian(d1, C.buildD1Model(chart("Karka", planetsInHouse("Karka", 1))));
  assert.deepStrictEqual([d1.children[0].attrs.id, d1.children[0].textContent], ["d1-title", "North Indian D1 chart, Lagna Karka"]);
  assert.strictEqual(d1.children[1].attrs.id, "d1-desc");
  const d9 = fakeSvg();
  C.renderNorthIndian(d9, C.buildD9Model(d9Chart("Simha", SPREAD)), { id: "d9", title: "North Indian D9 Navamsa chart, D9 Lagna " });
  assert.deepStrictEqual([d9.children[0].attrs.id, d9.children[0].textContent], ["d9-title", "North Indian D9 Navamsa chart, D9 Lagna Simha"]);
  assert.strictEqual(d9.children[1].attrs.id, "d9-desc");
  assert.match(d9.children[1].textContent, /^House 1, Simha: Sun \(Surya\)\. House 2, Kanya: Moon \(Chandra\)\./);
  assert.match(d9.children[1].textContent, /House 7, Kumbha: empty\./);
  const groups = d9.children.filter((c) => c.tagName === "g");
  assert.strictEqual(groups.length, 12);
  assert.deepStrictEqual(groups[3].children.filter((c) => c.attrs["data-graha"]).map((c) => c.attrs["data-graha"]), ["mercury", "rahu_mean"]);
  assert.deepStrictEqual(groups[0].children.filter((c) => c.attrs["data-graha"]).map((c) => c.attrs["data-graha"]), ["lagna", "sun"]);
});
