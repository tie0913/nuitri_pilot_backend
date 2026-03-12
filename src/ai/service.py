import json
import asyncio
import threading
from dataclasses import dataclass
from typing import Any, Dict, List

from src.ai.client import AIClient
from src.ai.validators import validate_basic_schema, validate_content_rules


@dataclass
class AISuggestionResult:
    success: bool
    data: Dict[str, Any] | None
    error: str | None


def build_prompt(user_profile: dict, goal: str) -> str:
    # Old schema is kept for backwards compatibility with existing tests.
    return (
        "You are NutriPilot AI.\n"
        "Return ONLY valid JSON. No markdown. No code fences.\n"
        'Schema: {"recommendations": [string], "warnings": [string]}\n'
        "Rules:\n"
        "- recommendations: 5 to 10 short bullet-style strings (max 14 words each)\n"
        "- warnings: 0 to 5 short strings\n\n"
        "- Avoid medical-claim words like cure, detox, miracle, guarantee.\n"
        "Output example:\n"
        '{"recommendations":["Choose grilled protein + vegetables","Swap sugary drinks for water","Add fiber-rich whole grains","Keep portions balanced","Include healthy fats in moderation"],"warnings":["High added sugar may affect blood glucose"]}\n\n'
        f"UserProfile: {json.dumps(user_profile, ensure_ascii=False)}\n"
        f"Goal: {goal}\n"
    )


def build_repair_prompt(
    user_profile: dict,
    goal: str,
    previous_output: str,
    validation_errors: List[str],
) -> str:
    clipped_output = (previous_output or "").strip()
    if len(clipped_output) > 1800:
        clipped_output = clipped_output[:1800] + "...(truncated)"

    errs = "\n".join(f"- {e}" for e in validation_errors[:12]) or "- unknown validation error"

    return (
        "You previously returned invalid output.\n"
        "Return ONLY valid JSON. No markdown. No code fences.\n"
        'Required schema: {"recommendations": [string], "warnings": [string]}\n'
        "Hard constraints:\n"
        "- recommendations length: 5 to 10\n"
        "- warnings length: 0 to 5\n"
        "- recommendations and warnings must contain plain strings only\n"
        "- Avoid medical claims (cure/detox/miracle/guarantee)\n\n"
        f"Validation errors to fix:\n{errs}\n\n"
        f"Previous invalid output:\n{clipped_output}\n\n"
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


def _run_coro_sync(coro):
    """
    Run async code safely from sync contexts.
    If a loop is already running (rare for this module), run in a helper thread.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    holder: Dict[str, Any] = {"result": None, "error": None}

    def _runner():
        try:
            holder["result"] = asyncio.run(coro)
        except Exception as exc:
            holder["error"] = exc

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join()
    if holder["error"] is not None:
        raise holder["error"]
    return holder["result"]


def _get_agent_for_image_pipeline():
    from src.suggestion.agent import get_agent

    return get_agent()


def _route_image_profile(user_profile: dict) -> AISuggestionResult | None:
    if not isinstance(user_profile, dict):
        return None

    base64_img = user_profile.get("base64_img")
    if not isinstance(base64_img, str) or not base64_img.strip():
        return None

    chronics = user_profile.get("chronics") or []
    allergies = user_profile.get("allergies") or []

    if not isinstance(chronics, list):
        chronics = []
    if not isinstance(allergies, list):
        allergies = []

    chronics = [str(x).strip() for x in chronics if str(x).strip()]
    allergies = [str(x).strip() for x in allergies if str(x).strip()]

    try:
        agent = _get_agent_for_image_pipeline()
        data = _run_coro_sync(agent.get(base64_img, chronics, allergies))
        if not isinstance(data, dict):
            raise ValueError("image pipeline returned invalid response type")
        return AISuggestionResult(success=True, data=data, error=None)
    except Exception as exc:
        return AISuggestionResult(success=False, data=None, error=str(exc))


def _validate_output(obj: Dict[str, Any], strict_quality: bool) -> List[str]:
    errors: List[str] = []
    errors += validate_basic_schema(obj, max_recs=12)
    errors += validate_content_rules(obj)

    if strict_quality:
        recs = obj.get("recommendations", [])
        warns = obj.get("warnings", [])
        if isinstance(recs, list):
            if len(recs) < 5:
                errors.append("recommendations must have at least 5 items")
            if len(recs) > 10:
                errors.append("recommendations must have at most 10 items")
        if isinstance(warns, list) and len(warns) > 5:
            errors.append("warnings must have at most 5 items")

    return errors


def _parse_and_validate(raw_text: str, strict_quality: bool) -> tuple[Dict[str, Any] | None, List[str]]:
    try:
        parsed = parse_ai_json(raw_text)
    except Exception as exc:
        return None, [f"invalid json/schema: {exc}"]

    errors = _validate_output(parsed, strict_quality=strict_quality)
    return parsed, errors


def get_suggestions(user_profile: dict, goal: str, client: AIClient | None = None) -> AISuggestionResult:
    image_routed = _route_image_profile(user_profile)
    if image_routed is not None:
        return image_routed

    default_client = client is None
    client = client or AIClient()

    try:
        prompt = build_prompt(user_profile, goal)
        raw = client.ask(prompt)
        parsed, errors = _parse_and_validate(raw, strict_quality=default_client)

        # One auto-repair attempt: ask model to fix invalid format/content deterministically.
        if errors:
            repair_prompt = build_repair_prompt(user_profile, goal, raw, errors)
            repaired_raw = client.ask(repair_prompt)
            parsed, errors = _parse_and_validate(repaired_raw, strict_quality=default_client)

        if errors or parsed is None:
            detail = "; ".join(errors[:5]) if errors else "unknown validation error"
            raise ValueError(f"AI output failed validation after repair attempt: {detail}")

        return AISuggestionResult(success=True, data=parsed, error=None)
    except Exception as e:
        return AISuggestionResult(success=False, data=None, error=str(e))
