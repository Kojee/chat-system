from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from .context import current_api_key, current_user_id


class AuthHeadersMiddleware(BaseHTTPMiddleware):
    """
    Validates that an API key and a user id are present in the headers of the requests. 
    """

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/mcp"):
            return await call_next(request)

        api_key = request.headers.get("x-api-key")
        raw_user_id = request.headers.get("x-user-id")
        if not api_key or not raw_user_id:
            return JSONResponse(
                {"error": "missing X-Api-Key or X-User-Id header"}, status_code=401
            )
        try:
            user_id = int(raw_user_id)
        except ValueError:
            return JSONResponse(
                {"error": "X-User-Id must be an integer"}, status_code=401
            )

        api_token = current_api_key.set(api_key)
        user_token = current_user_id.set(user_id)
        try:
            return await call_next(request)
        finally:
            current_api_key.reset(api_token)
            current_user_id.reset(user_token)
