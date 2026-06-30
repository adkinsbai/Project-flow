import { adminClient, getUserFromRequest } from "../_shared/supabase.ts";
import { json, okOptions } from "../_shared/cors.ts";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return okOptions();

  const { user, error } = await getUserFromRequest(req);
  if (!user) return json({ error }, { status: 401 });

  const supabase = adminClient();

  if (req.method === "PATCH") {
    const body = await req.json().catch(() => ({}));
    const patch: Record<string, unknown> = {};
    if (typeof body.hasSeenGuide === "boolean") patch.has_seen_guide = body.hasSeenGuide;
    if (typeof body.displayName === "string") patch.display_name = body.displayName.trim();

    if (Object.keys(patch).length) {
      const { error: updateError } = await supabase
        .from("profiles")
        .update(patch)
        .eq("id", user.id);
      if (updateError) return json({ error: updateError.message }, { status: 400 });
    }
  }

  const { data: profile, error: profileError } = await supabase
    .from("profiles")
    .select("*")
    .eq("id", user.id)
    .single();

  if (profileError) return json({ error: profileError.message }, { status: 400 });

  const now = Date.now();
  const trialEndsAt = profile.trial_ends_at ? new Date(profile.trial_ends_at).getTime() : 0;
  const hasLifetime = profile.plan === "lifetime";
  const trialActive = !hasLifetime && trialEndsAt > now;

  return json({
    user: {
      id: user.id,
      email: user.email,
      displayName: profile.display_name,
    },
    profile: {
      hasSeenGuide: profile.has_seen_guide,
      plan: profile.plan,
      trialStartedAt: profile.trial_started_at,
      trialEndsAt: profile.trial_ends_at,
      lifetimeUnlockedAt: profile.lifetime_unlocked_at,
      creemCustomerId: profile.creem_customer_id,
    },
    entitlement: {
      active: hasLifetime || trialActive,
      plan: hasLifetime ? "lifetime" : "trial",
      trialActive,
      hasLifetime,
      daysLeft: hasLifetime ? null : Math.max(0, Math.ceil((trialEndsAt - now) / 86400000)),
    },
  });
});
