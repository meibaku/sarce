-- Saved positions (docs/DESIGN.md: Review "Add to Train", PHASES 2.1): a position the player keeps
-- to drill later. It becomes Train's fifth source, "a saved position". `best_san` is the engine's
-- move when Sarce knew it at save time (from the game's analysis); manual positions may have none.
create table if not exists public.saved_positions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  fen text not null,
  title text not null default 'Saved position',
  note text not null default '',
  best_san text,
  game_id uuid references public.games (id) on delete set null,
  ply integer,
  created_at timestamptz not null default now(),
  unique (user_id, fen)
);

create index if not exists saved_positions_user_id_idx on public.saved_positions (user_id, created_at desc);

alter table public.saved_positions enable row level security;

create policy "Users can view own saved positions"
  on public.saved_positions for select using (user_id = auth.uid());

create policy "Users can save positions"
  on public.saved_positions for insert with check (user_id = auth.uid());

create policy "Users can delete own saved positions"
  on public.saved_positions for delete using (user_id = auth.uid());

grant select, insert, update, delete on public.saved_positions to service_role;
