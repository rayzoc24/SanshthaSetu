from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


# ---------------------------------------------------------------------------
# SQLAlchemy engine
# ---------------------------------------------------------------------------
# pool_pre_ping=True: issues a cheap SELECT 1 before handing out a connection
# so stale connections (e.g. after Neon auto-suspend) are discarded silently.
# SSL is handled by ?sslmode=require in DATABASE_URL — no extra kwarg needed.
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # safe for APIs: objects don't lazy-load after commit
)


# ---------------------------------------------------------------------------
# Declarative base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """
    Yields a SQLAlchemy session for the duration of one request.
    Closes the session in the finally block regardless of success or error.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
