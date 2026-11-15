-- Daily AI insight card ("Make sense of the changes" -> AI recommendation).
--
-- One row per evaluation of a check-in: a short title and summary written by the
-- language model (or the fallback text) from numbers the backend computed out of
-- the session's check-ins and, when available, the Eres forecast. The checklist
-- tasks stay in public.check_in_actions; they share (check_in_id, evaluation_key)
-- with their insight.
--
-- Same lifecycle as the actions: a correction to the check-in changes the
-- evaluation_key, the backend inserts a new insight and marks the previous one
-- as superseded in the same transaction.

create table public.check_in_insights (
  id uuid primary key default gen_random_uuid(),
  check_in_id uuid not null references public.check_ins(id) on delete cascade,
  evaluation_key text not null check (btrim(evaluation_key) <> ''),
  title text not null check (btrim(title) <> ''),
  summary text not null check (btrim(summary) <> ''),
  -- Numbers computed by the backend and given to the model, e.g. sleep and
  -- fatigue against the average of the previous check-ins. Not model output.
  facts jsonb not null check (jsonb_typeof(facts) = 'object'),
  -- 'ai' = text written by the language model; 'fallback' = versioned default text.
  source text not null check (source in ('ai', 'fallback')),
  -- Provider and model that wrote the text; null for the fallback. Free text
  -- because the provider is not decided yet.
  generator text check (generator is null or btrim(generator) <> ''),
  created_at timestamptz not null default now(),
  superseded_at timestamptz,

  constraint check_in_insights_evaluation_key unique (check_in_id, evaluation_key),
  constraint check_in_insights_source_generator_check check (
    (source = 'ai' and generator is not null)
    or (source = 'fallback' and generator is null)
  ),
  constraint check_in_insights_superseded_check check (
    superseded_at is null or superseded_at >= created_at
  )
);

create index check_in_insights_check_in_created_idx
  on public.check_in_insights (check_in_id, created_at desc);

-- At most one current insight per check-in.
create unique index check_in_insights_current_idx
  on public.check_in_insights (check_in_id)
  where superseded_at is null;

-- Server-only access, like the other tables: RLS on, no policies, and no
-- grants for the public API roles. The backend reads it through DATABASE_URL
-- after checking check_ins.session_id.
alter table public.check_in_insights enable row level security;
revoke all on table public.check_in_insights from public, anon, authenticated;
