"""Logging setup with PII redaction.

Every log record passes through `RedactingFilter`, which masks phone numbers, PNRs,
Aadhaar-like IDs, emails, JWTs and the values of sensitive keys (otp, captcha, password...).
"""

import logging
import re
from typing import Any

_SENSITIVE_KEYS = (
    r"otp|captcha|password|passwd|pin|token|secret|value|answer|pnr|phone|mobile|aadhaar"
)

_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # key=value / "key": "value" pairs for sensitive keys
    (
        re.compile(
            rf"(?i)(\b(?:{_SENSITIVE_KEYS})\b[\"']?\s*[:=]\s*[\"']?)([^\"'&,\s}}]+)",
        ),
        r"\1[REDACTED]",
    ),
    (re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "[JWT]"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "[EMAIL]"),
    # Aadhaar-like 12 digits (optionally grouped 4-4-4)
    (re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)"), "[ID]"),
    # +91 phone numbers
    (re.compile(r"\+?91[ -]?[6-9]\d{9}(?!\d)"), "[PHONE]"),
    # 10-digit numbers: PNRs and mobile numbers
    (re.compile(r"(?<!\d)\d{10}(?!\d)"), "[NUM10]"),
]


def redact(text: str) -> str:
    for pattern, repl in _PATTERNS:
        text = pattern.sub(repl, text)
    return text


def redact_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact(value)
    if isinstance(value, dict):
        return {k: redact_value(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return type(value)(redact_value(v) for v in value)
    return value


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - malformed record
            return True
        record.msg = redact(message)
        record.args = None
        return True


_configured = False


def setup_logging(level: str = "INFO") -> None:
    global _configured
    if _configured:
        return
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
    _configured = True
