from datetime import datetime, timezone
from functools import lru_cache

from bson import ObjectId

from src.suggestion.agent import get_agent
from src.suggestion.repo import SuggestionRepo
from src.util.mongo import MongoDBPool
from src.wellness.repository import AllergiesRepo, ChronicsRepo, WellnessRepo

# NEW: audit runs in service (avoids circular import issues)
from src.ai.audit import run_ai_audit


class SuggestionService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def _feedback_to_text(feedback_value) -> str:
        if isinstance(feedback_value, dict):
            return str(
                feedback_value.get("explaination")
                or feedback_value.get("explanation")
                or feedback_value.get("text")
                or ""
            ).strip()
        return str(feedback_value or "").strip()

    @staticmethod
    def _feedback_to_legacy_obj(level_value, feedback_text: str) -> dict:
        try:
            level_int = int(level_value)
        except Exception:
            level_int = 2
        if level_int not in (1, 2, 3):
            level_int = 2
        return {
            "level": str(level_int),
            "explaination": str(feedback_text or ""),
        }

    @staticmethod
    def _normalize_mark(value) -> int:
        try:
            m = int(float(value))
        except Exception:
            m = 0
        if m < 0:
            return 0
        if m > 100:
            return 100
        return m

    def _normalize_feedback_for_frontend(self, doc: dict) -> dict:
        if not isinstance(doc, dict):
            return doc
        doc["mark"] = self._normalize_mark(doc.get("mark", 0))
        feedback_text = self._feedback_to_text(doc.get("feedback"))
        doc["feedback"] = self._feedback_to_legacy_obj(doc.get("level"), feedback_text)
        doc["feedback_text"] = feedback_text
        return doc

    async def read_suggestion_page(self, user_id, last_id):
        suggestion_repo = SuggestionRepo(self.db)
        page = await suggestion_repo.find_suggestions_page(user_id, last_id)
        return [self._normalize_feedback_for_frontend(x) for x in (page or [])]

    async def get_suggestion(self, base64_img, base64_thumbnail, user_id):
        wellness_repo = WellnessRepo(self.db)
        chronics_repo = ChronicsRepo(self.db)
        allergies_repo = AllergiesRepo(self.db)

        # wellness can be None for new users
        wellness = await wellness_repo.get_user_wellness_items_lists(user_id)
        wellness = wellness or {}

        chronics_ids = wellness.get("chronics", []) or []
        allergies_ids = wellness.get("allergies", []) or []

        chronics_objs = await chronics_repo.get_item_list_by_ids(chronics_ids) if chronics_ids else []
        allergies_objs = await allergies_repo.get_item_list_by_ids(allergies_ids) if allergies_ids else []

        chronics_names = [x.get("name", "") for x in chronics_objs if isinstance(x, dict) and x.get("name")]
        allergies_names = [x.get("name", "") for x in allergies_objs if isinstance(x, dict) and x.get("name")]

        # --- PRIMARY AI RESULT (agent returns normalized schema; NO audit here) ---
        agent = get_agent()
        suggestion = await agent.get(base64_img, chronics_names, allergies_names)

        # Fail-closed if agent output is weird
        if not isinstance(suggestion, dict):
            suggestion = {
                "code": 1,
                "message": "AI returned invalid response type",
                "mark": 0,
                "level": 3,
                "feedback": (
                    "Unable to assess this meal because the AI response was invalid. "
                    "Please upload a clearer photo or include an ingredient list."
                ),
                "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
                "detected_ingredients": [],
            }

        # --- Enforce required keys/types (extra safety) ---
        suggestion.setdefault("code", 0)
        suggestion.setdefault("message", "")
        suggestion.setdefault("mark", 0)
        suggestion.setdefault("level", 2)
        suggestion.setdefault("feedback", "")
        suggestion.setdefault("recommendation", ["Greek salad", "Vegetable soup", "Oatmeal with fruit"])
        suggestion.setdefault("detected_ingredients", [])

        # Normalize detected_ingredients type (defensive)
        if not isinstance(suggestion.get("detected_ingredients"), list):
            suggestion["detected_ingredients"] = []

        # Normalize recommendation type (defensive)
        if not isinstance(suggestion.get("recommendation"), list) or len(suggestion.get("recommendation", [])) == 0:
            suggestion["recommendation"] = ["Greek salad", "Vegetable soup", "Oatmeal with fruit"]

        suggestion["mark"] = self._normalize_mark(suggestion.get("mark", 0))
        if suggestion["mark"] > 0:
            suggestion["code"] = 0
            suggestion["message"] = ""
        feedback_text = self._feedback_to_text(suggestion.get("feedback"))
        suggestion["feedback"] = feedback_text

        # --- AUDIT GATE (RUNS HERE) ---
        detected_ingredients = [str(x) for x in (suggestion.get("detected_ingredients") or [])]
        nutrition = suggestion.get("nutrition", None)  # optional; usually None

        audit = run_ai_audit(
            ai_output={
                "code": suggestion.get("code"),
                "message": suggestion.get("message"),
                "mark": suggestion.get("mark"),
                "level": suggestion.get("level"),
                "feedback": feedback_text,
                "recommendation": suggestion.get("recommendation"),
                "detected_ingredients": suggestion.get("detected_ingredients"),
            },
            user_allergies=[str(a) for a in (allergies_names or [])],
            detected_ingredients=detected_ingredients,
            nutrition=nutrition,
        )

        suggestion["audit"] = {
            "passed": audit.passed,
            "issues": audit.issues,
            "judge_notes": audit.judge_notes,
        }

        # If audit failed, block unsafe/unreliable AI output
        if not audit.passed:
            suggestion = {
                "code": 1,
                "message": "AI audit failed",
                "mark": 0,
                "level": 3,
                "feedback": (
                    "Unable to confidently assess this meal from the image. "
                    "Please upload a clearer photo of the ingredient list or add the ingredients in text "
                    "so we can check allergies safely."
                ),
                "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
                "detected_ingredients": [],
                "audit": {
                    "passed": False,
                    "issues": audit.issues or [{"code": "AUDIT_FAILED", "message": "audit failed"}],
                    "judge_notes": audit.judge_notes or "",
                },
            }

        # --- SAVE RESULT ---
        suggestion_repo = SuggestionRepo(self.db)

        record = {
            # existing fields (keep for backward compatibility)
            "mark": suggestion.get("mark"),
            "feedback": self._feedback_to_legacy_obj(suggestion.get("level"), self._feedback_to_text(suggestion.get("feedback"))),
            "feedback_text": self._feedback_to_text(suggestion.get("feedback")),
            "recommendation": suggestion.get("recommendation"),

            # NEW fields (proof + debugging + allergy checks)
            "code": suggestion.get("code"),
            "message": suggestion.get("message"),
            "level": suggestion.get("level"),
            "detected_ingredients": suggestion.get("detected_ingredients"),
            "audit": suggestion.get("audit"),

            "user_id": ObjectId(user_id),
            "thumbnail": base64_thumbnail,
            "time": datetime.now(timezone.utc),
        }

        saved = await suggestion_repo.save(record)
        return self._normalize_feedback_for_frontend(saved)


@lru_cache
def get_suggestion_service():
    return SuggestionService(MongoDBPool.get_db())
