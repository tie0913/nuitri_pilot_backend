from functools import lru_cache
from abc import abstractmethod
import asyncio
import json
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI
from src.util.config import get_settings


class AIAgent:
    @abstractmethod
    async def get(self, base64_img, chronics, allergies) -> Dict[str, Any]:
        pass


class OpenAIAgent(AIAgent):
    def __init__(self):
        config = get_settings()
        self.client = AsyncOpenAI(api_key=config.OPEN_AI_API_KEY)

    def _as_data_url(self, maybe_b64: str, default_mime: str = "image/jpeg") -> str:
        s = (maybe_b64 or "").strip()
        if s.startswith("data:image/") and ";base64," in s:
            return s
        if s.startswith("http://") or s.startswith("https://"):
            return s
        return f"data:{default_mime};base64,{s}"

    @staticmethod
    def _json_contract_errors(obj: Any, required_keys: Optional[List[str]]) -> List[str]:
        errors: List[str] = []
        if not isinstance(obj, dict):
            return ["json output must be an object"]
        for k in (required_keys or []):
            if k not in obj:
                errors.append(f"missing key: {k}")
        return errors

    @staticmethod
    def _is_not_found_text(txt: str) -> bool:
        s = str(txt or "").strip().upper()
        return (not s) or s == "NOT_FOUND"

    async def _repair_json_once(
        self,
        model: str,
        original_user_text: str,
        invalid_output: str,
        required_keys: Optional[List[str]],
        timeout_s: float,
        max_output_tokens: int,
    ) -> Dict[str, Any]:
        required = ", ".join(required_keys or []) or "(no required keys)"
        repair_system = "You fix invalid model outputs. Return ONLY valid JSON. No markdown."
        repair_user = (
            "Fix the previous response so it is a single valid JSON object.\n"
            f"Required keys: {required}\n"
            "Do not add explanations. Keep original intent.\n\n"
            f"Original task:\n{original_user_text}\n\n"
            f"Invalid output:\n{invalid_output[:1800]}"
        )

        resp = await asyncio.wait_for(
            self.client.responses.create(
                model=model,
                input=[
                    {"role": "system", "content": [{"type": "input_text", "text": repair_system}]},
                    {"role": "user", "content": [{"type": "input_text", "text": repair_user}]},
                ],
                temperature=0,
                max_output_tokens=max_output_tokens,
            ),
            timeout=timeout_s,
        )

        repaired_text = (resp.output_text or "").strip()
        repaired_obj = json.loads(repaired_text)
        repair_errors = self._json_contract_errors(repaired_obj, required_keys)
        if repair_errors:
            raise ValueError("json repair failed contract: " + "; ".join(repair_errors[:5]))
        return repaired_obj

    # -----------------------------
    # Public entry
    # -----------------------------
    async def get(self, base64_img, chronics, allergies) -> Dict[str, Any]:
        """
        Agent responsibility:
        - Call the model(s)
        - Normalize output
        - NEVER crash on bad user images / API errors
        - DO NOT run audit here
        """
        config = get_settings()
        image_url = self._as_data_url(base64_img)

        # Keep defaults strict to avoid long frontend "Analyzing..." hangs.
        call_timeout_s = float(getattr(config, "OPEN_AI_TIMEOUT_S", 15) or 15)
        max_retries = int(getattr(config, "OPEN_AI_MAX_RETRIES", 0) or 0)
        total_timeout_s = float(getattr(config, "OPEN_AI_TOTAL_TIMEOUT_S", 50) or 50)

        loop = asyncio.get_running_loop()
        deadline = loop.time() + total_timeout_s

        def _next_timeout_s() -> float:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise asyncio.TimeoutError("Total AI timeout reached")
            return min(call_timeout_s, max(1.0, remaining))

        try:
            # 1) Route first so meal photos (pizza, burger, etc.) don't fail OCR-first.
            kind = await self._route_image_kind(
                model=config.OPEN_AI_MODEL,
                image_url=image_url,
                timeout_s=_next_timeout_s(),
                retries=max_retries,
            )

            if kind == "NON_FOOD":
                return self._code1_non_food_image_response()

            if kind == "FOOD":
                scored_photo = await self._score_from_food_photo(
                    model=config.OPEN_AI_MODEL,
                    image_url=image_url,
                    chronics=chronics,
                    allergies=allergies,
                    timeout_s=_next_timeout_s(),
                    retries=max_retries,
                    expected_kind="FOOD",
                    force_best_effort=True,
                )
                normalized_photo = self._normalize_ai_output(scored_photo)
                if self._is_non_food_signal(
                    normalized_photo.get("feedback", ""),
                    normalized_photo.get("detected_ingredients", []),
                ):
                    return self._code1_non_food_image_response()
                if int(normalized_photo.get("code", 1) or 1) == 0:
                    return normalized_photo
                return self._code0_food_photo_best_effort_response(
                    chronics=chronics,
                    allergies=allergies,
                    seed=normalized_photo,
                )

            # 2) LABEL/UNKNOWN: OCR-first path with a relaxed OCR rescue pass.
            ing_text = await self._extract_ingredients_text(
                model=config.OPEN_AI_MODEL,
                image_url=image_url,
                timeout_s=_next_timeout_s(),
                retries=max_retries,
                relaxed=False,
            )

            if self._is_not_found_text(ing_text):
                ing_text = await self._extract_ingredients_text(
                    model=config.OPEN_AI_MODEL,
                    image_url=image_url,
                    timeout_s=_next_timeout_s(),
                    retries=max_retries,
                    relaxed=True,
                )

            if self._is_not_found_text(ing_text):
                scored_photo = await self._score_from_food_photo(
                    model=config.OPEN_AI_MODEL,
                    image_url=image_url,
                    chronics=chronics,
                    allergies=allergies,
                    timeout_s=_next_timeout_s(),
                    retries=max_retries,
                    expected_kind="LABEL",
                    force_best_effort=False,
                )
                normalized_photo = self._normalize_ai_output(scored_photo)
                if self._is_non_food_signal(
                    normalized_photo.get("feedback", ""),
                    normalized_photo.get("detected_ingredients", []),
                ):
                    return self._code1_non_food_image_response()
                if int(normalized_photo.get("code", 1) or 1) == 0:
                    return normalized_photo
                return self._code1_uncertain_label_response(chronics, allergies)

            # 3) Score pass: text-only scoring (stable when OCR has signal)
            scored = await self._score_from_ingredients_text(
                model=config.OPEN_AI_MODEL,
                ingredients_text=ing_text,
                chronics=chronics,
                allergies=allergies,
                timeout_s=_next_timeout_s(),
                retries=max_retries,
            )

            normalized_scored = self._normalize_ai_output(scored)
            if self._is_non_food_signal(
                normalized_scored.get("feedback", ""),
                normalized_scored.get("detected_ingredients", []),
            ):
                return self._code1_non_food_image_response()
            if int(normalized_scored.get("code", 1) or 1) == 0:
                return normalized_scored

            # Rescue path: if text scoring failed, try image-only scoring.
            scored_photo = await self._score_from_food_photo(
                model=config.OPEN_AI_MODEL,
                image_url=image_url,
                chronics=chronics,
                allergies=allergies,
                timeout_s=_next_timeout_s(),
                retries=max_retries,
                expected_kind="LABEL",
                force_best_effort=False,
            )
            normalized_photo = self._normalize_ai_output(scored_photo)
            if self._is_non_food_signal(
                normalized_photo.get("feedback", ""),
                normalized_photo.get("detected_ingredients", []),
            ):
                return self._code1_non_food_image_response()
            if int(normalized_photo.get("code", 1) or 1) == 0:
                return normalized_photo

            return normalized_scored

        except asyncio.TimeoutError:
            return {
                "code": 1,
                "message": "AI processing timed out. Please try a clearer image.",
                "mark": 0,
                "level": 3,
                "feedback": (
                    "The image analysis took too long and timed out. "
                    "Please retry with a close-up photo of the Ingredients section "
                    "(good lighting, no glare, in focus) or paste ingredients as text."
                ),
                "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
                "detected_ingredients": [],
            }
        except Exception as e:
            # Never leak SDK exception names like BadRequestError in message
            safe_detail = self._safe_error_detail(e)

            return {
                "code": 1,
                "message": "Unable to process image: " + safe_detail,
                "mark": 0,
                "level": 3,
                "feedback": (
                    "I couldn't confidently read an ingredient list from this image. "
                    "If this is a packaged food, please upload a clearer photo of the Ingredients section "
                    "(close-up, good lighting, no glare). If it’s a food photo, I can still give general guidance "
                    "but I can’t score ingredients without the label or typed ingredients."
                ),
                "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
                "detected_ingredients": [],
            }

    # -----------------------------
    # Step 1: route kind
    # -----------------------------
    async def _route_image_kind(self, model: str, image_url: str, timeout_s: float, retries: int) -> str:
        """
        Returns: 'LABEL' or 'FOOD' or 'NON_FOOD'
        Cheap classifier. Keeps the expensive OCR pipeline only for likely label images.
        """
        system_text = "You are a strict classifier. Reply with ONLY one token: LABEL, FOOD, or NON_FOOD."
        user_text = (
            "Decide if the image is a readable food label, a food image, or unrelated to food. "
            "Return LABEL for close-up ingredient/nutrition labels with readable text. "
            "Return FOOD for meals, packaged food, or food photos without readable labels. "
            "Return NON_FOOD for landscapes, people, pets, buildings, documents, or any non-food scene."
        )

        raw = await self._call_responses_json_or_text(
            model=model,
            system_text=system_text,
            user_text=user_text,
            image_url=image_url,
            max_output_tokens=32,  # ✅ must be >= 16 (OpenAI minimum)
            temperature=0,
            timeout_s=timeout_s,
            retries=retries,
            expect_json=False,
        )

        token = (raw or "").strip().upper()
        if "NON_FOOD" in token:
            return "NON_FOOD"
        if "LABEL" in token:
            return "LABEL"
        return "FOOD"

    # -----------------------------
    # Step 2: OCR extract
    # -----------------------------
    async def _extract_ingredients_text(
        self,
        model: str,
        image_url: str,
        timeout_s: float,
        retries: int,
        relaxed: bool = False,
    ) -> str:
        """
        OCR step. Returns raw label text (ingredients and/or nutrition) or 'NOT_FOUND'.
        """
        system_text = "You extract text. Reply with ONLY text. No JSON. No markdown."
        if not relaxed:
            user_text = (
                "Extract useful nutrition label text from the image.\n"
                "Rules:\n"
                "- If you see an 'Ingredients' section, copy the ingredients text.\n"
                "- If ingredients are not visible but Nutrition Facts are readable, copy key nutrition lines.\n"
                "- Return plain text only, no explanations.\n"
                "- If you cannot read either ingredients or nutrition facts, reply with exactly: NOT_FOUND\n"
            )
        else:
            user_text = (
                "Best-effort OCR from a potentially blurry food label image.\n"
                "Rules:\n"
                "- Try to recover ANY readable tokens from ingredients and nutrition lines.\n"
                "- If only partial text is visible, return that partial text (plain text, no JSON).\n"
                "- Return NOT_FOUND only if absolutely no useful food-label text is visible.\n"
            )

        txt = await self._call_responses_json_or_text(
            model=model,
            system_text=system_text,
            user_text=user_text,
            image_url=image_url,
            max_output_tokens=220,
            temperature=0,
            timeout_s=timeout_s,
            retries=retries,
            expect_json=False,
        )

        return (txt or "").strip()

    # -----------------------------
    # Step 3: Score (text-only)
    # -----------------------------
    async def _score_from_ingredients_text(
        self,
        model: str,
        ingredients_text: str,
        chronics: List[str],
        allergies: List[str],
        timeout_s: float,
        retries: int,
    ) -> Dict[str, Any]:
        """
        Text-only JSON scoring. Much more stable than scoring directly from the image.
        """
        system_text = "You are a nutrition assistant. Return ONLY valid JSON. No markdown. No extra text."

        user_text = f"""
You are given food label text (already extracted) which may include ingredients and/or nutrition facts.
Also you are given the user's chronics and allergies.

You MUST return JSON with this EXACT schema:

{{
  "code": 0,
  "message": "",
  "mark": 0,
  "level": 1,
  "feedback": "string (>= 50 words, plain English)",
  "recommendation": ["string","string","string"],
  "detected_ingredients": ["string","string"]
}}

Rules:
- code: 0 = success, 1 = failure.
- If the extracted label text is missing/unreadable, set:
  code=1, message explaining why, mark=0, level=3, feedback explaining uncertainty,
  recommendation must still be a non-empty list, detected_ingredients should be [].
- mark must be between 0 and 100.
- level: 1=good, 2=intermediate, 3=not recommend.
- recommendation must be 3-4 similar healthier options (names only).
- detected_ingredients: parse ingredients into a list (best effort; [] if unavailable).
- Avoid medical claims like "cure/heal/detox/miracle/guarantee".

User chronics: {chronics}
User allergies: {allergies}

Extracted label text:
{ingredients_text}

Now respond with ONLY JSON.
        """.strip()

        raw_obj = await self._call_responses_json_or_text(
            model=model,
            system_text=system_text,
            user_text=user_text,
            image_url=None,
            max_output_tokens=700,
            temperature=0,
            timeout_s=timeout_s,
            retries=retries,
            expect_json=True,
            json_required_keys=[
                "code",
                "message",
                "mark",
                "level",
                "feedback",
                "recommendation",
                "detected_ingredients",
            ],
        )

        return raw_obj

    async def _score_from_food_photo(
        self,
        model: str,
        image_url: str,
        chronics: List[str],
        allergies: List[str],
        timeout_s: float,
        retries: int,
        expected_kind: str = "FOOD",
        force_best_effort: bool = False,
    ) -> Dict[str, Any]:
        """
        Fallback when OCR extraction fails.
        Works for both food photos and label-like photos where OCR missed text.
        """
        system_text = "You are a nutrition assistant. Return ONLY valid JSON. No markdown. No extra text."
        extra_force_rule = ""
        if force_best_effort:
            extra_force_rule = (
                "- Rescue mode: if the image is a recognizable meal (pizza, burger, salad, bowl, snack), "
                "you MUST return code=0 with best-effort inferred ingredients.\n"
            )

        user_text = f"""
You are given a food-related image. Use all visible cues (label text, nutrition panel, package clues, and food appearance).
Expected image type hint: {expected_kind}

If it looks like a label with readable nutrition facts, use visible numbers/words.
If it looks like a meal photo, estimate likely ingredients from visible food.
Prefer a best-effort useful result instead of hard failure when there is any usable signal.

Return JSON with this EXACT schema:
{{
  "code": 0,
  "message": "",
  "mark": 0,
  "level": 1,
  "feedback": "string (>= 35 words, plain English)",
  "recommendation": ["string","string","string"],
  "detected_ingredients": ["string","string"]
}}

Rules:
- Keep code=0 unless the image is truly unusable/blank/too blurry.
- For food photos, avoid code=1 unless image is blank/corrupted/unidentifiable.
{extra_force_rule}- Mention uncertainty clearly when ingredients are inferred.
- mark must be between 0 and 100.
- level: 1=good, 2=intermediate, 3=not recommend.
- recommendation must be 3-4 practical healthier alternatives.
- detected_ingredients should list likely visible ingredients (best effort).
- If likely allergens are visible, explicitly warn with words like avoid/allergy/contains.
- Avoid medical claims like cure/heal/detox/miracle/guarantee.

User chronics: {chronics}
User allergies: {allergies}
Now respond with ONLY JSON.
        """.strip()

        raw_obj = await self._call_responses_json_or_text(
            model=model,
            system_text=system_text,
            user_text=user_text,
            image_url=image_url,
            max_output_tokens=700,
            temperature=0,
            timeout_s=timeout_s,
            retries=retries,
            expect_json=True,
            json_required_keys=[
                "code",
                "message",
                "mark",
                "level",
                "feedback",
                "recommendation",
                "detected_ingredients",
            ],
        )
        return raw_obj

    # -----------------------------
    # Low-level caller with timeout + retry
    # -----------------------------
    async def _call_responses_json_or_text(
        self,
        model: str,
        system_text: str,
        user_text: str,
        image_url: Optional[str],
        max_output_tokens: int,
        temperature: float,
        timeout_s: float,
        retries: int,
        expect_json: bool,
        json_required_keys: Optional[List[str]] = None,
    ):
        last_err: Optional[Exception] = None

        # ✅ Hard guard: OpenAI requires >= 16
        if max_output_tokens is None or int(max_output_tokens) < 16:
            max_output_tokens = 16

        for attempt in range(retries + 1):
            try:
                input_payload = [
                    {"role": "system", "content": [{"type": "input_text", "text": system_text}]},
                    {"role": "user", "content": [{"type": "input_text", "text": user_text}]},
                ]

                if image_url:
                    input_payload[1]["content"].append({"type": "input_image", "image_url": image_url})

                resp = await asyncio.wait_for(
                    self.client.responses.create(
                        model=model,
                        input=input_payload,
                        temperature=temperature,
                        max_output_tokens=max_output_tokens,
                    ),
                    timeout=timeout_s,
                )

                out_text = (resp.output_text or "").strip()

                if expect_json:
                    parsed = json.loads(out_text)
                    contract_errors = self._json_contract_errors(parsed, json_required_keys)
                    if contract_errors:
                        return await self._repair_json_once(
                            model=model,
                            original_user_text=user_text,
                            invalid_output=out_text,
                            required_keys=json_required_keys,
                            timeout_s=timeout_s,
                            max_output_tokens=max_output_tokens,
                        )
                    return parsed

                return out_text

            except Exception as e:
                last_err = e
                if attempt < retries:
                    await asyncio.sleep(0.3 * (attempt + 1))
                    continue

        raise last_err

    # -----------------------------
    # Code=1 helpers (fast UX)
    # -----------------------------
    def _code1_food_photo_response(self, chronics, allergies) -> Dict[str, Any]:
        return {
            "code": 1,
            "message": "No readable ingredient label detected in the photo.",
            "mark": 0,
            "level": 3,
            "feedback": (
                "This looks like a food photo (not a clear ingredient label), so I can’t reliably read ingredients. "
                "If this is packaged food, please upload a close-up of the Ingredients section (good lighting, no glare). "
                "If it’s homemade/restaurant food, paste ingredients or tell me what it is and how it was prepared. "
                "Given your chronics/allergies, I can still give general safer swaps and what to watch for."
            ),
            "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
            "detected_ingredients": [],
        }

    def _code1_unreadable_label_response(self) -> Dict[str, Any]:
        return {
            "code": 1,
            "message": "Ingredient list missing or unreadable.",
            "mark": 0,
            "level": 3,
            "feedback": (
                "I couldn’t confidently read the ingredient list. Please upload a clearer photo of the Ingredients section "
                "(close-up, flat label, good lighting, no glare, in focus). If you paste the ingredients as text, "
                "I can score it more reliably and check allergens."
            ),
            "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
            "detected_ingredients": [],
        }

    def _code1_non_food_image_response(self) -> Dict[str, Any]:
        return {
            "code": 1,
            "message": "This image does not appear to be food.",
            "mark": 0,
            "level": 3,
            "feedback": (
                "I could not detect food or a nutrition label in this image. "
                "Please upload a meal photo or a clear ingredient-label photo so I can score it."
            ),
            "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
            "detected_ingredients": [],
        }

    @staticmethod
    def _is_non_food_signal(feedback, detected_ingredients) -> bool:
        detected = detected_ingredients if isinstance(detected_ingredients, list) else []
        detected = [str(x).strip() for x in detected if str(x).strip()]
        if detected:
            return False

        fb = str(feedback or "").lower()
        non_food_phrases = [
            "does not contain any food",
            "no food items",
            "not food",
            "non-food",
            "scenic photo",
            "landscape",
            "mountain",
            "lake",
            "nature photo",
            "travel photo",
            "please provide an image that includes food",
            "food items or labels",
        ]
        return any(p in fb for p in non_food_phrases)

    def _code0_food_photo_best_effort_response(self, chronics, allergies, seed: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Best-effort success response for recognizable food photos without readable labels.
        Keeps uncertainty explicit but avoids hard failure for normal meal images.
        """
        src = seed if isinstance(seed, dict) else {}

        recs = src.get("recommendation", src.get("recommendations", [])) or []
        if isinstance(recs, str):
            recs = [r.strip() for r in recs.split(",") if r.strip()]
        if not isinstance(recs, list):
            recs = []
        recs = [str(r).strip() for r in recs if str(r).strip()]
        if not recs:
            recs = ["Greek salad", "Vegetable soup", "Oatmeal with fruit"]

        detected = src.get("detected_ingredients", src.get("ingredients", [])) or []
        if isinstance(detected, str):
            detected = [x.strip() for x in detected.split(",") if x.strip()]
        if not isinstance(detected, list):
            detected = []
        detected = [str(x).strip() for x in detected if str(x).strip()][:30]

        try:
            mark = float(src.get("mark", 0) or 0)
        except Exception:
            mark = 0.0
        if mark <= 0:
            mark = 55.0 if detected else 50.0
        mark = max(0.0, min(100.0, mark))

        try:
            level = int(src.get("level", 2) or 2)
        except Exception:
            level = 2
        if level not in (1, 2, 3):
            level = 2
        if level == 3 and mark >= 45:
            level = 2

        feedback = str(src.get("feedback", "") or "").strip()
        if self._is_non_food_signal(feedback, detected):
            return self._code1_non_food_image_response()

        if len([w for w in feedback.split() if w.strip()]) < 20:
            chronic_txt = ", ".join([str(x) for x in (chronics or []) if str(x).strip()]) or "your health goals"
            allergy_txt = ", ".join([str(x) for x in (allergies or []) if str(x).strip()]) or "known allergens"
            feedback = (
                "This appears to be a food photo, so I am giving a best-effort score from visible cues only. "
                "Because the ingredient label is not readable, treat this as approximate guidance for "
                f"{chronic_txt}. For {allergy_txt}, confirm packaged ingredients before relying on this result."
            )

        if self._is_non_food_signal(feedback, detected):
            return self._code1_non_food_image_response()

        return {
            "code": 0,
            "message": "",
            "mark": int(round(mark)),
            "level": level,
            "feedback": feedback,
            "recommendation": recs[:4],
            "detected_ingredients": detected,
        }

    def _code1_uncertain_label_response(self, chronics, allergies) -> Dict[str, Any]:
        chronic_txt = ", ".join([str(x) for x in (chronics or []) if str(x).strip()]) or "your health goals"
        allergy_txt = ", ".join([str(x) for x in (allergies or []) if str(x).strip()]) or "known allergens"
        return {
            "code": 1,
            "message": "Ingredient list missing or unreadable.",
            "mark": 0,
            "level": 3,
            "feedback": (
                "I could not read the full ingredient list clearly. "
                f"Given {chronic_txt}, and possible sensitivity to {allergy_txt}, please upload a clearer ingredient-label "
                "photo or provide the ingredients in text so I can score this safely."
            ),
            "recommendation": ["Greek salad", "Vegetable soup", "Oatmeal with fruit"],
            "detected_ingredients": [],
        }

    # -----------------------------
    # Sanitizers / normalizer
    # -----------------------------
    def _safe_error_detail(self, e: Exception) -> str:
        msg = str(e) if e else "Unknown error"
        for bad in ["BadRequestError", "RateLimitError", "APIError", "AuthenticationError"]:
            msg = msg.replace(bad, "Error")
        msg = msg.strip()
        if len(msg) > 300:
            msg = msg[:300] + "..."
        return msg or "Error"

    def _promote_best_effort(self, out: Dict[str, Any]) -> Dict[str, Any]:
        """
        Some model outputs return code=1 even with meaningful score + feedback.
        Promote those to code=0 so UI can treat them as usable best-effort results.
        """
        if not isinstance(out, dict):
            return out
        try:
            code = int(out.get("code", 1) or 1)
        except Exception:
            code = 1
        try:
            mark = float(out.get("mark", 0) or 0)
        except Exception:
            mark = 0.0
        feedback = str(out.get("feedback", "") or "").strip()
        feedback_words = len([w for w in feedback.split() if w.strip()])
        ingredients = out.get("detected_ingredients") or []
        if not isinstance(ingredients, list):
            ingredients = []
        recs = out.get("recommendation", out.get("recommendations", [])) or []
        if not isinstance(recs, list):
            recs = []

        has_signal = (
            (mark >= 25 and feedback_words >= 16)
            or len(ingredients) >= 2
            or (feedback_words >= 28 and len(recs) >= 3)
        )
        if code == 1 and has_signal:
            out["code"] = 0
            out["message"] = ""
        return out

    def _normalize_ai_output(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}

        try:
            out["code"] = int(raw.get("code", 0) or 0)
        except Exception:
            out["code"] = 0
        out["message"] = str(raw.get("message", "") or "")

        mark = raw.get("mark", 0)
        try:
            m = float(mark)
            out["mark"] = int(m) if m.is_integer() else m
        except Exception:
            out["mark"] = 0

        lvl = raw.get("level", 2)
        try:
            out["level"] = int(lvl)
        except Exception:
            out["level"] = 2
        if out["level"] not in (1, 2, 3):
            out["level"] = 2

        fb = raw.get("feedback", "")
        if isinstance(fb, dict):
            fb = fb.get("explaination") or fb.get("explanation") or json.dumps(fb)
        out["feedback"] = str(fb or "").strip()

        recs = raw.get("recommendation", raw.get("recommendations", []))
        if isinstance(recs, str):
            recs = [r.strip() for r in recs.split(",") if r.strip()]
        if not isinstance(recs, list):
            recs = []
        recs = [str(r).strip() for r in recs if str(r).strip()]
        if len(recs) == 0:
            recs = ["Greek salad", "Vegetable soup", "Oatmeal with fruit"]
        out["recommendation"] = recs[:4]

        ings = raw.get("detected_ingredients", raw.get("ingredients", []))
        if isinstance(ings, str):
            ings = [i.strip() for i in ings.split(",") if i.strip()]
        if not isinstance(ings, list):
            ings = []
        out["detected_ingredients"] = [str(i).strip() for i in ings if str(i).strip()][:30]

        if out["code"] == 1 and not out["message"]:
            out["message"] = "Could not confidently analyze this image."
        if not out["feedback"]:
            if out["code"] == 0:
                out["feedback"] = "This food appears acceptable, but please review portion size and ingredients."
            else:
                out["feedback"] = (
                    "I could not confidently read enough details from this image. "
                    "Try a closer, sharper photo or add ingredients in text."
                )

        return self._promote_best_effort(out)


@lru_cache
def get_agent():
    return OpenAIAgent()

