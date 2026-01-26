import grpc
import tutoring_pb2
import tutoring_pb2_grpc

STUDENT_ID = "00000000-0000-0000-0000-000000000001"

def main():
    with open("last_session.txt", "r") as f:
        sid = f.read().strip()

    channel = grpc.insecure_channel("localhost:50051")
    stub = tutoring_pb2_grpc.TutoringServiceStub(channel)

    resp = stub.Turn(tutoring_pb2.TurnRequest(
        student_id=STUDENT_ID,
        session_id=sid,
        user_text="next"
    ))
    print("Resume Turn response:", resp)

if __name__ == "__main__":
    main()
