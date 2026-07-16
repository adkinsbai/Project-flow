# Freemium Entitlement Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the expiring trial gate with a server-authoritative Free/Pro entitlement foundation, Planned/Ongoing node lifecycle, a 12-ongoing Free limit, theme access rules, and privacy-safe product analytics.

**Architecture:** Supabase remains the authority for plans and limits. Shared Edge Function helpers compute entitlement and enforce the ongoing limit on every workspace write; browser helpers mirror the contract only for immediate UX. The static web and desktop HTML surfaces load the same `app/*.js` modules, and Node tests execute those exact browser modules through `vm`.

**Tech Stack:** Supabase PostgreSQL, Supabase Edge Functions/Deno TypeScript, React 18 UMD, browser JavaScript, Node 24 tests, Vercel static deployment, Electron desktop shell.

## Global Constraints

- Free has at most 12 nodes whose normalized status is `ongoing` across the workspace.
- Legacy `active` status normalizes to `ongoing`; `planned` and `done` do not consume ongoing capacity.
- Free receives two AI generations per usage period, but AI invocation is outside this plan.
- Pro plan keys are `pro_monthly`, `pro_quarterly`, and `pro_annual`.
- Existing `lifetime` users migrate to `legacy_lifetime` and keep core Pro access.
- Downgrade never deletes or hides workspace data.
- A user above the Free limit may save edits, completions, and deletions, but may not increase the ongoing count.
- Analytics must never include project titles, node titles, descriptions, email addresses, or workspace payloads.
- `index.html` and `project-flow.html` must remain byte-identical after each frontend task.
- `output/`, `tmp/`, `.env*`, and design documents remain excluded from Vercel uploads.

---

## File Map

- `supabase/migrations/20260716000000_freemium_entitlements.sql`: schema migration, legacy mapping, plan catalog, analytics event storage, RLS, and entitlement-field protection.
- `supabase/functions/_shared/entitlement.ts`: plan types, status normalization, ongoing counting, and authoritative entitlement computation.
- `scripts/entitlement-edge.test.mjs`: Node 24 unit tests importing the pure TypeScript entitlement helper.
- `supabase/functions/me/index.ts`: returns the new entitlement contract.
- `supabase/functions/workspace/index.ts`: enforces the authoritative ongoing limit before workspace writes.
- `supabase/functions/events/index.ts`: authenticated, allowlisted, content-free analytics ingestion.
- `app/entitlement.js`: browser normalization and plan presentation helpers.
- `app/limits.js`: exact client-side ongoing counting and creation checks.
- `app/analytics.js`: small authenticated event queue that sends only allowlisted metadata.
- `scripts/verify-entitlement-foundation.mjs`: executes the exact browser modules and asserts the contract.
- `scripts/verify-ui-sync-copy.mjs`: verifies both formal HTML files load shared modules and remain aligned.
- `index.html`: node lifecycle, creation gates, account/status UI, theme preview, analytics events.
- `project-flow.html`: mechanical copy of `index.html` after frontend changes.
- `scripts/deploy-supabase.ps1`: deploys the new `events` function with existing backend functions.
- `package.json`: adds focused verification commands.
- `.gitignore`: keeps local application forms, PDFs, and temporary render artifacts out of commits.

---

### Task 1: Add the Freemium Schema and Plan Catalog

**Files:**
- Create: `supabase/migrations/20260716000000_freemium_entitlements.sql`
- Modify: `.gitignore`
- Test: `supabase/migrations/20260716000000_freemium_entitlements.sql`

**Interfaces:**
- Produces: `profiles.plan`, subscription fields, `plan_catalog`, and `product_events` consumed by all later tasks.
- Preserves: every current `lifetime` profile as `legacy_lifetime`; every current `trial` profile becomes `free`.

- [ ] **Step 1: Write the migration with assertions that initially fail in a transaction**

Append a verification block to the migration that raises when required rows are missing:

