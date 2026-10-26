-- Independent validation must be held out from detector tuning; make the split explicit and queryable.
alter table public.pattern_instances
  add column if not exists review_set text not null default 'calibration'
  check (review_set in ('calibration', 'heldout'));

create index if not exists pattern_instances_review_set_idx
  on public.pattern_instances (concept_key, review_set, review_status);
