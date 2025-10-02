from functools import lru_cache
from fastapi import Depends
from datetime import datetime, timedelta, timezone

from src.util.email_sender import send_email
from src.user.repository import UserRepository, get_user_repository
from src.util.otp_generator import generate_otp




class UserService:

    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def confirm_otp_and_reset_password(self, email:str, otp:str, password:str) :
        otp_record = await self.repository.get_otp_by_email_and_bus_id(email, "1")
        if otp_record is None:
            return (1, 'otp has expired')
        elif otp_record['otp'] != otp:
            return (2, 'otp is invalid')
        elif datetime.now() > otp_record['expireAt']:
            return (1, 'otp has expired')
        else:
            update_result = await self.repository.update_password_and_delete_otp(email, "1", password)
            if update_result:
                return (0, 'password has been reset')
            else:
                return (3, 'reset password has error')

    async def send_otp_for_reset_password(self, email:str) -> tuple:
        user = await self.repository.get_user_by_email(email)
        if user is None:
            return (1, 'user does not exist')
        else:
            otp = generate_otp(6)
            expireAt = datetime.now(timezone.utc) + timedelta(minutes=20)
            otp_saved = await self.repository.save_user_otp(email=email, otp=otp, busId="1", expireAt=expireAt)

            if otp_saved is False : return (1, 'sending otp code has error')

            email_content = UserService.get_email(otp, expireAt)
            email_send = send_email(user['email'], 'Reset Your Password - Nutri Pilot', email_content)

            if email_send :
                return (0, 'otp code has been sent')
            else:
                return (1, 'sending otp code has error')


    @classmethod
    def get_email(cls, opt, expireAt) -> str:
        email_template = f"""
            Dear User,

                Here is your OTP number for resetting your password.
            If you did not request for this, please ignore it.

                {opt}

                It will expire at {expireAt.strftime('%Y-%m-%d %H:%M:%S')}

            Thank you.

            Regards

            Nutri Pilot

        """
        return email_template
    
@lru_cache
def get_user_service() -> UserService:
    repository = get_user_repository()
    return UserService(repository)