```sql
do $$
begin
  if not exists (select 1 from public.plan_catalog where plan_key = 'free' and ongoing_limit = 12) then
    raise exception 'free plan seed missing';
  end if;
  if not exists (select 1 from public.plan_catalog where plan_key = 'legacy_lifetime') then
    raise exception 'legacy lifetime seed missing';
  end if;
end;
$$;
```

- [ ] **Step 2: Implement the complete migration**

Use this schema shape:

```sql
alter table public.profiles drop constraint if exists profiles_plan_check;

alter table public.profiles
  add column if not exists subscription_status text not null default 'inactive',
  add column if not exists subscription_provider text,
  add column if not exists subscription_product_id text,
  add column if not exists subscription_id text,
  add column if not exists current_period_start timestamptz,
  add column if not exists current_period_end timestamptz,
  add column if not exists cancel_at_period_end boolean not null default false,
  add column if not exists ai_period_start timestamptz,
  add column if not exists ai_period_end timestamptz,
  add column if not exists ai_used integer not null default 0 check (ai_used >= 0),
  add column if not exists legacy_lifetime boolean not null default false;

update public.profiles
set legacy_lifetime = true,
    plan = 'legacy_lifetime',
    subscription_status = 'active'
where plan = 'lifetime';

update public.profiles
set plan = 'free', subscription_status = 'inactive'
where plan = 'trial';

alter table public.profiles
  add constraint profiles_plan_check
  check (plan in ('free','pro_monthly','pro_quarterly','pro_annual','legacy_lifetime'));

create table if not exists public.plan_catalog (
  plan_key text primary key,
  creem_product_id text unique,
  billing_period text check (billing_period in ('month','quarter','year','lifetime') or billing_period is null),
  price_usd numeric(10,2) not null default 0,
  ongoing_limit integer check (ongoing_limit is null or ongoing_limit >= 0),
  ai_monthly_limit integer check (ai_monthly_limit is null or ai_monthly_limit >= 0),
  theme_access text[] not null default '{}',
  active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

insert into public.plan_catalog
  (plan_key,billing_period,price_usd,ongoing_limit,ai_monthly_limit,theme_access)
values
  ('free',null,0,12,2,array['dark']),
  ('pro_monthly','month',12,null,null,array['all']),
  ('pro_quarterly','quarter',32.40,null,null,array['all']),
  ('pro_annual','year',115.20,null,null,array['all']),
  ('legacy_lifetime','lifetime',0,null,2,array['all'])
on conflict (plan_key) do update set
  billing_period = excluded.billing_period,
  price_usd = excluded.price_usd,
  ongoing_limit = excluded.ongoing_limit,
  ai_monthly_limit = excluded.ai_monthly_limit,
  theme_access = excluded.theme_access,
  updated_at = now();

create table if not exists public.product_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  event_name text not null,
  session_id text not null,
  properties jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists product_events_user_created_idx
on public.product_events(user_id, created_at desc);

alter table public.plan_catalog enable row level security;
alter table public.product_events enable row level security;
```

Update `protect_profile_entitlement_fields()` so authenticated clients cannot alter any new subscription, AI quota, or legacy fields. Do not create a direct client insert policy for `product_events`; the `events` Edge Function writes with the service role.

- [ ] **Step 3: Validate migration syntax against the linked project without applying it**

Run:

```powershell
& "$env:USERPROFILE\.local\supabase-cli\v2.108.0\supabase.exe" db lint --linked
```

Expected: no SQL errors involving `20260716000000_freemium_entitlements.sql`.

- [ ] **Step 4: Ignore local non-product artifacts**

Append:

```gitignore
output/
tmp/
```

Confirm `git check-ignore output tmp` prints both paths.

- [ ] **Step 5: Commit**

```powershell
git add supabase/migrations/20260716000000_freemium_entitlements.sql .gitignore
git commit -m "Add freemium entitlement schema"
```

---

### Task 2: Create the Authoritative Entitlement Helper

**Files:**
- Create: `supabase/functions/_shared/entitlement.ts`
- Create: `scripts/entitlement-edge.test.mjs`

