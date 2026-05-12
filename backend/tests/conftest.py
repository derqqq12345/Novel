"""
Pytest 설정 및 공통 픽스처
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import JSON, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.database import Base

# 테스트용 인메모리 SQLite 데이터베이스
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


# SQLite에서 JSONB를 JSON으로 변환
@event.listens_for(Base.metadata, "before_create")
def _set_sqlite_pragma(target, connection, **kw):
    """SQLite에서 JSONB를 JSON으로 변환"""
    if connection.dialect.name == "sqlite":
        from sqlalchemy import Table
        for table in target.tables.values():
            for column in table.columns:
                if isinstance(column.type, JSONB):
                    column.type = JSON()


@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 픽스처"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db() -> AsyncGenerator[AsyncSession, None]:
    """테스트용 데이터베이스 세션 픽스처"""
    # 테스트용 엔진 생성
    engine = create_async_engine(
        TEST_DATABASE_URL,
        poolclass=NullPool,
        echo=False,
    )

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 세션 팩토리 생성
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # 세션 생성 및 제공
    async with async_session() as session:
        yield session
        await session.rollback()

    # 테이블 삭제
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
