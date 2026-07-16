# Project Flow Activation, Subscription, and AI Design

## 1. Objective

Upgrade Project Flow from a trial-gated workflow canvas into a sustainable freemium product for individual project executors.

The design must achieve three outcomes:

1. A new user reaches first value within 60 seconds.
2. Free users can use the product indefinitely within clear limits.
3. Pro subscription revenue covers ongoing AI and infrastructure costs.

The primary user is an individual founder, independent developer, student, or knowledge worker who wants to turn a goal into the next executable step.

## 2. Product Model

### Free

- US$0.
- One default visual theme.
- At most 12 ongoing nodes across the workspace.
- Two successful AI workflow generations per monthly usage period.
- Unlimited completed-node history.
- Full viewing, completion, deletion, and export access.
- Existing data is never deleted when a limit is reached.

An ongoing node is any node whose status is not `done`. The limit is global across the workspace, not per project. At 12 ongoing nodes, the user may complete or delete existing nodes but may not create, duplicate, import, or AI-confirm additional ongoing nodes until capacity is available.

### Pro

- Monthly: US$12.
- Quarterly: US$32.40, a 10% discount from monthly billing.
- Annual: US$115.20, a 20% discount from monthly billing.
- Unlimited ongoing nodes.
- All visual themes.
- AI workflow generation presented as unlimited, subject to a documented fair-use policy and backend abuse controls.
- Web and desktop account sync.

### Legacy Lifetime

Existing lifetime customers retain permanent access to core Pro workflow features, all themes, and sync. They do not receive technically unlimited AI because AI has a continuing marginal cost. Their AI allowance is separately configurable and must be shown clearly in the account UI.

## 3. First-Use Activation

The current static guide is replaced as the primary onboarding experience by an interactive activation flow. The guide remains available from Help for later reference.

### Step 1: Define a Real Goal

After account creation and email confirmation, the user sees:

> What do you want to move forward today?

The user can:

- Enter a goal and choose `Break it down with AI`.
- Start from a template.
- Create manually.
- Skip and explore.

The default `My First Project` placeholder must not appear as if it were real user data. Manual creation may create an editable empty root only after the user selects that path.

The AI option states that Free includes two AI generations per month.

### Step 2: Review an AI Plan

AI returns a structured, editable preview containing a root goal and a bounded set of child steps. The user may edit, remove, regenerate, or accept the result.

The result does not mutate the workspace until accepted. A failed request or invalid response does not consume quota. Returning a valid editable preview records one successful generation because the model cost has already been incurred. Closing or abandoning that preview does not restore quota.

### Step 3: Complete the First Loop

After entering the canvas, one contextual prompt asks the user to complete the first actionable node. When completed, Project Flow shows:

- A concise completion acknowledgement.
- The next recommended ongoing node.
- Confirmation that the workspace has been saved.

This is the activation event. Continue, Branch, timeline, multi-select, and advanced controls are introduced contextually when first encountered rather than in an upfront tour.

## 4. Upgrade Experience

### Persistent Status

The top bar shows a compact status rather than a generic `Update Pro` button:

- Free: `Free - 5/12 ongoing`.
- Pro: `Pro` plus the next renewal date in the account panel.
- Legacy lifetime: `Lifetime`.

The primary command is consistently named `Upgrade to Pro` in English and `升级 Pro` in Chinese.

### Ongoing Limit

- At 9/12, the status gains a non-blocking warning treatment.
- At 11/12, a lightweight message appears after creation.
- At 12/12, attempts to create another ongoing node are blocked before mutation.

The limit message prioritizes progress:

> You are already moving 12 tasks forward. Complete one to create another, or upgrade to Pro for unlimited ongoing work.

Actions:

- Focus today's next task.
- Upgrade to Pro.

### AI Limit

Free users see their remaining successful generations. When exhausted, manual creation remains available. The message explains that quota resets monthly and Pro includes AI under fair use.

### Theme Limit

