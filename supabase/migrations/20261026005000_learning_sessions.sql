-- LE2.4: fixed, non-adaptive session manifests and answer-safe presentations.
alter table public.pattern_instances drop constraint if exists pattern_instances_bank_partition_check;
alter table public.pattern_instances add constraint pattern_instances_bank_partition_check
  check (bank_partition in ('baseline', 'instruction', 'immediate', 'day7', 'day28', 'transfer'));

create table if not exists public.learning_sessions (
  id uuid primary key,
  enrollment_id uuid not null references public.learning_enrollments (id),
  phase text not null check (phase in ('baseline', 'learning', 'immediate', 'day7', 'day28')),
  protocol_version integer not null check (protocol_version > 0),
  item_count integer not null check (item_count in (4, 9, 18)),
  created_at timestamptz not null default now(),
  completed_at timestamptz,
  unique (enrollment_id, phase)
);

create table if not exists public.learning_presentations (
  id uuid primary key,
  session_id uuid not null references public.learning_sessions (id),
  enrollment_id uuid not null references public.learning_enrollments (id),
  pattern_id uuid not null references public.pattern_instances (id),
  presentation_token uuid not null unique,
  ordinal smallint not null check (ordinal > 0),
  family_key text not null,
  item_label text not null check (item_label in ('positive', 'near_miss', 'control')),
  presented_at timestamptz,
  responded_at timestamptz,
  unique (session_id, ordinal),
  unique (enrollment_id, pattern_id),
  check (responded_at is null or presented_at is not null),
  check (responded_at is null or responded_at >= presented_at)
);

create index if not exists learning_presentations_next_idx
  on public.learning_presentations (session_id, ordinal) where responded_at is null;
create index if not exists learning_presentations_family_idx
  on public.learning_presentations (enrollment_id, family_key);

alter table public.learning_sessions enable row level security;
alter table public.learning_presentations enable row level security;
grant select, insert, update on public.learning_sessions to service_role;
grant select, insert, update on public.learning_presentations to service_role;

create or replace function public.create_learning_session(p_session jsonb, p_presentations jsonb)
returns uuid
language plpgsql security definer set search_path = public
as $$
declare
  session_id uuid := (p_session->>'id')::uuid;
  expected integer := (p_session->>'item_count')::integer;
begin
  if jsonb_typeof(p_presentations) <> 'array' or jsonb_array_length(p_presentations) <> expected then
    raise exception 'presentation count does not match session';
  end if;
  insert into public.learning_sessions (id, enrollment_id, phase, protocol_version, item_count, created_at)
  values (
    session_id, (p_session->>'enrollment_id')::uuid, p_session->>'phase',
    (p_session->>'protocol_version')::integer, expected, (p_session->>'created_at')::timestamptz
  );
  insert into public.learning_presentations (
    id, session_id, enrollment_id, pattern_id, presentation_token, ordinal, family_key, item_label
  ) select
    (item->>'id')::uuid, session_id, (p_session->>'enrollment_id')::uuid,
    (item->>'pattern_id')::uuid, (item->>'presentation_token')::uuid,
    (item->>'ordinal')::smallint, item->>'family_key', item->>'item_label'
  from jsonb_array_elements(p_presentations) item;
  return session_id;
end;
$$;

create or replace function public.next_learning_presentation(p_session_id uuid, p_enrollment_id uuid)
returns jsonb
language plpgsql security definer set search_path = public
as $$
declare
  presentation public.learning_presentations%rowtype;
  pattern public.pattern_instances%rowtype;
begin
  select * into presentation from public.learning_presentations
    where session_id = p_session_id and enrollment_id = p_enrollment_id and responded_at is null
    order by ordinal limit 1 for update;
  if not found then return null; end if;
  update public.learning_presentations set presented_at = coalesce(presented_at, now())
    where id = presentation.id returning * into presentation;
  select * into strict pattern from public.pattern_instances where id = presentation.pattern_id;
  return jsonb_build_object(
    'presentationToken', presentation.presentation_token,
    'ordinal', presentation.ordinal,
    'positionFen', pattern.position_fen,
    'conceptKey', pattern.concept_key,
    'familyKey', pattern.family_key,
    'sourceType', pattern.source_type,
    'difficultyContext', pattern.difficulty_context,
    'presentedAt', presentation.presented_at
  );
end;
$$;

revoke all on function public.create_learning_session(jsonb, jsonb) from public, anon, authenticated;
revoke all on function public.next_learning_presentation(uuid, uuid) from public, anon, authenticated;
grant execute on function public.create_learning_session(jsonb, jsonb) to service_role;
grant execute on function public.next_learning_presentation(uuid, uuid) to service_role;
