import os
import re
import signal
import grpc
import asyncio
import threading
import random
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
    insert_attempt,
)

# ===============================
# FSM State Constants
# ===============================
# Maps to proto FsmState enum
FSM_START = 0      # FSM_UNSPECIFIED - initial
FSM_EXPLAIN = 1    # EXPLAIN - teaching content
FSM_QUIZ = 2       # QUIZ - asking question
FSM_EVALUATE = 3   # EVALUATE - checking answer
FSM_HINT = 4       # HINT - showing hint
FSM_REVEAL = 5     # REVEAL - showing answer
FSM_END = 6        # END - session complete (use REVEAL+1 conceptually)

MAX_ATTEMPTS = 3   # After 3 wrong attempts, reveal answer

# ===============================
# Math Question Generator
# ===============================
ADDITION_EXPLAIN = """Let's learn about addition!

Addition means putting numbers together to find a total.
When we add, we use the + symbol.

For example:
  2 + 3 = 5  (two plus three equals five)
  4 + 1 = 5  (four plus one equals five)

Now let's practice with some questions!"""


def generate_addition_question():
    """Generate a simple addition question with numbers <= 20."""
    # Keep both numbers small so sum <= 20
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    answer = a + b

    return {
        "a": a,
        "b": b,
        "answer": answer,
        "prompt": f"What is {a} + {b}?",
        "hint1": f"Try counting: start with {a}, then count up {b} more.",
        "hint2": f"Use your fingers! Hold up {a} fingers, then {b} more. Count them all.",
        "reveal": f"The answer is {answer}. {a} + {b} = {answer}",
    }


# ===============================
# Answer Parser (Rule-based)
# ===============================
WORD_TO_NUM = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4,
    "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20,
}


def parse_answer(user_text: str) -> int | None:
    """
    Extract numeric answer from user input.

    Handles:
    - Plain number: "8"
    - Word: "eight"
    - Equation: "3+5=8"
    - Sentence: "the answer is 8"
    - With spaces: "3 + 5 = 8"
    """
    text = user_text.strip().lower()

    if not text:
        return None

    # Pattern 1: Extract number after "=" or "is"
    match = re.search(r'[=]\s*(\d+)', text)
    if match:
        return int(match.group(1))

    match = re.search(r'\bis\s+(\d+)', text)
    if match:
        return int(match.group(1))

    # Pattern 2: Word number anywhere
    for word, num in WORD_TO_NUM.items():
        if word in text:
            return num

    # Pattern 3: Plain number (last number in string for "3+5=8" without spaces)
    numbers = re.findall(r'\d+', text)
    if numbers:
        # Take the last number (likely the answer)
        return int(numbers[-1])

    return None


