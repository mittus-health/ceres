from collections.abc import Mapping
from dataclasses import dataclass

DEFAULT_TIMEOUT_SECONDS = 45.0


@dataclass(frozen=True, slots=True)
class Settings:
    """Configuration read once from the environment. Secrets stay server side."""

    commandcode_api_key: str | None = None
    commandcode_base_url: str | None = None
    commandcode_model: str | None = None
    # The model reasons before answering, so allow more time than a plain completion.
    generator_timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS

    @property
    def llm_configured(self) -> bool:
        return bool(
            self.commandcode_api_key and self.commandcode_base_url and self.commandcode_model
        )

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> "Settings":
        return cls(
            commandcode_api_key=env.get("COMMANDCODE_API_KEY") or None,
            commandcode_base_url=env.get("COMMANDCODE_BASE_URL") or None,
            commandcode_model=env.get("COMMANDCODE_MODEL") or None,
            generator_timeout_seconds=float(
                env.get("CERES_GENERATOR_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS)
            ),
        )
