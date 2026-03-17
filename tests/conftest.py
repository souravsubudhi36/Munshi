"""Shared pytest fixtures for Munshi tests."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from munshi.db.database import Base
from munshi.db import models  # noqa: F401 — register all ORM models
from munshi.db.models import Shop

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
_SessionFactory = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(scope="function")
async def db_session():
    """Create a fresh in-memory database for each test."""
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with _SessionFactory() as session:
        # Seed a default shop
        shop = Shop(id=1, name="Test Shop", owner_name="Test Owner", language="hi")
        session.add(shop)
        await session.commit()

        yield session

    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
