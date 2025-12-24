from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import grpc
import asyncio
import time

import tutoring_pb2
import tutoring_pb2_grpc
from db import get_topics, init_pool, pool, get_latest_session
import db

app = FastAPI()

@app.on_event("startup")
async def startup():
    await init_pool()

# gRPC channel to your existing server
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
    # 1) Load session
    session = await conn.fetchrow(
        "SELECT session_id, topic_id, status FROM sessions WHERE session_id=$1",
        session_id
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 2) Guard: already completed => never ask new question
    if session["status"] == "COMPLETED":
        return {
            "session_id": session_id,
            "topic_id": session["topic_id"],
            "state": "COMPLETED",
            "question": None,
            "message": "Session already completed."
        }

    topic_id = session["topic_id"]

    # 3) Pick next unanswered question (unanswered = no correct attempt in this session)
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

    # 4) If none left => mark COMPLETED in DB and return terminal response
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

    # 5) Save current question in session
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
def start(req: StartReq):
    print("START HIT", time.time(), "BODY=", req.dict())
    print("START received:", {"student_id": req.student_id, "topic_id": req.topic_id})
    resp = STUB.StartSession(tutoring_pb2.StartSessionRequest(
        student_id=req.student_id,
        topic_id=req.topic_id
    ))
    return {
        "session_id": resp.session_id,
        "state": int(resp.state),
        "tutor_text": resp.tutor_text
    }

@app.post("/turn")
async def turn(req: TurnReq):
    p = db.pool()
    async with p.acquire() as conn:
        # Fetch session info to get topic_id
        session = await conn.fetchrow(
            "SELECT session_id, topic_id FROM sessions WHERE session_id=$1",
            req.session_id
        )
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        topic_id = session["topic_id"]
        
        # HARD GUARD: if already completed, don't accept answers
        total = await conn.fetchval("SELECT COUNT(*) FROM questions WHERE topic_id=$1", topic_id) or 0
        correct = await conn.fetchval(
            """
            SELECT COUNT(DISTINCT question_id)
            FROM attempts
            WHERE student_id=$1 AND topic_id=$2 AND is_correct=true
            """,
            req.student_id, topic_id
        ) or 0
        
        if total > 0 and correct >= total:
            await conn.execute(
                "UPDATE sessions SET state='COMPLETED' WHERE session_id=$1",
                req.session_id
            )
            return {
                "session_id": req.session_id,
                "topic_id": topic_id,
                "state": "COMPLETED",
                "question": None,
                "message": "Topic already completed."
            }
    
    resp = STUB.Turn(tutoring_pb2.TurnRequest(
        student_id=req.student_id,
        session_id=req.session_id,
        user_text=req.user_text
    ))

    # These fields exist only if your proto added them.
    # If not, they'll simply be absent and that's fine.
    out = {
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
    return out

@app.get("/api/topics")
async def api_topics():
    topics = await get_topics()
    return topics

@app.get("/api/progress")
async def api_progress(student_id: str, topic_id: str):
    """Get progress for a student on a topic: correct, total, percentage."""
    p = db.pool()
    async with p.acquire() as c:
        # Total questions in topic
        total_result = await c.fetchval(
            "SELECT COUNT(*) FROM questions WHERE topic_id = $1",
            topic_id
        )
        total = total_result or 0
        
        # Correct answers for this student in this topic (count distinct questions)
        correct_result = await c.fetchval(
            "SELECT COUNT(DISTINCT question_id) FROM attempts WHERE student_id = $1 AND topic_id = $2 AND is_correct = true",
            student_id,
            topic_id
        )
        correct = correct_result or 0
        
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
    """Get next question for session or mark as completed."""
    print("NEXT HIT", time.time(), "session_id=", session_id)
    p = db.pool()
    async with p.acquire() as conn:
        result = await get_next_question_or_complete(conn, session_id)
        print("NEXT_RESULT", result)
        return result

# Serve static files (HTML, CSS, JS)
app.mount("/", StaticFiles(directory="static", html=True), name="static")
