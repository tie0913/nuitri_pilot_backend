
from datetime import datetime
from src.util.base_repository import BaseRepository


class OTPRepository(BaseRepository):

    def __init__(self, db):
        super().__init__(db)

    def get_collection_name(self) -> str:
        return "otps"

    async def get_otp_by_email_and_bus_id(self, email:str, bus_id:str):
        return await self.find_one({"email":email, "bus_id": bus_id})

     # insert a otp code for a business method by a email
    async def save_otp(self, email:str, otp:str, bus_id:str, expire_at:datetime):
        await self.insert({
                                "email": email,
                                "otp": otp,
                                "bus_id": bus_id,
                                "expire_at": expire_at
                                })

    async def delete_otp(self, email:str, bus_id:str):
        await self.delete_many({"email":email, "bus_id":bus_id})