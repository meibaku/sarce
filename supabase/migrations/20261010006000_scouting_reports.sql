-- Chaos Lens M8 — opponent scouting (docs/CHAOS_PLAN.md).
-- Private preparation reports about players the owner named. Aggregates only: the
-- scouted player's games are never stored. No policy lets anyone read another owner's rows.

create table public.scouting_reports (
  id uuid primary key default gen_random_uuid(),
  owner_user_id uuid not null references public.profiles (id) on delete cascade,
  target_username text not null,
  source text not null check (source in ('chess_com', 'lichess')),
  games_sampled int not null default 0,
  report jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (owner_user_id, source, target_username)
);

-- For deletion on request: find every report about one player.
create index scouting_reports_target_idx on public.scouting_reports (source, target_username);

alter table public.scouting_reports enable row level security;

create policy "Owners can view their scouting reports"
  on public.scouting_reports for select
  using (owner_user_id = auth.uid());

create policy "Owners can delete their scouting reports"
  on public.scouting_reports for delete
  using (owner_user_id = auth.uid());

grant select, insert, update, delete on public.scouting_reports to service_role;
