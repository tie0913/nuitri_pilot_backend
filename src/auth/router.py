from fastapi import APIRouter, Depends, Body
from src.auth.filters import JWTUserGuard
from src.auth.service import AuthService, get_auth_service
from src.util.json import generate_result
from src.util.ctx import request_user_id
auth_router = APIRouter(prefix="/auth")


@auth_router.post("/sign-in")
async def signin(body:dict = Body(...), auth_service:AuthService=Depends(get_auth_service)):
    email = body['email']
    password = body['password']
    result_tuple = await auth_service.signIn(email= email, password= password)
    return generate_result(result_tuple)

@auth_router.post("/forget-password")
async def reset_password(body:dict = Body(...), service: AuthService = Depends(get_auth_service)):
    result_tuple = await service.send_otp_for_reset_password(body['email'])
    return generate_result(result_tuple)

@auth_router.post("/reset-password")
async def confirm_otp_and_reset_password(body:dict = Body(...), service: AuthService = Depends(get_auth_service)):
    result_tuple = await service.confirm_otp_and_reset_password(body['email'], body['otp'], body['password'])
    return generate_result(result_tuple)

@auth_router.post("/sign-out", dependencies=[Depends(JWTUserGuard())])
async def signout(auth_service:AuthService=Depends(get_auth_service)):
    try:
        await auth_service.signOut(request_user_id())
        return generate_result((0, "You have signed out"))
    except Exception as e:
        print(e)
        return generate_result((1, "Signing out has error"))
    