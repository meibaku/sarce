-- Chaos map: the opening positions a player reaches most, and the one sound move in each that sets the hardest
-- problem for opponents at their level (app/services/chaos_map.py). Rebuilt on request: the API replaces a
-- player's rows as a set. Computed only from finished games.
create table if not exists public.chaos_map (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade,
  fen text not null,
  fen_key text not null,
  line text not null,
  seen integer not null,
  predictability real,
  usual_move text not null,
  usual_p_fail real,
  usual_stake real,
  chaos_move text not null,
  chaos_uci text not null,
  chaos_p_fail real,
  chaos_stake real,
  chaos_ep_loss real,
  elo integer not null,
  computed_at timestamptz not null default now(),
  unique (user_id, fen_key)
);

alter table public.chaos_map enable row level security;

create policy "Users can view own chaos map"
  on public.chaos_map for select using (user_id = auth.uid());

grant select, insert, update, delete on public.chaos_map to service_role;
