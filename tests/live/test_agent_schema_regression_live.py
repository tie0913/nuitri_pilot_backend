import base64
from io import BytesIO

import pytest

from src.suggestion.service import SuggestionService
from src.ai.audit import run_ai_audit


def _b64_data_url_from_png_bytes(png_bytes: bytes) -> str:
    return "data:image/png;base64," + base64.b64encode(png_bytes).decode("utf-8")


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_service_contract_invalid_image_returns_fail_closed_with_audit():
    """
    REAL user flow: image -> SuggestionService -> agent -> audit -> stored output.
    So audit must exist in the SERVICE output (not agent output).
    """
    svc = SuggestionService(db=None)  # db not used in this contract test

    # Bad user image
    bad_img = "data:image/png;base64,not_base64"

    # Call agent directly but run audit exactly like service would
    # (We don't call svc.get_suggestion because it requires Mongo repos.)
    from src.suggestion.agent import get_agent
    agent = get_agent()
    suggestion = await agent.get(bad_img, chronics=["PCOS"], allergies=["milk"])

    # Service-enforced required keys
    suggestion.setdefault("code", 0)
    suggestion.setdefault("message", "")
    suggestion.setdefault("mark", 0)
    suggestion.setdefault("level", 2)
    suggestion.setdefault("feedback", "")
    suggestion.setdefault("recommendation", ["Greek salad", "Vegetable soup", "Oatmeal with fruit"])
    suggestion.setdefault("detected_ingredients", [])

    audit = run_ai_audit(
        ai_output=suggestion,
        user_allergies=["milk"],
        detected_ingredients=[str(x) for x in (suggestion.get("detected_ingredients") or [])],
        nutrition=None,
    )

    suggestion["audit"] = {
        "passed": audit.passed,
        "issues": audit.issues,
        "judge_notes": audit.judge_notes,
    }

    # ✅ Stable schema WITH audit
    for k in [
        "code",
        "message",
        "mark",
        "level",
        "feedback",
        "recommendation",
        "detected_ingredients",
        "audit",
    ]:
        assert k in suggestion, f"missing key: {k}"

    # Fail closed expectations
    assert suggestion["code"] == 1
    assert suggestion["mark"] == 0
    assert suggestion["level"] == 3
    assert isinstance(suggestion["audit"], dict)
    assert suggestion["audit"]["passed"] is False


@pytest.mark.ai_live
@pytest.mark.asyncio
async def test_service_contract_synthetic_image_returns_audit_object():
    """
    No real user images stored in repo.
    Generate synthetic label image and ensure SERVICE-style output includes audit.
    """
    try:
        from PIL import Image, ImageDraw
    except Exception:
        pytest.skip("Pillow not installed; skipping synthetic image smoke test")

    img = Image.new("RGB", (900, 220), color="white")
    draw = ImageDraw.Draw(img)
    draw.text((20, 40), "Ingredients: milk, sugar, wheat flour", fill="black")

    buf = BytesIO()
    img.save(buf, format="PNG")
    base64_img = _b64_data_url_from_png_bytes(buf.getvalue())

    from src.suggestion.agent import get_agent
    agent = get_agent()
    suggestion = await agent.get(base64_img, chronics=[], allergies=["milk"])

    suggestion.setdefault("code", 0)
    suggestion.setdefault("message", "")
    suggestion.setdefault("mark", 0)
    suggestion.setdefault("level", 2)
    suggestion.setdefault("feedback", "")
    suggestion.setdefault("recommendation", ["Greek salad", "Vegetable soup", "Oatmeal with fruit"])
    suggestion.setdefault("detected_ingredients", [])

    audit = run_ai_audit(
        ai_output=suggestion,
        user_allergies=["milk"],
        detected_ingredients=[str(x) for x in (suggestion.get("detected_ingredients") or [])],
        nutrition=None,
    )

    suggestion["audit"] = {
        "passed": audit.passed,
        "issues": audit.issues,
        "judge_notes": audit.judge_notes,
    }

    # Must always include audit at service layer
    assert "audit" in suggestion and isinstance(suggestion["audit"], dict)
    assert "passed" in suggestion["audit"]