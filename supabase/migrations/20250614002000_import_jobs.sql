-- Background Chess.com import job tracking.

create table public.import_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles (id) on delete cascade,
  chess_com_username text not null,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'complete', 'failed')),
  analyze_after_import boolean not null default true,
  archives_total int not null default 0,
  archives_done int not null default 0,
  games_fetched int not null default 0,
  games_new int not null default 0,
  games_skipped int not null default 0,
  games_updated int not null default 0,
  error_message text,
  started_at timestamptz,
  finished_at timestamptz,
  created_at timestamptz not null default now()
);

create index import_jobs_user_username_idx
  on public.import_jobs (user_id, chess_com_username, created_at desc);

alter table public.import_jobs enable row level security;

create policy "Users can view own import jobs"
  on public.import_jobs for select
  using (auth.uid() = user_id);

grant select, insert, update, delete on table public.import_jobs to service_role;
