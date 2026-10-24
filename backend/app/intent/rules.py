"""Offline keyword/regex intent parser. Always available, needs no API key or network.

Handles Hindi (Devanagari), English and Hinglish (romanised Hindi).
"""

import re

from app.intent.base import IntentProvider, RawIntent
from app.models.flow import FlowDefinition, FlowParam

_DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")

_HINDI_NUMBER_WORDS = {
    "ek": 1, "do": 2, "teen": 3, "char": 4, "paanch": 5, "das": 10, "bees": 20, "tees": 30,
    "chalis": 40, "pachas": 50, "saath": 60, "sattar": 70, "assi": 80, "nabbe": 90,
    "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पांच": 5, "पाँच": 5, "दस": 10, "बीस": 20,
    "तीस": 30, "चालीस": 40, "पचास": 50, "साठ": 60, "सत्तर": 70, "अस्सी": 80, "नब्बे": 90,
}  # fmt: skip

_AGE = re.compile(
    r"(?:age|umar|umra|umr|उम्र|आयु|उमर)\D{0,12}?(\d{1,3})"
    r"|(\d{1,3})\s*(?:years?|yrs?|y/o|saal|sal|वर्ष|साल|बरस)",
    re.I,
)
_INCOME = re.compile(
    r"(?:₹|rs\.?|rupees?|रुपये|रुपए|income|aamdani|amdani|kamai|आमदनी|आय|कमाई|salary|तनख्वाह)?\s*"
    r"(\d+(?:[.,]\d+)*)\s*(lakh|lac|lakhs|लाख|thousand|hazaar|hazar|हज़ार|हजार|k|crore|करोड़)?",
    re.I,
)
_INCOME_HINT = re.compile(
    r"income|aamdani|amdani|kamai|आमदनी|आय|कमाई|salary|तनख्वाह|₹|rs\.?|rupees?|रुपये|रुपए|lakh|लाख|hazaar|हज़ार|हजार",
    re.I,
)
_MULTIPLIER = {
    "lakh": 100000, "lac": 100000, "lakhs": 100000, "लाख": 100000,
    "thousand": 1000, "hazaar": 1000, "hazar": 1000, "हज़ार": 1000, "हजार": 1000, "k": 1000,
    "crore": 10000000, "करोड़": 10000000,
}  # fmt: skip
_YESTERDAY = re.compile(r"\b(yesterday|kal|kal\s+wali|parso)\b|कल|परसों", re.I)
_TODAY = re.compile(r"\b(today|aaj)\b|आज", re.I)


def normalize(text: str) -> str:
    text = text.translate(_DEVANAGARI_DIGITS)
    # "45 12 34 56 78" spoken in groups -> join long digit runs
    text = re.sub(r"(?<=\d)[\s-](?=\d)", "", text) if re.search(r"\d[\s-]\d", text) else text
    return " ".join(text.split())


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\wऀ-ॿ]+", text.lower()))


def _contains(text_lower: str, tokens: set[str], phrase: str) -> bool:
    phrase = phrase.lower()
    if " " in phrase or not phrase.isascii():
        return phrase in text_lower
    return phrase in tokens


def extract_enum(param: FlowParam, text: str) -> str | None:
    lower = text.lower()
    tokens = _tokens(text)
    best: tuple[int, str] | None = None
    for opt in param.options or []:
        for cand in [opt.value.replace("_", " "), opt.label.en, opt.label.hi, *opt.synonyms]:
            if cand and _contains(lower, tokens, cand):
                if best is None or len(cand) > best[0]:  # prefer the longest match
                    best = (len(cand), opt.value)
    return best[1] if best else None


def extract_income(text: str) -> int | None:
    if not _INCOME_HINT.search(text):
        return None
    best = None
    for m in _INCOME.finditer(text):
        raw, unit = m.group(1), (m.group(2) or "").lower()
        try:
            number = float(raw.replace(",", ""))
        except ValueError:
            continue
        value = number * _MULTIPLIER.get(unit, 1)
        if unit or value >= 1000:
            best = int(value)
    return best


def extract_age(text: str) -> int | None:
    m = _AGE.search(text)
    if m:
        return int(m.group(1) or m.group(2))
    lower = text.lower()
    for word, value in _HINDI_NUMBER_WORDS.items():
        if re.search(rf"(?<![\wऀ-ॿ]){re.escape(word)}\s*(saal|sal|साल|वर्ष)", lower):
            return value
    return None


def extract_param(param: FlowParam, text: str, answer: bool = False) -> str | None:
    """Pull one parameter out of free text.

    `answer=True` means the text is a reply to a question about this very parameter
    ("How old are you?" -> "65"), so any plausible number is accepted.
    """
    text = normalize(text)
    if param.type == "enum":
        return extract_enum(param, text)
    if param.type == "date":
        if _YESTERDAY.search(text):
            return "yesterday"
        if _TODAY.search(text):
            return "today"
        m = re.search(r"\d{1,2}[-/.]\d{1,2}[-/.]\d{4}|\d{4}-\d{2}-\d{2}", text)
        return m.group(0) if m else None
    if param.name == "age":
        age = extract_age(text)
        if age is None and answer:
            m = re.search(r"(?<![\d.])(\d{1,3})(?![\d.])", text)
            age = int(m.group(1)) if m else None
        return str(age) if age is not None else None
    if param.name == "income":
        income = extract_income(text)
        if income is None and answer:
            m = re.search(r"\d[\d,]*", text)
            income = int(m.group(0).replace(",", "")) if m else None
        return str(income) if income is not None else None
    if param.regex:
        # find a token that satisfies the param's own regex, e.g. ^\d{10}$ or ^\d{5}$
        body = param.regex.strip("^$")
        m = re.search(rf"(?<!\d){body}(?!\d)", text)
        return m.group(0) if m else None
    return text.strip() or None


class RulesProvider(IntentProvider):
    name = "rules"

    @staticmethod
    def _keyword_score(flow: FlowDefinition, text: str) -> float:
        lower = text.lower()
        tokens = _tokens(text)
        return float(sum(_contains(lower, tokens, kw) for kw in flow.keywords))

    @staticmethod
    def _shape_score(flow: FlowDefinition, text: str) -> float:
        # a PNR-shaped / train-number-shaped number is a strong signal
        return sum(
            1.5 for p in flow.params if p.regex and p.type == "string" and extract_param(p, text)
        )

    async def parse(self, text: str, lang: str, flows: list[FlowDefinition]) -> RawIntent:
        text = normalize(text)
        keyword_scores = {f.id: self._keyword_score(f, text) for f in flows}
        any_keywords = any(keyword_scores.values())

        def score(flow: FlowDefinition) -> float:
            kw = keyword_scores[flow.id]
            # A bare number only counts for flows the words point at — unless there are no
            # words to go on at all ("4512345678" on its own is still a PNR).
            if kw or not any_keywords:
                return kw + self._shape_score(flow, text)
            return 0.0

        scored = sorted(((score(f), f) for f in flows), key=lambda x: -x[0])
        if not scored or scored[0][0] < 1.0:
            return RawIntent(flow_id=None, params={}, confidence=0.0)
        best_score, flow = scored[0]
        runner_up = scored[1][0] if len(scored) > 1 else 0.0
        params: dict[str, str | int | float | None] = {}
        for p in flow.params:
            value = extract_param(p, text)
            if value is not None:
                params[p.name] = value
        margin = best_score - runner_up
        confidence = min(0.95, 0.45 + 0.15 * best_score + 0.1 * margin)
        return RawIntent(flow_id=flow.id, params=params, confidence=round(confidence, 2))
