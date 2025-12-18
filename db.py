import asyncpg
import os


# Database connection pool
pool = None


async def init_db():
    """Initialize database connection pool."""
    global pool
    db_url = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/tutoring")
    pool = await asyncpg.create_pool(db_url)


async def close_db():
    """Close database connection pool."""
    global pool
    if pool:
        await pool.close()


async def get_connection():
    """Get a connection from the pool."""
    global pool
    if not pool:
        await init_db()
    return pool


async def execute(query, *args):
    """Execute a query and return results."""
    pool_conn = await get_connection()
    async with pool_conn.acquire() as conn:
        return await conn.fetch(query, *args)


async def execute_one(query, *args):
    """Execute a query and return a single row."""
    pool_conn = await get_connection()
    async with pool_conn.acquire() as conn:
        return await conn.fetchrow(query, *args)


async def execute_scalar(query, *args):
    """Execute a query and return a scalar value."""
    pool_conn = await get_connection()
    async with pool_conn.acquire() as conn:
        return await conn.fetchval(query, *args)


async def execute_many(query, *args_list):
    """Execute a query multiple times."""
    pool_conn = await get_connection()
    async with pool_conn.acquire() as conn:
        return await conn.executemany(query, args_list)
