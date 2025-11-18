

from bson import ObjectId
from src.util.base_repository import BaseRepository


class SuggestionRepo(BaseRepository):

    def __init__(self, db):
        super().__init__(db)

    def get_collection_name(self):
        return "suggestions"

    async def save(self, record):
        result = await self.insert(record)
        record['_id'] = result.inserted_id
        return record

    async def find_page(self, user_id, last_id):
        condition = {'user_id': ObjectId(user_id)}
        if last_id is not None:
            condition['_id'] = {'$lt': ObjectId(last_id)}

        return await self.find_page(condition, {'_id':-1})
