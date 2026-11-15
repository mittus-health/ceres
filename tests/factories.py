from datetime import date

from app.domain.entities import CheckIn, ReadyForecast


def check_in(day: int, sleep: float, fatigue: int, **extra) -> CheckIn:
    values = dict(
        id=f"id-{day}",
        check_in_date=date(2026, 11, day),
        sleep_hours=sleep,
        stress_level=2,
        mood_level=2,
        team_conflict_level=1,
        fatigue=fatigue,
    )
    return CheckIn(**{**values, **extra})


def as_json(c: CheckIn, **extra) -> dict:
    return {
        "id": c.id,
        "check_in_date": c.check_in_date.isoformat(),
        "sleep_hours": c.sleep_hours,
        "stress_level": c.stress_level,
        "mood_level": c.mood_level,
        "team_conflict_level": c.team_conflict_level,
        "fatigue": c.fatigue,
        **extra,
    }


# Six earlier days at 6.7 h with fatigue averaging 3.5, then today at 6.5 h and fatigue 5.
EARLIER = [check_in(i + 1, 6.7, f) for i, f in enumerate([3, 4, 3, 4, 3, 4])]
TODAY = check_in(7, 6.5, 5)
HISTORY = [*EARLIER, TODAY]

READY = ReadyForecast(
    probability_high_fatigue=0.38, model_version="eres-v2", predicted_at="2026-11-14T12:00:00.000Z"
)
READY_JSON = {
    "status": "ready",
    "probability_high_fatigue": 0.38,
    "model_version": "eres-v2",
    "predicted_at": "2026-11-14T12:00:00.000Z",
}
