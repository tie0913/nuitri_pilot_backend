from functools import lru_cache
from src.auth.token import create_token 
from src.user.otp_repository import OTPRepository
from src.user.user_repository import UserRepository
from src.auth.session_repository import SessionRepository
from datetime import datetime, timedelta, timezone
from src.util.email_sender import send_email
from src.util.mongo import MongoDBPool
from src.util.otp_generator import generate_otp
from src.util.tx_executor import with_txn

AUTH_SERVICE_FORGET_PASSWORD_BUS_ID = "1"
AUTH_SERVICE_SIGN_UP_BUS_ID = "2"

REQUEST_OTP_ALLOWED_LIST = [AUTH_SERVICE_FORGET_PASSWORD_BUS_ID, AUTH_SERVICE_SIGN_UP_BUS_ID]

NOT_MATCHED_TEXT = (1, 'Email and Password are not matched')
class AuthService:
    
    def __init__(self, db):
        self.db = db
    
    #
    # 登录方法
    # 0  :  token
    # 1  : 用户与密码不匹配
    #
    async def signIn(self, email:str, password:str) -> tuple:
        user_repo = UserRepository(self.db)
        sess_repo = SessionRepository(self.db)
        user = await user_repo.get_user_by_email(email)
        if user is not None and password == user['password']:
            user_id = str(user['_id'])
            token = create_token(user_id)
            expire_at = datetime.now(timezone.utc) + timedelta(minutes=15)
            await sess_repo.save_session(user_id = user_id, expire_at = expire_at)
            return (0, token)
        else:
            return NOT_MATCHED_TEXT


    async def signOut(self, user_id:str):
        sess_repo = SessionRepository(self.db)
        await sess_repo.remove_by_user_id(user_id)

    async def get_user_by_email(self, email:str):
        user_repo = UserRepository(self.db)
        return await user_repo.get_user_by_email(email)

    async def confirm_password(self, email:str, otp:str, password:str, biz_id:str) :
        otp_repo = OTPRepository(self.db)
        user_repo = UserRepository(self.db)

        otp_record = await otp_repo.get_otp_by_email_and_bus_id(email, bus_id=biz_id)
        if otp_record is None:
            return (1, 'otp has expired')
        elif otp_record['otp'] != otp:
            return (2, 'otp is invalid')
        elif datetime.now(timezone.utc) > otp_record['expire_at']:
            return (1, 'otp has expired')
        else:
            async def delete_otp_and_update_user():
                await otp_repo.delete_otp(email, bus_id=biz_id)
                return await user_repo.update_password(email=email, password=password)
            
            async def delete_otp_and_create_user():
                await otp_repo.delete_otp(email=email, bus_id=biz_id)
                return await user_repo.create_user(email=email, password=password)

            try:
                if biz_id == AUTH_SERVICE_FORGET_PASSWORD_BUS_ID:
                    await with_txn(self.db, delete_otp_and_update_user)
                    return (0, 'password has been reset')
                elif biz_id == AUTH_SERVICE_SIGN_UP_BUS_ID:
                    await with_txn(self.db, delete_otp_and_create_user)
                    return (0, 'signing up succeed')
            except Exception as e:
                print(e)
                return (3, 'reset password has error')


    async def request_otp(self, email:str, biz_id: str) -> tuple:

        user_repo = UserRepository(self.db)
        otp_repo = OTPRepository(self.db)

        user = await user_repo.get_user_by_email(email)

        if biz_id == AUTH_SERVICE_SIGN_UP_BUS_ID and user is not None:
            return (1, "email exists already")

        elif biz_id == AUTH_SERVICE_FORGET_PASSWORD_BUS_ID and user is None:
            return (1, 'user does not exist')
        elif biz_id in REQUEST_OTP_ALLOWED_LIST:
            print('----------------------Here is Sending OTP-----------------')
            otp = generate_otp(6)
            expire_at = datetime.now(timezone.utc) + timedelta(minutes=20)
            async def reset():
                await otp_repo.delete_otp(email=email, bus_id=biz_id)
                await otp_repo.save_otp(email=email, otp=otp, bus_id=biz_id, expire_at=expire_at)
            try:
                await with_txn(self.db, reset)
                email_title = AuthService.get_email_title(biz_id=biz_id)
                email_content = AuthService.get_email(otp, expire_at, biz_id)
                email_send = send_email(email, email_title, email_content)
                if email_send :
                    return (0, 'otp code has been sent')
                else:
                    return (1, 'sending otp code has error')
            except Exception as e:
                print(e)
                return (1, "saving otp code has error")
        else:
            print('unkown biz id ')
            return (1, "unknown biz id" + str(biz_id))

    @classmethod
    def get_email_title(cls, biz_id) -> str:
        if biz_id == AUTH_SERVICE_FORGET_PASSWORD_BUS_ID:
            return "Reset Your Password - Nutri Pilot"
        elif biz_id == AUTH_SERVICE_SIGN_UP_BUS_ID:
            return "Sign up Your Account - Nutri Pilot"
        else:
            raise Exception("Unrecognized business id")

    @classmethod
    def get_email(cls, opt, expireAt, biz_id) -> str:

        reason = ""
        if biz_id == AUTH_SERVICE_FORGET_PASSWORD_BUS_ID:
            reason = "resetting your password"
        elif biz_id == AUTH_SERVICE_SIGN_UP_BUS_ID:
            reason = "signing up"
        else:
            raise Exception("Unrecognized business id")
        
        email_template = f"""
            Dear User,

                Here is your OTP number for {reason}.
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
    return AuthService(MongoDBPool.get_db());