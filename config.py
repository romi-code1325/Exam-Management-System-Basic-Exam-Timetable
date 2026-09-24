"""
Application configuration.

All values are read from environment variables so the same code can run
locally, in CI, or on a hosting platform (Render/Railway/Vercel) purely
through env var configuration. See .env.example for the full list.
"""
import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    # Secret used to sign JWT access tokens. MUST be overridden in production.
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRES_MINUTES: int = int(os.getenv("JWT_EXPIRES_MINUTES", "120"))

    # SQLite file. Kept as a simple file-based DB since the assessment scope
    # is intentionally small (no room allocation, no clash detection, etc.).
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", "exam_timetable.db")

    # Bootstrap admin credentials (single admin account, as allowed by the
    # "Easy" scope of this assessment -- no multi-admin/role system required).
    ADMIN_EMAIL: str = os.getenv("ADMIN_EMAIL", "admin@example.com")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "admin123")

    PORT: int = int(os.getenv("PORT", "5000"))
    DEBUG: bool = os.getenv("FLASK_DEBUG", "false").lower() == "true"
