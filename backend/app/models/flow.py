"""Flow DSL: declarative JSON describing how to complete a task on a website."""

from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.common import LocalizedText


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class Locator(_Strict):
    """How to find an element. Prefer accessible queries; `css` is the last resort."""

    role: str | None = None
    name: str | None = None
    label: str | None = None
    placeholder: str | None = None
    text: str | None = None
    test_id: str | None = None
    css: str | None = None
    exact: bool = False
    nth: int | None = None
    visible: bool = False  # only match visible elements (sites often render hidden duplicates)

    @model_validator(mode="after")
    def _one_strategy(self) -> "Locator":
        strategies = [self.role, self.label, self.placeholder, self.text, self.test_id, self.css]
        if sum(s is not None for s in strategies) != 1:
            raise ValueError(
                "locator needs exactly one of role, label, placeholder, text, test_id, css"
            )
        if self.name is not None and self.role is None:
            raise ValueError("locator `name` is only valid together with `role`")
        return self


class FieldSpec(_Strict):
    """A field extracted relative to a list item."""

    locator: Locator | None = None  # None = the item itself
    attribute: str | None = None


# ---- steps ---------------------------------------------------------------


class _Step(_Strict):
    timeout_ms: int = Field(default=15000, ge=100, le=120000)
    narrate: LocalizedText | None = None  # optional progress message shown before the step


class GotoStep(_Step):
    type: Literal["goto"]
    url: str


class FillStep(_Step):
    type: Literal["fill"]
    locator: Locator
    value: str
    # Type key by key (for inputs that react to key events, e.g. autocomplete boxes)
    typing_delay_ms: int | None = Field(default=None, ge=0, le=1000)


class PressStep(_Step):
    type: Literal["press"]
    locator: Locator
    key: str = Field(pattern=r"^[A-Za-z0-9+]+$")  # e.g. Enter, Tab, ArrowDown


class PauseStep(_Strict):
    """Let a page settle (animations, debounced filters). Max 10 s."""

    type: Literal["pause"]
    ms: int = Field(ge=0, le=10000)


class ClickStep(_Step):
    type: Literal["click"]
    locator: Locator
    # Mark clicks that change state on the website (submit an application, payment...).
    # The validator requires a preceding `ask_user kind=confirm`.
    changes_state: bool = False
    force: bool = False  # click even if an overlay covers the element (custom dropdowns)


class SelectStep(_Step):
    type: Literal["select"]
    locator: Locator
    value: str


class WaitForStep(_Step):
    type: Literal["wait_for"]
    locator: Locator
    state: Literal["visible", "hidden", "attached", "detached"] = "visible"


class ExtractStep(_Step):
    type: Literal["extract"]
    locator: Locator
    as_: Literal["text", "table", "attribute", "list"] = Field(default="text", alias="as")
    into: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")
    attribute: str | None = None  # for as=attribute
    fields: dict[str, FieldSpec] | None = None  # for as=list
    columns: list[str] | None = None  # for as=table: rename columns by position
    limit: int | None = Field(default=None, ge=1, le=100)

    @model_validator(mode="after")
    def _check(self) -> "ExtractStep":
        if self.as_ == "attribute" and not self.attribute:
            raise ValueError("extract as=attribute needs `attribute`")
        if self.as_ == "list" and not self.fields:
            raise ValueError("extract as=list needs `fields`")
        return self


class ScreenshotStep(_Step):
    type: Literal["screenshot"]
    locator: Locator | None = None


class AskUserStep(_Step):
    type: Literal["ask_user"]
    kind: Literal["captcha", "otp", "confirm", "param"]
    prompt: LocalizedText
    screenshot_locator: Locator | None = None
    fill_locator: Locator | None = None
    param: str | None = None  # for kind=param: context variable to store the answer in
    wait_minutes: float | None = Field(default=None, gt=0, le=30)


class IfExistsStep(_Step):
    type: Literal["if_exists"]
    locator: Locator
    then: list["Step"] = Field(default_factory=list)
    else_: list["Step"] = Field(default_factory=list, alias="else")
    timeout_ms: int = Field(default=2000, ge=0, le=120000)


class AssertStep(_Step):
    type: Literal["assert"]
    locator: Locator
    text_contains: str | None = None
    message: LocalizedText | None = None


class NarrateStep(_Strict):
    type: Literal["narrate"]
    en: str
    hi: str


class FailStep(_Strict):
    type: Literal["fail"]
    message: LocalizedText


Step = Annotated[
    GotoStep
    | FillStep
    | ClickStep
    | SelectStep
    | WaitForStep
    | ExtractStep
    | ScreenshotStep
    | AskUserStep
    | IfExistsStep
    | AssertStep
    | NarrateStep
    | FailStep
    | PressStep
    | PauseStep,
    Field(discriminator="type"),
]
IfExistsStep.model_rebuild()


# ---- params & flow -------------------------------------------------------


class ParamOption(_Strict):
    value: str
    label: LocalizedText
    synonyms: list[str] = Field(default_factory=list)


class FlowParam(_Strict):
    name: str = Field(pattern=r"^[a-z_][a-z0-9_]*$")
    type: Literal["string", "int", "date", "enum"] = "string"
    regex: str | None = None
    options: list[ParamOption] | None = None  # for type=enum
    prompt: LocalizedText
    example: str | None = None
    required: bool = True
    default: str | None = None
    sensitive: bool = False  # masked in task history and logs


class Viewport(_Strict):
    width: int = Field(ge=320, le=1920)
    height: int = Field(ge=480, le=1400)


class FlowDefinition(_Strict):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    version: int = Field(ge=1)
    title: LocalizedText
    description: LocalizedText
    site: str  # live base URL
    mock_path: str  # path under MOCK_SITES_URL used in DEMO_MODE
    params: list[FlowParam] = Field(default_factory=list)
    steps: list[Step]
    result_template: LocalizedText
    # Plain-language question asked before running, e.g. "You want the status of PNR {{pnr}}?"
    confirm_template: LocalizedText | None = None
    requires: list[Literal["captcha", "otp", "confirm"]] = Field(default_factory=list)
    verified_at: datetime | None = None
    enabled: bool = True
    est_minutes_saved: float = 5.0
    keywords: list[str] = Field(default_factory=list)  # hints for the rules intent parser
    examples: list[str] = Field(default_factory=list)  # sample utterances (also for LLM prompts)
    # Optional natural-language goal for goal-based engines (TinyFish). Ignored by Playwright.
    goal: str | None = None
    viewport: Viewport | None = None  # default is a phone-sized viewport
    notes: str | None = None  # for maintainers: verification status, known quirks, TODOs

    def param(self, name: str) -> FlowParam | None:
        return next((p for p in self.params if p.name == name), None)

    def public(self, lang: str | None = None) -> dict[str, Any]:
        """Shape returned by GET /v1/flows (no steps)."""
        return {
            "id": self.id,
            "version": self.version,
            "title": self.title.model_dump(),
            "description": self.description.model_dump(),
            "requires": self.requires,
            "verified": self.verified_at is not None,
            "params": [
                {
                    "name": p.name,
                    "type": p.type,
                    "regex": p.regex,
                    "prompt": p.prompt.model_dump(),
                    "example": p.example,
                    "required": p.required,
                    "sensitive": p.sensitive,
                    "options": [
                        {"value": o.value, "label": o.label.model_dump()} for o in p.options
                    ]
                    if p.options
                    else None,
                }
                for p in self.params
            ],
            "examples": self.examples,
        }
