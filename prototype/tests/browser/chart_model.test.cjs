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
