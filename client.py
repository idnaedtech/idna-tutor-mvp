import grpc
import tutoring_pb2
import tutoring_pb2_grpc
import sys

def main():
    channel = grpc.insecure_channel("localhost:50051")
    stub = tutoring_pb2_grpc.TutoringServiceStub(channel)

    # Check if we're using a hardcoded session_id for persistence testing
    if len(sys.argv) > 1:
        sid = sys.argv[1]
        print(f"Using hardcoded session_id: {sid}")
        def turn(text):
            resp = stub.Turn(tutoring_pb2.TurnRequest(student_id="00000000-0000-0000-0000-000000000001", session_id=sid, user_text=text))
            print("USER:", text)
            print("BOT :", resp.tutor_text, "| next_state:", resp.next_state, "| intent:", resp.intent, "| attempts:", resp.attempt_count)
            print("-"*60)
        turn("test")
    else:
        start = stub.StartSession(tutoring_pb2.StartSessionRequest(student_id="00000000-0000-0000-0000-000000000001"))
        print("StartSession:", start)
        print("SESSION_ID:", start.session_id)

        sid = start.session_id

        def turn(text):
            resp = stub.Turn(tutoring_pb2.TurnRequest(student_id="00000000-0000-0000-0000-000000000001", session_id=sid, user_text=text))
            print("USER:", text)
            print("BOT :", resp.tutor_text, "| next_state:", resp.next_state, "| intent:", resp.intent, "| attempts:", resp.attempt_count)
            print("-"*60)

        turn("next")
        turn("5")     # wrong
        turn("anything")  # will be evaluated (wrong) -> hint/reveal path
        turn("4")     # try correct

if __name__ == "__main__":
    main()
