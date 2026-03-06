import json
from dataclasses import dataclass
from typing import Any, Dict, List

from src.ai.client import AIClient


@dataclass
class AISuggestionResult:
    success: bool
    data: Dict[str, Any] | None
    error: str | None


def build_prompt(user_profile: dict, goal: str) -> str:
    # Keep prompt deterministic for testing (OLD schema, because tests mock this)
    return (
        "You are NutriPilot AI.\n"
        "Return ONLY valid JSON. No markdown. No code fences.\n"
        'Schema: {"recommendations": [string], "warnings": [string]}\n'
        "Rules:\n"
        "- recommendations: 5 to 10 short bullet-style strings\n"
        "- warnings: 0 to 5 short strings\n\n"
        f"UserProfile: {json.dumps(user_profile, ensure_ascii=False)}\n"
        f"Goal: {goal}\n"
    )


def parse_ai_json(text: str) -> Dict[str, Any]:
    # Strict JSON parsing for OLD schema (tests depend on it)
    obj = json.loads(text)
    if not isinstance(obj, dict):
        raise ValueError("AI output must be a JSON object")
    if "recommendations" not in obj or "warnings" not in obj:
        raise ValueError("Missing required keys")
    if not isinstance(obj["recommendations"], list) or not isinstance(obj["warnings"], list):
        raise ValueError("Invalid schema types")

    # Keep this output EXACTLY as tests expect
    return obj


def get_suggestions(user_profile: dict, goal: str, client: AIClient | None = None) -> AISuggestionResult:
    client = client or AIClient()

    try:
        prompt = build_prompt(user_profile, goal)
        raw = client.ask(prompt)
        parsed = parse_ai_json(raw)
        return AISuggestionResult(success=True, data=parsed, error=None)
    except Exception as e:
        return AISuggestionResult(success=False, data=None, error=str(e))