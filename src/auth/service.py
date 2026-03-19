from functools import lru_cache
from src.auth.token import create_token 
from src.user.otp_repository import OTPRepository
from src.user.user_repository import UserRepository
from src.auth.session_repository import SessionRepository
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from src.util.date_format_util import format_time
from src.util.email_sender import send_email
from src.util.mongo import MongoDBPool
from src.util.otp_generator import generate_otp
from src.util.tx_executor import with_txn
from src.util.ctx import get_ctx

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
            expire_at = datetime.now(timezone.utc) + timedelta(days=10)
            uid = get_ctx().uid
            await sess_repo.save_session(user_id = user_id, uid=uid, expire_at = expire_at)
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
        if otp_record is None and biz_id == AUTH_SERVICE_FORGET_PASSWORD_BUS_ID:
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
                return (3, 'reset password has error')


    async def request_otp(self, email:str, biz_id: str) -> tuple:

        user_repo = UserRepository(self.db)
        otp_repo = OTPRepository(self.db)

        user = await user_repo.get_user_by_email(email)

        prev_otp = await otp_repo.get_otp_by_email_and_bus_id(email=email, bus_id=biz_id)

        if user is None and biz_id == AUTH_SERVICE_FORGET_PASSWORD_BUS_ID:
            return (1, "We cannot send OTP to this mailbox")
        elif user is not None and biz_id == AUTH_SERVICE_SIGN_UP_BUS_ID:
            return (1, "This email has been registed")
        elif prev_otp is not None:
            user_timezone = get_ctx().timezone
            expire_at_user_local = prev_otp['expire_at'].astimezone(ZoneInfo(user_timezone))
            return (1, f"You have sent an email before,\n don't send email again before {format_time(expire_at_user_local)}")
        elif biz_id in REQUEST_OTP_ALLOWED_LIST:
            print('----------------------Here is Sending OTP-----------------')
            otp = generate_otp(6)
            expire_at = datetime.now(timezone.utc) + timedelta(minutes=10)
            async def reset():
                await otp_repo.delete_otp(email=email, bus_id=biz_id)
                await otp_repo.save_otp(email=email, otp=otp, bus_id=biz_id, expire_at=expire_at)
            try:
                await with_txn(self.db, reset)
                email_title = AuthService.get_email_title(biz_id=biz_id)
                user_timezone = get_ctx().timezone
                expire_at_user_local = expire_at.astimezone(ZoneInfo(user_timezone))
                email_content = AuthService.get_email(otp, expire_at_user_local, biz_id)
                email_send = send_email(email, email_title, email_content)
                if email_send :
                    return (0, 'otp code has been sent')
                else:
                    return (1, 'sending otp code has error')
            except Exception as e:
                return (1, "saving otp code has error")
        else:
            print('unkown biz id ')
            return (1, "unknown operation code")

    @classmethod
    def get_email_title(cls, biz_id) -> str:
        if biz_id == AUTH_SERVICE_FORGET_PASSWORD_BUS_ID:
            return "Reset Your Password - Nutri Pilot"
        elif biz_id == AUTH_SERVICE_SIGN_UP_BUS_ID:
            return "Sign up Your Account - Nutri Pilot"
        else:
            raise Exception("Unrecognized business id")

    @classmethod
    def get_email(cls, otp, expireAt, biz_id) -> str:
        reason = ""
        if biz_id == AUTH_SERVICE_FORGET_PASSWORD_BUS_ID:
            reason = "Reseting Password"
        elif biz_id == AUTH_SERVICE_SIGN_UP_BUS_ID:
            reason = "Signing Up"
        else:
            raise Exception("Unrecognized business id")
        return f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="UTF-8">
            <title>NutriPilot</title>
            </head>

            <body style="margin:0; padding:0; background-color:#EAF4EA; font-family:Arial, sans-serif;">

            <table width="100%" cellpadding="0" cellspacing="0" border="0">
            <tr>
            <td align="center">

            <!-- Container -->
            <table width="600" cellpadding="0" cellspacing="0" border="0" 
            style="background:#ffffff; margin:40px auto; border-radius:16px; overflow:hidden; box-shadow:0 8px 28px rgba(0,0,0,0.12);">

            <!-- Header -->
            <tr>
            <td style="background:#F7FBF7; padding:32px; text-align:center; border-bottom:1px solid #E0E0E0;">
            <img src="cid:logo" alt="Nutri Pilot" width="100" style="display:block; margin:auto;">
            </td>
            </tr>

            <!-- Content -->
            <tr>
            <td style="padding:48px 48px 24px 48px; text-align:center;">

            <h2 style="margin:0; color:#1B5E20; font-size:26px; font-weight:700;">
            Your {reason} OTP Code
            </h2>

            <p style="margin:20px 0 30px 0; color:#555; font-size:16px;">
            Use the code below to continue your healthy journey with NutriPilot.
            </p>

            <!-- Code Box -->
            <div style="
              margin:30px auto;
              padding:22px 30px;
              display:inline-block;
              background:#ffffff;
              border-radius:12px;
              border:2px solid #66BB6A;
              font-size:36px;
              letter-spacing:8px;
              color:#1B5E20;
              font-weight:bold;
              box-shadow:0 4px 12px rgba(0,0,0,0.08);
            ">
            {otp}
            </div>

            <p style="margin-top:32px; color:#777; font-size:14px;">
            This code will expire at {format_time(expireAt)}
            </p>

            </td>
            </tr>

            <!-- Footer -->
            <tr>
            <td style="padding:24px; text-align:center; font-size:12px; color:#999; background:#FAFAFA;">
            NutriPilot — Your AI Nutrition Companion<br>
            All times are shown in your local time.
            </td>
            </tr>

            </table>

            </td>
            </tr>
            </table>

            </body>
            </html>
        """    
        
@lru_cache
def get_auth_service() -> AuthService:
    return AuthService(MongoDBPool.get_db())



class SessionService:

    def __init__(self, db):
        self.db = db


    async def is_user_still_online(self, user_id, uid):
        sess_repo = SessionRepository(self.db)
        session = await sess_repo.get_by_user_id(user_id=user_id)
        print('--------------session------------------')
        print(session)
        if session is None:
            return (101, 'session expires, please sign in again')
        else:
            now = datetime.now(timezone.utc)
            if uid != session['uid']:
                return (102, 'You account signed in on other devices')
            elif now > session['expire_at']:
                return (101, 'session expires, please sign in again')
            else:
                return (0, True)


@lru_cache
def get_session_service() -> SessionService:
    return SessionService(MongoDBPool.get_db())