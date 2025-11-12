from functools import lru_cache
from src.util.json import convert_id
from src.wellness.repository import ChronicsRepo, AllergiesRepo, WellnessRepo
from src.util.ctx import request_user_id
from src.util.mongo import MongoDBPool
from pymongo.errors import DuplicateKeyError

class WellnessService:

    def __init__(self, db):
        self.db = db

    async def get_user_wellness(self, catalogName):
        item_repo = self.get_wellness_item_repo(catalogName)
        item_list = await item_repo.get_item_list()
        wellnessRepo = WellnessRepo(self.db)
        wellness = await wellnessRepo.get_user_wellness_items_lists(request_user_id())
        return {
            "items": convert_id(item_list),
            "selectedIds": wellness[catalogName]
        }

    async def add_wellness_catalog_item(self, catalogName, name):
        repo = self.get_wellness_item_repo(catalogName)
        try:
            return await repo.create_new_item(name)
        except DuplicateKeyError as e:
            return await repo.get_item_by_name(name)
    
    async def save_user_selected_wellness_item_ids(self, catalogName, selectedIds):
        wellnessRepo = WellnessRepo(self.db)
        await wellnessRepo.save_user_selected_wellness_item_ids(request_user_id(), catalogName, selectedIds)

    def get_wellness_item_repo(self, catalogName):
        repo = None
        if catalogName == "chronics":
            repo = ChronicsRepo(self.db)
        elif catalogName == "allergies":
            repo = AllergiesRepo(self.db)
        else:
            raise Exception("unsupported catalogName")
        return repo

@lru_cache
def get_wellness_service() -> WellnessService:
    return WellnessService(MongoDBPool.get_db())