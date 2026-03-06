import hashlib
from typing import Any, Dict, List


def _hash_text(s: str) -> str:
    h = hashlib.sha256(s.encode("utf-8")).hexdigest()
    return f"sha256:{h}"


def score_output(out: Dict[str, Any]) -> Dict[str, Any]:
    """
    Keep this deterministic and cheap.
    We do NOT judge if the advice is 'good'—only if it stays within guardrails.
    """
    feedback = str(out.get("feedback", "") or "")
    recs = out.get("recommendation") or []
    ing = out.get("detected_ingredients") or []

    return {
        "mark": out.get("mark", 0),
        "level": out.get("level", 2),
        "feedback_hash": _hash_text(feedback.strip().lower()),
        "recommendation": recs[:4],
        "detected_ingredients": ing[:30],
    }


def contains_any(text: str, needles: List[str]) -> bool:
    t = text.lower()
    return any(n.lower() in t for n in needles)


def contains_none(text: str, needles: List[str]) -> bool:
    t = text.lower()
    return all(n.lower() not in t for n in needles)