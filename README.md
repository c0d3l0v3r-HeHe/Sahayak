# Sahayak · सहायक

**A voice-first assistant that completes tasks on government and public websites for people who struggle to use them.**

Speak in Hindi, English or Hinglish — *"मेरी ट्रेन कहाँ है?"*, *"check my PNR"* — and Sahayak
understands the request, confirms it in plain language, runs a saved browser flow on the real
website, hands control back to you for CAPTCHA / OTP / final confirmation, and reads the result aloud.

> Status: under active development (hackathon build — Codesprint 2026, InnovaThon, CodeBuild 2.0).

## Contents

- [Features](#features)
- [Quick start](#quick-start)
- [Repository layout](#repository-layout)
- [Privacy & safety](#privacy--safety)
- [License](#license)

## Features

- Voice in/out in Hindi and English (on-device, free)
- Declarative JSON "flows" — add a website without writing code
- CAPTCHA, OTP and confirmation are always handed to the human
- `DEMO_MODE` runs everything against bundled mock sites — stage-safe
- Costs ₹0 to run: works with no API keys at all

## Quick start

_Detailed walkthrough coming in a later phase._

```bash
cp .env.example .env
docker compose up --build
```

## Repository layout

```
backend/   FastAPI API, worker, flows, mock sites
mobile/    Flutter app (Android first)
docs/      Architecture and how to add a flow
```

## Privacy & safety

- Passwords, OTPs and CAPTCHA answers are never stored.
- Personal identifiers are redacted in logs.
- Task details auto-delete after 7 days; hand-off records after 10 minutes.

## License

[MIT](LICENSE)