**Interfaces:**
- Produces: `normalizeNodeStatus(status)`, `countOngoingNodes(data)`, and `computeEntitlement(profile, plan, ongoingUsed, now)`.
- Consumed by: `me`, `workspace`, and later AI/billing functions.

- [ ] **Step 1: Write failing Node 24 tests**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { computeEntitlement, countOngoingNodes, normalizeNodeStatus } from "../supabase/functions/_shared/entitlement.ts";

test("legacy active nodes count as ongoing", () => {
  assert.equal(normalizeNodeStatus("active"), "ongoing");
  assert.equal(countOngoingNodes({ nodes: {
    n1: { status: "active" },
    n2: { status: "planned" },
    n3: { status: "done" },
  }}), 1);
});

test("free entitlement exposes exact limits", () => {
  const value = computeEntitlement(
    { plan: "free", subscription_status: "inactive", cancel_at_period_end: false, ai_used: 1 },
    { plan_key: "free", ongoing_limit: 12, ai_monthly_limit: 2, theme_access: ["dark"] },
    5,
    new Date("2026-07-16T00:00:00Z"),
  );
  assert.equal(value.isPro, false);
  assert.equal(value.ongoingLimit, 12);
  assert.equal(value.ongoingUsed, 5);
  assert.equal(value.aiRemaining, 1);
});

test("legacy lifetime keeps core pro access", () => {
  const value = computeEntitlement(
    { plan: "legacy_lifetime", subscription_status: "active", legacy_lifetime: true, ai_used: 0 },
    { plan_key: "legacy_lifetime", ongoing_limit: null, ai_monthly_limit: 2, theme_access: ["all"] },
    50,
    new Date("2026-07-16T00:00:00Z"),
  );
  assert.equal(value.isPro, true);
  assert.equal(value.ongoingLimit, null);
});
```

- [ ] **Step 2: Run tests and confirm red**

Run:

Run: `node --test scripts/entitlement-edge.test.mjs`

Expected: failure because `entitlement.ts` does not exist.

- [ ] **Step 3: Implement the helper**

The returned contract must be:

```ts
export type Entitlement = {
  plan: "free" | "pro_monthly" | "pro_quarterly" | "pro_annual" | "legacy_lifetime";
  isPro: boolean;
  subscriptionStatus: string;
  currentPeriodEnd: string | null;
  cancelAtPeriodEnd: boolean;
  ongoingLimit: number | null;
  ongoingUsed: number;
  ongoingRemaining: number | null;
  aiMonthlyLimit: number | null;
  aiUsed: number;
  aiRemaining: number | null;
  aiPeriodEnd: string | null;
  availableThemes: string[];
};
```

Implement `countOngoingNodes` with `status === "ongoing" || status === "active"`. `planned`, `done`, and `ghost` do not count. `computeEntitlement` treats all three `pro_*` plans and `legacy_lifetime` as Pro; Free is never expired or locked.

- [ ] **Step 4: Run tests and confirm green**

Run: `node --test scripts/entitlement-edge.test.mjs`

Expected: three passing tests.

- [ ] **Step 5: Commit**

```powershell
git add supabase/functions/_shared/entitlement.ts scripts/entitlement-edge.test.mjs
git commit -m "Add authoritative entitlement computation"
```

---

### Task 3: Return Entitlement from `me` and Enforce It in `workspace`

**Files:**
- Modify: `supabase/functions/me/index.ts`
- Modify: `supabase/functions/workspace/index.ts`
- Create: `scripts/verify-edge-entitlement-contract.mjs`
- Modify: `package.json`

**Interfaces:**
- Consumes: `computeEntitlement()` and `countOngoingNodes()` from Task 2.
- Produces: `GET /me` entitlement contract and `ONGOING_LIMIT_REACHED` workspace error.

- [ ] **Step 1: Write a failing source-contract test**

Create a Node test that reads both Edge Function sources and asserts:

```js
assert.match(meSource, /computeEntitlement/);
assert.match(meSource, /plan_catalog/);
assert.match(workspaceSource, /ONGOING_LIMIT_REACHED/);
assert.match(workspaceSource, /newOngoing > oldOngoing/);
```

Add `"verify:edge-entitlement": "node scripts/verify-edge-entitlement-contract.mjs"` to `package.json`.

- [ ] **Step 2: Run and confirm red**

Run: `npm run verify:edge-entitlement`

Expected: failure because the functions still return the old trial/lifetime contract.

- [ ] **Step 3: Update `me`**

Load the profile, latest workspace data, and matching plan catalog row. Return:

```ts
const entitlement = computeEntitlement(
  profile,
  planCatalog,
  countOngoingNodes(workspace?.data),
  new Date(),
);

