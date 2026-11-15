from collections.abc import Sequence
from dataclasses import dataclass

from app.domain.entities import GeneratedText


@dataclass(frozen=True, slots=True)
class TextLimits:
    title: int = 80
    summary: int = 400
    next_step: int = 200
    task_title: int = 100


class TextValidator:
    """Checks that written text has every field within limits and exactly the planned tasks."""

    def __init__(self, limits: TextLimits) -> None:
        self._limits = limits

    def is_valid(self, text: object, task_keys: Sequence[str]) -> bool:
        if not isinstance(text, GeneratedText) or not isinstance(text.task_titles, dict):
            return False
        limits = self._limits
        return (
            self._fits(text.title, limits.title)
            and self._fits(text.summary, limits.summary)
            and self._fits(text.next_step, limits.next_step)
            and sorted(text.task_titles) == sorted(task_keys)
            and all(self._fits(text.task_titles[key], limits.task_title) for key in task_keys)
        )

    @staticmethod
    def _fits(value: object, limit: int) -> bool:
        return isinstance(value, str) and 0 < len(value.strip()) <= limit
