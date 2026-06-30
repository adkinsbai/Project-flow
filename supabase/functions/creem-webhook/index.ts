import { adminClient } from "../_shared/supabase.ts";
import { json, okOptions } from "../_shared/cors.ts";

async function hmacSha256Hex(secret: string, payload: string) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const signature = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload));
  return Array.from(new Uint8Array(signature)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function safeEqual(a: string, b: string) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

function findReferenceId(object: Record<string, unknown>) {
  const checkout = (object.checkout || {}) as Record<string, unknown>;
  const order = (object.order || {}) as Record<string, unknown>;
  const metadata = (object.metadata || checkout.metadata || order.metadata || {}) as Record<string, unknown>;
  return String(metadata.referenceId || metadata.reference_id || metadata.userId || "");
}

function findCustomerId(object: Record<string, unknown>) {
  const customer = object.customer as Record<string, unknown> | undefined;
  return String(object.customer_id || customer?.id || "");
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return okOptions();
  if (req.method !== "POST") return json({ error: "Method not allowed" }, { status: 405 });

  const secret = Deno.env.get("CREEM_WEBHOOK_SECRET");
  if (!secret) return json({ error: "Webhook secret is not configured" }, { status: 500 });

  const rawBody = await req.text();
  const signature = req.headers.get("creem-signature") || "";
  const expected = await hmacSha256Hex(secret, rawBody);
  if (!signature || !safeEqual(signature, expected)) {
    return json({ error: "Invalid signature" }, { status: 401 });
  }

  const event = JSON.parse(rawBody);
  const eventId = String(event.id || `${event.eventType}-${event.created_at || Date.now()}`);
  const eventType = String(event.eventType || event.type || "");
  const object = (event.object || {}) as Record<string, unknown>;

  const supabase = adminClient();
  const { error: insertError } = await supabase
    .from("creem_events")
    .insert({ id: eventId, event_type: eventType, payload: event })
    .select("id")
    .single();

  if (insertError && !insertError.message.includes("duplicate key")) {
    return json({ error: insertError.message }, { status: 400 });
  }
  if (insertError?.message.includes("duplicate key")) {
    return json({ ok: true, duplicate: true });
  }

  const grantEvents = new Set(["checkout.completed", "subscription.active", "subscription.trialing", "subscription.paid"]);
  const revokeEvents = new Set(["subscription.expired", "subscription.paused"]);
  const referenceId = findReferenceId(object);

  if (referenceId && grantEvents.has(eventType)) {
    const { error } = await supabase
      .from("profiles")
      .update({
        plan: "lifetime",
        lifetime_unlocked_at: new Date().toISOString(),
        creem_customer_id: findCustomerId(object) || null,
      })
      .eq("id", referenceId);
    if (error) return json({ error: error.message }, { status: 400 });
  }

  if (referenceId && revokeEvents.has(eventType)) {
    const { error } = await supabase
      .from("profiles")
      .update({
        plan: "trial",
        lifetime_unlocked_at: null,
      })
      .eq("id", referenceId)
      .is("creem_license_key_hash", null);
    if (error) return json({ error: error.message }, { status: 400 });
  }

  return json({ ok: true });
});
