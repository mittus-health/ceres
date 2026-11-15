"""Domain entities. Plain data: no framework, no I/O."""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

Indicator = Literal[
    "sleep_hours", "fatigue", "mood_level", "stress_level", "team_conflict_level"
]
INDICATORS: tuple[Indicator, ...] = (
    "sleep_hours",
    "fatigue",
    "mood_level",
    "stress_level",
    "team_conflict_level",
)

TaskSource = Literal["forecast", "check_in"]
ActionCode = Literal["monitor", "recheck"]


@dataclass(frozen=True, slots=True)
class CheckIn:
    id: str
    check_in_date: date
    sleep_hours: float
    stress_level: int
    mood_level: int
    team_conflict_level: int
    fatigue: int


@dataclass(frozen=True, slots=True)
class ReadyForecast:
    probability_high_fatigue: float
    model_version: str
    predicted_at: str


@dataclass(frozen=True, slots=True)
class InsufficientHistory:
    pass


@dataclass(frozen=True, slots=True)
class Unavailable:
    pass


# Only `ReadyForecast` carries a result; the others mean "no forecast task".
Forecast = ReadyForecast | InsufficientHistory | Unavailable


@dataclass(frozen=True, slots=True)
class IndicatorFact:
    current: int | float
    # Mean of the previous check-ins; None without history.
    baseline_mean: float | None
    # current - baseline_mean, one decimal; None without history.
    delta: float | None
    direction: Literal["up", "down", "same"] | None


@dataclass(frozen=True, slots=True)
class ForecastFact:
    probability_high_fatigue: float
    model_version: str


@dataclass(frozen=True, slots=True)
class Facts:
    """Numbers computed in code and handed to the text writer."""

    check_in_id: str
    check_in_date: date
    comparison: Literal["available", "no_history"]
    compared_check_ins: int
    indicators: dict[Indicator, IndicatorFact]
    forecast: ForecastFact | None


@dataclass(frozen=True, slots=True)
class ForecastSnapshot:
    probability_high_fatigue: float
    model_version: str
    predicted_at: str


@dataclass(frozen=True, slots=True)
class Task:
    """A checklist task, ready to be saved as one `check_in_actions` row."""

    task_key: str
    title: str
    source: TaskSource
    action_code: ActionCode
    reason_code: str
    ruleset_version: str
    kind: Literal["task"] = "task"
    status: Literal["suggested"] = "suggested"
    forecast_snapshot: ForecastSnapshot | None = None


@dataclass(frozen=True, slots=True)
class TaskSpec:
    """A task decided by rules, before its title is worded."""

    task_key: str
    source: TaskSource
    action_code: ActionCode
    reason_code: str
    ruleset_version: str
    default_title: str
    forecast_snapshot: ForecastSnapshot | None = None

    def titled(self, title: str) -> Task:
        return Task(
            task_key=self.task_key,
            title=title,
            source=self.source,
            action_code=self.action_code,
            reason_code=self.reason_code,
            ruleset_version=self.ruleset_version,
            forecast_snapshot=self.forecast_snapshot,
        )


@dataclass(frozen=True, slots=True)
class GeneratedText:
    """Wording for the card and the task titles."""

    title: str
    summary: str
    next_step: str
    # Exactly one title per planned task, keyed by `task_key`.
    task_titles: dict[str, str] = field(default_factory=dict)
    # Provider and model that wrote it; None for the deterministic text.
    author: str | None = None


@dataclass(frozen=True, slots=True)
class Insight:
    title: str
    summary: str
    next_step: str
    facts: Facts
    source: Literal["ai", "fallback"]
    generator: str | None


@dataclass(frozen=True, slots=True)
class Recommendation:
    insight: Insight
    tasks: list[Task]
