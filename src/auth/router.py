from fastapi import APIRouter, Depends, Body
from src.auth.service import AuthService, get_auth_service
auth_router = APIRouter()


@auth_router.post("/auth/signin")
async def signin(body:dict = Body(...), auth_service:AuthService=Depends(get_auth_service)):
    email = body['email']
    password = body['password']
    return await auth_service.signIn(email= email, password= password)
