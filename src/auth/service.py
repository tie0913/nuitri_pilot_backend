from functools import lru_cache
from src.auth.token import TokenService, get_token_service
from src.user.repository import UserRepository, get_user_repository
from src.auth.repository import SessionRepository, get_session_repository
from datetime import datetime, timedelta, timezone

from src.util.email_sender import send_email
from src.util.otp_generator import generate_otp

NOT_MATCHED_TEXT = (1, 'Email and Password are not matched')

class AuthService:
    
    def __init__(self, token_service:TokenService, user_repository:UserRepository, session_repository:SessionRepository):
        self.token_service = token_service
        self.user_repository = user_repository
        self.session_repository = session_repository
    
    #
    # 登录方法
    # 0  :  token
    # 1  : 用户与密码不匹配
    #
    async def signIn(self, email:str, password:str) -> tuple:
        user = await self.user_repository.get_user_by_email(email)
        if user is not None and password == user['password']:
            user_id = str(user['_id'])
            token = self.token_service.create_token(user_id)
            expire_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            await self.session_repository.save_session(user_id = user_id, expire_at = expire_at)
            return (0, token)
        else:
            return NOT_MATCHED_TEXT


    async def signOut(self, user_id:str):
        await self.session_repository.remove_by_user_id(user_id)

    async def get_user_by_email(self, email:str):
        return await self.user_repository.get_user_by_email(email)


    async def confirm_otp_and_reset_password(self, email:str, otp:str, password:str) :
        otp_record = await self.user_repository.get_otp_by_email_and_bus_id(email, "1")
        if otp_record is None:
            return (1, 'otp has expired')
        elif otp_record['otp'] != otp:
            return (2, 'otp is invalid')
        elif datetime.now() > otp_record['expireAt']:
            return (1, 'otp has expired')
        else:
            update_result = await self.user_repository.update_password_and_delete_otp(email, "1", password)
            if update_result:
                return (0, 'password has been reset')
            else:
                return (3, 'reset password has error')

    async def send_otp_for_reset_password(self, email:str) -> tuple:
        user = await self.user_repository.get_user_by_email(email)
        if user is None:
            return (1, 'user does not exist')
        else:
            otp = generate_otp(6)
            expireAt = datetime.now(timezone.utc) + timedelta(minutes=20)
            otp_saved = await self.user_repository.save_user_otp(email=email, otp=otp, busId="1", expireAt=expireAt)

            if otp_saved is False : return (1, 'sending otp code has error')

            email_content = AuthService.get_email(otp, expireAt)
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
def get_auth_service() -> AuthService:
    return AuthService(get_token_service(), get_user_repository(), get_session_repository());