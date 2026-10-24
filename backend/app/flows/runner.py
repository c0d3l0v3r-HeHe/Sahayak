"""Executes a validated flow step by step against a BrowserSession.

The runner knows nothing about Mongo or the API: it reports progress through a RunContext,
which the worker implements (events, screenshots, hand-offs, cancellation).
"""

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.timeutil import local_today
from app.engine.base import BrowserEngine, BrowserSession, ElementNotFound, TransientError
from app.flows.templating import render
from app.handoff.service import HandoffCancelled, HandoffTimeout
from app.models.common import LocalizedText
from app.models.flow import (
    AskUserStep,
    AssertStep,
    ClickStep,
    ExtractStep,
    FailStep,
    FillStep,
    FlowDefinition,
    GotoStep,
    IfExistsStep,
    Locator,
    NarrateStep,
    PauseStep,
    PressStep,
    ScreenshotStep,
    SelectStep,
    Step,
    WaitForStep,
)

log = logging.getLogger(__name__)

MSG_SITE_DOWN = LocalizedText(
    en="The website is not responding right now. Please try again in a few minutes.",
    hi="वेबसाइट अभी जवाब नहीं दे रही है। कृपया कुछ मिनट बाद फिर कोशिश करें।",
)
MSG_SITE_CHANGED = LocalizedText(
    en="The website looks different than expected, so I could not finish this task.",
    hi="वेबसाइट उम्मीद से अलग दिख रही है, इसलिए मैं यह काम पूरा नहीं कर पाया।",
)
MSG_TIMEOUT = LocalizedText(
    en="I waited, but did not get an answer in time. Please start again.",
    hi="मैंने इंतज़ार किया, पर समय पर जवाब नहीं मिला। कृपया फिर से शुरू करें।",
)
MSG_CANCELLED = LocalizedText(en="Task cancelled.", hi="काम रद्द कर दिया गया।")


class FlowFailed(Exception):
    def __init__(self, message: LocalizedText, detail: str = ""):
        self.message = message
        self.detail = detail
        super().__init__(detail or message.en)


class TaskCancelled(Exception):
    pass


class HandoffExpired(Exception):
    pass


@dataclass
class RunResult:
    text: LocalizedText
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text.model_dump(), "data": self.data}


class RunContext(ABC):
    @abstractmethod
    async def step(self, message: LocalizedText) -> None: ...

    @abstractmethod
    async def screenshot(self, image: bytes) -> str: ...

    @abstractmethod
    async def ask(
        self, kind: str, prompt: LocalizedText, image_id: str | None, param: str | None,
        timeout_s: float,
    ) -> str:  # fmt: skip
        """Hand control to the user; returns the answer (never persisted)."""

    @abstractmethod
    async def cancelled(self) -> bool: ...


@dataclass
class RunnerConfig:
    demo_mode: bool = True
    mock_sites_url: str = "http://localhost:8000/mock"
    delay_min_ms: int = 250
    delay_max_ms: int = 700
    step_retries: int = 2
    retry_backoff_s: float = 1.0
    handoff_timeout_s: float = 300
    lang: str = "en"


def render_locator(loc: Locator, scope: dict[str, Any]) -> Locator:
    updates = {
        k: render(v, scope)
        for k in ("name", "label", "placeholder", "text", "css", "test_id")
        if isinstance(v := getattr(loc, k), str) and "{{" in v
    }
    return loc.model_copy(update=updates) if updates else loc


