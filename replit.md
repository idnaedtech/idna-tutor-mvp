# Python Workspace

## Overview
A plain Python workspace for general Python development. No web frameworks or external dependencies - just pure Python.

## Project Structure
- `main.py` - gRPC server with sophisticated FSM tutoring logic (runs in workflow)
- `client.py` - Test client that connects to the gRPC server
- `db.py` - Async PostgreSQL database helpers using asyncpg
- `tutoring.proto` - gRPC service definition with FSM states
- `tutoring_pb2.py` - Generated Protocol Buffers Python code
- `tutoring_pb2_grpc.py` - Generated gRPC service Python code
- `requirements.txt` - Project dependencies
- `protos/` - Legacy proto files (can be cleaned up)

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

## Running the Project

### Start the Server
The server runs automatically in the workflow on `:50051`:
```bash
python main.py
```

### Test with Client
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

## Recent Changes
- 2025-12-18: Added db.py with async PostgreSQL connection helpers
- 2025-12-18: Added asyncpg for async database operations
- 2025-12-18: Enhanced tutoring service with advanced FSM and intent classification
- 2025-12-18: Created gRPC server with tutoring session management
- 2025-12-18: Initial project setup with grpcio packages

## User Preferences
- Plain Python without frameworks
- Simple workspace for Python development
- gRPC and Protocol Buffers support
