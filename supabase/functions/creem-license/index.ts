import { adminClient, getUserFromRequest } from "../_shared/supabase.ts";
import { json, okOptions } from "../_shared/cors.ts";

const CREEM_TEST_API = "https://test-api.creem.io";
const CREEM_LIVE_API = "https://api.creem.io";

async function sha256Hex(input: string) {
  const data = new TextEncoder().encode(input);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return okOptions();
  if (req.method !== "POST") return json({ error: "Method not allowed" }, { status: 405 });

  const { user, error } = await getUserFromRequest(req);
  if (!user) return json({ error }, { status: 401 });

  const body = await req.json().catch(() => ({}));
  const key = String(body.key || "").trim();
  if (!key) return json({ error: "License key is required" }, { status: 400 });

  const apiKey = Deno.env.get("CREEM_API_KEY");
  const testMode = (Deno.env.get("CREEM_TEST_MODE") || "true").toLowerCase() !== "false";
  if (!apiKey) return json({ error: "Creem is not configured" }, { status: 500 });

  const base = testMode ? CREEM_TEST_API : CREEM_LIVE_API;
  const instanceName = `Project Flow user ${user.id}`;
  const activateResponse = await fetch(`${base}/v1/licenses/activate`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": apiKey,
    },
    body: JSON.stringify({ key, instance_name: instanceName }),
  });

  const activation = await activateResponse.json().catch(() => ({}));
  if (!activateResponse.ok) {
    return json({ error: "License activation failed", details: activation }, { status: 400 });
  }

  const status = activation.status || activation.license?.status || "active";
  if (!["active", "trialing"].includes(status)) {
    return json({ error: "License is not active", status, details: activation }, { status: 400 });
  }

  const instanceId = activation.instance?.id || activation.instance_id || null;
  const supabase = adminClient();
  const { error: updateError } = await supabase
    .from("profiles")
    .update({
      plan: "lifetime",
      lifetime_unlocked_at: new Date().toISOString(),
      creem_license_key_hash: await sha256Hex(key),
      creem_license_instance_id: instanceId,
    })
    .eq("id", user.id);

  if (updateError) return json({ error: updateError.message }, { status: 400 });

  return json({
    ok: true,
    plan: "lifetime",
    instanceId,
  });
});
