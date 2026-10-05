import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

# Importing models registers their DDL on Base.metadata so create_all picks them up.
from chat_backend import models  # noqa: F401
from chat_backend.db import Base


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