return json({
  user: { id: user.id, email: user.email, displayName: profile.display_name },
  profile: {
    hasSeenGuide: profile.has_seen_guide,
    plan: profile.plan,
    subscriptionStatus: profile.subscription_status,
  },
  entitlement,
});
```

Remove the trial-active lock calculation from `me`; legacy response fields may remain for one release only if the old frontend still reads them.

- [ ] **Step 4: Enforce the limit in `workspace`**

Before update/insert, compute:

```ts
const oldOngoing = countOngoingNodes(existing?.data);
const newOngoing = countOngoingNodes(data);
const entitlement = computeEntitlement(profile, planCatalog, oldOngoing, new Date());

if (
  entitlement.ongoingLimit !== null
  && newOngoing > entitlement.ongoingLimit
  && newOngoing > oldOngoing
) {
  return json({
    error: "Free supports at most 12 ongoing tasks",
    code: "ONGOING_LIMIT_REACHED",
    entitlement: { ...entitlement, ongoingUsed: oldOngoing },
  }, { status: 403 });
}
```

The existing workspace select must include `data`, not only `id`, so reductions above the limit remain savable.

- [ ] **Step 5: Run focused and existing tests**

Run:

```powershell
npm run verify:edge-entitlement
npm run verify:merge
npm run verify:creem
```

Expected: all pass.

- [ ] **Step 6: Commit**

```powershell
git add supabase/functions/me/index.ts supabase/functions/workspace/index.ts scripts/verify-edge-entitlement-contract.mjs package.json
git commit -m "Enforce freemium workspace limits"
```

---

### Task 4: Add Shared Browser Entitlement and Limit Modules

**Files:**
- Create: `app/entitlement.js`
- Create: `app/limits.js`
- Create: `scripts/verify-entitlement-foundation.mjs`
- Modify: `package.json`

**Interfaces:**
- Produces: `window.PFEntitlement.normalize(raw)`, `window.PFEntitlement.label(value)`, `window.PFLimits.normalizeWorkspace(data)`, `countOngoing(nodes)`, and `canIncreaseOngoing(nodes, addition, entitlement)`.
- Consumed by: the formal app HTML in Tasks 5 and 6.

- [ ] **Step 1: Write the failing VM test**

Load the exact browser files through `vm.runInNewContext` and assert:

```js
assert.equal(PFLimits.countOngoing({
  n1: { status: "active" },
  n2: { status: "planned" },
  n3: { status: "done" },
}), 1);

assert.equal(PFLimits.canIncreaseOngoing(
  Object.fromEntries(Array.from({ length: 12 }, (_, i) => [`n${i}`, { status: "ongoing" }])),
  1,
  { ongoingLimit: 12 },
).allowed, false);

