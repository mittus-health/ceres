"""Ports: what the application needs from the outside. Infrastructure implements them."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from app.domain.entities import Facts, GeneratedText, TaskSpec


@dataclass(frozen=True, slots=True)
class TextRequest:
    """What a text writer receives. Never has the free-text description or a session id."""

    facts: Facts
    # The writer words these titles; it does not add or remove tasks.
    tasks: Sequence[TaskSpec]


class TextWriter(Protocol):
    """Writes the card text and the task titles."""

    async def write(self, request: TextRequest) -> GeneratedText: ...


class ChatModel(Protocol):
    """A chat-completion language model, reduced to what the app uses."""

    # Provider and model, e.g. "provider:model".
    id: str

    async def complete(self, system: str, user: str) -> str: ...
