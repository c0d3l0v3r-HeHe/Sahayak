import logging

from app.core.logging import RedactingFilter, redact, redact_value


def test_pnr_and_phone():
    assert "4512345678" not in redact("PNR 4512345678 checked")
    assert "9876543210" not in redact("call +91 9876543210")


def test_aadhaar_like():
    assert redact("id 1234 5678 9012") == "id [ID]"


def test_email_and_jwt():
    out = redact("user a.b@example.com token eyJhbGciOi.eyJzdWIiOi.c2lnbmF0dXJl")
    assert "example.com" not in out and "eyJ" not in out


def test_sensitive_keys():
    out = redact('{"otp": "482913", "captcha": "K7PQR", "flow": "pnr_status"}')
    assert "482913" not in out and "K7PQR" not in out and "pnr_status" in out
    assert "secret" not in redact("password=secret&x=1")


def test_train_numbers_kept():
    assert redact("train 12301 delayed") == "train 12301 delayed"


def test_redact_value_nested():
    out = redact_value({"a": ["PNR 4512345678"], "b": 3})
    assert out == {"a": ["PNR [NUM10]"], "b": 3}


def test_filter_on_record(caplog):
    logger = logging.getLogger("redaction-test")
    logger.addFilter(RedactingFilter())
    with caplog.at_level(logging.INFO, logger="redaction-test"):
        logger.info("pnr is %s", "4512345678")
    assert "4512345678" not in caplog.text
