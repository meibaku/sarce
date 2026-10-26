-- LE2.5: expiring, single-use admission. Only hashes cross the persistence boundary;
-- the API returns each plaintext token exactly once when an operator creates a batch.
create table if not exists public.learning_invite_batches (
  id uuid primary key,
  created_by uuid not null references auth.users (id),
  protocol_version integer not null check (protocol_version > 0),
  cohort text not null check (cohort in ('qualitative', 'controlled')),
  invite_count integer not null check (invite_count > 0 and invite_count % 2 = 0),
  expires_at timestamptz not null,
  created_at timestamptz not null default now(),
  check (expires_at > created_at)
);

create table if not exists public.learning_invites (
  id uuid primary key,
  batch_id uuid not null references public.learning_invite_batches (id),
  token_hash text not null unique check (token_hash ~ '^[0-9a-f]{64}$'),
  arm text not null check (arm in ('experimental', 'active_control')),
  expires_at timestamptz not null,
  redeemed_at timestamptz,
  redeemed_by uuid references auth.users (id),
  created_at timestamptz not null default now(),
  check ((redeemed_at is null) = (redeemed_by is null)),
  check (redeemed_at is null or redeemed_at <= expires_at)
);

create index if not exists learning_invites_batch_idx on public.learning_invites (batch_id);

alter table public.learning_invite_batches enable row level security;
alter table public.learning_invites enable row level security;

grant select, insert on public.learning_invite_batches to service_role;
grant select, insert, update on public.learning_invites to service_role;

-- Persist the batch and every invitation together. JSON input keeps plaintext tokens
-- out of PostgreSQL while the function enforces the balancing contract independently.
create or replace function public.create_learning_invite_batch(
  p_batch jsonb,
  p_invites jsonb
) returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  batch_id uuid := (p_batch->>'id')::uuid;
  invite_count integer := (p_batch->>'invite_count')::integer;
  experimental_count integer;
  control_count integer;
begin
  if jsonb_typeof(p_invites) <> 'array' or jsonb_array_length(p_invites) <> invite_count then
    raise exception 'invitation count does not match batch';
  end if;
  select
    count(*) filter (where item->>'arm' = 'experimental'),
    count(*) filter (where item->>'arm' = 'active_control')
  into experimental_count, control_count
  from jsonb_array_elements(p_invites) item;
  if experimental_count <> invite_count / 2 or control_count <> invite_count / 2 then
    raise exception 'invitation batch is not evenly assigned';
  end if;

  insert into public.learning_invite_batches (
    id, created_by, protocol_version, cohort, invite_count, expires_at, created_at
  ) values (
    batch_id, (p_batch->>'created_by')::uuid, (p_batch->>'protocol_version')::integer,
    p_batch->>'cohort', invite_count, (p_batch->>'expires_at')::timestamptz,
    (p_batch->>'created_at')::timestamptz
  );
  insert into public.learning_invites (id, batch_id, token_hash, arm, expires_at, created_at)
  select
    (item->>'id')::uuid, batch_id, item->>'token_hash', item->>'arm',
    (item->>'expires_at')::timestamptz, (item->>'created_at')::timestamptz
  from jsonb_array_elements(p_invites) item;
  return batch_id;
end;
$$;

revoke all on function public.create_learning_invite_batch(jsonb, jsonb) from public, anon, authenticated;
grant execute on function public.create_learning_invite_batch(jsonb, jsonb) to service_role;

-- Locking the invitation and creating the enrollment in one transaction prevents
-- two concurrent requests from consuming the same invitation.
create or replace function public.redeem_learning_invite(
  p_token_hash text,
  p_user_id uuid,
  p_adult_confirmed boolean,
  p_consented_at timestamptz
) returns public.learning_enrollments
language plpgsql
security definer
set search_path = public
as $$
declare
  invite public.learning_invites%rowtype;
  batch public.learning_invite_batches%rowtype;
  enrollment public.learning_enrollments%rowtype;
begin
  if not p_adult_confirmed then
    raise exception 'adult confirmation is required';
  end if;

  select * into invite
    from public.learning_invites
    where token_hash = p_token_hash
    for update;
  if not found or invite.redeemed_at is not null or invite.expires_at <= now() then
    raise exception 'invitation is invalid, expired, or already used';
  end if;

  select * into strict batch
    from public.learning_invite_batches
    where id = invite.batch_id;

  insert into public.learning_enrollments (
    user_id, protocol_version, cohort, arm, adult_confirmed, consented_at
  ) values (
    p_user_id, batch.protocol_version, batch.cohort, invite.arm, true, p_consented_at
  ) returning * into enrollment;

  update public.learning_invites
    set redeemed_at = now(), redeemed_by = p_user_id
    where id = invite.id;
  return enrollment;
end;
$$;

revoke all on function public.redeem_learning_invite(text, uuid, boolean, timestamptz) from public, anon, authenticated;
grant execute on function public.redeem_learning_invite(text, uuid, boolean, timestamptz) to service_role;
