from src.suggestion.agent import OpenAIAgent


def _agent_no_init() -> OpenAIAgent:
    return OpenAIAgent.__new__(OpenAIAgent)


def test_non_food_signal_detected_from_feedback_phrase():
    agent = _agent_no_init()
    assert agent._is_non_food_signal(
        "The image does not contain any food items or labels. It appears to be a scenic photo.",
        [],
    ) is True


def test_non_food_signal_not_triggered_when_detected_ingredients_exist():
    agent = _agent_no_init()
    assert agent._is_non_food_signal(
        "This is a scenic photo.",
        ["tomato", "cheese"],
    ) is False


def test_best_effort_response_demotes_non_food_to_code1():
    agent = _agent_no_init()
    out = agent._code0_food_photo_best_effort_response(
        chronics=[],
        allergies=[],
        seed={
            "code": 0,
            "mark": 70,
            "level": 1,
            "feedback": "This image appears to be a scenic landscape and has no food items or labels.",
            "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
            "detected_ingredients": [],
        },
    )
    assert int(out.get("code", 0)) == 1
    assert int(out.get("mark", 1)) == 0
