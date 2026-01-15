from fastapi import FastAPI
from pydantic import BaseModel
import os
import grpc

import tutoring_pb2
import tutoring_pb2_grpc

app = FastAPI()

print("### RUNNING CLEAN BASELINE WEBAPP ###", flush=True)


# ---------
# Models
# ---------
class StartSessionIn(BaseModel):
    student_id: str
    topic_id: str


class TurnIn(BaseModel):
    student_id: str
    session_id: str
    user_text: str


# -------------
# gRPC helper
# -------------
def get_stub() -> tutoring_pb2_grpc.TutoringServiceStub:
    target = os.getenv("GRPC_TARGET")
    use_tls = os.getenv("GRPC_USE_TLS", "0") == "1"

    if not target:
        raise RuntimeError("GRPC_TARGET not set")

    channel = (
        grpc.secure_channel(target, grpc.ssl_channel_credentials())
        if use_tls
        else grpc.insecure_channel(target)
    )
    return tutoring_pb2_grpc.TutoringServiceStub(channel)


# ----------
# Routes
# ----------
@app.get("/")
def root():
    # Some platforms health-check "/" by default.
    return {"status": "ok"}


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/grpc_ping")
def grpc_ping():
    target = os.getenv("GRPC_TARGET")
    use_tls = os.getenv("GRPC_USE_TLS", "0") == "1"
    if not target:
        return {"ok": False, "error": "GRPC_TARGET not set"}

    try:
        channel = (
            grpc.secure_channel(target, grpc.ssl_channel_credentials())
            if use_tls
            else grpc.insecure_channel(target)
        )

        grpc.channel_ready_future(channel).result(timeout=10)
        return {"ok": True, "target": target, "tls": use_tls}

    except Exception as e:
        return {
            "ok": False,
            "target": target,
            "tls": use_tls,
            "error_type": type(e).__name__,
            "error": repr(e),
        }


@app.post("/start_session")
def start_session(payload: StartSessionIn):
    stub = get_stub()
    resp = stub.StartSession(
        tutoring_pb2.StartSessionRequest(
            student_id=payload.student_id,
            topic_id=payload.topic_id,
        ),
        timeout=10,
    )
    return {
        "ok": True,
        "session_id": resp.session_id,
        "state": int(resp.state),
        "tutor_text": resp.tutor_text,
    }


@app.post("/turn")
def turn(payload: TurnIn):
    stub = get_stub()
    resp = stub.Turn(
        tutoring_pb2.TurnRequest(
            student_id=payload.student_id,
            session_id=payload.session_id,
            user_text=payload.user_text,
        ),
        timeout=10,
    )

    return {
        "ok": True,
        "session_id": resp.session_id,
        "next_state": int(resp.next_state),
        "tutor_text": resp.tutor_text,
        "intent": resp.intent,
        "attempt_count": resp.attempt_count,
        "frustration_counter": resp.frustration_counter,
        "topic_id": resp.topic_id,
        "question_id": resp.question_id,
        "title": resp.title,
    }


# -------------------------
# Debug: prove which file is running
# -------------------------
@app.get("/__whoami")
def whoami():
    return {
        "file": __file__,
        "cwd": os.getcwd(),
        "port_env": os.getenv("PORT"),
        "grpc_target": os.getenv("GRPC_TARGET"),
        "grpc_use_tls": os.getenv("GRPC_USE_TLS", "0"),
    }
