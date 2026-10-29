-- Restore-safe erasure ledger. It has no FK to auth/users, so the operator can
-- export it before a restore and re-import it before readiness is enabled.
create table public.account_deletion_tombstones (
  job_id uuid primary key,
  user_id uuid not null,
  receipt_hash text not null check (length(receipt_hash) = 64),
  requested_at timestamptz not null default now(),
  completed_at timestamptz,
  last_restore_check_at timestamptz
);

create index account_deletion_tombstones_user_idx
  on public.account_deletion_tombstones (user_id, requested_at desc);

alter table public.account_deletion_tombstones enable row level security;
-- Service-role only. The ledger is moved through the operator restore command.
