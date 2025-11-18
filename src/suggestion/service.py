
from functools import lru_cache
from src.suggestion.agent import get_agent
from src.util.mongo import MongoDBPool
from src.wellness.repository import AllergiesRepo, ChronicsRepo, WellnessRepo


class SuggestionService:

    def __init__(self, db):
        self.db = db


    async def get_suggestion(self, base64_img, user_id):
        wellness_repo = WellnessRepo(self.db)
        chronics_repo = ChronicsRepo(self.db)
        allergies_repo = AllergiesRepo(self.db)

        wellness = await wellness_repo.get_user_wellness_items_lists(user_id)

        chronics_ids = wellness['chronics']
        allergies_ids = wellness['allergies']

        chronics_objs = await chronics_repo.get_item_list_by_ids(chronics_ids)
        allergies_objs = await allergies_repo.get_item_list_by_ids(allergies_ids)

        chronics_names = list(map(lambda x : x['name'], chronics_objs))
        allergies_names = list(map(lambda x : x['name'], allergies_objs))

        agent = get_agent()
        response = await agent.get(base64_img, chronics_names, allergies_names)
        return response


@lru_cache
def get_suggestion_service():
    return SuggestionService(MongoDBPool.get_db())
