"""HTTP contract (Pydantic). Validates input and maps it to domain entities."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.domain import entities


class Strict(BaseModel):
    # Unknown fields are rejected so a description or a session id cannot slip
    # through to the language model by accident.
    model_config = ConfigDict(extra="forbid")


# ---- request ---------------------------------------------------------------


class CheckInIn(Strict):
    """A `check_ins` row without `session_id`, `description` and timestamps."""

    id: str = Field(min_length=1)
    check_in_date: date
    sleep_hours: float = Field(strict=True, ge=0, le=24)
    stress_level: int = Field(strict=True, ge=1, le=5)
    mood_level: int = Field(strict=True, ge=1, le=5)
    team_conflict_level: int = Field(strict=True, ge=1, le=5)
    fatigue: int = Field(strict=True, ge=1, le=7)

    def to_domain(self) -> entities.CheckIn:
        return entities.CheckIn(**self.model_dump())


class ReadyForecastIn(Strict):
    status: Literal["ready"]
    probability_high_fatigue: float = Field(strict=True, ge=0, le=1)
    model_version: str = Field(min_length=1, max_length=128)
    predicted_at: str = Field(min_length=1)


class InsufficientHistoryIn(Strict):
    status: Literal["insufficient_history"]


class UnavailableIn(Strict):
    status: Literal["unavailable"]


ForecastIn = Annotated[
    ReadyForecastIn | InsufficientHistoryIn | UnavailableIn, Field(discriminator="status")
]


class RecommendationRequest(Strict):
    # Oldest first; the last one is today's check-in.
    check_ins: list[CheckInIn] = Field(min_length=1, max_length=90)
    # Absent, insufficient or unavailable means no forecast task; the card and
    # the check-in task are still produced from the check-ins alone.
    forecast: ForecastIn | None = None

    @model_validator(mode="after")
    def ordered_unique_dates(self) -> "RecommendationRequest":
        dates = [c.check_in_date for c in self.check_ins]
        if any(a >= b for a, b in zip(dates, dates[1:])):
            raise ValueError("check_ins must be ordered by date, oldest first, one per date.")
        return self

    def domain_check_ins(self) -> list[entities.CheckIn]:
        return [c.to_domain() for c in self.check_ins]

    def domain_forecast(self) -> entities.Forecast | None:
        match self.forecast:
            case ReadyForecastIn() as f:
                return entities.ReadyForecast(
                    f.probability_high_fatigue, f.model_version, f.predicted_at
                )
            case InsufficientHistoryIn():
                return entities.InsufficientHistory()
            case UnavailableIn():
                return entities.Unavailable()
            case _:
                return None


# ---- response --------------------------------------------------------------


class FromDomain(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class IndicatorFactOut(FromDomain):
    # Hours for sleep (can have decimals); a whole number for the 1-5 and 1-7 scales.
    current: int | float
    baseline_mean: float | None
    delta: float | None
    direction: Literal["up", "down", "same"] | None


class ForecastFactOut(FromDomain):
    probability_high_fatigue: float
    model_version: str


class FactsOut(FromDomain):
    check_in_id: str
    check_in_date: date
    comparison: Literal["available", "no_history"]
    compared_check_ins: int
    indicators: dict[entities.Indicator, IndicatorFactOut]
    forecast: ForecastFactOut | None


class ForecastSnapshotOut(FromDomain):
    probability_high_fatigue: float
    model_version: str
    predicted_at: str


class TaskOut(FromDomain):
    """One row for `check_in_actions`."""

    task_key: str
    title: str
    source: Literal["forecast", "check_in"]
    kind: Literal["task"]
    action_code: Literal["monitor", "recheck"]
    reason_code: str
    ruleset_version: str
    status: Literal["suggested"]
    forecast_snapshot: ForecastSnapshotOut | None


class InsightOut(FromDomain):
    """The card; maps to `check_in_insights`."""

    title: str
    summary: str
    # The line under the summary on the card.
    next_step: str
    facts: FactsOut
    source: Literal["ai", "fallback"]
    # Provider and model when `source` is "ai"; null for the fallback.
    generator: str | None


class RecommendationResponse(FromDomain):
    insight: InsightOut
    tasks: list[TaskOut]
