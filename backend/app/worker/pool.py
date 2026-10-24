"""A small browser pool: one Chromium per worker, N concurrent isolated contexts."""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from urllib.parse import urlparse

from app.engine.base import BrowserEngine


class BrowserPool:
    def __init__(self, engine: BrowserEngine, concurrency: int, per_site: int):
        self.engine = engine
        self.concurrency = concurrency
        self._slots = asyncio.Semaphore(concurrency)
        self._sites: defaultdict[str, asyncio.Semaphore] = defaultdict(
            lambda: asyncio.Semaphore(per_site)
        )
        self.active = 0

    async def start(self) -> None:
        await self.engine.start()

    async def stop(self) -> None:
        await self.engine.stop()

    @asynccontextmanager
    async def slot(self, site_url: str) -> AsyncIterator[BrowserEngine]:
        """Wait for a free slot and for the site's politeness limit."""
        host = urlparse(site_url).netloc or site_url
        async with self._sites[host], self._slots:
            self.active += 1
            try:
                yield self.engine
            finally:
                self.active -= 1
