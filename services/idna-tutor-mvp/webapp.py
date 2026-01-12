from __future__ import annotations

import os
import uuid
import time
import logging
import traceback
from pathlib import Path
from typing import Tuple, Optional

import grpc
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import tutoring_pb2
import tutoring_pb2_grpc

from db import get_topics, init_pool, get_latest_session
import db


# -------------------------
# Logging
# -------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s:%(lineno)d - %(message)s",
)
logger = logging.getLogger("idna.webapp")


# -------------------------
# App
# -------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TURN_ROUTER_VERSION = "v2-2A"

DEFAULT_STUDENT_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_TOPIC_ID = "g6_math_add_01"


# -------------------------
# Static
# -------------------------
# Your static directory should be: services/idna-tutor-mvp/static/
STATIC_DIR = Path(__file__).resolve().parent / "static"

if STATIC_DIR.is_dir():
    # Serve UI assets at /
    app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static-root")
    logger.warning("Static mounted at / from %s", STATIC_DIR)
else:
    logger.warning("Static dir missing: %s (skipping static mount)", STATIC_DIR)


# -------------------------
# Models
# -------------------------
class TurnIn(BaseModel):
    text: str
    session_id: Optional[str] = None


class TurnOut(BaseModel):
    ok: bool
    session_id: str
    intent: str
    reply: str


class StartReq(BaseModel):
    student_id: str = DEFAULT_STUDENT_ID
    topic_id: str = DEFAULT_TOPIC_ID


class TurnReq(BaseModel):
    student_id: str
    session_id: str
    user_text: str


# -------------------------
# Startup / Health
# -------------------------
@app.get("/healthz")
def healthz():
    return {"status": "ok", "version": TURN_ROUTER_VERSION}


@app.on_event("startup")
async def startup():
    await init_pool()


# -------------------------
# gRPC client
# -------------------------
GRPC_TARGET = os.getenv("GRPC_TARGET")
GRPC_USE_TLS = os.getenv("GRPC_USE_TLS", "0")

_GRPC_OPTIONS = [
    ("grpc.keepalive_time_ms", 30_000),
    ("grpc.keepalive_timeout_ms", 10_000),
    ("grpc.http2.max_pings_without_data", 0),
    ("grpc.keepalive_permit_without_calls", 1),
]

def _make_channel(target: str) -> grpc.Channel:
    auto_tls = (".up.railway.app" in target)
    use_tls = (GRPC_USE_TLS == "1") or (auto_tls and GRPC_USE_TLS != "0")

    if use_tls:
        creds = grpc.ssl_channel_credentials()
        return grpc.secure_channel(target, creds, options=_GRPC_OPTIONS)

    return grpc.insecure_channel(target, options=_GRPC_OPTIONS)


logger.info("GRPC_TARGET=%s GRPC_USE_TLS=%s", GRPC_TARGET, GRPC_USE_TLS)
CHANNEL = _make_channel(GRPC_TARGET)
STUB = tutoring_pb2_grpc.TutoringServiceStub(CHANNEL)


def _start_session_grpc(student_id: str, topic_id: str):
    return STUB.StartSession(
        tutoring_pb2.StartSessionRequest(student_id=student_id, topic_id=topic_id),
        timeout=20,
    )


def _turn_grpc(student_id: str, session_id: str, user_text: str):
    return STUB.Turn(
        tutoring_pb2.TurnRequest(student_id=student_id, session_id=session_id, user_text=user_text),
        timeout=20,
    )


# -------------------------
# Intent classifier
# -------------------------
def _classify_intent(text: str) -> Tuple[str, bool]:
    t = (text or "").lower().strip()
    tokens = [tok for tok in t.replace("?", " ? ").split() if tok]

    greet_words = {"hi", "hello", "hey"}
    wh_words = {"what", "why", "how", "when", "where"}

    if not (text or "").strip():
        return "empty", False

    is_question = ("?" in t)
    if not is_question and tokens:
        if tokens[0] in wh_words:
            is_question = True
        elif tokens[0] in greet_words and len(tokens) > 1 and tokens[1] in wh_words:
            is_question = True

    if is_question:
        return "question", True
    if any(w in tokens for w in greet_words):
        return "greet", False
    return "unknown", False


