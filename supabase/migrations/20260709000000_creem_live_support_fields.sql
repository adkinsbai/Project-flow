alter table public.profiles
  add column if not exists creem_checkout_id text,
  add column if not exists creem_order_id text,
  add column if not exists creem_product_id text,
  add column if not exists creem_last_event_id text,
  add column if not exists creem_last_event_type text;

create index if not exists profiles_creem_checkout_id_idx
on public.profiles(creem_checkout_id);

create index if not exists profiles_creem_order_id_idx
on public.profiles(creem_order_id);
