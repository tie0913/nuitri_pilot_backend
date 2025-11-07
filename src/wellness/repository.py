from src.util.base_repository import BaseRepository
from bson import ObjectId

class ChronicsRepo(BaseRepository):

    def __init__(self, db):
          super().__init__(db)

    def get_collection_name(self):
         return 'chronics'

    async def get_chronic_list(self):
         return await self.find_all()
    



class AllergiesRepo(BaseRepository):
     
    def __init__(self, db):
        super().__init__(db)

    def get_collection_name(self):
        return 'allergies'

    async def get_allergies_list(self):
         return await self.find_all()

        


class WellnessRepo(BaseRepository):

    def __init__(self, db):
        super().__init__(db)

    def get_collection_name(self):
        return "wellness"

    async def get_user_wellness_items_lists(self, user_id):
        return await self.find_one({"user_id": ObjectId(user_id)})