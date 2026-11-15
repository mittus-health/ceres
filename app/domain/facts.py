from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal

from app.domain.entities import (
    INDICATORS,
    CheckIn,
    Facts,
    Forecast,
    ForecastFact,
    IndicatorFact,
    ReadyForecast,
)

_ONE_DECIMAL = Decimal("0.1")


def _one_decimal(value: Decimal) -> float:
    return float(value.quantize(_ONE_DECIMAL, rounding=ROUND_HALF_UP))


class FactsCalculator:
    """Compares the latest check-in with the ones before it.

    The latest check-in is left out of its own baseline.
    """

    def __init__(self, window: int = 7) -> None:
        self._window = window

    def calculate(self, check_ins: Sequence[CheckIn], forecast: Forecast | None) -> Facts:
        """`check_ins` is oldest first; the last one is the current check-in."""
        if not check_ins:
            raise ValueError("At least one check-in is required.")
        current = check_ins[-1]
        previous = list(check_ins[-(self._window + 1) : -1])
        return Facts(
            check_in_id=current.id,
            check_in_date=current.check_in_date,
            comparison="available" if previous else "no_history",
            compared_check_ins=len(previous),
            indicators={name: self._indicator(name, current, previous) for name in INDICATORS},
            forecast=(
                ForecastFact(forecast.probability_high_fatigue, forecast.model_version)
                if isinstance(forecast, ReadyForecast)
                else None
            ),
        )

    @staticmethod
    def _indicator(name: str, current: CheckIn, previous: list[CheckIn]) -> IndicatorFact:
        value = getattr(current, name)
        if not previous:
            return IndicatorFact(value, None, None, None)
        # Decimal(str(x)) keeps 6.7 as 6.7, so means and deltas round predictably.
        mean = sum(Decimal(str(getattr(c, name))) for c in previous) / len(previous)
        delta = _one_decimal(Decimal(str(value)) - mean)
        return IndicatorFact(
            current=value,
            baseline_mean=_one_decimal(mean),
            delta=delta,
            direction="up" if delta > 0 else "down" if delta < 0 else "same",
        )
