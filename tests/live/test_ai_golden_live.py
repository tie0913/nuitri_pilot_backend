import json
import os
from pathlib import Path

import pytest

from src.ai.service import get_suggestions
from src.ai.validators import validate_basic_schema, validate_content_rules


def _load_cases(raw):
    """
    Supports these formats:
      1) [ {case}, {case} ]
      2) { "cases": [ {case}, ... ] }
      3) { "id1": {case}, "id2": {case} }
    """
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        if isinstance(raw.get("cases"), list):
            return raw["cases"]
        vals = list(raw.values())
        if vals and isinstance(vals[0], dict):
            return vals
    return []


@pytest.mark.skipif(os.getenv("RUN_AI_LIVE") != "1", reason="Set RUN_AI_LIVE=1 to run live AI tests")
def test_golden_cases_live_quality_gate():
    raw = json.loads(Path("tests/ai_eval/golden_cases.json").read_text(encoding="utf-8"))
    cases = _load_cases(raw)

    assert cases, "golden_cases.json parsed to empty case list (unexpected format)"

    failures = []

    for idx, c in enumerate(cases, start=1):
        # tolerate missing fields
        user_profile = c.get("user_profile", {})
        goal = c.get("goal", "")

        res = get_suggestions(user_profile, goal)

        if not res.success or not res.data:
            failures.append(f"case#{idx}: AI call failed: {res.error}")
            continue

        # Validators are backwards-compatible now:
        # - accept old schema {"recommendations","warnings"}
        # - accept new schema too
        errors = []
        errors += validate_basic_schema(res.data, max_recs=c.get("max_recommendations", 12))
        errors += validate_content_rules(res.data)

        if errors:
            failures.append(f"case#{idx}: " + "; ".join(errors))

    assert not failures, "Golden live failures:\n" + "\n".join(failures)