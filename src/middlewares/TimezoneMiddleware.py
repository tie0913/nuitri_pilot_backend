from starlette.middleware.base import BaseHTTPMiddleware
from src.util.ctx import get_ctx 

class TimezoneMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        ctx = get_ctx()
        ctx.timezone = request.headers.get("X-Timezone", "UTC")
        ctx.uid = request.headers.get("UID")
        return await call_next(request)