from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import time
import uuid
import os
import logging
import traceback
import grpc

import tutoring_pb2
import tutoring_pb2_grpc
from db import get_topics, init_pool, get_latest_session
import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s:%(lineno)d - %(message)s",
)

logger = logging.getLogger("idna.turn_grpc")

# Deploy-proof version tag (check logs / include in reply)
TURN_ROUTER_VERSION = "v2-2A"

# Defaults (Phase 2A minimal diff)
DEFAULT_STUDENT_ID = "00000000-0000-0000-0000-000000000001"
DEFAULT_TOPIC_ID = "g6_math_add_01"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Models
# -------------------------

class TurnIn(BaseModel):
    text: str
    session_id: str | None = None

class TurnOut(BaseModel):
    ok: bool
    session_id: str
    intent: str
    reply: str

# -------------------------
# Health + startup
# -------------------------

@app.get("/healthz")
def healthz():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    await init_pool()

# -------------------------
# gRPC tutoring endpoints
# -------------------------

# Use Railway env var. Default targets the Railway private service name.
GRPC_TARGET = os.getenv("GRPC_TARGET")
# "1" to use TLS, "0" for insecure (typical for private network)
GRPC_USE_TLS = os.getenv("GRPC_USE_TLS", "0")

logger.info("GRPC_TARGET=%s GRPC_USE_TLS=%s", GRPC_TARGET, GRPC_USE_TLS)

_GRPC_OPTIONS = [
    ("grpc.keepalive_time_ms", 30_000),
    ("grpc.keepalive_timeout_ms", 10_000),
    ("grpc.http2.max_pings_without_data", 0),
    ("grpc.keepalive_permit_without_calls", 1),
]

def _make_channel(target: str) -> grpc.Channel:
    # Auto TLS for public Railway domains unless explicitly disabled
    auto_tls = (".up.railway.app" in target)
    use_tls = (GRPC_USE_TLS == "1") or (auto_tls and GRPC_USE_TLS != "0")

    if use_tls:
        creds = grpc.ssl_channel_credentials()
        return grpc.secure_channel(target, creds, options=_GRPC_OPTIONS)

    return grpc.insecure_channel(target, options=_GRPC_OPTIONS)

CHANNEL = _make_channel(GRPC_TARGET)
STUB = tutoring_pb2_grpc.TutoringServiceStub(CHANNEL)

class StartReq(BaseModel):
    student_id: str = DEFAULT_STUDENT_ID
    topic_id: str = DEFAULT_TOPIC_ID

class TurnReq(BaseModel):
    student_id: str
    session_id: str
    user_text: str

def _start_session_grpc(student_id: str, topic_id: str):
    # timeout avoids silent hangs
    return STUB.StartSession(
        tutoring_pb2.StartSessionRequest(student_id=student_id, topic_id=topic_id),
        timeout=20
    )

def _turn_grpc(student_id: str, session_id: str, user_text: str):
    # timeout avoids silent hangs
    return STUB.Turn(
        tutoring_pb2.TurnRequest(
            student_id=student_id,
            session_id=session_id,
            user_text=user_text,
        ),
        timeout=20
    )

# -------------------------
# Phase 2A: /turn router
#   - greet/unknown/empty => local reply (as before)
#   - question => gRPC Turn (or StartSession if no session_id)
# -------------------------

def _classify_intent(text: str) -> tuple[str, bool]:
    t = (text or "").lower().strip()
    tokens = [tok for tok in t.replace("?", " ? ").split() if tok]

    greet_words = {"hi", "hello", "hey"}
    wh_words = {"what", "why", "how", "when", "where"}

    is_question = False
    if "?" in t:
        is_question = True
    elif tokens:
        if tokens[0] in wh_words:
            is_question = True
        elif tokens[0] in greet_words and len(tokens) > 1 and tokens[1] in wh_words:
            is_question = True

    if not (text or "").strip():
        return "empty", False
    if is_question:
        return "question", True
    if any(w in tokens for w in greet_words):
        return "greet", False
    return "unknown", False