The default theme is usable on Free. Pro themes remain visible with lock indicators and may be previewed temporarily. Persisting a Pro theme requires Pro. Downgrading returns the saved theme to the default without deleting the prior preference, so it can be restored after resubscription.

### Upgrade Page

The upgrade surface presents the three billing periods and four value points:

- Unlimited ongoing nodes.
- AI workflow generation under fair use.
- All themes.
- Web and desktop sync.

The annual option may be visually recommended, but the interface must not use fake countdowns, misleading savings, or preselected consent.

## 5. Entitlement Architecture

Entitlement is computed on the server and returned as one authoritative object. Frontends must not infer access from product IDs, checkout query parameters, or cached labels.

Supported plan keys:

```text
free
pro_monthly
pro_quarterly
pro_annual
legacy_lifetime
```

The entitlement response includes:

```text
plan
isPro
subscriptionStatus
currentPeriodEnd
cancelAtPeriodEnd
ongoingLimit
ongoingUsed
aiMonthlyLimit
aiUsed
aiPeriodEnd
availableThemes
```

`null` represents no product limit. It does not disable abuse and safety controls.

## 6. Data Model

Extend `profiles` with subscription and usage-summary fields:

```text
plan
subscription_status
subscription_provider
subscription_product_id
subscription_id
current_period_start
current_period_end
cancel_at_period_end
ai_period_start
ai_period_end
ai_used
legacy_lifetime
```

Add `plan_catalog`:

```text
plan_key
creem_product_id
billing_period
price_usd
ongoing_limit
ai_monthly_limit
theme_access
active
```

Product mappings are maintained server-side. A client may submit a `planKey` to checkout but never a product ID, price, limit, or entitlement.

Add `ai_usage_events`:

```text
id
user_id
request_id
status
model
input_tokens
output_tokens
created_at
```

`request_id` is unique per user so network retries cannot double-count usage.

## 7. AI Service

AI calls run through a Supabase Edge Function. No model key is exposed to the browser or desktop renderer.

Request flow:

1. Authenticate the user.
2. Load the authoritative entitlement.
3. Enforce Free quota or Pro fair-use controls.
4. Enforce input-length and request-rate limits.
5. Call the configured model with a strict structured-output schema.
6. Validate node count, hierarchy, titles, dates, and field sizes.
7. Record one successful use after schema validation.
8. Return an editable preview and its request ID.

Free quota counts valid previews returned to the user. Regeneration creates a new request and consumes another generation when its preview succeeds. Provider errors, timeouts, and schema-invalid outputs do not consume quota. Retrying the same request ID is idempotent and cannot consume quota twice.

Pro fair-use controls include per-minute rate limiting, a daily soft threshold, a monthly safety threshold, maximum input size, maximum output nodes, and automated abuse detection. Normal users do not see a running Pro counter. When a safety threshold is reached, the system degrades gracefully with a clear retry or support path rather than silently failing.

## 8. Creem Subscription Lifecycle

Creem uses separate products for monthly, quarterly, and annual plans. Checkout accepts only a known internal `planKey`; the server resolves its active Creem product.

The webhook must:

1. Verify the Creem signature against the raw request body.
2. Persist the raw event using the provider event ID.
3. Treat duplicate event IDs as successful no-ops.
4. Map the provider product ID through `plan_catalog`.
5. Update subscription status, billing period, and current period end.
6. Recompute entitlement.
7. Preserve the last successfully handled event for support diagnostics.

Required event behavior:

- `checkout.completed`, `subscription.active`, and `subscription.paid`: grant or renew the mapped Pro plan.
- `subscription.canceled`: set `cancel_at_period_end`; retain Pro until `current_period_end`.
- `subscription.expired`: downgrade after the paid period ends.
- `refund.created` and `dispute.created`: update access according to the verified provider state and refund scope.

License-key activation must verify the key with Creem and derive product, status, and expiration from the verified activation result. It must not convert every valid key into lifetime access.

