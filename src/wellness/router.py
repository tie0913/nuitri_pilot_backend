from multiprocessing import get_logger
from fastapi import APIRouter, Body, Depends
from src.wellness.service import WellnessService, get_wellness_service
from src.auth.filters import JWTUserGuard
from src.util.json import generate_result, to_json


wellness_router = APIRouter(prefix="/wellness")

@wellness_router.post("/get_user_wellness_and_items", dependencies=[Depends(JWTUserGuard())])
async def get_user_wellness(catalogName, wellness_service: WellnessService=Depends(get_wellness_service)):
    try:
        wellness = await wellness_service.get_user_wellness(catalogName)
        return generate_result((0, wellness))
    except Exception as e:
        return generate_result((1, "get_user_wellness_and_items has error"))


@wellness_router.post("/add_wellness_catalog_item", dependencies=[Depends(JWTUserGuard())])
async def add_wellness_catalog_item(catalogName, body:dict=Body(...), wellness_service:WellnessService=Depends(get_wellness_service)):

    name = body['name']
    if name is None or len(name) == 0:
        return generate_result((-1 , "parameter name is missed"))
    try:
        doc = await wellness_service.add_wellness_catalog_item(catalogName, body['name'])
        return generate_result((0, to_json(doc)));
    except Exception as e:
        return generate_result((1, "add wellness catalog item has error"))

    
@wellness_router.post("/save_user_selected_ids", dependencies=[Depends(JWTUserGuard())])
async def save_user_selected_wellness_items_ids(catalogName, body:dict=Body(...), wellness_service:WellnessService=Depends(get_wellness_service)):
    
    if "selectedIds" not in body:
        return generate_result((-1, "parameter is missed"))
    try:
        selectedIds = body['selectedIds']
        await wellness_service.save_user_selected_wellness_item_ids(catalogName, selectedIds)
        return generate_result((0, True))
    except Exception as e:
        return generate_result((1, "save_user_selected_ids has error"))
    
