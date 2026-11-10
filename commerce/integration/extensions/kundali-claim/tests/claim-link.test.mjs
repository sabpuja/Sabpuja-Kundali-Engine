import { test } from "node:test";
import assert from "node:assert/strict";
import { claimBase, hasKundali, orderStatusLink, thankYouLink } from "../src/claim-link.js";

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
