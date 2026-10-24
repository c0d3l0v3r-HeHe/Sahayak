# Sahayak · सहायक

**A voice-first assistant that completes tasks on government and public websites for people who
struggle to use them**: elderly people, people with low literacy or poor eyesight, or anyone
uncomfortable online.

Speak in Hindi, English or Hinglish (*"मेरी ट्रेन कहाँ है?"*, *"check my PNR"*). Sahayak:

1. **understands** the request and asks for any missing detail, one question at a time;
2. **confirms** in plain language: *"आप PNR 4512345678 की स्थिति जानना चाहते हैं?"*;
3. **runs a saved browser flow** on the real website, narrating each step with a live screenshot;
4. **hands control back to you** for CAPTCHA, OTP or final confirmation, and never bypasses them;
5. **reads the answer aloud** and shows it in large text.

> Built for Codesprint 2026, InnovaThon and CodeBuild 2.0. MIT licensed. Costs **₹0** to run.

| Home | Listening | Task in progress | CAPTCHA hand-off | Result |
|---|---|---|---|---|
| _screenshot_ | _screenshot_ | _screenshot_ | _screenshot_ | _screenshot_ |

<!-- Add screenshots to docs/screenshots/ and replace the placeholders above. -->

## What it can do today

| Task | Website | Hand-off | Live selectors |
|---|---|---|---|
| Find government schemes (age, gender, state) | myScheme | — | ✅ verified 2026-10-24 |
| Where is my train? (live running status) | NTES | — | ✅ verified 2026-10-24 |
| PNR status | Indian Railways PNR enquiry | CAPTCHA | ⚠️ partly verified, see [notes](backend/app/flows/definitions/pnr_status.json) |

All three run end to end against bundled **mock replicas** in `DEMO_MODE`, which is the stage-safe
default and needs no internet.

## Quick start (about 5 minutes)

**You need:** Docker, and Flutter 3.x with an Android emulator or phone for the app.
No API keys are needed.

```bash
git clone https://github.com/c0d3l0v3r-HeHe/Sahayak.git
cd Sahayak
cp .env.example .env            # defaults are fine: DEMO_MODE=true, no keys
docker compose up --build       # api + worker + mongo
```

Check it:

- http://localhost:8000/health → `{"status":"ok","demo_mode":true}`
- http://localhost:8000/docs → interactive API docs
- http://localhost:8000/mock/ → the demo replica websites
- http://localhost:8000/v1/stats → demo counters

Run the app:

```bash
cd mobile
flutter pub get
# Android emulator (10.0.2.2 is the host machine):
flutter run
# Real phone on the same Wi-Fi:
flutter run --dart-define=API_BASE_URL=http://<your-computer-ip>:8000
```

Optional: `docker compose exec api python -m scripts.seed --demo-history <device-id>` adds three
finished sample tasks so History isn't empty.

### Without Docker

