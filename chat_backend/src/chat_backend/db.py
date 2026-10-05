from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from .config import settings


class Base(DeclarativeBase):
    pass


_sqla_url = settings.chatdb_dsn.replace("postgresql://", "postgresql+psycopg://", 1)
engine = create_async_engine(_sqla_url)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