# -------------------------
# /turn router (Phase 2A)
# -------------------------
@app.post("/turn", response_model=TurnOut)
def turn(payload: TurnIn):
    text = (payload.text or "").strip()
    sid_in = (payload.session_id or "").strip() or None

    intent, is_question = _classify_intent(text)

    logger.info(
        "TURN version=%s grpc=%s intent=%s sid_in=%r text=%r",
        TURN_ROUTER_VERSION, GRPC_TARGET, intent, sid_in, text
    )

    # local replies
    if intent == "empty":
        sid = sid_in or str(uuid.uuid4())
        return {"ok": True, "session_id": sid, "intent": "empty", "reply": "Say something."}

    if not is_question:
        sid = sid_in or str(uuid.uuid4())
        if intent == "greet":
            return {
                "ok": True,
                "session_id": sid,
                "intent": "greet",
                "reply": f"Hi. Ask a question like: 'Explain fractions'. [{TURN_ROUTER_VERSION}]",
            }
        return {
            "ok": True,
            "session_id": sid,
            "intent": "unknown",
            "reply": f"Say it as a question. You said: {text} [{TURN_ROUTER_VERSION}]",
        }

    # question => gRPC
    try:
        student_id = DEFAULT_STUDENT_ID

        if not sid_in:
            start_resp = _start_session_grpc(student_id=student_id, topic_id=DEFAULT_TOPIC_ID)
            return {
                "ok": True,
                "session_id": start_resp.session_id,
                "intent": "start",
                "reply": start_resp.tutor_text,
            }

        resp = _turn_grpc(student_id=student_id, session_id=sid_in, user_text=text)
        resp_intent = getattr(resp, "intent", None) or "question"

        return {
            "ok": True,
            "session_id": resp.session_id,
            "intent": str(resp_intent),
            "reply": resp.tutor_text,
        }

    except grpc.RpcError as e:
        logger.error("gRPC error in /turn: code=%s details=%s", e.code(), e.details())
        try:
            logger.error("gRPC debug_error_string=%s", e.debug_error_string())
        except Exception:
            pass
        logger.error("traceback:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail={"grpc_code": str(e.code()), "grpc_details": e.details()})

    except Exception:
        logger.error("Non-gRPC exception in /turn\n%s", traceback.format_exc())
        raise HTTPException(status_code=500, detail="Internal error")


# -------------------------
# Existing REST endpoints
# -------------------------
async def get_next_question_or_complete(conn, session_id: str):
    session = await conn.fetchrow(
        "SELECT session_id, topic_id, status FROM sessions WHERE session_id=$1",
        session_id
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session["status"] == "COMPLETED":
        return {
            "session_id": session_id,
            "topic_id": session["topic_id"],
            "state": "COMPLETED",
            "question": None,
            "message": "Session already completed."
        }

    topic_id = session["topic_id"]

    q = await conn.fetchrow(
        """
        SELECT q.question_id, q.prompt, q.qtype, q.answer_key, q.hint1, q.hint2, q.reveal_explain
        FROM questions q
        WHERE q.topic_id = $1
          AND NOT EXISTS (
            SELECT 1 FROM attempts a
            WHERE a.session_id = $2
              AND a.question_id = q.question_id
              AND a.is_correct = true
          )
        ORDER BY q.question_id
        LIMIT 1
        """,
        topic_id, session_id
    )

    if not q:
        await conn.execute(
            """
            UPDATE sessions
            SET status='COMPLETED',
                completed_at=NOW(),
                current_question_id=NULL
            WHERE session_id=$1 AND status <> 'COMPLETED'
            """,
            session_id
        )
        return {
            "session_id": session_id,
            "topic_id": topic_id,
            "state": "COMPLETED",
            "question": None,
            "message": "No more questions left in this topic."
        }

    await conn.execute(
        "UPDATE sessions SET current_question_id=$1 WHERE session_id=$2",
        q["question_id"], session_id
    )

    return {
        "session_id": session_id,
        "topic_id": topic_id,
        "state": "ASKING",
        "question": {
            "question_id": q["question_id"],
            "prompt": q["prompt"],
            "qtype": q["qtype"],
            "hint1": q["hint1"],
            "hint2": q["hint2"],
        }
    }


@app.post("/start")
async def start(req: StartReq):
    p = db.pool()
    async with p.acquire() as conn:
        total = await conn.fetchval(
            "SELECT COUNT(*) FROM questions WHERE topic_id=$1",
            req.topic_id
        ) or 0

        correct = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT question_id)
            FROM attempts
            WHERE student_id=$1 AND topic_id=$2 AND is_correct=true
            """,
            req.student_id, req.topic_id
        ) or 0

        if total > 0 and correct >= total:
            return {
                "blocked": True,
                "state": "COMPLETED",
                "session_id": None,
                "topic_id": req.topic_id,
                "tutor": "Topic already completed. Restart blocked.",
                "message": "Topic already completed. Restart blocked."
            }

    resp = STUB.StartSession(
        tutoring_pb2.StartSessionRequest(student_id=req.student_id, topic_id=req.topic_id),
        timeout=20
    )

    return {"session_id": resp.session_id, "state": int(resp.state), "tutor_text": resp.tutor_text}


@app.post("/api/reset")
async def reset_student_progress(student_id: str, topic_id: str):
    p = db.pool()
    async with p.acquire() as conn:
        await conn.execute("DELETE FROM attempts WHERE student_id=$1 AND topic_id=$2", student_id, topic_id)
    return {"status": "ok", "message": f"Reset progress for {student_id} on {topic_id}"}


@app.post("/turn_grpc")
def turn_grpc(req: TurnReq):
    try:
        resp = STUB.Turn(
            tutoring_pb2.TurnRequest(student_id=req.student_id, session_id=req.session_id, user_text=req.user_text),
            timeout=20
        )
        return {
            "session_id": resp.session_id,
            "state": int(resp.next_state),
            "tutor_text": resp.tutor_text,
            "attempt_count": getattr(resp, "attempt_count", None),
            "frustration_counter": getattr(resp, "frustration_counter", None),
            "intent": getattr(resp, "intent", None),
            "topic_id": getattr(resp, "topic_id", None),
            "question_id": getattr(resp, "question_id", None),
            "concept_title": getattr(resp, "concept_title", None),
        }

    except grpc.RpcError as e:
        logger.error("gRPC Turn() failed: code=%s details=%s", e.code(), e.details())
        try:
            logger.error("gRPC debug_error_string=%s", e.debug_error_string())
        except Exception:
            pass
        logger.error("traceback:\n%s", traceback.format_exc())
        raise HTTPException(status_code=502, detail={"grpc_code": str(e.code()), "grpc_details": e.details()})


@app.get("/api/topics")
async def api_topics():
    return await get_topics()


@app.get("/api/progress")
async def api_progress(student_id: str, topic_id: str):
    p = db.pool()
    async with p.acquire() as c:
        total = await c.fetchval("SELECT COUNT(*) FROM questions WHERE topic_id = $1", topic_id) or 0
        correct = await c.fetchval(
            "SELECT COUNT(DISTINCT question_id) FROM attempts WHERE student_id = $1 AND topic_id = $2 AND is_correct = true",
            student_id, topic_id
        ) or 0

    pct = int((correct / total * 100)) if total > 0 else 0
    return {"correct": correct, "total": total, "pct": pct}


@app.get("/api/resume")
async def resume_session(student_id: str):
    row = await get_latest_session(student_id)
    if not row:
        return {"status": "none"}

    return {"status": "ok", "session_id": row["session_id"], "topic_id": row["topic_id"], "state": row["state"]}


@app.get("/api/next")
async def api_next(session_id: str):
    p = db.pool()
    async with p.acquire() as conn:
        return await get_next_question_or_complete(conn, session_id)
