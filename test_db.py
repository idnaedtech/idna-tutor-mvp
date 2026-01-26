import asyncio
from db import init_pool, create_session, get_session, update_session

async def test_db():
    await init_pool()
    
    session_id = "test-session-001"
    student_id = "student-001"
    
    # Create a session
    await create_session(session_id, student_id)
    print(f"Created session: {session_id}")
    
    # Get the session
    s = await get_session(session_id)
    print(f"Retrieved session: {s}")
    
    # Update the session
    await update_session(session_id, state="QUIZ", attempt_count=1, frustration_counter=0)
    print("Updated session state to QUIZ")
    
    # Get updated session
    s = await get_session(session_id)
    print(f"Updated session: {s}")

if __name__ == "__main__":
    asyncio.run(test_db())
