import json

import httpx
import pytest

from app.application.ports import TextRequest
from app.application.text_validation import TextLimits
from app.domain.facts import FactsCalculator
from app.domain.task_policies import CheckInFollowUpPolicy, ForecastFollowUpPolicy, TaskPlanner
from app.infrastructure.llm.commandcode_chat_model import CommandCodeChatModel
from app.infrastructure.llm.llm_text_writer import LlmTextWriter
from app.infrastructure.llm.prompt import build_system_prompt, build_user_message
from app.infrastructure.settings import Settings
from tests.factories import HISTORY, READY

CONTENT = {
    "title": "Less sleep. More fatigue.",
    "summary": "You slept 6.5 h, down 0.2 h from your recent average.",
    "next_step": "Record your sleep and fatigue again at your next check-in.",
    "task_titles": {"check_in_follow_up": "Record a new check-in"},
}


def request() -> TextRequest:
    facts = FactsCalculator().calculate(HISTORY, None)
    return TextRequest(facts, TaskPlanner([CheckInFollowUpPolicy(), ForecastFollowUpPolicy()]).plan(facts, None))


def chat_model(handler) -> CommandCodeChatModel:
    client = httpx.AsyncClient(base_url="https://provider.test/v1", transport=httpx.MockTransport(handler))
    return CommandCodeChatModel("secret", "https://provider.test/v1", "vendor/model", client=client)


def completion(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"role": "assistant", "content": content}}]})


# ---- CommandCodeChatModel (transport only) ---------------------------------


async def test_chat_model_posts_an_openai_style_request():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen.update(url=str(req.url), body=json.loads(req.content))
        return completion("hello")

    model = chat_model(handler)
    assert await model.complete("sys", "usr") == "hello"
    assert model.id == "commandcode:vendor/model"
    assert seen["url"] == "https://provider.test/v1/chat/completions"
    assert seen["body"]["model"] == "vendor/model"
    assert [m["role"] for m in seen["body"]["messages"]] == ["system", "user"]


@pytest.mark.parametrize("status", [401, 500])
async def test_chat_model_raises_on_http_errors(status):
    with pytest.raises(httpx.HTTPStatusError):
        await chat_model(lambda r: httpx.Response(status, json={"error": "x"})).complete("s", "u")


# ---- LlmTextWriter (prompt + parsing, over any ChatModel) -------------------


class FakeChat:
    id = "fake:model"

    def __init__(self, answer):
        self.answer, self.seen = answer, None

    async def complete(self, system, user):
        self.seen = (system, user)
        return self.answer


async def test_writer_parses_the_json_answer_and_records_the_author():
    text = await LlmTextWriter(FakeChat(json.dumps(CONTENT)), TextLimits()).write(request())
    assert (text.title, text.author) == ("Less sleep. More fatigue.", "fake:model")
    assert text.task_titles == {"check_in_follow_up": "Record a new check-in"}


async def test_writer_accepts_json_wrapped_in_a_code_fence():
    text = await LlmTextWriter(FakeChat("```json\n" + json.dumps(CONTENT) + "\n```"), TextLimits()).write(request())
    assert text.title == "Less sleep. More fatigue."


@pytest.mark.parametrize("answer", ["not json at all", json.dumps({"title": "only a title"})])
async def test_writer_raises_on_unusable_answers(answer):
    with pytest.raises((ValueError, KeyError)):
        await LlmTextWriter(FakeChat(answer), TextLimits()).write(request())


def test_user_message_has_the_facts_and_no_free_text():
    message = json.loads(build_user_message(request()))
    assert message["facts"]["indicators"]["sleep_hours"]["delta"] == -0.2
    assert message["facts"]["check_in_date"] == "2026-11-07"
    assert [t["task_key"] for t in message["tasks"]] == ["check_in_follow_up"]
    assert "description" not in json.dumps(message) and "session" not in json.dumps(message)


def test_system_prompt_uses_the_configured_limits():
    prompt = build_system_prompt(TextLimits(title=10, summary=20, next_step=30, task_title=40))
    for limit in ("at most 10", "at most 20", "at most 30", "at most 40"):
        assert limit in prompt
    assert "Do not give medical advice" in prompt


# ---- Settings --------------------------------------------------------------


def test_llm_is_configured_only_when_all_three_settings_exist():
    assert not Settings.from_env({}).llm_configured
    assert not Settings.from_env({"COMMANDCODE_API_KEY": "k", "COMMANDCODE_BASE_URL": "u"}).llm_configured
    full = Settings.from_env(
        {"COMMANDCODE_API_KEY": "k", "COMMANDCODE_BASE_URL": "https://p/v1", "COMMANDCODE_MODEL": "m"}
    )
    assert full.llm_configured and full.generator_timeout_seconds == 45.0


def test_timeout_is_configurable():
    assert Settings.from_env({"CERES_GENERATOR_TIMEOUT_SECONDS": "12.5"}).generator_timeout_seconds == 12.5
