-- LE2.3: consent, player-level assignment and append-only responses. Attempts retain pseudonymous evidence when an
-- account is removed; the nullable user link controls access, while participant_key remains the analysis identity.
create table if not exists public.learning_enrollments (
  id uuid primary key default gen_random_uuid(),
  user_id uuid unique references auth.users (id) on delete set null,
  participant_key uuid not null unique default gen_random_uuid(),
  protocol_version integer not null check (protocol_version > 0),
  cohort text not null check (cohort in ('qualitative', 'controlled')),
  arm text not null check (arm in ('experimental', 'active_control')),
  adult_confirmed boolean not null check (adult_confirmed),
  consented_at timestamptz not null,
  enrolled_at timestamptz not null default now(),
  withdrawn_at timestamptz,
  check (withdrawn_at is null or withdrawn_at >= consented_at)
);

create table if not exists public.learning_attempts (
  id uuid primary key default gen_random_uuid(),
  client_attempt_id uuid not null,
  enrollment_id uuid not null references public.learning_enrollments (id),
  pattern_id uuid references public.pattern_instances (id) on delete set null,
  participant_key uuid not null,
  protocol_version integer not null check (protocol_version > 0),
  scoring_version integer not null check (scoring_version > 0),
  detector_version integer not null check (detector_version > 0),
  phase text not null check (phase in ('baseline', 'learning', 'immediate', 'day7', 'day28', 'transfer')),
  arm text not null check (arm in ('experimental', 'active_control')),
  concept_key text not null,
  family_key text not null,
  item_label text not null check (item_label in ('positive', 'near_miss', 'control')),
  position_key text not null,
  response jsonb not null,
  correct boolean not null,
  assistance text not null check (assistance in ('independent', 'hinted', 'revealed')),
  confidence smallint check (confidence between 1 and 5),
  latency_ms integer not null check (latency_ms >= 0 and latency_ms <= 3600000),
  novel boolean not null,
  scheduled_for timestamptz,
  presented_at timestamptz not null,
  responded_at timestamptz not null,
  recorded_at timestamptz not null default now(),
  unique (enrollment_id, client_attempt_id),
  check (responded_at >= presented_at)
);

create index if not exists learning_attempts_participant_idx
  on public.learning_attempts (participant_key, concept_key, responded_at);
create index if not exists learning_attempts_phase_idx
  on public.learning_attempts (protocol_version, phase, arm);

alter table public.learning_enrollments enable row level security;
alter table public.learning_attempts enable row level security;

-- These tables are API-only: assignment and answer keys must not be client-writable or readable before response.
grant select, insert, update on public.learning_enrollments to service_role;
grant select, insert on public.learning_attempts to service_role;

create or replace function public.reject_learning_attempt_mutation()
returns trigger
language plpgsql
as $$
begin
  raise exception 'learning_attempts is append-only';
end;
$$;

drop trigger if exists learning_attempts_no_update on public.learning_attempts;
create trigger learning_attempts_no_update
before update or delete on public.learning_attempts
for each row execute function public.reject_learning_attempt_mutation();

