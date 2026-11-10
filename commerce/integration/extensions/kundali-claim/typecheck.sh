#!/bin/sh
# Type-checks each block against the @shopify/ui-extensions 2026.10 types of its own target (component names, props,
# and the shopify.* APIs each target really has). Needs: npm install; npx tsc (typescript 5.9).
set -e
cd "$(dirname "$0")"
check() {
  cat > "typecheck-$1.d.ts" <<DTS
import '@shopify/ui-extensions';
//@ts-ignore
declare module './src/$1.jsx' { const shopify: import('@shopify/ui-extensions/$2').Api; const globalThis: { shopify: typeof shopify }; }
//@ts-ignore
declare module './src/ClaimBlock.jsx' { const shopify: import('@shopify/ui-extensions/$2').Api; const globalThis: { shopify: typeof shopify }; }
DTS
  npx tsc --noEmit --allowJs --checkJs --jsx react-jsx --jsxImportSource preact --module esnext \
    --moduleResolution bundler --target es2022 --skipLibCheck "typecheck-$1.d.ts" "src/$1.jsx" src/ClaimBlock.jsx \
    src/claim-link.js && echo "$1 ($2): types OK"
  rm -f "typecheck-$1.d.ts"
}
check ThankYou purchase.thank-you.block.render
check OrderStatus customer-account.order-status.block.render
