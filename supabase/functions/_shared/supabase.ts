import { createClient } from "https://esm.sh/@supabase/supabase-js@2.45.4";

export function adminClient() {
  const url = Deno.env.get("SUPABASE_URL");
  const key = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");
  if (!url || !key) throw new Error("Missing Supabase service role configuration");
  return createClient(url, key, {
    auth: { persistSession: false },
  });
}

export async function getUserFromRequest(req: Request) {
  const authHeader = req.headers.get("Authorization") || "";
  const token = authHeader.replace(/^Bearer\s+/i, "");
  if (!token) return { user: null, error: "Missing Authorization header" };

  const supabase = adminClient();
  const { data, error } = await supabase.auth.getUser(token);
  if (error || !data.user) return { user: null, error: error?.message || "Invalid session" };
  return { user: data.user, error: null };
}
