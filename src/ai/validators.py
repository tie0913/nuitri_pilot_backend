import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


BANNED_PHRASES = ["heal", "cure", "detox", "miracle", "guarantee"]
ALLOWED_LEVELS = {1, 2, 3}


def _min_feedback_words() -> int:
    try:
        return max(8, int(os.getenv("AI_AUDIT_MIN_FEEDBACK_WORDS", "20")))
    except Exception:
        return 20

ALLERGEN_KEYWORDS = {
    "milk": ["milk", "whey", "casein", "lactose", "butter", "cheese", "cream", "yogurt"],
    "dairy": ["milk", "whey", "casein", "lactose", "butter", "cheese", "cream", "yogurt"],
    "egg": ["egg", "eggs", "albumen", "ovalbumin"],
    "peanut": ["peanut", "groundnut"],
    "tree nut": ["almond", "walnut", "cashew", "pistachio", "pecan", "hazelnut", "macadamia"],
    "soy": ["soy", "soya", "soybean"],
    "wheat": ["wheat", "gluten", "flour"],
    "gluten": ["gluten", "wheat", "barley", "rye", "malt"],
    "fish": ["fish", "salmon", "tuna", "cod"],
    "shellfish": ["shrimp", "prawn", "crab", "lobster"],
    "sesame": ["sesame", "tahini"],
}


@dataclass
class ValidationIssue:
    code: str
    message: str


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _word_count(s: str) -> int:
    return len([w for w in str(s).split() if w.strip()])


def _lower_list(xs: List[str]) -> List[str]:
    return [str(x).strip().lower() for x in (xs or []) if str(x).strip()]


def _detect_allergen_hits(user_allergies: List[str], detected_ingredients: List[str]) -> List[str]:
    allergies = _lower_list(user_allergies)
    ingredients_text = " ".join(_lower_list(detected_ingredients))

    hits: List[str] = []

    for allergy in allergies:
        if allergy and allergy in ingredients_text:
            hits.append(allergy)
            continue

        for key, kws in ALLERGEN_KEYWORDS.items():
            if allergy == key:
                for kw in kws:
                    if re.search(rf"\b{re.escape(kw)}\b", ingredients_text):
                        hits.append(allergy)
                        break

    return sorted(list(set(hits)))


# NOTE: tests pass max_recs=... so we accept it + **kwargs for safety.
def validate_basic_schema(obj: Dict[str, Any], max_recs: int = 12, **kwargs) -> List[str]:
    """
    Backwards-compatible validator for tests.

    Accepts BOTH shapes:
    Old: {"recommendations": [...], "warnings": [...]}
    New: {"code","message","mark","level","feedback","recommendation","detected_ingredients", ...}

    Returns: list[str] errors (empty means pass)
    """
    _ = kwargs  # ignore any extra args tests might add later

    errors: List[str] = []
    if not isinstance(obj, dict):
        return ["output must be a dict/json object"]

    # Old schema path
    if "recommendations" in obj and "warnings" in obj:
        if not isinstance(obj["recommendations"], list):
            errors.append("recommendations must be a list")
        else:
            if len(obj["recommendations"]) == 0:
                errors.append("recommendations must be non-empty")
            if len(obj["recommendations"]) > int(max_recs):
                errors.append(f"recommendations must be <= {max_recs}")

        if not isinstance(obj["warnings"], list):
            errors.append("warnings must be a list")

        return errors

    # New schema path
    required = ["code", "message", "mark", "level", "feedback", "recommendation", "detected_ingredients"]
    for k in required:
        if k not in obj:
            errors.append(f"missing key: {k}")
    if errors:
        return errors

    try:
        code = int(obj.get("code"))
        if code not in (0, 1):
            errors.append("code must be 0 or 1")
    except Exception:
        errors.append("code must be an int (0 or 1)")

    if not isinstance(obj.get("message"), str):
        errors.append("message must be a string")

    mark = obj.get("mark")
    if not _is_number(mark):
        errors.append("mark must be a number")
    else:
        if mark < 0 or mark > 100:
            errors.append("mark must be between 0 and 100")

    lvl = obj.get("level")
    if isinstance(lvl, bool) or lvl is None:
        errors.append("level must be an int (1,2,3)")
    else:
        if _is_number(lvl) and not isinstance(lvl, int):
            if float(lvl).is_integer():
                lvl = int(lvl)
            else:
                errors.append("level must be an int (1,2,3)")
                lvl = None
        if lvl is not None and lvl not in ALLOWED_LEVELS:
            errors.append("level must be 1, 2, or 3")

    if not isinstance(obj.get("feedback"), str):
        errors.append("feedback must be a string")

    rec = obj.get("recommendation")
    if not isinstance(rec, list):
        errors.append("recommendation must be a list")
    else:
        rec_clean = [r for r in rec if isinstance(r, str) and r.strip()]
        if len(rec_clean) == 0:
            errors.append("recommendation must be a non-empty list of strings")
        if len(rec) > 4:
            errors.append("recommendation must have at most 4 items")

    di = obj.get("detected_ingredients")
    if not isinstance(di, list):
        errors.append("detected_ingredients must be a list")
    else:
        bad = [x for x in di if not isinstance(x, str)]
        if bad:
            errors.append("detected_ingredients items must be strings")

    return errors


