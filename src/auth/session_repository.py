from bson import ObjectId
from src.util.base_repository import BaseRepository

class SessionRepository(BaseRepository):

    def __init__(self, db):
        super().__init__(db)
    
    def get_collection_name(self) -> str:
        return "sessions"

    # 这个方法保存登录用户的session信息，未来可以扩展相关的字段
    async def save_session(self, user_id, uid, expire_at):
        self.collection.update_one(
            {"user_id": ObjectId(user_id)},
            {
                "$set": {
                    "uid": uid,
                    "expire_at": expire_at
                }
            },
            upsert=True
        )
  

    async def remove_by_user_id(self, user_id):
        await self.delete_many({"user_id":ObjectId(user_id)})


    async def get_by_user_id(self, user_id):
        return await self.find_one({"user_id": ObjectId(user_id)})
