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
from app.models import Question

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
    finally:
        db.close()

    logger.info("IDNA Didi v7.0 ready")
    yield
    logger.info("Shutting down")


def _seed_questions(db):
    """Load seed questions into the database."""
    from app.content.seed_questions import QUESTIONS
    for q_data in QUESTIONS:
        q = Question(
            id=q_data["id"],
            subject=q_data["subject"],
            chapter=q_data["chapter"],
            class_level=q_data["class_level"],
            question_type=q_data["question_type"],
            question_text=q_data["question_text"],
            question_voice=q_data["question_voice"],
            answer=q_data["answer"],
            answer_variants=q_data.get("answer_variants"),
            key_concepts=q_data.get("key_concepts"),
            eval_method=q_data.get("eval_method", "exact"),
            hints=q_data.get("hints"),
            solution=q_data.get("solution"),
            target_skill=q_data["target_skill"],
            difficulty=q_data.get("difficulty", 1),
            active=True,
        )
        db.add(q)
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
if web_dir.exists():
    app.mount("/static", StaticFiles(directory=str(web_dir / "static")), name="static")

    @app.get("/")
    async def serve_login():
        return FileResponse(str(web_dir / "login.html"))

    @app.get("/student")
    async def serve_student():
        return FileResponse(str(web_dir / "student.html"))

    @app.get("/parent")
    async def serve_parent():
        return FileResponse(str(web_dir / "parent.html"))


# Health check
@app.get("/health")
async def health():
    return {"status": "ok", "version": "7.0.0"}
