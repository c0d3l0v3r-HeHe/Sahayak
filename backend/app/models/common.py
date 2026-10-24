from datetime import UTC, datetime
from uuid import uuid4

from pydantic import BaseModel, ConfigDict

Lang = str  # "en" | "hi"


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id() -> str:
    return uuid4().hex


class LocalizedText(BaseModel):
    model_config = ConfigDict(extra="forbid")

    en: str
    hi: str

    def get(self, lang: str) -> str:
        return self.hi if lang == "hi" else self.en
