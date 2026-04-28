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

    # ─── Ollama ───────────────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen:14b")

    # ─── CORS ─────────────────────────────────────────────────────────────────
    @property
    def CORS_ORIGINS(self) -> list[str]:
        raw = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
        return [o.strip() for o in raw.split(",") if o.strip()]

    # ─── DB (나중에 사용) ──────────────────────────────────────────────────────
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/novel_platform",
    )
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")


settings = Settings()
