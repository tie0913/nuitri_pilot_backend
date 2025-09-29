from fastapi import APIRouter, Depends, Body
from src.user.service import UserService, get_user_service

user_router = APIRouter()

@user_router.post("/users/reset_password")
async def reset_password(body:dict = Body(...), service: UserService = Depends(get_user_service)):

    person = await service.send_otp_for_reset_password(body['email'])
    return {
        "success":True,
        "bizCode":0,
        "message":"",
        "data":{
            "code":"1234567890",
            "p":person['name']

        }
    }