-- LE2.2: reviewed instructional and assessment positions. Targets and verification are API-only so a client cannot
-- read an answer before responding. Personal game-derived rows are never made global implicitly.
create table if not exists public.pattern_instances (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid,
  visibility text not null check (visibility in ('private', 'global')),
  concept_key text not null check (char_length(concept_key) between 1 and 100),
  position_fen text not null check (char_length(position_fen) <= 120),
  position_key text not null check (char_length(position_key) <= 120),
  family_key text not null check (char_length(family_key) between 1 and 200),
  dedupe_key text not null unique check (char_length(dedupe_key) = 64),
  source_type text not null check (source_type in ('own_game', 'curated', 'generated')),
  source_game_id uuid references public.games (id) on delete cascade,
  source_ply integer check (source_ply is null or source_ply >= 0),
  label text not null check (label in ('positive', 'near_miss', 'control')),
  target jsonb not null default '{}'::jsonb,
  verification jsonb not null default '{}'::jsonb,
  difficulty_context jsonb not null default '{}'::jsonb,
  bank_partition text check (bank_partition in ('instruction', 'immediate', 'day7', 'day28', 'transfer')),
  stockfish_version text not null check (char_length(stockfish_version) between 1 and 100),
  analysis_nodes integer not null check (analysis_nodes > 0),
  detector_version integer not null check (detector_version > 0),
  review_status text not null default 'candidate' check (review_status in ('candidate', 'approved', 'rejected', 'retired')),
  review_annotations jsonb not null default '[]'::jsonb check (jsonb_typeof(review_annotations) = 'array'),
  annotation_count smallint not null default 0 check (annotation_count >= 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (
    (visibility = 'private' and owner_id is not null) or
    (visibility = 'global' and owner_id is null)
  ),
  check (
    (source_type = 'own_game' and visibility = 'private' and source_game_id is not null) or
    (source_type <> 'own_game' and source_game_id is null)
  ),
  check (review_status <> 'approved' or annotation_count > 0)
);

create index if not exists pattern_instances_owner_status_idx
  on public.pattern_instances (owner_id, concept_key, review_status);
create index if not exists pattern_instances_global_status_idx
  on public.pattern_instances (concept_key, review_status) where visibility = 'global';
create index if not exists pattern_instances_family_idx
  on public.pattern_instances (family_key);

alter table public.pattern_instances enable row level security;

-- Deliberately no authenticated/anon policy or grant: the row contains the answer. Thin API services authenticate,
-- scope and sanitize every served item; reviewer tooling uses the service role.
grant select, insert, update, delete on public.pattern_instances to service_role;
