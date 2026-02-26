from starlette.middleware.base import BaseHTTPMiddleware
from src.util.ctx import get_ctx

class TimezoneMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        tz = request.headers.get("X-Timezone")
        if tz:
            get_ctx().timezone = tz
        else:
            get_ctx().timezone = "UTC"

        response = await call_next(request)
        return response