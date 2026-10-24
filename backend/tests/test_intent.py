import json
from datetime import timedelta

import httpx
import pytest

from app.core.config import Settings
from app.core.timeutil import local_today
from app.flows.registry import FlowRegistry
from app.intent.base import ProviderError
from app.intent.llm import GeminiProvider, GroqProvider, OllamaProvider, parse_strict
from app.intent.rules import RulesProvider, normalize
from app.intent.service import IntentService, build_providers

TODAY = local_today().isoformat()
YESTERDAY = (local_today() - timedelta(days=1)).isoformat()


@pytest.fixture(scope="module")
def registry():
    return FlowRegistry.load()


@pytest.fixture(scope="module")
def rules_service(registry):
    return IntentService(Settings(intent_provider="rules"), registry)


# (utterance, expected flow, expected params subset, expected missing)
UTTERANCES = [
    ("check my PNR 4512345678", "pnr_status", {"pnr": "4512345678"}, []),
    ("मेरा PNR 4512345678 है, स्थिति बताओ", "pnr_status", {"pnr": "4512345678"}, []),
    ("mera ticket confirm hua kya? PNR ४५१२३४५६७८", "pnr_status", {"pnr": "4512345678"}, []),
    ("PNR status batao 451 234 5678", "pnr_status", {"pnr": "4512345678"}, []),
    ("is my ticket confirmed", "pnr_status", {}, ["pnr"]),
    ("मेरी ट्रेन 12301 कहाँ है?", "train_running_status", {"train_no": "12301", "date": TODAY}, []),
    ("Where is train 12951 right now", "train_running_status", {"train_no": "12951"}, []),
    ("12002 kitni late hai", "train_running_status", {"train_no": "12002"}, []),
    (
        "train 12627 running status yesterday",
        "train_running_status",
        {"train_no": "12627", "date": YESTERDAY},
        [],
    ),
    (
        "kal wali 12301 gaadi kahan hai",
        "train_running_status",
        {"train_no": "12301", "date": YESTERDAY},
        [],
    ),
    ("मेरी ट्रेन कहाँ है?", "train_running_status", {}, ["train_no"]),
    (
        "Which government schemes can I get? I am a 67 year old woman from Delhi, income 80000",
        "scheme_finder",
        {"age": "67", "gender": "female", "state": "delhi", "income": "80000"},
        [],
    ),
    (
        "mujhe pension yojana batao, meri umar 65 saal hai, main bihar se hoon",
        "scheme_finder",
        {"age": "65", "state": "bihar"},
        ["gender"],  # income is optional: live myScheme search cannot filter by it
    ),
    (
        "मैं 70 साल की महिला हूँ, उत्तर प्रदेश में रहती हूँ, आमदनी 1 लाख, कोई योजना बताओ",
        "scheme_finder",
        {"age": "70", "gender": "female", "state": "uttar_pradesh", "income": "100000"},
        [],
    ),
    (
        "schemes for a 30 year old man in Tamil Nadu with 2.5 lakh income",
        "scheme_finder",
        {"age": "30", "gender": "male", "state": "tamil_nadu", "income": "250000"},
        [],
    ),
    ("sarkari yojana for farmers in MP", "scheme_finder", {"state": "madhya_pradesh"}, None),
    ("what's the weather today", None, {}, []),
    ("गाना बजाओ", None, {}, []),
    ("book a cab to the airport", None, {}, []),
]


@pytest.mark.parametrize(("text", "flow_id", "params", "missing"), UTTERANCES)
async def test_rules_utterances(rules_service, text, flow_id, params, missing):
    result = await rules_service.parse(text, "hi")
    assert result["flow_id"] == flow_id, result
    for k, v in params.items():
        assert result["params"].get(k) == v, (k, result["params"])
    if missing is not None:
        assert result["missing_params"] == missing
    assert result["provider"] == "rules"


def test_at_least_15_utterances():
    assert len(UTTERANCES) >= 15


def test_normalize_devanagari_digits_and_spacing():
    assert normalize("PNR ४५१ २३४ ५६७८") == "PNR 4512345678"


async def test_confirmation_in_both_languages(rules_service):
    result = await rules_service.parse("check my PNR 4512345678", "en")
    assert result["confirmation"]["en"] == "You want to check the status of PNR 4512345678?"
    assert result["confirmation"]["hi"] == "आप PNR 4512345678 की स्थिति जानना चाहते हैं?"


async def test_scheme_confirmation_uses_labels(rules_service):
    result = await rules_service.parse(
        "schemes for a 30 year old man in Tamil Nadu with 2.5 lakh income", "en"
    )
    assert "Male" in result["confirmation"]["en"] and "₹2,50,000" in result["confirmation"]["en"]
    assert "पुरुष" in result["confirmation"]["hi"] and "तमिलनाडु" in result["confirmation"]["hi"]


async def test_missing_param_gives_next_prompt(rules_service):
    result = await rules_service.parse("is my ticket confirmed", "hi")
    assert result["confirmation"] is None
    assert "PNR" in result["next_prompt"]["hi"]


async def test_no_match_lists_supported_tasks(rules_service):
    result = await rules_service.parse("order pizza", "en")
    assert result["flow_id"] is None
    assert "can't do that yet" in result["confirmation"]["en"]
    assert {s["id"] for s in result["supported"]} == {
        "scheme_finder", "train_running_status", "pnr_status"
    }  # fmt: skip


