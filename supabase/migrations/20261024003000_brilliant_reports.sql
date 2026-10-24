-- "Chess.com called this Brilliant" (plan 3.3): the player says another site marked a move Brilliant that Sarce
-- didn't, and the clause Sarce's rule stopped at is stored with it. Calibration data for Benchmark B (plan 4.2).
-- No free text, so nothing to moderate; one report per move and site.
create table if not exists public.brilliant_reports (
  id uuid primary key default gen_random_uuid(),
  game_id uuid not null references public.games (id) on delete cascade,
  ply integer not null check (ply >= 0),
  user_id uuid references auth.users (id) on delete cascade,
  source text not null check (source in ('chess_com', 'lichess')),
  failed_clause text not null check (
    failed_clause in ('real_sacrifice', 'sound', 'not_lost', 'not_already_winning', 'not_forced', 'hard_to_find', 'unknown')
  ),
  rule text not null,
  created_at timestamptz not null default now(),
  unique (game_id, ply, source)
);

create index if not exists brilliant_reports_game_id_idx on public.brilliant_reports (game_id);

alter table public.brilliant_reports enable row level security;

create policy "Users can view reports on own games"
  on public.brilliant_reports for select
  using (exists (select 1 from public.games g where g.id = brilliant_reports.game_id and g.user_id = auth.uid()));

create policy "Users can report moves in own games"
  on public.brilliant_reports for insert
  with check (exists (select 1 from public.games g where g.id = brilliant_reports.game_id and g.user_id = auth.uid()));

-- The API writes with the service role, as for the other per-game tables.
grant select, insert, update, delete on public.brilliant_reports to service_role;
