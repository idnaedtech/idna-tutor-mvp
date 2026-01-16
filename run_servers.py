#!/usr/bin/env python3
"""Start both gRPC and FastAPI servers for Railway deployment"""
import subprocess
import time
import sys
import os

# Get port from Railway environment (defaults to 8000 for local dev)
web_port = os.environ.get("PORT", "8000")
grpc_port = os.environ.get("GRPC_PORT", "50051")

# Set GRPC_TARGET for webapp to connect to gRPC server
os.environ["GRPC_TARGET"] = f"localhost:{grpc_port}"

# Start gRPC server (from services/idna-grpc/)
grpc_env = os.environ.copy()
grpc_env["GRPC_PORT"] = grpc_port
grpc_proc = subprocess.Popen(
    [sys.executable, "services/idna-grpc/main.py"],
    env=grpc_env
)
print(f"[run_servers] gRPC server starting on port {grpc_port}...", flush=True)
time.sleep(3)

# Check if gRPC server started successfully
if grpc_proc.poll() is not None:
    print(f"[run_servers] ERROR: gRPC server exited with code {grpc_proc.returncode}", flush=True)
    sys.exit(1)

print(f"[run_servers] Starting FastAPI on port {web_port}...", flush=True)

# Start FastAPI/uvicorn server (blocking)
subprocess.run([
    sys.executable, "-m", "uvicorn",
    "webapp:app",
    "--host", "0.0.0.0",
    "--port", web_port
])
