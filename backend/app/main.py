"""
FastAPI 애플리케이션 진입점
"""
import logging
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    애플리케이션 라이프사이클 관리.
    시작 시 DB 연결 확인, 종료 시 리소스 정리.
    """
    # ── 시작 ──────────────────────────────────────────────────────────────────
    logger.info(f"애플리케이션 시작 - env={settings.ENVIRONMENT} debug={settings.DEBUG}")

    # TODO: Phase 2에서 DB 연결 확인 추가
    # TODO: Phase 5에서 Qdrant 연결 확인 추가

    yield

    # ── 종료 ──────────────────────────────────────────────────────────────────
    logger.info("애플리케이션 종료")


def create_application() -> FastAPI:
    """FastAPI 애플리케이션 인스턴스를 생성하고 설정합니다."""

    app = FastAPI(
        title="AI 장편소설 생성 플랫폼",
        description="Qwen AI 모델을 활용한 장편소설 생성 전문 플랫폼 API",
        version="0.1.0",
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        lifespan=lifespan,
    )

    # ── CORS 미들웨어 ─────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── 속도 제한 의존성 ──────────────────────────────────────────────────────
    from backend.app.core.dependencies import RateLimiter

    # ── 라우터 등록 ───────────────────────────────────────────────────────────
    from backend.app.api.auth import router as auth_router
    from backend.app.api.chapters import router as chapters_router
    from backend.app.api.characters import router as characters_router
    from backend.app.api.consistency import router as consistency_router
    from backend.app.api.export import router as export_router
    from backend.app.api.generate import router as generate_router
    from backend.app.api.plot import router as plot_router
    from backend.app.api.projects import router as projects_router
    from backend.app.api.worldbuilding import router as worldbuilding_router

    app.include_router(
        auth_router,
        prefix="/api",
        dependencies=[Depends(RateLimiter())],
    )
    app.include_router(generate_router, prefix="/api", tags=["소설 생성"])
    app.include_router(
        projects_router,
        prefix="/api",
        dependencies=[Depends(RateLimiter())],
    )
    app.include_router(
        chapters_router,
        prefix="/api",
        dependencies=[Depends(RateLimiter())],
    )
    app.include_router(
        characters_router,
        prefix="/api",
        dependencies=[Depends(RateLimiter())],
    )
    app.include_router(
        plot_router,
        prefix="/api",
        dependencies=[Depends(RateLimiter())],
    )
    app.include_router(
        worldbuilding_router,
        prefix="/api",
        dependencies=[Depends(RateLimiter())],
    )
    app.include_router(
        consistency_router,
        prefix="/api",
        dependencies=[Depends(RateLimiter())],
    )
    app.include_router(
        export_router,
        prefix="/api",
        dependencies=[Depends(RateLimiter())],
    )

    # ── 헬스체크 엔드포인트 ───────────────────────────────────────────────────
    @app.get("/health", tags=["시스템"])
    async def health_check() -> JSONResponse:
        """서비스 상태 확인 엔드포인트"""
        return JSONResponse(
            content={
                "status": "healthy",
                "environment": settings.ENVIRONMENT,
                "version": "0.1.0",
            }
        )

    @app.get("/", tags=["시스템"])
    async def root() -> JSONResponse:
        """루트 엔드포인트"""
        return JSONResponse(
            content={
                "message": "AI 장편소설 생성 플랫폼 API",
                "docs": "/docs" if settings.DEBUG else "비활성화됨",
            }
        )

    return app


# WSGI/ASGI 서버에서 사용할 앱 인스턴스
app = create_application()