async def test_follow_up_answer_fills_expected_param(rules_service):
    first = await rules_service.parse("mujhe yojana batao, main bihar se hoon", "hi")
    assert first["missing_params"][0] == "age"
    second = await rules_service.parse(
        "पैंसठ नहीं, 65", "hi", flow_id="scheme_finder", known=first["params"], expecting="age"
    )
    assert second["params"]["age"] == "65" and second["params"]["state"] == "bihar"
    third = await rules_service.parse(
        "mahila", "hi", flow_id="scheme_finder", known=second["params"], expecting="gender"
    )
    assert third["params"]["gender"] == "female"
    assert third["missing_params"] == [] and third["confirmation"]
    assert "आमदनी" not in third["confirmation"]["hi"]  # optional income left out
    fourth = await rules_service.parse(
        "डेढ़ नहीं, 150000", "hi", flow_id="scheme_finder", known=third["params"],
        expecting="income",
    )  # fmt: skip
    assert fourth["params"]["income"] == "150000"
    assert "₹1,50,000" in fourth["confirmation"]["en"]


async def test_invalid_values_reported(rules_service):
    result = await rules_service.parse(
        "1 hazaar saal ka aadmi yojana", "en", flow_id="scheme_finder", known={"age": "999"}
    )
    assert "age" not in result["params"]


# ---- LLM providers (HTTP mocked) --------------------------------------------


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


GOOD = {"flow_id": "pnr_status", "params": {"pnr": "4512345678"}, "confidence": 0.93}


async def test_gemini_provider(registry):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key")
        body = json.loads(request.content)
        assert body["generationConfig"]["responseMimeType"] == "application/json"
        assert "pnr_status" in body["systemInstruction"]["parts"][0]["text"]
        text = json.dumps(GOOD)
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{"text": text}]}}]})

    provider = GeminiProvider("k", "gemini-2.0-flash", client=_client(handler))
    intent = await provider.parse("PNR 4512345678 batao", "hi", registry.all())
    assert intent.flow_id == "pnr_status" and seen["key"] == "k"
    assert "gemini-2.0-flash:generateContent" in seen["url"]


async def test_groq_retry_once_then_succeeds(registry):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        content = "Sure! here you go" if calls["n"] == 1 else json.dumps(GOOD)
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    provider = GroqProvider("k", "m", client=_client(handler))
    service = IntentService(Settings(), registry, providers=[provider, RulesProvider()])
    result = await service.parse("ticket status 4512345678", "en")
    assert calls["n"] == 2 and result["provider"] == "groq"
    assert result["params"] == {"pnr": "4512345678"}


async def test_invalid_twice_falls_back_to_rules(registry):
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        bad = {"flow_id": "pnr_status", "params": {}, "confidence": 7}  # out of range
        return httpx.Response(200, json={"message": {"content": json.dumps(bad)}})

    provider = OllamaProvider("http://ollama:11434", "llama3.2", client=_client(handler))
    service = IntentService(Settings(), registry, providers=[provider, RulesProvider()])
    result = await service.parse("मेरी ट्रेन 12301 कहाँ है?", "hi")
    assert calls["n"] == 2
    assert result["provider"] == "rules" and result["flow_id"] == "train_running_status"


async def test_provider_http_error_falls_back(registry):
    provider = GroqProvider("k", "m", client=_client(lambda r: httpx.Response(429)))
    service = IntentService(Settings(), registry, providers=[provider, RulesProvider()])
    result = await service.parse("check my PNR 4512345678", "en")
    assert result["provider"] == "rules" and result["flow_id"] == "pnr_status"


async def test_llm_null_flow_uses_rules_if_they_match(registry):
    none = {"flow_id": None, "params": {}, "confidence": 0}

    def handler(request):
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(none)}}]})

    service = IntentService(
        Settings(),
        registry,
        providers=[GroqProvider("k", "m", client=_client(handler)), RulesProvider()],
    )
    assert (await service.parse("PNR 4512345678", "en"))["flow_id"] == "pnr_status"
    assert (await service.parse("tell me a joke", "en"))["flow_id"] is None


def test_parse_strict(registry):
    flows = registry.all()
    assert parse_strict("```json\n" + json.dumps(GOOD) + "\n```", flows).flow_id == "pnr_status"
    with pytest.raises(ProviderError):
        parse_strict(json.dumps({**GOOD, "flow_id": "rocket_launch"}), flows)
    with pytest.raises(ProviderError):
        parse_strict(json.dumps({**GOOD, "extra": 1}), flows)
    stripped = parse_strict(json.dumps({**GOOD, "params": {"pnr": "1", "bogus": "x"}}), flows)
    assert stripped.params == {"pnr": "1"}


def test_build_providers():
    def names(**kw):
        return [p.name for p in build_providers(Settings(intent_provider="", **kw))]

    assert names() == ["rules"]
    assert names(gemini_api_key="g", groq_api_key="q") == ["gemini", "rules"]
    assert names(groq_api_key="q") == ["groq", "rules"]
    assert names(ollama_url="http://x") == ["ollama", "rules"]
    assert [
        p.name for p in build_providers(Settings(gemini_api_key="g", intent_provider="rules"))
    ] == ["rules"]


@pytest.mark.mongo
async def test_intent_endpoint(client, auth):
    resp = await client.post(
        "/v1/intent/parse", json={"text": "मेरी ट्रेन 12301 कहाँ है?", "lang": "hi"}, headers=auth
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["flow_id"] == "train_running_status" and body["confirmation"]["hi"]
    assert (await client.post("/v1/intent/parse", json={"text": "x"})).status_code == 401
