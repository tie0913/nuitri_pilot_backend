from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.util.mongo import MongoDBPool

from src.util.logger import get_logger

# This is the backend server context
# we use this method to maintain all kinds of resources
@asynccontextmanager
async def context(ap:FastAPI):

    logger = get_logger()
    logger.info("Start initing MongoDB Connections")
    await MongoDBPool.connect_to_db()
    logger.info("MongoDB Connections initiation has been done")

    yield
    logger.info("Start closing MongoDB Connections")
    MongoDBPool.close()
    logger.info("MongoDB Connections distinguish has been done")

