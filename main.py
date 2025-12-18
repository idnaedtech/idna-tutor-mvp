import grpc
from concurrent import futures
import sys

from protos import tutoring_pb2
from protos import tutoring_pb2_grpc


class TutoringServicer(tutoring_pb2_grpc.TutoringServiceServicer):
    def Ping(self, request, context):
        return tutoring_pb2.PingResponse(msg="PONG: " + request.msg)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=5))
    tutoring_pb2_grpc.add_TutoringServiceServicer_to_server(TutoringServicer(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    print("gRPC server running on :50051")
    server.wait_for_termination()


if __name__ == "__main__":
    serve()
