# Project Flow

Project Flow is a visual workflow planner with account-based access, a 30-day free trial, and a Creem-powered lifetime membership flow.

## Current Architecture

- Frontend: static React page in `index.html`
- Auth/database: Supabase Auth + Postgres
- Backend: Supabase Edge Functions
- Payments and license keys: Creem
- Static hosting: GitHub Pages or any static host

GitHub Pages can host the frontend, but it cannot run the account backend. Supabase Edge Functions hold the private keys and call Creem securely.

## Creem Setup

1. Create a Creem account at `https://creem.io/dashboard`.
2. Start in test mode and create/get a `creem_test_...` API key.
3. Create a one-time product for Project Flow lifetime access:
   - Name: `Project Flow Lifetime`
   - Price: `9.9`
   - Billing type: one-time
   - Enable License Key Management on the product.
4. Save the product ID as `CREEM_LIFETIME_PRODUCT_ID`.
5. Add a webhook endpoint in Creem:
   - URL: `https://YOUR_PROJECT.supabase.co/functions/v1/creem-webhook`
   - Events: `checkout.completed`, subscription grant/revoke events if enabled.
6. Copy the webhook secret as `CREEM_WEBHOOK_SECRET`.

Creem will handle payment and license key delivery. The app also lets a user paste their Creem license key to unlock lifetime access.

## Supabase Setup

1. Create a Supabase project.
2. Apply the SQL migration in `supabase/migrations/20260630000000_project_flow_auth_creem.sql`.
3. Deploy Edge Functions:

For the current hosted project, the prepared Windows helper is:

```powershell
.\scripts\deploy-supabase.ps1 -ProjectRef pksjwrajpyobkzxlqmrz -AppUrl https://project-flow-delta.vercel.app/
```

It prompts for the Supabase access token, database password, service role key, and Creem secrets without committing them to git.

Manual commands:

```bash
supabase functions deploy me
supabase functions deploy workspace
supabase functions deploy creem-checkout
supabase functions deploy creem-license
supabase functions deploy creem-webhook
```

4. Set function secrets:

```bash
supabase secrets set SUPABASE_URL=https://YOUR_PROJECT.supabase.co
supabase secrets set SUPABASE_SERVICE_ROLE_KEY=YOUR_SERVICE_ROLE_KEY
supabase secrets set APP_URL=https://adkinsbai.github.io/Project-flow/
supabase secrets set CREEM_API_KEY=creem_test_YOUR_KEY
supabase secrets set CREEM_WEBHOOK_SECRET=YOUR_WEBHOOK_SECRET
supabase secrets set CREEM_LIFETIME_PRODUCT_ID=prod_YOUR_PRODUCT_ID
supabase secrets set CREEM_TEST_MODE=true
```

5. Create `config.js` from the example:

```bash
copy config.example.js config.js
```

Then fill:

```js
window.PROJECT_FLOW_SUPABASE_URL = "https://YOUR_PROJECT.supabase.co";
window.PROJECT_FLOW_SUPABASE_ANON_KEY = "YOUR_SUPABASE_ANON_KEY";
```

`config.js` is intentionally ignored by git so you do not commit project keys by accident. The anon key is safe for frontend use, but the service role key and Creem key must stay only in Supabase secrets.

## Access Rules

- New users get a server-side 30-day trial when their Supabase Auth user is created.
- Lifetime access is granted when:
  - Creem sends a verified `checkout.completed` webhook with the user's `referenceId`, or
  - the user redeems a valid Creem license key inside the app.
- The first-login guide state is stored as `profiles.has_seen_guide`.

## Local Preview

For static preview:

```bash
python -m http.server 8766 --bind 127.0.0.1
```

Open `http://127.0.0.1:8766/index.html`.

Without `config.js`, the app shows a setup notice instead of enabling login.
