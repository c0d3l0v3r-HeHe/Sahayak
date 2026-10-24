"""Record and verify flows against real websites.

    # 1. Record: opens a browser; your clicks are turned into Playwright code you can
    #    translate into flow steps (prefer role/label/placeholder locators).
    uv run python -m scripts.record_flow record https://enquiry.indianrail.gov.in/mntes/

    # 2. Verify: run a flow through the real runner. Hand-offs (CAPTCHA/OTP/confirm) are
    #    asked in this terminal; screenshots go to ./data/verify/<flow_id>/.
    uv run python -m scripts.record_flow verify train_running_status --live -p train_no=12301
    uv run python -m scripts.record_flow verify pnr_status --live -p pnr=1234567890 --mark-verified

Without --live the flow runs against the mock replicas (start the API first).
`--mark-verified` stamps `verified_at` in the flow JSON after a successful live run.
"""

import argparse
import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.core.config import get_settings
from app.engine.playwright_engine import PlaywrightEngine
from app.flows.registry import DEFINITIONS_DIR, FlowRegistry
from app.flows.runner import FlowFailed, FlowRunner, RunContext, RunnerConfig
from app.flows.validator import validate_params
from app.models.common import LocalizedText

RECORDINGS = Path(__file__).parent / "recordings"


class ConsoleContext(RunContext):
    def __init__(self, out: Path):
        self.out = out
        self.n = 0
        out.mkdir(parents=True, exist_ok=True)

    async def step(self, message: LocalizedText) -> None:
        print(f"  • {message.en}  |  {message.hi}")

    async def screenshot(self, image: bytes) -> str:
        self.n += 1
        path = self.out / f"{self.n:02d}.jpg"
        path.write_bytes(image)
        print(f"    [screenshot] {path}")
        return path.stem

    async def ask(self, kind, prompt, image_id, param, timeout_s) -> str:
        if image_id:
            print(f"    [image] {self.out / (image_id + '.jpg')}")
        return await asyncio.to_thread(input, f"  ? [{kind}] {prompt.en} > ")

    async def cancelled(self) -> bool:
        return False


def record(url: str) -> int:
    RECORDINGS.mkdir(exist_ok=True)
    target = RECORDINGS / f"{datetime.now():%Y%m%d-%H%M%S}.py"
    print(f"Recording to {target}. Close the browser window when done.")
    cmd = [sys.executable, "-m", "playwright", "codegen", "--target", "python-async",
           "--viewport-size", "412,860", "-o", str(target), url]  # fmt: skip
    return subprocess.call(cmd)


async def verify(flow_id: str, live: bool, params: dict[str, str], mark: bool, headed: bool) -> int:
    settings = get_settings()
    flow = FlowRegistry.load().get(flow_id)
    if flow is None:
        print(f"unknown flow {flow_id}")
        return 2
    clean, missing, invalid = validate_params(flow, params)
    if missing or invalid:
        print(f"missing={missing} invalid={invalid}")
        return 2
    engine = PlaywrightEngine(headless=not headed)
    await engine.start()
    cfg = RunnerConfig(
        demo_mode=not live,
        mock_sites_url=settings.mock_sites_url,
        delay_min_ms=settings.action_delay_min_ms,
        delay_max_ms=settings.action_delay_max_ms,
        handoff_timeout_s=600,
    )
    runner = FlowRunner(engine, cfg)
    print(f"Running {flow_id} against {runner.base_url(flow)}")
    try:
        result = await runner.run(flow, clean, ConsoleContext(Path("data/verify") / flow_id))
    except FlowFailed as exc:
        print(f"FAILED: {exc.message.en}  ({exc.detail})")
        return 1
    finally:
        await engine.stop()
    print("\nRESULT (en):", result.text.en)
    print("RESULT (hi):", result.text.hi)
    print("DATA:", json.dumps(result.data, ensure_ascii=False, indent=2)[:2000])
    if mark and live:
        path = DEFINITIONS_DIR / f"{flow_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["verified_at"] = datetime.now(UTC).isoformat(timespec="seconds")
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"marked {path.name} verified_at={data['verified_at']}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    rec = sub.add_parser("record", help="open playwright codegen on a URL")
    rec.add_argument("url")
    ver = sub.add_parser("verify", help="run a flow and print what happens")
    ver.add_argument("flow_id")
    ver.add_argument("--live", action="store_true", help="use the real website (not DEMO_MODE)")
    ver.add_argument("-p", "--param", action="append", default=[], help="name=value")
    ver.add_argument("--mark-verified", action="store_true")
    ver.add_argument("--headed", action="store_true", help="show the browser")
    args = parser.parse_args()
    if args.cmd == "record":
        return record(args.url)
    params = dict(p.split("=", 1) for p in args.param)
    return asyncio.run(verify(args.flow_id, args.live, params, args.mark_verified, args.headed))


if __name__ == "__main__":
    raise SystemExit(main())
