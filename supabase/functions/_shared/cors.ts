export const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type, creem-signature",
  "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, OPTIONS",
};

export function json(data: unknown, init: ResponseInit = {}) {
  return new Response(JSON.stringify(data), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...corsHeaders,
      ...(init.headers || {}),
    },
  });
}

export function okOptions() {
  return new Response("ok", { headers: corsHeaders });
}
