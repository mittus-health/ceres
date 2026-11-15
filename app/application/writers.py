"""TextWriter implementations that need no I/O: the deterministic writer and the guard."""

import asyncio
import logging

from app.application.ports import TextRequest, TextWriter
from app.application.text_validation import TextValidator
from app.domain.entities import Facts, GeneratedText, IndicatorFact

log = logging.getLogger("ceres")


def _fmt(value: float) -> str:
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _points(value: float) -> str:
    return f"{_fmt(value)} {'point' if value == 1 else 'points'}"


class TemplateTextWriter:
    """Deterministic English text from the computed facts.

    The text states the numbers and gives no medical advice. It is the
    fallback when the language model is missing, slow or wrong.
    """

    async def write(self, request: TextRequest) -> GeneratedText:
        facts = request.facts
        task_titles = {spec.task_key: spec.default_title for spec in request.tasks}
        sleep, fatigue = facts.indicators["sleep_hours"], facts.indicators["fatigue"]

        if facts.comparison == "no_history":
            return GeneratedText(
                title="Your first check-in is saved.",
                summary=(
                    "There are no earlier check-ins to compare with yet. "
                    f"You slept {_fmt(sleep.current)} h and rated your fatigue {int(fatigue.current)} of 7."
                ),
                next_step="Keep logging every day. Comparisons appear from your second check-in.",
                task_titles=task_titles,
            )

        title_parts = [
            {"down": "Less sleep.", "up": "More sleep."}.get(sleep.direction or ""),
            {"up": "More perceived fatigue.", "down": "Less perceived fatigue."}.get(
                fatigue.direction or ""
            ),
        ]
        recheck = any(
            spec.task_key == "check_in_follow_up" and spec.action_code == "recheck"
            for spec in request.tasks
        )
        return GeneratedText(
            title=" ".join(part for part in title_parts if part) or "A steady check-in.",
            summary=" ".join(self._sentences(facts)),
            next_step=(
                "At your next check-in, record your sleep hours and fatigue again to see if the change persists."
                if recheck
                else "Keep logging your check-ins every day so changes are easier to spot."
            ),
            task_titles=task_titles,
        )

    def _sentences(self, facts: Facts) -> list[str]:
        indicators = facts.indicators
        sentences = [
            self._sleep(indicators["sleep_hours"]),
            self._fatigue(indicators["fatigue"]),
        ]
        for extra in (
            self._scale("Your stress level", indicators["stress_level"], "above", "below"),
            self._scale(
                "Your mood rating", indicators["mood_level"], "more negative than", "more positive than"
            ),
            self._scale("Team conflict", indicators["team_conflict_level"], "above", "below"),
        ):
            if extra:
                sentences.append(extra)
        return sentences

    @staticmethod
    def _sleep(sleep: IndicatorFact) -> str:
        delta = abs(sleep.delta or 0)
        if sleep.direction == "down":
            return f"You slept {_fmt(sleep.current)} h, down {_fmt(delta)} h from your recent average."
        if sleep.direction == "up":
            return f"You slept {_fmt(sleep.current)} h, up {_fmt(delta)} h from your recent average."
        return f"You slept {_fmt(sleep.current)} h, in line with your recent average."

    @staticmethod
    def _fatigue(fatigue: IndicatorFact) -> str:
        delta = abs(fatigue.delta or 0)
        if fatigue.direction == "up":
            return f"Your perceived fatigue was {_points(delta)} above average."
        if fatigue.direction == "down":
            return f"Your perceived fatigue was {_points(delta)} below average."
        return "Your perceived fatigue matched your average."

    @staticmethod
    def _scale(subject: str, fact: IndicatorFact, up: str, down: str) -> str | None:
        """A secondary scale is mentioned only when it moved by at least one point."""
        if fact.delta is None or abs(fact.delta) < 1:
            return None
        return f"{subject} was {_points(abs(fact.delta))} {up if fact.delta > 0 else down} average."


class GuardedTextWriter:
    """Uses `primary` when it answers in time with valid text; otherwise `fallback`.

    A decorator over two TextWriters, so it can stand wherever one is expected.
    """

    def __init__(
        self,
        primary: TextWriter,
        fallback: TextWriter,
        validator: TextValidator,
        timeout_seconds: float,
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._validator = validator
        self._timeout = timeout_seconds

    async def write(self, request: TextRequest) -> GeneratedText:
        try:
            text = await asyncio.wait_for(self._primary.write(request), self._timeout)
        except Exception:  # noqa: BLE001 - any failure of the primary means "use the fallback"
            log.warning("Primary text writer failed; using fallback text.", exc_info=True)
            return await self._fallback.write(request)
        if self._validator.is_valid(text, [spec.task_key for spec in request.tasks]):
            return text
        log.warning("Primary text writer returned invalid text; using fallback text.")
        return await self._fallback.write(request)
