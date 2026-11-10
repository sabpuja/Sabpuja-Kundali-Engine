// purchase.thank-you.block.render: shown after checkout when the order contains the Janam Kundali product.
import "@shopify/ui-extensions/preact";
import { render } from "preact";
import { ClaimBlock } from "./ClaimBlock.jsx";
import { claimBase, hasKundali, thankYouLink } from "./claim-link.js";

export default function extension() {
  render(<Extension />, document.body);
}

function Extension() {
  const settings = shopify.settings.value || {};
  const base = claimBase(settings.claim_url);
  if (!base || !hasKundali(shopify.lines.value, settings.sku)) return null;
  const confirmation = shopify.orderConfirmation.value;
  return <ClaimBlock href={thankYouLink(base, confirmation && confirmation.order && confirmation.order.id)} />;
}
