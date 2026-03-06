from src.ai.service import build_prompt, get_suggestions
from src.ai.client import AIClient


class FakeAIClient(AIClient):
    def __init__(self, response_text: str):
        self._resp = response_text

    def ask(self, prompt: str) -> str:
        # You can assert prompt content here too if you want
        return self._resp


def test_build_prompt_is_deterministic():
    p = build_prompt({"age": 23, "diet": "veg"}, "fat loss")
    assert "Return ONLY valid JSON" in p
    assert "\"diet\": \"veg\"" in p
    assert "Goal: fat loss" in p


def test_ai_service_parses_valid_json():
    fake = FakeAIClient('{"recommendations":["A"],"warnings":["W"]}')
    res = get_suggestions({"age": 23}, "fat loss", client=fake)
    assert res.success is True
    assert res.data["recommendations"] == ["A"]
    assert res.data["warnings"] == ["W"]


def test_ai_service_rejects_non_json():
    fake = FakeAIClient("not json")
    res = get_suggestions({"age": 23}, "fat loss", client=fake)
    assert res.success is False
    assert res.data is None
    assert res.error is not None