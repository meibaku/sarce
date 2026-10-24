-- First-import and first-read milestones (plan 3.1), written atomically: the key is added only when absent, and
-- the rest of profiles.settings is left as it is in the row, so a concurrent settings save can't be overwritten
-- by a stale copy (and can't erase the milestone either). Called by the API with the service role.
create or replace function public.record_profile_milestone(owner uuid, milestone text, at text)
returns boolean
language sql
security invoker
set search_path = public
as $$
  with updated as (
    update public.profiles
       set settings = coalesce(settings, '{}'::jsonb) || jsonb_build_object(milestone, at)
     where id = owner
       and milestone in ('firstImportAt', 'firstReadAt')
       and not (coalesce(settings, '{}'::jsonb) ? milestone)
    returning 1
  )
  select exists (select 1 from updated);
$$;

revoke all on function public.record_profile_milestone(uuid, text, text) from public, anon, authenticated;
grant execute on function public.record_profile_milestone(uuid, text, text) to service_role;
