import uuid
import os
import grpc
from concurrent import futures
import asyncio
import threading
import time
from queue import Queue

import tutoring_pb2
import tutoring_pb2_grpc
from db import init_pool, create_session, get_session, update_session, pick_topic, pick_question, get_question, mark_question_seen, get_topic, get_next_question, get_next_question_in_session, mark_seen, insert_attempt, check_and_mark_completion

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
        "ACTIVE": tutoring_pb2.FsmState.QUIZ,
        "EXPLAIN": tutoring_pb2.FsmState.EXPLAIN,
        "QUIZ": tutoring_pb2.FsmState.QUIZ,
        "EVALUATE": tutoring_pb2.FsmState.EVALUATE,
        "HINT": tutoring_pb2.FsmState.HINT,
        "REVEAL": tutoring_pb2.FsmState.REVEAL,
        "COMPLETED": tutoring_pb2.FsmState.QUIZ,
    }
    return state_map.get(state_str, tutoring_pb2.FsmState.EXPLAIN)

def int_to_state(state_int: int) -> str:
    """Convert protobuf enum to state string for DB."""
    state_map = {
        tutoring_pb2.FsmState.EXPLAIN: "EXPLAIN",
        tutoring_pb2.FsmState.QUIZ: "QUIZ",
        tutoring_pb2.FsmState.EVALUATE: "EVALUATE",
        tutoring_pb2.FsmState.HINT: "HINT",
        tutoring_pb2.FsmState.REVEAL: "REVEAL",
    }
    return state_map.get(state_int, "EXPLAIN")

