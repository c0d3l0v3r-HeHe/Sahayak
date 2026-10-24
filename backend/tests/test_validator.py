import copy
import json

import pytest

from app.flows.registry import DEFINITIONS_DIR, FlowRegistry
from app.flows.validator import (
    FlowValidationError,
    coerce_param,
    normalize_date,
    redacted_params,
    validate_flow,
    validate_params,
)

L = {"en": "x", "hi": "x"}


def base_flow(**overrides):
    flow = {
        "id": "demo",
        "version": 1,
        "title": L,
        "description": L,
        "site": "https://example.org",
        "mock_path": "/demo",
        "params": [{"name": "q", "prompt": L}],
        "steps": [{"type": "goto", "url": "{{base}}/?q={{q}}"}],
        "result_template": {"en": "done {{q}}", "hi": "हो गया {{q}}"},
    }
    flow.update(overrides)
    return flow


def test_bundled_flows_are_valid():
    registry = FlowRegistry.load(DEFINITIONS_DIR)
    assert {f.id for f in registry.all()} == {"scheme_finder", "train_running_status", "pnr_status"}


def test_valid_minimal_flow():
    assert validate_flow(base_flow()).id == "demo"


def test_schema_rejects_unknown_step_type():
    with pytest.raises(FlowValidationError):
        validate_flow(base_flow(steps=[{"type": "teleport"}]))


def test_schema_rejects_missing_hindi():
    with pytest.raises(FlowValidationError):
        validate_flow(base_flow(title={"en": "only english"}))


def test_unknown_template_variable():
    with pytest.raises(FlowValidationError, match="unknown variable 'nope'"):
        validate_flow(base_flow(steps=[{"type": "goto", "url": "{{nope}}"}]))


def test_extracted_variables_become_known():
    steps = [
        {"type": "goto", "url": "{{base}}"},
        {"type": "extract", "locator": {"css": "h1"}, "into": "title"},
    ]
    flow = base_flow(steps=steps, result_template={"en": "{{title}}", "hi": "{{title}}"})
    validate_flow(flow)


def test_result_template_unknown_variable():
    with pytest.raises(FlowValidationError, match="result_template"):
        validate_flow(base_flow(result_template={"en": "{{ghost}}", "hi": "x"}))


def test_state_changing_click_requires_confirm():
    click = {
        "type": "click",
        "locator": {"role": "button", "name": "Submit"},
        "changes_state": True,
    }
    with pytest.raises(FlowValidationError, match="confirm"):
        validate_flow(base_flow(steps=[click]))
    confirm = {"type": "ask_user", "kind": "confirm", "prompt": L}
    validate_flow(base_flow(steps=[confirm, click], requires=["confirm"]))


def test_captcha_handoff_needs_locators_and_requires():
    ask = {"type": "ask_user", "kind": "captcha", "prompt": L}
    with pytest.raises(FlowValidationError) as exc:
        validate_flow(base_flow(steps=[ask]))
    joined = " ".join(exc.value.errors)
    assert "fill_locator" in joined and "screenshot_locator" in joined and "requires" in joined


def test_locator_needs_exactly_one_strategy():
    step = {"type": "click", "locator": {"role": "button", "css": "button"}}
    with pytest.raises(FlowValidationError):
        validate_flow(base_flow(steps=[step]))


def test_duplicate_params():
    with pytest.raises(FlowValidationError, match="duplicate"):
        validate_flow(base_flow(params=[{"name": "q", "prompt": L}, {"name": "q", "prompt": L}]))


def test_if_exists_branches_validated():
    step = {
        "type": "if_exists",
        "locator": {"text": "x"},
        "then": [{"type": "goto", "url": "{{zzz}}"}],
    }
    with pytest.raises(FlowValidationError, match="zzz"):
        validate_flow(base_flow(steps=[step]))


def test_locator_template_checked():
    step = {"type": "click", "locator": {"role": "radio", "name": "{{missing}}"}}
    with pytest.raises(FlowValidationError, match="missing"):
        validate_flow(base_flow(steps=[step]))


# ---- params ---------------------------------------------------------------


@pytest.fixture(scope="module")
def flows():
    return FlowRegistry.load()


def test_validate_params_ok(flows):
    flow = flows.get("pnr_status")
    clean, missing, invalid = validate_params(flow, {"pnr": " 4512345678 "})
    assert clean == {"pnr": "4512345678"} and not missing and not invalid


def test_validate_params_missing_and_invalid(flows):
    flow = flows.get("pnr_status")
    _, missing, _ = validate_params(flow, {})
    assert missing == ["pnr"]
    _, _, invalid = validate_params(flow, {"pnr": "123"})
    assert invalid == ["pnr"]


def test_defaults_applied(flows):
    flow = flows.get("train_running_status")
    clean, missing, _ = validate_params(flow, {"train_no": "12301"})
    assert not missing and len(clean["date"]) == 10


def test_enum_synonyms(flows):
    flow = flows.get("scheme_finder")
    assert coerce_param(flow, "gender", "Mahila") == "female"
    assert coerce_param(flow, "gender", "पुरुष") == "male"
    assert coerce_param(flow, "state", "UP") == "uttar_pradesh"
    assert coerce_param(flow, "state", "बिहार") == "bihar"
    assert coerce_param(flow, "state", "Atlantis") is None


def test_int_with_commas(flows):
    assert coerce_param(flows.get("scheme_finder"), "income", "1,20,000") == "120000"


def test_normalize_date():
    from datetime import date

    today = date(2026, 10, 24)
    assert normalize_date("today", today) == "2026-10-24"
    assert normalize_date("कल", today) == "2026-10-23"
    assert normalize_date("23/10/2026", today) == "2026-10-23"
    assert normalize_date("someday", today) is None


def test_redacted_params(flows):
    flow = flows.get("pnr_status")
    assert redacted_params(flow, {"pnr": "4512345678"}) == {"pnr": "••••••5678"}


def test_json_files_roundtrip():
    for path in DEFINITIONS_DIR.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        validate_flow(copy.deepcopy(data))
