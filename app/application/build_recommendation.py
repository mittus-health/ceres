from collections.abc import Sequence

from app.application.ports import TextRequest, TextWriter
from app.domain.entities import CheckIn, Forecast, Insight, Recommendation
from app.domain.facts import FactsCalculator
from app.domain.task_policies import TaskPlanner


class BuildRecommendation:
    """Use case: today's card and tasks from the session's check-ins and the Eres result.

    Facts and tasks come from code. The text writer only words them. Every
    collaborator is injected, so the use case knows nothing about HTTP or about
    any language model.
    """

    def __init__(
        self, facts: FactsCalculator, planner: TaskPlanner, writer: TextWriter
    ) -> None:
        self._facts = facts
        self._planner = planner
        self._writer = writer

    async def execute(
        self, check_ins: Sequence[CheckIn], forecast: Forecast | None = None
    ) -> Recommendation:
        facts = self._facts.calculate(check_ins, forecast)
        specs = self._planner.plan(facts, forecast)
        text = await self._writer.write(TextRequest(facts=facts, tasks=specs))
        return Recommendation(
            insight=Insight(
                title=text.title.strip(),
                summary=text.summary.strip(),
                next_step=text.next_step.strip(),
                facts=facts,
                source="ai" if text.author else "fallback",
                generator=text.author,
            ),
            tasks=[spec.titled(text.task_titles[spec.task_key].strip()) for spec in specs],
        )
