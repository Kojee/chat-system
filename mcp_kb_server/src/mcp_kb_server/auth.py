from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class AuthHeadersMiddleware(BaseHTTPMiddleware):
    """
    Validates that an API key is present in the headers of the requests. 
    """

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/mcp"):
            return await call_next(request)
        # Just validate the presence of the key for now 
        # In the future, we could validate against a list of valid keys
        if not request.headers.get("x-api-key"):
            return JSONResponse(
                {"error": "missing X-Api-Key header"}, status_code=401
            )
        return await call_next(request)
