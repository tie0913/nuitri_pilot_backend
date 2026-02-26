from fastapi import FastAPI
import uvicorn
from src.util.logger import get_logger
from src.util.config import get_settings
from src.ctx import context

app = FastAPI(lifespan=context)


from src.user.router import user_router
from src.auth.router import auth_router
from src.wellness.router import wellness_router
from src.suggestion.router import suggestion_router
from src.util.TimezoneMiddleware import TimezoneMiddleware

app.include_router(user_router)
app.include_router(auth_router)
app.include_router(wellness_router)
app.include_router(suggestion_router)

app.add_middleware(TimezoneMiddleware)
@app.get("/")
async def root():
    get_logger().info("This is a log")
    return "Welcome to Nuitri Pilot"

if __name__ == "__main__":
    conf = get_settings()
    uvicorn.run("src.main:app", host="0.0.0.0", port=conf.PORT, reload=True)