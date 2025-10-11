
from functools import lru_cache

from bson import ObjectId

from src.util.mongo import MongoDBPool


class SessionRepository:

    def __init__(self, db):
        self.db = db
    

    # 这个方法保存登录用户的session信息，未来可以扩展相关的字段
    async def save_session(self, user_id, expire_at):
        await self.db['sessions'].insert_one({
            "user_id": ObjectId(user_id),
            "expire_at": expire_at
        })

    async def remove_by_user_id(self, user_id):
        await self.db['session'].delete_many({"user_id":ObjectId(user_id)})


@lru_cache
def get_session_repository() -> SessionRepository :
    db = MongoDBPool.get_db()
    return SessionRepository(db)