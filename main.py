import uuid
import grpc
from concurrent import futures

import tutoring_pb2
import tutoring_pb2_grpc

# --- In-memory state (for learning). DB comes later. ---
SESSIONS = {}  # session_id -> state dict

def classify_intent(text: str) -> str:
    t = (text or "").strip().lower()
    if t == "" or t in {"...", "hmm"}:
        return "silence"
    if t in {"next", "ok", "okay", "continue"}:
        return "command_next"
    if t in {"repeat", "again"}:
        return "command_repeat"
    if "don't know" in t or "dont know" in t or t in {"idk"}:
        return "dont_know"
    if any(x in t for x in ["stop", "wait"]):
        return "interrupt"
    if len(t) < 2:
        return "nonsense"
    return "content"

def understood_signal(text: str) -> bool:
    t = (text or "").strip().lower()
    if t in {"next", "ask me a question", "question", "quiz"}:
        return True
    # simple paraphrase heuristic
    return len(t.split()) >= 4

def grade_answer(user_text: str) -> bool:
    # MVP: fixed question with fixed answer for now
    # Question: "What is 2 + 2?"
    # Answer: "4"
    t = (user_text or "").strip().lower()
    return t in {"4", "four"}

class TutoringServicer(tutoring_pb2_grpc.TutoringServiceServicer):
    def StartSession(self, request, context):
        session_id = str(uuid.uuid4())
        SESSIONS[session_id] = {
            "student_id": request.student_id,
            "state": tutoring_pb2.EXPLAIN,
            "attempt_count": 0,
            "frustration": 0,
            "question": "What is 2 + 2?",
        }
        return tutoring_pb2.StartSessionResponse(
            session_id=session_id,
            state=tutoring_pb2.EXPLAIN,
            tutor_text="Today we learn addition. When ready, say 'next' or explain it back in one line."
        )

    def Turn(self, request, context):
        s = SESSIONS.get(request.session_id)
        if not s:
            context.set_code(grpc.StatusCode.NOT_FOUND)
            context.set_details("Session not found. StartSession first.")
            return tutoring_pb2.TurnResponse()

        user_text = request.user_text or ""
        intent = classify_intent(user_text)

        # universal interrupt
        if intent == "interrupt":
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=s["state"],
                tutor_text="Okay. Tell me your doubt in one line.",
                attempt_count=s["attempt_count"],
                frustration_counter=s["frustration"],
                intent=intent
            )

        state = s["state"]

        # --- EXPLAIN ---
        if state == tutoring_pb2.EXPLAIN:
            if intent == "command_repeat":
                tutor_text = "Addition means combining numbers. Example: 2 + 2 = 4. Say 'next' when ready."
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.EXPLAIN,
                    tutor_text=tutor_text,
                    attempt_count=s["attempt_count"],
                    frustration_counter=s["frustration"],
                    intent=intent
                )

            if understood_signal(user_text) or intent == "command_next":
                s["state"] = tutoring_pb2.QUIZ
                s["attempt_count"] = 0
                tutor_text = f"Question: {s['question']}"
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.QUIZ,
                    tutor_text=tutor_text,
                    attempt_count=s["attempt_count"],
                    frustration_counter=s["frustration"],
                    intent="ask_question"
                )

            tutor_text = "Addition means combining numbers. Say 'next' when ready, or explain in one line."
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.EXPLAIN,
                tutor_text=tutor_text,
                attempt_count=s["attempt_count"],
                frustration_counter=s["frustration"],
                intent="teach"
            )

        # --- QUIZ -> EVALUATE ---
        if state == tutoring_pb2.QUIZ:
            s["state"] = tutoring_pb2.EVALUATE
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.EVALUATE,
                tutor_text="Got it. Let me check.",
                attempt_count=s["attempt_count"],
                frustration_counter=s["frustration"],
                intent="evaluate"
            )

        # --- EVALUATE ---
        if state == tutoring_pb2.EVALUATE:
            correct = grade_answer(user_text)
            if correct:
                s["state"] = tutoring_pb2.EXPLAIN
                s["attempt_count"] = 0
                s["frustration"] = 0
                tutor_text = "Correct. Good. We move to the next concept later."
                return tutoring_pb2.TurnResponse(
                    session_id=request.session_id,
                    next_state=tutoring_pb2.EXPLAIN,
                    tutor_text=tutor_text,
                    attempt_count=s["attempt_count"],
                    frustration_counter=s["frustration"],
                    intent="correct"
                )
            else:
                s["attempt_count"] += 1
                s["frustration"] += 1
                if s["attempt_count"] >= 2 or s["frustration"] >= 3:
                    # reveal and move on
                    s["state"] = tutoring_pb2.EXPLAIN
                    s["attempt_count"] = 0
                    s["frustration"] = 0
                    tutor_text = "Not quite. The answer is 4 because 2+2 means two groups of two. Moving on."
                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.EXPLAIN,
                        tutor_text=tutor_text,
                        attempt_count=0,
                        frustration_counter=0,
                        intent="reveal"
                    )
                else:
                    s["state"] = tutoring_pb2.HINT
                    tutor_text = "Hint: count 2, then count 2 more."
                    return tutoring_pb2.TurnResponse(
                        session_id=request.session_id,
                        next_state=tutoring_pb2.HINT,
                        tutor_text=tutor_text,
                        attempt_count=s["attempt_count"],
                        frustration_counter=s["frustration"],
                        intent="hint"
                    )

        # --- HINT -> QUIZ again ---
        if state == tutoring_pb2.HINT:
            s["state"] = tutoring_pb2.QUIZ
            tutor_text = f"Try again: {s['question']}"
            return tutoring_pb2.TurnResponse(
                session_id=request.session_id,
                next_state=tutoring_pb2.QUIZ,
                tutor_text=tutor_text,
                attempt_count=s["attempt_count"],
                frustration_counter=s["frustration"],
                intent="retry"
            )

        # fallback
        s["state"] = tutoring_pb2.EXPLAIN
        return tutoring_pb2.TurnResponse(
            session_id=request.session_id,
            next_state=tutoring_pb2.EXPLAIN,
            tutor_text="Reset. Let's continue.",
            attempt_count=s["attempt_count"],
            frustration_counter=s["frustration"],
            intent="reset"
        )

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tutoring_pb2_grpc.add_TutoringServiceServicer_to_server(TutoringServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC FSM server running on :50051")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
