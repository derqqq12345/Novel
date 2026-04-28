"""
데이터베이스 연결 및 세션 관리 모듈
비동기 SQLAlchemy 엔진과 세션 팩토리를 설정합니다.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from backend.app.config import settings


class Base(DeclarativeBase):
    """모든 SQLAlchemy ORM 모델의 기반 클래스"""
    pass


# 비동기 SQLAlchemy 엔진 생성
# asyncpg 드라이버 사용, 커넥션 풀 최소 10개 설정
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_pre_ping=True,  # 연결 유효성 사전 확인
)

# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 의존성 주입용 데이터베이스 세션 제공 함수.

    사용 예시:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """개발 환경에서 테이블을 생성합니다. 프로덕션에서는 Alembic 마이그레이션을 사용하세요."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def drop_tables() -> None:
    """테스트 환경에서 테이블을 삭제합니다."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