assert.equal(PFEntitlement.label({ plan: "legacy_lifetime" }), "Lifetime");
```

- [ ] **Step 2: Run and confirm red**

Run: `node scripts/verify-entitlement-foundation.mjs`

Expected: failure because the browser modules do not exist.

- [ ] **Step 3: Implement the browser modules**

Use IIFEs with no build dependency:

```js
(function (root) {
  function label(value) {
    if (value.plan === 'legacy_lifetime') return 'Lifetime';
    if (value.isPro) return 'Pro';
    return 'Free';
  }
  function normalize(raw) {
    var value = raw || {};
    return {
      plan: value.plan || 'free',
      isPro: !!value.isPro,
      ongoingLimit: value.ongoingLimit == null ? null : Number(value.ongoingLimit),
      ongoingUsed: Number(value.ongoingUsed || 0),
      aiMonthlyLimit: value.aiMonthlyLimit == null ? null : Number(value.aiMonthlyLimit),
      aiUsed: Number(value.aiUsed || 0),
      availableThemes: Array.isArray(value.availableThemes) ? value.availableThemes : ['dark']
    };
  }
  root.PFEntitlement = { normalize: normalize, label: label };
})(window);
```

`app/limits.js` must normalize `active` to `ongoing` without mutating the supplied object and return `{ allowed, used, limit, remaining }` from creation checks.

- [ ] **Step 4: Run and confirm green**

Run: `node scripts/verify-entitlement-foundation.mjs`

Expected: pass.

- [ ] **Step 5: Add the npm command and commit**

Add `"verify:entitlement": "node scripts/verify-entitlement-foundation.mjs"`, then:

```powershell
git add app/entitlement.js app/limits.js scripts/verify-entitlement-foundation.mjs package.json
git commit -m "Add shared freemium browser rules"
```

---

### Task 5: Introduce Planned/Ongoing and Gate Every Creation Path

**Files:**
- Modify: `index.html`
- Modify: `project-flow.html`
- Modify: `scripts/verify-ui-sync-copy.mjs`

**Interfaces:**
- Consumes: `window.PFLimits` and `profileBundle.entitlement`.
- Produces: Planned node UI, Start action, limit modal, and guarded creation functions.

- [ ] **Step 1: Extend the UI verification so it fails**

Require both HTML files to include:

```js
assert.match(html, /\.\/app\/entitlement\.js/);
assert.match(html, /\.\/app\/limits\.js/);
assert.match(html, /status:'planned'/);
assert.match(html, /ONGOING_LIMIT_REACHED/);
assert.ok(!html.includes('试用已结束'));
```

- [ ] **Step 2: Run and confirm red**

Run: `npm run verify:ui-sync`

Expected: failure on missing shared modules and Planned lifecycle.

- [ ] **Step 3: Load shared modules and normalize saved data**

Add before Babel:

```html
<script src="./app/entitlement.js"></script>
<script src="./app/limits.js"></script>
```

When local or cloud data loads, call `PFLimits.normalizeWorkspace(data)` so legacy `active` nodes become `ongoing` in memory and are persisted on the next save.

- [ ] **Step 4: Add one creation guard and use it everywhere**

Inside `App`, implement:

```jsx
const entitlementView = PFEntitlement.normalize(profileBundle?.entitlement);
const checkOngoingCapacity = useCallback((addition=1, source='manual') => {
  const result = PFLimits.canIncreaseOngoing(nodesRef.current, addition, entitlementView);
  if (!result.allowed) {
    setLimitNotice({ source, used: result.used, limit: result.limit });
  }
  return result.allowed;
}, [entitlementView]);
```

Call it before mutation in `addRoot`, `confirmInput`, Planned `Start`, and legacy text-workflow acceptance. For parsed workflows, create the root as `ongoing` and descendants as `planned`; block only when the root itself cannot fit.

- [ ] **Step 5: Add Planned rendering and Start action**

Planned cards use muted styling and display `Planned`. The node menu shows `Start` for Planned nodes. Starting calls the same capacity guard, then sets `{ status: 'ongoing', updatedAt: now() }`.

`Done` continues to work for Ongoing nodes. Continue and Branch create Ongoing nodes and therefore use the guard.

- [ ] **Step 6: Replace the expiry overlay with the limit notice**

Remove `LockedOverlay`. The limit notice copy is:

```text
你正在同时推进 12 个任务
完成一个现有任务即可继续创建；升级 Pro 后可同时推进不限数量的任务。
```

Actions call `focusNextTask` and open the upgrade/account surface.

- [ ] **Step 7: Copy the formal app mechanically and verify**

```powershell
Copy-Item -LiteralPath index.html -Destination project-flow.html -Force
npm run verify:ui-sync
npm run verify:entitlement
npm run verify:merge
```

Expected: all pass and SHA-256 hashes of the HTML files match.

- [ ] **Step 8: Commit**

```powershell
git add index.html project-flow.html scripts/verify-ui-sync-copy.mjs
git commit -m "Add planned work and Free ongoing limit"
```

---

### Task 6: Show Plan Status and Gate Theme Persistence

**Files:**
- Modify: `index.html`
- Modify: `project-flow.html`
- Modify: `scripts/verify-ui-sync-copy.mjs`

**Interfaces:**
- Consumes: normalized entitlement from Task 4.
- Produces: `Free - x/12 ongoing`, `Pro`, or `Lifetime` status and preview-only Pro themes for Free users.

- [ ] **Step 1: Write failing UI contract checks**

```js
assert.match(html, /Free.*ongoing/);
assert.match(html, /升级 Pro/);
assert.match(html, /theme-preview/);
assert.ok(!html.includes('Update Pro'));
```

- [ ] **Step 2: Run and confirm red**

Run: `npm run verify:ui-sync`

Expected: failure on old `Update Pro` and absent plan status.

- [ ] **Step 3: Implement the compact status**

Display:

```jsx
<button className={`plan-pill ${ongoingUsed >= 9 ? 'warn' : ''}`} onClick={()=>setAccountOpen(true)}>
  {entitlementView.plan === 'free'
    ? `Free · ${ongoingUsed}/${entitlementView.ongoingLimit} ongoing`
    : entitlementView.plan === 'legacy_lifetime' ? 'Lifetime' : 'Pro'}
