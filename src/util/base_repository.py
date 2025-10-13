from abc import ABC, abstractmethod

class BaseRepository(ABC):

    def __init__(self, db):
        self.collection = db[self.get_collection_name()]


    @abstractmethod
    def get_collection_name(self) -> str :  
        pass

    async def insert(self, object:dict):
        await self.collection.insert_one(object)

    async def update_one(self, param:dict, updated:dict):
        await self.collection.update_one(param, updated)

    async def delete_many(self, param:dict):
        await self.collection.delete_many(param)

    async def find_one(self, param:dict):
        return await self.collection.find_one(param)