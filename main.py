import uuid
import grpc
from concurrent import futures
import asyncio
import os
import threading
from queue import Queue

import tutoring_pb2
import tutoring_pb2_grpc
from db import init_pool, create_session, get_session, update_session, pick_topic, pick_question, get_question, pick_question_unseen, mark_question_seen, get_topic

# Global async runner
_async_queue = Queue()
_async_thread = None

def _async_worker():
    """Worker thread that runs async operations with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    while True:
        coro, result_queue = _async_queue.get()
        if coro is None:
            break
        try:
            result = loop.run_until_complete(coro)
            result_queue.put(("success", result))
        except Exception as e:
            result_queue.put(("error", e))

def _start_async_worker():
    """Start the async worker thread."""
    global _async_thread
    if _async_thread is None:
        _async_thread = threading.Thread(target=_async_worker, daemon=True)
        _async_thread.start()

def _run_async(coro):
    """Run async code in the worker thread."""
    _start_async_worker()
    result_queue = Queue()
    _async_queue.put((coro, result_queue))
    status, result = result_queue.get()
    if status == "error":
        raise result
    return result

def classify_intent(text: str) -> str:
    t = (text or "").strip().lower()
    if t == "" or t in {"...", "hmm"}:
        return "silent"
    if t in {"i don't know", "idk", "not sure", "confused"}:
        return "confused"
    if t in {"explain", "tell me", "teach", "explain more", "again"}:
        return "command_repeat"
    if t in {"next", "ok", "good", "got it", "i understand"}:
        return "command_next"
    if t in {"stop", "wait", "pause", "i'm stuck", "help"}:
        return "interrupt"
    return "answer"

def understood_signal(text: str) -> bool:
    return classify_intent(text) in {"command_next", "silent"}

def normalize(s: str) -> str:
    return (s or "").strip().lower()

def is_correct(user_text: str, answer_key: str) -> bool:
    return normalize(user_text) == normalize(answer_key)

def grade_answer(text: str) -> bool:
    t = normalize(text)
    return t == "4" or t == "four"

def state_to_int(state_str: str) -> int:
    state_map = {
        "EXPLAIN": tutoring_pb2.EXPLAIN,
        "QUIZ": tutoring_pb2.QUIZ,
        "EVALUATE": tutoring_pb2.EVALUATE,
        "HINT": tutoring_pb2.HINT,
        "REVEAL": tutoring_pb2.REVEAL,
    }
    return state_map.get(state_str, tutoring_pb2.EXPLAIN)

def int_to_state(state_int: int) -> str:
    """Convert protobuf enum to state string for DB."""
    state_map = {
        tutoring_pb2.EXPLAIN: "EXPLAIN",
        tutoring_pb2.QUIZ: "QUIZ",
        tutoring_pb2.EVALUATE: "EVALUATE",
        tutoring_pb2.HINT: "HINT",
        tutoring_pb2.REVEAL: "REVEAL",
    }
    return state_map.get(state_int, "EXPLAIN")

class TutoringServicer(tutoring_pb2_grpc.TutoringServiceServicer):
    def StartSession(self, request, context):
        student_id = request.student_id
        topic_id = request.topic_id
        
        # Create session in DB (store student_id + topic_id, set state to QUIZ)
        session_id = _run_async(create_session(student_id=student_id, topic_id=topic_id, state="QUIZ"))
        
        return tutoring_pb2.StartSessionResponse(
            session_id=session_id,
            state=tutoring_pb2.QUIZ,
            tutor_text="Session started. Ready to begin."
        )

    def Turn(self, request, context):
        s = _run_async(get_session(request.session_id))
        
        if not s:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Session not found. StartSession first.")
            return tutoring_pb2.TurnResponse()

        user_text = request.user_text or ""
        intent = classify_intent(user_text)
        
        state = state_to_int(s["state"])
        attempt_count = s["attempt_count"]
        frustration = s["frustration_counter"]

        # universal interrupt
        if intent == "interrupt":
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=state,
                tutor_text="Okay. Tell me your doubt in one line.",
                attempt_count=attempt_count,
                frustration_counter=frustration,
                intent=intent
            )

        # --- EXPLAIN ---
        if state == tutoring_pb2.EXPLAIN:
            if intent == "command_repeat":
                tutor_text = "Addition means combining numbers. Example: 2 + 2 = 4. Say 'next' when ready."
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.EXPLAIN,
                    tutor_text=tutor_text,
                    attempt_count=attempt_count,
                    frustration_counter=frustration,
                    intent=intent
                )

            if understood_signal(user_text) or intent == "command_next":
                topic_id = s["topic_id"]
                qrow = _run_async(pick_question_unseen(request.session_id, topic_id))
                if not qrow:
                    qrow = _run_async(pick_question(topic_id))
                _run_async(update_session(
                    request.session_id,
                    state="QUIZ",
                    attempt_count=0,
                    current_question_id=str(qrow["question_id"])
                ))
                # Fetch topic info for progress signal
                topic = _run_async(pick_topic(6, "math", "en"))
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.QUIZ,
                    tutor_text=f"Question: {qrow['prompt']}",
                    attempt_count=0,
                    frustration_counter=s["frustration_counter"],
                    intent="ask_question",
                    topic_id=str(topic_id) if topic_id else "",
                    question_id=str(qrow["question_id"]),
                    title=str(topic["title"]) if topic and topic["title"] else ""
                )

            topic_id = s["topic_id"]
            topic = _run_async(pick_topic(6, "math", "en"))
            tutor_text = "Addition means combining numbers. Say 'next' when ready, or explain in one line."
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.EXPLAIN,
                tutor_text=tutor_text,
                attempt_count=attempt_count,
                frustration_counter=frustration,
                intent="teach",
                topic_id=topic_id or "",
                question_id="",
                title=topic["title"] if topic else ""
            )

        # --- QUIZ -> EVALUATE ---
        if state == tutoring_pb2.QUIZ:
            _run_async(update_session(request.session_id, state="EVALUATE"))
            topic_id = s["topic_id"]
            qid = s["current_question_id"]
            topic = _run_async(pick_topic(6, "math", "en"))
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.EVALUATE,
                tutor_text="Got it. Let me check.",
                attempt_count=attempt_count,
                frustration_counter=frustration,
                intent="evaluate",
                topic_id=topic_id or "",
                question_id=qid or "",
                title=topic["title"] if topic else ""
            )

        # --- EVALUATE ---
        if state == tutoring_pb2.EVALUATE:
            qid = s["current_question_id"]
            q = _run_async(get_question(qid))
            correct = is_correct(user_text, q["answer_key"])
            if correct:
                _run_async(mark_question_seen(request.session_id, qid))
                topic_id = s["topic_id"]
                new_q = _run_async(pick_question_unseen(request.session_id, topic_id))
                if not new_q:
                    new_q = _run_async(pick_question(topic_id))
                _run_async(update_session(
                    request.session_id,
                    state="QUIZ",
                    attempt_count=0,
                    frustration_counter=0,
                    current_question_id=str(new_q["question_id"])
                ))
                topic = _run_async(pick_topic(6, "math", "en"))
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.QUIZ,
                    tutor_text=f"Correct! Next question: {new_q['prompt']}",
                    attempt_count=0,
                    frustration_counter=0,
                    intent="correct",
                    topic_id=str(topic_id) if topic_id else "",
                    question_id=str(new_q["question_id"]),
                    title=str(topic["title"]) if topic and topic["title"] else ""
                )
            else:
                attempt_count = s["attempt_count"] + 1
                frustration = s["frustration_counter"] + 1
                if attempt_count >= 2 or frustration >= 3:
                    _run_async(update_session(request.session_id, state="EXPLAIN", attempt_count=0, frustration_counter=0))
                    tutor_text = f"Not quite. {q['reveal_explain']} Moving on."
                    topic_id = s["topic_id"]
                    topic = _run_async(pick_topic(6, "math", "en"))
                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.EXPLAIN,
                        tutor_text=tutor_text,
                        attempt_count=0,
                        frustration_counter=0,
                        intent="reveal",
                        topic_id=topic_id or "",
                        question_id="",
                        title=topic["title"] if topic else ""
                    )
                else:
                    hint_text = q["hint1"] if attempt_count == 1 else q["hint2"]
                    _run_async(update_session(request.session_id, state="HINT", attempt_count=attempt_count, frustration_counter=frustration))
                    topic_id = s["topic_id"]
                    topic = _run_async(pick_topic(6, "math", "en"))
                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.HINT,
                        tutor_text=f"Hint: {hint_text}",
                        attempt_count=attempt_count,
                        frustration_counter=frustration,
                        intent="hint",
                        topic_id=topic_id or "",
                        question_id=s["current_question_id"] or "",
                        title=topic["title"] if topic else ""
                    )

        # --- HINT -> QUIZ again ---
        if state == tutoring_pb2.HINT:
            _run_async(update_session(request.session_id, state="QUIZ"))
            qid = s["current_question_id"]
            q = _run_async(get_question(qid))
            topic_id = s["topic_id"]
            topic = _run_async(pick_topic(6, "math", "en"))
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.QUIZ,
                tutor_text=f"Try again: {q['prompt']}",
                attempt_count=attempt_count,
                frustration_counter=frustration,
                intent="retry",
                topic_id=topic_id or "",
                question_id=qid or "",
                title=topic["title"] if topic else ""
            )

        # fallback
        _run_async(update_session(request.session_id, state="EXPLAIN"))
        topic_id = s.get("topic_id", "")
        topic = _run_async(pick_topic(6, "math", "en"))
        return tutoring_pb2.TurnResponse(
            session_id=request.session_id,
            next_state=tutoring_pb2.EXPLAIN,
            tutor_text="Reset. Let's continue.",
            attempt_count=attempt_count,
            frustration_counter=frustration,
            intent="reset",
            topic_id=topic_id,
            question_id="",
            title=topic["title"] if topic else ""
        )

def serve():
    _run_async(init_pool())
    
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tutoring_pb2_grpc.add_TutoringServiceServicer_to_server(TutoringServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC FSM server running on :50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
