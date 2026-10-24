"""Intent parsing pipeline: LLM provider (if configured) -> strict validation -> retry once ->
rules fallback; then parameter normalisation, missing-detail detection and a plain-language
confirmation in both languages."""

import logging
from datetime import date
from typing import Any

from app.core.config import Settings
from app.core.timeutil import local_today
from app.flows.registry import FlowRegistry
from app.flows.templating import render
from app.flows.validator import coerce_param
from app.intent.base import IntentProvider, ProviderError, RawIntent
from app.intent.llm import GeminiProvider, GroqProvider, OllamaProvider
from app.intent.rules import RulesProvider, extract_param
from app.models.common import LocalizedText
from app.models.flow import FlowDefinition

log = logging.getLogger(__name__)

_MONTHS_HI = ["जनवरी", "फ़रवरी", "मार्च", "अप्रैल", "मई", "जून", "जुलाई", "अगस्त", "सितंबर",
              "अक्टूबर", "नवंबर", "दिसंबर"]  # fmt: skip


def build_providers(settings: Settings) -> list[IntentProvider]:
    """Primary provider first; `rules` is always last."""
    forced = settings.intent_provider.strip().lower()
    candidates: list[IntentProvider] = []
    if settings.gemini_api_key and forced in ("", "gemini"):
        candidates.append(GeminiProvider(settings.gemini_api_key, settings.gemini_model))
    if settings.groq_api_key and forced in ("", "groq"):
        candidates.append(GroqProvider(settings.groq_api_key, settings.groq_model))
    if settings.ollama_url and forced in ("", "ollama"):
        candidates.append(OllamaProvider(settings.ollama_url, settings.ollama_model))
    if forced == "rules":
        candidates = []
    return [*candidates[:1], RulesProvider()]


def _display_date(iso: str, lang: str) -> str:
    d = date.fromisoformat(iso)
    delta = (local_today() - d).days
    if lang == "hi":
        return {0: "आज", 1: "कल"}.get(delta, f"{d.day} {_MONTHS_HI[d.month - 1]}")
    return {0: "today", 1: "yesterday"}.get(delta, d.strftime("%-d %b %Y"))


def display_values(flow: FlowDefinition, params: dict[str, str], lang: str) -> dict[str, str]:
    out = dict(params)
    for name, value in params.items():
        p = flow.param(name)
        if p is None:
            continue
        if p.type == "enum":
            opt = next((o for o in p.options or [] if o.value == value), None)
            if opt:
                out[name] = opt.label.get(lang)
        elif p.type == "date":
            out[name] = _display_date(value, lang)
    return out


class IntentService:
    def __init__(
        self,
        settings: Settings,
        registry: FlowRegistry,
        providers: list[IntentProvider] | None = None,
    ):
        self.registry = registry
        self.providers = providers or build_providers(settings)

    async def _raw(
        self, text: str, lang: str, flows: list[FlowDefinition]
    ) -> tuple[RawIntent, str]:
        rules = self.providers[-1]
        for provider in self.providers[:-1]:
            for attempt in (1, 2):  # strict JSON; one retry on invalid output
                try:
                    intent = await provider.parse(text, lang, flows)
                except ProviderError as exc:
                    log.warning("%s attempt %d failed: %s", provider.name, attempt, exc)
                    continue
                if intent.flow_id is None:
                    fallback = await rules.parse(text, lang, flows)
                    if fallback.flow_id:
                        return fallback, rules.name
                return intent, provider.name
        return await rules.parse(text, lang, flows), rules.name

    async def parse(
        self,
        text: str,
        lang: str,
        flow_id: str | None = None,
        known: dict[str, str] | None = None,
        expecting: str | None = None,
    ) -> dict[str, Any]:
        flows = self.registry.all()
        context_flow = self.registry.get(flow_id) if flow_id else None
        provider = "context"

        if context_flow and expecting and context_flow.param(expecting):
            # Follow-up answer to "How old are you?" etc.
            param = context_flow.param(expecting)
            assert param is not None
            value = extract_param(param, text, answer=True)
            raw_params: dict[str, Any] = {expecting: value} if value else {}
            flow, confidence = context_flow, 0.9 if value else 0.3
        else:
            raw, provider = await self._raw(text, lang, flows)
            matched = self.registry.get(raw.flow_id) if raw.flow_id else None
            if matched is None:
                return self._no_match(provider)
            flow, raw_params, confidence = matched, raw.params, raw.confidence

        params: dict[str, str] = {}
        if known and context_flow and context_flow.id == flow.id:
            for k, v in known.items():
                if (c := coerce_param(flow, k, v)) is not None:
                    params[k] = c
        invalid: list[str] = []
        for k, v in raw_params.items():
            c = coerce_param(flow, k, v)
            if c is None:
                invalid.append(k)
            else:
                params[k] = c
        for p in flow.params:
            if p.name not in params and p.default is not None and not p.required:
                params[p.name] = coerce_param(flow, p.name, p.default) or p.default
        missing = [p.name for p in flow.params if p.required and p.name not in params]
        return self._response(flow, params, missing, invalid, confidence, provider)

    def _response(
        self,
        flow: FlowDefinition,
        params: dict[str, str],
        missing: list[str],
        invalid: list[str],
        confidence: float,
        provider: str,
    ) -> dict[str, Any]:
        confirmation = None
        next_prompt = None
        if missing:
            p = flow.param(missing[0])
            assert p is not None
            next_prompt = p.prompt.model_dump()
        else:
            tpl = flow.confirm_template or LocalizedText(
                en=f"Shall I do this: {flow.title.en}?", hi=f"क्या मैं यह करूँ: {flow.title.hi}?"
            )
            confirmation = {
                lang: render(getattr(tpl, lang), display_values(flow, params, lang))
                for lang in ("en", "hi")
            }
        return {
            "flow_id": flow.id,
            "title": flow.title.model_dump(),
            "params": params,
            "display_params": {lang: display_values(flow, params, lang) for lang in ("en", "hi")},
            "missing_params": missing,
            "invalid_params": invalid,
            "next_prompt": next_prompt,
            "confirmation": confirmation,
            "confidence": round(confidence, 2),
            "provider": provider,
            "supported": None,
        }

    def _no_match(self, provider: str) -> dict[str, Any]:
        flows = self.registry.all()
        en = ", ".join(f.title.en for f in flows)
        hi = ", ".join(f.title.hi for f in flows)
        return {
            "flow_id": None,
            "title": None,
            "params": {},
            "display_params": None,
            "missing_params": [],
            "invalid_params": [],
            "next_prompt": None,
            "confirmation": {
                "en": f"Sorry, I can't do that yet. I can help you with: {en}.",
                "hi": f"माफ़ कीजिए, यह काम मैं अभी नहीं कर सकता। मैं इनमें मदद कर सकता हूँ: {hi}।",
            },
            "confidence": 0.0,
            "provider": provider,
            "supported": [{"id": f.id, "title": f.title.model_dump()} for f in flows],
        }
