from fastapi import FastAPI

from src.util.logger import get_logger
app = FastAPI()

@app.get("/")
async def root():
    get_logger().info("This is a log")
    return "Welcome to Nuitri Pilot"