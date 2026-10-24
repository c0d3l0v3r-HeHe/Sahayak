"""Mock replicas of the supported websites, for tests and the stage-safe DEMO_MODE.

Pages are static HTML + JS under ./static. The only dynamic part is the fake CAPTCHA used by
the PNR replica: the server draws random letters as an SVG and checks the answer once.
Every page carries a visible "demo replica" banner — these are not the real websites.
"""

import hashlib
import random
import secrets
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.core.config import Settings

STATIC = Path(__file__).parent / "static"
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
COOKIE = "mock_sid"


def _captcha_svg(code: str, seed: int) -> str:
    rnd = random.Random(seed)
    w, h = 200, 64
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
        f'<rect width="{w}" height="{h}" fill="#f1efe6"/>',
    ]
    for _ in range(6):
        x1, y1, x2, y2 = (
            rnd.randint(0, w),
            rnd.randint(0, h),
            rnd.randint(0, w),
            rnd.randint(0, h),
        )
        parts.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#9a9a8a" stroke-width="1.5"/>'
        )
    step = w / (len(code) + 1)
    for i, ch in enumerate(code):
        x = step * (i + 0.6) + rnd.randint(-4, 4)
        y = 44 + rnd.randint(-6, 6)
        rot = rnd.randint(-22, 22)
        parts.append(
            f'<text x="{x:.0f}" y="{y}" font-family="monospace" font-size="34" font-weight="700" '
            f'fill="#2b2b2b" transform="rotate({rot} {x:.0f} {y})">{ch}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)


class PnrQuery(BaseModel):
    pnr: str = Field(pattern=r"^\d{10}$")
    captcha: str = Field(max_length=12)


def _pnr_result(pnr: str) -> dict:
    h = int(hashlib.sha256(pnr.encode()).hexdigest(), 16)
    trains = [
        ("12301", "Howrah Rajdhani Express", "Howrah Jn", "New Delhi", "3A"),
        ("12951", "Mumbai Rajdhani Express", "Mumbai Central", "New Delhi", "2A"),
        ("12627", "Karnataka Express", "KSR Bengaluru", "New Delhi", "SL"),
        ("12839", "Howrah Chennai Mail", "Howrah Jn", "MGR Chennai Central", "SL"),
        ("22691", "Rajdhani Express", "KSR Bengaluru", "Hazrat Nizamuddin", "3A"),
    ]
    number, name, src, dst, cls = trains[h % len(trains)]
    count = 1 + (h >> 8) % 4
    passengers = []
    for i in range(count):
        r = (h >> (12 + i * 6)) % 10
        coach = {"3A": "B", "2A": "A", "SL": "S"}[cls] + str(1 + r % 6)
        booking = f"WL {10 + r * 3}" if r < 4 else f"CNF/{coach}/{10 + r * 7}"
        if r < 2:
            current = f"WL {2 + r}"
        elif r < 4:
            current = f"RAC {5 + r}"
        else:
            current = f"CNF/{coach}/{10 + r * 7}"
        passengers.append(
            {
                "passenger": f"Passenger {i + 1}",
                "booking_status": booking,
                "current_status": current,
            }
        )
    day = 1 + (h >> 40) % 28
    return {
        "pnr": pnr,
        "train_number": number,
        "train_name": name.upper(),
        "train": f"{number} - {name}",
        "fare": str(500 + h % 3000),
        "from": src,
        "to": dst,
        "date": f"{day:02d}-11-2026",
        "class": cls,
        "chart": "Chart Not Prepared",
        "passengers": passengers,
    }


def create_mock_app(settings: Settings) -> FastAPI:
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    sessions: dict[str, tuple[str, float]] = {}

    def _sid(request: Request) -> str:
        return request.cookies.get(COOKIE) or secrets.token_hex(8)

    @app.get("/")
    async def index() -> RedirectResponse:
        return RedirectResponse("index.html")

    @app.get("/pnr/PNR/captcha.svg")
    async def captcha(request: Request) -> Response:
        sid = _sid(request)
        code = settings.mock_captcha_code or "".join(secrets.choice(ALPHABET) for _ in range(5))
        sessions[sid] = (code, time.time())
        if len(sessions) > 5000:  # keep memory bounded
            for key in sorted(sessions, key=lambda k: sessions[k][1])[:1000]:
                sessions.pop(key, None)
        resp = Response(
            _captcha_svg(code, secrets.randbits(32)),
            media_type="image/svg+xml",
            headers={"Cache-Control": "no-store"},
        )
        resp.set_cookie(COOKIE, sid, httponly=True, samesite="lax")
        return resp

    @app.post("/pnr/PNR/api/status")
    async def pnr_status(body: PnrQuery, request: Request) -> JSONResponse:
        sid = request.cookies.get(COOKIE, "")
        expected = sessions.pop(sid, None)  # a CAPTCHA can be tried only once
        if expected is None or expected[0].upper() != body.captcha.strip().upper():
            return JSONResponse({"error": "captcha"}, status_code=400)
        if body.pnr.startswith("0"):
            return JSONResponse({"error": "not_found"}, status_code=404)
        return JSONResponse(_pnr_result(body.pnr))

    app.mount("/", StaticFiles(directory=STATIC, html=True), name="static")
    return app
