import os
import asyncio
import asyncpg

async def main():
    # Build connection string from env vars
    user = os.environ.get("PGUSER", "postgres")
    password = os.environ.get("PGPASSWORD", "password")
    host = os.environ.get("PGHOST", "localhost")
    port = os.environ.get("PGPORT", "5432")
    database = os.environ.get("PGDATABASE", "postgres")
    
    url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    conn = await asyncpg.connect(url)
    try:
        v = await conn.fetchval("select now()")
        print("DB connected. now() =", v)
        rows = await conn.fetch("select session_id, state, attempt_count from sessions order by updated_at desc limit 5")
        print("Recent sessions:", [dict(r) for r in rows])
    finally:
        await conn.close()

asyncio.run(main())
