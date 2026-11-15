import pytest

from app.domain.entities import InsufficientHistory, Unavailable
from app.domain.facts import FactsCalculator
from tests.factories import EARLIER, HISTORY, READY, TODAY, check_in

calc = FactsCalculator(window=7)


def test_compares_latest_with_earlier_excluding_itself():
    facts = calc.calculate(HISTORY, None)
    assert facts.comparison == "available" and facts.compared_check_ins == 6
    sleep, fatigue = facts.indicators["sleep_hours"], facts.indicators["fatigue"]
    assert (sleep.current, sleep.baseline_mean, sleep.delta, sleep.direction) == (6.5, 6.7, -0.2, "down")
    assert (fatigue.current, fatigue.baseline_mean, fatigue.delta, fatigue.direction) == (5, 3.5, 1.5, "up")
    assert facts.indicators["stress_level"].direction == "same"


def test_uses_at_most_seven_previous_check_ins():
    long = [check_in(i + 1, 1.0 if i == 0 else 8.0, 3) for i in range(10)]
    facts = calc.calculate([*long, check_in(11, 8.0, 3)], None)
    assert facts.compared_check_ins == 7
    assert facts.indicators["sleep_hours"].baseline_mean == 8.0  # the 1 h record is outside the window


def test_window_is_configurable():
    assert FactsCalculator(window=2).calculate(HISTORY, None).compared_check_ins == 2


def test_single_check_in_has_no_comparison():
    facts = calc.calculate([TODAY], None)
    assert facts.comparison == "no_history"
    fatigue = facts.indicators["fatigue"]
    assert (fatigue.baseline_mean, fatigue.delta, fatigue.direction) == (None, None, None)


def test_forecast_numbers_only_when_ready():
    assert calc.calculate(HISTORY, None).forecast is None
    assert calc.calculate(HISTORY, InsufficientHistory()).forecast is None
    assert calc.calculate(HISTORY, Unavailable()).forecast is None
    forecast = calc.calculate(HISTORY, READY).forecast
    assert (forecast.probability_high_fatigue, forecast.model_version) == (0.38, "eres-v2")


def test_requires_at_least_one_check_in():
    with pytest.raises(ValueError):
        calc.calculate([], None)


def test_earlier_list_is_not_mutated():
    before = list(EARLIER)
    calc.calculate([*EARLIER, TODAY], None)
    assert EARLIER == before