```bash
docker run -d -p 27017:27017 mongo:7          # or any MongoDB, e.g. Atlas free tier
cd backend
uv sync && uv run playwright install chromium
EMBEDDED_WORKER=true uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`EMBEDDED_WORKER=true` runs the worker inside the API process: one command, good for a laptop demo.

## Demo walkthrough (stage script)

1. **Onboarding:** pick हिन्दी, allow the microphone.
2. **Train:** tap the mic and say *"मेरी ट्रेन 12301 कहाँ है?"* → confirm with **हाँ** → watch the
   steps tick off with the live screenshot → hear the result.
3. **PNR with CAPTCHA:** say *"check my PNR 4512345678"* → **Yes** → the bottom sheet shows the
   CAPTCHA image → read the letters aloud or type them → result: passenger status, read aloud.
   Point out that the answer went straight to the browser and was never stored.
4. **Schemes, no voice:** tap the *सरकारी योजनाएँ खोजें* chip → answer age, gender and state one at
   a time (voice or keypad) → five matching schemes with links → **Share**.
5. **Unsupported request:** say *"pizza order karo"* → a friendly "can't do that yet", plus the
   list of what it can do.
6. **Scale story:** `docker compose up --scale worker=3`, then open `/metrics` and `/v1/stats`.

Fallbacks if the venue misbehaves:
- no internet: everything above runs on the mock sites (`DEMO_MODE=true`);
- noisy room: use the keypad (*लिखकर बताएँ*);
- no LLM key: the offline rules parser handles all of the phrases above.

## Configuration

Everything is set through environment variables. See [.env.example](.env.example).

| Variable | Default | Purpose |
|---|---|---|
| `DEMO_MODE` | `true` | Route every flow to the mock replicas |
| `GEMINI_API_KEY` / `GROQ_API_KEY` / `OLLAMA_URL` | empty | Optional LLM for free-form requests (free tiers or local). Without one, the rules parser is used. |
| `INTENT_PROVIDER` | auto | Force `gemini`, `groq`, `ollama` or `rules` |
| `BROWSER_ENGINE` | `playwright` | `tinyfish` only if `TINYFISH_API_KEY` is set |
| `WORKER_CONCURRENCY` | `2` | Browser contexts per worker |
| `PER_SITE_CONCURRENCY` | `2` | Politeness limit per website, per worker |
| `ACTION_DELAY_MIN_MS` / `MAX_MS` | `250` / `700` | Human-like pause between actions |
| `TASK_TTL_DAYS` / `HANDOFF_TTL_MINUTES` | `7` / `10` | Data retention |
| `JWT_SECRET` | dev value | **Change in any shared deployment** |

**Live websites:** set `DEMO_MODE=false`. Government sites change and sometimes block automated
traffic. If a flow fails, the user gets a clear bilingual message, and
`uv run python -m scripts.record_flow verify <flow> --live` shows what changed.

## How it works

```
mobile/   Flutter app: voice in/out, Riverpod, go_router, Hindi + English
backend/
  app/api/v1      auth, intent, flows, tasks (+WebSocket), stats, /metrics
  app/intent      rules | Gemini | Groq | Ollama, strict JSON, fallback chain
  app/flows       flow DSL, validator, runner, definitions/*.json
  app/engine      BrowserEngine: Playwright (default), TinyFish (optional)
  app/queue       JobQueue interface + MongoJobQueue
  app/worker      worker loop, browser pool, internal hand-off endpoint
  app/handoff     CAPTCHA / OTP / confirm hand-offs (answers never stored)
  mock_sites/     replicas of each website for tests and demo mode
  scripts/        record_flow.py (codegen + live verify), seed.py
docs/             architecture (Mermaid diagrams), adding a flow
```

- **[Architecture and scalability](docs/architecture.md)**: system diagram, task sequence with
  hand-off, status machine, how it scales.
- **[Adding a flow](docs/adding-a-flow.md)**: teach Sahayak a new website with a JSON file.

## Privacy & safety

- CAPTCHA and OTP are **always** handed to the user, never solved or bypassed.
- Passwords, OTPs and CAPTCHA answers are **never stored**: not in the database, not in logs.
  Answers travel from the app to the waiting worker in memory only.
- Anything that submits or changes something on a website needs explicit confirmation. The flow
  validator rejects flows that skip it.
- Personal identifiers are masked in task history (`••••••5678`), and logs are redacted.
- Task details auto-delete after **7 days** and hand-off records after **10 minutes** (Mongo TTL indexes).
- Anonymous device login: no name, phone or email. **Delete my data** is in Settings.
- Polite automation: low per-site concurrency, human-like pacing, honest user agent.

## Cost: ₹0

| Piece | Free option |
|---|---|
| Database | MongoDB in Docker, or Atlas M0 free tier |
| Speech in/out | On-device Android speech recognition and TTS |
| Understanding requests | Offline rules parser; optional Gemini/Groq free tiers or local Ollama |
| Browser automation | Playwright + Chromium (open source) |
| Hosting | Any free-tier VM or a laptop for demos |

## Development

```bash
cd backend && uv run ruff check . && uv run mypy app && uv run pytest -q   # needs Mongo on :27017
cd mobile && flutter analyze && flutter test
```

The backend tests include end-to-end runs of every flow, with real headless Chromium against the
mock sites, including the CAPTCHA hand-off. CI runs everything on every push. See
[CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE)
