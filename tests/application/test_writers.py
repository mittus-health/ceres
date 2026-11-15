import asyncio

import pytest

from app.application.ports import TextRequest
from app.application.text_validation import TextLimits, TextValidator
from app.application.writers import GuardedTextWriter, TemplateTextWriter
from app.domain.entities import GeneratedText, InsufficientHistory
from app.domain.facts import FactsCalculator
from app.domain.task_policies import CheckInFollowUpPolicy, ForecastFollowUpPolicy, TaskPlanner
from tests.factories import EARLIER, HISTORY, READY, TODAY, check_in

planner = TaskPlanner([CheckInFollowUpPolicy(), ForecastFollowUpPolicy()])


def request(history=HISTORY, forecast=None) -> TextRequest:
    facts = FactsCalculator().calculate(history, forecast)
    return TextRequest(facts, planner.plan(facts, forecast))


# ---- TemplateTextWriter ----------------------------------------------------


async def test_template_states_the_computed_numbers():
    text = await TemplateTextWriter().write(request())
    assert text.author is None
    assert text.title == "Less sleep. More perceived fatigue."
    assert text.summary == (
        "You slept 6.5 h, down 0.2 h from your recent average. "
        "Your perceived fatigue was 1.5 points above average."
    )
    assert "record your sleep hours and fatigue again" in text.next_step
    assert text.task_titles == {"check_in_follow_up": "Record your sleep and fatigue again at your next check-in"}


async def test_template_titles_every_planned_task():
    text = await TemplateTextWriter().write(request(forecast=READY))
    assert set(text.task_titles) == {"check_in_follow_up", "forecast_follow_up"}


async def test_template_first_check_in():
    text = await TemplateTextWriter().write(request([TODAY], InsufficientHistory()))
    assert text.title == "Your first check-in is saved."
    assert "no earlier check-ins" in text.summary


async def test_template_steady_check_in_monitors():
    text = await TemplateTextWriter().write(request([*EARLIER, check_in(7, 6.7, 4)]))
    assert text.next_step.startswith("Keep logging")


async def test_secondary_scale_only_when_it_moved_a_point_or_more():
    stressed = await TemplateTextWriter().write(request([*EARLIER, check_in(7, 6.5, 5, stress_level=4)]))
    assert "Your stress level was 2 points above average." in stressed.summary
    assert "stress" not in (await TemplateTextWriter().write(request())).summary


# ---- GuardedTextWriter -----------------------------------------------------


class FakeWriter:
    def __init__(self, result=None, error=None, delay=0.0):
        self.result, self.error, self.delay, self.calls = result, error, delay, 0

    async def write(self, req):
        self.calls += 1
        await asyncio.sleep(self.delay)
        if self.error:
            raise self.error
        return self.result


def ai_text(**overrides) -> GeneratedText:
    base = dict(
        title="Sleep dipped, fatigue rose.",
        summary="You slept 6.5 h and felt more tired than usual.",
        next_step="Log sleep and fatigue again at your next check-in.",
        task_titles={"check_in_follow_up": "Log sleep and fatigue again", "forecast_follow_up": "Revisit the estimate"},
        author="test:model",
    )
    return GeneratedText(**{**base, **overrides})


def guarded(primary, timeout=1.0) -> GuardedTextWriter:
    return GuardedTextWriter(primary, TemplateTextWriter(), TextValidator(TextLimits()), timeout)


async def test_guard_passes_valid_primary_text_through():
    text = await guarded(FakeWriter(ai_text())).write(request(forecast=READY))
    assert text.author == "test:model" and text.title == "Sleep dipped, fatigue rose."


BAD = {
    "an empty title": FakeWriter(ai_text(title=" ")),
    "an overlong summary": FakeWriter(ai_text(summary="x" * 401)),
    "a missing task title": FakeWriter(ai_text(task_titles={"check_in_follow_up": "x"})),
    "a task it was not asked for": FakeWriter(
        ai_text(task_titles={"check_in_follow_up": "x", "forecast_follow_up": "y", "contact_medical": "Call"})
    ),
    "an error": FakeWriter(error=RuntimeError("provider down")),
}


@pytest.mark.parametrize("primary", BAD.values(), ids=BAD.keys())
async def test_guard_falls_back_on_bad_primary(primary):
    text = await guarded(primary).write(request(forecast=READY))
    assert text.author is None
    assert text.title == "Less sleep. More perceived fatigue."
    assert set(text.task_titles) == {"check_in_follow_up", "forecast_follow_up"}


async def test_guard_falls_back_when_the_primary_is_too_slow():
    text = await guarded(FakeWriter(ai_text(), delay=1), timeout=0.02).write(request(forecast=READY))
    assert text.author is None
