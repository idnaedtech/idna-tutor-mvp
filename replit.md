# Python Workspace

## Overview
A plain Python workspace for general Python development. No web frameworks or external dependencies - just pure Python.

## Project Structure
- `main.py` - gRPC server implementation with session management
- `protos/` - Protocol Buffer definitions
  - `tutoring.proto` - gRPC service with FSM state management
  - `tutoring_pb2.py` - Generated Protocol Buffers Python code
  - `tutoring_pb2_grpc.py` - Generated gRPC service Python code
  - `__init__.py` - Package initialization

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

## Running the Project
Run the application using:
```bash
python main.py
```

## Recent Changes
- 2025-12-18: Added grpcio, grpcio-tools, and protobuf packages
- 2025-12-18: Initial project setup with main.py

## User Preferences
- Plain Python without frameworks
- Simple workspace for Python development
- gRPC and Protocol Buffers support
