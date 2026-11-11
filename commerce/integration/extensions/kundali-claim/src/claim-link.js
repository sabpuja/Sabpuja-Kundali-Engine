// Pure helpers shared by both blocks (KUN-COM-UX-CLAIM-001). No Shopify globals here, so they are unit-tested in Node.
//
// The claim link never carries an e-mail address, birth detail, token or secret. It carries at most the order
// reference in the URL fragment (after "#"), which browsers do not send to any server, so it reaches neither the
// commerce host's logs nor a Referer header. The claim page removes it from the address bar on arrival.

const GID_ORDER = /^gid:\/\/shopify\/Order\/([0-9]{1,20})$/;
const ORDER_NAME = /^#?([0-9]{1,12})$/;

/** The merchant's claim page URL, reduced to "https://host[:port]/", or null when it is not a plain https origin. */
export function claimBase(value) {
  if (typeof value !== "string" || value.length > 200) return null;
  let url;
  try { url = new URL(value.trim()); } catch (e) { return null; }
  if (url.protocol !== "https:" || url.username || url.password || url.search || url.hash) return null;
  if (url.pathname !== "/" && url.pathname !== "") return null;
  return `${url.origin}/`;
}

/** True when one of the lines is the Janam Kundali product (matched by SKU). */
export function hasKundali(lines, sku) {
  const want = typeof sku === "string" ? sku.trim() : "";
  if (!want || !Array.isArray(lines)) return false;
  return lines.some((line) => line && line.merchandise && line.merchandise.sku === want);
}

/** Thank you page: the order id from the order confirmation (the page shows no order number yet). */
export function thankYouLink(base, orderGid) {
  const m = typeof orderGid === "string" ? GID_ORDER.exec(orderGid) : null;
  return m ? `${base}#ref=${m[1]}` : base;
}

/** The order GID from the Thank you page's order confirmation, or undefined while it has not arrived yet. */
export function orderIdFromConfirmation(confirmation) {
  const id = confirmation && confirmation.order ? confirmation.order.id : undefined;
  return typeof id === "string" ? id : undefined;
}

/**
 * QA diagnostic for the Thank you identifier: the GID type and digit count only, never the id itself, plus whether
 * a confirmation number is present. Example: "QA: confirmation present; order id Order, 13 digits".
 */
export function describeOrderId(confirmation, orderId) {
  const parts = [];
  parts.push(confirmation ? "confirmation present" : "no confirmation yet");
  if (confirmation && typeof confirmation.number === "string") parts.push("confirmation number " + confirmation.number.length + " chars");
  const id = orderId !== undefined ? orderId
    : (confirmation && confirmation.order && confirmation.order.id !== undefined ? confirmation.order.id : undefined);
  if (id === undefined || id === null) parts.push("order id none");
  else if (typeof id !== "string") parts.push("order id not text");
  else {
    const m = /^gid:\/\/shopify\/([A-Za-z]{1,40})\/([0-9]{1,30})$/.exec(id);
    parts.push(m ? "order id " + m[1] + ", " + m[2].length + " digits" : "order id other format, " + id.length + " chars");
  }
  return "QA: " + parts.join("; ");
}

/** Order status page: the order number the customer also sees in the e-mail ("#1001"). */
export function orderStatusLink(base, orderName) {
  const m = typeof orderName === "string" ? ORDER_NAME.exec(orderName.trim()) : null;
  return m ? `${base}#order=${m[1]}` : base;
}
