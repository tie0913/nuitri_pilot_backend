import json
from pathlib import Path

from src.ai.service import get_suggestions
from src.ai.client import AIClient
from src.ai.validators import validate_basic_schema, validate_content_rules


class FakeAIClient(AIClient):
    def __init__(self, response_text: str):
        self._resp = response_text

    def ask(self, prompt: str) -> str:
        return self._resp


def _load_cases(raw):
    """
    Supports these formats:
      1) [ {case}, {case} ]
      2) { "cases": [ {case}, ... ] }
      3) { "id1": {case}, "id2": {case} }  (dict-of-dicts)
    Returns: list[dict]
    """
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]

    if isinstance(raw, dict):
        if isinstance(raw.get("cases"), list):
            return [x for x in raw["cases"] if isinstance(x, dict)]

        vals = list(raw.values())
        if vals and isinstance(vals[0], dict):
            return [x for x in vals if isinstance(x, dict)]

    return []


def test_golden_cases_mocked_schema_and_rules():
    raw = json.loads(Path("tests/ai_eval/golden_cases.json").read_text(encoding="utf-8"))
    cases = _load_cases(raw)
    assert cases, "golden_cases.json parsed to empty case list (unexpected format)"

    # Deterministic mocked response you control
    fake_json = json.dumps(
        {"recommendations": ["Increase protein and fiber intake."], "warnings": ["Watch added sugar."]}
    )
    fake = FakeAIClient(fake_json)

    for idx, c in enumerate(cases, start=1):
        cid = str(c.get("id") or c.get("case_id") or c.get("name") or f"case_{idx:03d}").strip()

        res = get_suggestions(c.get("user_profile", {}), c.get("goal", ""), client=fake)
        assert res.success is True

        errors = []
        errors += validate_basic_schema(res.data, max_recs=c.get("max_recommendations", 12))
        errors += validate_content_rules(
            res.data,
            must_include_any=c.get("must_include_any"),
            must_not_include_any=c.get("must_not_include_any"),
        )

        assert errors == [], f"Case {cid} failed: {errors}"