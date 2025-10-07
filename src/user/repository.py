from functools import lru_cache
from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase
from src.util.mongo import MongoDBPool
from datetime import datetime
from src.util.json import to_json

from src.util.logger import get_logger
class UserRepository:

    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    async def get_user_by_email(self, email:str):
        collection = self.db['users']
        person = await collection.find_one({"email": email})
        return to_json(person)

    # insert a otp code for a business method by a email
    async def save_user_otp(self, email:str, otp:str, busId:str, expireAt:datetime) -> bool:
        logger = get_logger()
        logger.info("expireAt=" + str(expireAt))
        res = None
        async with await self.db.client.start_session() as session:
            async with session.start_transaction():
                await self.db['otps'].delete_many({"email":email, "busId":busId})
                res = await self.db['otps'].insert_one({
                                                "email": email,
                                                "otp": otp,
                                                "busId": busId,
                                                "expireAt": expireAt
                                                })
                
        if res is None:
            return False
        else :
            return res.acknowledged

    
    async def get_otp_by_email_and_bus_id(self, email:str, bus_id:str) -> str:
        user = await self.db['otps'].find_one({"email":email, "busId": bus_id})
        return to_json(user)
    async def get_otp_by_email_and_bus_id(self, email:str, bus_id:str):
        otp = await self.db['otps'].find_one({"email":email, "busId": bus_id})
        return to_json(otp)

    async def update_password_and_delete_otp(self, email:str, bus_id:str, password:str):

        res = None
        async with await self.db.client.start_session() as session:
            async with session.start_transaction():
                await self.db['otps'].delete_many({"email":email, "busId":bus_id})
                res = await self.db['users'].update_one({"email":email}, {"$set": {"password":password}})
        
        if res is None:
            return False
        else:
            return res.acknowledged

@lru_cache
def get_user_repository() -> UserRepository:
    db = MongoDBPool.get_db()
    return UserRepository(db)