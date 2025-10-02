from fastapi import APIRouter, Depends, Body
from src.user.service import UserService, get_user_service

user_router = APIRouter()


def generate_result(t:tuple):

    if t[0] == 0:
        return {
            "success":True,
            "code":t[0],
            "message":"",
            "data":t[1]
        }
    else:
        return {
            "success":False,
            "code":t[0],
            "message":t[1],
            "data":""
        }

@user_router.post("/users/apply_for_reseting_password_otp")
async def reset_password(body:dict = Body(...), service: UserService = Depends(get_user_service)):
    result_tuple = await service.send_otp_for_reset_password(body['email'])
    return generate_result(result_tuple)

@user_router.post("/users/confirm_otp_and_reset_password")
async def confirm_otp_and_reset_password(body:dict = Body(...), service: UserService = Depends(get_user_service)):
    result_tuple = await service.confirm_otp_and_reset_password(body['email'], body['otp'], body['password'])
    return generate_result(result_tuple)