</button>
```

Rename every upgrade command to `升级 Pro`. Account status must show plan and renewal/cancellation fields from the entitlement contract without calculating dates on the client.

- [ ] **Step 4: Implement theme preview**

Free users may click a locked theme to preview it for the current session. Do not write the locked theme to `localStorage`. Show a small persistent preview bar with `恢复默认` and `升级 Pro`. Pro and Lifetime persist all themes normally.

- [ ] **Step 5: Verify, copy, and commit**

```powershell
Copy-Item -LiteralPath index.html -Destination project-flow.html -Force
npm run verify:ui-sync
npm run verify:entitlement
git add index.html project-flow.html scripts/verify-ui-sync-copy.mjs
git commit -m "Show plan status and Pro theme previews"
```

---

### Task 7: Add Privacy-Safe Product Analytics

**Files:**
- Create: `supabase/functions/events/index.ts`
- Create: `app/analytics.js`
- Create: `scripts/verify-product-analytics.mjs`
- Modify: `index.html`
- Modify: `project-flow.html`
- Modify: `scripts/deploy-supabase.ps1`
- Modify: `package.json`

**Interfaces:**
- Produces: `POST /events` and `window.PFAnalytics.track(name, properties)`.
- Consumes: the existing authenticated `apiCall()` transport.

- [ ] **Step 1: Write failing analytics safety checks**

The test reads the Edge Function and browser module and asserts an exact allowlist:

```js
const allowed = [
  'app_loaded','entitlement_loaded','node_created','node_started',
  'node_completed','ongoing_limit_seen','upgrade_viewed'
];
for (const name of allowed) assert.match(edgeSource, new RegExp(name));
for (const forbidden of ['title','description','email','workspace']) {
  assert.doesNotMatch(browserSource, new RegExp(`properties\\.${forbidden}`));
}
```

- [ ] **Step 2: Implement the authenticated Edge Function**

Accept only POST, authenticate with `getUserFromRequest`, reject event names outside the allowlist, require a 16-80 character `sessionId`, and retain only scalar properties named `source`, `used`, `limit`, `plan`, and `surface`. Insert with `adminClient()` into `product_events`.

- [ ] **Step 3: Implement the browser queue**

`app/analytics.js` creates a random session ID in `sessionStorage`, queues at most 50 events, and calls a transport registered by the app:

```js
PFAnalytics.setTransport(function (event) {
  return apiCall('events', { method: 'POST', body: event });
});
```

Failure drops no product data and retries only during the current session with exponential delays capped at 30 seconds.

- [ ] **Step 4: Track the first seven events**

Add calls at authenticated load, entitlement load, successful node creation/start/completion, limit display, and upgrade-surface open. Never pass titles or descriptions.

- [ ] **Step 5: Add deployment and verification commands**

Add `events` to `$functions` in `scripts/deploy-supabase.ps1`. Add `"verify:analytics": "node scripts/verify-product-analytics.mjs"` to `package.json`.

- [ ] **Step 6: Verify, copy, and commit**

```powershell
Copy-Item -LiteralPath index.html -Destination project-flow.html -Force
npm run verify:analytics
npm run verify:ui-sync
git add supabase/functions/events/index.ts app/analytics.js scripts/verify-product-analytics.mjs index.html project-flow.html scripts/deploy-supabase.ps1 package.json
git commit -m "Track privacy-safe activation events"
```

---

### Task 8: Run Full Verification, Migrate, Deploy, and Perform UAT

**Files:**
- Modify only if verification finds a scoped defect in files from Tasks 1-7.

**Interfaces:**
- Consumes: all prior tasks.
- Produces: linked Supabase schema/functions and a Vercel production deployment tied to the final Git commit.

- [ ] **Step 1: Run the complete local verification suite**

```powershell
npm run verify:entitlement
npm run verify:edge-entitlement
npm run verify:analytics
npm run verify:merge
npm run verify:creem
npm run verify:ui-sync
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 2: Verify repository hygiene**

