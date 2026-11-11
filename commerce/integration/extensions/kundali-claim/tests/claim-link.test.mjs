import { test } from "node:test";
import assert from "node:assert/strict";
import { claimBase, describeOrderId, hasKundali, orderIdFromConfirmation, orderStatusLink, thankYouLink } from "../src/claim-link.js";

const BASE = "https://kundali-qa.example.test/";

test("claim base accepts only a plain https origin", () => {
  assert.equal(claimBase("https://kundali-qa.example.test/"), BASE);
  assert.equal(claimBase(" https://kundali-qa.example.test "), BASE);
  for (const bad of ["http://kundali-qa.example.test/", "https://user:pw@kundali-qa.example.test/",
    "https://kundali-qa.example.test/?email=a@b.c", "https://kundali-qa.example.test/#x",
    "https://kundali-qa.example.test/claim", "javascript:alert(1)", "", null, undefined, 42, "x".repeat(300)]) {
    assert.equal(claimBase(bad), null, String(bad));
  }
});

test("shown only for the Kundali SKU", () => {
  const lines = [{ merchandise: { sku: "OTHER" } }, { merchandise: { sku: "SBK-ESS-EN-1" } }];
  assert.equal(hasKundali(lines, "SBK-ESS-EN-1"), true);
  assert.equal(hasKundali(lines, " SBK-ESS-EN-1 "), true);
  assert.equal(hasKundali([{ merchandise: { sku: "OTHER" } }], "SBK-ESS-EN-1"), false);
  assert.equal(hasKundali([{ merchandise: {} }, null, {}], "SBK-ESS-EN-1"), false);
  assert.equal(hasKundali(lines, ""), false);
  assert.equal(hasKundali(undefined, "SBK-ESS-EN-1"), false);
});

test("links carry only the order reference, in the fragment", () => {
  assert.equal(thankYouLink(BASE, "gid://shopify/Order/6822712901691"), BASE + "#ref=6822712901691");
  assert.equal(thankYouLink(BASE, "gid://shopify/Customer/1"), BASE);
  assert.equal(thankYouLink(BASE, undefined), BASE);
  assert.equal(orderStatusLink(BASE, "#1004"), BASE + "#order=1004");
  assert.equal(orderStatusLink(BASE, "SP-1004"), BASE);
  for (const link of [thankYouLink(BASE, "gid://shopify/Order/1"), orderStatusLink(BASE, "#1")]) {
    const url = new URL(link);
    assert.equal(url.search, "");
    assert.doesNotMatch(link, /@|token|secret|birth|email/i);
  }
});

test("the order id is read when it arrives, and a late arrival updates the link", () => {
  // The first render has no confirmation yet, so the link is the bare host.
  assert.equal(thankYouLink(BASE, orderIdFromConfirmation(undefined)), BASE);
  assert.equal(thankYouLink(BASE, orderIdFromConfirmation({ order: null })), BASE);
  // Later the signal carries the order: the same helper now produces the #ref link.
  const later = { order: { id: "gid://shopify/Order/6838" } };
  assert.equal(thankYouLink(BASE, orderIdFromConfirmation(later)), BASE + "#ref=6838");
  assert.equal(orderIdFromConfirmation({ order: { id: 7 } }), undefined);
});

test("QA diagnostic shows only the identifier type and length, never the identifier", () => {
  assert.equal(describeOrderId(undefined, undefined), "QA: no confirmation yet; order id none");
  const order = { order: { id: "gid://shopify/Order/6838123456789" }, number: "4XTHGQHXW" };
  const line = describeOrderId(order, orderIdFromConfirmation(order));
  assert.equal(line, "QA: confirmation present; confirmation number 9 chars; order id Order, 13 digits");
  const identity = { order: { id: "gid://shopify/OrderIdentity/6838123456789" } };
  assert.equal(describeOrderId(identity, orderIdFromConfirmation(identity)),
    "QA: confirmation present; order id OrderIdentity, 13 digits");
  assert.equal(describeOrderId({ order: { id: "abc" } }, "abc"), "QA: confirmation present; order id other format, 3 chars");
  for (const l of [line]) { assert.ok(!l.includes("6838123456789")); assert.ok(!l.includes("4XTHGQHXW")); }
  // An OrderIdentity id is NOT turned into a claim reference (no unproven mapping).
  assert.equal(thankYouLink(BASE, orderIdFromConfirmation(identity)), BASE);
});
