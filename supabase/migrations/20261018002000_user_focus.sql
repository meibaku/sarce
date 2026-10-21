-- v1.0 Recap and Play: the weekly focus the player picks and today's intention for their next game
-- (docs/DESIGN.md). The intention is graded after import and never shown during a game elsewhere.
-- owner_id is the profile id (local-first mode has no auth user), so it carries no FK to auth.users.
create table if not exists public.user_focus (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  kind text not null check (kind in ('weekly', 'today')),
  value text not null check (char_length(value) <= 120),
  set_at timestamptz not null default now()
);

create index if not exists user_focus_owner_kind_idx on public.user_focus (owner_id, kind, set_at desc);

alter table public.user_focus enable row level security;

create policy "Users can view own focus"
  on public.user_focus for select
  using (owner_id = auth.uid());

create policy "Users can set own focus"
  on public.user_focus for insert
  with check (owner_id = auth.uid());

grant select, insert, update, delete on public.user_focus to service_role;
