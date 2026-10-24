"""Browser engine abstraction. The flow runner only talks to these interfaces."""

from abc import ABC, abstractmethod
from typing import Any

from app.models.flow import FieldSpec, Locator


class TransientError(Exception):
    """Navigation hiccup or timeout — worth retrying."""


class ElementNotFound(Exception):
    pass


class BrowserSession(ABC):
    """One isolated browser context (cookies, storage) for a single task."""

    @abstractmethod
    async def goto(self, url: str, timeout_ms: int) -> None: ...

    @abstractmethod
    async def fill(self, locator: Locator, value: str, timeout_ms: int) -> None: ...

    @abstractmethod
    async def click(self, locator: Locator, timeout_ms: int) -> None: ...

    @abstractmethod
    async def select(self, locator: Locator, value: str, timeout_ms: int) -> None: ...

    @abstractmethod
    async def wait_for(self, locator: Locator, state: str, timeout_ms: int) -> None: ...

    @abstractmethod
    async def exists(self, locator: Locator, timeout_ms: int) -> bool: ...

    @abstractmethod
    async def text(self, locator: Locator, timeout_ms: int) -> str: ...

    @abstractmethod
    async def attribute(self, locator: Locator, name: str, timeout_ms: int) -> str | None: ...

    @abstractmethod
    async def table(self, locator: Locator, timeout_ms: int) -> list[dict[str, str]]: ...

    @abstractmethod
    async def items(
        self, locator: Locator, fields: dict[str, FieldSpec], limit: int | None, timeout_ms: int
    ) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def screenshot(self, locator: Locator | None = None) -> bytes:
        """JPEG bytes of the viewport, or of one element."""

    @abstractmethod
    async def close(self) -> None: ...


class BrowserEngine(ABC):
    name: str = "base"

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def new_session(self) -> BrowserSession: ...
