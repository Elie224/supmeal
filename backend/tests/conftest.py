"""Conftest : fixture DB de test."""

import asyncio
import os
import sys
from collections.abc import AsyncGenerator

import asyncpg
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

# Forcer env=test AVANT import de l'app
os.environ["APP_ENV"] = "test"

# Host DB: containerized runs use service name `db`, host runs use loopback.
if os.path.exists("/.dockerenv"):
    os.environ["POSTGRES_HOST"] = "db"
else:
    os.environ["POSTGRES_HOST"] = "127.0.0.1"
os.environ["POSTGRES_DB"] = "supmeal_test"

if sys.platform.startswith("win"):
    # Evite certaines erreurs reseau asyncpg/Proactor sous Windows
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Ajout du path server/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import cookbook, recipe, shopping, user  # noqa: E402,F401

settings = get_settings()
TEST_DB_URL = settings.database_url


async def _ensure_test_database() -> None:
    """Create test database if it doesn't already exist."""
    conn = await asyncpg.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        database="postgres",
        ssl=False,
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", settings.postgres_db
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{settings.postgres_db}"')
    finally:
        await conn.close()


@pytest_asyncio.fixture(scope="function")
async def engine():
    await _ensure_test_database()
    eng = create_async_engine(
        TEST_DB_URL,
        connect_args={"ssl": False},
        poolclass=NullPool,
        pool_pre_ping=True,
    )
    # Retry once in case of transient Windows socket reset
    for attempt in (1, 2):
        try:
            async with eng.begin() as conn:
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            break
        except Exception:
            if attempt == 2:
                raise
            await asyncio.sleep(0.5)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session:
        yield session


@pytest_asyncio.fixture
async def client(engine) -> AsyncGenerator[AsyncClient, None]:
    maker = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        async with maker() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db_override
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
