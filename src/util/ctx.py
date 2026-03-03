from dataclasses import dataclass
from typing import Optional
from contextvars import ContextVar

@dataclass
class RequestContext:
    user_id: Optional[str] = None
    token: Optional[str] = None
    timezone:Optional[str] = None
    uid:Optional[str] = None

_ctx: ContextVar[RequestContext] = ContextVar("request_ctx")

def get_ctx() -> RequestContext:
    return _ctx.get()

def set_ctx(ctx: RequestContext):
    return _ctx.set(ctx)

def reset_ctx(token):
    _ctx.reset(token)
