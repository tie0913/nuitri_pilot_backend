from abc import ABC, abstractmethod

class BaseRepository(ABC):

    def __init__(self, db):
        self.collection = db[self.get_collection_name()]


    @abstractmethod
    def get_collection_name(self) -> str :  
        pass

    async def insert(self, object:dict):
        return await self.collection.insert_one(object)

    async def update_one(self, param:dict, updated:dict, upsert:bool = False):
        await self.collection.update_one(param, updated, upsert)

    async def delete_many(self, param:dict):
        await self.collection.delete_many(param)

    async def find_one(self, param:dict, with_id:bool = False):
        if with_id:
            return await self.collection.find_one(param)
        else:
            return await self.collection.find_one(param, {'_id': 0})
    
    async def find_many(self, param:dict):
        cursor = self.collection.find(param)
        return await cursor.to_list(length=None)

    async def find_all(self):
        cursor = self.collection.find({})
        return await cursor.to_list(length=None)
    
    async def find_page(self, param:dict, sort, page:int =10):
        cursor = self.collection.find(param).sort(sort).limit(page);
        return await cursor.to_list(length=None)