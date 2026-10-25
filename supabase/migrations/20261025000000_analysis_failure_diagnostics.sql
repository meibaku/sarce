-- Durable analysis retry budget and operator-only failure diagnostics.
alter table public.games
  add column if not exists analysis_attempts smallint not null default 0,
  add column if not exists analysis_error text,
  add column if not exists analysis_failed_at timestamptz;

alter table public.games
  add constraint games_analysis_attempts_nonnegative check (analysis_attempts >= 0);

comment on column public.games.analysis_error is
  'Bounded, sanitized operator diagnostic for the most recent analysis failure.';
