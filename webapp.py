from fastapi import FastAPI, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from contextlib import asynccontextmanager
import os
import grpc
from grpc import RpcError

import tutoring_pb2
import tutoring_pb2_grpc
import db


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize DB pool
    await db.init_pool()
    print("DB pool initialized", flush=True)
    yield
    # Shutdown: nothing to clean up


app = FastAPI(lifespan=lifespan)

print("### RUNNING CLEAN BASELINE WEBAPP ###", flush=True)


# ---------
# Models
# ---------
class StartSessionIn(BaseModel):
    student_id: str
    topic_id: str


class TurnIn(BaseModel):
    student_id: str
    session_id: str
    user_text: str


# -------------
# gRPC helper
# -------------
def get_stub() -> tutoring_pb2_grpc.TutoringServiceStub:
    target = os.getenv("GRPC_TARGET")
    use_tls = os.getenv("GRPC_USE_TLS", "0") == "1"

    if not target:
        raise RuntimeError("GRPC_TARGET not set")

    channel = (
        grpc.secure_channel(target, grpc.ssl_channel_credentials())
        if use_tls
        else grpc.insecure_channel(target)
    )
    return tutoring_pb2_grpc.TutoringServiceStub(channel)


# ----------
# Routes
# ----------
@app.get("/")
def root():
    # Some platforms health-check "/" by default.
    return {"status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/grpc_ping")
def grpc_ping():
    target = os.getenv("GRPC_TARGET")
    use_tls = os.getenv("GRPC_USE_TLS", "0") == "1"
    if not target:
        return {"ok": False, "error": "GRPC_TARGET not set"}

    try:
        channel = (
            grpc.secure_channel(target, grpc.ssl_channel_credentials())
            if use_tls
            else grpc.insecure_channel(target)
        )

        grpc.channel_ready_future(channel).result(timeout=10)
        return {"ok": True, "target": target, "tls": use_tls}

    except Exception as e:
        return {
            "ok": False,
            "target": target,
            "tls": use_tls,
            "error_type": type(e).__name__,
            "error": repr(e),
        }


@app.post("/start_session")
def start_session(payload: StartSessionIn):
    try:
        stub = get_stub()
        resp = stub.StartSession(
            tutoring_pb2.StartSessionRequest(
                student_id=payload.student_id,
                topic_id=payload.topic_id,
            ),
            timeout=10,
        )
        return {
            "ok": True,
            "session_id": resp.session_id,
            "state": int(resp.state),
            "tutor_text": resp.tutor_text,
        }

    except RpcError as e:
        # Return real gRPC error instead of FastAPI "Internal Server Error"
        return {
            "ok": False,
            "grpc_code": str(e.code()),
            "error": e.details(),
            "target": os.getenv("GRPC_TARGET"),
            "tls": os.getenv("GRPC_USE_TLS", "0") == "1",
        }

    except Exception as e:
        return {"ok": False, "error_type": type(e).__name__, "error": repr(e)}


@app.post("/turn")
def turn(payload: TurnIn):
    try:
        stub = get_stub()
        resp = stub.Turn(
            tutoring_pb2.TurnRequest(
                student_id=payload.student_id,
                session_id=payload.session_id,
                user_text=payload.user_text,
            ),
            timeout=10,
        )

        return {
            "ok": True,
            "session_id": resp.session_id,
            "next_state": int(resp.next_state),
            "tutor_text": resp.tutor_text,
            "intent": resp.intent,
            "attempt_count": resp.attempt_count,
            "frustration_counter": resp.frustration_counter,
            "topic_id": resp.topic_id,
            "question_id": resp.question_id,
            "title": resp.title,
        }

    except RpcError as e:
        return {
            "ok": False,
            "grpc_code": str(e.code()),
            "error": e.details(),
            "target": os.getenv("GRPC_TARGET"),
            "tls": os.getenv("GRPC_USE_TLS", "0") == "1",
        }

    except Exception as e:
        return {"ok": False, "error_type": type(e).__name__, "error": repr(e)}


# -------------------------
# API endpoints for frontend
# -------------------------
@app.get("/api/topics")
async def api_topics():
    """Return list of available topics for the dropdown."""
    try:
        topics = await db.get_topics()
        return topics
    except Exception as e:
        return []


@app.get("/api/progress")
async def api_progress(
    student_id: str = Query(...),
    topic_id: str = Query(...)
):
    """Return progress for a student on a topic."""
    try:
        correct = await db.count_correct_questions(student_id, topic_id)
        # Get total questions in topic
        async with db.pool().acquire() as c:
            total = await c.fetchval(
                "SELECT COUNT(*) FROM questions WHERE topic_id=$1",
                topic_id
            )
        total = total or 0
        pct = round((correct / total) * 100) if total > 0 else 0
        return {"correct": correct, "total": total, "pct": pct}
    except Exception as e:
        return {"correct": 0, "total": 0, "pct": 0, "error": str(e)}


@app.get("/api/resume")
async def api_resume(student_id: str = Query(...)):
    """Get the latest session for a student to resume."""
    try:
        session = await db.get_latest_session(student_id)
        if session:
            return {
                "status": "ok",
                "session_id": session["session_id"],
                "topic_id": session["topic_id"],
                "state": session["state"],
            }
        return {"status": "not_found"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/start")
def start_session_alias(payload: StartSessionIn):
    """Alias for /start_session to match frontend expectations."""
    return start_session(payload)


# -------------------------
# Debug: prove which file is running
# -------------------------
@app.get("/__whoami")
def whoami():
    return {
        "file": __file__,
        "cwd": os.getcwd(),
        "port_env": os.getenv("PORT"),
        "grpc_target": os.getenv("GRPC_TARGET"),
        "grpc_use_tls": os.getenv("GRPC_USE_TLS", "0"),
    }


# -------------------------
# Static file serving (must be last)
# -------------------------
@app.get("/ui")
async def serve_ui():
    """Serve the main UI page."""
    return FileResponse("static/index.html")


# Mount static files for any additional assets
app.mount("/static", StaticFiles(directory="static"), name="static")
