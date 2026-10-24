"""Validate flow definitions (JSON schema + semantic checks) and task parameters."""

import re
from datetime import date, timedelta
from typing import Any

import jsonschema
from pydantic import ValidationError

from app.core.timeutil import local_today
from app.flows.templating import TemplateError, render, variables
from app.models.flow import (
    AskUserStep,
    ClickStep,
    ExtractStep,
    FillStep,
    FlowDefinition,
    GotoStep,
    IfExistsStep,
    SelectStep,
    Step,
)

BUILTIN_VARS = {"base", "today", "lang"}


class FlowValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__("; ".join(errors))


_schema_cache: dict[str, Any] | None = None


def flow_json_schema() -> dict[str, Any]:
    global _schema_cache
    if _schema_cache is None:
        _schema_cache = FlowDefinition.model_json_schema(by_alias=True)
    return _schema_cache


def _check_template(text: str, known: set[str], where: str, errors: list[str]) -> None:
    try:
        render(text, {})  # syntax / filter check
    except TemplateError as exc:
        errors.append(f"{where}: {exc}")
        return
    except ValueError:
        pass  # e.g. date filter on empty input — fine at validation time
    for name in variables(text):
        if name not in known:
            errors.append(f"{where}: unknown variable '{name}'")


def _check_locators(step: Step, known: set[str], where: str, errors: list[str]) -> None:
    for key in ("locator", "screenshot_locator", "fill_locator"):
        loc = getattr(step, key, None)
        if loc is None:
            continue
        for attr in ("name", "label", "placeholder", "text", "css", "test_id"):
            value = getattr(loc, attr)
            if isinstance(value, str) and "{{" in value:
                _check_template(value, known, f"{where}.{key}.{attr}", errors)


def _walk(
    steps: list[Step],
    known: set[str],
    confirmed: bool,
    path: str,
    errors: list[str],
    asks: set[str],
) -> bool:
    for i, step in enumerate(steps):
        where = f"{path}[{i}]({step.type})"
        _check_locators(step, known, where, errors)
        if isinstance(step, GotoStep):
            _check_template(step.url, known, where, errors)
        elif isinstance(step, FillStep | SelectStep):
            _check_template(step.value, known, where, errors)
        elif isinstance(step, ClickStep) and step.changes_state and not confirmed:
            errors.append(f"{where}: state-changing click must follow ask_user kind=confirm")
        elif isinstance(step, ExtractStep):
            known.add(step.into)
        elif isinstance(step, AskUserStep):
            asks.add(step.kind)
            if step.kind in ("captcha", "otp") and step.fill_locator is None:
                errors.append(f"{where}: {step.kind} hand-off needs fill_locator")
            if step.kind == "captcha" and step.screenshot_locator is None:
                errors.append(f"{where}: captcha hand-off needs screenshot_locator")
            if step.kind == "param":
                if not step.param:
                    errors.append(f"{where}: param hand-off needs `param`")
                else:
                    known.add(step.param)
            if step.kind == "confirm":
                confirmed = True
        elif isinstance(step, IfExistsStep):
            then_known, else_known = set(known), set(known)
            c1 = _walk(step.then, then_known, confirmed, f"{where}.then", errors, asks)
            c2 = _walk(step.else_, else_known, confirmed, f"{where}.else", errors, asks)
            known |= then_known & else_known
            confirmed = confirmed or (c1 and c2)
    return confirmed


def validate_flow(data: dict[str, Any] | FlowDefinition) -> FlowDefinition:
    errors: list[str] = []
    if isinstance(data, FlowDefinition):
        flow = data
    else:
        validator = jsonschema.Draft202012Validator(flow_json_schema())
        schema_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        if schema_errors:
            raise FlowValidationError(
                [f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in schema_errors]
            )
        try:
            flow = FlowDefinition.model_validate(data)
        except ValidationError as exc:
            raise FlowValidationError(
                [f"{'/'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()]
            ) from exc

    names = [p.name for p in flow.params]
    if len(names) != len(set(names)):
        errors.append("params: duplicate names")
    for p in flow.params:
        if p.regex:
            try:
                re.compile(p.regex)
            except re.error as exc:
                errors.append(f"params.{p.name}: bad regex ({exc})")
        if p.type == "enum" and not p.options:
            errors.append(f"params.{p.name}: enum needs options")

    known = set(names) | BUILTIN_VARS
    for p in flow.params:
        if p.type == "enum":
            known |= {f"{p.name}_label", f"{p.name}_label_hi"}
    asks: set[str] = set()
    _walk(flow.steps, known, False, "steps", errors, asks)
    for kind in ("captcha", "otp"):
        if kind in asks and kind not in flow.requires:
            errors.append(f"requires: flow asks for {kind} but does not declare it")
    for lang in ("en", "hi"):
        _check_template(
            getattr(flow.result_template, lang), known, f"result_template.{lang}", errors
        )

    if flow.confirm_template:
        for lang in ("en", "hi"):
            _check_template(
                getattr(flow.confirm_template, lang),
                set(names) | BUILTIN_VARS,
                f"confirm_template.{lang}",
                errors,
            )

    if errors:
        raise FlowValidationError(errors)
    return flow


# ---- parameters ----------------------------------------------------------


def normalize_date(value: str, today: date | None = None) -> str | None:
    today = today or local_today()
    v = value.strip().lower()
    relative = {
        "today": 0, "aaj": 0, "आज": 0,
        "yesterday": -1, "kal": -1, "कल": -1,
        "tomorrow": 1,
    }  # fmt: skip
    if v in relative:
        return (today + timedelta(days=relative[v])).isoformat()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            from datetime import datetime

            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def coerce_param(flow: FlowDefinition, name: str, raw: Any) -> str | None:
    """Normalize one parameter value; returns None if it is invalid."""
    p = flow.param(name)
    if p is None or raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    if p.type == "int":
        digits = re.sub(r"[\s,]", "", value)
        if not re.fullmatch(r"-?\d+", digits):
            return None
        value = str(int(digits))
    elif p.type == "date":
        normalized = normalize_date(value)
        if normalized is None:
            return None
        value = normalized
    elif p.type == "enum":
        lowered = value.lower()
        for opt in p.options or []:
            candidates = {opt.value.lower(), opt.label.en.lower(), opt.label.hi.lower()}
            candidates |= {s.lower() for s in opt.synonyms}
            if lowered in candidates:
                value = opt.value
                break
        else:
            return None
    if p.regex and not re.fullmatch(p.regex, value):
        return None
    return value


def validate_params(
    flow: FlowDefinition, params: dict[str, Any]
) -> tuple[dict[str, str], list[str], list[str]]:
    """Returns (clean params, missing names, invalid names)."""
    clean: dict[str, str] = {}
    missing: list[str] = []
    invalid: list[str] = []
    for p in flow.params:
        raw = params.get(p.name)
        if raw in (None, ""):
            if p.default is not None:
                clean[p.name] = coerce_param(flow, p.name, p.default) or p.default
            elif p.required:
                missing.append(p.name)
            continue
        value = coerce_param(flow, p.name, raw)
        if value is None:
            invalid.append(p.name)
        else:
            clean[p.name] = value
    return clean, missing, invalid


def redacted_params(flow: FlowDefinition, params: dict[str, str]) -> dict[str, str]:
    from app.flows.templating import mask

    out = {}
    for k, v in params.items():
        p = flow.param(k)
        out[k] = mask(v) if p and p.sensitive else v
    return out
