from main import serve
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    tutoring_pb2_grpc.add_TutoringServiceServicer_to_server(TutoringServicer(), server)
    import os  # add near the top of the file if not already present
    port = os.environ.get("PORT", "50051")
    server.add_insecure_port(f"0.0.0.0:{port}")
    server.start()
    print(f"gRPC FSM server running on 0.0.0.0:{port}")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
