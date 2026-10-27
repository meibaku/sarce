-- Preserve both independent votes when reviewers submit against the same candidate concurrently.
create or replace function public.append_pattern_review_annotation(
  p_pattern_id uuid,
  p_reviewer text,
  p_decision text,
  p_note text
) returns public.pattern_instances
language plpgsql
security definer
set search_path = public
as $$
declare
  pattern public.pattern_instances%rowtype;
  annotation jsonb;
begin
  if length(trim(p_reviewer)) = 0 or length(p_reviewer) > 80 then
    raise exception 'reviewer is required';
  end if;
  if p_decision not in ('approve', 'reject', 'unclear') then
    raise exception 'invalid review decision';
  end if;
  if length(coalesce(p_note, '')) > 500 then
    raise exception 'review note is too long';
  end if;

  select * into pattern
    from public.pattern_instances
    where id = p_pattern_id and review_status = 'candidate'
    for update;
  if not found then
    raise exception 'candidate pattern not found';
  end if;
  if exists (
    select 1 from jsonb_array_elements(pattern.review_annotations) item
    where item->>'reviewer' = trim(p_reviewer)
  ) then
    raise exception 'reviewer already annotated this pattern';
  end if;

  annotation := jsonb_build_object(
    'reviewer', trim(p_reviewer),
    'decision', p_decision,
    'note', trim(coalesce(p_note, '')),
    'at', now()
  );
  update public.pattern_instances
    set review_annotations = pattern.review_annotations || jsonb_build_array(annotation),
        annotation_count = pattern.annotation_count + 1,
        updated_at = now()
    where id = pattern.id
    returning * into pattern;
  return pattern;
end;
$$;

revoke all on function public.append_pattern_review_annotation(uuid, text, text, text)
  from public, anon, authenticated;
grant execute on function public.append_pattern_review_annotation(uuid, text, text, text)
  to service_role;
