import os
import uuid
from urllib.parse import urlparse

import asyncpg

_pool: asyncpg.Pool | None = None


def _pool_kwargs_from_env() -> dict:
    """
    Preferred: DATABASE_URL (Railway/Supabase)
    Fallback: PG* env vars
    """
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        u = urlparse(db_url)
        # Railway Postgres typically requires SSL
        return {
            "user": u.username,
            "password": u.password,
            "database": (u.path or "").lstrip("/"),
            "host": u.hostname,
            "port": u.port or 5432,
            "ssl": "require",
        }

    # Fallback: discrete PG env vars (local dev)
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "password")
    host = os.environ.get("PGHOST", "localhost")
    port = int(os.environ.get("PGPORT", "5432"))
    database = os.environ.get("PGDATABASE", "postgres")
    return {
        "user": user,
        "password": password,
        "database": database,
        "host": host,
        "port": port,
        # local usually no ssl; if you need it, set PGSSLMODE=require and handle here
    }


async def init_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        cfg = _pool_kwargs_from_env()
        _pool = await asyncpg.create_pool(
            min_size=1,
            max_size=5,
            **cfg,
        )
        await _run_migrations(_pool)
    return _pool


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("DB pool is not initialized. Call await init_pool() at startup.")
    return _pool


async def _run_migrations(p: asyncpg.Pool) -> None:
    """
    Idempotent schema updates needed by the app.
    NOTE: on conflict do nothing requires UNIQUE constraints. We create them.
    """
    async with p.acquire() as c:
        # --- seen_questions ---
        # Expect at minimum these columns for your current functions:
        # student_id, topic_id, session_id, question_id
        await c.execute(
            """
            CREATE TABLE IF NOT EXISTS seen_questions (
              id SERIAL PRIMARY KEY,
              student_id VARCHAR(36),
              topic_id VARCHAR(100),
              session_id VARCHAR(36) NOT NULL,
              question_id VARCHAR(100) NOT NULL,
              created_at TIMESTAMP DEFAULT NOW()
            );
            """
        )

        # Ensure columns exist if table was created earlier with fewer columns
        await c.execute("""ALTER TABLE seen_questions ADD COLUMN IF NOT EXISTS student_id VARCHAR(36);""")
        await c.execute("""ALTER TABLE seen_questions ADD COLUMN IF NOT EXISTS topic_id VARCHAR(100);""")
        await c.execute("""ALTER TABLE seen_questions ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT NOW();""")

        # Unique constraints so ON CONFLICT works
        # 1) Session-level seen tracking
        await c.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_seen_questions_session
            ON seen_questions(session_id, question_id);
            """
        )
        # 2) Student+topic-level seen tracking (optional but matches get_next_question)
        await c.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_seen_questions_student_topic
            ON seen_questions(student_id, topic_id, question_id);
            """
        )

        # --- attempts ---
        await c.execute(
            """
            CREATE TABLE IF NOT EXISTS attempts (
              id SERIAL PRIMARY KEY,
              student_id VARCHAR(36) NOT NULL,
              session_id VARCHAR(36) NOT NULL,
              topic_id VARCHAR(100) NOT NULL,
              question_id VARCHAR(100) NOT NULL,
              user_answer TEXT,
              is_correct BOOLEAN NOT NULL,
              created_at TIMESTAMP DEFAULT NOW()
            );
            """
        )

        await c.execute("""CREATE INDEX IF NOT EXISTS idx_attempts_student_topic ON attempts(student_id, topic_id);""")
        await c.execute("""CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);""")


# -------------------------
# App queries (your functions)
# -------------------------

async def create_session(
    student_id: str,
    topic_id: str = "",
    state: str = "ACTIVE",
    current_question_id: str | None = None,
) -> str:
    session_id = str(uuid.uuid4())
    q = """
    insert into sessions(session_id, student_id, topic_id, state, attempt_count, frustration_counter, current_question_id)
    values($1,$2,$3,$4,0,0,$5)
    """
    async with pool().acquire() as c:
        await c.execute(q, session_id, student_id, topic_id, state, current_question_id)
    return session_id


async def get_session(session_id: str):
    q = "select * from sessions where session_id=$1"
    async with pool().acquire() as c:
        return await c.fetchrow(q, session_id)


