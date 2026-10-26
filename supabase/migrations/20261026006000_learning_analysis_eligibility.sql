-- LE2.6: freeze analysis inclusion on each append-only attempt. Defaults keep any controlled
-- pre-migration records eligible while new qualitative attempts are excluded by the API snapshot.
alter table public.learning_enrollments
  add column if not exists analysis_eligible boolean not null default true;

alter table public.learning_attempts
  add column if not exists cohort text not null default 'controlled'
  check (cohort in ('qualitative', 'controlled')),
  add column if not exists analysis_eligible boolean not null default true;

create index if not exists learning_attempts_primary_analysis_idx
  on public.learning_attempts (protocol_version, analysis_eligible, cohort, phase, arm);
