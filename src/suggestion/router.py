from multiprocessing import get_logger
from fastapi import APIRouter, Body, Depends, File, UploadFile
from src.auth.filters import JWTUserGuard
from src.suggestion.service import SuggestionService, get_suggestion_service
from src.util.ctx import get_ctx
from src.util.image_util import dealwith_img
from src.util.json import bson_col_to_json, generate_result, to_json

suggestion_router = APIRouter(prefix="/suggestion", dependencies=[Depends(JWTUserGuard())])

@suggestion_router.post('/ask')
async def ask_for_suggesstion(img:UploadFile=File(...), suggestion_service:SuggestionService=Depends(get_suggestion_service)):
    logger = get_logger()
    try:
        user_id = get_ctx().user_id
        img_info = await dealwith_img(img=img, user_id=user_id)
        if img_info['success']:
            logger.info("upload succeeds")
            resp = await suggestion_service.get_suggestion(
                img_info=img_info,
                user_id=user_id)
            logger.info("analysis succeeds")
            return generate_result((0, to_json(resp)))
        else:
            logger.error("upload failed")
            raise Exception(str(img_info['errors']))
    except Exception as e:
        print(e)
        logger.error("we have errors", e)
        return generate_result((1, "error"))

@suggestion_router.post('/get')
async def get_suggestion_page(body:dict=Body(...), suggestion_serivce:SuggestionService=Depends(get_suggestion_service)):
    last_id = None
    if 'last_id' in body:
        last_id = body['last_id']
    try:
        page = await suggestion_serivce.read_suggestion_page(get_ctx().user_id, last_id)
        return generate_result((0, bson_col_to_json(page)))
    except Exception as e:
        return generate_result((1, "reading suggestions list has error"))


@suggestion_router.post('/delete_by_id')
async def delete_by_id(body:dict=Body(...), suggestion_service:SuggestionService=Depends(get_suggestion_service)):
    id = None
    if 'id' in body:
        id = body['id']
    try:
        await suggestion_service.delete_by_id(id=id)
        return generate_result((0, True))
    except Exception as e:
        return generate_result((1, "deleting records has error"))
                        