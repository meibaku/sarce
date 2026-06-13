-- Sarce initial schema
-- Style-vector schema is versioned from day one

-- Profiles (extends auth.users)
create table public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  chess_com_username text,
  style_goal jsonb not null default '{"target_brilliant_min": 6, "target_brilliant_max": 10}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;

create policy "Users can view own profile"
  on public.profiles for select
  using (auth.uid() = id);

create policy "Users can update own profile"
  on public.profiles for update
  using (auth.uid() = id);

create policy "Users can insert own profile"
  on public.profiles for insert
  with check (auth.uid() = id);

-- Games imported from Chess.com or other sources
create table public.games (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles (id) on delete cascade,
  chess_com_username text not null,
  external_id text not null unique,
  pgn text not null,
  played_at timestamptz,
  opponent text,
  opponent_rating int,
  time_control text,
  result text check (result in ('win', 'loss', 'draw')),
  user_color text check (user_color in ('white', 'black')),
  analysis_status text not null default 'pending'
    check (analysis_status in ('pending', 'processing', 'complete', 'failed')),
  created_at timestamptz not null default now()
);

create index games_user_id_idx on public.games (user_id);
create index games_played_at_idx on public.games (played_at desc);
create index games_analysis_status_idx on public.games (analysis_status);

alter table public.games enable row level security;

create policy "Users can view own games"
  on public.games for select
  using (auth.uid() = user_id);

create policy "Users can insert own games"
  on public.games for insert
  with check (auth.uid() = user_id or user_id is null);

-- Per-move classification results
create table public.game_moves (
  id uuid primary key default gen_random_uuid(),
  game_id uuid not null references public.games (id) on delete cascade,
  ply int not null,
  uci text not null,
  quality text not null check (quality in (
    'best', 'excellent', 'good', 'inaccuracy', 'mistake', 'blunder', 'miss', 'brilliant'
  )),
  cp_loss numeric,
  eval_before numeric,
  eval_after numeric,
  is_brilliant boolean not null default false,
  created_at timestamptz not null default now(),
  unique (game_id, ply)
);

create index game_moves_game_id_idx on public.game_moves (game_id);

alter table public.game_moves enable row level security;

create policy "Users can view moves for own games"
  on public.game_moves for select
  using (
    exists (
      select 1 from public.games g
      where g.id = game_moves.game_id and g.user_id = auth.uid()
    )
  );

-- Aggregated per-game analysis
create table public.game_analyses (
  id uuid primary key default gen_random_uuid(),
  game_id uuid not null references public.games (id) on delete cascade unique,
  distribution jsonb not null default '{}'::jsonb,
  brilliant_pct numeric not null default 0,
  total_moves int not null default 0,
  style_vector jsonb,
  analyzed_at timestamptz not null default now()
);

alter table public.game_analyses enable row level security;

create policy "Users can view analyses for own games"
  on public.game_analyses for select
  using (
    exists (
      select 1 from public.games g
      where g.id = game_analyses.game_id and g.user_id = auth.uid()
    )
  );

-- Rolling user baseline
create table public.user_baselines (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.profiles (id) on delete cascade unique,
  distribution jsonb not null default '{}'::jsonb,
  brilliant_pct numeric not null default 0,
  games_analyzed int not null default 0,
  target_brilliant_min numeric not null default 6,
  target_brilliant_max numeric not null default 10,
  updated_at timestamptz not null default now()
);

alter table public.user_baselines enable row level security;

create policy "Users can view own baseline"
  on public.user_baselines for select
  using (auth.uid() = user_id);

-- Reference players (Tal, user-selected idols)
create table public.reference_players (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  source text not null check (source in ('pgn_corpus', 'chess_com')),
  source_identifier text not null,
  games_sampled int not null default 0,
  benchmark_status text not null default 'pending'
    check (benchmark_status in ('pending', 'processing', 'complete', 'failed')),
  created_at timestamptz not null default now(),
  unique (source, source_identifier)
);

alter table public.reference_players enable row level security;

create policy "Reference players are readable by authenticated users"
  on public.reference_players for select
  to authenticated
  using (true);

-- Cached benchmark results for reference players
create table public.reference_benchmarks (
  id uuid primary key default gen_random_uuid(),
  reference_player_id uuid not null references public.reference_players (id) on delete cascade unique,
  distribution jsonb not null default '{}'::jsonb,
  brilliant_pct numeric not null default 0,
  style_vector jsonb not null,
  computed_at timestamptz not null default now()
);

alter table public.reference_benchmarks enable row level security;

create policy "Benchmarks readable by authenticated users"
  on public.reference_benchmarks for select
  to authenticated
  using (true);

-- Versioned style vectors (evolves as features are tuned)
create table public.style_vectors (
  id uuid primary key default gen_random_uuid(),
  entity_type text not null check (entity_type in ('user', 'game', 'reference')),
  entity_id uuid not null,
  version int not null default 1,
  vector jsonb not null,
  created_at timestamptz not null default now(),
  unique (entity_type, entity_id, version)
);

create index style_vectors_entity_idx on public.style_vectors (entity_type, entity_id);

alter table public.style_vectors enable row level security;

create policy "Users can view own style vectors"
  on public.style_vectors for select
  using (
    entity_type = 'reference'
    or (
      entity_type in ('user', 'game')
      and entity_id in (
        select id from public.profiles where id = auth.uid()
        union
        select id from public.games where user_id = auth.uid()
      )
    )
  );

-- Seed Tal as default reference player
insert into public.reference_players (name, source, source_identifier)
values ('Mikhail Tal', 'pgn_corpus', 'pgnmentor-tal');

-- Auto-create profile on signup
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id)
  values (new.id);
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_user();
