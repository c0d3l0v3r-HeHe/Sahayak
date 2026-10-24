"""Optional engine for sponsor demos: TinyFish's hosted web agent.

Used only when TINYFISH_API_KEY is set and BROWSER_ENGINE=tinyfish. TinyFish works from a
natural-language goal rather than our step DSL, so it is only used for flows that define a
`goal` and need no human hand-off (CAPTCHA / OTP can never be delegated). Everything else
falls back to local Playwright sessions.
Docs: https://docs.tinyfish.ai (POST /v1/automation/run with {url, goal}, X-API-Key header).
"""

import json
import logging
from typing import Any

import httpx

from app.engine.base import BrowserEngine, BrowserSession, TransientError
from app.engine.playwright_engine import PlaywrightEngine

log = logging.getLogger(__name__)

TINYFISH_RUN_URL = "https://agent.tinyfish.ai/v1/automation/run"


class TinyFishEngine(BrowserEngine):
    name = "tinyfish"

    def __init__(self, api_key: str, fallback: PlaywrightEngine, run_url: str = TINYFISH_RUN_URL):
        self.api_key = api_key
        self.fallback = fallback
        self.run_url = run_url

    async def start(self) -> None:
        await self.fallback.start()

    async def stop(self) -> None:
        await self.fallback.stop()

    async def new_session(self, viewport: dict[str, int] | None = None) -> BrowserSession:
        return await self.fallback.new_session(viewport)

    async def run_goal(self, url: str, goal: str, timeout_s: float = 180) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=timeout_s) as client:
                resp = await client.post(
                    self.run_url,
                    headers={"X-API-Key": self.api_key},
                    json={"url": url, "goal": goal},
                )
        except httpx.HTTPError as exc:
            raise TransientError(f"tinyfish unreachable: {exc}") from exc
        if resp.status_code >= 500:
            raise TransientError(f"tinyfish {resp.status_code}")
        resp.raise_for_status()
        body = resp.json()
        status = str(body.get("status", "COMPLETED")).upper()
        if status not in ("COMPLETED", "SUCCESS", "SUCCEEDED"):
            raise RuntimeError(f"tinyfish run {status}")
        result = body.get("result", body.get("resultJson", body))
        if isinstance(result, str):
            try:
                result = json.loads(result)
            except json.JSONDecodeError:
                result = {"text": result}
        return result if isinstance(result, dict) else {"items": result}
