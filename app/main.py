import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.application.build_recommendation import BuildRecommendation
from app.container import build_chat_model, build_text_writer, build_use_case
from app.infrastructure.settings import Settings


def create_app(
    settings: Settings | None = None,
    use_case: BuildRecommendation | None = None,
) -> FastAPI:
    """App factory. Tests pass their own `use_case`; production builds it from the environment."""
    settings = settings or Settings.from_env(os.environ)
    chat_model = None if use_case else build_chat_model(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        if chat_model is not None and hasattr(chat_model, "aclose"):
            await chat_model.aclose()

    app = FastAPI(
        title="Ceres",
        description="Daily AI recommendation for Mittus. Stateless: the backend sends data and saves the result.",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.build_recommendation = use_case or build_use_case(
        build_text_writer(chat_model, settings)
    )
    app.include_router(router)
    return app


app = create_app()