class FlowRunner:
    def __init__(self, engine: BrowserEngine, config: RunnerConfig):
        self.engine = engine
        self.cfg = config

    def base_url(self, flow: FlowDefinition) -> str:
        if self.cfg.demo_mode:
            return self.cfg.mock_sites_url.rstrip("/") + flow.mock_path.rstrip("/")
        return flow.site.rstrip("/")

    async def run(self, flow: FlowDefinition, params: dict[str, str], ctx: RunContext) -> RunResult:
        variables: dict[str, Any] = {
            **params,
            "base": self.base_url(flow),
            "today": local_today().isoformat(),
            "lang": self.cfg.lang,
        }
        # enum params also expose their English label, e.g. {{gender_label}} -> "Female"
        for p in flow.params:
            if p.type == "enum" and p.name in params:
                opt = next((o for o in p.options or [] if o.value == params[p.name]), None)
                if opt:
                    variables[f"{p.name}_label"] = opt.label.en
                    variables[f"{p.name}_label_hi"] = opt.label.hi
        extracted: dict[str, Any] = {}

        run_goal = getattr(self.engine, "run_goal", None)
        if run_goal and flow.goal and not flow.requires:
            await ctx.step(
                LocalizedText(en="Working on the website…", hi="वेबसाइट पर काम चल रहा है…")
            )
            try:
                data = await run_goal(variables["base"], render(flow.goal, variables))
            except TransientError as exc:
                raise FlowFailed(MSG_SITE_DOWN, str(exc)) from exc
            extracted.update(data)
        else:
            viewport = flow.viewport.model_dump() if flow.viewport else None
            session = await self.engine.new_session(viewport)
            try:
                await self._steps(flow.steps, session, variables, extracted, ctx)
            finally:
                await session.close()

        scope = {**variables, **extracted}
        text = LocalizedText(
            en=render(flow.result_template.en, scope), hi=render(flow.result_template.hi, scope)
        )
        return RunResult(text=text, data=extracted)

    # ---- internals -----------------------------------------------------------

    async def _pause(self) -> None:
        lo, hi = self.cfg.delay_min_ms, max(self.cfg.delay_min_ms, self.cfg.delay_max_ms)
        if hi > 0:
            await asyncio.sleep(random.uniform(lo, hi) / 1000)

    async def _retry(self, what: str, fn: Any) -> Any:
        attempt = 0
        while True:
            try:
                return await fn()
            except TransientError as exc:
                if attempt >= self.cfg.step_retries:
                    raise FlowFailed(MSG_SITE_DOWN, f"{what}: {exc}") from exc
                attempt += 1
                log.info("retrying %s after transient error (attempt %d)", what, attempt)
                await asyncio.sleep(self.cfg.retry_backoff_s * 2 ** (attempt - 1))
            except ElementNotFound as exc:
                raise FlowFailed(MSG_SITE_CHANGED, f"{what}: {exc}") from exc

    async def _snap(self, session: BrowserSession, ctx: RunContext) -> None:
        try:
            await ctx.screenshot(await session.screenshot())
        except Exception as exc:  # a missing screenshot must never fail a task
            log.debug("screenshot failed: %s", exc)

    async def _steps(
        self,
        steps: list[Step],
        session: BrowserSession,
        variables: dict[str, Any],
        extracted: dict[str, Any],
        ctx: RunContext,
    ) -> None:
        for step in steps:
            if await ctx.cancelled():
                raise TaskCancelled()
            scope = {**variables, **extracted}
            narrate = getattr(step, "narrate", None)
            if narrate is not None:
                await ctx.step(narrate)
            await self._one(step, session, variables, extracted, scope, ctx)

    async def _one(
        self,
        step: Step,
        session: BrowserSession,
        variables: dict[str, Any],
        extracted: dict[str, Any],
        scope: dict[str, Any],
        ctx: RunContext,
    ) -> None:
        updates = {
            k: render_locator(v, scope)
            for k in ("locator", "screenshot_locator", "fill_locator")
            if isinstance(v := getattr(step, k, None), Locator)
        }
        if updates:
            step = step.model_copy(update=updates)  # type: ignore[assignment]
        match step:
            case NarrateStep():
                await ctx.step(LocalizedText(en=render(step.en, scope), hi=render(step.hi, scope)))
            case GotoStep():
                url = render(step.url, scope)
                if url.startswith("/"):
                    url = variables["base"] + url
                await self._pause()
                await self._retry("goto", lambda: session.goto(url, step.timeout_ms))
                await self._snap(session, ctx)
            case FillStep():
                value = render(step.value, scope)
                await self._pause()
                await self._retry(
                    "fill",
                    lambda: session.fill(
                        step.locator, value, step.timeout_ms, step.typing_delay_ms
                    ),
                )
            case PressStep():
                await self._pause()
                await self._retry(
                    "press", lambda: session.press(step.locator, step.key, step.timeout_ms)
                )
            case PauseStep():
                await asyncio.sleep(step.ms / 1000)
            case SelectStep():
                value = render(step.value, scope)
                await self._pause()
                await self._retry(
                    "select", lambda: session.select(step.locator, value, step.timeout_ms)
                )
            case ClickStep():
                await self._pause()
                await self._retry(
                    "click", lambda: session.click(step.locator, step.timeout_ms, step.force)
                )
                await self._snap(session, ctx)
            case WaitForStep():
                await self._retry(
                    "wait_for", lambda: session.wait_for(step.locator, step.state, step.timeout_ms)
                )
            case ExtractStep():
                extracted[step.into] = await self._retry(
                    "extract", lambda: self._extract(session, step)
                )
            case ScreenshotStep():
                try:
                    await ctx.screenshot(await session.screenshot(step.locator))
                except Exception as exc:
                    log.debug("screenshot step failed: %s", exc)
            case IfExistsStep():
                found = await session.exists(step.locator, step.timeout_ms)
                branch = step.then if found else step.else_
                await self._steps(branch, session, variables, extracted, ctx)
            case AssertStep():
                ok = await session.exists(step.locator, step.timeout_ms)
                if ok and step.text_contains:
                    ok = (
                        step.text_contains.lower()
                        in (await session.text(step.locator, step.timeout_ms)).lower()
                    )
                if not ok:
                    raise FlowFailed(step.message or MSG_SITE_CHANGED, "assert failed")
            case FailStep():
                raise FlowFailed(
                    LocalizedText(
                        en=render(step.message.en, scope), hi=render(step.message.hi, scope)
                    ),
                    "flow fail step",
                )
            case AskUserStep():
                await self._ask(step, session, variables, ctx)

    async def _extract(self, session: BrowserSession, step: ExtractStep) -> Any:
        match step.as_:
            case "text":
                return await session.text(step.locator, step.timeout_ms)
            case "attribute":
                return await session.attribute(step.locator, step.attribute or "", step.timeout_ms)
            case "table":
                rows = await session.table(step.locator, step.timeout_ms)
                if step.columns:
                    rows = [dict(zip(step.columns, r.values(), strict=False)) for r in rows]
                return rows[: step.limit] if step.limit else rows
            case "list":
                return await session.items(
                    step.locator, step.fields or {}, step.limit, step.timeout_ms
                )

    async def _ask(
        self,
        step: AskUserStep,
        session: BrowserSession,
        variables: dict[str, Any],
        ctx: RunContext,
    ) -> None:
        image_id = None
        if step.screenshot_locator is not None:
            try:
                image_id = await ctx.screenshot(await session.screenshot(step.screenshot_locator))
            except Exception as exc:
                raise FlowFailed(MSG_SITE_CHANGED, f"hand-off screenshot: {exc}") from exc
        timeout = step.wait_minutes * 60 if step.wait_minutes else self.cfg.handoff_timeout_s
        try:
            answer = await ctx.ask(step.kind, step.prompt, image_id, step.param, timeout)
        except HandoffTimeout as exc:
            raise HandoffExpired() from exc
        except HandoffCancelled as exc:
            raise TaskCancelled() from exc

        if step.kind == "confirm":
            if answer != "yes":
                raise TaskCancelled()
            return
        if step.kind == "param" and step.param:
            variables[step.param] = answer
        if step.fill_locator is not None:
            await self._pause()
            locator = step.fill_locator
            await self._retry("fill", lambda: session.fill(locator, answer, 15000))
