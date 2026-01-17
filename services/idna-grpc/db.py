import os
import json
import asyncpg
from urllib.parse import urlparse

_pool = None


def _parse_database_url() -> dict:
    """Parse DATABASE_URL into connection parameters."""
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        u = urlparse(db_url)
        return {
            "user": u.username,
            "password": u.password,
            "database": u.path.lstrip("/"),
            "host": u.hostname,
            "port": u.port or 5432,
            "ssl": "require",
        }
    # Fallback to individual env vars for local dev
    return {
        "user": os.environ.get("PGUSER", "postgres"),
        "password": os.environ.get("PGPASSWORD", "password"),
        "database": os.environ.get("PGDATABASE", "postgres"),
        "host": os.environ.get("PGHOST", "localhost"),
        "port": int(os.environ.get("PGPORT", "5432")),
    }


async def init_pool():
    global _pool
    if _pool is None:
        cfg = _parse_database_url()
        _pool = await asyncpg.create_pool(
            **cfg,
            min_size=1,
            max_size=5
        )

        # Create/update tables if they don't exist
        async with _pool.acquire() as c:
            # Add fsm_data column to sessions for FSM state storage
            await c.execute("""
            ALTER TABLE sessions
            ADD COLUMN IF NOT EXISTS fsm_data JSONB DEFAULT '{}';
            """)

            # Update seen_questions table to add student_id and topic_id if they don't exist
            await c.execute("""
            ALTER TABLE seen_questions
            ADD COLUMN IF NOT EXISTS student_id VARCHAR(36);
            """)
            await c.execute("""
            ALTER TABLE seen_questions
            ADD COLUMN IF NOT EXISTS topic_id VARCHAR(100);
            """)

            # Create attempts table if it doesn't exist
            await c.execute("""
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
            """)
            await c.execute("""
            CREATE INDEX IF NOT EXISTS idx_attempts_student_topic ON attempts(student_id, topic_id);
            """)
            await c.execute("""
            CREATE INDEX IF NOT EXISTS idx_attempts_session ON attempts(session_id);
            """)

def pool() -> asyncpg.Pool | None:
    return _pool


async def close_pool():
    """Gracefully close the database connection pool."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None

async def create_session(
    student_id: str,
    topic_id: str = "",
    state: str = "ACTIVE",
    current_question_id: str | None = None,
    fsm_data: dict | None = None
):
    import uuid
    session_id = str(uuid.uuid4())
    fsm_json = json.dumps(fsm_data) if fsm_data else "{}"

    q = """
    INSERT INTO sessions(session_id, student_id, topic_id, state, attempt_count, frustration_counter, current_question_id, fsm_data)
    VALUES($1, $2, $3, $4, 0, 0, $5, $6::jsonb)
    """
    async with pool().acquire() as c:
        await c.execute(q, session_id, student_id, topic_id, state, current_question_id, fsm_json)
    return session_id

async def get_session(session_id: str):
    q = "SELECT * FROM sessions WHERE session_id=$1"
    async with pool().acquire() as c:
        row = await c.fetchrow(q, session_id)
        if row:
            # Convert to dict and parse fsm_data if present
            result = dict(row)
            if result.get("fsm_data"):
                # asyncpg returns JSONB as dict already, but handle string case
                if isinstance(result["fsm_data"], str):
                    result["fsm_data"] = json.loads(result["fsm_data"])
            return result
        return None

async def update_session(session_id: str, **fields):
    keys = list(fields.keys())
    if not keys:
        return

    # Convert fsm_data dict to JSON string for JSONB column
    if "fsm_data" in fields and isinstance(fields["fsm_data"], dict):
        fields["fsm_data"] = json.dumps(fields["fsm_data"])

    # Build SET clause with proper casting for fsm_data
    set_parts = []
    for i, k in enumerate(keys):
        if k == "fsm_data":
            set_parts.append(f"{k}=${i+2}::jsonb")
        else:
            set_parts.append(f"{k}=${i+2}")
    set_clause = ", ".join(set_parts)

    q = f"UPDATE sessions SET {set_clause}, updated_at=now() WHERE session_id=$1"
    values = [fields[k] for k in keys]
    async with pool().acquire() as c:
        await c.execute(q, session_id, *values)

async def get_topic(topic_id: str):
    """Get a specific topic by ID."""
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
    """Pick a question not yet seen in this session."""
    q = """
    select question_id, prompt, answer_key, hint1, hint2, reveal_explain
    from questions
    where topic_id=$1
    and question_id not in (select question_id from seen_questions where session_id=$2)
    order by random()
    limit 1
    """
    async with pool().acquire() as c:
        return await c.fetchrow(q, topic_id, session_id)

async def mark_question_seen(session_id: str, question_id: str):
    """Mark a question as seen in this session."""
    q = """
    insert into seen_questions(session_id, question_id)
    values($1, $2)
    on conflict do nothing
    """
    async with pool().acquire() as c:
        await c.execute(q, session_id, question_id)

async def mark_seen(student_id: str, topic_id: str, session_id: str, question_id: str):
    """Mark a question as seen for this student in the topic."""
    q = """
    insert into seen_questions(student_id, topic_id, session_id, question_id)
    values ($1, $2, $3, $4)
    on conflict do nothing
    """
    async with pool().acquire() as c:
        await c.execute(q, student_id, topic_id, session_id, question_id)

async def get_next_question(student_id: str, topic_id: str):
    """Get next unseen question for this student in the topic."""
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
    """Get next question for this session, excluding only questions answered correctly in THIS session."""
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

async def insert_attempt(session_id: str, student_id: str, topic_id: str, question_id: str, is_correct: bool):
    q = """
    insert into public.attempts (session_id, student_id, topic_id, question_id, is_correct)
    values ($1, $2, $3, $4, $5)
    returning id, created_at;
    """
    try:
        async with pool().acquire() as c:
            row = await c.fetchrow(q, session_id, student_id, topic_id, question_id, is_correct)
        print("INSERT ATTEMPT OK", dict(row) if row else row)
        return row
    except Exception as e:
        print("INSERT ATTEMPT FAILED", repr(e))
        raise

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

async def count_correct_questions(student_id: str, topic_id: str):
    """Count distinct questions a student answered correctly for a topic."""
    q = """
    select count(distinct question_id)
    from public.attempts
    where student_id = $1 and topic_id = $2 and is_correct = true;
    """
    async with pool().acquire() as c:
        count = await c.fetchval(q, student_id, topic_id)
        return count or 0

async def check_and_mark_completion(session_id: str, topic_id: str):
    """Check if all questions in topic are answered correctly. If so, mark session COMPLETED."""
    p = pool()
    async with p.acquire() as c:
        # Count total questions in topic
        total = await c.fetchval("SELECT COUNT(*) FROM questions WHERE topic_id=$1", topic_id)
        if not total or total == 0:
            return False
        
        # Count distinct correct answers for this session
        correct = await c.fetchval(
            """
            SELECT COUNT(DISTINCT question_id)
            FROM attempts
            WHERE session_id=$1 AND topic_id=$2 AND is_correct=true
            """,
            session_id, topic_id
        )
        correct = correct or 0
        
        # If all questions answered correctly, mark session COMPLETED
        if correct >= total:
            await c.execute(
                "UPDATE sessions SET state='COMPLETED' WHERE session_id=$1",
                session_id
            )
            print("SESSION_MARKED_COMPLETED", session_id)
            return True
        
        return False
