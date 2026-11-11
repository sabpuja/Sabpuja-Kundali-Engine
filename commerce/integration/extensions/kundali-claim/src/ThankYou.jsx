// purchase.thank-you.block.render: shown after checkout when the order contains the Janam Kundali product.
import "@shopify/ui-extensions/preact";
import { render } from "preact";
import { useSubscription } from "@shopify/ui-extensions/checkout/preact";
import { ClaimBlock } from "./ClaimBlock.jsx";
import { claimBase, describeOrderId, hasKundali, orderIdFromConfirmation, thankYouLink } from "./claim-link.js";

export default function extension() {
  render(<Extension />, document.body);
}

function Extension() {
  // Subscribe explicitly: the order confirmation can arrive after the first render.
  const confirmation = useSubscription(shopify.orderConfirmation);
  const settings = shopify.settings.value || {};
  const base = claimBase(settings.claim_url);
  if (!base || !hasKundali(shopify.lines.value, settings.sku)) return null;
  const orderId = orderIdFromConfirmation(confirmation);
  // QA stores only: show the id's type and digit count (never the id itself) to verify the identifier format.
  const diagnostic = settings.qa_diagnostics === true ? describeOrderId(confirmation, orderId) : undefined;
  return <ClaimBlock href={thankYouLink(base, orderId)} diagnostic={diagnostic} />;
}
