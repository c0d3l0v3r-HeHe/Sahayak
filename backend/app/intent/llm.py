"""LLM-backed intent providers. Each must return strict JSON matching `RawIntent`."""

import json
import re
from typing import Any

import httpx
from pydantic import ValidationError

from app.intent.base import IntentProvider, ProviderError, RawIntent
from app.models.flow import FlowDefinition

TIMEOUT_S = 10.0

SYSTEM_PROMPT = """You turn a spoken request from an Indian user (Hindi, English or Hinglish) \
into a task for a voice assistant that fills in government websites.

Supported tasks (flow_id, purpose, parameters):
{catalog}

Reply with ONE JSON object and nothing else:
{{"flow_id": "<one of the ids above, or null if none fits>",
  "params": {{"<param name>": "<value>"}},
  "confidence": <number 0..1>}}

Rules:
- Only include params the user actually said. Never invent values.
- Enum params must use one of the listed option values exactly.
- Numbers as plain digits (convert Hindi number words and "lakh"/"hazaar": 1.5 lakh -> 150000).
- Dates: "today", "yesterday", or YYYY-MM-DD.
- If the request is not one of the supported tasks, use flow_id null and confidence 0."""


def catalog(flows: list[FlowDefinition]) -> str:
    lines = []
    for f in flows:
        params = []
        for p in f.params:
            desc = f"{p.name} ({p.type}"
            if p.options:
                values = [o.value for o in p.options]
                desc += ": " + "|".join(values[:40])
            elif p.regex:
                desc += f", pattern {p.regex}"
            desc += ")" if p.required else ", optional)"
            params.append(desc)
        examples = "; ".join(f.examples[:3])
        lines.append(
            f"- {f.id}: {f.description.en} Params: {', '.join(params) or 'none'}. "
            f"Examples: {examples}"
        )
    return "\n".join(lines)


def parse_strict(content: str, flows: list[FlowDefinition]) -> RawIntent:
    """Validate model output. Tolerates a ```json fence, nothing else."""
    text = content.strip()
    fence = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.S)
    if fence:
        text = fence.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderError(f"not JSON: {exc}") from exc
    try:
        intent = RawIntent.model_validate(data)
    except ValidationError as exc:
        raise ProviderError(f"schema mismatch: {exc.error_count()} errors") from exc
    ids = {f.id for f in flows}
    if intent.flow_id is not None and intent.flow_id not in ids:
        raise ProviderError(f"unknown flow_id {intent.flow_id!r}")
    if intent.flow_id:
        flow = next(f for f in flows if f.id == intent.flow_id)
        allowed = {p.name for p in flow.params}
        intent.params = {k: v for k, v in intent.params.items() if k in allowed and v is not None}
    return intent


class _LLMProvider(IntentProvider):
    def __init__(self, model: str, client: httpx.AsyncClient | None = None):
        self.model = model
        self._client = client

    def _http(self) -> httpx.AsyncClient:
        return self._client or httpx.AsyncClient(timeout=TIMEOUT_S)

    async def _complete(self, system: str, user: str) -> str:
        raise NotImplementedError

    async def parse(self, text: str, lang: str, flows: list[FlowDefinition]) -> RawIntent:
        system = SYSTEM_PROMPT.format(catalog=catalog(flows))
        user = f"User language: {lang}\nUser said: {text}"
        try:
            content = await self._complete(system, user)
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError(f"{self.name} request failed: {type(exc).__name__}") from exc
        return parse_strict(content, flows)

    async def _post(self, url: str, **kwargs: Any) -> dict[str, Any]:
        client = self._http()
        try:
            resp = await client.post(url, **kwargs)
            resp.raise_for_status()
            return resp.json()
        finally:
            if self._client is None:
                await client.aclose()


class GeminiProvider(_LLMProvider):
    """Google Gemini API (free tier). https://ai.google.dev"""

    name = "gemini"
    BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str, model: str, client: httpx.AsyncClient | None = None):
        super().__init__(model, client)
        self.api_key = api_key

    async def _complete(self, system: str, user: str) -> str:
        body = await self._post(
            f"{self.BASE}/{self.model}:generateContent",
            headers={"x-goog-api-key": self.api_key},
            json={
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
            },
        )
        return body["candidates"][0]["content"]["parts"][0]["text"]


class GroqProvider(_LLMProvider):
    """Groq (free tier), OpenAI-compatible chat completions."""

    name = "groq"
    URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self, api_key: str, model: str, client: httpx.AsyncClient | None = None):
        super().__init__(model, client)
        self.api_key = api_key

    async def _complete(self, system: str, user: str) -> str:
        body = await self._post(
            self.URL,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": self.model,
                "temperature": 0,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        return body["choices"][0]["message"]["content"]


class OllamaProvider(_LLMProvider):
    """Local model through Ollama — fully offline, free."""

    name = "ollama"

    def __init__(self, url: str, model: str, client: httpx.AsyncClient | None = None):
        super().__init__(model, client)
        self.url = url.rstrip("/")

    async def _complete(self, system: str, user: str) -> str:
        body = await self._post(
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
        )
        return body["message"]["content"]
