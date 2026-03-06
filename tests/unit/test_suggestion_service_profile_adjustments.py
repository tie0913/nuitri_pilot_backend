from src.suggestion.service import SuggestionService


def test_profile_adjustment_caps_mark_for_allergy_hits():
    svc = SuggestionService(db=None)
    suggestion = {
        "code": 0,
        "message": "",
        "mark": 78,
        "level": 1,
        "feedback": "This pizza has pepperoni and cheese.",
        "recommendation": ["Veggie pizza", "Salad bowl", "Grilled tofu wrap"],
        "detected_ingredients": ["pizza crust", "pepperoni", "cheese"],
    }

    out = svc._apply_profile_safety_adjustments(
        suggestion=suggestion,
        chronics_names=["overweight"],
        allergies_names=["pork", "beef"],
    )

    assert out["mark"] <= 15
    assert out["level"] == 3
    assert "avoid this option due to your allergy profile" in str(out.get("feedback", "")).lower()


def test_profile_adjustment_caps_mark_for_overweight_risk_terms():
    svc = SuggestionService(db=None)
    suggestion = {
        "code": 0,
        "message": "",
        "mark": 72,
        "level": 1,
        "feedback": "Burger with cheese and fries.",
        "recommendation": ["Lean protein bowl", "Vegetable soup", "Grilled fish with salad"],
        "detected_ingredients": ["burger bun", "beef patty", "cheese", "fries"],
    }

    out = svc._apply_profile_safety_adjustments(
        suggestion=suggestion,
        chronics_names=["overweight"],
        allergies_names=[],
    )

    assert out["mark"] <= 35
    assert int(out["level"]) >= 2
    assert "higher-calorie choice" in str(out.get("feedback", "")).lower()


def test_profile_adjustment_leaves_safe_case_unchanged():
    svc = SuggestionService(db=None)
    suggestion = {
        "code": 0,
        "message": "",
        "mark": 70,
        "level": 1,
        "feedback": "This bowl has quinoa, spinach, and chickpeas.",
        "recommendation": ["Lentil bowl", "Greek salad", "Vegetable soup"],
        "detected_ingredients": ["quinoa", "spinach", "chickpeas"],
    }

    out = svc._apply_profile_safety_adjustments(
        suggestion=suggestion,
        chronics_names=["thyroid"],
        allergies_names=["milk"],
    )

    assert out["mark"] == 70
    assert out["level"] == 1


def test_profile_adjustment_demotes_non_food_feedback_to_code1():
    svc = SuggestionService(db=None)
    suggestion = {
        "code": 0,
        "message": "",
        "mark": 50,
        "level": 2,
        "feedback": "The image provided does not contain any food items or labels. It appears to be a scenic photo.",
        "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
        "detected_ingredients": [],
    }

    out = svc._apply_profile_safety_adjustments(
        suggestion=suggestion,
        chronics_names=[],
        allergies_names=[],
    )

    assert int(out["code"]) == 1
    assert int(out["mark"]) == 0
    assert int(out["level"]) == 3
