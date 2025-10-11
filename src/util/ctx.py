from dataclasses import dataclass
from typing import Optional
from contextvars import ContextVar

@dataclass
class RequestContext:
    user_id: Optional[str] = None
    token: Optional[str] = None

_ctx: ContextVar[RequestContext] = ContextVar("request_ctx", default=RequestContext())

def get_ctx() -> RequestContext:
    return _ctx.get()

def _set_ctx(ctx: RequestContext):
    return _ctx.set(ctx)

def _reset_ctx(token):
    _ctx.reset(token)

def request_user_id():
    user_id = _ctx.get().user_id
    if not user_id:
        raise RuntimeError("You should have use filter for your method")
    return user_id
