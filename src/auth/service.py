from functools import lru_cache
from src.auth.token import TokenService, get_token_service
from src.user.repository import UserRepository, get_user_repository
from src.auth.repository import SessionRepository, get_session_repository

from datetime import datetime, timedelta, timezone

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

        
@lru_cache
def get_auth_service() -> AuthService:
    return AuthService(get_token_service(), get_user_repository(), get_session_repository());