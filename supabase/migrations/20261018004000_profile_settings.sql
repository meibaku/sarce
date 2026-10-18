-- v1.0 Settings (docs/DESIGN.md): per-player preferences beside the existing style goal —
-- question budget, quiet week, sources, theme, mascot and motion. Kept as one jsonb document so
-- adding a preference does not need a migration; the API validates the keys.
alter table public.profiles
  add column if not exists settings jsonb not null default '{}'::jsonb;
