"""Which tasks exist and what each one is. Decided by rules, never by the model.

Each task is one `TaskPolicy`. Adding a task means adding a policy and
registering it in the composition root; `TaskPlanner` does not change.
Thresholds are for the demo's synthetic data, not clinical thresholds.
"""

from collections.abc import Sequence
from typing import Protocol

from app.domain.entities import (
    Facts,
    Forecast,
    ForecastSnapshot,
    ReadyForecast,
    TaskSpec,
)


class TaskPolicy(Protocol):
    def plan(self, facts: Facts, forecast: Forecast | None) -> TaskSpec | None:
        """The task this policy wants, or None when it has nothing to suggest."""
        ...


class CheckInFollowUpPolicy:
    """Always suggests a follow-up from the daily check-in."""

    ruleset_version = "ceres-check-in-v1"

    def __init__(self, sleep_drop_hours: float = 1.0, fatigue_rise_points: float = 1.0) -> None:
        self._sleep_drop = sleep_drop_hours
        self._fatigue_rise = fatigue_rise_points

    def plan(self, facts: Facts, forecast: Forecast | None) -> TaskSpec | None:
        sleep = facts.indicators["sleep_hours"].delta
        fatigue = facts.indicators["fatigue"].delta
        worsened = (sleep is not None and sleep <= -self._sleep_drop) or (
            fatigue is not None and fatigue >= self._fatigue_rise
        )
        return TaskSpec(
            task_key="check_in_follow_up",
            source="check_in",
            action_code="recheck" if worsened else "monitor",
            reason_code=(
                "check_in_sleep_or_fatigue_worsened"
                if worsened
                else "check_in_stable_or_no_history"
            ),
            ruleset_version=self.ruleset_version,
            default_title=(
                "Record your sleep and fatigue again at your next check-in"
                if worsened
                else "Keep tracking your daily check-ins"
            ),
        )


class ForecastFollowUpPolicy:
    """Suggests a follow-up from the Eres forecast, only when it has a result."""

    # Same display policy and threshold as Check-in Actions uses today.
    ruleset_version = "demo-follow-up-v1"

    def __init__(self, recheck_probability: float = 0.5) -> None:
        self._recheck_probability = recheck_probability

    def plan(self, facts: Facts, forecast: Forecast | None) -> TaskSpec | None:
        if not isinstance(forecast, ReadyForecast):
            return None
        recheck = forecast.probability_high_fatigue >= self._recheck_probability
        return TaskSpec(
            task_key="forecast_follow_up",
            source="forecast",
            action_code="recheck" if recheck else "monitor",
            reason_code=(
                "forecast_at_or_above_demo_threshold"
                if recheck
                else "forecast_below_demo_threshold"
            ),
            ruleset_version=self.ruleset_version,
            default_title=(
                "Review your records and make a new check-in when appropriate"
                if recheck
                else "Check the fatigue estimate again at your next check-in"
            ),
            forecast_snapshot=ForecastSnapshot(
                probability_high_fatigue=forecast.probability_high_fatigue,
                model_version=forecast.model_version,
                predicted_at=forecast.predicted_at,
            ),
        )


class TaskPlanner:
    def __init__(self, policies: Sequence[TaskPolicy]) -> None:
        self._policies = tuple(policies)

    def plan(self, facts: Facts, forecast: Forecast | None) -> list[TaskSpec]:
        specs = (policy.plan(facts, forecast) for policy in self._policies)
        return [spec for spec in specs if spec is not None]
