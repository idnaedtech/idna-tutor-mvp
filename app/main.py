"""
IDNA EdTech v7.0 — Main Application
FastAPI app. Mounts routers, CORS, serves static files.
Database initialization and question bank seeding on startup.
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

    # Seed question bank if empty
    db = SessionLocal()
    try:
        count = db.query(Question).count()
        if count == 0:
            logger.info("Seeding question bank...")
            _seed_questions(db)
            logger.info(f"Seeded {db.query(Question).count()} questions")
        else:
            logger.info(f"Question bank has {count} questions")

        # Seed test student if none exist
        student_count = db.query(Student).count()
        if student_count == 0:
            logger.info("Seeding test student...")
            _seed_test_student(db)
            logger.info("Test student created (PIN: 1234)")
    finally:
        db.close()

    logger.info("IDNA Didi v7.0 ready")
    yield
    logger.info("Shutting down")


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
            active=True,
        )
        db.add(q)
    db.commit()


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
    title="IDNA Didi v7.0",
    description="AI Voice Tutor for Class 8 NCERT",
    version="7.0.0",
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
from app.routers import auth, student
app.include_router(auth.router)
app.include_router(student.router)

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
    return {"status": "ok", "version": "7.0.0"}
