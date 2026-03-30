
from datetime import datetime, timezone
from functools import lru_cache

from bson import ObjectId
from src.suggestion.agent import get_agent
from src.suggestion.repo import SuggestionRepo
from src.util.mongo import MongoDBPool
from src.wellness.repository import AllergiesRepo, ChronicsRepo, WellnessRepo


class SuggestionService:

    def __init__(self, db):
        self.db = db


    async def delete_by_id(self,id=id):
        suggesstion_repo = SuggestionRepo(self.db)
        await suggesstion_repo.delete_by_id(id=id)

    async def read_suggestion_page(self, user_id, last_id):
        suggestion_repo = SuggestionRepo(self.db)
        return await suggestion_repo.find_suggestions_page(user_id, last_id)

    #path, b64_result['base64_img'], b64_result['base64_thumbnail'], 
    async def get_suggestion(self, img_info:dict, user_id):
        wellness_repo = WellnessRepo(self.db)
        chronics_repo = ChronicsRepo(self.db)
        allergies_repo = AllergiesRepo(self.db)

        wellness = await wellness_repo.get_user_wellness_items_lists(user_id)

        chronics_ids = wellness['chronics'] or []
        allergies_ids = wellness['allergies'] or []

        chronics_objs = await chronics_repo.get_item_list_by_ids(chronics_ids)
        allergies_objs = await allergies_repo.get_item_list_by_ids(allergies_ids)

        chronics_names = list(map(lambda x : x['name'], chronics_objs))
        allergies_names = list(map(lambda x : x['name'], allergies_objs))

        agent = get_agent()
        suggestion = await agent.get(img_info['base64_img'], chronics_names, allergies_names)

        suggestion_repo = SuggestionRepo(self.db)

        print(suggestion)

        if suggestion['code'] == 1 :
            return (1, "The picture cannot be recognized")
        else :
            record = {
                "mark": suggestion["mark"],
                "feedback": suggestion["feedback"],
                "recommendation": suggestion["recommendation"],
                "user_id": ObjectId(user_id),
                "thumbnail":img_info['base64_thumbnail'],
                "path" : img_info['path'],
                "time": datetime.now(timezone.utc)
            }

            res = await suggestion_repo.save(record)
            return (0, res)

@lru_cache
def get_suggestion_service():
    return SuggestionService(MongoDBPool.get_db())
