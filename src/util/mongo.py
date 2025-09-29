
# This is the mongo client definition
# We are supposed to use one client instance in this whole backend server
# because all the coroutine will share it thus we will not consume too much resources

from motor.motor_asyncio import AsyncIOMotorClient
from src.util.config import get_settings
from src.util.logger import get_logger

class MongoDBPool:

    client: AsyncIOMotorClient = None
    db = None

    @classmethod
    async def connect_to_db(cls):
        if cls.client is None:
            cls.client = AsyncIOMotorClient(get_settings().getMongoDBUrl())
            cls.db = cls.client[get_settings().MONGO_SCHEMA_NAME]

    @classmethod
    async def close(cls):
        if cls.client is not None:
            cls.client.close()
            cls.client = None
            cls.db = None

    @classmethod
    def get_db(cls):
        return MongoDBPool.db