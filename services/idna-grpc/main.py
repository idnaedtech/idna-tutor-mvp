import os
import signal
import grpc
import asyncio
import threading
from queue import Queue
from concurrent import futures

# Optional: gRPC health check (graceful if unavailable)
try:
    from grpc_health.v1 import health
    from grpc_health.v1 import health_pb2
    from grpc_health.v1 import health_pb2_grpc
    HEALTH_CHECK_AVAILABLE = True
except ImportError:
    print("[gRPC] WARNING: grpcio-health-checking not installed, health check disabled", flush=True)
    HEALTH_CHECK_AVAILABLE = False

import tutoring_pb2
import tutoring_pb2_grpc

from db import (
    init_pool,
    close_pool,
    create_session,
    get_session,
    update_session,
    pick_topic,
    pick_question,
    get_question,
    get_next_question,
    get_next_question_in_session,
    mark_seen,
    insert_attempt,
    check_and_mark_completion,
)

# ===============================
# Async DB runner (thread-safe)
# ===============================
_async_queue = Queue()
_async_thread = None


def _async_worker():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        coro, result_queue = _async_queue.get()
        if coro is None:
            break
        try:
            result = loop.run_until_complete(coro)
            result_queue.put(("ok", result))
        except Exception as e:
            result_queue.put(("err", e))


def _run_async(coro):
    global _async_thread
    if _async_thread is None:
        _async_thread = threading.Thread(target=_async_worker, daemon=True)
        _async_thread.start()

    result_queue = Queue()
    _async_queue.put((coro, result_queue))
    status, result = result_queue.get()
    if status == "err":
        raise result
    return result


# ===============================
# Helper logic
# ===============================
def normalize(s: str) -> str:
    return (s or "").strip().lower()


def is_correct(user_text: str, answer_key: str) -> bool:
    return normalize(user_text) == normalize(answer_key)


def classify_intent(text: str) -> str:
    t = normalize(text)
    if not t:
        return "silent"
    if t in {"next", "ok", "got it"}:
        return "command_next"
    return "answer"


# ===============================
# gRPC Service
# ===============================
class TutoringServicer(tutoring_pb2_grpc.TutoringServiceServicer):

    def StartSession(self, request, context):
        if not request.student_id or not request.topic_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("student_id and topic_id required")
            return tutoring_pb2.StartSessionResponse()

        q = _run_async(get_next_question(request.student_id, request.topic_id))
        if not q:
            q = _run_async(pick_question(request.topic_id))

        if not q:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("No questions available")
            return tutoring_pb2.StartSessionResponse()

        session_id = _run_async(
            create_session(
                student_id=request.student_id,
                topic_id=request.topic_id,
                state="ACTIVE",
                current_question_id=str(q["question_id"]),
            )
        )

        return tutoring_pb2.StartSessionResponse(
            session_id=session_id,
            state=tutoring_pb2.FsmState.QUIZ,
            tutor_text=f"Question: {q['prompt']}",
        )

    def Turn(self, request, context):
        s = _run_async(get_session(request.session_id))
        if not s:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Session not found")
            return tutoring_pb2.TurnResponse()

        qid = s["current_question_id"]
        q = _run_async(get_question(qid))
        correct = is_correct(request.user_text, q["answer_key"])

        if correct:
            _run_async(insert_attempt(request.session_id, request.student_id, s["topic_id"], qid, True))
            _run_async(mark_seen(request.student_id, s["topic_id"], request.session_id, qid))

            next_q = _run_async(get_next_question_in_session(request.session_id, s["topic_id"]))
            if not next_q:
                _run_async(update_session(request.session_id, state="COMPLETED", current_question_id=None))
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    tutor_text="✅ Topic completed",
                    intent="complete",
                )

            _run_async(update_session(
                request.session_id,
                state="ACTIVE",
                current_question_id=str(next_q["question_id"]),
            ))

            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                tutor_text=f"✅ Correct! Next: {next_q['prompt']}",
                intent="next_question",
            )

        else:
            _run_async(insert_attempt(request.session_id, request.student_id, s["topic_id"], qid, False))
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                tutor_text=f"❌ Try again. Hint: {q.get('hint1', '')}",
                intent="hint",
            )


# ===============================
# gRPC Server bootstrap
# ===============================
_server = None
_health_servicer = None


def _shutdown_handler(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    sig_name = signal.Signals(signum).name
    print(f"[gRPC] Received {sig_name}, shutting down gracefully...", flush=True)

    if _server:
        # Stop accepting new requests, wait up to 10s for in-flight
        _server.stop(grace=10)

    # Close DB pool
    try:
        _run_async(close_pool())
        print("[gRPC] DB pool closed", flush=True)
    except Exception as e:
        print(f"[gRPC] Error closing DB pool: {e}", flush=True)

    # Stop the async worker thread
    _async_queue.put((None, None))
    print("[gRPC] Shutdown complete", flush=True)


def serve():
    global _server, _health_servicer

    # 🔒 CRITICAL: Railway port binding
    grpc_port = os.getenv("PORT") or os.getenv("GRPC_PORT", "50051")

    # Init DB ONCE
    _run_async(init_pool())

    _server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    # Add TutoringService
    tutoring_pb2_grpc.add_TutoringServiceServicer_to_server(
        TutoringServicer(), _server
    )

    # Add Health Check service (if available)
    if HEALTH_CHECK_AVAILABLE:
        _health_servicer = health.HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(_health_servicer, _server)
        _health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
        _health_servicer.set("TutoringService", health_pb2.HealthCheckResponse.SERVING)

    _server.add_insecure_port(f"0.0.0.0:{grpc_port}")
    print(f"GRPC_LISTENING 0.0.0.0:{grpc_port}", flush=True)

    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)

    _server.start()
    health_status = "enabled" if HEALTH_CHECK_AVAILABLE else "disabled"
    print(f"[gRPC] Server started, health check {health_status}", flush=True)
    _server.wait_for_termination()


if __name__ == "__main__":
    serve()