def validate_content_rules(obj: Dict[str, Any], **kwargs) -> List[str]:
    """
    Backwards-compatible content rules for tests.
    """
    _ = kwargs

    errors: List[str] = []
    if not isinstance(obj, dict):
        return ["output must be a dict/json object"]

    # Old schema
    if "recommendations" in obj and "warnings" in obj:
        text = " ".join([str(x) for x in (obj.get("recommendations") or []) + (obj.get("warnings") or [])]).lower()
        for phrase in BANNED_PHRASES:
            if re.search(rf"\b{re.escape(phrase.lower())}\b", text):
                errors.append(f"contains banned phrase: {phrase}")
        return errors

    # New schema
    fb = obj.get("feedback", "")
    if not isinstance(fb, str):
        return ["feedback must be a string"]

    try:
        code = int(obj.get("code", 0))
    except Exception:
        code = 0
    min_words = _min_feedback_words() if code == 0 else 8
    if _word_count(fb) < min_words:
        errors.append(f"feedback must be at least {min_words} words")

    fb_lower = fb.lower()
    for phrase in BANNED_PHRASES:
        if re.search(rf"\b{re.escape(phrase.lower())}\b", fb_lower):
            errors.append(f"feedback contains banned phrase: {phrase}")

    return errors


def validate_ai_result(
    result: Dict[str, Any],
    user_allergies: List[str],
    detected_ingredients: List[str],
    nutrition: Optional[Dict[str, Any]] = None,
) -> List[ValidationIssue]:
    """
    Deterministic validator used by the audit gate.
    Returns list[ValidationIssue]. Empty list => pass.
    """
    issues: List[ValidationIssue] = []

    for e in validate_basic_schema(result, max_recs=12):
        issues.append(ValidationIssue(code="SCHEMA", message=e))

    for e in validate_content_rules(result):
        issues.append(ValidationIssue(code="CONTENT", message=e))

    hits = _detect_allergen_hits(user_allergies, detected_ingredients)
    if hits:
        warning_text = ""
        if "warnings" in result:
            warning_text = " ".join([str(x) for x in (result.get("warnings") or [])]).lower()
        else:
            warning_text = str(result.get("feedback", "") or "").lower()

        if ("allergy" not in warning_text) and ("avoid" not in warning_text) and ("contains" not in warning_text):
            issues.append(
                ValidationIssue(
                    code="ALLERGY",
                    message=f"Detected possible allergen(s) {hits} but output does not clearly warn (missing 'allergy/avoid/contains').",
                )
            )

    _ = nutrition
    return issues
