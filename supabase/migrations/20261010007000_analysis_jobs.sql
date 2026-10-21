-- Chaos Lens M8 — per-user analysis job queue (docs/CHAOS_PLAN.md).
-- Replaces in-process BackgroundTasks when JOB_QUEUE_ENABLED is on: jobs survive a restart,
-- and one user's long backlog cannot starve another's.

create table public.analysis_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles (id) on delete cascade,
  chess_com_username text,
  kind text not null check (kind in ('analyze_pending')),
  payload jsonb not null default '{}'::jsonb,
  status text not null default 'queued'
    check (status in ('queued', 'running', 'done', 'failed')),
  attempts int not null default 0,
  error text,
  created_at timestamptz not null default now(),
  started_at timestamptz,
  finished_at timestamptz
);

create index analysis_jobs_status_created_idx on public.analysis_jobs (status, created_at);

alter table public.analysis_jobs enable row level security;

create policy "Users can view their own analysis jobs"
  on public.analysis_jobs for select
  using (user_id = auth.uid());

grant select, insert, update, delete on public.analysis_jobs to service_role;

-- Atomically claim the oldest queued job whose owner has nothing running.
-- "Owner" is (user_id, chess_com_username); `skip locked` lets several workers poll safely.
create or replace function public.claim_next_analysis_job()
returns setof public.analysis_jobs
language sql
security definer
set search_path = public
as $$
  update public.analysis_jobs
  set status = 'running', started_at = now(), attempts = attempts + 1
  where id = (
    select j.id
    from public.analysis_jobs j
    where j.status = 'queued'
      and not exists (
        select 1
        from public.analysis_jobs r
        where r.status = 'running'
          and r.user_id is not distinct from j.user_id
          and r.chess_com_username is not distinct from j.chess_com_username
      )
    order by j.created_at
    limit 1
    for update skip locked
  )
  returning *;
$$;

revoke all on function public.claim_next_analysis_job() from public, anon, authenticated;
grant execute on function public.claim_next_analysis_job() to service_role;
