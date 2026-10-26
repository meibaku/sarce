-- ADR 0011: adopt the evidence-backed percentage-point bands without overwriting a player's custom goal.
alter table public.profiles
  alter column style_goal set default '{"target_brilliant_min": 0.2, "target_brilliant_max": 0.6}'::jsonb;

update public.profiles
set style_goal = '{"target_brilliant_min": 0.2, "target_brilliant_max": 0.6}'::jsonb,
    updated_at = now()
where style_goal = '{"target_brilliant_min": 6, "target_brilliant_max": 10}'::jsonb;

alter table public.user_baselines
  alter column target_brilliant_min set default 0.2,
  alter column target_brilliant_max set default 0.6;

update public.user_baselines
set target_brilliant_min = 0.2,
    target_brilliant_max = 0.6,
    updated_at = now()
where target_brilliant_min = 6 and target_brilliant_max = 10;
