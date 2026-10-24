-- Analysis monitor (dev mode): what every machine and engine is doing now, what happened, and how fast.
-- Written by the API and the node gateway with the service role; read by the monitor endpoints. No client policies.

-- One row per computer (the server and each Sarce Node), replaced every few seconds.
create table if not exists public.machine_snapshots (
  machine text primary key check (char_length(machine) <= 80),
  role text not null check (role in ('server', 'node')),
  cpu real,
  mem_used real,
  mem_total_gb real,
  uptime_s bigint,
  process_started_at timestamptz,
  bundle text,
  engines integer not null default 0,
  updated_at timestamptz not null default now()
);

-- One row per engine (a node worker, or one of the server's analysis slots).
create table if not exists public.engine_snapshots (
  machine text not null check (char_length(machine) <= 80),
  engine integer not null,
  state text not null,
  game_id uuid,
  done integer not null default 0,
  total integer not null default 0,
  started_at timestamptz,
  progress_at timestamptz,
  cpu real,
  rss_mb real,
  games_today integer not null default 0,
  last_game_s integer,
  updated_at timestamptz not null default now(),
  primary key (machine, engine)
);

-- What happened: claims, finished and failed games, restarts, updates, and alerts (rate drops, stalls, offline).
create table if not exists public.analysis_events (
  id bigserial primary key,
  at timestamptz not null default now(),
  machine text,
  engine integer,
  kind text not null,
  game_id uuid,
  detail jsonb not null default '{}'::jsonb
);
create index if not exists analysis_events_at_idx on public.analysis_events (at desc);

-- Games and positions finished per machine per minute: the 24-hour chart and the rate-drop check.
create table if not exists public.analysis_throughput (
  minute timestamptz not null,
  machine text not null,
  games integer not null default 0,
  positions integer not null default 0,
  primary key (minute, machine)
);

alter table public.machine_snapshots enable row level security;
alter table public.engine_snapshots enable row level security;
alter table public.analysis_events enable row level security;
alter table public.analysis_throughput enable row level security;

grant select, insert, update, delete on public.machine_snapshots, public.engine_snapshots, public.analysis_events, public.analysis_throughput to service_role;
grant usage, select on sequence public.analysis_events_id_seq to service_role;

-- Count a finished game into this minute's row atomically (several engines finish at once).
create or replace function public.bump_throughput(p_machine text, p_games integer, p_positions integer)
returns void
language sql
security invoker
set search_path = public
as $$
  insert into analysis_throughput (minute, machine, games, positions)
  values (date_trunc('minute', now()), p_machine, p_games, p_positions)
  on conflict (minute, machine) do update
     set games = analysis_throughput.games + excluded.games,
         positions = analysis_throughput.positions + excluded.positions;
$$;

revoke all on function public.bump_throughput(text, integer, integer) from public, anon, authenticated;
grant execute on function public.bump_throughput(text, integer, integer) to service_role;