@app.post("/turn", response_model=TurnOut)
def turn(payload: TurnIn):
    text = (payload.text or "").strip()
    sid_in = (payload.session_id or "").strip() or None

    intent, is_question = _classify_intent(text)

    logger.info(
        "TURN_ROUTER_VERSION=%s GRPC_TARGET=%s intent=%s sid_in=%r text=%r",
        TURN_ROUTER_VERSION, GRPC_TARGET, intent, sid_in, text
    )

    # Non-question paths stay local (minimal diff)
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
                "reply": f"Hi. Say a question like: 'Explain fractions'. [{TURN_ROUTER_VERSION}]",
            }
        return {
            "ok": True,
            "session_id": sid,
            "intent": "unknown",
            "reply": f"Say it as a question. You said: {text} [{TURN_ROUTER_VERSION}]",
        }

    # Question path => gRPC
    student_id = DEFAULT_STUDENT_ID

    try:
        # If no session_id yet, start a session and return the first tutor prompt
        if not sid_in:
            start_resp = _start_session_grpc(student_id=student_id, topic_id=DEFAULT_TOPIC_ID)
            return {
                "ok": True,
                "session_id": start_resp.session_id,
                "intent": "start",
                "reply": start_resp.tutor_text,
            }

        # Otherwise, continue the session with Turn()
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
        raise HTTPException(
            status_code=502,
            detail={"grpc_code": str(e.code()), "grpc_details": e.details()}
        )

    except Exception:
        logger.error("Non-gRPC exception in /turn")
        logger.error("traceback:\n%s", traceback.format_exc())
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
        print("SESSION_MARKED_COMPLETED", session_id)
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
    print("START HIT", time.time(), "BODY=", req.dict())
    print("START received:", {"student_id": req.student_id, "topic_id": req.topic_id})

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

        print(f"RESTART CHECK: student_id={req.student_id}, topic_id={req.topic_id}, total={total}, correct={correct}")
        if total > 0 and correct >= total:
            print(f"RESTART BLOCKED: Topic completed ({correct}/{total})")
            return {
                "blocked": True,
                "state": "COMPLETED",
                "session_id": None,
                "topic_id": req.topic_id,
                "tutor": "Topic already completed. Restart blocked.",
                "message": "Topic already completed. Restart blocked."
            }

    resp = STUB.StartSession(tutoring_pb2.StartSessionRequest(
        student_id=req.student_id,
        topic_id=req.topic_id
    ), timeout=20)

    print(f"NORMAL START: state={resp.state}, tutor_text={resp.tutor_text}")
    return {
        "session_id": resp.session_id,
        "state": int(resp.state),
        "tutor_text": resp.tutor_text
    }

@app.post("/api/reset")
async def reset_student_progress(student_id: str, topic_id: str):
    p = db.pool()
    async with p.acquire() as conn:
        await conn.execute(
            "DELETE FROM attempts WHERE student_id=$1 AND topic_id=$2",
            student_id, topic_id
        )
    return {"status": "ok", "message": f"Reset progress for {student_id} on {topic_id}"}

# ✅ FIXED /turn_grpc
@app.post("/turn_grpc")
def turn_grpc(req: TurnReq):
    try:
        grpc_req = tutoring_pb2.TurnRequest(
            student_id=req.student_id,
            session_id=req.session_id,
            user_text=req.user_text
        )

        resp = STUB.Turn(grpc_req, timeout=20)

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

        try:
            logger.error("gRPC trailing_metadata=%s", e.trailing_metadata())
        except Exception:
            pass

        logger.error("traceback:\n%s", traceback.format_exc())

        raise HTTPException(
            status_code=502,
            detail={"grpc_code": str(e.code()), "grpc_details": e.details()}
        )

    except Exception:
        logger.error("Non-gRPC exception in /turn_grpc")
        logger.error("traceback:\n%s", traceback.format_exc())
        raise

@app.get("/api/topics")
async def api_topics():
    return await get_topics()

@app.get("/api/progress")
async def api_progress(student_id: str, topic_id: str):
    p = db.pool()
    async with p.acquire() as c:
        total = await c.fetchval(
            "SELECT COUNT(*) FROM questions WHERE topic_id = $1",
            topic_id
        ) or 0

        correct = await c.fetchval(
            "SELECT COUNT(DISTINCT question_id) FROM attempts WHERE student_id = $1 AND topic_id = $2 AND is_correct = true",
            student_id,
            topic_id
        ) or 0

    pct = int((correct / total * 100)) if total > 0 else 0
    print("PROGRESS", {"student_id": student_id, "topic_id": topic_id, "correct": correct, "total": total, "pct": pct})
    return {"correct": correct, "total": total, "pct": pct}

@app.get("/api/resume")
async def resume_session(student_id: str):
    row = await get_latest_session(student_id)
    if not row:
        return {"status": "none"}

    return {
        "status": "ok",
        "session_id": row["session_id"],
        "topic_id": row["topic_id"],
        "state": row["state"]
    }

@app.get("/api/next")
async def api_next(session_id: str):
    print("NEXT HIT", time.time(), "session_id=", session_id)
    p = db.pool()
    async with p.acquire() as conn:
        result = await get_next_question_or_complete(conn, session_id)
        print("NEXT_RESULT", result)
        return result

# Static (keep last)


app.mount("/", StaticFiles(directory="static", html=True), name="static")
def grpc_ping():
    target = os.getenv("GRPC_TARGET")
    use_tls = os.getenv("GRPC_USE_TLS", "0") == "1"

    if not target:
        return {"ok": False, "error": "GRPC_TARGET not set"}

    if use_tls:
        channel = grpc.secure_channel(target, grpc.ssl_channel_credentials())
    else:
        channel = grpc.insecure_channel(target)

    try:
        grpc.channel_ready_future(channel).result(timeout=3)
        return {"ok": True, "target": target}
    except Exception as e:
        return {"ok": False, "target": target, "error": str(e)}
