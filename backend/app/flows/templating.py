"""Tiny template language for flow values and result messages.

{{pnr}}                     variable
{{date|date:%d-%m-%Y}}      filters: date, upper, lower, mask, default, title, inr, range10
{{#schemes}}..{{/schemes}}  repeat for each item of a list (item fields in scope, {{@n}} = 1-based index)
{{^schemes}}..{{/schemes}}  render only if the list is empty / missing
"""

import re
from datetime import date, datetime
from typing import Any

_VAR = re.compile(r"\{\{\s*([@a-zA-Z_][\w.]*|\.)((?:\s*\|\s*[a-z_][a-z0-9_]*(?::[^}|]*)?)*)\s*\}\}")
_SECTION = re.compile(r"\{\{([#^])\s*([a-zA-Z_][\w.]*)\s*\}\}(.*?)\{\{/\s*\2\s*\}\}", re.S)


class TemplateError(ValueError):
    pass


def variables(template: str) -> set[str]:
    """Top-level variable names used by a template (excluding names inside sections)."""
    names: set[str] = set()
    for m in _SECTION.finditer(template):
        names.add(m.group(2).split(".")[0])
    stripped = _SECTION.sub("", template)
    for m in _VAR.finditer(stripped):
        name = m.group(1)
        if not name.startswith("@") and name != ".":
            names.add(name.split(".")[0])
    return names


def _lookup(ctx: dict[str, Any], dotted: str) -> Any:
    if dotted in ctx:
        return ctx[dotted]
    cur: Any = ctx
    for part in dotted.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def mask(value: str, keep: int = 4) -> str:
    if len(value) <= keep:
        return "•" * len(value)
    return "•" * (len(value) - keep) + value[-keep:]


def _apply_filter(value: Any, name: str, arg: str | None) -> Any:
    match name:
        case "upper":
            return "" if value is None else str(value).upper()
        case "lower":
            return "" if value is None else str(value).lower()
        case "title":
            return "" if value is None else str(value).title()
        case "mask":
            return "" if value is None else mask(str(value), int(arg or 4))
        case "inr":  # Indian digit grouping: 120000 -> 1,20,000
            if value in (None, ""):
                return ""
            digits = str(value)
            if not digits.isdigit() or len(digits) <= 3:
                return digits
            head, tail = digits[:-3], digits[-3:]
            groups: list[str] = []
            while len(head) > 2:
                groups.insert(0, head[-2:])
                head = head[:-2]
            return ",".join([head, *groups, tail]) if head else ",".join([*groups, tail])
        case "range10":  # age bucket used by filters: 67 -> "61 - 70", 7 -> "0 - 10"
            if value in (None, ""):
                return ""
            n = min(int(value), 110)  # the last bucket on myScheme is "101 - 110"
            if n <= 10:
                return "0 - 10"
            lo = (n - 1) // 10 * 10 + 1
            return f"{lo} - {lo + 9}"
        case "default":
            return arg if value in (None, "") else value
        case "date":
            if value in (None, ""):
                return ""
            return _parse_date(value).strftime(arg or "%Y-%m-%d")
        case _:
            raise TemplateError(f"unknown filter: {name}")


def _render_vars(template: str, ctx: dict[str, Any]) -> str:
    def repl(m: re.Match[str]) -> str:
        value = _lookup(ctx, m.group(1))
        for f in filter(None, (s.strip() for s in m.group(2).split("|"))):
            fname, _, farg = f.partition(":")
            value = _apply_filter(value, fname.strip(), farg if _ else None)
        return "" if value is None else str(value)

    return _VAR.sub(repl, template)


def render(template: str, ctx: dict[str, Any]) -> str:
    def section(m: re.Match[str]) -> str:
        kind, name, body = m.group(1), m.group(2), m.group(3)
        value = _lookup(ctx, name)
        items = value if isinstance(value, list) else ([] if not value else [value])
        if kind == "^":
            return _render_vars(body, ctx) if not items else ""
        out = []
        for i, item in enumerate(items, start=1):
            scope = {**ctx, "@n": i, ".": item}
            if isinstance(item, dict):
                scope.update(item)
            out.append(_render_vars(body, scope))
        return "".join(out)

    return _render_vars(_SECTION.sub(section, template), ctx).strip()
