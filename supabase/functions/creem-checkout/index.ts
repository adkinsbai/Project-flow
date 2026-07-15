import { adminClient, getUserFromRequest } from "../_shared/supabase.ts";
import { json, okOptions } from "../_shared/cors.ts";

const CREEM_TEST_API = "https://test-api.creem.io";
const CREEM_LIVE_API = "https://api.creem.io";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return okOptions();
  if (req.method !== "POST") return json({ error: "Method not allowed" }, { status: 405 });

  const { user, error } = await getUserFromRequest(req);
  if (!user) return json({ error }, { status: 401 });

  const apiKey = Deno.env.get("CREEM_API_KEY");
  const productId = Deno.env.get("CREEM_LIFETIME_PRODUCT_ID");
  const appUrl = Deno.env.get("APP_URL") || "https://project-flow-delta.vercel.app/";
  const testMode = (Deno.env.get("CREEM_TEST_MODE") || "true").toLowerCase() !== "false";

  if (!apiKey || !productId) {
    return json({ error: "Creem is not configured" }, { status: 500 });
  }

  const supabase = adminClient();
  const { data: profile } = await supabase
    .from("profiles")
    .select("creem_customer_id")
    .eq("id", user.id)
    .single();

  const successUrl = `${appUrl.replace(/\/$/, "")}/?payment=success`;
  const checkoutBody = {
    product_id: productId,
    success_url: successUrl,
    customer: {
      email: user.email,
    },
    metadata: {
      referenceId: user.id,
      source: "project-flow",
    },
    ...(profile?.creem_customer_id ? { customer_id: profile.creem_customer_id } : {}),
  };

  const response = await fetch(`${testMode ? CREEM_TEST_API : CREEM_LIVE_API}/v1/checkouts`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
    },
    body: JSON.stringify(checkoutBody),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    return json({ error: "Creem checkout failed", details: data }, { status: response.status });
  }

  const checkoutUrl = data.checkout_url || data.checkoutUrl || data.url;
  if (!checkoutUrl) {
    return json({ error: "Creem did not return a checkout URL", details: data }, { status: 502 });
  }

  return json({
    checkoutUrl,
    checkout: data,
  });
});
