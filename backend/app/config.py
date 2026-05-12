"""
애플리케이션 설정 관리 모듈
"""
import os
from pathlib import Path

# 루트 디렉토리의 .env 파일 로드
from dotenv import load_dotenv

# 프로젝트 루트의 .env 를 찾아서 로드
_root = Path(__file__).parent.parent.parent  # AI/
load_dotenv(_root / ".env", override=False)


class Settings:
    # ─── 환경 ─────────────────────────────────────────────────────────────────
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")

    # ─── Qwen / DashScope ─────────────────────────────────────────────────────
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_MODEL: str = os.getenv("QWEN_MODEL", "qwen-max")
    QWEN_API_BASE_URL: str = os.getenv(
        "QWEN_API_BASE_URL",
        "https://dashscope.aliyuncs.com/compatible-mode/v1",
    )

    # ─── Ollama ───────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen:14b")

    # ─── CORS ─────────────────────────────────────────────────────────────────
    @property
    def CORS_ORIGINS(self) -> list[str]:
        raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
        return [o.strip() for o in raw.split(",") if o.strip()]

    # ─── DB ───────────────────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/novel_platform",
    )
    # 커넥션 풀 설정 (최소 10개 유지)
    DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
    DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
    DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # ─── Qdrant ───────────────────────────────────────────────────────────────
    QDRANT_URL: str = os.getenv("QDRANT_URL", "http://localhost:6333")
    QDRANT_API_KEY: str = os.getenv("QDRANT_API_KEY", "")
    QDRANT_COLLECTION_NAME: str = os.getenv("QDRANT_COLLECTION_NAME", "novel_passages")

    # ─── JWT ──────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str = os.getenv(
        "JWT_SECRET_KEY",
        "change-this-to-a-strong-random-secret-key-in-production",
    )
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # ─── 속도 제한 ────────────────────────────────────────────────────────────
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = int(
        os.getenv("RATE_LIMIT_REQUESTS_PER_MINUTE", "100")
    )


settings = Settings()
