import os
from urllib.parse import urlparse

import asyncpg

_pool: asyncpg.Pool | None = None


def _parse_database_url() -> dict:
    """
    Supports Railway/Supabase DATABASE_URL like:
      postgres://user:pass@host:port/dbname
    """
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")

    u = urlparse(db_url)
    if not u.hostname or not u.path:
        raise RuntimeError("DATABASE_URL is malformed")

    return {
        "user": u.username,
        "password": u.password,
        "database": u.path.lstrip("/"),
        "host": u.hostname,
        "port": u.port or 5432,
        # Railway commonly requires SSL
        "ssl": "require",
    }


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        cfg = _parse_database_url()
        _pool = await asyncpg.create_pool(
            **cfg,
            min_size=1,
            max_size=5,
        )
    return _pool


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized. Call await init_pool() on startup.")
    return _pool


# =========================
# Sessions
# =========================

async def create_session(
    student_id: str,
    topic_id: str,
    state: str = "ACTIVE",
    current_question_id: str | None = None,
) -> str:
    import uuid
    session_id = str(uuid.uuid4())

    q = """
    INSERT INTO sessions(
      session_id, student_id, topic_id, status, state,
      attempt_count, frustration_counter, current_question_id
    )
    VALUES($1,$2,$3,'ACTIVE',$4,0,0,$5)
    """
    async with pool().acquire() as c:
        await c.execute(q, session_id, student_id, topic_id, state, current_question_id)
    return session_id


async def get_session(session_id: str):
    q = "SELECT * FROM sessions WHERE session_id=$1"
    async with pool().acquire() as c:
        return await c.fetchrow(q, session_id)


async def update_session(session_id: str, **fields):
    if not fields:
        return
    keys = list(fields.keys())
    set_clause = ", ".join([f"{k}=${i+2}" for i, k in enumerate(keys)])
    q = f"UPDATE sessions SET {set_clause}, updated_at=now() WHERE session_id=$1"
    values = [fields[k] for k in keys]
    async with pool().acquire() as c:
        await c.execute(q, session_id, *values)


async def get_latest_session(student_id: str):
    q = """
    SELECT session_id, student_id, topic_id, state, status
    FROM sessions
    WHERE student_id = $1
    ORDER BY created_at DESC
    LIMIT 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, student_id)


# =========================
# Topics / Concepts / Questions
# =========================

async def get_topics():
    # Query from topics table (primary), fallback to concepts if topics is empty
    q = """
    SELECT topic_id, title
    FROM topics
    ORDER BY title
    """
    async with pool().acquire() as c:
        rows = await c.fetch(q)
        if rows:
            return [dict(r) for r in rows]
        # Fallback to concepts table for backwards compatibility
        q2 = "SELECT topic_id, title FROM concepts ORDER BY title"
        rows = await c.fetch(q2)
        return [dict(r) for r in rows]


async def get_topic(topic_id: str):
    q = """
    SELECT topic_id, title, grade, subject
    FROM topics
    WHERE topic_id=$1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, topic_id)


async def pick_question(topic_id: str):
    q = """
    SELECT question_id, prompt, answer_key, hint1, hint2, reveal_explain
    FROM questions
    WHERE topic_id=$1
    ORDER BY random()
    LIMIT 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, topic_id)


async def get_question(question_id: str):
    q = """
    SELECT question_id, prompt, answer_key, hint1, hint2, reveal_explain
    FROM questions
    WHERE question_id=$1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, question_id)


# =========================
# Option B — SESSION-level seen
# uses table: session_seen_questions(session_id, question_id)
# =========================

async def mark_question_seen_in_session(session_id: str, question_id: str):
    q = """
    INSERT INTO session_seen_questions(session_id, question_id)
    VALUES($1,$2)
    ON CONFLICT DO NOTHING
    """
    async with pool().acquire() as c:
        await c.execute(q, session_id, question_id)


async def pick_question_unseen_in_session(session_id: str, topic_id: str):
    q = """
    SELECT question_id, prompt, answer_key, hint1, hint2, reveal_explain
    FROM questions
    WHERE topic_id=$1
      AND NOT EXISTS (
        SELECT 1
        FROM session_seen_questions ssq
        WHERE ssq.session_id=$2
          AND ssq.question_id=questions.question_id
      )
    ORDER BY random()
    LIMIT 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, topic_id, session_id)


# =========================
# Lifetime seen (per-student per-topic) — KEEP existing PK behavior
# uses table: seen_questions(student_id, topic_id, question_id) PK(student_id,topic_id,question_id)
# =========================

async def mark_seen_lifetime(student_id: str, topic_id: str, question_id: str):
    q = """
    INSERT INTO seen_questions(student_id, topic_id, question_id)
    VALUES($1,$2,$3)
    ON CONFLICT DO NOTHING
    """
    async with pool().acquire() as c:
        await c.execute(q, student_id, topic_id, question_id)


async def get_next_question_lifetime(student_id: str, topic_id: str):
    q = """
    SELECT question_id, prompt, answer_key, hint1, hint2, reveal_explain
    FROM questions
    WHERE topic_id=$1
      AND NOT EXISTS (
        SELECT 1
        FROM seen_questions sq
        WHERE sq.student_id=$2
          AND sq.topic_id=$1
          AND sq.question_id=questions.question_id
      )
    ORDER BY random()
    LIMIT 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, topic_id, student_id)


# =========================
# Attempts
# =========================

async def insert_attempt(
    session_id: str,
    student_id: str,
    topic_id: str,
    question_id: str,
    is_correct: bool,
    user_answer: str | None = None,
):
    q = """
    INSERT INTO attempts (session_id, student_id, topic_id, question_id, is_correct, user_answer)
    VALUES ($1,$2,$3,$4,$5,$6)
    RETURNING attempt_id, created_at;
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, session_id, student_id, topic_id, question_id, is_correct, user_answer)


async def count_correct_questions(student_id: str, topic_id: str) -> int:
    q = """
    SELECT COUNT(DISTINCT question_id)
    FROM attempts
    WHERE student_id=$1 AND topic_id=$2 AND is_correct=true;
    """
    async with pool().acquire() as c:
        n = await c.fetchval(q, student_id, topic_id)
        return int(n or 0)


async def check_and_mark_completion(session_id: str, topic_id: str) -> bool:
    async with pool().acquire() as c:
        total = await c.fetchval("SELECT COUNT(*) FROM questions WHERE topic_id=$1", topic_id)
        if not total or total == 0:
            return False

        correct = await c.fetchval(
            """
            SELECT COUNT(DISTINCT question_id)
            FROM attempts
            WHERE session_id=$1 AND topic_id=$2 AND is_correct=true
            """,
            session_id, topic_id
        )
        correct = correct or 0

        if correct >= total:
            await c.execute(
                "UPDATE sessions SET state='COMPLETED', status='COMPLETED', completed_at=now() WHERE session_id=$1",
                session_id
            )
            return True

        return False
