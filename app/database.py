"""
IDNA EdTech v7.0 — Database Engine
SQLAlchemy async-compatible setup. Works with SQLite (dev) and PostgreSQL (prod).
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.pool import StaticPool

import os
from app.config import DATABASE_URL

# Set RESET_DATABASE=true to drop all tables and recreate (use for schema migrations)
RESET_DATABASE = os.getenv("RESET_DATABASE", "false").lower() == "true"


# ─── Engine Setup ────────────────────────────────────────────────────────────

_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # SQLite needs special handling for concurrent access
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    # Enable WAL mode for better concurrent read performance
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # PostgreSQL — standard pooled connection
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Test connections before use
        echo=False,
    )


# ─── Session Factory ─────────────────────────────────────────────────────────

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ─── Base Class ──────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


# ─── Dependency ──────────────────────────────────────────────────────────────

def get_db():
    """FastAPI dependency: yields a database session, auto-closes."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables. Called once at startup."""
    if RESET_DATABASE:
        import logging
        logger = logging.getLogger("idna")
        logger.warning("RESET_DATABASE=true — dropping all tables!")
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped. Creating fresh schema...")
    Base.metadata.create_all(bind=engine)
