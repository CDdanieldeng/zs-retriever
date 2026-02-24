"""Database session management."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db.models import Base


def get_engine():
    """Create SQLite engine. Ensures data dir exists."""
    settings = get_settings()
    path = settings.sqlite_path
    path.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def _get_session_factory() -> sessionmaker[Session]:
    global _engine, _SessionLocal
    if _SessionLocal is None:
        _engine = get_engine()
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=_engine,
        )
    return _SessionLocal


def get_db() -> Session:
    """Get database session. Caller must close or use as context manager."""
    SessionLocal = _get_session_factory()
    return SessionLocal()


def init_db() -> None:
    """Create all tables."""
    _get_session_factory()
    Base.metadata.create_all(bind=_engine)
