from starlette.middleware.base import BaseHTTPMiddleware
from src.util.ctx import RequestContext, set_ctx, reset_ctx

class ContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        ctx = RequestContext()
        token = set_ctx(ctx)
        try:
            response = await call_next(request)
            return response
        finally:
            reset_ctx(token)