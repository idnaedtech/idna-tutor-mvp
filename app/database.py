"""
IDNA EdTech v7.3 — Database Engine
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


def run_migrations():
    """Add missing columns to existing tables. Safe to run multiple times (idempotent)."""
    import logging
    from sqlalchemy import text, inspect

    logger = logging.getLogger("idna")
    inspector = inspect(engine)

    # Check if sessions table exists
    if 'sessions' not in inspector.get_table_names():
        return  # Table doesn't exist yet, will be created by create_all

    existing_columns = {col['name'] for col in inspector.get_columns('sessions')}

    # Column migrations for sessions table
    # Use TEXT for JSON on SQLite, JSON/JSONB for PostgreSQL
    json_type = "TEXT" if _is_sqlite else "JSONB"

    migrations = {
        'teaching_turn': f"ALTER TABLE sessions ADD COLUMN teaching_turn INTEGER DEFAULT 0",
        'explanations_given': f"ALTER TABLE sessions ADD COLUMN explanations_given {json_type} DEFAULT '[]'",
        'language_pref': f"ALTER TABLE sessions ADD COLUMN language_pref VARCHAR(20) DEFAULT 'hinglish'",
        'conversation_history': f"ALTER TABLE sessions ADD COLUMN conversation_history {json_type} DEFAULT '[]'",
        'current_concept_id': f"ALTER TABLE sessions ADD COLUMN current_concept_id VARCHAR(100)",
        'concept_mastery': f"ALTER TABLE sessions ADD COLUMN concept_mastery {json_type} DEFAULT '{{}}'",
        # v7.3.28: Empathy one-turn-max flag
        'empathy_given': "ALTER TABLE sessions ADD COLUMN empathy_given BOOLEAN DEFAULT FALSE",
    }

    with engine.begin() as conn:
        for col_name, sql in migrations.items():
            if col_name not in existing_columns:
                try:
                    conn.execute(text(sql))
                    logger.info(f"Migration: added column '{col_name}' to sessions table")
                except Exception as e:
                    logger.warning(f"Migration: column '{col_name}' may already exist: {e}")


def init_db():
    """Create all tables. Called once at startup."""
    if RESET_DATABASE:
        import logging
        from sqlalchemy import text
        logger = logging.getLogger("idna")
        logger.warning("RESET_DATABASE=true — dropping all tables!")

        with engine.connect() as conn:
            if _is_sqlite:
                # SQLite: get all tables and drop them
                tables = conn.execute(text(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )).fetchall()
                for (table_name,) in tables:
                    conn.execute(text(f"DROP TABLE IF EXISTS {table_name}"))
            else:
                # PostgreSQL: drop all tables in public schema with CASCADE
                conn.execute(text("DROP SCHEMA public CASCADE"))
                conn.execute(text("CREATE SCHEMA public"))
                conn.execute(text("GRANT ALL ON SCHEMA public TO PUBLIC"))
            conn.commit()

        logger.info("All tables dropped. Creating fresh schema...")

    # Create tables first
    Base.metadata.create_all(bind=engine)

    # Then run migrations to add any missing columns to existing tables
    run_migrations()
