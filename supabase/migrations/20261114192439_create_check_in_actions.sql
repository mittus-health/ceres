create table public.check_in_actions (
  id uuid primary key default gen_random_uuid(),
  check_in_id uuid not null references public.check_ins(id) on delete cascade,
  evaluation_key text not null check (btrim(evaluation_key) <> ''),
  action_code text not null check (action_code in (
    'monitor', 'recheck', 'contact_crew', 'contact_medical'
  )),
  reason_code text not null check (btrim(reason_code) <> ''),
  ruleset_version text not null check (btrim(ruleset_version) <> ''),
  forecast_snapshot jsonb not null,
  status text not null default 'suggested' check (status in (
    'suggested', 'acknowledged', 'completed', 'dismissed', 'superseded'
  )),
  created_at timestamptz not null default now(),
  acknowledged_at timestamptz,
  resolved_at timestamptz,

  constraint check_in_actions_evaluation_action_key
    unique (check_in_id, evaluation_key, action_code),

  constraint check_in_actions_forecast_snapshot_check check (
    jsonb_typeof(forecast_snapshot) = 'object'
    and jsonb_typeof(forecast_snapshot -> 'model_version') is not distinct from 'string'
    and btrim(forecast_snapshot ->> 'model_version') <> ''
    and jsonb_typeof(forecast_snapshot -> 'predicted_at') is not distinct from 'string'
    and btrim(forecast_snapshot ->> 'predicted_at') <> ''
    and case when jsonb_typeof(forecast_snapshot -> 'probability_high_fatigue') = 'number'
      then (forecast_snapshot ->> 'probability_high_fatigue')::numeric between 0 and 1
      else false
    end
  ),

  constraint check_in_actions_status_timestamps_check check (
    (
      (status = 'suggested' and acknowledged_at is null and resolved_at is null)
      or (status = 'acknowledged' and acknowledged_at is not null and resolved_at is null)
      or (status in ('completed', 'dismissed', 'superseded') and resolved_at is not null)
    )
    and (acknowledged_at is null or acknowledged_at >= created_at)
    and (resolved_at is null or resolved_at >= coalesce(acknowledged_at, created_at))
  )
);

create index check_in_actions_check_in_created_idx
  on public.check_in_actions (check_in_id, created_at desc);

alter table public.check_in_actions enable row level security;
revoke all on table public.check_in_actions from public, anon, authenticated;
