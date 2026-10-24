"""Default engine: local headless Chromium via Playwright."""

import asyncio
import logging
import re
from typing import Any

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import Locator as PWLocator
from playwright.async_api import TimeoutError as PWTimeout

from app.engine.base import BrowserEngine, BrowserSession, ElementNotFound, TransientError
from app.models.flow import FieldSpec, Locator

log = logging.getLogger(__name__)

VIEWPORT: Any = {"width": 412, "height": 860}
USER_AGENT_SUFFIX = " SahayakAssistant/0.1 (+https://github.com/c0d3l0v3r-HeHe/Sahayak)"


def _key(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", header.strip().lower()).strip("_") or "col"


def resolve(root: Page | PWLocator, loc: Locator) -> PWLocator:
    if loc.role is not None:
        result = root.get_by_role(loc.role, name=loc.name, exact=loc.exact)  # type: ignore[arg-type]
    elif loc.label is not None:
        result = root.get_by_label(loc.label, exact=loc.exact)
    elif loc.placeholder is not None:
        result = root.get_by_placeholder(loc.placeholder, exact=loc.exact)
    elif loc.text is not None:
        result = root.get_by_text(loc.text, exact=loc.exact)
    elif loc.test_id is not None:
        result = root.get_by_test_id(loc.test_id)
    else:
        result = root.locator(loc.css or "")
    if loc.nth is not None:
        result = result.nth(loc.nth)
    return result


def _wrap(exc: Exception, what: str) -> Exception:
    if isinstance(exc, PWTimeout):
        return TransientError(f"timeout: {what}")
    msg = str(exc)
    if "net::" in msg or "Navigation" in msg or "Target closed" in msg:
        return TransientError(f"navigation: {what}")
    return ElementNotFound(f"{what}: {msg.splitlines()[0] if msg else exc!r}")


class PlaywrightSession(BrowserSession):
    def __init__(self, context: BrowserContext, page: Page):
        self.context = context
        self.page = page

    def _first(self, loc: Locator) -> PWLocator:
        el = resolve(self.page, loc)
        return el if loc.nth is not None else el.first

    async def goto(self, url: str, timeout_ms: int) -> None:
        try:
            await self.page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        except (PWTimeout, PlaywrightError) as exc:
            raise TransientError(f"could not open {url}: {exc}") from exc

    async def fill(self, locator: Locator, value: str, timeout_ms: int) -> None:
        try:
            await self._first(locator).fill(value, timeout=timeout_ms)
        except (PWTimeout, PlaywrightError) as exc:
            raise _wrap(exc, "fill") from None  # never chain: the message could carry the value

    async def click(self, locator: Locator, timeout_ms: int) -> None:
        try:
            await self._first(locator).click(timeout=timeout_ms)
        except (PWTimeout, PlaywrightError) as exc:
            raise _wrap(exc, "click") from exc

    async def select(self, locator: Locator, value: str, timeout_ms: int) -> None:
        el = self._first(locator)
        try:
            try:
                await el.select_option(value=value, timeout=timeout_ms)
            except PlaywrightError:
                await el.select_option(label=value, timeout=timeout_ms)
        except (PWTimeout, PlaywrightError) as exc:
            raise _wrap(exc, "select") from exc

    async def wait_for(self, locator: Locator, state: str, timeout_ms: int) -> None:
        try:
            await self._first(locator).wait_for(state=state, timeout=timeout_ms)  # type: ignore[arg-type]
        except (PWTimeout, PlaywrightError) as exc:
            raise _wrap(exc, f"wait_for {state}") from exc

    async def exists(self, locator: Locator, timeout_ms: int) -> bool:
        el = self._first(locator)
        if timeout_ms <= 0:
            return await el.is_visible()
        try:
            await el.wait_for(state="visible", timeout=timeout_ms)
            return True
        except (PWTimeout, PlaywrightError):
            return False

    async def text(self, locator: Locator, timeout_ms: int) -> str:
        try:
            el = self._first(locator)
            await el.wait_for(state="attached", timeout=timeout_ms)
            return " ".join((await el.inner_text(timeout=timeout_ms)).split())
        except (PWTimeout, PlaywrightError) as exc:
            raise _wrap(exc, "extract text") from exc

    async def attribute(self, locator: Locator, name: str, timeout_ms: int) -> str | None:
        try:
            el = self._first(locator)
            await el.wait_for(state="attached", timeout=timeout_ms)
            if name == "href":  # absolute URL, resolved by the browser
                return await el.evaluate("e => e.href || e.getAttribute('href')")
            return await el.get_attribute(name, timeout=timeout_ms)
        except (PWTimeout, PlaywrightError) as exc:
            raise _wrap(exc, "extract attribute") from exc

    async def table(self, locator: Locator, timeout_ms: int) -> list[dict[str, str]]:
        try:
            el = self._first(locator)
            await el.wait_for(state="visible", timeout=timeout_ms)
            rows: list[list[str]] = await el.evaluate(
                """t => Array.from(t.querySelectorAll('tr')).map(r =>
                    Array.from(r.querySelectorAll('th,td')).map(c => c.innerText.trim()))"""
            )
        except (PWTimeout, PlaywrightError) as exc:
            raise _wrap(exc, "extract table") from exc
        rows = [r for r in rows if any(r)]
        if not rows:
            return []
        headers = [_key(h) for h in rows[0]]
        return [dict(zip(headers, r, strict=False)) for r in rows[1:]]

    async def items(
        self, locator: Locator, fields: dict[str, FieldSpec], limit: int | None, timeout_ms: int
    ) -> list[dict[str, Any]]:
        all_items = resolve(self.page, locator)
        try:
            await all_items.first.wait_for(state="visible", timeout=timeout_ms)
        except (PWTimeout, PlaywrightError):
            return []
        count = await all_items.count()
        out: list[dict[str, Any]] = []
        for i in range(min(count, limit or count)):
            item = all_items.nth(i)
            row: dict[str, Any] = {}
            for name, spec in fields.items():
                target = resolve(item, spec.locator).first if spec.locator else item
                try:
                    if spec.attribute == "href":
                        row[name] = await target.evaluate(
                            "e => e.href || e.getAttribute('href')", timeout=2000
                        )
                    elif spec.attribute:
                        row[name] = await target.get_attribute(spec.attribute, timeout=2000)
                    else:
                        row[name] = " ".join((await target.inner_text(timeout=2000)).split())
                except (PWTimeout, PlaywrightError):
                    row[name] = None
            out.append(row)
        return out

    async def screenshot(self, locator: Locator | None = None) -> bytes:
        if locator is not None:
            return await self._first(locator).screenshot(type="jpeg", quality=80, timeout=10000)
        return await self.page.screenshot(type="jpeg", quality=60, timeout=10000)

    async def close(self) -> None:
        try:
            await self.context.close()
        except PlaywrightError:
            pass


class PlaywrightEngine(BrowserEngine):
    name = "playwright"

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._pw: Playwright | None = None
        self._browser: Browser | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._browser and self._browser.is_connected():
                return
            if self._pw is None:
                self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=self.headless)
            log.info("chromium %s started", self._browser.version)

    async def stop(self) -> None:
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._pw:
            await self._pw.stop()
            self._pw = None

    async def new_session(self) -> BrowserSession:
        if not (self._browser and self._browser.is_connected()):
            await self.start()  # relaunch after a browser crash
        assert self._browser is not None
        ua = await self._default_user_agent()
        context = await self._browser.new_context(
            viewport=VIEWPORT, locale="en-IN", timezone_id="Asia/Kolkata", user_agent=ua
        )
        page = await context.new_page()
        return PlaywrightSession(context, page)

    _ua: str | None = None

    async def _default_user_agent(self) -> str:
        if self._ua is None:
            assert self._browser is not None
            ctx = await self._browser.new_context()
            page = await ctx.new_page()
            base = await page.evaluate("navigator.userAgent")
            await ctx.close()
            self._ua = base + USER_AGENT_SUFFIX  # identify ourselves honestly
        return self._ua