class TutoringServicer(tutoring_pb2_grpc.TutoringServiceServicer):
    def StartSession(self, request, context):
        student_id = request.student_id
        topic_id = request.topic_id

        if not student_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("student_id is required")
            return tutoring_pb2.StartSessionResponse()

        if not topic_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("topic_id is required")
            return tutoring_pb2.StartSessionResponse()

        # Get first question
        qrow = _run_async(get_next_question(student_id, topic_id))
        if not qrow:
            qrow = _run_async(pick_question(topic_id))
        
        if not qrow:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("No questions found for this topic")
            return tutoring_pb2.StartSessionResponse()

        # Create session in DB with first question already loaded
        session_id = _run_async(create_session(
            student_id=student_id,
            topic_id=topic_id,
            state="ACTIVE",
            current_question_id=str(qrow["question_id"])
        ))

        return tutoring_pb2.StartSessionResponse(
            session_id=session_id,
            state=tutoring_pb2.FsmState.QUIZ,
            tutor_text=f"Question: {qrow['prompt']}"
        )

    def Turn(self, request, context):
        print("TURN HIT", time.time(), "BODY=", {"student_id": request.student_id, "session_id": request.session_id, "user_text": request.user_text})
        
        # Guard: Check if session is already completed (prevent answer spam after completion)
        s = _run_async(get_session(request.session_id))
        if not s:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Session not found. StartSession first.")
            return tutoring_pb2.TurnResponse()
        
        print("TURN_SESSION_STATUS", s["state"])
        
        if s["state"] == "COMPLETED":
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.FsmState.QUIZ,
                tutor_text="Session already completed. No more answers accepted.",
                intent="completed"
            )
        
        user_text = request.user_text or ""
        intent = classify_intent(user_text)
        
        state = state_to_int(s["state"])
        attempt_count = s["attempt_count"]
        frustration = s["frustration_counter"]

        # --- COMPLETED ---
        if s["state"] == "COMPLETED":
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.FsmState.QUIZ,
                tutor_text="This topic is finished. Please select a new topic and click Start Session.",
                intent="completed"
            )

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
        if state == tutoring_pb2.FsmState.EXPLAIN:
            if intent == "command_repeat":
                tutor_text = "Addition means combining numbers. Example: 2 + 2 = 4. Say 'next' when ready."
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.FsmState.EXPLAIN,
                    tutor_text=tutor_text,
                    attempt_count=attempt_count,
                    frustration_counter=frustration,
                    intent=intent
                )

            if understood_signal(user_text) or intent == "command_next":
                topic_id = s["topic_id"]
                qrow = _run_async(get_next_question(request.student_id, topic_id))
                if not qrow:
                    qrow = _run_async(pick_question(topic_id))
                _run_async(update_session(
                    request.session_id,
                    state="ACTIVE",
                    attempt_count=0,
                    current_question_id=str(qrow["question_id"])
                ))
                # Fetch topic info for progress signal
                topic = _run_async(pick_topic(6, "math", "en"))
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.FsmState.QUIZ,
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
                next_state=tutoring_pb2.FsmState.EXPLAIN,
                tutor_text=tutor_text,
                attempt_count=attempt_count,
                frustration_counter=frustration,
                intent="teach",
                topic_id=topic_id or "",
                question_id="",
                title=topic["title"] if topic else ""
            )

        # --- QUIZ: grade immediately and continue ---
        if state == tutoring_pb2.FsmState.QUIZ:
            topic_id = s["topic_id"]
            qid = s["current_question_id"]
            user_answer = (request.user_text or "").strip()
            
            # Safety: must have topic + current question
            if not topic_id or not qid:
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.FsmState.QUIZ,
                    tutor_text="Error: no question loaded. Start a new session.",
                    attempt_count=attempt_count,
                    frustration_counter=frustration,
                    intent="error",
                    topic_id=topic_id or "",
                    question_id=qid or "",
                    title=""
                )
            
            # Load question from DB
            q = _run_async(get_question(qid))
            if not q:
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.FsmState.QUIZ,
                    tutor_text="Error: question not found.",
                    attempt_count=attempt_count,
                    frustration_counter=frustration,
                    intent="error",
                    topic_id=topic_id or "",
                    question_id=qid or "",
                    title=""
                )
            
            # Grade the answer
            correct = is_correct(user_answer, q["answer_key"])
            
            if correct:
                # Record attempt
                _run_async(insert_attempt(request.session_id, request.student_id, topic_id, qid, True))
                
                # Check if topic is now complete
                _run_async(check_and_mark_completion(request.session_id, topic_id))
                
                # Mark question as seen
                _run_async(mark_seen(request.student_id, topic_id, request.session_id, qid))
                
                # Get next question (session-specific, only exclude correct answers in THIS session)
                next_q = _run_async(get_next_question_in_session(request.session_id, topic_id))
                
                if not next_q:
                    # No more questions in this topic
                    _run_async(update_session(request.session_id, state="COMPLETED", current_question_id=None))
                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.FsmState.QUIZ,
                        tutor_text="✅ Correct! You've completed all questions in this topic.",
                        attempt_count=0,
                        frustration_counter=0,
                        intent="complete",
                        topic_id=topic_id,
                        question_id="",
                        title=""
                    )
                
                # Update session with next question
                _run_async(update_session(
                    request.session_id,
                    state="ACTIVE",
                    current_question_id=str(next_q["question_id"]),
                    attempt_count=0,
                    frustration_counter=frustration
                ))
                
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.FsmState.QUIZ,
                    tutor_text=f"✅ Correct! Next question: {next_q['prompt']}",
                    attempt_count=0,
                    frustration_counter=frustration,
                    intent="next_question",
                    topic_id=topic_id,
                    question_id=str(next_q["question_id"]),
                    title=next_q.get("title", "")
                )
            else:
                # Record attempt
                _run_async(insert_attempt(request.session_id, request.student_id, topic_id, qid, False))
                
                # Check if topic is now complete (even with wrong answer, might have answered all questions)
                _run_async(check_and_mark_completion(request.session_id, topic_id))
                
                # Wrong answer: give hint
                new_attempts = attempt_count + 1
                new_frustration = frustration + 1
                
                # Update session
                _run_async(update_session(
                    request.session_id,
                    state="HINT",
                    attempt_count=new_attempts,
                    frustration_counter=new_frustration
                ))
                
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.FsmState.HINT,
                    tutor_text=f"❌ Not quite. Hint: {q.get('hint1', 'Try again.')}",
                    attempt_count=new_attempts,
                    frustration_counter=new_frustration,
                    intent="hint",
                    topic_id=topic_id,
                    question_id=qid,
                    title=q.get("title", "")
                )

        # --- EVALUATE ---
        if state == tutoring_pb2.FsmState.EVALUATE:
            qid = s["current_question_id"]
            q = _run_async(get_question(qid))
            correct = is_correct(user_text, q["answer_key"])
            if correct:
                _run_async(mark_seen(request.student_id, s["topic_id"], request.session_id, qid))
                topic_id = s["topic_id"]
                new_q = _run_async(get_next_question(request.student_id, topic_id))
                if not new_q:
                    new_q = _run_async(pick_question(topic_id))
                _run_async(update_session(
                    request.session_id,
                    state="ACTIVE",
                    attempt_count=0,
                    frustration_counter=0,
                    current_question_id=str(new_q["question_id"])
                ))
                topic = _run_async(pick_topic(6, "math", "en"))
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.FsmState.QUIZ,
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
                        next_state=tutoring_pb2.FsmState.EXPLAIN,
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
                        next_state=tutoring_pb2.FsmState.HINT,
                        tutor_text=f"Hint: {hint_text}",
                        attempt_count=attempt_count,
                        frustration_counter=frustration,
                        intent="hint",
                        topic_id=topic_id or "",
                        question_id=s["current_question_id"] or "",
                        title=topic["title"] if topic else ""
                    )

        # --- HINT -> QUIZ again ---
        if state == tutoring_pb2.FsmState.HINT:
            _run_async(update_session(request.session_id, state="ACTIVE"))
            qid = s["current_question_id"]
            q = _run_async(get_question(qid))
            topic_id = s["topic_id"]
            topic = _run_async(pick_topic(6, "math", "en"))
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.FsmState.QUIZ,
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
            next_state=tutoring_pb2.FsmState.EXPLAIN,
            tutor_text="Reset. Let's continue.",
            attempt_count=attempt_count,
            frustration_counter=frustration,
            intent="reset",
            topic_id=topic_id,
            question_id="",
            title=topic["title"] if topic else ""
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tutoring_pb2_grpc.add_TutoringServiceServicer_to_server(
        TutoringServicer(), server
    )
    
    grpc_port = os.getenv("GRPC_PORT", "50051")
    server.add_insecure_port(f"0.0.0.0:{grpc_port}")

    server.start()
    print(f"gRPC FSM server running on 0.0.0.0:{grpc_port}")
    server.wait_for_termination()


   

if __name__ == "__main__":
    serve()