Downgrade never deletes workspace data. Users above the Free ongoing limit retain view, complete, delete, and export operations but cannot add ongoing work.

## 9. Shared Frontend Boundary

`index.html` and `project-flow.html` currently duplicate the application. Before product behavior expands, shared application logic should be extracted so web and desktop load the same modules.

Target ownership boundaries:

```text
app/entitlement.js
app/onboarding.js
app/billing.js
app/ai.js
app/app.jsx
```

The exact build arrangement may follow the existing static deployment constraints, but business rules must have one source of truth and one test surface.

## 10. Error and Recovery Behavior

- Email confirmation explains the next step and supports resend.
- Authentication errors are localized and actionable.
- AI timeout, malformed output, and provider failure do not consume quota; a valid preview does.
- Checkout creation failure keeps the user in Project Flow and offers retry.
- Webhook delay displays payment as processing and provides refresh/support actions.
- Cloud sync failure never implies that data is safely stored remotely.
- Subscription downgrade never makes data disappear.
- Theme downgrade restores the default without corrupting theme preference.
- All account, consent, billing, and support copy uses one selected language consistently.

## 11. Analytics and Success Criteria

Track product events without storing task content:

```text
signup_started
signup_completed
email_confirmed
onboarding_goal_submitted
ai_generation_started
ai_generation_previewed
ai_generation_accepted
first_node_completed
activation_completed
ongoing_limit_seen
ai_limit_seen
upgrade_viewed
checkout_started
subscription_activated
subscription_renewed
subscription_canceled
subscription_expired
```

Initial success criteria:

- Median time from first authenticated load to `activation_completed` is under 60 seconds.
- Activation means a real project exists and at least one actionable node has been completed.
- AI failures never decrement visible Free quota; each valid returned preview decrements it once.
- Subscription state converges correctly after duplicate and out-of-order webhook delivery.
- No downgrade path deletes or hides existing workspace data.

## 12. Delivery Phases

### Phase 1: Entitlement Foundation

- Introduce plan catalog, subscription fields, entitlement computation, and legacy mapping.
- Preserve current customers.
- Add entitlement contract tests.

### Phase 2: Activation and Free Limits

- Replace placeholder onboarding with goal-first activation.
- Add 12-ongoing enforcement in every creation path.
- Add theme preview and Free/Pro status UI.

### Phase 3: AI Generation

- Add the AI Edge Function, structured output, preview/accept flow, quota ledger, and fair-use protection.
- Add failure, retry, idempotency, and acceptance tests.

### Phase 4: Creem Subscriptions

- Create monthly, quarterly, and annual mappings.
- Replace lifetime-only checkout and license logic.
- Add renewal, cancellation, expiration, refund, dispute, and downgrade tests.

### Phase 5: End-to-End Release Verification

- Verify new signup through first value.
- Verify Free limits and reset behavior.
- Verify all three purchase periods.
- Verify cancellation and expiration without data loss.
- Verify web and desktop parity.
- Deploy Supabase changes before the frontend that depends on them.
- Confirm the Vercel deployment references the intended Git commit.

## 13. Acceptance Scenarios

1. A new user can create and complete a first workflow within 60 seconds.
2. A Free user can create the twelfth ongoing node but not the thirteenth.
3. Completing or deleting an ongoing node immediately restores Free capacity.
4. Import, duplication, templates, AI acceptance, Continue, and Branch cannot bypass the ongoing limit.
5. A Free user can receive two valid AI previews per usage period; failures do not count and each valid preview counts once even if it is later abandoned.
6. A Pro user sees no normal-use AI counter but is protected by backend fair-use controls.
7. Monthly, quarterly, and annual checkout products map to the correct plan and expiration.
8. Cancellation preserves Pro through the paid period.
9. Expiration downgrades to Free without deleting data.
10. Duplicate and out-of-order webhooks do not corrupt subscription state.
11. Legacy lifetime users retain core Pro access.
12. Web and desktop display the same entitlement and enforce the same limits.
