-- Fixed-snapshot Maia backfills enumerate one checkpoint at a time. The primary key starts with
-- fen_key, so a model-only cache scan otherwise becomes a sequential scan and times out as the
-- shared probability cache grows.
create index if not exists human_probs_model_version_idx
  on public.human_probs (model_version, fen_key, elo);
