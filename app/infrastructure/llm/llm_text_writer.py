import json
import re

from app.application.ports import ChatModel, TextRequest
from app.application.text_validation import TextLimits
from app.domain.entities import GeneratedText
from app.infrastructure.llm.prompt import build_system_prompt, build_user_message


class LlmTextWriter:
    """TextWriter backed by any ChatModel: builds the prompt and reads the JSON answer."""

    def __init__(self, chat_model: ChatModel, limits: TextLimits) -> None:
        self._chat_model = chat_model
        self._system_prompt = build_system_prompt(limits)

    async def write(self, request: TextRequest) -> GeneratedText:
        content = await self._chat_model.complete(
            self._system_prompt, build_user_message(request)
        )
        return self.parse(content, author=self._chat_model.id)

    @staticmethod
    def parse(content: str, author: str) -> GeneratedText:
        """Reads the model's JSON object, tolerating a code fence around it."""
        body = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
        data = json.loads(body)
        return GeneratedText(
            title=data["title"],
            summary=data["summary"],
            next_step=data["next_step"],
            task_titles=data["task_titles"],
            author=author,
        )
