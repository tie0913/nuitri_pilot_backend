from fastapi import APIRouter, Depends, File, UploadFile
import base64
from src.auth.filters import JWTUserGuard
from src.suggestion.service import get_suggestion_service
from src.util.ctx import request_user_id
from src.util.json import generate_result

suggestion_router = APIRouter(prefix="/suggestion")

async def to_image_part(img: UploadFile):
    file_bytes = await img.read()
    base64_str = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{img.content_type};base64,{base64_str}"

@suggestion_router.post('/ask', dependencies=[Depends(JWTUserGuard())])
async def ask_for_suggesstion(img:UploadFile=File(...), suggestion_service=Depends(get_suggestion_service)):
    try:
        base64_img = await to_image_part(img)
        resp = await suggestion_service.get_suggestion(base64_img, request_user_id())
        print(resp)
        return generate_result((0, resp))
    except Exception as e:
        return generate_result((1, "error"))