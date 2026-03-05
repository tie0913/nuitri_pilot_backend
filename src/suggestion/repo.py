
from datetime import timedelta, datetime
from pymongo import ReturnDocument
from bson import ObjectId
from src.util.base_repository import BaseRepository

class Cooldown(BaseRepository):

    def __init__(self, db):
        super().__init__(db)

    def get_collection_name(self):
        return "cooldowns"
    
    async def lock(self, key, start_at:datetime) -> bool:
        doc = await self.collection.find_one_and_update(
            {"_id": key},
            {
                "$setOnInsert":{
                    "start_at": start_at
                }
            },
            upsert=True,
            return_document=ReturnDocument.BEFORE
        )
        return doc is None
    
    async def release(self, key, start_at: datetime, now: datetime, cd):

        expire_at = max(start_at + timedelta(seconds=cd), now)

        await self.collection.update_one(
            {"_id": key},
            {
                "$set":{"expire_at": expire_at}
            }
        )

class SuggestionRepo(BaseRepository):

    def __init__(self, db):
        super().__init__(db)

    def get_collection_name(self):
        return "suggestions"

    async def save(self, record):
        result = await self.insert(record)
        record['_id'] = result.inserted_id
        return record

    async def find_suggestions_page(self, user_id, last_id):
        condition = {'user_id': ObjectId(user_id)}
        if last_id is not None:
            condition['_id'] = {'$lt': ObjectId(last_id)}
        return await self.find_page(condition, {'_id':-1})

    async def delete_by_id(self, id):
        await self.delete_by_primary_key({'_id': ObjectId(id)})