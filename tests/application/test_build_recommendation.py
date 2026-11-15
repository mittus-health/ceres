from app.application.build_recommendation import BuildRecommendation
from app.application.writers import TemplateTextWriter
from app.domain.entities import GeneratedText
from app.domain.facts import FactsCalculator
from app.domain.task_policies import CheckInFollowUpPolicy, ForecastFollowUpPolicy, TaskPlanner
from tests.factories import HISTORY, READY, TODAY


class RecordingWriter:
    def __init__(self, author=None):
        self.author, self.seen = author, None

    async def write(self, request):
        self.seen = request
        return GeneratedText(
            title=" A title ",
            summary="A summary.",
            next_step="A next step.",
            task_titles={spec.task_key: f"Do {spec.task_key}" for spec in request.tasks},
            author=self.author,
        )


def use_case(writer) -> BuildRecommendation:
    return BuildRecommendation(
        FactsCalculator(), TaskPlanner([CheckInFollowUpPolicy(), ForecastFollowUpPolicy()]), writer
    )


async def test_the_writer_receives_the_facts_and_the_planned_tasks_only():
    writer = RecordingWriter()
    await use_case(writer).execute(HISTORY, READY)
    assert writer.seen.facts.check_in_id == "id-7"
    assert [t.task_key for t in writer.seen.tasks] == ["check_in_follow_up", "forecast_follow_up"]


async def test_tasks_come_from_the_rules_and_titles_from_the_writer():
    result = await use_case(RecordingWriter()).execute(HISTORY, READY)
    assert [(t.task_key, t.action_code, t.title) for t in result.tasks] == [
        ("check_in_follow_up", "recheck", "Do check_in_follow_up"),
        ("forecast_follow_up", "monitor", "Do forecast_follow_up"),
    ]
    assert result.tasks[1].forecast_snapshot.model_version == "eres-v2"


async def test_source_is_ai_when_the_writer_has_an_author():
    result = await use_case(RecordingWriter(author="test:model")).execute(HISTORY, READY)
    assert (result.insight.source, result.insight.generator) == ("ai", "test:model")
    assert result.insight.title == "A title"  # trimmed


async def test_source_is_fallback_without_an_author():
    result = await use_case(RecordingWriter(author=None)).execute(HISTORY, READY)
    assert (result.insight.source, result.insight.generator) == ("fallback", None)


async def test_end_to_end_with_the_template_writer():
    result = await use_case(TemplateTextWriter()).execute([TODAY])
    assert result.insight.facts.comparison == "no_history"
    assert [t.task_key for t in result.tasks] == ["check_in_follow_up"]
