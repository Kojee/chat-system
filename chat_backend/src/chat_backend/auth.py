from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

USER_ID_COOKIE = "user_id"
_PROTECTED_PREFIXES = ("/chats",)


class CookieAuthMiddleware(BaseHTTPMiddleware):
    """
    Validates presence of the `user_id` cookie on chat routes.

    The login endpoint sets the cookie; everything under /chats requires it.
    No actual validation of the value (matches the prototype's mocked-auth posture).
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if not any(path.startswith(p) for p in _PROTECTED_PREFIXES):
            return await call_next(request)
        if not request.cookies.get(USER_ID_COOKIE):
            return JSONResponse(
                {"error": f"missing {USER_ID_COOKIE} cookie; call /login first"},
                status_code=401,
            )
        return await call_next(request)