```powershell
git status --short
git check-ignore output tmp .env
```

Expected: no source changes are unstaged; local business artifacts and secrets are not included in deployment or commits.

- [ ] **Step 3: Apply the Supabase migration and deploy functions**

Run the existing secure deployment helper:

```powershell
.\scripts\deploy-supabase.ps1 -ProjectRef pksjwrajpyobkzxlqmrz -AppUrl https://project-flow-delta.vercel.app/
```

Expected: database push succeeds and `me`, `workspace`, `events`, and existing Creem functions deploy. Do not expose secret values in logs or commits.

- [ ] **Step 4: Run authenticated API smoke tests**

Using a disposable test account token, verify:

```text
GET /functions/v1/me -> plan=free, ongoingLimit=12
PUT workspace with 12 ongoing -> 200
PUT workspace increasing 12 to 13 ongoing -> 403, code=ONGOING_LIMIT_REACHED
PUT workspace reducing 13 to 12 ongoing -> 200
POST /events with node_completed and scalar properties -> 200
POST /events with unknown name -> 400
```

Delete the disposable test account after verification.

- [ ] **Step 5: Commit any final scoped corrections and push**

```powershell
git status --short
git push origin main
git rev-parse HEAD
```

Expected: local `main` equals `origin/main`.

- [ ] **Step 6: Deploy Vercel production**

```powershell
$vercel = 'C:\Users\10990\AppData\Local\npm-cache\_npx\67eb4586ca667318\node_modules\.bin\vercel.cmd'
& $vercel --prod --yes
& $vercel inspect project-flow-delta.vercel.app
```

Expected: target `production`, status `Ready`, aliases include `pmpro.com.cn`, `www.pmpro.com.cn`, and `project-flow-delta.vercel.app`.

- [ ] **Step 7: Perform browser UAT on web and desktop**

Verify these scenarios with a fresh Free account and a seeded Legacy Lifetime account:

```text
1. Fresh account is never blocked by an expired trial.
2. Legacy active nodes load as Ongoing.
3. Planned nodes do not consume the 12-task capacity.
4. The twelfth Ongoing node succeeds and the thirteenth is blocked before mutation.
5. Completing one task immediately restores one capacity slot.
6. A user already above 12 can complete/delete and sync without losing data.
7. Free theme preview does not persist after reload.
8. Lifetime keeps all themes and unlimited Ongoing.
9. Web and desktop show the same plan and counts.
10. Analytics rows contain no user task content.
```

- [ ] **Step 8: Record release evidence**

Add the final commit SHA, Supabase migration name, deployed function versions, Vercel deployment ID, and UAT results to the release notes or deployment log. Do not include tokens, email addresses, or workspace content.
