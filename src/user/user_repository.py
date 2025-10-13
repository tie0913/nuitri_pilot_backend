from src.util.base_repository import BaseRepository

class UserRepository(BaseRepository):

    def __init__(self, db):
        super().__init__(db)
    
    def get_collection_name(self) -> str:
        return "users"

    async def get_user_by_email(self, email:str):
        return await self.find_one({"email": email})

    async def update_password(self, email:str, password:str):
        await self.update_one({"email":email}, {"$set": {"password":password}})
