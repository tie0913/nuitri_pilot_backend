import os
import pytest

from src.ai.service import get_suggestions

pytestmark = pytest.mark.ai_live


@pytest.mark.skipif(os.getenv("RUN_AI_LIVE") != "1", reason="Set RUN_AI_LIVE=1 to run live AI tests")
def test_live_ai_returns_valid_schema():
    # Requires OPENAI_API_KEY to be set in environment
    res = get_suggestions({"age": 23, "diet": "veg"}, "fat loss")
    assert res.success is True
    assert "recommendations" in res.data
    assert "warnings" in res.data