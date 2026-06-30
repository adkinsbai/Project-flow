create extension if not exists pgcrypto;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  display_name text,
  has_seen_guide boolean not null default false,
  trial_started_at timestamptz not null default now(),
  trial_ends_at timestamptz not null default (now() + interval '30 days'),
  plan text not null default 'trial' check (plan in ('trial', 'lifetime')),
  lifetime_unlocked_at timestamptz,
  creem_customer_id text,
  creem_license_key_hash text,
  creem_license_instance_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null default 'Untitled Project',
  data jsonb not null default '{}'::jsonb,
  schema_version integer not null default 1,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create table if not exists public.creem_events (
  id text primary key,
  event_type text not null,
  payload jsonb not null,
  processed_at timestamptz not null default now()
);

create or replace function public.touch_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_touch_updated_at on public.profiles;
create trigger profiles_touch_updated_at
before update on public.profiles
for each row execute function public.touch_updated_at();

drop trigger if exists projects_touch_updated_at on public.projects;
create trigger projects_touch_updated_at
before update on public.projects
for each row execute function public.touch_updated_at();

create or replace function public.create_profile_for_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email, display_name)
  values (
    new.id,
    coalesce(new.email, ''),
    coalesce(new.raw_user_meta_data->>'display_name', split_part(coalesce(new.email, ''), '@', 1))
  )
  on conflict (id) do nothing;
  return new;
end;
$$;

create or replace function public.protect_profile_entitlement_fields()
returns trigger
language plpgsql
as $$
begin
  if auth.role() = 'authenticated' then
    if new.plan is distinct from old.plan
      or new.trial_started_at is distinct from old.trial_started_at
      or new.trial_ends_at is distinct from old.trial_ends_at
      or new.lifetime_unlocked_at is distinct from old.lifetime_unlocked_at
      or new.creem_customer_id is distinct from old.creem_customer_id
      or new.creem_license_key_hash is distinct from old.creem_license_key_hash
      or new.creem_license_instance_id is distinct from old.creem_license_instance_id then
      raise exception 'entitlement fields are server-managed';
    end if;
  end if;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.create_profile_for_new_user();

drop trigger if exists protect_profile_entitlement_fields on public.profiles;
create trigger protect_profile_entitlement_fields
before update on public.profiles
for each row execute function public.protect_profile_entitlement_fields();

alter table public.profiles enable row level security;
alter table public.projects enable row level security;
alter table public.creem_events enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own"
on public.profiles for select
using (auth.uid() = id);

drop policy if exists "profiles_update_own_preferences" on public.profiles;
create policy "profiles_update_own_preferences"
on public.profiles for update
using (auth.uid() = id)
with check (auth.uid() = id);

drop policy if exists "projects_select_own" on public.projects;
create policy "projects_select_own"
on public.projects for select
using (auth.uid() = user_id and deleted_at is null);

drop policy if exists "projects_insert_own" on public.projects;
create policy "projects_insert_own"
on public.projects for insert
with check (auth.uid() = user_id);

drop policy if exists "projects_update_own" on public.projects;
create policy "projects_update_own"
on public.projects for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

drop policy if exists "projects_delete_own" on public.projects;
create policy "projects_delete_own"
on public.projects for delete
using (auth.uid() = user_id);

create index if not exists projects_user_id_updated_at_idx
on public.projects(user_id, updated_at desc)
where deleted_at is null;

create index if not exists profiles_creem_customer_id_idx
on public.profiles(creem_customer_id);
