from fastapi import FastAPI
from pydantic import BaseModel
import grpc

import tutoring_pb2
import tutoring_pb2_grpc

app = FastAPI()

# gRPC channel to your existing server
CHANNEL = grpc.insecure_channel("localhost:50051")
STUB = tutoring_pb2_grpc.TutoringServiceStub(CHANNEL)

class StartReq(BaseModel):
    student_id: str = "00000000-0000-0000-0000-000000000001"

class TurnReq(BaseModel):
    student_id: str
    session_id: str
    user_text: str

@app.post("/start")
def start(req: StartReq):
    resp = STUB.StartSession(tutoring_pb2.StartSessionRequest(student_id=req.student_id))
    return {
        "session_id": resp.session_id,
        "state": int(resp.state),
        "tutor_text": resp.tutor_text
    }

@app.post("/turn")
def turn(req: TurnReq):
    resp = STUB.Turn(tutoring_pb2.TurnRequest(
        student_id=req.student_id,
        session_id=req.session_id,
        user_text=req.user_text
    ))

    # These fields exist only if your proto added them.
    # If not, they'll simply be absent and that's fine.
    out = {
        "session_id": resp.session_id,
        "state": int(resp.next_state),
        "tutor_text": resp.tutor_text,
        "attempt_count": getattr(resp, "attempt_count", None),
        "frustration_counter": getattr(resp, "frustration_counter", None),
        "intent": getattr(resp, "intent", None),
        "topic_id": getattr(resp, "topic_id", None),
        "question_id": getattr(resp, "question_id", None),
        "concept_title": getattr(resp, "concept_title", None),
    }
    return out
