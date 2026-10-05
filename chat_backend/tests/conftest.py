import os

# Settings require OPENAI_API_KEY at import. No test here calls the model (the redteam
# suite talks to the backend running in Docker, which has its own key), so a placeholder
# keeps the suite runnable without a real key. Must be set before chat_backend is imported.
os.environ.setdefault("OPENAI_API_KEY", "test-key-not-used")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from testcontainers.postgres import PostgresContainer  # noqa: E402

# Importing models registers their DDL on Base.metadata so create_all picks them up.
from chat_backend import models  # noqa: F401, E402
from chat_backend.db import Base  # noqa: E402


def pytest_addoption(parser):
    parser.addoption(
        "--redteam",
        action="store_true",
        default=False,
        help="run red-team tests against the running stack (`make up`; paid OpenAI calls)",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--redteam"):
        return
    skip = pytest.mark.skip(reason="needs --redteam to run")
    for item in items:
        if item.get_closest_marker("redteam"):
            item.add_marker(skip)


@pytest_asyncio.fixture(scope="session")
async def postgres_url():
    """One Postgres container per test session (image is cached after first pull)."""
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        yield pg.get_connection_url()


@pytest_asyncio.fixture(scope="session")
async def engine(postgres_url):
    eng = create_async_engine(postgres_url)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Per-test AsyncSession bound to a connection-scoped transaction that's rolled back at teardown."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        Session = async_sessionmaker(bind=conn, expire_on_commit=False, class_=AsyncSession)
        async with Session() as s:
            yield s
        await trans.rollback()
