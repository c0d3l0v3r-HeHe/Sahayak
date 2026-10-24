import pytest

from app.flows.templating import TemplateError, mask, render, variables


def test_simple_variable():
    assert render("PNR {{pnr}}", {"pnr": "1234567890"}) == "PNR 1234567890"


def test_missing_variable_renders_empty():
    assert render("a{{x}}b", {}) == "ab"


def test_filters():
    ctx = {"d": "2026-10-24", "g": "female", "p": "1234567890", "e": ""}
    assert render("{{d|date:%d-%m-%Y}}", ctx) == "24-10-2026"
    assert render("{{g|title}} {{g|upper}}", ctx) == "Female FEMALE"
    assert render("{{p|mask}}", ctx) == "••••••7890"
    assert render("{{e|default:none}}", ctx) == "none"


def test_dotted_lookup():
    assert render("{{a.b}}", {"a": {"b": 5}}) == "5"


def test_list_section_and_index():
    ctx = {"items": [{"name": "A"}, {"name": "B"}]}
    assert render("{{#items}}{{@n}}.{{name}} {{/items}}", ctx) == "1.A 2.B"


def test_inverted_section():
    tpl = "{{^items}}none{{/items}}{{#items}}x{{/items}}"
    assert render(tpl, {"items": []}) == "none"
    assert render(tpl, {"items": [1]}) == "x"


def test_dot_in_section():
    assert render("{{#xs}}[{{.}}]{{/xs}}", {"xs": ["a", "b"]}) == "[a][b]"


def test_unknown_filter():
    with pytest.raises(TemplateError):
        render("{{x|bogus}}", {"x": 1})


def test_variables():
    assert variables("{{a}} {{b|upper}} {{#c}}{{inner}}{{/c}}") == {"a", "b", "c"}


def test_mask_short():
    assert mask("12") == "••"


def test_filters_with_digits_in_name():
    assert render("{{a|range10}}", {"a": "67"}) == "61 - 70"
    assert render("{{a|range10}}", {"a": "7"}) == "0 - 10"
    assert render("{{a|range10}}", {"a": "120"}) == "101 - 110"
    assert render("₹{{a|inr}}", {"a": "1250000"}) == "₹12,50,000"
