from fastapi import APIRouter, Depends, Body
from src.auth.filters import JWTUserGuard
from src.auth.service import AuthService, get_auth_service, SessionService, get_session_service
from src.util.json import generate_result
from src.util.ctx import get_ctx
auth_router = APIRouter(prefix="/auth")

@auth_router.post("/sign-in")
async def signin(body:dict = Body(...), auth_service:AuthService=Depends(get_auth_service)):
    email = body['email']
    password = body['password']
    result_tuple = await auth_service.signIn(email= email, password= password)
    return generate_result(result_tuple)

@auth_router.post("/request-otp")
async def request_otp(body:dict = Body(...), service: AuthService = Depends(get_auth_service)):
    result_tuple = await service.request_otp(body['email'], body['biz_id'])
    print(result_tuple)
    return generate_result(result_tuple)

@auth_router.post("/confirm-password")
async def confirm_password(body:dict = Body(...), service: AuthService = Depends(get_auth_service)):
    result_tuple = await service.confirm_password(body['email'], body['otp'], body['password'], body['biz_id'])
    return generate_result(result_tuple)

@auth_router.post("/sign-out", dependencies=[Depends(JWTUserGuard())])
async def signout(auth_service:AuthService=Depends(get_auth_service)):
    try:
        await auth_service.signOut(get_ctx().user_id)
        return generate_result((0, "You have signed out"))
    except Exception as e:
        print(e)
        return generate_result((1, "Signing out has error"))
    
@auth_router.post("/me", dependencies=[Depends(JWTUserGuard())])
async def me():
    return generate_result((0, "OK"))

