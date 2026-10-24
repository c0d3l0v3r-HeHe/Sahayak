"""Application settings, loaded from environment variables (and an optional .env file)."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    app_env: str = "dev"
    log_level: str = "INFO"

    # Database
    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "sahayak"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_ttl_days: int = 30

    # Demo mode routes every flow to the local mock sites
    demo_mode: bool = True
    mock_sites_url: str = "http://localhost:8000/mock"
    serve_mock_sites: bool = True  # mount the mock sites under /mock on the API

    # Intent providers (all optional; `rules` always works)
    intent_provider: str = ""  # force one of: gemini | groq | ollama | rules
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"
    ollama_url: str = ""
    ollama_model: str = "llama3.2"

    # Browser engine
    browser_engine: str = "playwright"  # playwright | tinyfish
    tinyfish_api_key: str = ""
    headless: bool = True

    # Worker
    worker_concurrency: int = 2
    per_site_concurrency: int = 2
    action_delay_min_ms: int = 250
    action_delay_max_ms: int = 700
    job_claim_timeout_s: int = 300
    job_max_attempts: int = 2
    handoff_timeout_s: int = 300
    step_retries: int = 2
    # Run the worker inside the API process (handy for single-process local dev / demos)
    embedded_worker: bool = False
    worker_internal_port: int = 8100
    worker_internal_url: str = ""  # how the API reaches this worker; auto-detected if empty
    # Fixed answer for the mock CAPTCHA (tests only). Empty = random letters.
    mock_captcha_code: str = ""

    # Storage
    screenshot_dir: Path = BACKEND_DIR / "data" / "screens"
    task_ttl_days: int = 7
    handoff_ttl_minutes: int = 10

    cors_origins: str = "*"


@lru_cache
def get_settings() -> Settings:
    return Settings()
