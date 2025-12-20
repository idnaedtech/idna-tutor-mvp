#!/usr/bin/env python3
"""
FastAPI web interface for the gRPC tutoring service.
Provides REST endpoints that communicate with the gRPC backend.
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import grpc
import tutoring_pb2
import tutoring_pb2_grpc
import os

app = FastAPI(title="Tutoring Service Web API")

# gRPC channel (configure host based on environment)
GRPC_HOST = os.getenv("GRPC_HOST", "localhost")
GRPC_PORT = os.getenv("GRPC_PORT", "50051")
channel = grpc.insecure_channel(f"{GRPC_HOST}:{GRPC_PORT}")
stub = tutoring_pb2_grpc.TutoringServiceStub(channel)


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.post("/session/start")
async def start_session(student_id: str):
    """Start a new tutoring session"""
    try:
        response = stub.StartSession(tutoring_pb2.StartSessionRequest(student_id=student_id))
        return {
            "session_id": response.session_id,
            "tutor_text": response.tutor_text,
            "topic_id": response.topic_id,
            "title": response.title,
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/turn")
async def send_turn(session_id: str, student_id: str, user_text: str):
    """Send a user message in the tutoring session"""
    try:
        response = stub.Turn(
            tutoring_pb2.TurnRequest(
                student_id=student_id,
                session_id=session_id,
                user_text=user_text,
            )
        )
        return {
            "session_id": response.session_id,
            "tutor_text": response.tutor_text,
            "question_id": response.question_id,
            "topic_id": response.topic_id,
            "title": response.title,
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/session/{session_id}/resume")
async def resume_session(session_id: str, student_id: str):
    """Resume an existing tutoring session"""
    try:
        response = stub.ResumeSession(
            tutoring_pb2.ResumeSessionRequest(
                student_id=student_id,
                session_id=session_id,
            )
        )
        return {
            "session_id": response.session_id,
            "tutor_text": response.tutor_text,
            "question_id": response.question_id,
            "topic_id": response.topic_id,
            "title": response.title,
        }
    except grpc.RpcError as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
