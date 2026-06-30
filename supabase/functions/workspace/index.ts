import { adminClient, getUserFromRequest } from "../_shared/supabase.ts";
import { json, okOptions } from "../_shared/cors.ts";

const WORKSPACE_TITLE = "Project Flow Workspace";

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return okOptions();

  const { user, error } = await getUserFromRequest(req);
  if (!user) return json({ error }, { status: 401 });

  const supabase = adminClient();

  if (req.method === "GET") {
    const { data, error: selectError } = await supabase
      .from("projects")
      .select("id,title,data,schema_version,updated_at")
      .eq("user_id", user.id)
      .is("deleted_at", null)
      .order("updated_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (selectError) return json({ error: selectError.message }, { status: 400 });
    return json({ workspace: data || null });
  }

  if (req.method === "PUT") {
    const body = await req.json().catch(() => ({}));
    const data = body.data;
    if (!data || typeof data !== "object") return json({ error: "Workspace data is required" }, { status: 400 });

    const { data: existing, error: existingError } = await supabase
      .from("projects")
      .select("id")
      .eq("user_id", user.id)
      .is("deleted_at", null)
      .order("updated_at", { ascending: false })
      .limit(1)
      .maybeSingle();

    if (existingError) return json({ error: existingError.message }, { status: 400 });

    if (existing?.id) {
      const { data: updated, error: updateError } = await supabase
        .from("projects")
        .update({ title: body.title || WORKSPACE_TITLE, data, schema_version: 1 })
        .eq("id", existing.id)
        .eq("user_id", user.id)
        .select("id,title,data,schema_version,updated_at")
        .single();
      if (updateError) return json({ error: updateError.message }, { status: 400 });
      return json({ workspace: updated });
    }

    const { data: created, error: insertError } = await supabase
      .from("projects")
      .insert({ user_id: user.id, title: body.title || WORKSPACE_TITLE, data, schema_version: 1 })
      .select("id,title,data,schema_version,updated_at")
      .single();

    if (insertError) return json({ error: insertError.message }, { status: 400 });
    return json({ workspace: created });
  }

  return json({ error: "Method not allowed" }, { status: 405 });
});
