"""
IDNA EdTech v8.0 — Main Application
FastAPI app. Mounts routers, CORS, serves static files.
Database initialization and question bank seeding on startup.

v8.0: Complete session management rewrite with:
- SessionState dataclass (app/models/session.py)
- Complete FSM transition matrix (app/fsm/transitions.py)
- Per-state handlers (app/fsm/handlers.py)
- Language persistence across all turns
- Reteach cap at 3 with CB material injection
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import CORS_ORIGINS, LOG_LEVEL, BASE_DIR
from app.database import init_db, SessionLocal
from app.models import Question, Student

logger = logging.getLogger("idna")


# ─── Lifespan (startup/shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB + seed questions. Shutdown: cleanup."""
    # Configure logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    # Init database tables
    logger.info("Initializing database...")
    init_db()

    # v8.1.0: Auto-migrate missing columns (no Alembic in project)
    _run_migrations()

    # Seed question bank — upsert to catch new questions and level updates
    db = SessionLocal()
    try:
        count = db.query(Question).count()
        if count == 0:
            logger.info("Seeding question bank...")
            _seed_questions(db)
            logger.info(f"Seeded {db.query(Question).count()} questions")
        else:
            added, updated = _upsert_questions(db)
            total = db.query(Question).count()
            if added or updated:
                logger.info(f"Question bank upsert: {added} added, {updated} updated, {total} total")
            else:
                logger.info(f"Question bank has {total} questions")

        # Seed test student if none exist
        student_count = db.query(Student).count()
        if student_count == 0:
            logger.info("Seeding test student...")
            _seed_test_student(db)
            logger.info("Test student created (PIN: 1234)")
    finally:
        db.close()

    # v7.5.2: Start TTS precache in background (PostgreSQL-backed)
    try:
        from content_bank.loader import get_content_bank
        from app.voice.tts_precache import precache_content_bank, get_cache_stats_db
        from app.voice.tts import get_tts

        cb = get_content_bank()

        # Check cache stats from database
        precache_db = SessionLocal()
        try:
            cache_stats = get_cache_stats_db(precache_db)
            logger.info(f"TTS cache stats (DB): {cache_stats}")

            # v7.5.2: Only precache if DB cache is small
            if cache_stats["files"] < 50:
                tts = get_tts()

                async def tts_wrapper(text: str, lang: str) -> bytes:
                    """Wrapper to match precache expected signature."""
                    result = await tts.synthesize_async(text, lang)
                    return result.audio_bytes

                async def run_precache():
                    # Get fresh DB session for async context
                    from app.database import SessionLocal
                    async_db = SessionLocal()
                    try:
                        stats = await precache_content_bank(cb, tts_wrapper, async_db, ["hi-IN"])
                        logger.info(f"TTS precache complete: {stats}")
                    except Exception as e:
                        logger.error(f"TTS precache failed: {e}")
                    finally:
                        async_db.close()

                import asyncio
                asyncio.create_task(run_precache())
                logger.info("TTS precache started in background (2s rate limit)")
            else:
                logger.info(f"TTS precache skipped: {cache_stats['files']} entries already cached")
        finally:
            precache_db.close()
    except ImportError as e:
        logger.warning(f"TTS precache skipped (missing deps): {e}")
    except Exception as e:
        logger.error(f"TTS precache init failed: {e}")

    logger.info("IDNA Didi v10.5.0 ready")
    yield
    logger.info("Shutting down")


def _run_migrations():
    """v8.1.0: Add missing columns to production DB (no Alembic).

    This runs on every startup and uses IF NOT EXISTS to be idempotent.
    Safe to run multiple times.
    """
    from sqlalchemy import text
    from app.database import engine

    migrations = [
        # v8.1.0: P0 bug fixes
        "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS confusion_count INTEGER DEFAULT 0",
        "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS board_name VARCHAR(20) DEFAULT 'NCERT'",
        "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS topics_covered JSONB",
        # P0: Language auto-detection
        "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS consecutive_english_count INTEGER DEFAULT 0",
        # v10.4.0: 5-level teaching scaffold
        "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS current_level INTEGER DEFAULT 2",
        "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS consecutive_correct INTEGER DEFAULT 0",
        "ALTER TABLE sessions ADD COLUMN IF NOT EXISTS consecutive_wrong INTEGER DEFAULT 0",
        "ALTER TABLE question_bank ADD COLUMN IF NOT EXISTS level INTEGER DEFAULT 3",
    ]

    with engine.connect() as conn:
        for migration in migrations:
            try:
                conn.execute(text(migration))
                conn.commit()
                logger.info(f"Migration OK: {migration[:50]}...")
            except Exception as e:
                # Column might already exist or different DB (SQLite vs PostgreSQL)
                if "already exists" in str(e).lower() or "duplicate column" in str(e).lower():
                    pass  # Expected on subsequent runs
                elif "syntax error" in str(e).lower():
                    # SQLite doesn't support IF NOT EXISTS for ALTER TABLE
                    # Try without IF NOT EXISTS
                    try:
                        simple_migration = migration.replace(" IF NOT EXISTS", "")
                        conn.execute(text(simple_migration))
                        conn.commit()
                        logger.info(f"Migration OK (SQLite): {simple_migration[:50]}...")
                    except Exception as e2:
                        if "duplicate column" in str(e2).lower():
                            pass  # Already exists
                        else:
                            logger.warning(f"Migration skipped: {e2}")
                else:
                    logger.warning(f"Migration skipped: {e}")

    logger.info("Database migrations complete")


