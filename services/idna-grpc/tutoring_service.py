# services/idna-grpc/tutoring_service.py
import time
import uuid
import grpc

import tutoring_pb2
import tutoring_pb2_grpc


class TutoringService(tutoring_pb2_grpc.TutoringServiceServicer):
    def StartSession(self, request, context):
        # Create a session_id even if DB is not ready.
        session_id = str(uuid.uuid4())

        # Your proto likely has fields: session_id, next_state, tutor_text, intent, etc.
        # We only set the safest common ones: session_id + tutor_text.
        resp = tutoring_pb2.StartSessionResponse(
            session_id=session_id,
            tutor_text="Session started.",
        )
        return resp

    def Turn(self, request, context):
        # Echo back to prove connectivity.
        user_text = getattr(request, "user_text", "")
        session_id = getattr(request, "session_id", "")

        resp = tutoring_pb2.TurnResponse(
            session_id=session_id,
            tutor_text=f"gRPC received: {user_text}",
            intent="echo",
        )
        return resp
