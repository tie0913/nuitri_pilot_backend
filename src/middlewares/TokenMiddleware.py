from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.auth.service import get_session_service
from src.auth.token import decode_token
from src.util.ctx import get_ctx


class TokenMiddleware(BaseHTTPMiddleware):

    def __init__(self, app):
        super().__init__(app)
        self.path_set = {
            "/suggestion/ask",
            "/suggestion/get",
            "/suggestion/delete_by_id",

            "/wellness/get_user_wellness_and_items",
            "/wellness/add_wellness_catalog_item",
            "/wellness/save_user_selected_ids",

            "/auth/sign-out",
            "/auth/me",
        }
        #self.exclude_paths = set(exclude_paths or ["/login", "/docs", "/openapi.json"])

    async def dispatch(self, request: Request, call_next):
        # ---- 0) 白名单路径 ----
        if request.url.path  in self.path_set:

            error = JSONResponse(
                status_code=401,
                content={
                    "message": "Token is invalid, please sign in"
                }
            )

            # ---- 1) 获取 ctx（由上游 middleware 保证存在）----
            ctx = get_ctx()

            # ---- 2) 读取 uid ----
            uid = request.headers.get("uid")
            if not uid:
                print("UID")
                return error

            # ---- 3) 解析 Authorization ----
            token = request.headers.get("Authorization")
            if not token:
                print("TOKEN")
                return error

            # ---- 4) JWT 验证 ----
            try:
                decode_res = decode_token(token)

                if decode_res[0] != 0:
                    print("TOKEN DECODE")
                    return error

                user_id = decode_res[1]["text"]

                # ---- 5) 在线校验（防挤下线）----
                is_online = await get_session_service().is_user_still_online(
                    user_id=user_id,
                    uid=uid,
                )

                if is_online[0] != 0:

                    print("TOKEN is deleted")
                    return JSONResponse(
                        status_code=401,
                        content={"detail": is_online[1]},
                    )

                # ---- 6) 写入 ctx（这是你这个 middleware 唯一的“副作用”）----
                ctx.user_id = user_id
                ctx.token = token
                ctx.uid = uid

            except Exception:
                print("OTHEr")
                return error

        # ---- 7) 放行 ----
        return await call_next(request)
