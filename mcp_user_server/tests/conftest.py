import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from mcp_user_server.db import Base

from .factories import UserFactory


@pytest.fixture(scope="session")
def engine():
    """One Postgres container per test session — schema only, no data."""
    with PostgresContainer("postgres:16-alpine", driver="psycopg") as pg:
        eng = create_engine(pg.get_connection_url(), pool_pre_ping=True)
        Base.metadata.create_all(eng)
        yield eng
        eng.dispose()


@pytest.fixture(scope="session")
def session_local(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def patch_session_local(monkeypatch, session_local):
    """Redirect the tool's SessionLocal to the test container."""
    monkeypatch.setattr("mcp_user_server.mcp_app.SessionLocal", session_local)


@pytest.fixture(autouse=True)
def bind_factories(session_local):
    """Wire the test sessionmaker into factory_boy at the start of each test."""
    UserFactory._meta.sqlalchemy_session_factory = session_local
    yield


@pytest.fixture(autouse=True)
def clean_users(session_local):
    """Wipe users + reset the factory sequence after each test."""
    yield
    UserFactory.reset_sequence()
    with session_local() as s:
        s.execute(text("DELETE FROM users"))
        s.commit()