def _seed_questions(db):
    """Load seed questions into the database."""
    from app.content.seed_questions import QUESTIONS

    # Map difficulty strings to integers
    diff_map = {"easy": 1, "medium": 2, "hard": 3}

    for q_data in QUESTIONS:
        # Handle both old format (rational numbers) and new format (square/cube)
        difficulty = q_data.get("difficulty", 1)
        if isinstance(difficulty, str):
            difficulty = diff_map.get(difficulty, 2)

        q = Question(
            id=q_data["id"],
            subject=q_data.get("subject", "math"),
            chapter=q_data["chapter"],
            class_level=q_data.get("class_level", 8),
            question_type=q_data.get("question_type") or q_data.get("type", "direct"),
            question_text=q_data.get("question_text") or q_data.get("question_en") or q_data.get("question"),
            question_voice=q_data.get("question_voice") or q_data.get("question"),
            answer=q_data["answer"],
            answer_variants=q_data.get("answer_variants") or q_data.get("accept_patterns"),
            key_concepts=q_data.get("key_concepts"),
            eval_method=q_data.get("eval_method", "exact"),
            hints=q_data.get("hints"),
            solution=q_data.get("solution") or q_data.get("explanation"),
            target_skill=q_data["target_skill"],
            difficulty=difficulty,
            level=q_data.get("level", 3),
            active=True,
        )
        db.add(q)
    db.commit()


def _upsert_questions(db):
    """Insert missing questions and update level field on existing ones."""
    from app.content.seed_questions import QUESTIONS

    diff_map = {"easy": 1, "medium": 2, "hard": 3}
    added = 0
    updated = 0
    existing_ids = {q.id for q in db.query(Question).all()}

    for q_data in QUESTIONS:
        difficulty = q_data.get("difficulty", 1)
        if isinstance(difficulty, str):
            difficulty = diff_map.get(difficulty, 2)
        seed_level = q_data.get("level", 3)

        if q_data["id"] not in existing_ids:
            q = Question(
                id=q_data["id"],
                subject=q_data.get("subject", "math"),
                chapter=q_data["chapter"],
                class_level=q_data.get("class_level", 8),
                question_type=q_data.get("question_type") or q_data.get("type", "direct"),
                question_text=q_data.get("question_text") or q_data.get("question_en") or q_data.get("question"),
                question_voice=q_data.get("question_voice") or q_data.get("question"),
                answer=q_data["answer"],
                answer_variants=q_data.get("answer_variants") or q_data.get("accept_patterns"),
                key_concepts=q_data.get("key_concepts"),
                eval_method=q_data.get("eval_method", "exact"),
                hints=q_data.get("hints"),
                solution=q_data.get("solution") or q_data.get("explanation"),
                target_skill=q_data["target_skill"],
                difficulty=difficulty,
                level=seed_level,
                active=True,
            )
            db.add(q)
            added += 1
        else:
            # Update level if it changed from default
            existing = db.query(Question).filter(Question.id == q_data["id"]).first()
            if existing and existing.level != seed_level:
                existing.level = seed_level
                updated += 1

    db.commit()
    return added, updated


def _seed_test_student(db):
    """Create a test student for development/testing."""
    import uuid
    student = Student(
        id=str(uuid.uuid4()),
        name="Priya",
        pin="1234",
        class_level=8,
        preferred_language="hi-IN",
    )
    db.add(student)
    db.commit()


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="IDNA Didi v10.5",
    description="AI Voice Tutor for Class 8 NCERT — Parallel TTS",
    version="10.5.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount routers
from app.routers import auth, student, review
app.include_router(auth.router)
app.include_router(student.router)
app.include_router(review.router)

# TODO: Mount parent router when ready
# from app.routers import parent
# app.include_router(parent.router)

# Serve web UI
web_dir = BASE_DIR / "web"
static_dir = web_dir / "static"
if web_dir.exists():
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/")
    async def serve_login():
        return FileResponse(str(web_dir / "login.html"))

    @app.get("/student")
    async def serve_student():
        return FileResponse(str(web_dir / "student.html"))

    @app.get("/parent")
    async def serve_parent():
        return FileResponse(str(web_dir / "parent.html"))


# Health check (both /health and /healthz for Railway)
@app.get("/health")
@app.get("/healthz")
async def health():
    return {"status": "ok", "version": "10.5.0"}


@app.get("/health/detail")
async def health_detail():
    db = SessionLocal()
    try:
        q_count = db.query(Question).count()
        from sqlalchemy import func
        level_rows = db.query(Question.level, func.count()).group_by(Question.level).all()
        levels = {str(lvl): cnt for lvl, cnt in level_rows}
    finally:
        db.close()
    return {"status": "ok", "version": "10.5.0", "questions": q_count, "levels": levels}


# Keep-alive endpoint for UptimeRobot (prevents Railway sleep)
@app.get("/ping")
async def ping():
    return {"status": "awake"}
