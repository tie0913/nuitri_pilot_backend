from functools import lru_cache
from datetime import datetime, timedelta, timezone

from src.util.email_sender import send_email
from src.user.repository import UserRepository, get_user_repository
from src.util.otp_generator import generate_otp




class UserService:

    def __init__(self, repository: UserRepository):
        self.repository = repository


 
    
@lru_cache
def get_user_service() -> UserService:
    repository = get_user_repository()
    return UserService(repository)