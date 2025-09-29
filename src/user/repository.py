from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.util.mongo import MongoDBPool

class UserRepository:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.collection = db["users"]

    async def get_user_by_email(self, email:str):
        person = await self.collection.find_one({"email": email})
        return person


def get_user_repository(db = Depends(MongoDBPool.get_db)) -> UserRepository:
    return UserRepository(db)