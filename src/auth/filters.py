# app/deps/auth_guard.py
from typing import Optional, Tuple, AsyncGenerator
from fastapi import Header, HTTPException, status
from fastapi.responses import JSONResponse
from src.util.ctx import RequestContext, get_ctx, _set_ctx, _reset_ctx
from src.auth.token import decode_token
from src.util.json import generate_result

class JWTUserGuard:
    """
    统一拦截器/依赖：
    - 从头部取 token（优先 Authentication，兼容 Authorization: Bearer ...）
    - 验证失败：直接返回 JSON（401），提示“请重新登录”，不抛异常
    - 验证成功：把 user_id / token 写入协程上下文；响应后清理
    - 可用于：整个 APIRouter（dependencies=[Depends(...)]) 或 单个路由
    """
    def __init__(
        self,
        *,
        header_preference: Tuple[str, ...] = ("Authentication", "Authorization"),
    ):
        self.pref = tuple(h.lower() for h in header_preference)

    async def __call__(
        self,
        authentication: Optional[str] = Header(default=None, alias="Authentication"),
        authorization: Optional[str] = Header(default=None, alias="Authorization"),
    ) -> AsyncGenerator[None, None] | JSONResponse:
        # ---- 1) 取 token ----
        token: Optional[str] = None
        for name in self.pref:
            if name == "authentication" and authentication:
                token = authentication.strip()
                break
            if name == "authorization" and authorization:
                v = authorization.strip()
                token = v[7:].strip() if v.lower().startswith("bearer ") else v
                break
        if not token:
            return JSONResponse(
                generate_result((-1, 'Token is missing, please sign in')),
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="api"'},
            )

        user_id = None
        # ---- 2) JWT 验证与解析 —— 
        try:
            decode_res = decode_token(token)
            if decode_res[0] == 0:
                get_ctx().user_id = decode_res[1]['text']
            else:
                raise ValueError("empty_user_id")
        except Exception:
            return JSONResponse(
                generate_result((-1, 'Token is invalid, please sign in')),
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer error="invalid_token"'},
            )

        # ---- 3) 写入协程上下文；请求结束后清理 ----
        async def _gen() -> AsyncGenerator[None, None]:
            ctx = get_ctx()
            ctx.user_id = str(user_id)
            ctx.token = token
            tok = _set_ctx(ctx)
            try:
                print("here is gen " + token)
                yield
            finally:
                _reset_ctx(tok)

        return _gen()
