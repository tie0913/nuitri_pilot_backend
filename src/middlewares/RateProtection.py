from http.client import HTTPException

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timezone, timedelta

from src.suggestion.repo import Cooldown
from src.util.ctx import get_ctx
from src.util.mongo import MongoDBPool

class RateProtection(BaseHTTPMiddleware):

    def __init__(self, app):
        super().__init__(app)
        self.path_dict = {"/suggestion/ask": 30}

    async def dispatch(self, request, call_next):
        cooldown = Cooldown(MongoDBPool.get_db())
        key = str(get_ctx().user_id) + ":" + request.url.path
        need_rate_control = request.url.path in self.path_dict
        start_at = datetime.now(timezone.utc)
        cd = self.path_dict[request.url.path]
        expire_at = start_at + timedelta(seconds=cd)
        locked = False
        try:
            if need_rate_control:
                locked = await cooldown.lock(key=key, start_at=start_at, expire_at=expire_at)
                if locked is False:
                    return JSONResponse(
                        status_code=429,
                        content={
                            "message": f"You may request this service 1 time per {cd} seconds"
                        }
                    )
            return await call_next(request)
        except Exception:
            if need_rate_control:
                cooldown.release(key=key)
