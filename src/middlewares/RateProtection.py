from http.client import HTTPException

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone

from src.suggestion.repo import Cooldown
from src.util.ctx import get_ctx
from src.util.mongo import MongoDBPool

class RateProtection(BaseHTTPMiddleware):

    def __init__(self, app):
        super().__init__(app)
        self.path_dict = {"/suggestion/ask": 30}

    async def dispatch(self, request, call_next):
        cooldown = Cooldown(MongoDBPool.get_db())
        key = request.url.path + str(get_ctx().user_id)
        need_rate_control = request.url.path in self.path_dict
        start_at = datetime.now(timezone.utc)
        locked = False
        try:
            if need_rate_control:
                locked = await cooldown.lock(key=key, start_at=start_at)
                if locked is False:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "message": "You visited this API too much, please wait for at least one minute"
                        }
                    )
            return await call_next(request)
        finally:
            if need_rate_control and locked:
                await cooldown.release(key=key, start_at=start_at, now=datetime.now(timezone.utc), cd=30);
