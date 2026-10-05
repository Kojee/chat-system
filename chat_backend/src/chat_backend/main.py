import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from .auth import CookieAuthMiddleware
from .config import settings
from .db import AsyncSessionLocal, Base, engine
from .persistence import seed_default_agent_settings
from .routes import router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        await seed_default_agent_settings(session)
        await session.commit()
    async with AsyncPostgresSaver.from_conn_string(settings.chatdb_dsn) as checkpointer:
        await checkpointer.setup()
        app.state.checkpointer = checkpointer
        yield


app = FastAPI(lifespan=lifespan, title="Chat Backend")
app.add_middleware(CookieAuthMiddleware)
app.include_router(router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def run() -> None:
    uvicorn.run(
        "chat_backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=False,
    )
