// customer-account.order-status.block.render: the same action on the order status page, where customers come back
// later. Hidden for cancelled orders (the claim page would refuse them anyway).
import "@shopify/ui-extensions/preact";
import { render } from "preact";
import { ClaimBlock } from "./ClaimBlock.jsx";
import { claimBase, hasKundali, orderStatusLink } from "./claim-link.js";

export default function extension() {
  render(<Extension />, document.body);
}

function Extension() {
  const settings = shopify.settings.value || {};
  const base = claimBase(settings.claim_url);
  const order = shopify.order.value;
  if (!base || !order || order.cancelledAt || !hasKundali(shopify.lines.value, settings.sku)) return null;
  return <ClaimBlock href={orderStatusLink(base, order.name)} orderLabel={order.name} />;
}
