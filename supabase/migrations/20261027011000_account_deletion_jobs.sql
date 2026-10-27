-- Deletion receipts survive removal of auth.users so completion can be verified afterwards.
create table public.account_deletion_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  receipt_hash text not null check (length(receipt_hash) = 64),
  status text not null default 'processing' check (status in ('processing', 'failed', 'complete')),
  completed_steps jsonb not null default '[]'::jsonb,
  error text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index account_deletion_jobs_user_idx on public.account_deletion_jobs (user_id, created_at desc);
alter table public.account_deletion_jobs enable row level security;
-- Service-role only. Status is exposed by the API through an unguessable receipt.
