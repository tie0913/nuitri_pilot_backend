from fastapi import FastAPI
import uvicorn
from util.logger import get_logger
from util.config import get_settings
app = FastAPI()

@app.get("/")
async def root():
    get_logger().info("This is a log")
    return "Welcome to Nuitri Pilot"

if __name__ == "__main__":
    conf = get_settings()
    uvicorn.run("main:app", port=conf.PORT, reload=True)