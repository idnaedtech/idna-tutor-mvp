import grpc
import tutoring_pb2
import tutoring_pb2_grpc

STUDENT_ID = "00000000-0000-0000-0000-000000000001"

def main():
    channel = grpc.insecure_channel("localhost:50051")
    stub = tutoring_pb2_grpc.TutoringServiceStub(channel)

    start = stub.StartSession(tutoring_pb2.StartSessionRequest(student_id=STUDENT_ID))
    print("StartSession response:", start)

    with open("last_session.txt", "w") as f:
        f.write(start.session_id)

    print("Saved session_id to last_session.txt:", start.session_id)

if __name__ == "__main__":
    main()
