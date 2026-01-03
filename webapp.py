from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import grpc
import time
import uuid

import tutoring_pb2
import tutoring_pb2_grpc
from db import get_topics, init_pool, get_latest_session
import db

# Deploy-proof version tag (check logs / include in reply)
TURN_ROUTER_VERSION = "v2"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Phase-1 /turn (echo router)
# -------------------------

class TurnIn(BaseModel):
    text: str
    session_id: str | None = None

class TurnOut(BaseModel):
    ok: bool
    session_id: str
    intent: str
    reply: str

@app.post("/turn", response_model=TurnOut)
def turn(payload: TurnIn):
    text = (payload.text or "").strip()
    sid = payload.session_id or str(uuid.uuid4())

    t = text.lower().strip()
    print(f"TURN_ROUTER_VERSION={TURN_ROUTER_VERSION} text={t!r}")

    # Tokenize
    tokens = [tok for tok in t.replace("?", " ? ").split() if tok]

    greet_words = {"hi", "hello", "hey"}
    wh_words = {"what", "why", "how", "when", "where"}

    # Treat "hello what is 2+2" as a question (not greet)
    is_question = False
    if "?" in t:
        is_question = True
    elif tokens:
        if tokens[0] in wh_words:
            is_question = True
        elif tokens[0] in greet_words and len(tokens) > 1 and tokens[1] in wh_words:
            is_question = True

    if not text:
        intent = "empty"
        reply = "Say something."
    elif is_question:
        intent = "question"
        reply = f"Got it. You asked: {text} [{TURN_ROUTER_VERSION}]"
    elif any(w in tokens for w in greet_words):
        intent = "greet"
        reply = f"Hi. Say a question like: 'Explain fractions'. [{TURN_ROUTER_VERSION}]"
    else:
        intent = "unknown"
        reply = f"Say it as a question. You said: {text} [{TURN_ROUTER_VERSION}]"

    return {"ok": True, "session_id": sid, "intent": intent, "reply": reply}

# -------------------------
# Health
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

CHANNEL = grpc.insecure_channel("localhost:50051")
STUB = tutoring_pb2_grpc.TutoringServiceStub(CHANNEL)

class StartReq(BaseModel):
    student_id: str = "00000000-0000-0000-0000-000000000001"
    topic_id: str = "g6_math_add_01"

class TurnReq(BaseModel):
    student_id: str
    session_id: str
    user_text: str

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
    ))
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

@app.post("/turn_grpc")
def turn_grpc(req: TurnReq):
    resp = STUB.Turn(tutoring_pb2.TurnRequest(
        student_id=req.student_id,
        session_id=req.session_id,
        user_text=req.user_text
    ))

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
