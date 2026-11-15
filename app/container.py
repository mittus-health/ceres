"""Composition root: the one place that picks concrete classes and wires them together."""

from app.application.build_recommendation import BuildRecommendation
from app.application.ports import ChatModel, TextWriter
from app.application.text_validation import TextLimits, TextValidator
from app.application.writers import GuardedTextWriter, TemplateTextWriter
from app.domain.facts import FactsCalculator
from app.domain.task_policies import (
    CheckInFollowUpPolicy,
    ForecastFollowUpPolicy,
    TaskPlanner,
)
from app.infrastructure.llm.commandcode_chat_model import CommandCodeChatModel
from app.infrastructure.llm.llm_text_writer import LlmTextWriter
from app.infrastructure.settings import Settings


def build_chat_model(settings: Settings) -> ChatModel | None:
    """The language model, or None when it is not configured (fallback text only)."""
    if not settings.llm_configured:
        return None
    return CommandCodeChatModel(
        api_key=settings.commandcode_api_key,  # type: ignore[arg-type]
        base_url=settings.commandcode_base_url,  # type: ignore[arg-type]
        model=settings.commandcode_model,  # type: ignore[arg-type]
    )


def build_text_writer(chat_model: ChatModel | None, settings: Settings) -> TextWriter:
    template = TemplateTextWriter()
    if chat_model is None:
        return template
    limits = TextLimits()
    return GuardedTextWriter(
        primary=LlmTextWriter(chat_model, limits),
        fallback=template,
        validator=TextValidator(limits),
        timeout_seconds=settings.generator_timeout_seconds,
    )


def build_use_case(writer: TextWriter) -> BuildRecommendation:
    return BuildRecommendation(
        facts=FactsCalculator(window=7),
        planner=TaskPlanner([CheckInFollowUpPolicy(), ForecastFollowUpPolicy()]),
        writer=writer,
    )
