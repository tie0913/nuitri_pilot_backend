from multiprocessing import get_logger
from fastapi import APIRouter, Depends
from src.wellness.service import WellnessService, get_wellness_service
from src.auth.filters import JWTUserGuard
from src.util.json import generate_result


wellness_router = APIRouter(prefix="/wellness")


@wellness_router.post("/user_chronics", dependencies=[Depends(JWTUserGuard())])
async def get_user_chronics(wellness_service: WellnessService=Depends(get_wellness_service)):
    try:
        user_chronics = await wellness_service.get_user_chronics()
        return generate_result((0, user_chronics))
    except Exception as e:
        logger = get_logger()
        logger.error('reading user chronics data has error', e)
        return generate_result((1, "reading user chronics data has error"))
    