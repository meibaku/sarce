-- LE2.3 projection only: learning_attempts remains authoritative and this table may be rebuilt at any time.
create table if not exists public.learning_state (
  enrollment_id uuid not null references public.learning_enrollments (id),
  participant_key uuid not null,
  concept_key text not null,
  family_key text not null,
  scheduler_version integer not null check (scheduler_version > 0),
  stage text not null check (stage in ('retry', 'novel', 'delayed')),
  due_at timestamptz not null,
  last_attempt_id uuid not null references public.learning_attempts (id),
  independent_correct integer not null default 0 check (independent_correct >= 0),
  updated_at timestamptz not null,
  primary key (enrollment_id, concept_key, family_key)
);

create index if not exists learning_state_due_idx
  on public.learning_state (participant_key, due_at);

alter table public.learning_state enable row level security;
grant select, insert, update, delete on public.learning_state to service_role;

