from functools import lru_cache
from src.user.bson_util import convert_id
from src.wellness.repository import ChronicsRepo, AllergiesRepo, WellnessRepo
from src.util.ctx import request_user_id
from src.util.mongo import MongoDBPool

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
            "chronics":convert_id(chronicList),
            "selectedIds": wellness['chronics']
        }

@lru_cache
def get_wellness_service() -> WellnessService:
    return WellnessService(MongoDBPool.get_db())