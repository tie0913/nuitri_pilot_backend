from fastapi import APIRouter, Depends, Body
from src.user.service import UserService, get_user_service

user_router = APIRouter()

@user_router.post("/users/reset_password")
async def reset_password(body:dict = Body(...), service: UserService = Depends(get_user_service)):
    return {
        "success":True,
        "bizCode":0,
        "message":"",
        "data":{
            "code":"1234567890"
        }
    }