from app.core.config import Settings
from app.engine.base import BrowserEngine
from app.engine.playwright_engine import PlaywrightEngine


def create_engine(settings: Settings) -> BrowserEngine:
    playwright = PlaywrightEngine(headless=settings.headless)
    if settings.browser_engine == "tinyfish" and settings.tinyfish_api_key:
        from app.engine.tinyfish_engine import TinyFishEngine

        return TinyFishEngine(settings.tinyfish_api_key, fallback=playwright)
    return playwright
