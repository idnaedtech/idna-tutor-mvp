# Python Workspace

## Overview
A plain Python workspace for general Python development. No web frameworks or external dependencies - just pure Python.

## Project Structure
- `main.py` - gRPC server with sophisticated FSM tutoring logic (runs in workflow)
- `db.py` - Async PostgreSQL database helpers using asyncpg with thread-safe operations
- `client.py` - Full test client that demonstrates complete FSM flow
- `client_start.py` - Helper client to start a session and save session_id to file
- `client_resume.py` - Helper client to resume a saved session (tests persistence)
- `db_smoke.py` - Database connectivity verification script
- `test_db.py` - Test script for database operations (legacy)
- `tutoring.proto` - gRPC service definition with FSM states
- `tutoring_pb2.py` - Generated Protocol Buffers Python code
- `tutoring_pb2_grpc.py` - Generated gRPC service Python code
- `requirements.txt` - Project dependencies
- `last_session.txt` - Persistent session ID (generated during testing)

## gRPC Service API
The TutoringService provides two main RPCs:

### StartSession
- **Input**: `student_id` (string)
- **Output**: `session_id`, `state` (FSM), `tutor_text`
- **Purpose**: Initialize a new tutoring session for a student

### Turn
- **Input**: `student_id`, `session_id`, `user_text`
- **Output**: `session_id`, `next_state` (FSM), `tutor_text`, `attempt_count`, `frustration_counter`, `intent`
- **Purpose**: Process user input and advance the tutoring session

### FSM States
- `EXPLAIN` - Tutor explains concept
- `QUIZ` - Student takes quiz
- `EVALUATE` - Tutor evaluates answer
- `HINT` - Tutor provides hint
- `REVEAL` - Tutor reveals answer

## Dependencies
- grpcio==1.76.0 - gRPC Python library
- grpcio-tools==1.76.0 - Protocol buffer compiler and gRPC code generator
- protobuf==6.33.2 - Protocol Buffers library
- asyncpg==0.31.0 - Async PostgreSQL driver for Python

## Database Setup
The `db.py` module expects a `sessions` table. Create it with:

```sql
create table sessions (
    session_id text primary key,
    student_id text not null,
    state text not null,
    attempt_count integer default 0,
    frustration_counter integer default 0,
    question text,
    created_at timestamp default now(),
    updated_at timestamp default now()
);
```

Set `DATABASE_URL` environment variable (format: `postgresql://user:password@host/dbname`)

## Running the Project

### Start the Server
The server runs automatically in the workflow on `:50051`:
```bash
python main.py
```

### Test with gRPC Client
In a separate terminal or shell, run:
```bash
python client.py
```

This will:
1. Start a tutoring session
2. Send "next" to transition to QUIZ
3. Send "5" (wrong answer)
4. Send "anything" (wrong) to trigger HINT
5. Send "4" (correct answer)

### Test Session Persistence (Server Restart Proof)
This demonstrates that sessions survive server restarts:

**Terminal 1 - Start session:**
```bash
python client_start.py
```
Output: Session ID saved to `last_session.txt`

**Terminal 1 - Stop server, restart it:**
- Stop running `main.py`
- Start it again: `python main.py`

**Terminal 2 - Resume same session:**
```bash
python client_resume.py
```
Expected: Returns valid response with same session_id, not "Session not found"

### Database Connectivity Test
To verify PostgreSQL connection and see recent sessions:
```bash
python db_smoke.py
```

Output shows:
- DB connection status
- Recent sessions from sessions table
- Verification that session state persists correctly

### Test Database Operations
To test the database module directly (requires DATABASE_URL configured):
```bash
python test_db.py
```

This will test creating, retrieving, and updating sessions in the database.

## Recent Changes
- 2025-12-18: ✅ COMPLETE - Verified full session persistence across server restarts
- 2025-12-18: Created client_start.py, client_resume.py, db_smoke.py for testing
- 2025-12-18: Fixed DATABASE_URL parsing to use individual Postgres env vars
- 2025-12-18: Implemented thread-safe async worker for gRPC + asyncpg integration
- 2025-12-18: Added db.py with async PostgreSQL connection helpers
- 2025-12-18: Enhanced tutoring service with advanced FSM and intent classification
- 2025-12-18: Created gRPC server with tutoring session management
- 2025-12-18: Initial project setup with grpcio packages

## Status: PRODUCTION READY ✅
- ✅ gRPC server running on :50051
- ✅ PostgreSQL session persistence verified
- ✅ FSM states fully implemented (EXPLAIN → QUIZ → EVALUATE → HINT → REVEAL)
- ✅ Intent classification working (commands, answers, confusion signals)
- ✅ Frustration tracking persisting correctly
- ✅ Session resume after server restart confirmed
- ✅ Database connectivity validated

## User Preferences
- Plain Python without frameworks
- Simple workspace for Python development
- gRPC and Protocol Buffers support
