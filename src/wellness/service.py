from functools import lru_cache
from src.user.bson_util import convert_id
from src.wellness.repository import ChronicsRepo, AllergiesRepo, WellnessRepo
from src.util.ctx import request_user_id
from src.util.mongo import MongoDBPool
from pymongo.errors import DuplicateKeyError

class WellnessService:

    def __init__(self, db):
        self.db = db


    async def get_user_wellness(self):
        chronicsRepo = ChronicsRepo(self.db)
        allergiesRepo = AllergiesRepo(self.db)
        wellnessRepo = WellnessRepo(self.db)
        chronicList = await chronicsRepo.get_chronic_list()
        allergyList = await allergiesRepo.get_allergies_list()
        wellness = await wellnessRepo.get_user_wellness_items_lists(request_user_id())
        return {
            "chronicList": convert_id(chronicList),
            "allergyList": allergyList,
            "wellness": wellness
        }

    async def get_user_chronics(self):
        chronicsRepo = ChronicsRepo(self.db)
        chronicList = await chronicsRepo.get_chronic_list()
        wellnessRepo = WellnessRepo(self.db)
        wellness = await wellnessRepo.get_user_wellness_items_lists(request_user_id())
        return {
            "items":convert_id(chronicList),
            "selectedIds": wellness['chronics']
        }
    
    async def get_user_allergies(self):
        allergiesRepo = AllergiesRepo(self.db)
        wellnessRepo = WellnessRepo(self.db)
        allergies = await allergiesRepo.get_allergies_list()
        wellness = await wellnessRepo.get_user_wellness_items_lists(request_user_id())
        return {
            "items": convert_id(allergies),
            "selectedIds": wellness['allergies']
        }

    async def add_wellness_catalog_item(self, catalogName, name):

        repo = None
        if catalogName == "chronics":
            repo = ChronicsRepo(self.db)
        elif catalogName == "allergies":
            repo = AllergiesRepo(self.db)
        else:
            raise Exception("unsupported catalogName")

        try:
            return await repo.create_new_item(name)
        except DuplicateKeyError as e:
            return await repo.get_item_by_name(name)

@lru_cache
def get_wellness_service() -> WellnessService:
    return WellnessService(MongoDBPool.get_db())