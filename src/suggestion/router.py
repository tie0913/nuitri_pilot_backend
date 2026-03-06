import logging
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, Body

from src.auth.filters import JWTUserGuard
from src.suggestion.service import SuggestionService, get_suggestion_service
from src.util.ctx import request_user_id
from src.util.image_util import image_to_base64_with_thumbnail
from src.util.json import bson_col_to_json, generate_result, to_json

suggestion_router = APIRouter(prefix="/suggestion")
logger = logging.getLogger(__name__)


# -----------------------------
# Shared handler logic (so /ask and /ask_audited stay identical)
# -----------------------------
async def _handle_ask(
    img: UploadFile,
    suggestion_service: SuggestionService,
):
    # ✅ user id comes from context set by JWTUserGuard()
    user_id = request_user_id()

    b64_result = await image_to_base64_with_thumbnail(img)
    if not b64_result.get("success"):
        raise HTTPException(status_code=400, detail=b64_result.get("error", "Invalid image"))

    resp = await suggestion_service.get_suggestion(
        b64_result["base64_img"],
        b64_result["base64_thumbnail"],
        user_id,
    )

    return generate_result((0, to_json(resp)))


# ✅ Compatibility endpoint for your frontend (stops 404 on /suggestion/ask)
@suggestion_router.post("/ask", dependencies=[Depends(JWTUserGuard())])
async def ask_for_suggestion(
    img: UploadFile = File(...),
    suggestion_service: SuggestionService = Depends(get_suggestion_service),
):
    try:
        return await _handle_ask(img, suggestion_service)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /suggestion/ask")
        raise HTTPException(status_code=500, detail=str(e))


# ✅ Live AI audited endpoint (for curl/Postman)
# IMPORTANT:
# - Use dependencies=[Depends(JWTUserGuard())] so the guard runs and sets context
# - Then read user_id via request_user_id()
@suggestion_router.post("/ask_audited", dependencies=[Depends(JWTUserGuard())])
async def ask_for_suggestion_audited(
    img: UploadFile = File(...),
    suggestion_service: SuggestionService = Depends(get_suggestion_service),
):
    try:
        return await _handle_ask(img, suggestion_service)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error in /suggestion/ask_audited")
        raise HTTPException(status_code=500, detail=str(e))


@suggestion_router.post("/get", dependencies=[Depends(JWTUserGuard())])
async def get_suggestion_page(
    body: dict = Body(...),
    suggestion_serivce: SuggestionService = Depends(get_suggestion_service),
):
    last_id = body.get("last_id")
    try:
        page = await suggestion_serivce.read_suggestion_page(request_user_id(), last_id)
        return generate_result((0, bson_col_to_json(page)))
    except Exception as e:
        logger.exception("Error in /suggestion/get")
        raise HTTPException(status_code=500, detail=str(e))