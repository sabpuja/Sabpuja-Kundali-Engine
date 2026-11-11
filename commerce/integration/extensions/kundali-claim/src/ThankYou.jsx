// purchase.thank-you.block.render: shown after checkout when the order contains the Janam Kundali product.
import "@shopify/ui-extensions/preact";
import { render } from "preact";
import { useEffect, useState } from "preact/hooks";
import { effect } from "@preact/signals";
import { ClaimBlock } from "./ClaimBlock.jsx";
import { claimBase, hasKundali, orderIdFromConfirmation, thankYouLink } from "./claim-link.js";

export default function extension() {
  render(<Extension />, document.body);
}

function Extension() {
  // The order id can arrive after the first render, so follow the signal and re-render when it changes.
  const [orderId, setOrderId] = useState(undefined);
  useEffect(() => effect(() => {
    setOrderId(orderIdFromConfirmation(shopify.orderConfirmation.value));
  }), []);
  const settings = shopify.settings.value || {};
  const base = claimBase(settings.claim_url);
  if (!base || !hasKundali(shopify.lines.value, settings.sku)) return null;
  return <ClaimBlock href={thankYouLink(base, orderId)} />;
}
