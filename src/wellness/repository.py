from src.util.base_repository import BaseRepository
from bson import ObjectId

class ChronicsRepo(BaseRepository):

    def __init__(self, db):
        super().__init__(db)

    def get_collection_name(self):
        return 'chronics'

    async def get_item_list(self):
        return await self.find_all()

    async def create_new_item(self, name):
        doc = {"name": name}
        result = await self.insert(doc)
        doc['_id'] = result.inserted_id
        return doc
    
    async def get_item_by_name(self, name):
        return await self.find_one({"name": name}, with_id=True)

    async def get_item_list_by_ids(self, ids):
        return await self.find_many({
            "_id":{"$in":[ObjectId(id) for id in ids]}
        })


class AllergiesRepo(BaseRepository):
     
    def __init__(self, db):
        super().__init__(db)

    def get_collection_name(self):
        return 'allergies'

    async def get_item_list(self):
         return await self.find_all()

    async def create_new_item(self, name):
        doc = {"name": name}
        result = await self.insert(doc)
        doc['_id'] = result.inserted_id
        return doc

    async def get_item_by_name(self, name):
        return await self.find_one({"name": name}, with_id=True)

    async def get_item_list_by_ids(self, ids):
        return await self.find_many({
            "_id":{"$in":[ObjectId(id) for id in ids]}
        })



class WellnessRepo(BaseRepository):

    def __init__(self, db):
        super().__init__(db)

    def get_collection_name(self):
        return "wellness"

    async def get_user_wellness_items_lists(self, user_id):
        return await self.find_one({"user_id": ObjectId(user_id)})

    async def save_user_selected_wellness_item_ids(self, user_id, catalogName, selectedIds):
        await self.update_one({"user_id": ObjectId(user_id)}, {"$set": {catalogName: selectedIds}}, upsert=True)
        