async def update_session(session_id: str, **fields):
    keys = list(fields.keys())
    if not keys:
        return
    set_clause = ", ".join([f"{k}=${i+2}" for i, k in enumerate(keys)])
    q = f"update sessions set {set_clause}, updated_at=now() where session_id=$1"
    values = [fields[k] for k in keys]
    async with pool().acquire() as c:
        await c.execute(q, session_id, *values)


async def get_topic(topic_id: str):
    q = """
    select topic_id, title, explain_text
    from concepts
    where topic_id=$1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, topic_id)


async def pick_topic(grade: int, subject: str, language: str = "en"):
    q = """
    select topic_id, title, explain_text
    from concepts
    where grade=$1 and subject=$2 and language=$3
    order by created_at asc
    limit 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, grade, subject, language)


async def pick_question(topic_id: str):
    q = """
    select question_id, prompt, answer_key, hint1, hint2, reveal_explain
    from questions
    where topic_id=$1
    order by random()
    limit 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, topic_id)


async def get_question(question_id: str):
    q = """
    select question_id, prompt, answer_key, hint1, hint2, reveal_explain
    from questions
    where question_id=$1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, question_id)


async def pick_question_unseen(session_id: str, topic_id: str):
    q = """
    select question_id, prompt, answer_key, hint1, hint2, reveal_explain
    from questions
    where topic_id=$1
      and question_id not in (
        select question_id from seen_questions where session_id=$2
      )
    order by random()
    limit 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, topic_id, session_id)


async def mark_seen(student_id: str, topic_id: str, session_id: str, question_id: str):
    q = """
    insert into seen_questions(student_id, topic_id, session_id, question_id)
    values ($1, $2, $3, $4)
    on conflict do nothing
    """
    async with pool().acquire() as c:
        await c.execute(q, student_id, topic_id, session_id, question_id)


async def get_next_question(student_id: str, topic_id: str):
    q = """
    select question_id, prompt, answer_key, hint1, hint2, reveal_explain
    from questions
    where topic_id=$1
      and not exists (
        select 1
        from seen_questions sq
        where sq.student_id=$2
          and sq.topic_id=$1
          and sq.question_id=questions.question_id
      )
    order by random()
    limit 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, topic_id, student_id)


async def get_next_question_in_session(session_id: str, topic_id: str):
    q = """
    select question_id, prompt, answer_key, hint1, hint2, reveal_explain
    from questions
    where topic_id=$1
      and not exists (
        select 1
        from attempts a
        where a.session_id=$2
          and a.question_id=questions.question_id
          and a.is_correct=true
      )
    order by random()
    limit 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, topic_id, session_id)


async def insert_attempt(
    session_id: str,
    student_id: str,
    topic_id: str,
    question_id: str,
    is_correct: bool,
    user_answer: str | None = None,
):
    q = """
    insert into public.attempts (session_id, student_id, topic_id, question_id, is_correct, user_answer)
    values ($1, $2, $3, $4, $5, $6)
    returning id, created_at;
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, session_id, student_id, topic_id, question_id, is_correct, user_answer)


async def get_topics():
    q = """
    select topic_id, title
    from concepts
    order by grade, subject, title
    """
    async with pool().acquire() as c:
        rows = await c.fetch(q)
        return [dict(r) for r in rows]


async def get_latest_session(student_id: str):
    q = """
    select session_id, student_id, topic_id, state
    from sessions
    where student_id = $1
    order by created_at desc
    limit 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, student_id)


async def count_correct_questions(student_id: str, topic_id: str) -> int:
    q = """
    select count(distinct question_id)
    from public.attempts
    where student_id = $1 and topic_id = $2 and is_correct = true;
    """
    async with pool().acquire() as c:
        count = await c.fetchval(q, student_id, topic_id)
        return int(count or 0)


async def check_and_mark_completion(session_id: str, topic_id: str) -> bool:
    async with pool().acquire() as c:
        total = await c.fetchval("SELECT COUNT(*) FROM questions WHERE topic_id=$1", topic_id)
        if not total:
            return False

        correct = await c.fetchval(
            """
            SELECT COUNT(DISTINCT question_id)
            FROM attempts
            WHERE session_id=$1 AND topic_id=$2 AND is_correct=true
            """,
            session_id,
            topic_id,
        )
        correct = correct or 0

        if correct >= total:
            await c.execute("UPDATE sessions SET state='COMPLETED' WHERE session_id=$1", session_id)
            return True

        return False
