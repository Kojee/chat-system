import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from . import seed
from .auth import AuthHeadersMiddleware
from .config import settings
from .mcp_app import mcp

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed.run()
    async with mcp.session_manager.run():
        yield


app = FastAPI(lifespan=lifespan, title="User MCP Server")
app.add_middleware(AuthHeadersMiddleware)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.mount("/mcp", mcp.streamable_http_app())


def run() -> None:
    uvicorn.run(
        "mcp_user_server.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
