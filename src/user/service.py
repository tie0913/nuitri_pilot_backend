from fastapi import Depends

from src.user.repository import UserRepository, get_user_repository


class UserService:

    def __init__(self, repository: UserRepository):
        self.repository = repository


    async def send_otp_for_reset_password(self, email:str):
        return await self.repository.get_user_by_email(email)
    


def get_user_service(repository = Depends(get_user_repository)):
    return UserService(repository)