import grpc
from concurrent import futures
import uuid

from protos import tutoring_pb2
from protos import tutoring_pb2_grpc


class TutoringServicer(tutoring_pb2_grpc.TutoringServiceServicer):
    def __init__(self):
        self.sessions = {}
    
    def StartSession(self, request, context):
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "student_id": request.student_id,
            "state": tutoring_pb2.EXPLAIN,
            "attempt_count": 0,
            "frustration_counter": 0,
        }
        return tutoring_pb2.StartSessionResponse(
            session_id=session_id,
            state=tutoring_pb2.EXPLAIN,
            tutor_text="Hello! Let's start learning. I'll explain the concept first."
        )
    
    def Turn(self, request, context):
        session = self.sessions.get(request.session_id)
        if not session:
            context.abort(grpc.StatusCode.NOT_FOUND, "Session not found")
        
        session["attempt_count"] += 1
        current_state = session["state"]
        next_state = current_state
        tutor_text = "Great! Keep learning."
        intent = "respond"
        
        if current_state == tutoring_pb2.EXPLAIN:
            next_state = tutoring_pb2.QUIZ
            tutor_text = "Now let's test your understanding with a quiz."
            intent = "transition_to_quiz"
        elif current_state == tutoring_pb2.QUIZ:
            next_state = tutoring_pb2.EVALUATE
            tutor_text = "Let me evaluate your answer."
            intent = "evaluate_answer"
        elif current_state == tutoring_pb2.EVALUATE:
            next_state = tutoring_pb2.EXPLAIN
            tutor_text = "Let me explain this further."
            intent = "provide_hint"
        
        session["state"] = next_state
        
        return tutoring_pb2.TurnResponse(
            session_id=request.session_id,
            next_state=next_state,
            tutor_text=tutor_text,
            attempt_count=session["attempt_count"],
            frustration_counter=session["frustration_counter"],
            intent=intent
        )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    tutoring_pb2_grpc.add_TutoringServiceServicer_to_server(TutoringServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server running on :50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
