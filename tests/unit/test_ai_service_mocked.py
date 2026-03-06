from src.ai.service import build_prompt, get_suggestions
from src.ai.client import AIClient
import src.ai.service as ai_service


class FakeAIClient(AIClient):
    def __init__(self, response_text: str):
        self._resp = response_text

    def ask(self, prompt: str) -> str:
        # You can assert prompt content here too if you want
        return self._resp


class SequenceFakeAIClient(AIClient):
    def __init__(self, responses: list[str]):
        self._responses = list(responses)
        self.calls = 0

    def ask(self, prompt: str) -> str:
        self.calls += 1
        if self._responses:
            return self._responses.pop(0)
        return "not json"


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


def test_ai_service_repairs_once_after_invalid_first_output():
    fake = SequenceFakeAIClient(
        [
            "not json",
            '{"recommendations":["A","B","C","D","E"],"warnings":["W"]}',
        ]
    )

    res = get_suggestions({"age": 23}, "fat loss", client=fake)
    assert res.success is True
    assert res.data is not None
    assert len(res.data["recommendations"]) == 5
    assert fake.calls == 2


def test_ai_service_routes_base64_profile_to_image_agent(monkeypatch):
    class DummyAgent:
        async def get(self, base64_img, chronics, allergies):
            assert isinstance(base64_img, str) and base64_img
            assert chronics == ["pcos"]
            assert allergies == ["gluten"]
            return {
                "code": 0,
                "message": "",
                "mark": 77,
                "level": 1,
                "feedback": "Looks suitable in moderation.",
                "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
                "detected_ingredients": ["tomato", "olive oil"],
            }

    monkeypatch.setattr(ai_service, "_get_agent_for_image_pipeline", lambda: DummyAgent())

    res = get_suggestions(
        {"base64_img": "abc123", "chronics": ["pcos"], "allergies": ["gluten"]},
        "analyze meal",
        client=None,
    )

    assert res.success is True
    assert isinstance(res.data, dict)
    assert res.data["mark"] == 77
