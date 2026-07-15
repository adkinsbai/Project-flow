import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

function read(path) {
  return readFileSync(new URL(`../${path}`, import.meta.url), "utf8");
}

const checkout = read("supabase/functions/creem-checkout/index.ts");
const webhook = read("supabase/functions/creem-webhook/index.ts");
const envExample = read(".env.example");
const readme = read("README.md");
const deploy = read("scripts/deploy-supabase.ps1");

assert.match(checkout, /checkout_url\s*\|\|\s*data\.checkoutUrl\s*\|\|\s*data\.url/, "checkout should accept Creem checkout_url, checkoutUrl, or url");
assert.match(checkout, /success_url/, "checkout should send Creem API snake_case success_url");
assert.match(checkout, /referenceId/, "checkout metadata should carry the Supabase user id");

assert.match(webhook, /refund\.created/, "webhook should treat refunds as access-relevant events");
assert.match(webhook, /dispute\.created/, "webhook should treat disputes as access-relevant events");
assert.match(webhook, /creem_order_id/, "webhook should persist order id for support");
assert.match(webhook, /creem_last_event_id/, "webhook should persist last processed event id on profiles");

assert.match(envExample, /CREEM_API_KEY=creem_YOUR_LIVE_KEY/, "env example should show live Creem key now that production is approved");
assert.match(envExample, /CREEM_TEST_MODE=false/, "env example should default the approved channel to live mode");
assert.match(envExample, /CREEM_LIFETIME_PRODUCT_ID=prod_YOUR_12_USD_LIFETIME_PRODUCT/, "env example should mention the US$12 lifetime product");

assert.match(readme, /CREEM_TEST_MODE=false/, "README should document live-mode secrets");
assert.match(readme, /US\$12/, "README should use the current US$12 price");
assert.match(readme, /refund\.created/, "README should document refund webhook handling");
assert.match(readme, /dispute\.created/, "README should document dispute webhook handling");

assert.match(deploy, /Creem environment\? live\/test/, "deploy helper should ask for live/test environment, not a raw boolean");
assert.match(deploy, /project-flow-delta\.vercel\.app/, "deploy helper should keep the app callback URL configured");

console.log("Creem integration verification passed.");
