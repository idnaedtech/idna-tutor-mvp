# gRPC Tutoring Service - FSM with Database-Driven Content

## Overview
Complete tutoring system with:
- **FSM State Management**: EXPLAIN → QUIZ → EVALUATE → HINT → REVEAL
- **Database-Driven Content**: Topics and questions from PostgreSQL
- **Question Rotation**: Non-repeating question selection per session
- **Session Persistence**: State survives server restarts
- **Thread-Safe gRPC**: Async worker pattern for event loop compatibility

## Architecture
- `main.py` - gRPC server with FSM logic
- `db.py` - PostgreSQL async functions using asyncpg
- `tutoring.proto` - Protocol Buffer definitions
- `test_final.py` - Comprehensive working test ✅

## Database Schema
- `sessions` - session_id, student_id, state, topic_id, current_question_id, attempt_count, frustration_counter
- `concepts` - Topics with titles and explanations  
- `questions` - Questions with prompts, answers, hints
- `seen_questions` - Tracks question rotation (prevents repeats)

## Running
```bash
python main.py              # Start gRPC server on :50051
python test_final.py        # Run comprehensive test (WORKING)
```

## Test Results
✅ **test_final.py**: Question rotation verified - gets different questions after each correct answer
- Session persists across restarts
- Progress signals (topic_id, question_id, title) populate correctly
- Non-repeating logic prevents question duplicates

## Features Implemented
✅ FSM with 5 states + transitions
✅ Intent classification (command_next, confused, etc)
✅ Database content selection
✅ Question rotation + seen_questions tracking
✅ Hints (hint1, hint2) from DB
✅ Answer grading against DB answer_key
✅ Frustration tracking
✅ Session persistence
✅ gRPC streaming protocol
