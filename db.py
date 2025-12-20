import os
import asyncpg

_pool = None

async def init_pool():
    global _pool
    if _pool is None:
        # Build connection string from individual Postgres env vars
        user = os.environ.get("PGUSER", "postgres")
        password = os.environ.get("PGPASSWORD", "password")
        host = os.environ.get("PGHOST", "localhost")
        port = os.environ.get("PGPORT", "5432")
        database = os.environ.get("PGDATABASE", "postgres")
        
        dsn = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=1,
            max_size=5
        )
        
        # Create attempts table if it doesn't exist
        async with _pool.acquire() as c:
            await c.execute("""
            CREATE TABLE IF NOT EXISTS attempts (
              id SERIAL PRIMARY KEY,
              student_id VARCHAR(36) NOT NULL,
              session_id VARCHAR(36) NOT NULL,
              topic_id VARCHAR(100) NOT NULL,
              question_id VARCHAR(100) NOT NULL,
              user_answer TEXT NOT NULL,
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

def pool():
    return _pool

async def create_session(student_id: str, topic_id: str = "", state: str = "QUIZ", current_question_id: str = None):
    import uuid
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

async def insert_attempt(student_id: str, session_id: str, topic_id: str, question_id: str, user_answer: str, is_correct: bool):
    """Record an answer attempt."""
    q = """
    insert into attempts(student_id, session_id, topic_id, question_id, user_answer, is_correct, created_at)
    values($1, $2, $3, $4, $5, $6, now())
    """
    async with pool().acquire() as c:
        await c.execute(q, student_id, session_id, topic_id, question_id, user_answer, is_correct)
