-- Each row of public.check_in_actions becomes one checklist task ("My plan").
--
-- Before: one action per evaluation, identified by (check_in_id, evaluation_key,
-- action_code), always backed by an Eres forecast snapshot.
-- After: an evaluation produces several tasks (at least one per source the
-- evaluation had data for). A task has a title, a stable task_key within its
-- evaluation, a source (what it was derived from) and a kind (how the app
-- renders it). The daily insight card lives in public.check_in_insights and is
-- linked by (check_in_id, evaluation_key).
--
-- The current backend inserts actions without these columns; it must be updated
-- together with this migration.

alter table public.check_in_actions
  add column task_key text,
  add column title text,
  add column source text,
  add column kind text;

-- Existing rows are forecast-driven actions from the previous rules.
update public.check_in_actions
set task_key = 'forecast_follow_up',
    source = 'forecast',
    kind = 'task',
    title = case action_code
      when 'monitor' then 'Keep tracking your daily check-ins'
      when 'recheck' then 'Record a new check-in'
      when 'contact_crew' then 'Talk to your crew'
      when 'contact_medical' then 'Contact the medical team'
    end;

alter table public.check_in_actions
  alter column task_key set not null,
  alter column title set not null,
  alter column source set not null,
  alter column kind set not null,
  alter column kind set default 'task',
  -- Only tasks that come from the forecast carry a snapshot of it.
  alter column forecast_snapshot drop not null;

alter table public.check_in_actions
  add constraint check_in_actions_task_key_check
    check (task_key ~ '^[a-z0-9_]+$'),
  add constraint check_in_actions_title_check
    check (btrim(title) <> ''),
  -- forecast = derived from the Eres result; check_in = derived from the daily
  -- check-in data; system = created by the app (e.g. "Save today's check-in").
  add constraint check_in_actions_source_check
    check (source in ('forecast', 'check_in', 'system')),
  -- task = a plain task; review_insight = opens the daily insight card.
  add constraint check_in_actions_kind_check
    check (kind in ('task', 'review_insight')),
  add constraint check_in_actions_forecast_snapshot_source_check
    check (source <> 'forecast' or forecast_snapshot is not null);

-- The snapshot shape check rejects NULL (its string checks evaluate to false),
-- so recreate it to apply only when a snapshot is present.
alter table public.check_in_actions
  drop constraint check_in_actions_forecast_snapshot_check,
  add constraint check_in_actions_forecast_snapshot_check check (
    forecast_snapshot is null
    or (
      jsonb_typeof(forecast_snapshot) = 'object'
      and jsonb_typeof(forecast_snapshot -> 'model_version') is not distinct from 'string'
      and btrim(forecast_snapshot ->> 'model_version') <> ''
      and jsonb_typeof(forecast_snapshot -> 'predicted_at') is not distinct from 'string'
      and btrim(forecast_snapshot ->> 'predicted_at') <> ''
      and case when jsonb_typeof(forecast_snapshot -> 'probability_high_fatigue') = 'number'
        then (forecast_snapshot ->> 'probability_high_fatigue')::numeric between 0 and 1
        else false
      end
    )
  );

-- Several tasks per evaluation: the task, not the action code, identifies a row.
alter table public.check_in_actions
  drop constraint check_in_actions_evaluation_action_key,
  add constraint check_in_actions_evaluation_task_key
    unique (check_in_id, evaluation_key, task_key);
