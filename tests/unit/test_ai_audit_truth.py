from src.ai.audit import validate_ai_result


def _base_result(feedback: str) -> dict:
    return {
        "code": 0,
        "message": "",
        "mark": 75,
        "level": 2,
        "feedback": feedback,
        "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
        "detected_ingredients": ["milk powder", "sugar"],
    }


def test_audit_flags_feedback_without_evidence_terms():
    result = _base_result(
        "This appears healthy and balanced for your goals and can be used in moderation "
        "with portion control and hydration throughout the day."
    )
    issues = validate_ai_result(
        result=result,
        user_allergies=[],
        detected_ingredients=["milk powder", "sugar"],
        nutrition=None,
    )
    assert any(i.code == "FACT" and "grounded" in i.message for i in issues)


def test_audit_flags_unsupported_allergen_presence_claim():
    result = _base_result(
        "The label contains peanut and should be avoided for allergy risk. "
        "Oats and salt appear simple otherwise, but peanut content makes this unsafe today."
    )
    issues = validate_ai_result(
        result=result,
        user_allergies=[],
        detected_ingredients=["oats", "salt"],
        nutrition=None,
    )
    assert any(i.code == "FACT" and "unsupported allergen" in i.message for i in issues)


def test_audit_allows_grounded_feedback():
    result = _base_result(
        "The ingredients list includes milk powder and sugar, so this may raise blood sugar "
        "if portions are large. Keep serving size small and pair with higher-fiber foods."
    )
    issues = validate_ai_result(
        result=result,
        user_allergies=[],
        detected_ingredients=["milk powder", "sugar"],
        nutrition=None,
    )
    assert not any(i.code == "FACT" for i in issues)


def test_audit_does_not_flag_negated_allergen_presence():
    result = {
        "code": 0,
        "message": "",
        "mark": 70,
        "level": 2,
        "feedback": (
            "The product contains oats and honey. Since you have a soy allergy, "
            "it does not list soy as an ingredient, but check cross-contamination notes."
        ),
        "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
        "detected_ingredients": ["oats", "honey"],
    }
    issues = validate_ai_result(
        result=result,
        user_allergies=["soy"],
        detected_ingredients=["oats", "honey"],
        nutrition=None,
    )
    assert not any(i.code == "FACT" and "unsupported allergen" in i.message for i in issues)
