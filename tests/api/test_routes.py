import pytest
from fastapi.testclient import TestClient

from app.application.writers import TemplateTextWriter
from app.container import build_use_case
from app.infrastructure.settings import Settings
from app.main import create_app
from tests.factories import EARLIER, HISTORY, READY_JSON, TODAY, as_json


def make_client(writer=None) -> TestClient:
    return TestClient(create_app(Settings(), use_case=build_use_case(writer or TemplateTextWriter())))


client = make_client()
HISTORY_JSON = [as_json(c) for c in HISTORY]


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_post_returns_the_card_and_the_tasks():
    response = client.post("/v1/recommendations", json={"check_ins": HISTORY_JSON, "forecast": READY_JSON})
    assert response.status_code == 200
    body = response.json()
    assert body["insight"]["source"] == "fallback" and body["insight"]["generator"] is None
    assert body["insight"]["facts"]["check_in_id"] == "id-7"
    assert body["insight"]["facts"]["check_in_date"] == "2026-11-07"
    assert body["insight"]["facts"]["indicators"]["fatigue"]["current"] == 5  # a whole number, not 5.0
    assert [t["task_key"] for t in body["tasks"]] == ["check_in_follow_up", "forecast_follow_up"]
    assert body["tasks"][0]["forecast_snapshot"] is None
    assert body["tasks"][1]["forecast_snapshot"]["model_version"] == "eres-v2"


def test_response_has_exactly_the_documented_fields():
    body = client.post("/v1/recommendations", json={"check_ins": HISTORY_JSON, "forecast": READY_JSON}).json()
    assert set(body) == {"insight", "tasks"}
    assert set(body["insight"]) == {"title", "summary", "next_step", "facts", "source", "generator"}
    assert set(body["tasks"][0]) == {
        "task_key", "title", "source", "kind", "action_code", "reason_code",
        "ruleset_version", "status", "forecast_snapshot",
    }


def test_forecast_is_optional():
    response = client.post("/v1/recommendations", json={"check_ins": HISTORY_JSON})
    assert [t["task_key"] for t in response.json()["tasks"]] == ["check_in_follow_up"]


@pytest.mark.parametrize("forecast", [{"status": "insufficient_history"}, {"status": "unavailable"}])
def test_forecast_without_a_result_gives_no_forecast_task(forecast):
    response = client.post("/v1/recommendations", json={"check_ins": HISTORY_JSON, "forecast": forecast})
    assert [t["task_key"] for t in response.json()["tasks"]] == ["check_in_follow_up"]


@pytest.mark.parametrize(
    "payload",
    [
        {"check_ins": []},  # needs at least one
        {"check_ins": [as_json(TODAY), as_json(EARLIER[0])]},  # not oldest first
        {"check_ins": [as_json(TODAY), as_json(TODAY)]},  # duplicate date
        {"check_ins": [as_json(TODAY, description="free text")]},  # description is not accepted
        {"check_ins": [as_json(TODAY, session_id="abc")]},  # session id is not accepted
        {"check_ins": [as_json(TODAY, fatigue=8)]},  # out of range
        {"check_ins": [as_json(TODAY, sleep_hours="7")]},  # no string numbers
        {"check_ins": [as_json(TODAY)], "forecast": {**READY_JSON, "probability_high_fatigue": 1.2}},
        {"check_ins": [as_json(TODAY)], "forecast": {"status": "maybe"}},
    ],
)
def test_invalid_requests_are_rejected(payload):
    assert client.post("/v1/recommendations", json=payload).status_code == 422


def test_app_uses_the_injected_use_case():
    class Failing:
        async def write(self, request):
            raise AssertionError("the injected writer must be the one used")

    with pytest.raises(AssertionError):
        make_client(Failing()).post("/v1/recommendations", json={"check_ins": HISTORY_JSON})
