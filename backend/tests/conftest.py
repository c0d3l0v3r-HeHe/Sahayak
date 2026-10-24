import asyncio
import os
import socket
import tempfile
import threading
import time
from uuid import uuid4

# Configure before the app (and its cached settings) is imported.
os.environ.update(
    {
        "MONGO_DB": f"sahayak_test_{uuid4().hex[:8]}",
        "DEMO_MODE": "true",
        "MOCK_CAPTCHA_CODE": "K7PQR",
        "ACTION_DELAY_MIN_MS": "0",
        "ACTION_DELAY_MAX_MS": "0",
        "STEP_RETRIES": "1",
        "HANDOFF_TIMEOUT_S": "30",
        "JWT_SECRET": "test-secret-0123456789abcdef0123456789",
        "SCREENSHOT_DIR": tempfile.mkdtemp(prefix="sahayak-screens-"),
        "LOG_LEVEL": "WARNING",
        "INTENT_PROVIDER": "rules",
    }
)
os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")

import httpx  # noqa: E402
import pytest  # noqa: E402
import uvicorn  # noqa: E402
from pymongo import MongoClient  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.db.mongo import connect, ensure_indexes  # noqa: E402
from app.engine.playwright_engine import PlaywrightEngine  # noqa: E402
from app.flows.registry import get_registry  # noqa: E402
from app.handoff.service import LOCAL  # noqa: E402
from app.main import create_app  # noqa: E402
from mock_sites.server import create_mock_app  # noqa: E402


def _mongo_available() -> bool:
    try:
        MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=1000).admin.command("ping")
        return True
    except Exception:
        return False


MONGO_OK = _mongo_available()


def pytest_collection_modifyitems(config, items):
    skip = pytest.mark.skip(reason="MongoDB not reachable at MONGO_URL")
    for item in items:
        if "mongo" in item.keywords and not MONGO_OK:
            item.add_marker(skip)


def pytest_sessionfinish(session, exitstatus):
    if MONGO_OK:
        MongoClient(os.environ["MONGO_URL"]).drop_database(os.environ["MONGO_DB"])


@pytest.fixture(scope="session")
def settings():
    return get_settings()


@pytest.fixture(scope="session")
def mock_sites(settings):
    """Serve the mock replicas on a real port (Playwright needs real HTTP)."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    server = uvicorn.Server(
        uvicorn.Config(create_mock_app(settings), host="127.0.0.1", port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    url = f"http://127.0.0.1:{port}"
    settings.mock_sites_url = url
    yield url
    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="session")
async def db(settings):
    database = connect(settings)
    await ensure_indexes(database)
    yield database
    await database.close()


@pytest.fixture(scope="session")
async def engine():
    eng = PlaywrightEngine(headless=True)
    await eng.start()
    yield eng
    await eng.stop()


@pytest.fixture(scope="session")
async def app(settings):
    application = create_app(settings)
    async with application.router.lifespan_context(application):
        yield application


@pytest.fixture(scope="session")
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture(scope="session")
async def worker(app, mock_sites, engine, settings):
    from app.worker.worker import Worker

    state = app.state.sahayak
    w = Worker(settings, state.db, engine, get_registry(), LOCAL, queue=state.queue)
    w.poll_interval_s = 0.1
    task = asyncio.create_task(w.run_forever())
    yield w
    w.stop()
    await asyncio.wait_for(task, timeout=10)


async def login(client, device_id: str | None = None) -> dict:
    resp = await client.post(
        "/v1/auth/anonymous",
        json={"device_id": device_id or f"dev-{uuid4().hex}", "language": "en"},
    )
    assert resp.status_code == 200, resp.text
    return {"Authorization": f"Bearer {resp.json()['token']}"}


@pytest.fixture
async def auth(client):
    return await login(client)
