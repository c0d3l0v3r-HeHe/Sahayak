# Contributing to Sahayak

Thanks for helping make government websites usable for everyone.

## Ground rules

- **Never bypass CAPTCHAs, OTPs or any security measure.** Hand them to the user.
- **Never store passwords, OTPs or CAPTCHA answers**, not even in logs or tests' fixtures.
- **Confirm before submitting** anything that changes state on a website.
- **Be polite to the sites:** low concurrency, human-like pacing, honest user agent.
- **Zero cost:** new dependencies must be free or have a local alternative.
- Every user-facing string is in **both** `app_en.arb` and `app_hi.arb`, in short, simple sentences.

## Setup

```bash
# Backend
cd backend
uv sync
uv run playwright install chromium
docker run -d -p 27017:27017 --name sahayak-mongo mongo:7
uv run pytest -q

# Mobile
cd mobile
flutter pub get
flutter test
```

## Checks (CI runs the same)

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q
cd mobile && flutter analyze && flutter test
```

## Adding a website

See [docs/adding-a-flow.md](docs/adding-a-flow.md). A good flow PR contains:

1. `backend/app/flows/definitions/<id>.json` with `notes` on how it was verified
2. a mock replica under `backend/mock_sites/static/`
3. an integration test in `backend/tests/test_flows_integration.py`
4. keywords and examples in Hindi and English, so the offline intent parser finds it

## Commit style

Short imperative subject ("Add ration card flow"), with a body explaining *why* when it isn't
obvious. Keep PRs focused.

## Code of conduct

Be kind. Assume good intent. Our users are often elderly or new to the internet; design and
write with them in mind.
