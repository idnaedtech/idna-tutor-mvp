import os
import asyncpg

_pool = None

async def init_pool():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=os.environ["DATABASE_URL"],
            min_size=1,
            max_size=5
        )

def pool():
    return _pool

async def create_session(session_id: str, student_id: str):
    q = """
    insert into sessions(session_id, student_id, state, attempt_count, frustration_counter, question)
    values($1,$2,'EXPLAIN',0,0,'What is 2 + 2?')
    """
    async with pool().acquire() as c:
        await c.execute(q, session_id, student_id)

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
