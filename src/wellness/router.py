from multiprocessing import get_logger
from fastapi import APIRouter, Body, Depends
from src.wellness.service import WellnessService, get_wellness_service
from src.auth.filters import JWTUserGuard
from src.util.json import generate_result, to_json


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
    


@wellness_router.post("/user_allergies", dependencies=[Depends(JWTUserGuard())])
async def get_user_allergies(wellness_service: WellnessService=Depends(get_wellness_service)):
    logger = get_logger()
    try:
        user_allergies = await wellness_service.get_user_allergies()
        logger.info("here is user allergies ", user_allergies)    
        return generate_result((0, user_allergies))
    except Exception as e:
        logger.error("reading user allergies data has error", e)
        return generate_result((1, "reading user allergies data has error"))


@wellness_router.post("/add_wellness_catalog_item")
async def add_wellness_catalog_item(catalogName, body:dict=Body(...), wellness_service:WellnessService=Depends(get_wellness_service)):

    name = body['name']
    if name is None or len(name) == 0:
        return generate_result((-1 , "parameter name missed"))
    try:
        doc = await wellness_service.add_wellness_catalog_item(catalogName, body['name'])
        return generate_result((0, to_json(doc)));
    except Exception as e:
        return generate_result((1, "add wellness catalog item has error"))