"""Intent provider interface and the strict schema every provider must produce."""

from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field

from app.models.flow import FlowDefinition


class RawIntent(BaseModel):
    """What a provider returns. LLM output must validate against this exactly."""

    model_config = ConfigDict(extra="forbid")

    flow_id: str | None
    params: dict[str, str | int | float | None] = Field(default_factory=dict)
    confidence: float = Field(ge=0, le=1)


class ProviderError(Exception):
    """Provider unavailable or produced output that does not match the schema."""


class IntentProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def parse(self, text: str, lang: str, flows: list[FlowDefinition]) -> RawIntent: ...
