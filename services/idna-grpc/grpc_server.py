# services/idna-grpc/grpc_server.py
import os
import grpc
from concurrent import futures

import tutoring_pb2_grpc
from tutoring_service import TutoringService  # adjust if your servicer class is in a different file


def serve(port: int | None = None):
    port = port or int(os.getenv("GRPC_PORT", "50051"))

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tutoring_pb2_grpc.add_TutoringServicer_to_server(TutoringService(), server)

    bind_addr = f"0.0.0.0:{port}"
    server.add_insecure_port(bind_addr)

    print("GRPC_LISTENING", bind_addr, flush=True)
    server.start()
    server.wait_for_termination()
