# Adding a flow

A flow teaches Sahayak one task on one website. It is a JSON file: no Python needed.

## 1. Record the clicks

```bash
cd backend
uv run python -m scripts.record_flow record https://example.gov.in/some-page
```

This opens `playwright codegen`. Do the task by hand and the generated code is saved to
`scripts/recordings/`. Use it as a guide for selectors; don't copy it verbatim.

**Choosing locators**, best first:

1. `{"role": "button", "name": "Get Status"}`: what a screen reader sees; survives redesigns
2. `{"label": "PNR Number"}`, `{"placeholder": "Enter PNR No."}`
3. `{"text": "Invalid captcha"}`: visible text
4. `{"css": "#inputPnrNo"}`: last resort. Playwright extensions such as `:has-text()` and
   `:text-is()` work here.

Locator options: `exact`, `nth`, and `visible: true` (sites often render hidden duplicates of an
element, e.g. a desktop and a mobile filter panel). Every string can use `{{templates}}`.

## 2. Write the JSON

Create `backend/app/flows/definitions/<flow_id>.json`:

```json
{
  "id": "ration_card_status",
  "version": 1,
  "title": {"en": "Ration card status", "hi": "राशन कार्ड की स्थिति"},
  "description": {"en": "Check your ration card application.", "hi": "राशन कार्ड आवेदन की स्थिति देखें।"},
  "site": "https://example.gov.in",
  "mock_path": "/ration",
  "est_minutes_saved": 6,
  "keywords": ["ration", "राशन", "card"],
  "examples": ["mera ration card kahan tak pahuncha"],
  "params": [
    {"name": "application_no", "regex": "^[A-Z0-9]{8,14}$", "sensitive": true,
     "prompt": {"en": "Please tell me your application number.", "hi": "कृपया अपना आवेदन नंबर बताइए।"}}
  ],
  "steps": [
    {"type": "narrate", "en": "Opening the ration card website.", "hi": "राशन कार्ड वेबसाइट खोल रहे हैं।"},
    {"type": "goto", "url": "{{base}}/status"},
    {"type": "fill", "locator": {"label": "Application Number"}, "value": "{{application_no}}"},
    {"type": "ask_user", "kind": "captcha",
     "prompt": {"en": "Please read the letters in the picture.", "hi": "कृपया तस्वीर में लिखे अक्षर पढ़िए।"},
     "screenshot_locator": {"css": "#captchaImg"}, "fill_locator": {"label": "Captcha"}},
    {"type": "click", "locator": {"role": "button", "name": "Search"}},
    {"type": "wait_for", "locator": {"css": "#result, .error"}},
    {"type": "if_exists", "locator": {"css": ".error"}, "timeout_ms": 0, "then": [
      {"type": "fail", "message": {"en": "Application not found.", "hi": "आवेदन नहीं मिला।"}}
    ]},
    {"type": "extract", "locator": {"css": "#result .status"}, "into": "status"},
    {"type": "screenshot"}
  ],
  "result_template": {"en": "Your application is: {{status}}.", "hi": "आपके आवेदन की स्थिति: {{status}}।"},
  "confirm_template": {"en": "Shall I check application {{application_no}}?", "hi": "क्या मैं आवेदन {{application_no}} की स्थिति देखूँ?"},
  "requires": ["captcha"],
  "verified_at": null,
  "notes": "Recorded on YYYY-MM-DD against https://example.gov.in/status."
}
```

### Step reference

| Step | Fields | Notes |
|---|---|---|
| `goto` | `url` | Relative URLs (`/x`) join `{{base}}` |
| `fill` | `locator`, `value`, `typing_delay_ms?` | Set `typing_delay_ms` for inputs that react to key presses |
| `click` | `locator`, `changes_state?`, `force?` | `changes_state: true` **requires** an earlier `ask_user kind=confirm` |
| `select` | `locator`, `value` | Matches the option value, then the label |
| `press` | `locator`, `key` | e.g. `Enter` |
| `wait_for` | `locator`, `state` | `visible` (default), `hidden`, `attached`, `detached` |
| `extract` | `locator`, `as`, `into` | `text`, `attribute` (+`attribute`), `table` (+`columns`), `list` (+`fields`, `limit`) |
| `screenshot` | `locator?` | Sent to the app as the live view |
| `ask_user` | `kind`, `prompt`, `screenshot_locator?`, `fill_locator?`, `param?` | `captcha`, `otp`, `confirm`, `param`. The answer is never stored. |
| `if_exists` | `locator`, `then`, `else` | `timeout_ms: 0` checks right now |
| `assert` | `locator`, `text_contains?`, `message?` | |
| `narrate` | `en`, `hi` | A plain-language step shown and spoken in the app |
| `pause` | `ms` | ≤ 10 s, for debounced filters or animations |
| `fail` | `message` | Stop with a friendly bilingual message |

Every step accepts `timeout_ms` and an optional `narrate`.

**Template variables:** each param, values from earlier `extract` steps, `base`, `today` and
`lang`, plus `<param>_label` / `<param>_label_hi` for enum params. **Filters:** `upper`,
`lower`, `title`, `mask`, `default:x`, `date:%d-%b-%Y`, `inr` (Indian digit grouping),
`range10` (age bucket). Result templates support `{{#list}}…{{/list}}` loops with `{{@n}}`,
and `{{^list}}…{{/list}}` for the empty case.

Print the full JSON Schema with:

```bash
uv run python -c "import json; from app.flows.validator import flow_json_schema; print(json.dumps(flow_json_schema(), indent=2))"
```

## 3. Build a mock replica

Add `backend/mock_sites/static/<mock_path>/...`: a small static page that **mirrors the live
page's structure** (same labels, roles and ids), so the same steps run against it. Keep the
"demo replica — not a government website" banner. Put any server-side behaviour, such as a fake
CAPTCHA, in `mock_sites/server.py`.

## 4. Test it

Add a case to `backend/tests/test_flows_integration.py` (it runs the real worker and headless
Chromium against the mocks), then:

```bash
uv run pytest -q
uv run python -m scripts.record_flow verify ration_card_status -p application_no=AB12345678   # against mocks (API must be running)
```

## 5. Verify against the live site

```bash
uv run python -m scripts.record_flow verify ration_card_status --live --headed \
    -p application_no=AB12345678 --mark-verified
```

Hand-offs are asked in the terminal, and screenshots go to `data/verify/<flow_id>/`. On success,
`--mark-verified` stamps `verified_at`. If you could not verify a flow, leave `verified_at: null`
and say why in `notes`.

## Rules

- Never automate around a CAPTCHA or OTP: always `ask_user`.
- Anything that submits or changes something on the site must be preceded by `ask_user kind=confirm`.
  The validator enforces this for clicks marked `changes_state`.
- Mark identifiers `"sensitive": true` so they are masked in history and logs.
- Keep it polite: no loops, no rapid retries. The runner already adds human-like pauses.
