from fastapi import APIRouter, Depends, File, UploadFile
from src.auth.filters import JWTUserGuard
from src.util.json import generate_result

suggestion_router = APIRouter(prefix="/suggestion")


@suggestion_router.post('/ask', dependencies=[Depends(JWTUserGuard())])
async def ask_for_suggesstion(img:UploadFile=File(...)):
    print(img.filename)
    return generate_result((0, True))