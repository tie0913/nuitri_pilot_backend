from fastapi import APIRouter, Depends, Body
from src.user.service import UserService, get_user_service
from src.util.json import generate_result
user_router = APIRouter()



@user_router.post("/users/apply_for_reseting_password_otp")
async def reset_password(body:dict = Body(...), service: UserService = Depends(get_user_service)):
    result_tuple = await service.send_otp_for_reset_password(body['email'])
    return generate_result(result_tuple)

@user_router.post("/users/confirm_otp_and_reset_password")
async def confirm_otp_and_reset_password(body:dict = Body(...), service: UserService = Depends(get_user_service)):
    result_tuple = await service.confirm_otp_and_reset_password(body['email'], body['otp'], body['password'])
    return generate_result(result_tuple)