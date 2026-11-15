import pytest

from app.domain.entities import InsufficientHistory, ReadyForecast, TaskSpec, Unavailable
from app.domain.facts import FactsCalculator
from app.domain.task_policies import CheckInFollowUpPolicy, ForecastFollowUpPolicy, TaskPlanner
from tests.factories import EARLIER, HISTORY, READY, TODAY, check_in

calc = FactsCalculator()
planner = TaskPlanner([CheckInFollowUpPolicy(), ForecastFollowUpPolicy()])


def plan(history, forecast=None):
    return planner.plan(calc.calculate(history, forecast), forecast)


def test_check_in_and_forecast_tasks():
    specs = plan(HISTORY, READY)
    assert [(s.task_key, s.source, s.action_code) for s in specs] == [
        ("check_in_follow_up", "check_in", "recheck"),  # fatigue +1.5
        ("forecast_follow_up", "forecast", "monitor"),  # 0.38 < 0.5
    ]
    assert specs[0].forecast_snapshot is None
    assert specs[1].forecast_snapshot.predicted_at == "2026-11-14T12:00:00.000Z"
    assert specs[1].ruleset_version == "demo-follow-up-v1"


@pytest.mark.parametrize("forecast", [None, InsufficientHistory(), Unavailable()])
def test_no_forecast_task_without_an_eres_result(forecast):
    assert [s.task_key for s in plan(HISTORY, forecast)] == ["check_in_follow_up"]


def test_forecast_recheck_at_the_existing_threshold():
    high = ReadyForecast(0.5, "eres-v2", "2026-11-14T12:00:00.000Z")
    spec = plan(HISTORY, high)[1]
    assert (spec.action_code, spec.reason_code) == ("recheck", "forecast_at_or_above_demo_threshold")


def test_stable_check_in_is_monitor():
    assert plan([*EARLIER, check_in(7, 6.7, 3)])[0].action_code == "monitor"


def test_first_check_in_is_monitor():
    assert plan([TODAY])[0].action_code == "monitor"


@pytest.mark.parametrize(
    "today, expected",
    [
        (check_in(7, 5.7, 4), "recheck"),  # sleep exactly 1 h below the 6.7 average
        (check_in(7, 5.8, 4), "monitor"),  # 0.9 h below, fatigue +0.5
        (check_in(7, 6.7, 5), "recheck"),  # fatigue +1.5
    ],
)
def test_check_in_thresholds(today, expected):
    assert plan([*EARLIER, today])[0].action_code == expected


def test_thresholds_are_injected_not_hard_coded():
    strict = TaskPlanner([CheckInFollowUpPolicy(sleep_drop_hours=0.1)])
    assert strict.plan(calc.calculate([*EARLIER, check_in(7, 6.5, 3)], None), None)[0].action_code == "recheck"


def test_planner_accepts_any_policy():
    class Always:
        def plan(self, facts, forecast):
            return TaskSpec("extra", "check_in", "monitor", "r", "v", "Extra")

    specs = TaskPlanner([Always()]).plan(calc.calculate(HISTORY, None), None)
    assert [s.task_key for s in specs] == ["extra"]
