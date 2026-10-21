-- v1.0 Train: spaced review of drills (docs/DESIGN.md). After a drill the player says how sure they
-- were; Guessed brings it back tomorrow, Unsure in 3 days, Sure in 9. One row per answer.
-- owner_id is the profile id (local-first mode has no auth user), so it carries no FK to auth.users.
create table if not exists public.drill_reviews (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null,
  drill_key text not null check (char_length(drill_key) <= 200),
  confidence text not null check (confidence in ('guessed', 'unsure', 'sure')),
  next_due timestamptz not null,
  reviewed_at timestamptz not null default now()
);

create index if not exists drill_reviews_owner_key_idx on public.drill_reviews (owner_id, drill_key, reviewed_at desc);

alter table public.drill_reviews enable row level security;

create policy "Users can view own drill reviews"
  on public.drill_reviews for select
  using (owner_id = auth.uid());

create policy "Users can add own drill reviews"
  on public.drill_reviews for insert
  with check (owner_id = auth.uid());

grant select, insert, update, delete on public.drill_reviews to service_role;