def is_correct_answer(user_text: str, expected: int) -> bool:
    """Check if user's answer matches expected value."""
    parsed = parse_answer(user_text)
    return parsed == expected


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
# gRPC Service with FSM
# ===============================
class TutoringServicer(tutoring_pb2_grpc.TutoringServiceServicer):

    def StartSession(self, request, context):
        """START state: Create session, immediately go to EXPLAIN."""
        if not request.student_id:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("student_id required")
            return tutoring_pb2.StartSessionResponse()

        # Generate first question
        q = generate_addition_question()

        # Create session with EXPLAIN state
        session_id = _run_async(
            create_session(
                student_id=request.student_id,
                topic_id="t_cbse6_math_add",
                state="EXPLAIN",
                current_question_id=None,
                fsm_data={
                    "current_question": q,
                    "attempt_count": 0,
                    "questions_completed": 0,
                    "total_questions": 5,  # 5 questions per session
                }
            )
        )

        # Return EXPLAIN state with teaching content
        return tutoring_pb2.StartSessionResponse(
            session_id=session_id,
            state=tutoring_pb2.FsmState.EXPLAIN,
            tutor_text=ADDITION_EXPLAIN,
        )

    def Turn(self, request, context):
        """Process user input and transition FSM states."""
        session = _run_async(get_session(request.session_id))
        if not session:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Session not found")
            return tutoring_pb2.TurnResponse()

        current_state = session["state"]
        fsm_data = session.get("fsm_data") or {}
        student_id = request.student_id or session["student_id"]

        # Get current question data
        current_q = fsm_data.get("current_question") or generate_addition_question()
        attempt_count = fsm_data.get("attempt_count", 0)
        questions_completed = fsm_data.get("questions_completed", 0)
        total_questions = fsm_data.get("total_questions", 5)

        # ========== STATE MACHINE ==========

        # EXPLAIN → QUIZ (any input advances)
        if current_state == "EXPLAIN":
            fsm_data["attempt_count"] = 0
            _run_async(update_session(
                request.session_id,
                state="QUIZ",
                fsm_data=fsm_data
            ))

            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.FsmState.QUIZ,
                tutor_text=f"Question {questions_completed + 1}: {current_q['prompt']}",
                attempt_count=0,
            )

        # QUIZ → EVALUATE (any input is treated as answer attempt)
        if current_state == "QUIZ":
            # Immediately transition to EVALUATE and process answer
            current_state = "EVALUATE"

        # EVALUATE: Check answer
        if current_state == "EVALUATE":
            user_text = request.user_text
            expected = current_q["answer"]

            if is_correct_answer(user_text, expected):
                # CORRECT! Record attempt and move on
                attempt_count += 1
                _run_async(insert_attempt(
                    request.session_id, student_id, "addition",
                    f"q{questions_completed + 1}", True
                ))

                questions_completed += 1

                # Check if session complete
                if questions_completed >= total_questions:
                    _run_async(update_session(
                        request.session_id,
                        state="COMPLETED",
                        fsm_data=fsm_data
                    ))
                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.FsmState.REVEAL,  # Use REVEAL as END
                        tutor_text=f"Correct! {current_q['a']} + {current_q['b']} = {expected}\n\n"
                                   f"Great job! You completed all {total_questions} questions!",
                        intent="complete",
                        attempt_count=attempt_count,
                    )

                # Generate next question
                new_q = generate_addition_question()
                fsm_data["current_question"] = new_q
                fsm_data["attempt_count"] = 0
                fsm_data["questions_completed"] = questions_completed

                _run_async(update_session(
                    request.session_id,
                    state="QUIZ",
                    fsm_data=fsm_data
                ))

                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.FsmState.QUIZ,
                    tutor_text=f"Correct! {current_q['a']} + {current_q['b']} = {expected}\n\n"
                               f"Question {questions_completed + 1}: {new_q['prompt']}",
                    intent="correct",
                    attempt_count=attempt_count,
                )

            else:
                # WRONG - escalate hints
                attempt_count += 1
                fsm_data["attempt_count"] = attempt_count

                _run_async(insert_attempt(
                    request.session_id, student_id, "addition",
                    f"q{questions_completed + 1}", False
                ))

                if attempt_count == 1:
                    # First wrong → HINT1
                    _run_async(update_session(
                        request.session_id,
                        state="HINT",
                        fsm_data=fsm_data
                    ))
                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.FsmState.HINT,
                        tutor_text=f"Not quite. Let me help!\n\n{current_q['hint1']}\n\nTry again: {current_q['prompt']}",
                        intent="hint1",
                        attempt_count=attempt_count,
                        frustration_counter=1,
                    )

                elif attempt_count == 2:
                    # Second wrong → HINT2
                    _run_async(update_session(
                        request.session_id,
                        state="HINT",
                        fsm_data=fsm_data
                    ))
                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.FsmState.HINT,
                        tutor_text=f"Still not right. Here's another way to think about it:\n\n{current_q['hint2']}\n\nOne more try: {current_q['prompt']}",
                        intent="hint2",
                        attempt_count=attempt_count,
                        frustration_counter=2,
                    )

                else:
                    # Third wrong → REVEAL and move on
                    questions_completed += 1

                    # Check if session complete
                    if questions_completed >= total_questions:
                        _run_async(update_session(
                            request.session_id,
                            state="COMPLETED",
                            fsm_data=fsm_data
                        ))
                        return tutoring_pb2.TurnResponse(
                            session_id=request.session_id,
                            next_state=tutoring_pb2.FsmState.REVEAL,
                            tutor_text=f"{current_q['reveal']}\n\n"
                                       f"You completed all {total_questions} questions! Keep practicing!",
                            intent="complete",
                            attempt_count=attempt_count,
                            frustration_counter=3,
                        )

                    # Generate next question
                    new_q = generate_addition_question()
                    fsm_data["current_question"] = new_q
                    fsm_data["attempt_count"] = 0
                    fsm_data["questions_completed"] = questions_completed

                    _run_async(update_session(
                        request.session_id,
                        state="QUIZ",
                        fsm_data=fsm_data
                    ))

                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.FsmState.REVEAL,
                        tutor_text=f"{current_q['reveal']}\n\n"
                                   f"Let's try another one!\n\nQuestion {questions_completed + 1}: {new_q['prompt']}",
                        intent="reveal",
                        attempt_count=attempt_count,
                        frustration_counter=3,
                    )

        # HINT state → user tries again → back to EVALUATE
        if current_state == "HINT":
            # Process as EVALUATE
            user_text = request.user_text
            expected = current_q["answer"]

            if is_correct_answer(user_text, expected):
                # CORRECT after hint
                attempt_count += 1
                _run_async(insert_attempt(
                    request.session_id, student_id, "addition",
                    f"q{questions_completed + 1}", True
                ))

                questions_completed += 1

                if questions_completed >= total_questions:
                    _run_async(update_session(
                        request.session_id,
                        state="COMPLETED",
                        fsm_data=fsm_data
                    ))
                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.FsmState.REVEAL,
                        tutor_text=f"Correct! {current_q['a']} + {current_q['b']} = {expected}\n\n"
                                   f"Excellent! You completed all {total_questions} questions!",
                        intent="complete",
                        attempt_count=attempt_count,
                    )

                new_q = generate_addition_question()
                fsm_data["current_question"] = new_q
                fsm_data["attempt_count"] = 0
                fsm_data["questions_completed"] = questions_completed

                _run_async(update_session(
                    request.session_id,
                    state="QUIZ",
                    fsm_data=fsm_data
                ))

                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.FsmState.QUIZ,
                    tutor_text=f"Correct! {current_q['a']} + {current_q['b']} = {expected}\n\n"
                               f"Question {questions_completed + 1}: {new_q['prompt']}",
                    intent="correct",
                    attempt_count=attempt_count,
                )
            else:
                # Wrong again - continue escalation
                attempt_count += 1
                fsm_data["attempt_count"] = attempt_count

                _run_async(insert_attempt(
                    request.session_id, student_id, "addition",
                    f"q{questions_completed + 1}", False
                ))

                if attempt_count == 2:
                    _run_async(update_session(
                        request.session_id,
                        state="HINT",
                        fsm_data=fsm_data
                    ))
                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.FsmState.HINT,
                        tutor_text=f"Not quite yet. Here's another hint:\n\n{current_q['hint2']}\n\nLast try: {current_q['prompt']}",
                        intent="hint2",
                        attempt_count=attempt_count,
                        frustration_counter=2,
                    )
                else:
                    # attempt_count >= 3 → REVEAL
                    questions_completed += 1

                    if questions_completed >= total_questions:
                        _run_async(update_session(
                            request.session_id,
                            state="COMPLETED",
                            fsm_data=fsm_data
                        ))
                        return tutoring_pb2.TurnResponse(
                            session_id=request.session_id,
                            next_state=tutoring_pb2.FsmState.REVEAL,
                            tutor_text=f"{current_q['reveal']}\n\n"
                                       f"Session complete! You practiced {total_questions} questions.",
                            intent="complete",
                            attempt_count=attempt_count,
                            frustration_counter=3,
                        )

                    new_q = generate_addition_question()
                    fsm_data["current_question"] = new_q
                    fsm_data["attempt_count"] = 0
                    fsm_data["questions_completed"] = questions_completed

                    _run_async(update_session(
                        request.session_id,
                        state="QUIZ",
                        fsm_data=fsm_data
                    ))

                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.FsmState.REVEAL,
                        tutor_text=f"{current_q['reveal']}\n\n"
                                   f"Let's continue!\n\nQuestion {questions_completed + 1}: {new_q['prompt']}",
                        intent="reveal",
                        attempt_count=attempt_count,
                        frustration_counter=3,
                    )

        # COMPLETED state - session is done
        if current_state == "COMPLETED":
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.FsmState.REVEAL,
                tutor_text="This session is complete! Start a new session to practice more.",
                intent="complete",
            )

        # Fallback - unknown state
        return tutoring_pb2.TurnResponse(
            session_id=request.session_id,
            tutor_text=f"Unknown state: {current_state}. Please start a new session.",
            intent="error",
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
        _server.stop(grace=10)

    try:
        _run_async(close_pool())
        print("[gRPC] DB pool closed", flush=True)
    except Exception as e:
        print(f"[gRPC] Error closing DB pool: {e}", flush=True)

    _async_queue.put((None, None))
    print("[gRPC] Shutdown complete", flush=True)


def serve():
    global _server, _health_servicer

    grpc_port = os.getenv("PORT") or os.getenv("GRPC_PORT", "50051")

    _run_async(init_pool())

    _server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    tutoring_pb2_grpc.add_TutoringServiceServicer_to_server(
        TutoringServicer(), _server
    )

    if HEALTH_CHECK_AVAILABLE:
        _health_servicer = health.HealthServicer()
        health_pb2_grpc.add_HealthServicer_to_server(_health_servicer, _server)
        _health_servicer.set("", health_pb2.HealthCheckResponse.SERVING)
        _health_servicer.set("TutoringService", health_pb2.HealthCheckResponse.SERVING)

    _server.add_insecure_port(f"0.0.0.0:{grpc_port}")
    print(f"GRPC_LISTENING 0.0.0.0:{grpc_port}", flush=True)

    signal.signal(signal.SIGTERM, _shutdown_handler)
    signal.signal(signal.SIGINT, _shutdown_handler)

    _server.start()
    health_status = "enabled" if HEALTH_CHECK_AVAILABLE else "disabled"
    print(f"[gRPC] Server started, health check {health_status}", flush=True)
    _server.wait_for_termination()


if __name__ == "__main__":
    serve()
