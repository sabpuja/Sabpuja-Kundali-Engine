// The one block both targets render: heading, two short lines and a button that opens the claim page.
/** @param {{href: string, orderLabel?: string}} props */
export function ClaimBlock({ href, orderLabel }) {
  const t = (key, values) => shopify.i18n.translate(key, values);
  return (
    <s-section heading={t("heading")}>
      <s-stack gap="base">
        <s-paragraph>{t("body")}</s-paragraph>
        {orderLabel ? <s-paragraph>{t("order", { order: orderLabel })}</s-paragraph> : null}
        <s-paragraph>{t("language")}</s-paragraph>
        <s-button href={href} target="_blank" variant="primary">{t("button")}</s-button>
        <s-text color="subdued">{t("privacy")}</s-text>
      </s-stack>
    </s-section>
  );
}
